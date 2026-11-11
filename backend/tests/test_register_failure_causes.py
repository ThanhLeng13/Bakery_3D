"""Các nguyên nhân làm đăng ký thất bại.

Người dùng báo: tạo tài khoản thì hiện "Đã xảy ra lỗi, vui lòng thử lại sau".
`test_auth.py` chỉ kiểm các hàm validator và bộ giới hạn đăng nhập, KHÔNG có
test nào chạy qua `AuthService.register`, nên các nhánh dưới đây chưa từng được
kiểm. Mỗi test ở đây tương ứng một cách đăng ký có thể hỏng thật.

Dùng client Supabase giả: không gọi mạng, không tạo tài khoản thật.
"""

import asyncio

import pytest

from app.schemas.auth import AuthResponse
from app.services.auth_service import AuthService, AuthServiceError, ValidationError

MAT_KHAU_HOP_LE = "Matkhau1!"


class FakeUser:
    def __init__(self, user_id="11111111-1111-1111-1111-111111111111"):
        self.id = user_id


class FakeSession:
    def __init__(self, access="tok-abc", refresh="ref-abc"):
        self.access_token = access
        self.refresh_token = refresh


class FakeSignUpResult:
    def __init__(self, user, session):
        self.user = user
        self.session = session


class FakeAuth:
    def __init__(self, result=None, loi=None):
        self._result = result
        self._loi = loi
        self.lan_goi = []

    def sign_up(self, payload):
        self.lan_goi.append(payload)
        if self._loi:
            raise self._loi
        return self._result


class FakeInsert:
    def __init__(self, bang, loi=None):
        self._bang = bang
        self._loi = loi

    def execute(self):
        if self._loi:
            raise self._loi
        return type("R", (), {"data": [self._bang.du_lieu_cuoi]})()


class FakeTable:
    def __init__(self, loi_insert=None):
        self._loi_insert = loi_insert
        self.du_lieu_cuoi = None
        self.so_lan_insert = 0

    def insert(self, du_lieu):
        self.so_lan_insert += 1
        self.du_lieu_cuoi = du_lieu
        return FakeInsert(self, self._loi_insert)


class FakeSupabase:
    def __init__(self, sign_up_result=None, loi_sign_up=None, loi_insert=None):
        self.auth = FakeAuth(sign_up_result, loi_sign_up)
        self.bang = FakeTable(loi_insert)
        self.ten_bang_da_dung = []

    def table(self, ten):
        self.ten_bang_da_dung.append(ten)
        return self.bang


def chay(coro):
    return asyncio.run(coro)


def dang_ky(client, password=MAT_KHAU_HOP_LE):
    service = AuthService(client)
    return chay(
        service.register(
            email="khach@gmail.com",
            password=password,
            full_name="Nguyễn Văn Test",
            phone="0912345678",
        )
    )


class TestDangKyThanhCong:
    def test_tra_ve_token_va_ghi_dung_bang_users(self):
        client = FakeSupabase(FakeSignUpResult(FakeUser(), FakeSession()))
        ket_qua = dang_ky(client)

        assert ket_qua["access_token"] == "tok-abc"
        assert ket_qua["refresh_token"] == "ref-abc"
        assert ket_qua["user"]["role"] == "customer"
        assert client.ten_bang_da_dung == ["users"]
        assert client.bang.du_lieu_cuoi["role"] == "customer"
        # Phản hồi phải qua được chính schema mà endpoint khai báo.
        AuthResponse.model_validate(ket_qua)

    def test_khong_bao_gio_tu_gan_vai_tro_khac_customer(self):
        """Đăng ký công khai chỉ được tạo khách hàng.

        Nếu chỗ này lấy vai trò từ dữ liệu người dùng gửi lên thì ai cũng tự
        tạo được tài khoản quản trị.
        """
        client = FakeSupabase(FakeSignUpResult(FakeUser(), FakeSession()))
        dang_ky(client)
        assert client.bang.du_lieu_cuoi["role"] == "customer"


class TestThieuPhien:
    def test_sign_up_khong_tra_session_thi_token_rong(self):
        """Supabase bật xác nhận email thì `session` là None.

        Đây là hành vi HIỆN TẠI, ghi lại để thấy rõ hệ quả: API trả 201 kèm
        token rỗng, nên giao diện lưu token rỗng rồi tưởng đã đăng nhập. Người
        dùng bị đẩy về trang chủ trong trạng thái chưa có phiên thật.
        """
        client = FakeSupabase(FakeSignUpResult(FakeUser(), None))
        ket_qua = dang_ky(client)

        assert ket_qua["access_token"] == ""
        assert ket_qua["refresh_token"] == ""
        # Vẫn hợp lệ với schema, nên không có lá chắn nào chặn lại.
        AuthResponse.model_validate(ket_qua)

    def test_sign_up_khong_tra_user_thi_bao_loi_500(self):
        client = FakeSupabase(FakeSignUpResult(None, None))
        with pytest.raises(AuthServiceError) as e:
            dang_ky(client)
        assert e.value.status_code == 500
        assert client.bang.so_lan_insert == 0, "không được ghi users khi chưa có user"


class TestEmailDaTonTai:
    @pytest.mark.parametrize(
        "thong_bao",
        [
            "User already registered",
            "duplicate key value violates unique constraint",
            "unique constraint failed",
        ],
    )
    def test_nhan_ra_email_trung_va_tra_loi_theo_truong(self, thong_bao):
        client = FakeSupabase(loi_sign_up=Exception(thong_bao))
        with pytest.raises(ValidationError) as e:
            dang_ky(client)
        assert e.value.errors[0]["field"] == "email"


class TestGhiBangUsersThatBai:
    def test_rls_chan_insert_thi_tra_loi_500_chu_khong_im_lang(self):
        """Service dùng khoá anon, không phải service role.

        `_get_auth_service` gọi `get_supabase_client(use_service_role=False)`.
        Nếu RLS của `public.users` không cho phép dòng này, insert sẽ hỏng. Khi
        đó tài khoản ĐÃ được tạo trong Supabase Auth nhưng KHÔNG có hồ sơ ở
        `public.users` — đúng tình trạng làm đăng nhập sau đó trả về hồ sơ
        rỗng. Test này chốt rằng lỗi được báo ra thay vì bỏ qua.
        """
        client = FakeSupabase(
            FakeSignUpResult(FakeUser(), FakeSession()),
            loi_insert=Exception(
                'new row violates row-level security policy for table "users"'
            ),
        )
        with pytest.raises(AuthServiceError) as e:
            dang_ky(client)
        assert e.value.status_code == 500


class TestMatKhauYeu:
    def test_mat_khau_yeu_bi_chan_truoc_khi_goi_supabase(self):
        client = FakeSupabase(FakeSignUpResult(FakeUser(), FakeSession()))
        with pytest.raises(ValidationError) as e:
            dang_ky(client, password="123")

        assert all(loi["field"] == "password" for loi in e.value.errors)
        assert client.auth.lan_goi == [], "không được gọi sign_up khi mật khẩu yếu"
        assert client.bang.so_lan_insert == 0
