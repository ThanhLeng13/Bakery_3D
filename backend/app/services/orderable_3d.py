"""Mẫu 3D nào được phép bán.

Quyết định nghiệp vụ 07/10/2026: trong sáu mẫu thân bánh chỉ `round-1-tier` và
`round-2-tier` được bán. `round-3-tier`, `heart-1-tier`, `square-1-tier` và
`tall-1-tier` chỉ xem trong demo, vì chưa có giá và lead time được duyệt để sản
xuất.

Vì sao nằm ở backend
-------------------
Trước đây quy tắc này không tồn tại ở đâu cả: bảng `cake_3d_models` không có cột
phân biệt "xem được" và "bán được", nên hai sản phẩm hình tim vẫn bán được với
mẫu `heart-1-tier`. Chỉ ẩn nút ở giao diện thì gọi thẳng API vẫn tạo đơn được.
Ràng buộc phải ở server.

Cách mở bán thêm mẫu
--------------------
1. Bổ sung giá và lead time cho mẫu trong bảng sản phẩm.
2. Thêm slug vào `ORDERABLE_MODEL_SLUGS`.
3. Thêm ca kiểm thử tương ứng trong `tests/test_orderable_3d.py`.

Các slug ở đây là khoá của `cake_3d_models.slug`, không phải tên hiển thị.
"""

ORDERABLE_MODEL_SLUGS: tuple[str, ...] = (
    "round-1-tier",
    "round-2-tier",
)

PREVIEW_ONLY_REASON = (
    "Mẫu này hiện chỉ xem trong demo, chưa mở bán vì giá và thời gian chuẩn bị "
    "chưa được duyệt. Bạn có thể chọn mẫu bánh tròn 1 tầng hoặc 2 tầng."
)


class OrderableModelError(Exception):
    """Sản phẩm dùng mẫu 3D chưa được phép bán."""

    def __init__(self, slug: str, status_code: int = 400):
        message = f"Mẫu '{slug}' chưa mở bán. {PREVIEW_ONLY_REASON}"
        super().__init__(message)
        self.message = message
        self.slug = slug
        self.status_code = status_code


def normalize_slug(slug) -> str:
    if not isinstance(slug, str):
        return ""
    return slug.strip().lower()


def is_orderable_model(slug) -> bool:
    """True khi mẫu 3D này được phép đặt hàng."""
    return normalize_slug(slug) in ORDERABLE_MODEL_SLUGS


def ensure_orderable_model(slug) -> str | None:
    """Trả về slug đã chuẩn hóa, hoặc ném lỗi nếu mẫu chỉ để xem.

    Sản phẩm không gắn mẫu 3D nào trả về None và không bị chặn — đó là sản
    phẩm thường, không liên quan tới kho mô hình.

    Raises:
        OrderableModelError: mẫu tồn tại nhưng chưa được phép bán.
    """
    clean = normalize_slug(slug)
    if not clean:
        return None
    if clean not in ORDERABLE_MODEL_SLUGS:
        raise OrderableModelError(clean)
    return clean