"""Vì sao đăng nhập báo "sai mật khẩu" dù mật khẩu đúng.

Nguyên nhân đo được: `supabase-py 2.30` trả về **None** từ `maybe_single()` khi
không có dòng nào khớp (xem `SyncMaybeSingleRequestBuilder.execute`:
`if len(parsed.data) == 0: return None`).

`AuthService.login` đọc `user_result.data` ngay, nên khi tài khoản có trong
`auth.users` nhưng CHƯA có dòng trong bảng `public.users` thì:

    AttributeError: 'NoneType' object has no attribute 'data'

`except Exception` ngay dưới bắt lỗi đó và ném `Invalid email or password` (401).
Giao diện hiển thị "Email hoặc mật khẩu không đúng" — nên lỗi thiếu dữ liệu bị
che thành lỗi sai mật khẩu, và mỗi lần thử còn bị tính là một lần sai nên tài
khoản bị khoá 15 phút.

Đây đúng là tình huống của tài khoản admin/baker tạo tay trên Supabase
Dashboard: Dashboard chỉ tạo bản ghi trong `auth.users`, không tạo dòng
`public.users`.

Hai nhánh khác (`oauth_google`, `refresh_token`) đã kiểm `None` đúng cách, nên
chỉ `login` bị.
"""

import pytest

from app.services.auth_service import AuthService, AuthServiceError
from app.core.rate_limiter import login_rate_limiter


class _Session:
    access_token = "access-token-gia"
    refresh_token = "refresh-token-gia"


class _User:
    id = "11111111-1111-1111-1111-111111111111"
    email = "admin@example.test"
    user_metadata: dict = {}


class _AuthResponse:
    user = _User()
    session = _Session()


class _Auth:
    def sign_in_with_password(self, _creds):
        return _AuthResponse()


class _Query:
    """Bắt chước chuỗi gọi PostgREST; `execute()` trả về giá trị đã cho."""

    def __init__(self, result):
        self._result = result

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return self._result


class _Client:
    def __init__(self, user_row_result):
        self.auth = _Auth()
        self._result = user_row_result

    def table(self, _name):
        return _Query(self._result)


class _Row:
    def __init__(self, data):
        self.data = data


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    login_rate_limiter.reset(_User.email)
    yield
    login_rate_limiter.reset(_User.email)


@pytest.mark.asyncio
async def test_thieu_dong_trong_bang_users_khong_duoc_bao_sai_mat_khau():
    """Mật khẩu ĐÚNG nhưng thiếu dòng `public.users`: không được nói sai mật khẩu.

    `maybe_single()` trả None, nên `user_result.data` nổ `AttributeError`.
    """
    service = AuthService(_Client(user_row_result=None))

    result = await service.login(email=_User.email, password="MatKhauDung123!")

    assert result["access_token"] == "access-token-gia", (
        "Supabase đã xác thực thành công thì phải trả token, không được báo lỗi"
    )
    # Thiếu dòng trong bảng users thì về vai mặc định, không làm sập đăng nhập.
    assert result["user"]["role"] == "customer"
    assert result["user"]["email"] == _User.email


@pytest.mark.asyncio
async def test_thieu_dong_users_khong_bi_tinh_la_lan_dang_nhap_sai():
    """Không được tính vào bộ đếm khoá tài khoản.

    Lỗi cũ khiến khách thử 5 lần với mật khẩu ĐÚNG là bị khoá 15 phút.
    """
    service = AuthService(_Client(user_row_result=None))

    await service.login(email=_User.email, password="MatKhauDung123!")

    assert not login_rate_limiter.is_locked(_User.email)


@pytest.mark.asyncio
async def test_co_dong_users_tra_ve_dung_vai():
    """Trường hợp bình thường giữ nguyên: đọc đúng vai từ bảng."""
    row = _Row({"full_name": "Quản trị", "phone": "0900000000", "role": "admin"})
    service = AuthService(_Client(user_row_result=row))

    result = await service.login(email=_User.email, password="MatKhauDung123!")

    assert result["user"]["role"] == "admin"
    assert result["user"]["full_name"] == "Quản trị"


@pytest.mark.asyncio
async def test_full_name_null_trong_db_khong_lam_sap_response():
    """`full_name` NULL trong bảng users phải thành "" chứ không được là None.

    Nguyên nhân THỨ HAI của "đúng mật khẩu mà báo sai":
    `UserResponse.full_name` khai là `str` (bắt buộc), còn code cũ viết
    `user_data.get("full_name", "")`. Giá trị mặc định của `dict.get` CHỈ áp dụng
    khi THIẾU khoá; cột NULL trả về khoá có mặt với giá trị None, nên `.get` trả
    None. FastAPI validate response thất bại -> 500. Giao diện bắt mọi lỗi rồi in
    "Email hoặc mật khẩu không đúng", nên lỗi dữ liệu bị hiểu thành sai mật khẩu.

    Tài khoản admin/baker tạo bằng SQL hay Dashboard rất thường để trống
    full_name — đúng nhóm tài khoản người dùng báo lỗi.
    """
    row = _Row({"full_name": None, "phone": None, "role": "admin"})
    service = AuthService(_Client(user_row_result=row))

    result = await service.login(email=_User.email, password="MatKhauDung123!")

    assert result["user"]["full_name"] == "", "NULL phải quy về chuỗi rỗng"
    assert result["user"]["role"] == "admin", "không được mất vai admin"

    # Chốt lại bằng chính schema FastAPI dùng để validate response.
    from app.schemas.auth import AuthResponse

    AuthResponse.model_validate(result)


@pytest.mark.asyncio
async def test_email_null_khong_lam_sap_response():
    """`email` cũng khai là `str` bắt buộc trong UserResponse."""

    class _NoEmailUser(_User):
        email = None

    class _NoEmailAuthResponse:
        user = _NoEmailUser()
        session = _Session()

    class _NoEmailAuth:
        def sign_in_with_password(self, _creds):
            return _NoEmailAuthResponse()

    client = _Client(user_row_result=_Row({"full_name": "A", "role": "customer"}))
    client.auth = _NoEmailAuth()
    service = AuthService(client)

    result = await service.login(email="admin@example.test", password="X")

    from app.schemas.auth import AuthResponse

    AuthResponse.model_validate(result)


@pytest.mark.asyncio
async def test_mat_khau_sai_van_bao_loi_401():
    """Sửa lỗi trên KHÔNG được làm mật khẩu sai trở thành đăng nhập được."""

    class _FailingAuth:
        def sign_in_with_password(self, _creds):
            class _Empty:
                user = None
                session = None

            return _Empty()

    client = _Client(user_row_result=None)
    client.auth = _FailingAuth()
    service = AuthService(client)

    with pytest.raises(AuthServiceError) as exc:
        await service.login(email=_User.email, password="SaiMatKhau")

    assert exc.value.status_code == 401
