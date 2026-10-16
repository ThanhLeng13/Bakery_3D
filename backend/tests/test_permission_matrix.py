"""Ma trận phân quyền 4 vai trò × API — kiểm bằng cách GỌI THẬT.

Vì sao cần file này
-------------------
`frontend/src/lib/roles.ts` chỉ ẩn menu. Ẩn menu không phải bảo mật: bất kỳ ai
cũng gõ thẳng URL hoặc gọi API. Nếu chỉ kiểm tra "menu đã ẩn chưa" thì kết luận
"an toàn" là sai — và đây đúng là cái bẫy mà kế hoạch đã cảnh báo.

Vì vậy mọi dòng dưới đây đều gọi thật qua `TestClient`, chỉ thay `get_current_user`
(đọc token → đổi thành dict user). Không thay `require_role`: nếu thay cả nó thì
test chỉ chứng minh được mock, chứng minh không được gì.

Cách đọc kết quả
----------------
- 401 = chưa đăng nhập. Đúng.
- 403 = đã đăng nhập nhưng sai vai trò. Đúng — đây là kết quả ta muốn.
- 404/500 = đã lọt qua lớp phân quyền (có thể mới là 404 do id không tồn tại).
  **Đây là hàng đỏ** và là lý do file này tồn tại.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.v1.router import router
from app.core import dependencies


ALL_ROLES = ("customer", "staff", "baker", "admin")

# (method, path) -> các vai trò ĐƯỢC vào.
# Muốn kiểm tra thì thêm route thật vào bảng; không suy diễn từ tên file.
ALLOWED: dict[tuple[str, str], tuple[str, ...]] = {
    # ---- Khu vực staff: bán hàng. KHÔNG cho admin — staff_orders chỉ nhận
    # đúng `["staff"]`. Admin có khu vực riêng (/admin/orders) để xem toàn bộ.
    ("GET", "/api/v1/staff/orders"): ("staff",),
    ("GET", "/api/v1/staff/orders/{order_id}"): ("staff",),
    ("PATCH", "/api/v1/staff/orders/{order_id}/status"): ("staff",),
    # ---- Khu vực baker: sản xuất. Cũng không mở cho admin.
    ("GET", "/api/v1/baker/orders"): ("baker",),
    ("GET", "/api/v1/baker/orders/{order_id}"): ("baker",),
    ("PATCH", "/api/v1/baker/orders/{order_id}/status"): ("baker",),
    ("PATCH", "/api/v1/baker/orders/{order_id}/notes"): ("baker",),
    ("POST", "/api/v1/baker/orders/{order_id}/incident"): ("baker",),
    # ---- Khu vực admin: quản trị ----
    ("GET", "/api/v1/admin/orders"): ("admin",),
    ("GET", "/api/v1/admin/orders/{order_id}"): ("admin",),
    ("DELETE", "/api/v1/admin/orders/{order_id}"): ("admin",),
    ("GET", "/api/v1/admin/products"): ("admin",),
    ("POST", "/api/v1/admin/products"): ("admin",),
    ("GET", "/api/v1/admin/products/{product_id}"): ("admin",),
    ("PUT", "/api/v1/admin/products/{product_id}"): ("admin",),
    ("PATCH", "/api/v1/admin/products/{product_id}/status"): ("admin",),
    ("POST", "/api/v1/admin/products/{product_id}/images"): ("admin",),
    ("GET", "/api/v1/admin/users"): ("admin",),
    ("PATCH", "/api/v1/admin/users/{user_id}/role"): ("admin",),
    ("GET", "/api/v1/admin/options"): ("admin",),
    ("POST", "/api/v1/admin/options"): ("admin",),
    ("PUT", "/api/v1/admin/options/{option_id}"): ("admin",),
    ("PATCH", "/api/v1/admin/options/{option_id}/status"): ("admin",),
    ("DELETE", "/api/v1/admin/options/{option_id}"): ("admin",),
    # ---- Khu vực khách ----
    ("POST", "/api/v1/orders"): ("customer",),
    ("GET", "/api/v1/orders"): ("customer",),
    ("GET", "/api/v1/orders/{order_id}"): ("customer",),
    # ---- Đúng người thì đúng việc, không giới hạn customer ----
    # `/orders/quote` chỉ TÍNH tiền; `/loyalty/*` chỉ đọc/đổi điểm của chính
    # mình (user["id"] lấy từ token). Mở cho staff/baker/admin không rủi ro dữ
    # liệu — họ xem điểm của chính mình. Đây là quyết định thiết kế có chủ đích,
    # không phải sót quyền; nên ghi vào ma trận thay vì "vá" bằng require_customer.
    ("POST", "/api/v1/orders/quote"): ALL_ROLES,
    ("GET", "/api/v1/loyalty/me"): ALL_ROLES,
    ("POST", "/api/v1/loyalty/redeem"): ALL_ROLES,
    ("POST", "/api/v1/purchases"): ("customer",),
    ("GET", "/api/v1/purchases/history"): ("customer",),
    ("POST", "/api/v1/reviews"): ("customer",),
    ("POST", "/api/v1/chat/sessions"): ("customer",),
    ("POST", "/api/v1/chat/sessions/{session_id}/messages"): ("customer",),
    ("GET", "/api/v1/chat/sessions/{session_id}/history"): ("customer",),
    # ---- Danh mục công khai: KHÔNG cần đăng nhập (xem cửa hàng không cần
    # tài khoản). Ma trận chỉ mô tả route được bảo vệ, nên các route này nằm
    # ngoài bảng; xem `TestPublicRoutesNeedNoLogin` bên dưới.
}

# Thân request tối thiểu. Endpoint có validate sẽ trả 422 — nhưng 422 VẪN là
# "đã qua lớp phân quyền", nên test vẫn đo được điều cần đo.
BODIES: dict[tuple[str, str], dict] = {
    ("POST", "/api/v1/orders"): {"items": [{"product_id": "x", "quantity": 1}]},
    ("POST", "/api/v1/orders/quote"): {"items": [{"product_id": "x", "quantity": 1}]},
    ("POST", "/api/v1/loyalty/redeem"): {"points": 10, "reward_id": "x"},
    ("POST", "/api/v1/purchases"): {"items": [{"product_id": "x", "quantity": 1}]},
    ("POST", "/api/v1/reviews"): {"product_id": "x", "rating": 5, "comment": "ok"},
    ("POST", "/api/v1/chat/sessions"): {},
    ("POST", "/api/v1/admin/products"): {"name": "x", "base_price": 1},
    ("PUT", "/api/v1/admin/products/{product_id}"): {"name": "x", "base_price": 1},
    ("POST", "/api/v1/admin/products/{product_id}/images"): {"url": "x"},
    ("PATCH", "/api/v1/admin/products/{product_id}/status"): {"is_active": True},
    ("PATCH", "/api/v1/admin/users/{user_id}/role"): {"role": "staff"},
    ("POST", "/api/v1/admin/options"): {"option_type": "size", "value": "x"},
    ("PUT", "/api/v1/admin/options/{option_id}"): {"value": "y"},
    ("PATCH", "/api/v1/admin/options/{option_id}/status"): {"is_active": True},
    ("PATCH", "/api/v1/staff/orders/{order_id}/status"): {"status": "confirmed"},
    ("PATCH", "/api/v1/baker/orders/{order_id}/status"): {"status": "in_production"},
    ("PATCH", "/api/v1/baker/orders/{order_id}/notes"): {"notes": "ok"},
    ("POST", "/api/v1/baker/orders/{order_id}/incident"): {"incident_type": "other"},
}

PLACEHOLDERS = {
    "order_id": "00000000-0000-0000-0000-000000000001",
    "product_id": "00000000-0000-0000-0000-000000000002",
    "option_id": "00000000-0000-0000-0000-000000000003",
    "user_id": "00000000-0000-0000-0000-000000000004",
    "session_id": "00000000-0000-0000-0000-000000000005",
}

# Route nào chỉ cần chứng minh "vai trò sai bị chặn", không cần đi tới DB.
# Ta chặn sớm ở `require_role` nên DB không bao giờ được gọi.


def _concrete(path: str) -> str:
    for key, val in PLACEHOLDERS.items():
        path = path.replace("{" + key + "}", val)
    return path


def _client_as(role: str | None) -> TestClient:
    """TestClient với `get_current_user` trả về đúng vai trò muốn thử.

    Chỉ thay `get_current_user`. `require_admin`/`require_staff`/`require_baker`
    vẫn là hàm thật, nên 403 trong kết quả là hành vi thật của ứng dụng.
    """
    from fastapi import FastAPI

    app = FastAPI()
    # `router` của v1 đã có sẵn đường dẫn dạng `/auth/login`; tiền tố `/api/v1`
    # do `app.main` gắn. Không thêm ở đây, không thì thành `/api/v1/api/v1/...`
    # và mọi route trả 404 — trông như lỗ hổng nhưng thực ra là lỗi của test.
    app.include_router(router, prefix="/api/v1")

    async def _fake_current_user():
        if role is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=401, detail="Authentication required")
        return {"id": "user-test", "email": f"{role}@test.vn", "role": role}

    app.dependency_overrides[dependencies.get_current_user] = _fake_current_user
    return TestClient(app, raise_server_exceptions=False)


def _call(client: TestClient, method: str, path: str):
    key = (method, path)
    body = BODIES.get(key)
    concrete = _concrete(path)
    headers = {"Authorization": "Bearer test-token"}
    return client.request(method, concrete, json=body, headers=headers)


def _ids():
    return [
        f"{m} {p}"
        for (m, p) in ALLOWED
    ]


class TestPermissionMatrix:
    """Mỗi route, mỗi vai trò: vào được thì 2xx/404/422, sai thì 401/403."""

    @pytest.mark.parametrize("route", _ids())
    @pytest.mark.parametrize("role", ALL_ROLES)
    def test_role_is_allowed_exactly_when_matrix_says_so(self, route, role):
        method, path = route.split(" ", 1)
        allowed = ALLOWED[(method, path)]

        with _client_as(role) as client:
            resp = _call(client, method, path)

        if role in allowed:
            # Đã qua được lớp phân quyền: 404 (id giả) và 422 (thiếu trường) đều
            # chứng minh request đã tới tầng nghiệp vụ, không bị chặn ở quyền.
            assert resp.status_code not in (401, 403), (
                f"{role} BỊ CHẶN ở {route} dù ma trận cho phép. "
                f"Thực tế {resp.status_code}: {resp.text[:160]}"
            )
        else:
            # Sai vai trò: phải bị chặn ngay.
            assert resp.status_code in (401, 403), (
                f"{role} LỌT QUA phân quyền ở {route} — mã {resp.status_code}. "
                f"Đây là lỗ hổng, không phải lỗi của test."
            )


class TestNoTokenAlwaysRejected:
    """Route trong ma trận đều phải chặn khách chưa đăng nhập."""

    @pytest.mark.parametrize("route", _ids())
    def test_anonymous_is_401_or_403(self, route):
        method, path = route.split(" ", 1)
        with _client_as(None) as client:
            resp = _call(client, method, path)

        assert resp.status_code in (401, 403), (
            f"{route} mở cho khách chưa đăng nhập (mã {resp.status_code})."
        )


class TestPublicRoutesNeedNoLogin:
    """Danh mục công khai xem được không cần đăng nhập — chốt lại chủ đích.

    Nếu sau này ai đó gắn `require_customer` vào `/products`, khách vẫn xem cửa
    hàng được nhưng test này đỏ, báo đúng việc vừa thay đổi.
    """

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/products",
            "/api/v1/products/{product_id}",
            "/api/v1/cake-3d-models",
            "/api/v1/branches",
            "/api/v1/options",
        ],
    )
    def test_public_route_reaches_handler_without_token(self, path):
        with _client_as(None) as client:
            resp = client.get(_concrete(path))

        # 404 (id giả) / 422 = đã tới tầng nghiệp vụ. 401/403 = bị chặn oan.
        assert resp.status_code not in (401, 403), (
            f"{path} yêu cầu đăng nhập (mã {resp.status_code}) — xem cửa hàng cần "
            f"tài khoản thì khách lướt web sẽ bị chặn."
        )


class TestRoleCannotBeSelfAssigned:
    """Staff/baker/customer không tự nâng quyền, và không đổi quyền người khác."""

    @pytest.mark.parametrize("role", ("customer", "staff", "baker"))
    def test_non_admin_cannot_change_any_role(self, role):
        method, path = "PATCH", "/api/v1/admin/users/{user_id}/role"
        assert (method, path) in ALLOWED
        assert "admin" in ALLOWED[(method, path)]

        with _client_as(role) as client:
            resp = _call(client, method, path)

        assert resp.status_code in (401, 403), (
            f"{role} đổi được quyền của người khác (mã {resp.status_code})."
        )

    def test_admin_is_still_allowed(self):
        """Ngược lại: admin thì vào được, để chắc test trên không đỏ vì lý do sai."""
        with _client_as("admin") as client:
            resp = _call(client, "PATCH", "/api/v1/admin/users/{user_id}/role")

        assert resp.status_code not in (401, 403)
