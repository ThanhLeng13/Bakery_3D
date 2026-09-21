"""Middleware giới hạn kích thước body ở tầng ASGI.

LÝ DO TỒN TẠI
    `search_by_image` đọc tối đa `MAX_UPLOAD_BYTES + 1` byte, nên bản thân ảnh
    không bao giờ bị nạp trọn vào RAM. Nhưng FastAPI phân tích multipart TRƯỚC
    khi endpoint chạy, và bộ phân tích đó gom toàn bộ phần thân vào bộ nhớ. Một
    upload 2 GB vì thế vẫn có thể làm cạn RAM máy chủ trước khi endpoint kịp
    từ chối.

    Middleware này chặn ở tầng thấp hơn: nó đọc `Content-Length` và từ chối
    ngay, không chạm tới bộ phân tích multipart.

TẠI SAO LÀ ASGI THUẦN, KHÔNG PHẢI BaseHTTPMiddleware
    `BaseHTTPMiddleware` chạy SAU khi body đã được đọc và bọc lại thành
    `Request`, nên nó không chặn được chi phí phân tích. Muốn chặn trước, phải
    viết theo giao diện ASGI thuần để can thiệp vào luồng `receive`.

    Cách làm ở đây chỉ kiểm tra header rồi chuyển tiếp nguyên trạng: không đọc,
    không đệm, không sao chép body. Nhờ vậy không tốn thêm băng thông bộ nhớ,
    và các request bình thường (JSON nhỏ) không bị ảnh hưởng gì.

GIỚI HẠN ĐÃ BIẾT
    Chỉ nhìn được `Content-Length`. Request dùng `Transfer-Encoding: chunked`
    không khai báo độ dài nên lọt qua lớp này; khi đó lớp kiểm tra trong endpoint
    vẫn là chốt chặn thật. Đây là lý do endpoint KHÔNG được bỏ phần kiểm tra
    độ dài của chính nó.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# 413 là mã đúng nghĩa "Payload Too Large".
_BODY = b'{"detail":"Request body qu\xc3\xa1 l\xe1\xbb\x9bn."}'

# Trần số lần hút phần thân khi từ chối. Mỗi vòng hút một khối (~64 KB ở
# Uvicorn mặc định), nên 2048 vòng tương đương ~128 MB — rộng rãi cho mọi
# upload thật, nhưng vẫn chặn được client gửi vô hạn.
_MAX_DRAIN_CHUNKS = 2048


class BodySizeLimitMiddleware:
    """Từ chối request có `Content-Length` vượt ngưỡng."""

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Chỉ áp dụng cho HTTP; websocket và lifespan đi thẳng qua.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = self._content_length(scope)
        if content_length is not None and content_length > self.max_body_bytes:
            await self._reject(receive, send, content_length)
            return

        await self.app(scope, receive, send)

    def _content_length(self, scope: Scope) -> int | None:
        """Đọc Content-Length, trả None nếu thiếu hoặc không hợp lệ."""
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    return int(value)
                except (TypeError, ValueError):
                    # Header rác: để tầng dưới xử lý, coi như không khai báo.
                    return None
        return None

    async def _reject(
        self, receive: Receive, send: Send, content_length: int
    ) -> None:
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(_BODY)).encode()),
            # Nói rõ giới hạn để client biết đường sửa, thay vì chỉ báo lỗi suông.
            (b"x-max-body-bytes", str(self.max_body_bytes).encode()),
        ]
        await send(
            {"type": "http.response.start", "status": 413, "headers": headers}
        )
        await send({"type": "http.response.body", "body": _BODY})

        # Gửi xong response CHƯA đủ. Uvicorn tạm dừng đọc socket cho tới khi
        # `receive()` được gọi (httptools_impl.receive gọi flow.resume_reading).
        # Nếu ta thoát ngay, client vẫn đang đẩy phần thân lên và kết nối bị
        # ngắt giữa chừng — đo được trên server thật: upload 50 MB nhận
        # ConnectionAbortedError thay vì đọc được 413.
        #
        # Nên phải hút hết phần thân còn lại qua receive() để server tiêu thụ
        # trọn request rồi mới đóng. Dữ liệu hút vào bị bỏ đi ngay, không tích
        # luỹ, nên bộ nhớ vẫn không tăng theo kích thước upload.
        #
        # Có trần số vòng lặp: nếu client khai Content-Length gian dối hoặc gửi
        # mãi không dứt, ta thoát chứ không treo worker.
        for _ in range(_MAX_DRAIN_CHUNKS):
            message = await receive()
            if message.get("type") == "http.disconnect":
                break
            if not message.get("more_body", False):
                break
