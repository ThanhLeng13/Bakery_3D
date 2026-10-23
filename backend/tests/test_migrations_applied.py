"""Các migration bắt buộc đã được chạy thật trên CSDL chưa.

Gói 1 ghi rõ giới hạn: máy chỉ có service-role key, không có đường chạy
`CREATE FUNCTION`, nên ba migration phải chạy tay trên Supabase SQL Editor.
Không có gì trong code hay test nhắc lại điều đó, nên rất dễ tưởng là đã xong.

File này kiểm tra trạng thái thật trên CSDL và **bỏ qua (skip)** khi không có
khoá. Nhờ vậy CI vẫn xanh, còn trên máy người dùng thì lỗi hiện ra ngay thay vì
phải nhớ.

Chạy tay:
    cd backend
    .\\venv\\Scripts\\python.exe -m pytest tests/test_migrations_applied.py -v
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _has_credentials() -> bool:
    """Có dùng được CSDL thật không.

    Thử `create_client` thật thay vì soi chuỗi env. Lý do: khi chạy trong repo
    có `backend/.env`, `load_dotenv()` sẽ nạp khoá dù biến môi trường để trống,
    nên cách kiểm bằng `os.environ` cho ra "không có khoá" một cách sai — tôi
    dính vào đúng lỗi đó khi thử tắt biến để kiểm tra.
    """
    try:
        from dotenv import load_dotenv
        from supabase import create_client

        load_dotenv()
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            return False
        create_client(url, key)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _has_credentials(),
    reason="Không có khoá Supabase trên máy này (CI dùng khoá giả).",
)


class _CannotReachDatabase(RuntimeError):
    """Lỗi mạng hoặc DNS — KHÁC hoàn toàn với migration chưa chạy."""


def _is_unreachable(exc: Exception) -> bool:
    """Exception này do không gọi được CSDL, không phải do schema thiếu.

    Phân biệt này quan trọng: nếu lưới mạng bị báo thành "thiếu migration" thì
    người đọc sẽ chạy SQL không cần thiết, rồi tưởng đã sửa xong trong khi
    migration vẫn chưa chạy. Đã xảy ra một lần: `socket.gaierror
    [Errno -2] Name or service not known` bị in ra dưới nhãn "enum chưa có
    draft", hoàn toàn sai.
    """
    import socket

    if isinstance(exc, (socket.gaierror, TimeoutError, ConnectionError, OSError)):
        return True
    text = str(exc).lower()
    markers = (
        "name or service not known",
        "temporary failure in name resolution",
        "getaddrinfo",
        "connection refused",
        "connection reset",
        "connection aborted",
        "timed out",
        "could not connect",
        "max retries exceeded",
        "network is unreachable",
    )
    return any(m in text for m in markers)


def _require_reachable(fn, *args, **kwargs):
    """Chạy truy vấn, và báo lỗi mạng riêng biệt thay vì lẫn vào lỗi schema."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        if _is_unreachable(exc):
            pytest.fail(
                "Không gọi được CSDL Supabase (lỗi mạng/DNS), nên **không kết luận được**"
                " migration đã chạy hay chưa. Lỗi: " + str(exc)[:160]
                + ". Kiểm tra mạng rồi chạy lại."
            )
        raise


@pytest.fixture(scope="module")
def db():
    from dotenv import load_dotenv
    from supabase import create_client

    load_dotenv()
    client = create_client(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )

    # Chạm vào CSDL một lần ngay khi tạo fixture. Nếu không, mọi lỗi mạng sẽ lộ
    # ra giữa lúc test và bị quy cho schema.
    try:
        client.table("orders").select("id").limit(1).execute()
    except Exception as exc:
        if _is_unreachable(exc):
            pytest.skip(
                "Không gọi được CSDL Supabase (lỗi mạng/DNS): " + str(exc)[:120]
            )
        raise
    return client


def test_draft_is_allowed_as_an_order_status(db):
    """`add_draft_order_status.sql` — enum `order_status` phải có 'draft'.

    Không chạy migration này thì `create_draft_order` của agent lỗi ngay:
    Postgres trả `22P02 invalid input value for enum order_status: "draft"`.

    Cách kiểm: ghi thật một dòng rồi xoá. Không có cách nào hỏi kiểu enum mà
    không cần quyền đọc `pg_type`, và service-role key không đảm bảo có.
    """
    probe_id = "00000000-0000-0000-0000-0000000000d1"
    try:
        db.table("orders").delete().eq("id", probe_id).execute()
    except Exception:
        pass

    try:
        _require_reachable(
            db.table("orders").insert(
                {
                    "id": probe_id,
                    "customer_name": "probe",
                    "customer_email": "probe@example.invalid",
                    "customer_phone": "0",
                    "total_price": 0,
                    "status": "draft",
                }
            ).execute
        )
    except Exception as exc:
        # `_require_reachable` đã chuyển lỗi mạng thành fail rõ ràng; tới đây
        # là lỗi schema thật.
        message = str(exc)
        if "22P02" in message or "order_status" in message:
            pytest.fail(
                "Enum order_status chưa có 'draft' — chưa chạy "
                "migrations/add_draft_order_status.sql. Lỗi: " + message[:200]
            )
        raise
    else:
        db.table("orders").delete().eq("id", probe_id).execute()


def test_order_has_voucher_and_discount_columns(db):
    """`add_order_voucher_columns.sql` — bảng `orders` phải có đủ cột.

    Hai cột mà migration thực sự thêm là `voucher_code` và `voucher_discount`.
    Không phải `discount`/`subtotal`: tên đó chỉ là khoá trong JSON mà RPC trả về,
    và service trong Python dựng lại từ khoá đó — không có cột nào tên vậy.

    Hỏi từng cột riêng: `select *` không trả tên cột khi bảng rỗng, và cột thiếu
    thì PostgREST báo lỗi `42703`, tức là chính câu hỏi là cách kiểm.
    """
    missing = []
    for column in ("voucher_code", "voucher_discount"):
        try:
            _require_reachable(
                db.table("orders").select(column).limit(1).execute
            )
        except Exception as exc:
            message = str(exc)
            if "22P02" not in message and "PGRST" not in message and "42703" not in message:
                # Không phải lỗi "thiếu cột" — để nguyên để lỗi gốc lộ ra.
                raise
            missing.append(column)

    assert not missing, (
        "Cột thiếu trong bảng orders: " + ", ".join(missing)
        + " — chưa chạy migrations/add_order_voucher_columns.sql"
    )


def _rest_rpc_paths() -> list[str]:
    """Danh sách hàm RPC mà PostgREST phục vụ, đọc từ OpenAPI — chỉ đọc.

    Gọi `db.rpc(name, {})` để dò sự tồn tại thì **không phải** kiểm tra: với một
    hàm tồn tại, lời gọi thiếu tham số vẫn là `APIError`, dễ bị đọc nhầm thành
    "hàm không có". Ngược lại, khi hàm thiếu, thông báo cũng chỉ khác ở câu chữ
    — phải so khớp thủ công mỗi lần.

    OpenAPI của PostgREST liệt kê chính xác các hàm được expose, nên vắng mặt
    ở đây là bằng chứng thiếu chứ không phải giả định.
    """
    import json
    import urllib.request

    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/"
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    request = urllib.request.Request(
        url,
        headers={
            "apikey": key,
            "Authorization": "Bearer " + key,
            "Accept": "application/openapi+json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        spec = json.load(response)
    return sorted(p for p in spec.get("paths", {}) if p.startswith("/rpc/"))


def test_create_order_rpc_exists(db):
    """`add_create_order_rpc.sql` — hàm `rpc_create_order` phải được expose.

    Thiếu hàm thì `OrderService.create_order` gọi vào sẽ nhận `PGRST202`,
    tức đặt hàng không hoạt động dù giao diện vẫn hiện bình thường.
    """
    paths = _require_reachable(_rest_rpc_paths)
    assert "/rpc/rpc_create_order" in paths, (
        "PostgREST không phục vụ hàm rpc_create_order — chưa chạy "
        "migrations/add_create_order_rpc.sql. Các RPC đang có: "
        + ", ".join(p.removeprefix("/rpc/") for p in paths)
    )


def _rpc_argument_names(operation: dict) -> set[str]:
    """Tên tham số của một hàm RPC, đọc từ OpenAPI của PostgREST.

    PostgREST không liệt kê tham số hàm ở `parameters` kiểu `query`. Nó gom tất
    cả vào **một** tham số `in: "body"` tên `args`, và danh sách thật nằm ở
    `parameters[0].schema.properties`. Đã kiểm trên CSDL thật: `/rpc/match_cakes`
    có đúng 1 tham số body với `schema.properties` = `match_count`,
    `match_threshold`, `query_embedding`, và **0** tham số query.

    Vì vậy bản đầu của test này lấy `in == "query"` sẽ luôn ra tập rỗng — tức
    báo thiếu cả 12 tham số kể cả khi migration đã chạy đúng.

    Cố ý KHÔNG fallback sang tham số `query`. Đã thử: fallback đó cho ra kết quả
    hợp lý giả khi `schema.properties` rỗng, che mất đúng thứ cần phát hiện. Ở
    `rpc_create_order`, `p_voucher_code` và `p_voucher_discount` chính là hai
    tham số dễ mất, nên đọc thiếu rồi báo xanh là nguy hiểm hơn báo lỗi cấu trúc.
    """
    for param in operation.get("parameters", []):
        if param.get("in") == "body":
            return set((param.get("schema") or {}).get("properties") or {})
    return set()


def test_create_order_rpc_has_the_expected_signature(db):
    """Hàm phải nhận đúng 12 tham số, kể cả hai tham số voucher.

    Đây là lý do `add_create_order_rpc.sql` phải chạy **sau**
    `add_order_voucher_columns.sql`: chữ ký có `p_voucher_code` và
    `p_voucher_discount`. Hàm cũ thiếu hai tham số này vẫn gọi được nhưng sẽ
    âm thầm bỏ qua voucher, nên chỉ kiểm "hàm có tồn tại" là chưa đủ.
    """
    import json
    import urllib.request

    base = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/"
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    request = urllib.request.Request(
        base,
        headers={
            "apikey": key,
            "Authorization": "Bearer " + key,
            "Accept": "application/openapi+json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        spec = json.load(response)

    operation = spec.get("paths", {}).get("/rpc/rpc_create_order", {}).get("post")
    if operation is None:
        pytest.fail(
            "Chưa chạy migrations/add_create_order_rpc.sql — không thấy"
            " /rpc/rpc_create_order trong OpenAPI của PostgREST."
        )

    names = _rpc_argument_names(operation)
    expected = {
        "p_customer_id", "p_full_name", "p_phone", "p_email", "p_pickup_date",
        "p_total_price", "p_ai_summary", "p_voucher_code", "p_voucher_discount",
        "p_items", "p_customizations", "p_idempotency_key",
    }
    assert names, (
        "Đọc được vị trí /rpc/rpc_create_order nhưng không lấy được tên tham số"
        " nào — cấu trúc OpenAPI của PostgREST đã đổi, cần cập nhật test."
    )
    missing = expected - names
    assert not missing, (
        "rpc_create_order thiếu tham số: " + ", ".join(sorted(missing))
        + ". Có thể migration đã chạy phiên bản cũ, thiếu phần voucher."
    )


def test_idempotency_table_exists(db):
    """Bảng `order_idempotency` chặn bấm 'Đặt hàng' hai lần tạo hai đơn."""
    try:
        _require_reachable(
            db.table("order_idempotency").select("order_id").limit(1).execute
        )
    except Exception as exc:
        message = str(exc)
        if "PGRST" in message or "42" in message or "does not exist" in message:
            pytest.fail(
                "Chưa có bảng order_idempotency — chưa chạy "
                "migrations/add_create_order_rpc.sql. Lỗi: " + message[:160]
            )


def _sql_without_comments(source: str) -> str:
    """Bỏ comment `--` khỏi SQL, chỉ giữ phần thực sự được thực thi.

    Cần bước này vì file migration **giải thích lỗi bằng chính tên lỗi**: comment
    viết `pg_type.typkind` để nói rõ "đừng dùng cột này". Test đọc cả comment sẽ
    đỏ oan vĩnh viễn. Đã dính đúng lỗi đó ở bản đầu của test này.
    """
    return "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("--")
    )


def test_draft_status_migration_references_real_catalog_columns():
    """`add_draft_order_status.sql` phải đọc đúng cột trong catalog.

    Kiểm tĩnh, không cần CSDL. Bản đầu của migration hỏi `pg_type.typkind` — cột
    **không tồn tại** — nên chạy trên Supabase SQL Editor báo

        ERROR: 42703: column typ.typkind does not exist
        HINT: Perhaps you meant to reference the column "typ.typsend".

    và migration không áp dụng được. Người dùng đã dính đúng lỗi này, nên test
    này nhằm ngăn nó quay lại.

    Tên cột đúng là `typtype` (`typsend`, `typreceive`, ... là các cột khác).
    `add_staff_role.sql` — file đã chạy thành công trên cùng CSDL — dùng đúng
    tên đó.
    """
    source = (
        BACKEND_ROOT / "migrations" / "add_draft_order_status.sql"
    ).read_text(encoding="utf-8")

    executable = _sql_without_comments(source)

    assert "typkind" not in executable, (
        "add_draft_order_status.sql hỏi cột pg_type.typkind, cột không tồn tại."
        " Dùng typtype."
    )
    assert "typtype" in executable, (
        "add_draft_order_status.sql không hỏi typtype nên không kiểm được enum."
    )
    # Câu hỏi catalog phải thật sự đi tìm đúng type.
    assert "typname = 'order_status'" in executable, (
        "Câu hỏi catalog không giới hạn ở typname = 'order_status'."
    )


def test_migration_order_is_documented():
    """Thứ tự chạy 3 migration phải được ghi rõ trong chính file.

    `add_create_order_rpc.sql` có chữ ký chứa `p_voucher_code`/`p_voucher_discount`,
    nên nó cần hai file trước đã chạy. Chạy trước sẽ báo lỗi thiếu cột/cột enum,
    và lỗi lúc đó khó đọc ra nguyên nhân thật.
    """
    source = (
        BACKEND_ROOT / "migrations" / "add_create_order_rpc.sql"
    ).read_text(encoding="utf-8")

    assert "add_order_voucher_columns.sql" in source, (
        "add_create_order_rpc.sql không ghi là cần file cột voucher chạy trước."
    )