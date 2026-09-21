"""Middleware giới hạn kích thước body ở tầng ASGI.

LÝ DO TỒN TẠI
    `search_by_image` đọc tối đa `MAX_UPLOAD_BYTES + 1` byte, nên bản thân ảnh
    không bao giờ bị nạp trọn vào RAM. Nhưng FastAPI phân tích multipart TRƯỚC
    khi endpoint chạy, và bộ phân tích đó gom toàn bộ phần thân vào bộ nhớ. Một
    upload 2 GB vì thế vẫn có thể làm cạn RAM máy chủ trước khi endpoint kịp
    từ chối.

    Middleware này chặn ở tầng thấp hơn, không chạm tới bộ phân tích multipart.

HAI LỚP CHẶN
    1. Theo `Content-Length` — chặn trước khi đọc byte nào. Rẻ nhất, xử lý được
       gần như mọi client thật (trình duyệt và fetch() luôn gửi header này).
    2. Theo số byte ĐÃ CHẢY QUA — bọc `receive` để cộng dồn. Bắt được cả trường
       hợp `Transfer-Encoding: chunked` (không có Content-Length) và trường hợp
       client khai Content-Length nhỏ hơn thực tế.

    Lớp 2 là bắt buộc, không phải phòng xa. Đã đo trên server thật: một request
    chunked 30 MB lọt hoàn toàn qua lớp 1, được bộ phân tích multipart gom trọn
    vào RAM, rồi mới bị endpoint từ chối — tức là toàn bộ chi phí bộ nhớ đã trả
    xong trước khi có ai kiểm tra.

TẠI SAO LỚP 2 KHÔNG NÉM EXCEPTION
    Cách trực giác là ném một exception từ `receive` để dừng ứng dụng. Đã thử và
    đo được: nó KHÔNG hoạt động. Exception chui qua bộ phân tích multipart của
    Starlette rồi bị `fastapi/routing.py` bắt bằng `except Exception`, biến thành
    400 "There was an error parsing the body". Middleware không bao giờ nhận lại
    được, nên không thể trả 413 — và tệ hơn, bộ phân tích đã đọc hết 30 MB trước
    khi exception kịp phát tác.

    Nên lớp 2 thay vào đó CẮT dữ liệu: khi tổng vượt ngưỡng, nó trả về một khối
    cuối rỗng kèm `more_body: False`. Bộ phân tích thấy body kết thúc nên dừng
    bình thường, không bao giờ chạm tới phần dữ liệu khổng lồ. Sau khi ứng dụng
    chạy xong, middleware ghi đè response bằng 413.

TẠI SAO LÀ ASGI THUẦN, KHÔNG PHẢI BaseHTTPMiddleware
    `BaseHTTPMiddleware` chạy SAU khi body đã được đọc và bọc lại thành
    `Request`, nên nó không chặn được chi phí phân tích. Muốn chặn trước, phải
    viết theo giao diện ASGI thuần để can thiệp vào luồng `receive`.

ĐÁNH ĐỔI
    Khi request có Content-Length hợp lệ và nằm trong ngưỡng, receive được bọc
    lại nhưng chỉ cộng thêm một phép tính số nguyên mỗi khối — không sao chép,
    không đệm thêm. Chi phí không đáng kể so với việc đọc socket.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# 413 là mã đúng nghĩa "Payload Too Large".
_BODY = b'{"detail":"Request body qu\xc3\xa1 l\xe1\xbb\x9bn."}'

# Trần số lần hút phần thân khi từ chối. Mỗi vòng hút một khối (~64 KB ở
# Uvicorn mặc định), nên 2048 vòng tương đương ~128 MB — rộng rãi cho mọi
# upload thật, nhưng vẫn chặn được client gửi vô hạn.
_MAX_DRAIN_CHUNKS = 2048


class BodySizeLimitMiddleware:
    """Chặn request vượt ngưỡng, theo Content-Length và theo số byte thực chảy."""

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Chỉ áp dụng cho HTTP; websocket và lifespan đi thẳng qua.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Lớp 1: từ chối sớm theo header, chưa đọc byte nào.
        content_length = self._content_length(scope)
        if content_length is not None and content_length > self.max_body_bytes:
            await self._reject(receive, send)
            return

        # Lớp 2: đếm byte thật khi chúng chảy qua.
        #
        # KHÔNG ném exception ở đây. Đã thử và đo được: exception ném từ receive
        # sẽ chui qua bộ phân tích multipart của Starlette rồi bị
        # fastapi/routing.py bắt bằng `except Exception`, biến thành
        # 400 "There was an error parsing the body". Middleware không bao giờ
        # nhận được nó, nên không thể trả 413.
        #
        # Thay vào đó: đánh dấu cờ, cắt phần dữ liệu vượt ngưỡng, và báo hết
        # body. Bộ phân tích thấy body kết thúc nên dừng lại bình thường, không
        # bao giờ chạm tới phần dữ liệu khổng lồ.
        state = {"received": 0, "exceeded": False}

        async def counting_receive() -> Message:
            message = await receive()
            if message.get("type") != "http.request":
                return message

            if state["exceeded"]:
                # Đã vượt ngưỡng: không chuyển thêm byte nào cho ứng dụng.
                return {"type": "http.request", "body": b"", "more_body": False}

            body = message.get("body", b"")
            state["received"] += len(body)
            if state["received"] > self.max_body_bytes:
                state["exceeded"] = True
                # Cắt về đúng ngưỡng và kết thúc body. Ứng dụng thấy một body
                # cụt nên dừng ngay, không đọc tới phần còn lại.
                allowed = max(0, len(body) - (state["received"] - self.max_body_bytes))
                return {
                    "type": "http.request",
                    "body": body[:allowed],
                    "more_body": False,
                }

            return message

        # Giữ lại response của ứng dụng thay vì gửi thẳng ra ngoài.
        #
        # Lý do: khi body bị cắt, ứng dụng vẫn chạy tiếp và gửi response của nó
        # (thường là 400 vì multipart cụt, hoặc 200 nếu nó không quan tâm). Nếu ta
        # chuyển tiếp ngay thì client đã nhận status đó rồi, và không thể ghi đè
        # bằng 413 nữa — ASGI chỉ cho gửi http.response.start một lần.
        #
        # Nên đệm response lại. Chỉ khi ứng dụng chạy xong và ta biết chắc body
        # không vượt ngưỡng thì mới thả ra. Trường hợp bình thường (không vượt)
        # vẫn chỉ tốn thêm vài tham chiếu, không sao chép dữ liệu.
        buffered: list[Message] = []

        async def buffering_send(message: Message) -> None:
            buffered.append(message)

        await self.app(scope, counting_receive, buffering_send)

        if state["exceeded"]:
            # Body đã vượt ngưỡng: bỏ response của ứng dụng, trả 413.
            await self._reject(receive, send)
            return

        # Không vượt ngưỡng: thả response đã đệm ra ngoài, giữ nguyên thứ tự.
        for message in buffered:
            await send(message)

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

    async def _reject(self, receive: Receive, send: Send) -> None:
        """Gửi 413 rồi hút nốt phần thân."""
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

        await self._drain(receive)

    async def _drain(self, receive: Receive) -> None:
        """Hút phần thân còn lại để server tiêu thụ trọn request rồi mới đóng.

        Gửi xong response CHƯA đủ. Uvicorn tạm dừng đọc socket cho tới khi
        `receive()` được gọi (httptools_impl.receive gọi flow.resume_reading).
        Nếu ta thoát ngay, client vẫn đang đẩy phần thân lên và kết nối bị ngắt
        giữa chừng — đo được trên server thật: upload 50 MB nhận
        ConnectionAbortedError thay vì đọc được 413.

        Dữ liệu hút vào bị bỏ đi ngay, không tích luỹ, nên bộ nhớ không tăng
        theo kích thước upload. Có trần số vòng lặp: nếu client khai
        Content-Length gian dối hoặc gửi mãi không dứt, ta thoát chứ không treo
        worker.
        """
        for _ in range(_MAX_DRAIN_CHUNKS):
            try:
                message = await receive()
            except Exception:
                # Kết nối đã hỏng thì không còn gì để hút.
                break
            if message.get("type") == "http.disconnect":
                break
            if not message.get("more_body", False):
                break
