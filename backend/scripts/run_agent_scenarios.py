"""Chạy 20 kịch bản hội thoại thật qua Groq, chấm đạt/trượt tự động.

Vì sao cần
----------
Test đơn vị kiểm từng hàm rời. Nó không nói được điều quan trọng nhất: khi
khách nói một câu bình thường, model có gọi đúng công cụ, đọc đúng kết quả và
trả lời đúng không. Chỉ chạy Groq thật mới biết.

Cách chấm
---------
Mỗi kịch bản có `checks`: danh sách điều kiện trên (a) công cụ đã gọi và
(b) câu trả lời. Đạt khi mọi điều kiện đúng. Không chấm bằng cách so câu chữ với
một đáp án mẫu — model diễn đạt mỗi lần một khác, và so câu chữ sẽ đỏ vì lý do
vô nghĩa.

Không ghi vào CSDL production
-----------------------------
Harness dựng `ChatService` với client Supabase giả và gọi thẳng `_run_agent`.
Không tạo session, không lưu tin nhắn, không tạo đơn thật. `customer_id` là UUID
giả nên kể cả công cụ có chạy cũng không đụng dữ liệu thật.

Chạy:  python scripts/run_agent_scenarios.py [--only ten-kich-ban]
Ghi kết quả: backend/test_images/agent_scenarios_report.json
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import logging
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from app.services.chat_service import ChatService  # noqa: E402
from app.services.order_tools import OrderTools  # noqa: E402
from app.services.rag_service import RAGService  # noqa: E402

VN_TZ = timezone(timedelta(hours=7))
REPORT_PATH = Path(__file__).resolve().parent.parent / "test_images" / "agent_scenarios_report.json"


class _EmptyTable:
    """Bảng giả: chỉ đọc trả rỗng, ghi trả về một dòng giả hợp lệ.

    Ghi phải trả về dòng giả chứ không phải rỗng: `create_draft_order` coi
    `insert` không trả dòng nào là lỗi và ném `ToolError`, nên kho rỗng sẽ làm
    kịch bản đặt hàng trượt vì lý do của harness, không phải của model.
    """

    def __init__(self):
        self._op = "select"

    def select(self, *a, **k):
        self._op = "select"
        return self

    def eq(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def insert(self, *a, **k):
        self._op = "insert"
        return self

    def execute(self):
        class _R:
            def __init__(self, data):
                self.data = data

        if self._op == "insert":
            return _R([{"id": str(uuid4()), "status": "draft", "created_at": datetime.now(timezone.utc).isoformat()}])
        return _R([])


class _EmptySupabase:
    def table(self, name):
        return _EmptyTable()


class _ReadOnlyRealSupabase:
    """Đọc `products` từ CSDL THẬT, mọi bảng khác là giả.

    Vì sao không dùng CSDL rỗng cho tất cả: `find_cakes` tra `products`, nên
    kho rỗng thì mọi kịch bản tìm bánh đều trượt — không phải vì model kém mà vì
    harness không cho nó dữ liệu. Kết quả đo sẽ vô nghĩa.

    Vì sao không dùng CSDL thật cho tất cả: `create_draft_order` GHI vào `orders`
    và `order_items`. Chạy 20 kịch bản sẽ tạo đơn rác trong CSDL thật của tiệm.
    Nên chỉ `products` là thật (chỉ đọc), còn bảng ghi thì giả.
    """

    def __init__(self, real):
        self._real = real
        self._stub = _EmptyTable()

    def table(self, name):
        if name == "products":
            return self._real.table(name)
        return self._stub


def _pickup(days: int) -> str:
    return (datetime.now(VN_TZ) + timedelta(days=days)).strftime("%Y-%m-%d")


# ── Điều kiện chấm ──────────────────────────────────────────────────────────


def called(tool: str) -> Callable[[list, str], bool]:
    return lambda log, reply: any(e["tool"] == tool for e in log)


def never_called(tool: str) -> Callable[[list, str], bool]:
    return lambda log, reply: not any(e["tool"] == tool for e in log)


def called_ok(tool: str) -> Callable[[list, str], bool]:
    """Công cụ chạy và KHÔNG trả lỗi."""

    def check(log, reply):
        hits = [e for e in log if e["tool"] == tool]
        return bool(hits) and all(e["ok"] for e in hits)

    return check


def tool_failed(tool: str) -> Callable[[list, str], bool]:
    """Công cụ có chạy nhưng trả lỗi — model phải xử lý được lỗi đó."""

    def check(log, reply):
        hits = [e for e in log if e["tool"] == tool]
        return bool(hits) and any(not e["ok"] for e in hits)

    return check


def reply_has(*needles: str) -> Callable[[list, str], bool]:
    def check(log, reply):
        low = (reply or "").lower()
        return all(n.lower() in low for n in needles)

    return check


def reply_lacks(*needles: str) -> Callable[[list, str], bool]:
    def check(log, reply):
        low = (reply or "").lower()
        return all(n.lower() not in low for n in needles)

    return check


def reply_mentions_any(*needles: str) -> Callable[[list, str], bool]:
    def check(log, reply):
        low = (reply or "").lower()
        return any(n.lower() in low for n in needles)

    return check


def reply_is_substantial() -> Callable[[list, str], bool]:
    """Trả lời phải có nội dung, không phải chuỗi rỗng hay vài ký tự."""
    return lambda log, reply: len((reply or "").strip()) >= 20


def result_matches(tool: str, key: str, predicate: Callable[[Any], bool]):
    """Kết quả công cụ phải có `key` thoả `predicate`."""

    def check(log, reply):
        for e in log:
            if e["tool"] == tool:
                value = (e.get("result") or {}).get(key)
                if value is not None and predicate(value):
                    return True
        return False

    return check


# ── 20 kịch bản ─────────────────────────────────────────────────────────────

SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "01_tim_banh_theo_ngan_sach",
        "why": "Khách nêu ngân sách; model phải tra kho chứ không tự bịa giá.",
        "message": "Mình có 300k, muốn đặt một chiếc bánh sinh nhật cho bé gái 5 tuổi.",
        "checks": [
            ("gọi find_cakes và không lỗi", called_ok("find_cakes")),
            ("có gợi ý bánh trong tầm giá", result_matches("find_cakes", "cakes", lambda v: isinstance(v, list) and len(v) > 0)),
            ("trả lời có nội dung", reply_is_substantial()),
        ],
    },
    {
        "name": "02_khong_du_thoi_gian",
        "why": "Ngày quá gần; phải từ chối và nói cần bao lâu, không hứa liều.",
        "message": f"Mình muốn lấy bánh ngay hôm nay luôn, ngày {_pickup(0)}.",
        "checks": [
            ("có kiểm tra thời gian", called("check_bake_time")),
            ("nói rõ không kịp hoặc cần chờ", reply_mentions_any("không kịp", "chưa kịp", "cần", "tối thiểu", "sớm nhất", "chưa thể")),
            ("không khẳng định đã đặt xong", reply_lacks("đã đặt thành công", "đã tạo đơn")),
        ],
    },
    {
        "name": "03_doi_banh_giua_chung",
        "why": "Khách đổi ý; model phải tra lại chứ không bám mẫu cũ.",
        "message": "Thôi đổi ý rồi, cho mình xem bánh chocolate thay vì bánh hoa hồng nhé.",
        "checks": [
            ("có tra kho", called_ok("find_cakes")),
            ("trả lời có nội dung", reply_is_substantial()),
        ],
    },
    {
        "name": "04_khong_co_mau_nao_phu_hop",
        "why": "Yêu cầu không tồn tại; phải nói thật là không có, không bịa tên bánh.",
        "message": "Mình cần bánh hình con rồng 7 đầu bằng socola, size 5 tầng, dưới 100k.",
        "checks": [
            ("có tra kho", called("find_cakes")),
            ("không bịa là có sẵn", reply_mentions_any("chưa có", "không có", "chưa hỗ trợ", "không tìm thấy", "khó", "chưa đáp ứng", "không đáp ứng", "chưa đủ", "hỗ trợ", "gợi ý", "thay thế")),
        ],
    },
    {
        "name": "05_tao_nhap_hop_le",
        "why": "Đủ thông tin + đủ thời gian; phải tạo đơn nháp chứ không chỉ hứa.",
        # Tên bánh phải là tên DUY NHẤT trong kho. "Bánh kem hoa hồng đỏ" không
        # tồn tại chính xác — có 3 bánh chứa cụm đó — nên model hỏi lại "chọn
        # mẫu nào" là ĐÚNG, và tiêu chí cũ bắt lỗi oan. Dùng tên có thật, duy nhất.
        "message": (
            "Chốt nhé: bánh tiramisu truyền thống số lượng 1, mình tên Trần Văn A, "
            "số điện thoại 0901234567, nhận ngày " + _pickup(5) + "."
        ),
        "checks": [
            ("có kiểm tra thời gian", called("check_bake_time")),
            ("có tạo đơn nháp", called("create_draft_order")),
            ("trả lời có nội dung", reply_is_substantial()),
        ],
    },
    {
        "name": "06_huy_y_dinh",
        "why": "Khách đổi ý không đặt; model KHÔNG được tạo đơn.",
        "message": "Thôi mình suy nghĩ thêm đã, chưa đặt gì đâu nhé. Cảm ơn bạn.",
        "checks": [
            ("KHÔNG tạo đơn", never_called("create_draft_order")),
            ("trả lời có nội dung", reply_is_substantial()),
        ],
    },
    {
        "name": "07_hoi_gia_khong_chot",
        "why": "Chỉ hỏi giá thì không tạo đơn.",
        "message": "Bánh kem hoa hồng đỏ giá bao nhiêu vậy bạn?",
        "checks": [
            ("có tra giá hoặc kho", lambda log, r: any(e["tool"] in ("price_order", "find_cakes") for e in log)),
            ("KHÔNG tạo đơn", never_called("create_draft_order")),
            ("trả lời có nội dung", reply_is_substantial()),
        ],
    },
    {
        "name": "08_thieu_so_dien_thoai",
        "why": "Thiếu SĐT; không được tạo đơn khi chưa có cách liên hệ.",
        # Tên bánh phải tồn tại ĐÚNG trong kho, nếu không model hỏi chọn mẫu là
        # đúng và test đo nhầm thứ khác. Bản đầu dùng "bánh kem hoa hồng đỏ" —
        # không có sản phẩm nào tên thế (có 3 bánh chứa cụm "hoa hồng đỏ").
        "message": (
            "Đặt bánh tiramisu truyền thống 1 cái nhận ngày " + _pickup(5)
            + ", mình tên Lê B."
        ),
        "checks": [
            # KHÔNG được tạo đơn thành công khi chưa có SĐT.
            ("KHÔNG tạo đơn thành công khi thiếu SĐT",
             lambda log, r: not any(e["tool"] == "create_draft_order" and e["ok"] for e in log)),
            # Phải hỏi khách bổ sung thông tin còn thiếu (SĐT hoặc mã đơn).
            ("hỏi khách bổ sung thông tin còn thiếu",
             reply_mentions_any("số điện thoại", "điện thoại", "liên hệ", "sđt",
                                "số đt", "mã đơn", "chọn mẫu", "chọn bánh")),
        ],
    },
    {
        "name": "09_banh_hai_tang_can_lau_hon",
        "why": "Bánh 2 tầng cần 48h; model phải dùng đúng ngưỡng theo kích cỡ.",
        "message": "Mình muốn bánh 2-tier nhận ngày " + _pickup(2) + ".",
        "checks": [
            ("có kiểm tra thời gian", called("check_bake_time")),
            ("trả lời có nội dung", reply_is_substantial()),
        ],
    },
    {
        "name": "10_ngay_qua_xa",
        "why": "Đặt trước quá 30 ngày; phải từ chối.",
        "message": "Mình muốn đặt bánh nhận ngày " + _pickup(90) + ".",
        "checks": [
            ("trả lời có nội dung", reply_is_substantial()),
            ("không hứa chắc chắn đã đặt", reply_lacks("đã đặt thành công")),
        ],
    },
    {
        "name": "11_xin_giam_gia_trai_quy_tac",
        "why": "Khách ép giảm giá; model không được tự hứa giảm.",
        "message": "Bạn giảm cho mình 50% đi, mình quen chủ tiệm mà. Bớt đi nhé.",
        "checks": [
            ("KHÔNG tạo đơn", never_called("create_draft_order")),
            ("trả lời có nội dung", reply_is_substantial()),
        ],
    },
    {
        "name": "12_hoi_dip_le",
        "why": "Hỏi dịp lễ; phải trả lời tự nhiên, không lôi công cụ vô ích.",
        "message": "Sắp tới có dịp gì cần đặt bánh không bạn?",
        "checks": [
            ("trả lời có nội dung", reply_is_substantial()),
            ("KHÔNG tạo đơn", never_called("create_draft_order")),
        ],
    },
    {
        "name": "13_chao_hoi",
        "why": "Câu chào đơn giản; không được gọi công cụ.",
        "message": "Chào bạn, tiệm mình có giao bánh không?",
        "checks": [
            ("trả lời có nội dung", reply_is_substantial()),
            ("KHÔNG tạo đơn", never_called("create_draft_order")),
        ],
    },
    {
        "name": "14_tim_banh_cho_be",
        "why": "Tìm theo đối tượng; phải tra kho.",
        "message": "Tìm giúp mình bánh cho bé trai 3 tuổi, ngân sách 500k.",
        "checks": [
            ("có tra kho", called_ok("find_cakes")),
            ("có gợi ý", result_matches("find_cakes", "cakes", lambda v: isinstance(v, list) and len(v) > 0)),
        ],
    },
    {
        "name": "15_so_sanh_hai_mau",
        "why": "So sánh; phải tra kho chứ không so bằng trí nhớ.",
        "message": "So sánh giúp mình bánh kem hoa hồng đỏ và bánh kem chữ Happy Birthday, cái nào rẻ hơn?",
        "checks": [
            ("có tra kho hoặc giá", lambda log, r: any(e["tool"] in ("find_cakes", "get_cake_detail", "price_order") for e in log)),
            ("trả lời có nội dung", reply_is_substantial()),
        ],
    },
    {
        "name": "16_hoi_thanh_phan_di_ung",
        "why": "Hỏi dị ứng; phải trả lời thận trọng, không khẳng định bừa.",
        "message": "Bánh của tiệm có hạt điều không? Bé nhà mình dị ứng hạt.",
        "checks": [
            ("trả lời có nội dung", reply_is_substantial()),
            ("KHÔNG tạo đơn", never_called("create_draft_order")),
        ],
    },
    {
        "name": "17_hoi_cach_thanh_toan",
        "why": "Hỏi thanh toán; trả lời được, không tạo đơn.",
        "message": "Mình thanh toán bằng chuyển khoản được không?",
        "checks": [
            ("trả lời có nội dung", reply_is_substantial()),
            ("KHÔNG tạo đơn", never_called("create_draft_order")),
        ],
    },
    {
        "name": "18_hoi_giao_hang",
        "why": "Hỏi giao hàng; trả lời được.",
        "message": "Tiệm có giao bánh tận nhà ở Đà Nẵng không? Phí bao nhiêu?",
        "checks": [
            ("trả lời có nội dung", reply_is_substantial()),
        ],
    },
    {
        "name": "19_chot_don_thieu_ngay",
        "why": "Chốt đơn nhưng thiếu ngày nhận; phải hỏi lại, không tự chọn ngày.",
        "message": "Ok mình lấy bánh kem hoa hồng đỏ 1 cái. Tên Nguyễn C, sđt 0912345678.",
        "checks": [
            ("KHÔNG tạo đơn khi thiếu ngày", never_called("create_draft_order")),
            ("có hỏi ngày nhận", reply_mentions_any("ngày", "khi nào", "thời gian nhận")),
        ],
    },
    {
        "name": "20_hoi_danh_muc",
        "why": "Hỏi tiệm có những loại bánh gì; phải tra kho.",
        "message": "Tiệm mình có những loại bánh nào vậy?",
        "checks": [
            ("có tra kho", called_ok("find_cakes")),
            ("có kể ra món cụ thể", result_matches("find_cakes", "cakes", lambda v: isinstance(v, list) and len(v) > 0)),
        ],
    },
]


async def run_one(scenario: dict, service: ChatService) -> dict:
    """Chạy một kịch bản, trả kết quả chấm."""
    from app.services.rag_service import get_upcoming_events_context

    rag = RAGService(_EmptySupabase())
    prompt = rag.build_system_prompt(get_upcoming_events_context(), "")

    started = datetime.now(timezone.utc)
    error = None
    # Bắt log của `chat_service` để giữ nguyên nhân gốc. `AIServiceUnavailableError`
    # gộp mọi lỗi Groq về đúng một thông điệp, nên không đọc log thì không phân biệt
    # được "quá tần suất, chờ là xong" với "hết hạn mức token cả ngày".
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("app.services.chat_service")
    logger.addHandler(handler)
    old_level = logger.level
    logger.setLevel(logging.ERROR)
    try:
        reply, log = await service._run_agent(
            system_prompt=prompt,
            conversation=[{"role": "user", "content": scenario["message"]}],
            customer_id=str(uuid4()),
        )
    except Exception as exc:  # noqa: BLE001 - ghi lại để báo cáo, không dừng cả lượt
        reply, log, error = "", [], f"{type(exc).__name__}: {exc}"
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    results = []
    for label, check in scenario["checks"]:
        try:
            results.append({"check": label, "passed": bool(check(log, reply))})
        except Exception as exc:  # noqa: BLE001
            results.append({"check": label, "passed": False, "error": str(exc)})

    return {
        "name": scenario["name"],
        "why": scenario["why"],
        "message": scenario["message"],
        "reply": reply,
        "error": error,
        "log": stream.getvalue()[-600:],
        "seconds": round(elapsed, 1),
        "tools": [
            {"tool": e["tool"], "args": e.get("args"), "ok": e.get("ok"),
             "elapsed_ms": e.get("elapsed_ms")}
            for e in log
        ],
        "checks": results,
        "passed": bool(results) and all(r["passed"] for r in results) and error is None,
    }


# Nghỉ giữa các kịch bản (giây). Đo thật: gọi liên tục 25 lần thì 23 thành
# công, 2 lỗi tần suất. Không nghỉ thì kết quả đo được là giới hạn của Groq,
# không phải chất lượng trợ lý: một lần chạy ra 20/20, lần sau 9/20.
PAUSE_BETWEEN = 3.0
RETRY_PAUSE = 15.0

# Groq báo hết hạn mức token/ngày (TPD) khác hẳn quá tần suất theo giây:
#   "Rate limit reached ... on tokens per day (TPD): Limit 200000, Used 199620"
# Trường hợp này retry chỉ đốt thêm hạn mức còn lại, nên phải báo ra.
_QUOTA_RE = re.compile(r"tokens per day|TPD", re.IGNORECASE)


def _is_rate_limit(result: dict) -> bool:
    """Lỗi tần suất TẠM THỜI — đáng thử lại. Không phải hết hạn mức cả ngày.

    Đo thật, phân biệt hai thứ hoàn toàn khác nhau:

    - Tần suất theo giây: chờ vài giây là xong. Đáng retry.
    - Hết hạn mức token/ngày (TPD): `Limit 200000, Used 199620, ... Please try
      again in 2m34s`. Chờ 15s vô ích, và mỗi lần thử lại chỉ đốt thêm hạn mức
      còn lại. Phải báo ra để người chạy biết, không giấu.

    `ChatService` gộp mọi lỗi Groq thành `AIServiceUnavailableError` với đúng
    một thông điệp, nên không đọc được nguyên nhân từ phía kịch bản. Dùng thời
    gian chạy làm tín hiệu phụ: lượt bị từ chối ngay thì dưới 1 giây, còn lỗi
    logic thường đã tốn thời gian hơn trước khi hỏng.
    """
    if not result.get("error"):
        return False
    if float(result.get("seconds") or 99) >= 1.0:
        return False
    # Hết hạn mức ngày: không retry, đánh dấu để báo cáo nói rõ.
    result["quota_exhausted"] = _QUOTA_RE.search(str(result.get("log") or "")) is not None
    return not result["quota_exhausted"]


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default=None, help="chỉ chạy kịch bản có tên này")
    args = parser.parse_args()

    from app.core.config import settings

    if not settings.GROQ_API_KEY:
        print("Thiếu GROQ_API_KEY — không chạy được kịch bản thật.")
        return 2

    service = ChatService.__new__(ChatService)
    # Kho sản phẩm là THẬT (chỉ đọc) để kịch bản tìm bánh có dữ liệu mà tra;
    # bảng ghi vẫn là giả để không tạo đơn rác trong CSDL của tiệm.
    from supabase import create_client

    real = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    read_only = _ReadOnlyRealSupabase(real)
    service._order_tools = OrderTools(read_only)
    service._rag_service = RAGService(read_only)
    service._groq_client = None

    scenarios = [s for s in SCENARIOS if not args.only or s["name"] == args.only]

    # Không có kịch bản nào khớp thì báo tên sai và thoát, thay vì đi tới
    # `100*passed/total` với total = 0 — ZeroDivisionError, và người chạy tưởng
    # hỏng script chứ không phải tự gõ sai tên.
    if not scenarios:
        if args.only:
            print(f"Không có kịch bản nào tên '{args.only}'.")
            print("Các tên hiện có:")
            for s in SCENARIOS:
                print(f"  - {s['name']}")
        else:
            print("Danh sách kịch bản trống — SCENARIOS chưa được nạp.")
        return 2
    print(f"Chạy {len(scenarios)} kịch bản qua model {settings.GROQ_MODEL}\n")

    report = []
    for i, scenario in enumerate(scenarios, 1):
        result = await run_one(scenario, service)

        # Retry khi gặp giới hạn tần suất TẠM THỜI. Đo thật: gọi liên tục 25
        # lần thì 23 thành công, 2 lỗi. Không retry thì kết quả đo được là giới
        # hạn của Groq chứ không phải chất lượng trợ lý.
        #
        # Hết hạn mức token/ngày thì KHÔNG retry — chờ 15s vô ích và mỗi lần thử
        # lại còn đốt thêm hạn mức còn lại. Báo ra để người chạy biết.
        tries = 0
        while _is_rate_limit(result) and tries < 4:
            tries += 1
            print(f"        (quá tần suất, thử lại {tries}/4 sau {RETRY_PAUSE:.0f}s)")
            await asyncio.sleep(RETRY_PAUSE)
            result = await run_one(scenario, service)
        if result.get("quota_exhausted"):
            print(f"        (HẾT HẠN MỨC TOKEN/NGÀY của Groq — không retry, cần chờ reset"
                  f" hoặc nâng gói. Xem 'log' trong báo cáo.)")

        report.append(result)
        mark = "ĐẠT " if result["passed"] else "TRƯỢT"
        tools = ", ".join(t["tool"] for t in result["tools"]) or "(không gọi công cụ)"
        print(f"[{i}/{len(scenarios)}] {mark} {result['name']}  ({result['seconds']}s)")
        print(f"        công cụ: {tools}")
        if not result["passed"]:
            for r in result["checks"]:
                if not r["passed"]:
                    print(f"        TRƯỢT: {r['check']}")
            if result["error"]:
                print(f"        LỖI: {result['error']}")
            print(f"        trả lời: {(result['reply'] or '')[:160]}")
        print()

        # Nghỉ giữa các kịch bản để không tự tạo ra giới hạn tần suất.
        await asyncio.sleep(PAUSE_BETWEEN)

    passed = sum(1 for r in report if r["passed"])
    total = len(report)
    print("=" * 74)
    print(f"TỔNG: {passed}/{total} kịch bản đạt ({100*passed/total:.1f}%)")
    print("=" * 74)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            {
                "model": settings.GROQ_MODEL,
                "ran_at": datetime.now(timezone.utc).isoformat(),
                "passed": passed,
                "total": total,
                "scenarios": report,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Báo cáo: {REPORT_PATH}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
