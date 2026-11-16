"""Khách GHÉ LẤY hay GIAO HÀNG — hai loại đơn khác nhau về vận hành.

Bối cảnh
--------
Trước module này `orders` chỉ có `pickup_date`, nên hai loại đơn được lưu giống
hệt nhau:

    đơn ghé lấy — thợ làm xong, để quầy, chờ khách tới
    đơn giao    — thợ làm xong, phải đóng gói và giao tới một địa chỉ

Thợ đọc đơn không phân biệt được. Trợ lý AI cũng không có chỗ nào để hỏi, nên
nó chốt đơn mà không biết khách muốn nhận thế nào — và mọi đơn bị coi là ghé
lấy, kể cả đơn khách đang ngồi đợi shipper.

Những gì được khoá ở đây:
- giá trị lạ thì NÉM LỖI, không đoán (đoán bừa biến đơn ghé lấy thành giao hàng)
- giao hàng mà thiếu địa chỉ thì TỪ CHỐI
- ghé lấy mà có địa chỉ thì BỎ địa chỉ (không giữ hai nguồn sự thật)
- cách viết của khách/LLM ("giao hàng", "tự lấy"...) được chuẩn hoá
"""

import pytest

from app.services.fulfillment import (
    FulfillmentError,
    normalize_address,
    normalize_fulfillment_type,
    resolve_fulfillment,
)

ADDRESS = "123 Nguyễn Văn Linh, phường Phước Ninh, quận Hải Châu, Đà Nẵng"


class TestNormalizeFulfillmentType:
    def test_gia_tri_chuan_duoc_giu_nguyen(self):
        assert normalize_fulfillment_type("pickup") == "pickup"
        assert normalize_fulfillment_type("delivery") == "delivery"

    def test_bo_trong_thi_mac_dinh_ghe_lay(self):
        """Rỗng → pickup.

        Mặc định có chủ ý: đa số khách ghé lấy, và chọn 'delivery' mà thiếu địa
        chỉ sẽ tạo ra đơn không giao được.
        """
        assert normalize_fulfillment_type(None) == "pickup"
        assert normalize_fulfillment_type("") == "pickup"
        assert normalize_fulfillment_type("   ") == "pickup"

    def test_nhan_cach_viet_cua_khach(self):
        """Khách gõ 'Giao Hàng' hay 'giao hang' đều phải ra delivery."""
        for text in ("Giao hàng", "giao hang", "GIAO HÀNG", "ship", "shipper",
                     "giao tận nơi", "delivery"):
            assert normalize_fulfillment_type(text) == "delivery", text

    def test_nhan_cach_viet_ghe_lay(self):
        for text in ("Ghé lấy", "ghe lay", "tự lấy", "tu lay", "đến lấy",
                     "lấy tại quán", "nhận tại quán", "pickup"):
            assert normalize_fulfillment_type(text) == "pickup", text

    def test_cau_co_ca_hai_tu_thi_theo_y_giao_hang(self):
        """'Giao hàng chứ không ghé lấy' — ý khách là giao hàng.

        Nếu xét 'lấy' trước thì câu này bị đọc ngược, và đơn giao hàng bị lưu
        thành đơn chờ khách tới quán.
        """
        assert (
            normalize_fulfillment_type("giao hàng chứ không ghé lấy") == "delivery"
        )

    def test_gia_tri_la_thi_nem_loi_khong_doan(self):
        """Đoán bừa một chuỗi lạ thành 'delivery' có thể tạo đơn không giao được."""
        with pytest.raises(FulfillmentError, match="Không hiểu"):
            normalize_fulfillment_type("bất kỳ")


class TestResolveFulfillment:
    def test_giao_hang_co_dia_chi_hop_le(self):
        result = resolve_fulfillment("delivery", ADDRESS)
        assert result["fulfillment_type"] == "delivery"
        assert result["delivery_address"] == ADDRESS

    def test_giao_hang_thieu_dia_chi_bi_tu_choi(self):
        with pytest.raises(FulfillmentError, match="địa chỉ"):
            resolve_fulfillment("delivery", None)

    def test_giao_hang_dia_chi_toan_khoang_trang_bi_tu_choi(self):
        with pytest.raises(FulfillmentError, match="địa chỉ"):
            resolve_fulfillment("delivery", "     ")

    def test_giao_hang_dia_chi_qua_ngan_bi_tu_choi(self):
        """'Đà Nẵng' không phải địa chỉ giao được — shipper không tìm ra."""
        with pytest.raises(FulfillmentError, match="quá ngắn"):
            resolve_fulfillment("delivery", "Đà Nẵng")

    def test_giao_hang_dia_chi_qua_dai_bi_tu_choi(self):
        with pytest.raises(FulfillmentError, match="quá dài"):
            resolve_fulfillment("delivery", "A" * 301)

    def test_ghe_lay_bo_dia_chi_thua(self):
        """Ghé lấy mà vẫn có địa chỉ là hai nguồn sự thật mâu thuẫn.

        Thợ không biết tin `fulfillment_type` hay tin địa chỉ. Bỏ địa chỉ đi.
        """
        result = resolve_fulfillment("pickup", ADDRESS)
        assert result["fulfillment_type"] == "pickup"
        assert result["delivery_address"] is None

    def test_khong_truyen_gi_thi_ghe_lay(self):
        result = resolve_fulfillment(None, None)
        assert result == {"fulfillment_type": "pickup", "delivery_address": None}

    def test_dia_chi_duoc_chuan_hoa_khoang_trang(self):
        result = resolve_fulfillment("delivery", f"   {ADDRESS}   ")
        assert result["delivery_address"] == ADDRESS


class TestNormalizeAddress:
    def test_gop_khoang_trang_thua(self):
        assert normalize_address("  123  đường   A  ") == "123 đường A"

    def test_rong_thanh_none(self):
        assert normalize_address("") is None
        assert normalize_address("   ") is None
        assert normalize_address(None) is None


class TestChatbotMustAskForFulfillment:
    """Trợ lý AI không được chốt đơn khi chưa biết khách nhận thế nào."""

    def _tools(self):
        from app.services.order_tools import OrderTools

        class _DB:
            def table(self, *_a, **_k):
                raise AssertionError("Không được truy vấn CSDL trong test này")

        return OrderTools(_DB())

    def test_thieu_hinh_thuc_nhan_thi_khong_tao_don(self):
        """Đây là lỗi thật: trước đây mặc định là 'pickup', nên đơn giao hàng
        bị lưu thành đơn chờ khách — khách ngồi đợi shipper không tới."""
        tools = self._tools()
        with pytest.raises(Exception) as exc:
            tools.create_draft_order(
                customer_name="Nguyễn Văn A",
                customer_phone="0901234567",
                pickup_date="2099-12-31",
                items=[{"name": "Bánh kem", "quantity": 1}],
                customer_id="00000000-0000-0000-0000-000000000001",
            )
        assert "GIAO HÀNG" in str(exc.value) or "GHÉ LẤY" in str(exc.value)

    def test_giao_hang_thieu_dia_chi_thi_khong_tao_don(self):
        tools = self._tools()
        with pytest.raises(Exception) as exc:
            tools.create_draft_order(
                customer_name="Nguyễn Văn A",
                customer_phone="0901234567",
                pickup_date="2099-12-31",
                items=[{"name": "Bánh kem", "quantity": 1}],
                customer_id="00000000-0000-0000-0000-000000000001",
                fulfillment_type="delivery",
            )
        assert "địa chỉ" in str(exc.value)


class TestToolSchemaRequiresFulfillment:
    def test_hinh_thuc_nhan_la_tham_so_bat_buoc_trong_schema(self):
        """LLM tuân theo schema. Nếu `fulfillment_type` không nằm trong
        `required` thì nó sẽ không bao giờ gửi, và công cụ luôn từ chối."""
        from app.services.order_tools import TOOL_SCHEMAS

        schema = next(
            t for t in TOOL_SCHEMAS
            if t["function"]["name"] == "create_draft_order"
        )
        required = schema["function"]["parameters"]["required"]
        assert "fulfillment_type" in required
        assert "delivery_address" in schema["function"]["parameters"]["properties"]

    def test_schema_co_enum_hai_gia_tri(self):
        from app.services.order_tools import TOOL_SCHEMAS

        schema = next(
            t for t in TOOL_SCHEMAS
            if t["function"]["name"] == "create_draft_order"
        )
        prop = schema["function"]["parameters"]["properties"]["fulfillment_type"]
        # `_nullable` bọc type thành list, nên enum nằm cùng chỗ.
        assert prop["enum"] == ["pickup", "delivery"]

    def test_prompt_buoc_hoi_hinh_thuc_nhan(self):
        """Schema một mình không đủ: prompt phải nói cho LLM biết là phải hỏi."""
        from app.services.rag_service import SYSTEM_PROMPT_TEMPLATE

        assert "giao hàng" in SYSTEM_PROMPT_TEMPLATE.lower()
        assert "ghé lấy" in SYSTEM_PROMPT_TEMPLATE.lower()
        # Không được tự cho là khách ghé lấy.
        assert "KHÔNG được tự cho là khách ghé lấy" in SYSTEM_PROMPT_TEMPLATE

    def test_alias_anh_xa_dung_ten_tham_so(self):
        """LLM hay gửi 'address'/'fulfillment' thay vì tên trong schema."""
        from app.services.order_tools import _normalize_arguments

        out = _normalize_arguments(
            "create_draft_order",
            {"address": ADDRESS, "fulfillment": "delivery"},
        )
        assert out["delivery_address"] == ADDRESS
        assert out["fulfillment_type"] == "delivery"
