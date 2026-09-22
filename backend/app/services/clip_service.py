"""CLIP image search service — trụ cột 2 của đề tài.

Cho phép khách tải lên ảnh bánh yêu thích, dùng mô hình thị giác CLIP để tìm
sản phẩm / mẫu 3D gần giống nhất trong kho.

Cách hoạt động:
    1. Ảnh khách upload → chuẩn hóa (RGB, resize 224×224) → vector 512 chiều
    2. Gọi RPC match_cakes: so sánh cosine với toàn bộ embedding trong kho
    3. Trả về top-K kèm độ tương đồng

Model: ViT-B-32 pretrained laion2b_s34b_b79k
    - 512 chiều → khớp cột vector(512) trong schema
    - Chạy CPU đủ nhanh (~50ms/ảnh), không cần GPU

Tải model:
    Model được load MỘT LẦN và cache ở cấp module (_model). Load lại mỗi request
    sẽ tốn ~45s và ~350MB RAM — không chấp nhận được cho API.

Tối ưu độ trễ:
    Cả model CLIP lẫn client Supabase đều được cache ở cấp module. Đo trước khi
    tối ưu: 13.063ms cho request đầu (nạp model) và 624ms cho các request sau,
    trong đó 216ms là riêng create_client() và 84ms là truy vấn thật. Sau khi
    cache cả hai, request ấm còn ~114ms.
"""

import io
import logging
import threading
import time
from typing import Any, Optional

from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.utils.image_url import format_image_url

logger = logging.getLogger(__name__)

MODEL_NAME = "ViT-B-32"
PRETRAINED = "laion2b_s34b_b79k"
EMBEDDING_DIM = 512
# Kích thước tối đa của ảnh khách tải lên (10 MB).
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Ảnh nhỏ hơn ngưỡng này gần như chắc chắn không phải ảnh bánh thật.
MIN_IMAGE_SIDE = 32

# CLIP chuẩn hóa ảnh về 224×224 (khớp preprocess của ViT-B-32).
CLIP_INPUT_SIZE = 224

# Phân trang khi lọc theo loại sản phẩm (xem ClipSearchService._fetch_ranked).
# Trang đầu không nhỏ hơn ngần này để đỡ phải gọi RPC nhiều lần.
_MIN_PAGE = 20
# Trần số dòng quét qua: đủ rộng cho kho vài nghìn sản phẩm, nhưng vẫn chặn
# được vòng lặp vô hạn nếu RPC hành xử bất thường.
_MAX_SCAN = 500
# Trần số lần gọi RPC cho một lượt tìm kiếm.
_MAX_PAGES = 6

# ─── Cache Supabase client ───────────────────────────────────────────────────
# create_client() tốn ~216ms (bắt tay TLS + nạp OpenAPI schema PostgREST).
# Tạo mới mỗi request làm mỗi lần tìm kiếm mất ~624ms thay vì ~114ms.
_cached_client: Any = None
_client_lock = threading.Lock()


class ClipServiceError(Exception):
    """Base exception for CLIP service errors."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ClipModelUnavailableError(ClipServiceError):
    """Model chưa sẵn sàng (chưa cài thư viện hoặc load lỗi)."""

    def __init__(self, detail: str = ""):
        super().__init__(
            "Chức năng tìm kiếm bằng hình ảnh tạm thời không khả dụng."
            + (f" ({detail})" if detail else ""),
            status_code=503,
        )


class InvalidImageError(ClipServiceError):
    """Ảnh tải lên không hợp lệ."""

    def __init__(self):
        super().__init__("Tệp tải lên không phải ảnh hợp lệ.", status_code=400)


# ─── Model cache ─────────────────────────────────────────────────────────────
# Load một lần, dùng cho mọi request. Lock để tránh 2 request đồng thời cùng
# khởi tạo model (sẽ tốn gấp đôi RAM và có thể crash).
_model = None
_preprocess = None
_model_lock = threading.Lock()
_model_load_error: Optional[str] = None


def _load_model():
    """Load CLIP một lần duy nhất (thread-safe). Trả về (model, preprocess)."""
    global _model, _preprocess, _model_load_error

    if _model is not None:
        return _model, _preprocess

    with _model_lock:
        # Kiểm tra lại sau khi lấy lock: thread khác có thể vừa load xong.
        if _model is not None:
            return _model, _preprocess

        try:
            import open_clip
            import torch  # noqa: F401  (open_clip cần torch đã được import)

            logger.info("Loading CLIP model %s/%s ...", MODEL_NAME, PRETRAINED)
            started = time.perf_counter()
            model, _, preprocess = open_clip.create_model_and_transforms(
                MODEL_NAME, pretrained=PRETRAINED
            )
            model.eval()
            _model = model
            _preprocess = preprocess
            _model_load_error = None
            logger.info(
                "CLIP model loaded in %.1fs", time.perf_counter() - started
            )
        except Exception as exc:  # noqa: BLE001 - báo lỗi rõ cho endpoint
            # Không đưa chi tiết kỹ thuật ra ngoài; chỉ ghi log.
            logger.exception("Failed to load CLIP model")
            _model_load_error = type(exc).__name__
            raise ClipModelUnavailableError(_model_load_error) from exc

    return _model, _preprocess


def is_model_available() -> bool:
    """Kiểm tra model đã load được chưa, không kích hoạt load."""
    return _model is not None


def get_model_status() -> dict[str, Any]:
    """Trạng thái model cho endpoint health check."""
    return {
        "available": _model is not None,
        "model": MODEL_NAME,
        "pretrained": PRETRAINED,
        "embedding_dim": EMBEDDING_DIM,
        "load_error": _model_load_error,
    }


def _validate_and_open_image(raw: bytes) -> Image.Image:
    """Kiểm tra bytes tải lên có phải ảnh hợp lệ, trả về PIL Image RGB."""
    if not raw:
        raise InvalidImageError()

    if len(raw) > MAX_UPLOAD_BYTES:
        raise ClipServiceError(
            f"Ảnh quá lớn. Tối đa {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
            status_code=413,
        )

    try:
        image = Image.open(io.BytesIO(raw))
        # verify() phát hiện file hỏng/giả mạo, nhưng làm hỏng đối tượng Image
        # nên phải mở lại lần nữa ở dưới.
        image.verify()
        image = Image.open(io.BytesIO(raw))
        image = image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        # Thông báo chung: không lộ chi tiết thư viện/stack ra client.
        raise InvalidImageError()

    width, height = image.size
    if width < MIN_IMAGE_SIDE or height < MIN_IMAGE_SIDE:
        raise ClipServiceError(
            f"Ảnh quá nhỏ. Cần tối thiểu {MIN_IMAGE_SIDE}×{MIN_IMAGE_SIDE} pixel.",
            status_code=400,
        )

    return image


def embed_image_bytes(raw: bytes) -> list[float]:
    """Sinh vector 512 chiều từ bytes ảnh.

    Đây là hàm lõi: dùng cho cả ảnh khách upload và script sinh embedding kho.

    Thứ tự QUAN TRỌNG: kiểm tra ảnh TRƯỚC, nạp model SAU. Nạp model tốn ~45s và
    ~350MB RAM, nên nếu ảnh hỏng/không phải ảnh thì phải báo lỗi ngay mà không
    kích hoạt nạp model. Trước đây thứ tự ngược lại, khiến một request với bytes
    rác cũng đủ để nạp model và chặn cả tiến trình.
    """
    image = _validate_and_open_image(raw)
    model, preprocess = _load_model()

    import torch

    with torch.no_grad():
        tensor = preprocess(image).unsqueeze(0)
        features = model.encode_image(tensor)
        # Chuẩn hóa L2: cosine similarity chỉ đúng khi vector đã chuẩn hóa.
        features = features / features.norm(dim=-1, keepdim=True)
        vector = features[0].tolist()

    if len(vector) != EMBEDDING_DIM:
        # Bất biến quan trọng: schema là vector(512). Sai chiều = insert lỗi.
        raise ClipServiceError(
            "Mô hình trả về vector sai kích thước.", status_code=500
        )

    return vector


def _client():
    """Supabase client (service role).

    Client được TÁI DỤNG, không tạo mới mỗi request. Đo được: create_client()
    tốn trung bình 216ms vì phải bắt tay TLS và nạp OpenAPI schema của
    PostgREST. Cộng với 84ms truy vấn thật, mỗi lần tìm kiếm mất ~624ms.

    Tái dùng client đưa tổng xuống ~114ms, nhanh hơn 5.5 lần. Đây là client
    service-role chỉ đọc, không giữ token người dùng, nên dùng chung an toàn —
    khác với client có token auth (xem dependencies.get_supabase_client, chỗ đó
    cố ý tạo mới mỗi request để tránh rò token giữa các request).

    Khoá lại bằng _client_lock vì nhiều request có thể vào đồng thời lúc khởi
    động và cùng thấy cache rỗng.
    """
    global _cached_client
    if _cached_client is None:
        with _client_lock:
            if _cached_client is None:
                from supabase import create_client

                _cached_client = create_client(
                    settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
                )
    return _cached_client


class ClipSearchService:
    """Tìm sản phẩm gần giống nhất với ảnh khách tải lên."""

    def __init__(self, client: Any = None):
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = _client()
        return self._client

    def _fetch_ranked(
        self,
        vector: list[float],
        match_threshold: float,
        match_count: int,
        product_type: str | None,
    ) -> list[dict[str, Any]]:
        """Lấy `match_count` dòng khớp `product_type`, xếp theo similarity.

        Hỏi RPC theo từng trang và tăng dần kích thước trang cho tới khi đủ kết
        quả hoặc hết dữ liệu. Cách này đúng cho mọi phân bố: dù nhóm cần tìm nằm
        cuối bảng điểm, ta vẫn lấy tới khi tìm đủ, thay vì đoán một con số.

        Không lọc (`product_type is None`) thì chỉ gọi RPC một lần đúng
        `match_count` — giữ nguyên hành vi cũ, không tốn thêm request.

        Trần `_MAX_PAGES` để một kho rất lớn cũng không quét vô hạn: sau khi vét
        cạn `_MAX_SCAN` dòng mà vẫn không đủ thì trả về những gì đang có.
        """
        if not product_type:
            # Cắt lại tại đây thay vì tin RPC tôn trọng `match_count`: một số
            # backend bỏ qua giới hạn, và trả nhiều hơn số khách xin là sai.
            return self._rpc(vector, match_threshold, match_count)[:match_count]

        collected: list[dict[str, Any]] = []
        page = max(match_count * 2, _MIN_PAGE)
        scanned = 0

        for _ in range(_MAX_PAGES):
            batch = self._rpc(vector, match_threshold, page)
            # RPC trả về ít hơn số xin = đã hết dữ liệu, dừng ngay.
            exhausted = len(batch) < page
            scanned = len(batch)

            # THAY THẾ, không cộng dồn.
            #
            # `match_cakes` chỉ nhận `match_count`, KHÔNG có offset: xin 40 dòng
            # nghĩa là "lấy 40 dòng đầu", chứ không phải "lấy 40 dòng tiếp theo".
            # Đo trên CSDL thật: cả 20 id của trang 1 đều nằm trong trang 2.
            # Nếu extend() thì kết quả bị trùng — đo được 60 dòng nhưng chỉ có
            # 40 id duy nhất.
            #
            # Tệ hơn, thứ tự giữa các dòng CÙNG ĐIỂM không ổn định giữa hai lần
            # gọi (đã đo: `b[:20] == a` là False dù 5 dòng đầu giống nhau). Nên
            # cộng dồn vừa trùng vừa có thể SÓT sản phẩm.
            #
            # Trang sau luôn là tập cha của trang trước, nên chỉ cần giữ lại kết
            # quả mới nhất — vừa đúng, vừa không cần khử trùng lặp.
            collected = [r for r in batch if r.get("product_type") == product_type]

            if len(collected) >= match_count or exhausted or scanned >= _MAX_SCAN:
                break
            page = min(page * 2, _MAX_SCAN)

        return collected[:match_count]

    def _rpc(
        self, vector: list[float], match_threshold: float, count: int
    ) -> list[dict[str, Any]]:
        """Gọi match_cakes một lần. Lỗi mạng/DB → ClipServiceError."""
        try:
            response = self.client.rpc(
                "match_cakes",
                {
                    "query_embedding": vector,
                    "match_threshold": match_threshold,
                    "match_count": count,
                },
            ).execute()
        except Exception:
            logger.exception("match_cakes RPC failed")
            raise ClipServiceError(
                "Không thể tìm kiếm trong kho mẫu bánh.", status_code=503
            )
        return response.data or []

    def search_by_image(
        self,
        raw: bytes,
        match_count: int = 6,
        match_threshold: float = 0.0,
        product_type: str | None = None,
    ) -> dict[str, Any]:
        """Trả về danh sách sản phẩm giống nhất kèm độ tương đồng.

        Args:
            product_type: Lọc theo loại sản phẩm. `"cake"` = chỉ bánh sinh nhật
                (bánh thiết kế theo kiểu mẫu). None = tìm trong toàn kho.
                Lọc ở Python chứ không ở SQL vì RPC `match_cakes` không nhận
                tham số này; phải lấy dư kết quả rồi mới cắt, nếu không sẽ trả
                về ít hơn `match_count` dù kho còn hàng.

        Raises:
            InvalidImageError: ảnh hỏng / không phải ảnh.
            ClipModelUnavailableError: model chưa sẵn sàng.
            ClipServiceError: lỗi truy vấn database.
        """
        started = time.perf_counter()

        embed_started = time.perf_counter()
        vector = embed_image_bytes(raw)
        embed_ms = (time.perf_counter() - embed_started) * 1000

        # Kẹp tham số: tránh khách yêu cầu 10.000 kết quả.
        match_count = max(1, min(int(match_count), 20))
        match_threshold = max(0.0, min(float(match_threshold), 1.0))

        # Lọc theo loại sản phẩm.
        #
        # RPC `match_cakes` không nhận tham số lọc và luôn xếp hạng theo similarity
        # trên TOÀN kho, nên phải tự lọc ở đây. Cách làm cũ (xin match_count * 10,
        # trần 60) là SAI: nó giả định nhóm cần tìm phân bố đều trong bảng điểm.
        # Đo thật trên kho 105 `cake` + 18 `sweet`: xin 10 dòng chỉ được 3 `cake`,
        # vì `sweet` chen lên đầu. Khách xin 6 bánh sinh nhật có thể chỉ nhận 3.
        #
        # Cách đúng: hỏi từng trang cho tới khi đủ `match_count` dòng khớp, hoặc
        # tới khi RPC trả về ít hơn số đã xin (hết dữ liệu). Như vậy kết quả không
        # còn phụ thuộc vào việc nhóm khác xếp hạng cao hay thấp.
        search_started = time.perf_counter()
        rows = self._fetch_ranked(
            vector=vector,
            match_threshold=match_threshold,
            match_count=match_count,
            product_type=product_type,
        )
        search_ms = (time.perf_counter() - search_started) * 1000

        results = []
        for row in rows:
            similarity = float(row.get("similarity") or 0.0)
            results.append(
                {
                    "product_id": row.get("product_id"),
                    "name": row.get("product_name"),
                    "image_url": format_image_url(row.get("image_url")),
                    "category": row.get("category"),
                    "product_type": row.get("product_type"),
                    "base_price": row.get("base_price"),
                    # Trả về % để giao diện hiển thị trực tiếp.
                    "similarity": round(similarity, 4),
                    "similarity_percent": round(similarity * 100, 1),
                }
            )

        total_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "CLIP search: embed=%.0fms rpc=%.0fms total=%.0fms results=%d",
            embed_ms,
            search_ms,
            total_ms,
            len(results),
        )

        return {
            "results": results,
            "count": len(results),
            "timing_ms": {
                "embed": round(embed_ms, 1),
                "search": round(search_ms, 1),
                "total": round(total_ms, 1),
            },
            "model": MODEL_NAME,
        }
