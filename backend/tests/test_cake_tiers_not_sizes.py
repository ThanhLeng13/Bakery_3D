"""Số tầng thuộc về MẪU bánh, không phải kích thước.

Quy tắc nghiệp vụ
-----------------
Kích thước của bánh là đường kính (16cm / 20cm / 24cm). Số tầng do mẫu thân
bánh quyết định (`round-2-tier`, `round-3-tier`, …).

Trước đây "2-tier" vừa là một kích thước vừa là mẫu, nên giao diện hiện thêm
mục "2 tầng" trong danh sách kích thước dù khách đã chọn mẫu 2 tầng. Ngoài ra
bánh hai tầng chọn đường kính 20cm bị tính giá và thời gian của bánh một tầng.

Các test dưới đây khoá lại: giá và thời gian phải đi theo số tầng của mẫu, và
đơn cũ đã lưu `size="2-tier"` vẫn giữ nguyên nghĩa.
"""

from app.services.pricing import (
    DEFAULT_LEAD_HOURS,
    TWO_TIER_BASE_PRICE,
    TWO_TIER_LEAD_HOURS,
    base_price_for_design,
    lead_hours_for_design,
    lead_hours_for_items,
    order_total,
    price_breakdown,
    tiers_for_design,
    tiers_for_model_slug,
)


class TestTiersComeFromModel:
    def test_doc_so_tang_tu_slug(self):
        assert tiers_for_model_slug("round-1-tier") == 1
        assert tiers_for_model_slug("round-2-tier") == 2
        assert tiers_for_model_slug("round-3-tier") == 3
        assert tiers_for_model_slug(" Round-2-Tier ") == 2

    def test_slug_khong_hop_le_tra_0(self):
        assert tiers_for_model_slug(None) == 0
        assert tiers_for_model_slug("") == 0
        assert tiers_for_model_slug("cake-trai-tim") == 0

    def test_design_mot_tang_theo_mau(self):
        assert tiers_for_design({"model_slug": "round-1-tier", "size": "20cm"}) == 1

    def test_design_don_cu_dung_size_2_tier_van_la_hai_tang(self):
        """Đơn đã lưu trước đây không được đổi nghĩa sau khi tách khái niệm."""
        assert tiers_for_design({"size": "2-tier"}) == 2


class TestPriceFollowsTiers:
    def test_banh_hai_tang_chon_20cm_tinh_gia_hai_tang(self):
        """Đây là lỗi cũ: 20cm + mẫu 2 tầng từng bị tính 350.000đ."""
        design = {"model_slug": "round-2-tier", "size": "20cm"}
        assert base_price_for_design(design) == TWO_TIER_BASE_PRICE
        assert order_total(design) == TWO_TIER_BASE_PRICE

    def test_banh_mot_tang_giu_gia_theo_duong_kinh(self):
        assert base_price_for_design({"model_slug": "round-1-tier", "size": "20cm"}) == 350_000
        assert base_price_for_design({"model_slug": "round-1-tier", "size": "16cm"}) == 250_000

    def test_don_cu_size_2_tier_giu_gia_cu(self):
        assert price_breakdown({"size": "2-tier"})["base_price"] == TWO_TIER_BASE_PRICE

    def test_kich_thuoc_khong_hop_le_van_bao_loi(self):
        try:
            base_price_for_design({"model_slug": "round-1-tier", "size": "ban-mot-met"})
        except ValueError:
            pass
        else:
            raise AssertionError("kích thước không hỗ trợ phải ném ValueError")


class TestLeadTimeFollowsTiers:
    def test_mau_hai_tang_can_48_gio_du_chon_20cm(self):
        design = {"model_slug": "round-2-tier", "size": "20cm"}
        assert lead_hours_for_design(design) == TWO_TIER_LEAD_HOURS

    def test_mau_mot_tang_van_24_gio(self):
        design = {"model_slug": "round-1-tier", "size": "20cm"}
        assert lead_hours_for_design(design) == DEFAULT_LEAD_HOURS

    def test_don_cu_size_2_tier_van_48_gio(self):
        assert lead_hours_for_design({"size": "2-tier"}) == TWO_TIER_LEAD_HOURS

    def test_danh_sach_mon_doc_so_tang_tu_customization(self):
        """Checkout gửi mẫu trong `customization_json`, không phải ở dòng đơn."""
        items = [
            {
                "product_id": None,
                "size": "20cm",
                "customization_json": {"model_slug": "round-2-tier", "size": "20cm"},
            }
        ]
        assert lead_hours_for_items(items) == TWO_TIER_LEAD_HOURS

    def test_danh_sach_mon_mot_tang(self):
        items = [
            {
                "product_id": None,
                "size": "20cm",
                "customization_json": {"model_slug": "round-1-tier", "size": "20cm"},
            }
        ]
        assert lead_hours_for_items(items) == DEFAULT_LEAD_HOURS
