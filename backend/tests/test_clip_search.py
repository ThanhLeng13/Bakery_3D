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


class TestProductTypeFilter:
    """Lọc kết quả theo loại sản phẩm.

    Mặc định chỉ tìm bánh sinh nhật (`cake`), vì đó là nhóm khách tìm theo kiểu
    mẫu. Lọc sai chỗ này sẽ khiến khách tìm bánh sinh nhật nhưng nhận về
    tiramisu, mà test cũ vẫn xanh vì endpoint vẫn trả 200.
    """

    @staticmethod
    def _fake_rows():
        """Giả lập match_cakes trả về lẫn lộn cake và sweet, xếp theo similarity."""
        rows = []
        # sweet có similarity cao hơn — đây chính là ca dễ lọc nhầm.
        for i in range(6):
            rows.append({
                "product_id": f"sweet-{i}",
                "product_name": f"Bánh ngọt {i}",
                "image_url": None,
                "category": "bánh ngọt",
                "product_type": "sweet",
                "base_price": 50000,
                "similarity": 0.9 - i * 0.01,
            })
        for i in range(6):
            rows.append({
                "product_id": f"cake-{i}",
                "product_name": f"Bánh kem {i}",
                "image_url": None,
                "category": "bánh âu",
                "product_type": "cake",
                "base_price": 350000,
                "similarity": 0.7 - i * 0.01,
            })
        return rows

    def _run(self, product_type):
        from unittest.mock import MagicMock

        from app.services.clip_service import ClipSearchService

        fake_client = MagicMock()
        fake_client.rpc.return_value.execute.return_value.data = self._fake_rows()
        service = ClipSearchService(client=fake_client)

        with patch(
            "app.services.clip_service.embed_image_bytes",
            return_value=[0.0] * 512,
        ):
            result = service.search_by_image(
                b"x", match_count=4, product_type=product_type
            )
        # Tham số đã truyền cho RPC — cần biết đã xin dư kết quả chưa.
        rpc_args = fake_client.rpc.call_args[0]
        return result, rpc_args

    def test_filters_to_cake_only(self):
        """product_type='cake' chỉ trả về bánh kem, dù sweet có điểm cao hơn."""
        result, _ = self._run("cake")

        assert result["count"] == 4
        assert all(r["product_type"] == "cake" for r in result["results"])
        # Và phải là những cái điểm cao nhất TRONG nhóm cake.
        assert result["results"][0]["name"] == "Bánh kem 0"

    def test_filters_to_sweet_only(self):
        result, _ = self._run("sweet")

        assert result["count"] == 4
        assert all(r["product_type"] == "sweet" for r in result["results"])

    def test_no_filter_returns_everything(self):
        """product_type=None tìm toàn kho, không lọc."""
        result, _ = self._run(None)

        assert result["count"] == 4
        # Không lọc thì sweet điểm cao nhất phải đứng đầu.
        assert result["results"][0]["product_type"] == "sweet"

    def test_filter_requests_extra_rows_from_rpc(self):
        """Khi lọc, phải xin RPC nhiều hơn match_count.

        Nếu chỉ xin đúng match_count rồi lọc ở Python, kho mà nhóm cần tìm nằm
        cuối bảng điểm sẽ trả về ít hơn số khách yêu cầu — có khi rỗng — dù kho
        còn hàng.
        """
        _, rpc_args = self._run("cake")

        assert rpc_args[0] == "match_cakes"
        assert rpc_args[1]["match_count"] > 4, "phai xin du de sau khi loc con du"

    def test_filter_pages_until_enough(self):
        """Phải lấy đủ kết quả dù nhóm khác xếp hạng cao hơn hẳn.

        Đây là lỗi đã đo được trên kho thật: xin 10 dòng từ match_cakes chỉ nhận
        về 3 dòng `cake`, vì `sweet` chen lên đầu bảng điểm. Cách cũ (xin
        match_count * 10 rồi lọc) khiến khách xin 6 bánh sinh nhật chỉ nhận 3.

        Mock ở đây mô phỏng ĐÚNG hành vi thật của match_cakes: RPC không có
        offset, nên trang sau là TẬP CHA của trang trước (20 dòng đầu giống hệt,
        chỉ thêm dòng mới ở cuối). Nếu mock trả về tập hoàn toàn khác thì test sẽ
        không phát hiện được lỗi cộng dồn trùng lặp.
        """
        from unittest.mock import MagicMock, patch

        from app.services.clip_service import ClipSearchService

        def row(prefix, group, score):
            return {
                "product_id": f"{prefix}", "product_name": f"{group} {prefix}",
                "product_type": group, "similarity": score,
                "base_price": 1, "category": "x", "image_url": None,
            }

        # Trang 1 (20 dòng): 3 `cake` ở đầu rồi toàn `sweet`. Có sẵn `cake` ngay
        # từ trang 1 để CẢ HAI trang đều đóng góp kết quả khớp — nếu không, phép
        # cộng dồn trùng lặp sẽ không lộ ra.
        page1 = ([row(f"c{i}", "cake", 0.9 - i * 0.01) for i in range(3)]
                 + [row(f"s{i}", "sweet", 0.5 - i * 0.01) for i in range(17)])

        fake_client = MagicMock()
        # Trang 2 (40 dòng) = trang 1 + 20 dòng `cake` nữa ở cuối. Đây là
        # superset, giống hệt cách match_cakes trả về khi xin nhiều hơn.
        page2 = page1 + [row(f"d{i}", "cake", 0.4 - i * 0.01) for i in range(20)]
        fake_client.rpc.return_value.execute.side_effect = [
            MagicMock(data=page1),
            MagicMock(data=page2),
            MagicMock(data=page2),
            MagicMock(data=page2),
        ]
        service = ClipSearchService(client=fake_client)

        with patch("app.services.clip_service.embed_image_bytes", return_value=[0.0] * 512):
            result = service.search_by_image(b"x", match_count=10, product_type="cake")

        assert result["count"] == 10, "phai lay du ket qua du nhom khac xep truoc"
        assert all(r["product_type"] == "cake" for r in result["results"])
        assert fake_client.rpc.call_count >= 2, "phai goi lai RPC chu khong bo cuoc"

        # Không được trùng: trang 2 là superset của trang 1, nên cộng dồn sẽ cho
        # ra cùng một sản phẩm nhiều lần ('c0'..'c2' xuất hiện ở cả hai trang).
        ids = [r["product_id"] for r in result["results"]]
        assert len(ids) == len(set(ids)), f"ket qua bi trung: {ids}"

    def test_filter_stops_when_rpc_exhausted(self):
        """RPC hết dữ liệu thì dừng, không gọi lặp vô hạn."""
        from unittest.mock import MagicMock, patch

        from app.services.clip_service import ClipSearchService

        fake_client = MagicMock()
        # Trả về ít hơn số xin -> hết dữ liệu.
        fake_client.rpc.return_value.execute.return_value = MagicMock(
            data=[{"product_id": "s1", "product_name": "Ngọt", "product_type": "sweet",
                   "similarity": 0.9, "base_price": 1, "category": "x", "image_url": None}]
        )
        service = ClipSearchService(client=fake_client)
        with patch("app.services.clip_service.embed_image_bytes", return_value=[0.0] * 512):
            result = service.search_by_image(b"x", match_count=5, product_type="cake")

        assert result["count"] == 0
        assert fake_client.rpc.call_count == 1

    def test_unfiltered_result_is_capped(self):
        """Không lọc vẫn phải cắt đúng match_count dù RPC trả nhiều hơn."""
        from unittest.mock import MagicMock, patch

        from app.services.clip_service import ClipSearchService

        fake_client = MagicMock()
        fake_client.rpc.return_value.execute.return_value = MagicMock(
            data=[{"product_id": f"p{i}", "product_name": f"Bánh {i}",
                   "product_type": "sweet", "similarity": 0.9, "base_price": 1,
                   "category": "x", "image_url": None} for i in range(30)]
        )
        service = ClipSearchService(client=fake_client)
        with patch("app.services.clip_service.embed_image_bytes", return_value=[0.0] * 512):
            result = service.search_by_image(b"x", match_count=4, product_type=None)

        assert result["count"] == 4, "khong duoc tra nhieu hon so khach xin"

    def test_filter_does_not_overfetch_when_unfiltered(self):
        """Không lọc thì không xin dư — tránh kéo cả kho vô ích."""
        _, rpc_args = self._run(None)

        assert rpc_args[1]["match_count"] == 4

    def test_filter_returns_empty_when_no_match(self):
        """Lọc ra nhóm không có sản phẩm nào thì trả rỗng, không lỗi."""
        result, _ = self._run("khong-ton-tai")

        assert result["count"] == 0
        assert result["results"] == []

    def test_endpoint_defaults_to_cake(self):
        """Endpoint phải mặc định lọc bánh sinh nhật."""
        import inspect

        from fastapi.params import Form

        from app.api.v1.endpoints.search import search_by_image

        sig = inspect.signature(search_by_image)
        default = sig.parameters["product_type"].default
        # FastAPI bọc giá trị mặc định trong Form(...), nên phải lấy .default
        # chứ không so trực tiếp với chuỗi.
        assert isinstance(default, Form)
        assert default.default == "cake", "mac dinh phai la banh sinh nhat"

    def test_endpoint_treats_all_as_no_filter(self):
        """'all' nghĩa là không lọc; chuỗi rỗng KHÔNG có nghĩa đó.

        FastAPI coi chuỗi rỗng như field không được gửi và thay bằng mặc định
        "cake". Hành vi này đã kiểm chứng, nên test ghi lại đúng như thật thay
        vì mong đợi điều không xảy ra.
        """
        from unittest.mock import patch as _patch

        from fastapi.testclient import TestClient

        from app.main import app
        from app.services.clip_service import ClipSearchService

        captured = {}

        def fake_search(self, raw, match_count=6, match_threshold=0.0, product_type=None):
            captured["product_type"] = product_type
            return {"results": [], "count": 0, "timing_ms": {}, "model": "test"}

        client = TestClient(app)
        with _patch.object(ClipSearchService, "search_by_image", fake_search), \
             _patch("app.services.clip_service.embed_image_bytes", return_value=[0.0] * 512):
            # "all" -> không lọc
            client.post("/api/v1/search/by-image",
                        files={"file": ("t.jpg", b"x" * 100, "image/jpeg")},
                        data={"product_type": "all"})
            assert captured["product_type"] is None

            # Không gửi -> mặc định bánh sinh nhật
            client.post("/api/v1/search/by-image",
                        files={"file": ("t.jpg", b"x" * 100, "image/jpeg")})
            assert captured["product_type"] == "cake"

            # "sweet" -> lọc bánh ngọt
            client.post("/api/v1/search/by-image",
                        files={"file": ("t.jpg", b"x" * 100, "image/jpeg")},
                        data={"product_type": "sweet"})
            assert captured["product_type"] == "sweet"

    def test_filter_actually_reaches_service(self):
        """Lọc phải đi tới tận service, không bị nuốt ở tầng endpoint."""
        from unittest.mock import MagicMock, patch as _patch

        from app.services.clip_service import ClipSearchService

        fake_client = MagicMock()
        # Trả về lẫn lộn để chắc chắn việc lọc có tác dụng.
        fake_client.rpc.return_value.execute.return_value.data = [
            {"product_id": "s1", "product_name": "Ngọt", "product_type": "sweet",
             "similarity": 0.9, "base_price": 1, "category": "x", "image_url": None},
            {"product_id": "c1", "product_name": "Kem", "product_type": "cake",
             "similarity": 0.8, "base_price": 2, "category": "y", "image_url": None},
        ]
        service = ClipSearchService(client=fake_client)
        with _patch("app.services.clip_service.embed_image_bytes", return_value=[0.0] * 512):
            result = service.search_by_image(b"x", match_count=5, product_type="cake")

        assert result["count"] == 1
        assert result["results"][0]["name"] == "Kem"

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


class TestBodySizeLimitStreaming:
    """Lớp chặn thứ hai: đếm byte thật, bắt được chunked và Content-Length giả.

    Đây là lớp bắt buộc, không phải phòng xa. Đo trên server thật trước khi có
    nó: một request chunked 30 MB lọt hoàn toàn qua lớp 1, bị bộ phân tích
    multipart gom trọn vào RAM, rồi mới bị endpoint từ chối.
    """

    @staticmethod
    def _run(max_body_bytes, chunks):
        """Chạy middleware với các khối body cho trước. Trả (app_received, status)."""
        import asyncio

        from app.core.body_limit import BodySizeLimitMiddleware

        seen = {"total": 0}

        async def fake_app(scope, receive, send):
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    break
                seen["total"] += len(message.get("body", b""))
                if not message.get("more_body", False):
                    break
            await send(
                {"type": "http.response.start", "status": 200, "headers": []}
            )
            await send({"type": "http.response.body", "body": b"{}"})

        queue = list(chunks)

        async def receive():
            if queue:
                return {"type": "http.request", "body": queue.pop(0), "more_body": True}
            return {"type": "http.request", "body": b"", "more_body": False}

        sent = []

        async def send(message):
            sent.append(message)

        middleware = BodySizeLimitMiddleware(app=fake_app, max_body_bytes=max_body_bytes)
        # KHÔNG có content-length -> chỉ lớp 2 bắt được.
        asyncio.run(middleware({"type": "http", "headers": []}, receive, send))

        status = sent[0].get("status") if sent else None
        return seen["total"], status

    def test_chunked_body_over_limit_is_cut_and_rejected(self):
        """Chunked vượt ngưỡng: ứng dụng chỉ nhận tới ngưỡng, và trả 413."""
        limit = 100 * 1024
        received, status = self._run(limit, [b"x" * 65536] * 30)

        assert status == 413
        # Ứng dụng không bao giờ thấy quá ngưỡng.
        assert received <= limit
        # Và thực sự ít hơn nhiều so với 30 khối (1.9 MB).
        assert received < 30 * 65536

    def test_body_under_limit_passes_through_untouched(self):
        """Body dưới ngưỡng: ứng dụng nhận đủ, status giữ nguyên 200."""
        received, status = self._run(100 * 1024, [b"x" * 51200])

        assert status == 200
        assert received == 51200

    def test_body_exactly_at_limit_passes(self):
        """Đúng bằng ngưỡng thì phải lọt qua (ranh giới không được lệch thành >)."""
        limit = 100 * 1024
        received, status = self._run(limit, [b"x" * 51200, b"y" * 51200])

        assert status == 200
        assert received == limit

    def test_body_one_byte_over_limit_is_rejected(self):
        """Nhích qua ngưỡng đúng 1 byte cũng phải bị chặn."""
        limit = 100 * 1024
        received, status = self._run(limit, [b"x" * limit, b"y"])

        assert status == 413
        assert received <= limit

    def test_413_response_replaces_application_response(self):
        """413 phải thay thế response của ứng dụng, không bị response đó ghi đè.

        Ứng dụng vẫn chạy tiếp sau khi body bị cắt và gửi 200 của nó. Nếu
        middleware chuyển tiếp ngay thì client đã nhận 200 và không thể sửa nữa —
        ASGI chỉ cho gửi http.response.start một lần.
        """
        received, status = self._run(100 * 1024, [b"x" * 65536] * 5)

        assert status == 413, "response cua ung dung (200) da ghi de mat 413"

    def test_many_small_chunks_accumulate(self):
        """Nhiều khối nhỏ cộng lại vượt ngưỡng vẫn phải bị bắt.

        Nếu chỉ so từng khối với ngưỡng thì trường hợp này lọt.
        """
        limit = 10 * 1024
        received, status = self._run(limit, [b"x" * 1024] * 50)

        assert status == 413
        assert received <= limit
