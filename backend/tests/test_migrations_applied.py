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

import pytest


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


@pytest.fixture(scope="module")
def db():
    from dotenv import load_dotenv
    from supabase import create_client

    load_dotenv()
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


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
        db.table("orders").insert(
            {
                "id": probe_id,
                "customer_name": "probe",
                "customer_email": "probe@example.invalid",
                "customer_phone": "0",
                "total_price": 0,
                "status": "draft",
            }
        ).execute()
    except Exception as exc:
        pytest.fail(
            "Enum order_status chưa có 'draft' — chưa chạy "
            "migrations/add_draft_order_status.sql. Lỗi: " + str(exc)[:200]
        )
    else:
        db.table("orders").delete().eq("id", probe_id).execute()


def test_order_has_voucher_and_discount_columns(db):
    """`add_order_voucher_columns.sql` — bảng `orders` phải có đủ cột.

    Hỏi từng cột riêng: `select *` không trả tên cột khi bảng rỗng, và cột thiếu
    thì PostgREST báo lỗi `42703`, tức là chính câu hỏi là cách kiểm.
    """
    missing = []
    for column in ("voucher_code", "discount", "subtotal"):
        try:
            db.table("orders").select(column).limit(1).execute()
        except Exception as exc:
            missing.append(f"{column} ({str(exc)[:60]})")

    assert not missing, (
        "Cột thiếu trong bảng orders: " + ", ".join(missing)
        + " — chưa chạy migrations/add_order_voucher_columns.sql"
    )


def test_create_order_rpc_exists(db):
    """`add_create_order_rpc.sql` — hàm `rpc_create_order` phải tồn tại.

    Thiếu hàm thì `OrderService.create_order` gọi vào sẽ nhận `PGRST202`,
    tức đặt hàng không hoạt động dù giao diện vẫn hiện bình thường.
    """
    try:
        db.rpc("rpc_create_order", {}).execute()
    except Exception as exc:
        message = str(exc)
        if "PGRST202" in message:
            pytest.fail(
                "Chưa có hàm rpc_create_order — chưa chạy "
                "migrations/add_create_order_rpc.sql."
            )
        # Báo lỗi khác (thiếu tham số, v.v.) nghĩa là hàm ĐÃ tồn tại.
        if "function public.rpc_create_order" in message and "schema cache" in message:
            pytest.fail(
                "Chưa chạy migrations/add_create_order_rpc.sql: " + message[:180]
            )


def test_idempotency_table_exists(db):
    """Bảng `order_idempotency` chặn bấm 'Đặt hàng' hai lần tạo hai đơn."""
    try:
        db.table("order_idempotency").select("order_id").limit(1).execute()
    except Exception as exc:
        message = str(exc)
        if "PGRST" in message or "42" in message or "does not exist" in message:
            pytest.fail(
                "Chưa có bảng order_idempotency — chưa chạy "
                "migrations/add_create_order_rpc.sql. Lỗi: " + message[:160]
            )