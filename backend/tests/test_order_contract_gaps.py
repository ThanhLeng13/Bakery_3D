"""Ba lỗi hợp đồng đơn hàng đã đo được, giữ lại làm regression.

1. `check_bake_time` khai schema chỉ có `name`/`size`, nhưng `pricing` phân biệt
   mẫu làm sẵn bằng `cake_id`/`product_id`. LLM tuân theo schema nên không bao
   giờ gửi ID, và mọi mẫu làm sẵn — kể cả bánh hai tầng đã có sẵn — bị tính
   thành bánh đặt (48 giờ). Test cũ vẫn xanh vì nó tự nhét `cake_id` vào tham
   số, tức kiểm code chứ không kiểm đường thật mà LLM đi.

2. Checkout kiểm thời gian theo `item["size"]` rời, còn tính giá theo
   `customization_json["size"]`. Hai nguồn khác nhau nên thiết kế đã lưu là
   2 tầng mà gửi kèm `size: "20cm"` vẫn qua cửa 24 giờ trong khi tiền tính
   theo bánh hai tầng.

3. Trợ lý có thể tạo đơn nháp cho sản phẩm chỉ có mô hình xem trước, trong khi
   checkout chặn đúng sản phẩm đó — hai đường vào cùng một đơn cho hai kết quả.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.order_service import OrderService, PickupDateValidationError
from app.services.order_tools import TOOL_SCHEMAS

VN_TZ = timezone(timedelta(hours=7))
NIL_UUID = "00000000-0000-0000-0000-000000000000"


def _items_schema(tool_name: str) -> dict:
    tool = next(
        t for t in TOOL_SCHEMAS if t["function"]["name"] == tool_name
    )
    return tool["function"]["parameters"]["properties"]["items"]


def _item_properties(tool_name: str) -> dict:
    """Thuộc tính của TỪNG món trong mảng `items` của công cụ.

    `items` bọc qua `_nullable`, hàm đó giữ nguyên cú pháp và chỉ đổi
    `type` thành `["array", "null"]`, nên schema từng món vẫn nằm ở
    `properties.items.properties`. Đọc đúng đường đó thay vì đoán.
    """
    spec = _items_schema(tool_name)
    properties = spec.get("items", {}).get("properties")
    return properties or {}


def _service_stub() -> OrderService:
    return OrderService.__new__(OrderService)


def _in_hours(hours: float) -> datetime:
    return datetime.now(VN_TZ) + timedelta(hours=hours)


class TestTimingToolSchemaLetsLlmNameCatalogueItem:
    """Schema phải khai đúng thứ code dùng để nhận ra mẫu làm sẵn."""

    @pytest.mark.parametrize("tool_name", ["check_bake_time", "create_draft_order"])
    def test_schema_co_cake_id_va_product_id(self, tool_name):
        properties = _item_properties(tool_name)
        assert properties, f"{tool_name}: không tìm thấy schema của từng món"
        assert "cake_id" in properties, (
            f"{tool_name}: thiếu `cake_id` nên LLM không thể chỉ ra mẫu làm sẵn; "
            "mọi mẫu có sẵn sẽ bị tính là bánh đặt"
        )
        assert "product_id" in properties or tool_name == "create_draft_order", (
            f"{tool_name}: thiếu bí danh `product_id`"
        )

    def test_cong_cu_kiem_thoi_gian_co_du_hai_id(self):
        properties = _item_properties("check_bake_time")
        assert {"cake_id", "product_id"} <= set(properties), (
            "check_bake_time là công cụ tạo ra con số giờ, phải nhận được cả hai "
            "cách viết ID mà pricing hiểu"
        )

    def test_mo_ta_noi_ro_hau_qua_khi_thieu_id(self):
        description = _items_schema("check_bake_time").get("description", "")
        assert "cake_id" in description, (
            "phần mô tả phải hướng dẫn LLM gửi cake_id cho mẫu làm sẵn"
        )


class TestSavedDesignDecidesLeadTime:
    """Thiết kế đã lưu là nguồn duy nhất cho cả giá và thời gian."""

    def test_size_roi_khong_rut_ngan_duoc_thoi_gian_cua_thiet_ke_hai_tang(self):
        # Thiết kế lưu là 2 tầng, nhưng trường size rời nói 20cm (đúng ca đã đo).
        item = {
            "product_id": NIL_UUID,
            "size": "20cm",
            "customization_json": {"size": "2-tier", "toppings": [], "border": "none"},
        }
        with pytest.raises(PickupDateValidationError) as exc:
            _service_stub()._validate_pickup_date(_in_hours(30), [item])
        assert "48" in str(exc.value), (
            "bánh hai tầng đã lưu thiết kế phải cần 48 giờ, không được lấy size rời 20cm"
        )

    def test_thieu_size_roi_van_theo_thiet_ke(self):
        item = {
            "product_id": NIL_UUID,
            "customization_json": {"size": "2-tier", "toppings": [], "border": "none"},
        }
        with pytest.raises(PickupDateValidationError):
            _service_stub()._validate_pickup_date(_in_hours(30), [item])

    def test_thiet_ke_mot_tang_van_24_gio(self):
        item = {
            "product_id": NIL_UUID,
            "size": "20cm",
            "customization_json": {"size": "20cm", "toppings": [], "border": "none"},
        }
        # 30 giờ > 24 giờ nên phải qua; không được siết nhầm thành 48 giờ.
        _service_stub()._validate_pickup_date(_in_hours(30), [item])

    def test_dong_co_san_khong_bi_tinh_gio_theo_thiet_ke(self):
        """Mẫu làm sẵn có ID danh mục: bán ngay, kể cả hai tầng."""
        item = {
            "product_id": "11111111-1111-1111-1111-111111111111",
            "size": "2-tier",
        }
        _service_stub()._validate_pickup_date(_in_hours(1), [item])
