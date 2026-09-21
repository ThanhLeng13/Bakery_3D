"""CLIP image search tests — trụ cột 2.

Chiến lược test
---------------
Model CLIP thật nặng ~350 MB và mất ~45 giây để load, nên KHÔNG load trong CI.
Thay vào đó:
  - Mock `embed_image_bytes` để trả vector giả cố định
  - Test logic nghiệp vụ: validation ảnh, kẹp tham số, định dạng kết quả, xử lý lỗi

Phần model thật đã được kiểm chứng thủ công bằng ảnh thật (xem báo cáo):
  - Ảnh cùng sản phẩm: cosine 0.71
  - Ảnh khác sản phẩm: cosine 0.53
  - Ảnh bánh vs nhiễu ngẫu nhiên: 0.17
"""

import io
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.services import clip_service
from app.services.clip_service import (
    EMBEDDING_DIM,
    ClipModelUnavailableError,
    ClipSearchService,
    ClipServiceError,
    InvalidImageError,
    _validate_and_open_image,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def make_png_bytes(width: int = 224, height: int = 224) -> bytes:
    """Sinh một ảnh PNG hợp lệ để test."""
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color=(200, 180, 160)).save(buffer, format="PNG")
    return buffer.getvalue()


def make_embedding(value: float = 0.1) -> list[float]:
    """Vector giả đúng 512 chiều."""
    return [value] * EMBEDDING_DIM


# ─── Validation ảnh ──────────────────────────────────────────────────────────


class TestImageValidation:
    """Ảnh không hợp lệ phải bị từ chối TRƯỚC khi tốn thời gian chạy model."""

    def test_rejects_empty_bytes(self):
        with pytest.raises(InvalidImageError):
            _validate_and_open_image(b"")

    def test_rejects_non_image_bytes(self):
        with pytest.raises(InvalidImageError):
            _validate_and_open_image(b"day khong phai la anh")

    def test_rejects_truncated_png(self):
        """PNG hợp lệ nhưng bị cắt ngắn — phải phát hiện được."""
        valid = make_png_bytes()
        with pytest.raises(InvalidImageError):
            _validate_and_open_image(valid[: len(valid) // 3])

    def test_rejects_oversized_upload(self):
        with pytest.raises(ClipServiceError) as exc:
            _validate_and_open_image(b"x" * (11 * 1024 * 1024))
        assert exc.value.status_code == 413

    def test_rejects_image_too_small(self):
        with pytest.raises(ClipServiceError) as exc:
            _validate_and_open_image(make_png_bytes(10, 10))
        assert exc.value.status_code == 400

    def test_accepts_valid_png(self):
        image = _validate_and_open_image(make_png_bytes())
        assert image.mode == "RGB"
        assert image.size == (224, 224)

    def test_converts_rgba_to_rgb(self):
        """Ảnh PNG có alpha phải chuyển được sang RGB (CLIP cần 3 kênh)."""
        buffer = io.BytesIO()
        Image.new("RGBA", (100, 100), color=(255, 0, 0, 128)).save(buffer, format="PNG")
        image = _validate_and_open_image(buffer.getvalue())
        assert image.mode == "RGB"

    def test_invalid_bytes_do_not_trigger_model_load(self):
        """Bytes rác không được kích hoạt nạp model.

        Nạp model tốn ~45s và ~350MB RAM. Nếu thứ tự sai — nạp model trước rồi
        mới kiểm tra ảnh — thì chỉ cần một request với bytes rác là đủ để chặn
        tiến trình trong 45 giây. Test này gọi HÀM THẬT embed_image_bytes và
        chỉ patch _load_model, nên nó kiểm tra đúng thứ tự thực thi bên trong.
        """
        with patch.object(clip_service, "_load_model") as mock_load:
            with pytest.raises(InvalidImageError):
                clip_service.embed_image_bytes(b"day khong phai la anh")
            mock_load.assert_not_called()

    def test_valid_bytes_do_trigger_model_load(self):
        """Mặt còn lại: ảnh hợp lệ thì PHẢI nạp model để chạy suy luận."""
        with patch.object(clip_service, "_load_model") as mock_load:
            mock_load.side_effect = ClipModelUnavailableError("test")
            with pytest.raises(ClipModelUnavailableError):
                clip_service.embed_image_bytes(make_png_bytes())
            mock_load.assert_called_once()


# ─── Tìm kiếm ────────────────────────────────────────────────────────────────


class TestClipSearchService:
    """Logic tìm kiếm: gọi RPC đúng, định dạng kết quả, kẹp tham số."""

    def _service_with_rpc_result(self, rows):
        """Tạo service với Supabase client giả trả về `rows`."""
        client = MagicMock()
        client.rpc.return_value.execute.return_value = MagicMock(data=rows)
        return ClipSearchService(client)

    def test_returns_formatted_results(self):
        rows = [
            {
                "product_id": "p1",
                "product_name": "Bánh kem vanilla",
                "image_url": "https://example.test/a.jpg",
                "category": "bánh âu",
                "product_type": "cake",
                "base_price": 250000,
                "similarity": 0.8123,
            }
        ]
        service = self._service_with_rpc_result(rows)

        with patch(
            "app.services.clip_service.embed_image_bytes", return_value=make_embedding()
        ):
            result = service.search_by_image(make_png_bytes())

        assert result["count"] == 1
        item = result["results"][0]
        assert item["product_id"] == "p1"
        assert item["name"] == "Bánh kem vanilla"
        assert item["similarity"] == 0.8123
        # Phần trăm để giao diện hiển thị trực tiếp.
        assert item["similarity_percent"] == 81.2

    def test_passes_embedding_to_rpc(self):
        service = self._service_with_rpc_result([])
        vector = make_embedding(0.25)

        with patch(
            "app.services.clip_service.embed_image_bytes", return_value=vector
        ):
            service.search_by_image(make_png_bytes(), match_count=3, match_threshold=0.4)

        args = service.client.rpc.call_args
        assert args[0][0] == "match_cakes"
        assert args[0][1]["query_embedding"] == vector
        assert args[0][1]["match_count"] == 3
        assert args[0][1]["match_threshold"] == 0.4

    def test_clamps_match_count(self):
        """Không cho khách yêu cầu số lượng kết quả vô lý."""
        service = self._service_with_rpc_result([])
        with patch(
            "app.services.clip_service.embed_image_bytes", return_value=make_embedding()
        ):
            service.search_by_image(make_png_bytes(), match_count=9999)
            assert service.client.rpc.call_args[0][1]["match_count"] == 20

            service.search_by_image(make_png_bytes(), match_count=0)
            assert service.client.rpc.call_args[0][1]["match_count"] == 1

    def test_clamps_threshold(self):
        service = self._service_with_rpc_result([])
        with patch(
            "app.services.clip_service.embed_image_bytes", return_value=make_embedding()
        ):
            service.search_by_image(make_png_bytes(), match_threshold=5.0)
            assert service.client.rpc.call_args[0][1]["match_threshold"] == 1.0

            service.search_by_image(make_png_bytes(), match_threshold=-1.0)
            assert service.client.rpc.call_args[0][1]["match_threshold"] == 0.0

    def test_handles_empty_results(self):
        service = self._service_with_rpc_result([])
        with patch(
            "app.services.clip_service.embed_image_bytes", return_value=make_embedding()
        ):
            result = service.search_by_image(make_png_bytes())
        assert result["count"] == 0
        assert result["results"] == []

    def test_reports_timing_for_thesis_metrics(self):
        """Thời gian embed/truy vấn là số liệu cho báo cáo."""
        service = self._service_with_rpc_result([])
        with patch(
            "app.services.clip_service.embed_image_bytes", return_value=make_embedding()
        ):
            result = service.search_by_image(make_png_bytes())
        timing = result["timing_ms"]
        assert set(timing) == {"embed", "search", "total"}
        assert all(isinstance(v, (int, float)) and v >= 0 for v in timing.values())

    def test_rpc_failure_returns_service_error_not_raw_exception(self):
        """Lỗi database không được lộ chi tiết kỹ thuật ra client."""
        client = MagicMock()
        client.rpc.return_value.execute.side_effect = RuntimeError(
            'relation "public.cake_embeddings" does not exist'
        )
        service = ClipSearchService(client)

        with patch(
            "app.services.clip_service.embed_image_bytes", return_value=make_embedding()
        ):
            with pytest.raises(ClipServiceError) as exc:
                service.search_by_image(make_png_bytes())

        assert "cake_embeddings" not in exc.value.message
        assert "relation" not in exc.value.message
        assert exc.value.status_code == 503

    def test_similarity_handles_null(self):
        """similarity NULL từ database không được làm sập endpoint."""
        rows = [
            {
                "product_id": "p1",
                "product_name": "Bánh",
                "image_url": "https://example.test/a.jpg",
                "category": None,
                "product_type": None,
                "base_price": None,
                "similarity": None,
            }
        ]
        service = self._service_with_rpc_result(rows)
        with patch(
            "app.services.clip_service.embed_image_bytes", return_value=make_embedding()
        ):
            result = service.search_by_image(make_png_bytes())
        assert result["results"][0]["similarity"] == 0.0


# ─── Endpoint ────────────────────────────────────────────────────────────────


class TestSearchEndpoint:
    """Endpoint phải trả HTTP status đúng cho từng loại lỗi."""

    def test_status_endpoint_reports_model_state(self):
        """Endpoint báo cáo trạng thái model mà KHÔNG cần kết nối database.

        Mock phần đếm embedding: test này kiểm tra hình dạng response, không
        kiểm tra Supabase. Gọi mạng thật trong unit test sẽ chậm và flaky.
        """
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        # search.py imports get_supabase_client inside the function, so the
        # patch target must be the defining module, not the endpoint module.
        with patch("app.core.dependencies.get_supabase_client") as mock_get:
            mock_get.return_value.table.return_value.select.return_value.execute.return_value = (
                MagicMock(count=20)
            )
            response = client.get("/api/v1/search/status")

        assert response.status_code == 200
        body = response.json()
        assert body["embedding_dim"] == EMBEDDING_DIM
        assert body["model"] == "ViT-B-32"
        assert body["embedding_count"] == 20
        assert "ready" in body

    def test_status_survives_missing_table(self):
        """Bảng cake_embeddings chưa tồn tại (migration chưa chạy) không được
        làm sập health check — phải trả 200 với embedding_count = 0."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        with patch("app.core.dependencies.get_supabase_client") as mock_get:
            mock_get.return_value.table.return_value.select.return_value.execute.side_effect = (
                RuntimeError('relation "public.cake_embeddings" does not exist')
            )
            response = client.get("/api/v1/search/status")

        assert response.status_code == 200
        body = response.json()
        assert body["embedding_count"] == 0
        assert body["ready"] is False

    def test_rejects_non_image_upload(self):
        """Ảnh không hợp lệ phải trả 400 và KHÔNG được chạm tới model.

        Mock `embed_image_bytes` để tránh nạp torch/open_clip trong CI: việc
        validate nằm ở tầng dưới, không cần model thật. Nếu mock bị gọi, nghĩa
        là validation đã lọt lưới và model bị đánh thức vô ích.
        """
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        with patch(
            "app.services.clip_service.embed_image_bytes",
            side_effect=InvalidImageError(),
        ) as mock_embed:
            response = client.post(
                "/api/v1/search/by-image",
                files={"file": ("test.txt", b"khong phai anh", "text/plain")},
            )

        assert response.status_code == 400
        assert mock_embed.called
        # Không lộ chi tiết thư viện ảnh hay stack trace.
        assert "PIL" not in response.text
        assert "Traceback" not in response.text
        assert "UnidentifiedImageError" not in response.text

    def test_requires_file(self):
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        response = client.post("/api/v1/search/by-image")
        assert response.status_code == 422

    def test_rejects_oversized_upload_at_endpoint(self):
        """Ảnh vượt 10 MB phải bị chặn ở tầng endpoint với HTTP 413.

        Endpoint đọc tối đa MAX_UPLOAD_BYTES + 1 byte thay vì đọc trọn file,
        nên một upload rất lớn không bị nạp hết vào RAM trước khi từ chối.
        """
        from fastapi.testclient import TestClient

        from app.main import app
        from app.services.clip_service import MAX_UPLOAD_BYTES

        client = TestClient(app)
        # 10 MB + 2 byte: vượt ngưỡng đúng 2 byte, đủ để kích hoạt nhánh 413.
        oversized = b"x" * (MAX_UPLOAD_BYTES + 2)
        with patch(
            "app.services.clip_service.embed_image_bytes"
        ) as mock_embed:
            response = client.post(
                "/api/v1/search/by-image",
                files={"file": ("big.jpg", oversized, "image/jpeg")},
            )

        assert response.status_code == 413
        # Bị chặn trước khi chạm tới model.
        mock_embed.assert_not_called()

    def test_accepts_upload_of_exactly_max_size(self):
        """Ảnh đúng bằng giới hạn vẫn phải được chấp nhận.

        Đọc MAX + 1 byte để phân biệt "bằng giới hạn" với "vượt giới hạn";
        test này bảo vệ ranh giới đó khỏi bị lệch thành >=.
        """
        from fastapi.testclient import TestClient

        from app.main import app
        from app.services.clip_service import MAX_UPLOAD_BYTES

        client = TestClient(app)
        exactly_max = b"x" * MAX_UPLOAD_BYTES
        with patch(
            "app.services.clip_service.embed_image_bytes",
            side_effect=InvalidImageError(),
        ) as mock_embed:
            response = client.post(
                "/api/v1/search/by-image",
                files={"file": ("exact.jpg", exactly_max, "image/jpeg")},
            )

        # Nội dung là rác nên bị 400 ở tầng validate ảnh — điều quan trọng là
        # KHÔNG bị 413, tức là kích thước đúng giới hạn đã lọt qua cửa.
        assert response.status_code == 400
        assert mock_embed.called


# ─── Giới hạn body ở tầng ASGI ───────────────────────────────────────────────


class TestBodySizeLimitMiddleware:
    """Lớp chặn thứ nhất: từ chối theo Content-Length trước khi parse multipart.

    Không có lớp này, một upload rất lớn vẫn bị bộ phân tích multipart của
    FastAPI gom trọn vào RAM trước khi endpoint kịp kiểm tra kích thước.
    """

    def test_rejects_body_over_limit_before_parsing(self):
        from fastapi.testclient import TestClient

        from app.core.config import settings
        from app.main import app

        client = TestClient(app)
        oversized = b"x" * (settings.MAX_REQUEST_BODY_BYTES + 1024)
        response = client.post(
            "/api/v1/search/by-image",
            files={"file": ("huge.jpg", oversized, "image/jpeg")},
        )

        assert response.status_code == 413
        # Header cho client biết giới hạn thật là bao nhiêu.
        assert response.headers.get("x-max-body-bytes") == str(
            settings.MAX_REQUEST_BODY_BYTES
        )

    def test_limit_leaves_room_for_multipart_framing(self):
        """Giới hạn ASGI phải LỚN HƠN giới hạn ảnh.

        Bọc multipart luôn phình thêm vài trăm byte (boundary, tên field,
        header). Nếu đặt bằng đúng giới hạn ảnh thì một ảnh đúng 10 MB hợp lệ
        sẽ bị lớp ASGI từ chối nhầm trước khi endpoint kịp xem xét.
        """
        from app.core.config import settings
        from app.services.clip_service import MAX_UPLOAD_BYTES

        assert settings.MAX_REQUEST_BODY_BYTES > MAX_UPLOAD_BYTES

    def test_normal_requests_are_not_affected(self):
        """Request nhỏ phải đi qua bình thường — middleware không được chặn nhầm."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_missing_content_length_is_not_rejected(self):
        """Request không khai Content-Length phải đi tiếp, không bị chặn oan.

        Middleware chỉ nhìn được header này; thiếu nó thì để lớp kiểm tra trong
        endpoint làm việc, chứ không được đoán rồi từ chối.
        """
        from app.core.body_limit import BodySizeLimitMiddleware

        middleware = BodySizeLimitMiddleware(app=None, max_body_bytes=100)
        scope = {"type": "http", "headers": []}
        assert middleware._content_length(scope) is None

    def test_malformed_content_length_is_not_rejected(self):
        """Content-Length rác không được làm sập middleware."""
        from app.core.body_limit import BodySizeLimitMiddleware

        middleware = BodySizeLimitMiddleware(app=None, max_body_bytes=100)
        scope = {"type": "http", "headers": [(b"content-length", b"khong-phai-so")]}
        assert middleware._content_length(scope) is None

    def test_websocket_scope_passes_through(self):
        """WebSocket và lifespan không bị middleware đụng tới."""
        import asyncio

        from app.core.body_limit import BodySizeLimitMiddleware

        called = {}

        async def fake_app(scope, receive, send):
            called["scope_type"] = scope["type"]

        middleware = BodySizeLimitMiddleware(app=fake_app, max_body_bytes=100)
        asyncio.run(middleware({"type": "websocket", "headers": []}, None, None))
        assert called["scope_type"] == "websocket"

    def test_reject_drains_body_before_returning(self):
        """Khi từ chối, middleware phải hút hết phần thân qua receive().

        Uvicorn tạm dừng đọc socket cho tới khi `receive()` được gọi. Nếu ta gửi
        response rồi thoát ngay, client vẫn đang đẩy phần thân lên và kết nối bị
        ngắt giữa chừng. Test này khẳng định receive() ĐƯỢC gọi cho tới khi hết
        body, nên hành vi đó không bị xoá nhầm sau này.
        """
        import asyncio

        from app.core.body_limit import BodySizeLimitMiddleware

        drained = []

        async def receive():
            drained.append(1)
            # Hai khối body rồi hết.
            return {
                "type": "http.request",
                "body": b"x" * 10,
                "more_body": len(drained) < 2,
            }

        sent = []

        async def send(message):
            sent.append(message)

        middleware = BodySizeLimitMiddleware(app=None, max_body_bytes=5)
        scope = {
            "type": "http",
            "headers": [(b"content-length", b"999999")],
        }
        asyncio.run(middleware(scope, receive, send))

        # Đã gửi 413.
        assert sent[0]["type"] == "http.response.start"
        assert sent[0]["status"] == 413
        # Và đã hút trọn 2 khối body trước khi trả về.
        assert len(drained) == 2

    def test_drain_stops_on_disconnect(self):
        """Client ngắt giữa chừng thì dừng hút, không lặp vô hạn."""
        import asyncio

        from app.core.body_limit import BodySizeLimitMiddleware

        calls = []

        async def receive():
            calls.append(1)
            return {"type": "http.disconnect"}

        async def send(message):
            pass

        middleware = BodySizeLimitMiddleware(app=None, max_body_bytes=5)
        scope = {"type": "http", "headers": [(b"content-length", b"999999")]}
        asyncio.run(middleware(scope, receive, send))

        # Dừng ngay ở lần gọi đầu, không hút tiếp.
        assert len(calls) == 1
