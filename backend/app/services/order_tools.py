"""Công cụ cho trợ lý đặt bánh (ordering agent).

Trợ lý AI KHÔNG tự bịa giá hay tự bịa sản phẩm. Mọi con số đều lấy từ đây, đọc
trực tiếp từ CSDL. LLM chỉ quyết định GỌI công cụ nào và nói gì với khách.

Vì sao làm vậy thay vì để LLM tự trả lời:
    Cách cũ nhồi cả danh mục vào prompt rồi bắt LLM viết JSON trong câu trả lời,
    sau đó dùng regex bóc lại. Cách đó sai ở chỗ LLM có thể bịa tên bánh, bịa
    giá, hoặc viết JSON sai định dạng. Ở đây giá và tồn kho do code quyết định,
    nên không thể bịa.

Năm công cụ:
    find_cakes        — tìm bánh theo ngân sách / dịp / từ khoá
    get_cake_detail   — xem chi tiết một mẫu bánh
    price_order       — tính tiền, kiểm tra ngân sách
    check_bake_time   — kiểm tra ngày nhận có kịp làm không
    create_draft_order— tạo đơn nháp (KHÁCH PHẢI XÁC NHẬN)
"""

from __future__ import annotations

import inspect
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.services.pricing import (
    DEFAULT_LEAD_HOURS,
    custom_design_lead_hours,
    lead_hours_for_items,
)

logger = logging.getLogger(__name__)

# Múi giờ Việt Nam (UTC+7) — mọi mốc thời gian của tiệm đều tính theo giờ này.
VN_TZ = timezone(timedelta(hours=7))

# Tiệm cần đặt trước bao lâu. Bánh đơn giản 24h, bánh nhiều tầng/figure lâu hơn
# vì phải đặt nguyên liệu và trang trí thủ công.
#
# Số giờ nằm trong `pricing` để agent và checkout dùng chung một quy tắc.
# Ở đây chỉ giữ tên để các test và nơi gọi cũ vẫn import được.
MIN_LEAD_HOURS = DEFAULT_LEAD_HOURS
MIN_LEAD_HOURS_COMPLEX = 48

# Ngưỡng "đặt mẫu riêng" KHÔNG có hằng số riêng: nó CHÍNH LÀ
# `lead_hours_for_items(items)` — cùng số với `required_lead_hours`.
#
# Quy tắc của tiệm: bánh đơn giản cần 24 giờ, bánh phức tạp (hai tầng, hình
# dáng) cần 48 giờ. Dưới mốc đó chỉ bán được bánh sẵn có trong danh mục.
#
# Trước đây tách hai mốc (24 cho đặt mẫu, 48 cho làm bánh) là SAI. Lý do đã
# đo: một bánh hai tầng đặt trước 30 giờ sẽ bị chấp nhận đặt mẫu trong khi
# 48 giờ mới kịp làm — nhận đơn rồi không làm kịp. Một mốc duy nhất theo độ
# phức tạp loại bỏ hẳn lớp lỗi đó, và agent lẽ ra phải nói với khách đúng
# như checkout nói.


COMPLEX_KEYWORDS = ("2 tầng", "3 tầng", "figure", "tạo hình", "cưới")

MAX_RESULTS = 10

# Cửa sổ chống tạo trùng đơn nháp. LLM có thể gọi lại `create_draft_order` khi
# request trước bị timeout hoặc khi vòng lặp công cụ lặp lại; trong khoảng thời
# gian ngắn này, một đơn nháp y hệt (cùng khách, cùng ngày nhận, cùng nội dung)
# được coi là CÙNG một đơn và trả lại thay vì tạo thêm.
DRAFT_RETRY_WINDOW_MINUTES = 10


class ToolError(Exception):
    """Công cụ báo lỗi theo cách LLM hiểu được, không làm sập request."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _vn_now() -> datetime:
    return datetime.now(VN_TZ)


# `_is_complex` và `_lead_hours` đã bỏ: chúng đoán độ phức tạp từ *tên* sản
# phẩm, trong khi checkout đo theo *kích cỡ*, nên hai nơi cho hai đáp án lệch
# nhau 24 giờ cho cùng một đơn. Dùng `lead_hours_for_items`.


# Từ quá chung chung: gần như bánh nào cũng có trong tên, nên nếu tính là "khớp"
# thì tìm kiếm theo từ khoá trả về cả kho và thành vô dụng.
_STOPWORDS = {
    "bánh", "banh", "kem", "cái", "cai", "chiếc", "chiec", "loại", "loai",
    "mẫu", "mau", "của", "cua", "cho", "và", "va", "có", "co", "một", "mot",
    "sinh", "nhật", "nhat", "chúc", "chuc", "mừng", "mung",
}


def _words(text: str) -> list[str]:
    """Tách từ, bỏ ký tự trang trí để so khớp tên bánh.

    Tên bánh trong kho có ngoặc kép cong (”) và nhiều dấu câu; nếu không bỏ thì
    từ khoá lấy từ tên bánh sẽ không khớp lại được với chính tên đó.
    """
    cleaned = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in str(text).lower())
    return [w for w in cleaned.split() if len(w) > 1]


def _nullable(schema: dict) -> dict:
    """Cho một tham số tuỳ chọn nhận thêm `null`.

    Model hay gửi `null` cho tham số không dùng thay vì bỏ hẳn khoá. Groq kiểm
    tra tool call theo schema và TỪ CHỐI THẲNG nếu không khớp — đo được thật:

        "parameters for tool find_cakes did not match schema:
         `/budget`: expected integer, but got null"  (HTTP 400)

    Lỗi này ném ra từ tầng gọi API, `_run_agent` bắt mọi lỗi rồi ném
    `AIServiceUnavailableError`, nên CẢ LƯỢT CHAT SẬP: khách hỏi "tiệm có bánh
    gì" và nhận câu xin lỗi thay vì danh mục. Cho nhận `null` là đúng vì các hàm
    đã coi `None` như "khách không nêu".
    """
    t = schema.get("type")
    if isinstance(t, str):
        return {**schema, "type": [t, "null"]}
    return schema

class OrderTools:
    """Bộ công cụ thao tác trên CSDL cho trợ lý đặt bánh."""

    def __init__(self, supabase_client: Any):
        self._supabase = supabase_client

    # ────────────────────────────────────────────────────────────────────────
    # Tra cứu sản phẩm
    # ────────────────────────────────────────────────────────────────────────

    def _active_cakes(self) -> list[dict]:
        """Lấy mọi sản phẩm đang bán.

        Trước đây chỉ giữ `product_type == "cake"`, bỏ hết `sweet`. Kho có 18
        món `sweet` đang bán bình thường — tiramisu, cheesecake, brownie, su
        kem — nên khách hỏi tiramisu thì trợ lý trả lời "tiệm chưa có", tức là
        nói sai về chính cửa hàng mình. Cửa hàng (`catalog_service`) không lọc
        theo `product_type`, nên trợ lý phải thấy đúng tập đó.

        Sắp xếp bánh kem lên trước để khi khách hỏi chung chung, gợi ý vẫn
        nghiêng về mặt hàng chủ đạo — nhưng không ẩn món nào.
        """
        result = (
            self._supabase.table("products")
            .select("id, name, description, category, base_price, sizes, flavors, product_type")
            .eq("is_active", True)
            .execute()
        )
        rows = result.data or []
        return sorted(rows, key=lambda r: 0 if r.get("product_type") == "cake" else 1)

    def find_cakes(
        self,
        budget: Optional[int] = None,
        occasion: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 5,
    ) -> dict:
        """Tìm bánh phù hợp. Giá lấy từ CSDL, không do LLM bịa."""
        limit = max(1, min(int(limit or 5), MAX_RESULTS))
        products = self._active_cakes()

        matched = products

        if budget is not None:
            try:
                budget = int(budget)
            except (TypeError, ValueError):
                raise ToolError("Ngân sách phải là một con số (đơn vị VNĐ).")
            if budget <= 0:
                raise ToolError("Ngân sách phải lớn hơn 0.")
            matched = [p for p in matched if (p.get("base_price") or 0) <= budget]

        if keyword:
            # Bo cac tu chung chung ai cung co ("banh", "kem") — neu khong thi tu
            # khoa kieu "Bánh kem chữ Chúc Mừng" khop gan nhu ca kho, tra ve 91
            # ket qua vo nghia. Do thuc te: truoc khi loc, 91/105 banh deu "khop".
            words = [w for w in _words(keyword) if w not in _STOPWORDS]
            if words:
                scored = []
                for p in matched:
                    hay = f"{p.get('name','')} {p.get('description','')} {p.get('category','')}".lower()
                    hits = sum(1 for w in words if w in hay)
                    if hits:
                        scored.append((hits, p))
                scored.sort(key=lambda x: (-x[0], x[1].get("base_price") or 0))
                matched = [p for _h, p in scored]

        if occasion:
            # Dịp chỉ dùng để xếp hạng, không loại bỏ — kho chưa gắn nhãn dịp.
            occ = str(occasion).lower()
            matched = sorted(
                matched,
                key=lambda p: (0 if occ in f"{p.get('name','')} {p.get('description','')}".lower() else 1,
                               p.get("base_price") or 0),
            )

        if not matched:
            # Không có gì trong ngân sách: gợi ý mẫu rẻ nhất để khách biết mức giá.
            cheapest = sorted(products, key=lambda p: p.get("base_price") or 0)[:limit]
            return {
                "found": 0,
                "message": (
                    f"Không có bánh nào trong ngân sách {budget:,}đ."
                    if budget else "Không tìm thấy bánh phù hợp."
                ),
                "suggestions": [
                    {"name": p["name"], "price": p.get("base_price") or 0}
                    for p in cheapest
                ],
            }

        # Xếp hạng theo ĐỘ GẦN ngân sách, không phải rẻ nhất trước.
        #
        # Khách nói "ngân sách khoảng 450 nghìn" nghĩa là muốn chi CỠ 450k, chứ
        # không phải "càng rẻ càng tốt". Nếu chỉ lấy giá tăng dần thì mẫu 170k
        # luôn đứng đầu và trợ lý cứ gợi ý bánh rẻ nhất — đo thật đúng như vậy.
        # Chỉ áp dụng khi không có từ khoá/dịp, vì lúc đó độ liên quan mới là
        # tiêu chí chính.
        if budget is not None and not keyword and not occasion:
            matched = sorted(
                matched,
                key=lambda p: (
                    abs((p.get("base_price") or 0) - budget),
                    p.get("base_price") or 0,
                ),
            )

        return {
            "found": len(matched),
            "budget": budget,
            "cakes": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "price": p.get("base_price") or 0,
                    "category": p.get("category"),
                    "description": (p.get("description") or "")[:160],
                    "sizes": p.get("sizes") or [],
                    "flavors": p.get("flavors") or [],
                    # Chưa có kích cỡ khách chọn nên báo mức nhỏ nhất; đơn
                    # thật dùng `lead_hours_for_items` theo size khách chọn.
                    "needs_lead_hours": DEFAULT_LEAD_HOURS,
                }
                for p in matched[:limit]
            ],
        }

    def get_cake_detail(self, cake_id: Optional[str] = None, name: Optional[str] = None) -> dict:
        """Xem chi tiết một mẫu bánh, theo id hoặc theo tên."""
        if not cake_id and not name:
            raise ToolError("Cần cung cấp 'cake_id' hoặc 'name'.")

        products = self._active_cakes()
        found = None
        if cake_id:
            found = next((p for p in products if p["id"] == cake_id), None)
        if not found and name:
            target = str(name).strip().lower()
            found = next((p for p in products if p["name"].strip().lower() == target), None)
            if not found:
                found = next((p for p in products if target in p["name"].strip().lower()), None)
        if not found:
            raise ToolError(f"Không tìm thấy bánh nào khớp với '{name or cake_id}'.")

        return {
            "id": found["id"],
            "name": found["name"],
            "price": found.get("base_price") or 0,
            "category": found.get("category"),
            "description": found.get("description") or "",
            "sizes": found.get("sizes") or [],
            "flavors": found.get("flavors") or [],
            # Mức nhỏ nhất; đơn thật tính theo size khách chọn.
            "needs_lead_hours": DEFAULT_LEAD_HOURS,
        }

    # ────────────────────────────────────────────────────────────────────────
    # Tính tiền
    # ────────────────────────────────────────────────────────────────────────

    def price_order(self, items: list[dict], budget: Optional[int] = None) -> dict:
        """Tính tổng tiền. Đơn giá LUÔN lấy từ CSDL, bỏ qua giá LLM đưa vào."""
        if not items:
            raise ToolError("Đơn hàng phải có ít nhất một món.")

        products = self._active_cakes()
        by_id = {p["id"]: p for p in products}
        by_name = {p["name"].strip().lower(): p for p in products}

        lines, total = [], 0
        for item in items:
            qty = item.get("quantity", 1)
            try:
                qty = int(qty)
            except (TypeError, ValueError):
                raise ToolError("Số lượng phải là số nguyên.")
            if qty < 1:
                raise ToolError("Số lượng phải ít nhất là 1.")

            product = None
            if item.get("cake_id"):
                product = by_id.get(item["cake_id"])
            if product is None and item.get("name"):
                product = by_name.get(str(item["name"]).strip().lower())
            if product is None:
                raise ToolError(
                    f"Không tìm thấy bánh '{item.get('name') or item.get('cake_id')}' trong danh mục."
                )

            # Đơn giá lấy từ CSDL. Nếu LLM gửi giá khác, ghi log để biết mà sửa
            # prompt — nhưng KHÔNG dùng giá đó.
            unit = product.get("base_price") or 0
            claimed = item.get("unit_price")
            if claimed is not None and int(claimed) != unit:
                logger.warning(
                    "LLM claimed price %s for '%s' but catalog says %s; using catalog",
                    claimed, product["name"], unit,
                )

            line_total = unit * qty
            total += line_total
            lines.append({
                "name": product["name"],
                "cake_id": product["id"],
                "quantity": qty,
                "unit_price": unit,
                "line_total": line_total,
            })

        result = {"items": lines, "total_price": total, "currency": "VND"}

        if budget is not None:
            try:
                budget = int(budget)
            except (TypeError, ValueError):
                raise ToolError("Ngân sách phải là một con số (đơn vị VNĐ).")
            result["budget"] = budget
            result["over_budget"] = total > budget
            result["difference"] = total - budget
            if total > budget:
                result["message"] = (
                    f"Tổng {total:,}đ vượt ngân sách {budget:,}đ là {total - budget:,}đ. "
                    "Nên gợi ý khách giảm số lượng hoặc chọn mẫu rẻ hơn."
                )
            else:
                result["message"] = (
                    f"Tổng {total:,}đ nằm trong ngân sách {budget:,}đ "
                    f"(còn dư {budget - total:,}đ)."
                )
        return result

    # ────────────────────────────────────────────────────────────────────────
    # Thời gian
    # ────────────────────────────────────────────────────────────────────────

    def check_bake_time(self, pickup_date: str, items: Optional[list[dict]] = None) -> dict:
        """Kiểm tra ngày nhận có kịp làm không."""
        if not pickup_date:
            raise ToolError("Cần cung cấp 'pickup_date' (YYYY-MM-DD hoặc ISO 8601).")

        raw = str(pickup_date).strip()
        parsed = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
            try:
                parsed = datetime.strptime(raw[:19], fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            raise ToolError(
                f"Không hiểu ngày '{pickup_date}'. Dùng định dạng YYYY-MM-DD, ví dụ 2026-10-15."
            )
        parsed = parsed.replace(tzinfo=VN_TZ)

        # Hai mốc khác nhau, không được gộp:
        #
        # `lead` — mốc chờ của đơn ĐANG CÓ. Mẫu làm sẵn thì 0 giờ (bán ngay),
        # mẫu đặt thì 24 hay 48 giờ theo kích cước.
        # `design_lead` — mốc mà khách phải đạt để tiệm nhận LÀM mẫu mới.
        #
        # Trước đây cả hai mốc này là một: cả mẫu làm sẵn của bánh
        # hai tầng đẳng bị bắt phải đặt trước 48 giờ — sai, vì nó đã có sẵn.
        lead = lead_hours_for_items(items)
        design_lead = custom_design_lead_hours(items)

        # Ngày chỉ có ngày-tháng (YYYY-MM-DD) được hiểu là 00:00 hôm đó. Nếu khách
        # nói "hôm nay" thì 00:00 đã trôi qua, cho ra số giờ ÂM trông vô lý. Coi
        # mốc là CUỐI NGÀY để phản ánh đúng "còn kịp trong hôm nay không".
        now = _vn_now()
        date_only = len(raw) <= 10
        deadline = parsed + timedelta(hours=23, minutes=59) if date_only else parsed
        hours_notice = (deadline - now).total_seconds() / 3600

        return {
            # Vẫn trả về đúng ngày khách nói, không kèm giờ giả.
            "pickup_date": parsed.strftime("%Y-%m-%d"),
            # Mốc thời gian đã dùng để kết luận. `create_draft_order` phải lưu
            # đúng mốc này: trước đây nó parse lại chuỗi ngày thành 00:00, mất 24
            # giờ, nên agent nói "kịp" nhưng đơn lại lưu thành không kịp.
            "deadline": deadline.isoformat(),
            "hours_notice": round(hours_notice, 1),
            "required_lead_hours": lead,
            "is_possible": hours_notice >= lead,
            # Có được phép đặt mẫu riêng / tự thiết kế không.
            #
            # Quy tắc của tiệm: bánh ĐƠN GIẢN cần 24 giờ, bánh PHỨC TẠP (hai
            # tầng, hình dáng, trang trí thủ công nhiều) cần 48 giờ. Còn ít hơn
            # mốc đó thì chỉ bán được bánh sẵn có trong danh mục, vì làm mẫu mới
            # không kịp.
            #
            # Ngưỡng đặt mẫu là `design_lead`, KHÔNG phải `lead`.
            # `lead` là mốc của đơn đang có (0 giờ nếu toàn mẫu làm sẵn).
            # Trước đây tách ra hai mốc (24 cho đặt mẫu, 48 cho làm bánh) là sai:
            # bánh hai tầng phải cần 48 giờ ở CẢ HAI chỗ, nếu không sẽ nhận đơn
            # hai tầng mà không kịp làm.
            "custom_design_allowed": hours_notice >= design_lead,
            "message": (
                f"Kịp. Còn {hours_notice:.0f} giờ, cần tối thiểu {lead} giờ."
                if hours_notice >= lead
                else (
                    f"KHÔNG kịp. Chỉ còn {max(hours_notice, 0):.0f} giờ nhưng cần tối thiểu {lead} giờ. "
                    "Hãy đề nghị khách chọn ngày muộn hơn."
                )
            ),
        }

    # ────────────────────────────────────────────────────────────────────────
    # Tạo đơn nháp
    # ────────────────────────────────────────────────────────────────────────

    def create_draft_order(
        self,
        customer_name: str,
        customer_phone: str,
        pickup_date: str,
        items: list[dict],
        customer_email: Optional[str] = None,
        customer_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """Tạo đơn NHÁP (status='draft'), chưa phải đơn chính thức.

        Chỉ gọi sau khi khách đã xác nhận rõ ràng: mẫu bánh, số lượng, ngày nhận.

        LƯU Ý: bảng `orders` có `customer_id` NOT NULL (đã kiểm chứng bằng cách
        thử chèn — PostgREST không báo ràng buộc này trong schema). Nghĩa là mọi
        đơn đều phải thuộc một tài khoản. Khách chưa đăng nhập thì KHÔNG tạo được
        đơn, và trợ lý phải nói rõ để khách đăng nhập, chứ không được tạo đơn rác.
        """
        if not customer_id:
            return {
                "created": False,
                "reason": "not_logged_in",
                "message": (
                    "Chưa xác định được tài khoản khách nên chưa tạo được đơn. "
                    "Hãy đề nghị khách ĐĂNG NHẬP rồi đặt lại, hoặc gọi hotline của tiệm. "
                    "Đừng nói với khách là đơn đã được tạo."
                ),
            }

        if not customer_name or not str(customer_name).strip():
            raise ToolError("Cần tên khách để tạo đơn.")
        phone = str(customer_phone or "").strip()
        if len(phone) < 9:
            raise ToolError("Số điện thoại chưa hợp lệ (cần ít nhất 9 chữ số).")

        timed = self.check_bake_time(pickup_date, items)
        if not timed["is_possible"]:
            return {
                "created": False,
                "reason": "pickup_too_soon",
                "message": timed["message"],
                "earliest_possible": (
                    _vn_now() + timedelta(hours=timed["required_lead_hours"])
                ).strftime("%Y-%m-%d"),
            }

        priced = self.price_order(items)
        # Dùng đúng mốc `check_bake_time` đã kiểm tra, không parse lại chuỗi
        # ngày. Parse lại sẽ ra 00:00 và đơn lưu mất đúng 24 giờ so với mức
        # vừa kết luận là kịp.
        parsed = datetime.fromisoformat(timed["deadline"])

        # Tóm tắt cho thợ làm bánh đọc.
        summary = "; ".join(f"{l['name']} x{l['quantity']}" for l in priced["items"])
        ai_summary = f"{summary} | Nhận: {timed['pickup_date']} | Tổng: {priced['total_price']:,}đ"
        if notes:
            ai_summary += f" | Ghi chú: {notes}"

        order_insert: dict[str, Any] = {
            "customer_id": customer_id,
            "status": "draft",
            "total_price": priced["total_price"],
            "pickup_date": parsed.isoformat(),
            "customer_name": str(customer_name).strip(),
            "customer_phone": phone,
            "customer_email": customer_email,
            "ai_summary": ai_summary,
        }

        # ── Chống tạo trùng (idempotent) ──────────────────────────────────────
        # LLM có thể gọi lại công cụ này khi request trước timeout, hoặc vòng lặp
        # công cụ lặp lại. Nếu đã có đơn nháp VỪA tạo cho đúng khách, đúng ngày
        # nhận và đúng nội dung thì trả lại đơn đó, KHÔNG tạo thêm đơn rác.
        retry_since = datetime.now(timezone.utc) - timedelta(
            minutes=DRAFT_RETRY_WINDOW_MINUTES
        )
        try:
            existing = (
                self._supabase.table("orders")
                .select("id, status")
                .eq("customer_id", customer_id)
                .eq("status", "draft")
                .eq("pickup_date", parsed.isoformat())
                .eq("ai_summary", ai_summary)
                .gte("created_at", retry_since.isoformat())
                .limit(1)
                .execute()
            )
        except Exception:
            # Tra không được thì vẫn cho tạo đơn: thà có rủi ro trùng còn hơn
            # chặn khách đặt bánh chỉ vì một truy vấn phụ bị lỗi.
            logger.exception("Không tra được đơn nháp trùng (khách %s)", customer_id)
            existing = None

        if existing is not None and existing.data:
            same = existing.data[0]
            return {
                "created": True,
                "duplicate": True,
                "order_id": same["id"],
                "status": same.get("status") or "draft",
                "total_price": priced["total_price"],
                "pickup_date": timed["pickup_date"],
                "items": priced["items"],
                "message": (
                    f"Đơn nháp {same['id'][:8]} cho {order_insert['customer_name']} "
                    "đã có sẵn nên KHÔNG tạo thêm đơn trùng, "
                    f"nhận ngày {timed['pickup_date']}, tổng {priced['total_price']:,}đ. "
                    "Tiệm sẽ gọi xác nhận."
                ),
            }

        result = self._supabase.table("orders").insert(order_insert).execute()
        if not result.data:
            raise ToolError("Không tạo được đơn. Vui lòng thử lại.")

        order = result.data[0]

        # Một câu INSERT duy nhất cho TẤT CẢ món: PostgREST thực thi nó như một
        # câu lệnh, nên hoặc lưu đủ món, hoặc không món nào — không có đơn thiếu món.
        try:
            self._supabase.table("order_items").insert([
                {
                    "order_id": order["id"],
                    "product_id": line["cake_id"],
                    "quantity": line["quantity"],
                    "unit_price": line["unit_price"],
                }
                for line in priced["items"]
            ]).execute()
        except Exception as exc:
            # Lưu món thất bại thì phải xoá đơn vừa tạo, không để lại đơn rác
            # thiếu món mà nhân viên tưởng là đơn thật. Xoá món trước rồi mới xoá
            # đơn để không phụ thuộc vào việc khoá ngoại có ON DELETE CASCADE hay không.
            logger.exception("Lưu món thất bại, xoá đơn nháp %s", order["id"])
            for table, column in (("order_items", "order_id"), ("orders", "id")):
                try:
                    self._supabase.table(table).delete().eq(column, order["id"]).execute()
                except Exception:
                    logger.exception("Không xoá được %s của đơn %s", table, order["id"])
            raise ToolError(
                "Không tạo được đơn vì lỗi khi lưu món. Vui lòng thử lại."
            ) from exc

        return {
            "created": True,
            "order_id": order["id"],
            "status": order["status"],
            "total_price": priced["total_price"],
            "pickup_date": timed["pickup_date"],
            "items": priced["items"],
            "message": (
                f"Đã tạo đơn nháp {order['id'][:8]} cho {order_insert['customer_name']}, "
                f"nhận ngày {timed['pickup_date']}, tổng {priced['total_price']:,}đ. "
                "Tiệm sẽ gọi xác nhận."
            ),
        }


# ────────────────────────────────────────────────────────────────────────────
# Khai báo công cụ cho Groq (function calling)
# ────────────────────────────────────────────────────────────────────────────

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "find_cakes",
            "description": (
                "Tìm bánh trong danh mục theo ngân sách, dịp hoặc từ khoá. "
                "LUÔN dùng công cụ này trước khi nói tên bánh hay giá với khách — "
                "không được tự nghĩ ra sản phẩm hoặc giá. "
                "Cũng dùng khi khách hỏi tiệm có những loại bánh gì, xem menu, "
                "hoặc hỏi chung chung về danh mục — gọi không tham số cũng được, "
                "sẽ trả về danh sách bánh."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "budget": _nullable({"type": "integer", "description": "Ngân sách tối đa, đơn vị VNĐ. Ví dụ 400000."}),
                    "occasion": _nullable({"type": "string", "description": "Dịp: sinh nhật, kỷ niệm, cưới, thôi nôi..."}),
                    "keyword": _nullable({"type": "string", "description": "Từ khoá mô tả bánh khách muốn, ví dụ 'hoa hồng', '2 tầng'."}),
                    "limit": _nullable({"type": "integer", "description": "Số kết quả tối đa (1-10). Mặc định 5."}),
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cake_detail",
            "description": "Xem chi tiết một mẫu bánh: giá, kích cỡ, hương vị, mô tả.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cake_id": _nullable({"type": "string", "description": "ID bánh lấy từ find_cakes."}),
                    "name": _nullable({"type": "string", "description": "Tên bánh, dùng khi chưa có ID."}),
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "price_order",
            "description": (
                "Tính tổng tiền của đơn và kiểm tra có vượt ngân sách không. "
                "Đơn giá luôn lấy từ danh mục, không lấy giá do bạn đưa vào."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "Danh sách món trong đơn.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "cake_id": {"type": "string"},
                                "name": {"type": "string"},
                                "quantity": {"type": "integer"},
                            },
                            "required": ["quantity"],
                        },
                    },
                    "budget": _nullable({"type": "integer", "description": "Ngân sách khách đưa, nếu có."}),
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_bake_time",
            "description": (
                "Kiểm tra ngày nhận bánh có kịp làm không. Phải gọi trước khi hứa "
                "ngày với khách. Bánh nhiều tầng cần đặt trước lâu hơn. "
                "Gọi công cụ này NGAY khi khách nhắc tới một ngày nhận cụ thể, kể cả "
                "khi khách chỉ hỏi 'ngày đó kịp không' — KHÔNG trả lời số giờ đặt "
                "trước từ trí nhớ, và KHÔNG tự nói một ngày nào đó là sớm nhất. "
                "Kết quả có `custom_design_allowed`: false nghĩa là chỉ được bán "
                "bánh sẵn trong danh mục, không nhận đặt mẫu riêng."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pickup_date": {"type": "string", "description": "Ngày khách muốn nhận, định dạng YYYY-MM-DD."},
                    "items": _nullable({
                        "type": "array",
                        "description": (
                            "Các món trong đơn. PHẢI kèm `size` là kích cỡ khách "
                            "chọn (16cm, 20cm, 24cm, 2-tier) vì thời gian chuẩn bị "
                            "tính theo kích cỡ, KHÔNG theo tên bánh. Khách chưa nói "
                            "kích cỡ thì hỏi, hoặc bỏ trống để lấy mức mặc định."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "size": {
                                    "type": "string",
                                    "description": "Kích cỡ khách chọn: 16cm, 20cm, 24cm hoặc 2-tier.",
                                },
                            },
                        },
                    }),
                },
                "required": ["pickup_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_draft_order",
            "description": (
                "Tạo đơn nháp. CHỈ gọi sau khi khách đã xác nhận rõ ràng mẫu bánh, "
                "số lượng và ngày nhận. Không được tự ý tạo đơn khi khách chưa đồng ý."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Tên khách."},
                    "customer_phone": {"type": "string", "description": "Số điện thoại khách."},
                    "pickup_date": {"type": "string", "description": "Ngày nhận, YYYY-MM-DD."},
                    "items": {
                        "type": "array",
                        "description": (
                            "Các món trong đơn. Nên kèm `size` là kích cỡ khách chọn "
                            "(16cm, 20cm, 24cm, 2-tier) để kiểm tra thời gian làm đúng."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "cake_id": {"type": "string"},
                                "name": {"type": "string"},
                                "size": {
                                    "type": "string",
                                    "description": "Kích cỡ khách chọn: 16cm, 20cm, 24cm hoặc 2-tier.",
                                },
                                "quantity": {"type": "integer"},
                            },
                            "required": ["quantity"],
                        },
                    },
                    "customer_email": _nullable({"type": "string"}),
                    "notes": _nullable({"type": "string", "description": "Ghi chú: chữ trên bánh, dị ứng, giờ nhận."}),
                },
                "required": ["customer_name", "customer_phone", "pickup_date", "items"],
            },
        },
    },
]

# Tên công cụ -> phương thức. Dùng để tra khi LLM yêu cầu gọi.
TOOL_NAMES = {t["function"]["name"] for t in TOOL_SCHEMAS}


def _normalize_arguments(name: str, arguments: dict) -> dict:
    """Chấp nhận vài cách gọi tên tham số khác nhau của LLM.

    Đã gặp thật: model gọi `create_draft_order` với `phone` thay vì
    `customer_phone`. Nếu để nguyên thì hàm ném TypeError, LLM thử lại và có thể
    đốt hết số vòng cho phép mà vẫn không tạo được đơn. Ở đây quy về tên đúng.

    Chỉ ánh xạ những tên ĐỒNG NGHĨA RÕ RÀNG; tên lạ vẫn để nguyên cho TypeError
    bắt, vì đoán bừa còn nguy hiểm hơn là báo lỗi.
    """
    aliases = {
        "create_draft_order": {
            "phone": "customer_phone",
            "sdt": "customer_phone",
            "so_dien_thoai": "customer_phone",
            "name": "customer_name",
            "ten": "customer_name",
            "email": "customer_email",
            "date": "pickup_date",
            "ngay_nhan": "pickup_date",
            "cakes": "items",
            "products": "items",
        },
        "check_bake_time": {"date": "pickup_date", "ngay_nhan": "pickup_date"},
        "price_order": {"cakes": "items", "products": "items", "ngan_sach": "budget"},
        "find_cakes": {"ngan_sach": "budget", "q": "keyword", "tu_khoa": "keyword"},
        "get_cake_detail": {"id": "cake_id", "ten": "name"},
    }
    mapping = aliases.get(name)
    if not mapping:
        return arguments
    out = dict(arguments)
    for wrong, right in mapping.items():
        # Chỉ đổi khi tên đúng chưa được truyền — không ghi đè tham số hợp lệ.
        if wrong in out and right not in out:
            out[right] = out.pop(wrong)
    return out


def dispatch(tools: OrderTools, name: str, arguments: dict) -> dict:
    """Gọi công cụ theo tên. Lỗi được trả về dưới dạng dict để LLM đọc và sửa,
    không ném ra ngoài làm hỏng cả lượt chat."""
    handlers = {
        "find_cakes": tools.find_cakes,
        "get_cake_detail": tools.get_cake_detail,
        "price_order": tools.price_order,
        "check_bake_time": tools.check_bake_time,
        "create_draft_order": tools.create_draft_order,
    }
    handler = handlers.get(name)
    if handler is None:
        return {"error": f"Không có công cụ tên '{name}'."}
    args = _normalize_arguments(name, arguments or {})
    try:
        return handler(**args)
    except ToolError as exc:
        return {"error": exc.message}
    except TypeError as exc:
        # LLM truyền thiếu/thừa tham số — báo lại ĐÚNG tên tham số cần dùng, để
        # nó sửa được ngay ở vòng sau thay vì đoán mò.
        expected = inspect.signature(handler)
        allowed = [
            p.name for p in expected.parameters.values()
            if p.name not in ("self",) and p.kind is not p.VAR_KEYWORD
        ]
        return {
            "error": f"Sai tham số cho '{name}': {exc}",
            "expected_parameters": allowed,
            "hint": f"Hãy gọi lại '{name}' chỉ với các tham số: {', '.join(allowed)}",
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Tool %s failed", name)
        return {"error": f"Công cụ '{name}' gặp lỗi: {type(exc).__name__}"}
