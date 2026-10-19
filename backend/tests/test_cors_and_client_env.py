"""Cấu hình CORS và biến môi trường phía client.

Gói 6 yêu cầu xác nhận "biến môi trường phía client không chứa service-role key"
và rà cấu hình deploy. Hai thứ đó không thể kiểm bằng cách nhìn, nên ở đây khóa
lại bằng test.

Vì sao CORS quan trọng với bài này
-------------------------------
Ứng dụng chạy ở `localhost:3000` và gọi API ở `localhost:8000` — khác origin,
nên CORS không phải chi tiết hình thức. Nhưng `allow_credentials=True` khiến
mọi sai lầm ở đây là lỗi bảo mật theo hướng ngược lại: origin rộng bị động
tới thì trình duyệt gửi cookie phiên kèm theo. Vì vậy test giữ `allow_origins`
ở dạng danh sách cụ thể và không bao giờ là `*`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


def _cors_kwargs() -> dict:
    """Tham số thực truyền cho `CORSMiddleware` trong `app.main`.

    Parse bằng `ast` chứ không đọc text: so khớp chuỗi sẽ dính vào comment và
    dễ bỏ sót khi ai đó xếp lại dòng.
    """
    import ast

    source = (BACKEND_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if name != "add_middleware":
            continue
        args = [a.id for a in node.args if isinstance(a, ast.Name)]
        if "CORSMiddleware" not in args:
            continue

        found: dict = {}
        for kw in node.keywords:
            if isinstance(kw.value, ast.Constant):
                found[kw.arg] = kw.value.value
            elif isinstance(kw.value, ast.Name):
                found[kw.arg] = kw.value.id
        return found

    raise AssertionError("Không tìm thấy add_middleware(CORSMiddleware, ...) trong main.py")


def _configured_origins() -> list[str]:
    """Đọc `CORS_ORIGINS` thẳng từ source `config.py`.

    Cố tình KHÔNG dùng `from app.core.config import settings`. `settings` được
    tạo một lần rồi cache trong `sys.modules`, nên sau khi sửa file giá trị cũ
    vẫn còn — test sẽ xanh với cấu hình `["*"]` trong khi ứng dụng thật đang chạy
    với cấu hình đó. Đây chính là loại lỗi test im lặng cần tránh, và tôi đã
    dính vào nó: đột biến đặt CORS thành `["*"]` vẫn cho 6 test xanh.
    """
    import ast

    source = (BACKEND_ROOT / "app" / "core" / "config.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.AnnAssign):
                continue
            target = stmt.target
            if not isinstance(target, ast.Name) or target.id != "CORS_ORIGINS":
                continue
            if isinstance(stmt.value, ast.List):
                return [
                    e.value
                    for e in stmt.value.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)
                ]
            raise AssertionError(
                "CORS_ORIGINS không phải danh sách literal — cần cập nhật test này."
            )
    raise AssertionError("Không tìm thấy CORS_ORIGINS trong config.py")


class TestCorsIsNotWildcard:
    def test_allow_credentials_is_true_because_app_uses_sessions(self):
        assert _cors_kwargs().get("allow_credentials") is True, (
            "Ứng dụng dùng phiên, nên cần cookie. Nếu đặt False thì mọi request"
            " đã đăng nhập sẽ hỏng."
        )

    def test_origins_are_not_wildcard(self):
        """`allow_credentials=True` cùng `allow_origins=["*"]` là lỗ hổng.

        Starlette sẽ tự phản chiếu Origin thay vì chặn, tức mọi website đều gọi
        được API bằng phiên của người dùng.
        """
        origins = _configured_origins()
        assert "*" not in origins, (
            "CORS đang mở toàn bộ internet trong khi gửi cookie. Phải liệt kê"
            " từng origin."
        )
        assert origins, "CORS_ORIGINS rỗng thì frontend không gọi được API."

    def test_every_origin_is_an_explicit_scheme_host(self):
        """Không có origin dạng wildcard con như `https://*.vercel.app`.

        Wildcard con không được hỗ trợ và thường bị hiểu sai là đã an toàn.
        """
        for origin in _configured_origins():
            assert "*" not in origin, f"Origin chứa ký tự đại diện: {origin}"
            assert origin.startswith(("http://", "https://")), origin


class TestClientBundleHasNoServiceRoleKey:
    """Không được đẩy service-role key xuống trình duyệt.

    Key anon (`sb_publishable_…`) thì công khai và có trong mọi bundle. Key
    service-role (`sb_secret_…`) bỏ qua RLS của Postgres — lọt vào bundle là
    trao toàn bộ CSDL cho bất kỳ ai tải trang.
    """

    # Chỉ quét mã frontend. `backend/.env` có key thật và đã bị gitignore.
    CLIENT_DIR = REPO_ROOT / "frontend"

    def _client_files(self):
        for pattern in ("src/**/*.ts", "src/**/*.tsx", "scripts/**/*.js", "scripts/**/*.cjs"):
            for path in self.CLIENT_DIR.glob(pattern):
                yield path

    def test_no_source_file_mentions_a_service_role_variable(self):
        offenders = []
        for path in self._client_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            # `SERVICE_ROLE` đứng riêng; `SERVICE_ROLE_KEY` là biến backend.
            if re.search(r"SERVICE_ROLE", text):
                offenders.append(str(path.relative_to(REPO_ROOT)))
        assert not offenders, (
            "Mã phía client nhắc tới service-role key: " + ", ".join(offenders)
        )

    def test_no_hardcoded_secret_key_pattern(self):
        offenders = []
        for path in self._client_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            # Cần hơn 20 ký tự sau `sb_secret_` để không trúng dạng viết tắt
            # kiểu `sb_secret_…` trong tài liệu.
            if re.search(r"sb_secret_[A-Za-z0-9_\-]{20,}", text):
                offenders.append(str(path.relative_to(REPO_ROOT)))
        assert not offenders, (
            "Mã phía client chứa service-role key thật: " + ", ".join(offenders)
        )

    def test_public_env_vars_are_named_as_expected(self):
        """Client chỉ được đọc biến `NEXT_PUBLIC_*`, vì chỉ vậy mới được nhúng.

        Một biến `SUPABASE_ANON_KEY` đọc bằng `process.env` không có tiền tố
        sẽ là `undefined` lúc chạy, dễ bị hiểu nhầm là "thiếu cấu hình" thay vì
        là "sai tên".
        """
        env_local = self.CLIENT_DIR / ".env.local"
        if not env_local.exists():
            pytest.skip("Không có .env.local trên máy này (CI cũng vậy)")
        text = env_local.read_text(encoding="utf-8")
        supabase_vars = re.findall(r"^([A-Z0-9_]*SUPABASE[A-Z0-9_]*)=", text, re.MULTILINE)
        for name in supabase_vars:
            assert name.startswith("NEXT_PUBLIC_"), (
                f"{name} không có tiền tố NEXT_PUBLIC_ nên sẽ không tới được"
                " trình duyệt."
            )