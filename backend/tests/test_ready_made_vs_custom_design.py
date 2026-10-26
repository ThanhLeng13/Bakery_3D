"""Hai luồng bánh khác nhau: mẫu làm sẵn bán ngay, mẫu đặt thì mới cần chờ.

Bối cảnh
-------
Tiệm có hai loại hàng:

1. **Mẫu làm sẵn** — mỗi ngày tiệm làm sẵn một số mẫu, admin nhập vào danh
   mục để khách chọn. Đây là hàng CÓ SẴN, bán liền được, y hệt bán bất kỳ món
   nào khác trong tiệm — kể cả mẫu hai tầng đã làm sẵn.
2. **Mẫu đặt** — bánh làm riêng theo yêu cầu của khách. Cần chờ: bánh đơn giản
   (một tầng) 24 giờ, bánh phức tạp (hai tầng) 48 giờ.

Ranh giới giữa hai loại là `product_id`: mẫu làm sẵn có `product_id` thật
trong danh mục, mẫu đặt dùng UUID nil (`is_custom_cake`).

Lỗi đã xảy ra
-------------
Trước đây `lead_hours_for_items` tính mốc chờ cho MỌI dòng trong đơn, kể cả
mẫu làm sẵn. Hậu quả: một chiếc bánh hai tầng đã nằm sẵn trong danh mục bị
bắt phải đặt trước 48 giờ — khách muốn mua ngay cũng không được, dù hàng đã có
sẵn trong tủ. Ngược lại, nếu bỏ hết thì mẫu đặt hai tầng lại bị nhận khi chưa
kịp làm.

Test này khoá cả hai ranh giới, ở cả hai nơi dùng chung (`pricing` cho
checkout, `order_tools` cho agent) — vì trước đây chỗ này và chỗ kia đã lệch
nhau 24 giờ.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.order_tools import OrderTools
from app.services.pricing import (
    NIL_UUID,
    custom_design_lead_hours,
    lead_hours_for_items,
)
from app.services import rag_service

VN_TZ = timezone(timedelta(hours=7))

FREEZE = datetime(2026, 10, 7, 16, 22, tzinfo=VN_TZ)

# Mẫu làm sẵn: có product_id thật trong danh mục.
READY_MADE_1TIER = [{"product_id": "11111111-1111-1111-1111-111111111111", "size": "20cm"}]
READY_MADE_2TIER = [{"product_id": "22222222-2222-2222-2222-222222222222", "size": "2-tier"}]

# Mẫu đặt: product_id là UUID nil.
CUSTOM_1TIER = [{"product_id": NIL_UUID, "size": "20cm"}]
CUSTOM_2TIER = [{"product_id": NIL_UUID, "size": "2-tier"}]


def _tools(monkeypatch) -> OrderTools:
    monkeypatch.setattr("app.services.order_tools._vn_now", lambda: FREEZE)
    return OrderTools.__new__(OrderTools)


def _at(hours: float) -> str:
    return (FREEZE + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M")


class TestMauLamSanBanNgay:
    """Mẫu làm sẵn không cần chờ — kể cả mẫu hai tầng đã làm sẵn."""

    def test_moc_cho_mau_lam_san_la_0(self):
        assert lead_hours_for_items(READY_MADE_1TIER) == 0
        assert lead_hours_for_items(READY_MADE_2TIER) == 0

    def test_mau_hai_tang_lam_san_khong_can_48_gio(self):
        """Đây là lỗi đã xảy ra: bánh hai tầng có sẵn bị bắt đặt trước 48h."""
        assert lead_hours_for_items(READY_MADE_2TIER) == 0, (
            "mẫu hai tầng đã làm sẵn trong danh mục phải bán được ngay"
        )

    def test_don_chi_co_mau_lam_san_thi_ban_ngay_du_khach_can_hien_tai(self, monkeypatch):
        result = _tools(monkeypatch).check_bake_time(_at(1), items=READY_MADE_2TIER)
        assert result["required_lead_hours"] == 0
        assert result["is_possible"] is True

    def test_hai_mau_lam_san_cung_ban_ngay(self):
        items = READY_MADE_1TIER + READY_MADE_2TIER
        assert lead_hours_for_items(items) == 0


class TestMauDatCanCho:
    """Mẫu đặt vẫn theo 24/48 giờ như quy tắc của tiệm."""

    def test_mau_dat_mot_tang_can_24(self):
        assert lead_hours_for_items(CUSTOM_1TIER) == 24

    def test_mau_dat_hai_tang_can_48(self):
        assert lead_hours_for_items(CUSTOM_2TIER) == 48

    def test_mau_dat_hai_tang_dat_truoc_30_gio_thi_khong_du(self, monkeypatch):
        result = _tools(monkeypatch).check_bake_time(_at(30), items=CUSTOM_2TIER)
        assert result["is_possible"] is False
        assert result["custom_design_allowed"] is False

    def test_mau_dat_hai_tang_du_48_gio(self, monkeypatch):
        result = _tools(monkeypatch).check_bake_time(_at(48), items=CUSTOM_2TIER)
        assert result["is_possible"] is True
        assert result["custom_design_allowed"] is True

    def test_ranh_gioi_24_gio(self, monkeypatch):
        """23h59 thì chưa, 24h01 thì được."""
        tools = _tools(monkeypatch)
        assert tools.check_bake_time(_at(23.5), items=CUSTOM_1TIER)[
            "custom_design_allowed"
        ] is False
        assert tools.check_bake_time(_at(24.5), items=CUSTOM_1TIER)[
            "custom_design_allowed"
        ] is True

    def test_ranh_gioi_48_gio(self, monkeypatch):
        """47 giờ thì chưa, 49 giờ thì được."""
        tools = _tools(monkeypatch)
        assert tools.check_bake_time(_at(47), items=CUSTOM_2TIER)[
            "custom_design_allowed"
        ] is False
        assert tools.check_bake_time(_at(49), items=CUSTOM_2TIER)[
            "custom_design_allowed"
        ] is True


class TestDonNhieuMon:
    """Đơn nhiều món thì lấy mốc cao nhất trong các mẫu đặt."""

    def test_co_banh_hai_tang_thi_lay_48(self):
        items = [
            {"product_id": NIL_UUID, "size": "20cm"},
            {"product_id": NIL_UUID, "size": "2-tier"},
        ]
        assert lead_hours_for_items(items) == 48

    def test_chi_mau_lam_san_thi_ban_ngay(self):
        assert lead_hours_for_items(READY_MADE_1TIER + READY_MADE_2TIER) == 0


class TestCustomDesignLeadHours:
    """Mốc để NHẬN một mẫu đặt — không phụ thuộc đơn đang có mẫu làm sẵn."""

    def test_mau_lam_san_van_cho_moc_24(self):
        """Khách đang xem mẫu làm sẵn nhưng muốn đặt mẫu riêng: cần 24 giờ."""
        assert custom_design_lead_hours(READY_MADE_1TIER) == 24

    def test_mau_hai_tang_thi_48(self):
        assert custom_design_lead_hours(CUSTOM_2TIER) == 48

    def test_rong_thi_dung_mac_dinh(self):
        assert custom_design_lead_hours([]) == 24
        assert custom_design_lead_hours(None) == 24

    def test_mau_lam_san_van_phai_cho_24_gio_de_dat_mau_rieng(self, monkeypatch):
        """Ca then chốt, và là ca đã lọt qua đột biến.

        Đơn toàn mẫu làm sẵn thì `required_lead_hours` = 0 (bán ngay). Nhưng nếu
        khách muốn ĐẶT MẪU RIÊNG thì vẫn phải chờ 24 giờ — không phải 0.

        Nếu cờ `custom_design_allowed` lấy theo `lead` thì nó thành True ngay
        cả khi khách chỉ còn 1 giờ, và trợ lý sẽ nhận đơn mẫu riêng trong khi
        không kịp làm. Test này làm đỏ đúng lỗi đó.
        """
        result = _tools(monkeypatch).check_bake_time(_at(1), items=READY_MADE_1TIER)
        assert result["required_lead_hours"] == 0, "mẫu làm sẵn thì bán ngay"
        assert result["custom_design_allowed"] is False, (
            "nhưng đặt MẪU RIÊNG thì vẫn phải chờ 24 giờ"
        )

    def test_du_24_gio_thi_dat_mau_rieng_duoc(self, monkeypatch):
        result = _tools(monkeypatch).check_bake_time(_at(24), items=READY_MADE_1TIER)
        assert result["custom_design_allowed"] is True


class TestKhongCoItems:
    """Chưa biết khách chọn gì thì dùng mức mặc định, thận trọng hơn."""

    def test_rong_thi_24(self):
        assert lead_hours_for_items([]) == 24
        assert lead_hours_for_items(None) == 24


class TestNgayQuaKhu:
    def test_ngay_qua_khu_thi_khong_nhan_dat_mau(self, monkeypatch):
        past = (FREEZE - timedelta(days=2)).strftime("%Y-%m-%d")
        result = _tools(monkeypatch).check_bake_time(past, items=CUSTOM_1TIER)
        assert result["custom_design_allowed"] is False
        assert result["is_possible"] is False


class TestHaiMocKhongTheLech:
    """Mốc đặt mẫu và mốc làm bánh phải đồng nhất trong một đơn.

    Nếu lệch thì agent và checkout nói khác nhau với khách — hoặc tệ hơn, agent
    nhận đơn mà checkout từ chối.
    """

    def test_mau_dat_hai_tang_thi_hai_moc_bang_nhau(self, monkeypatch):
        result = _tools(monkeypatch).check_bake_time(_at(30), items=CUSTOM_2TIER)
        assert result["custom_design_allowed"] == result["is_possible"]

    def test_mau_dat_mot_tang_thi_hai_moc_bang_nhau(self, monkeypatch):
        result = _tools(monkeypatch).check_bake_time(_at(20), items=CUSTOM_1TIER)
        assert result["custom_design_allowed"] == result["is_possible"]


class TestPromptNoiHaiLuong:
    """Prompt phải nói rõ hai loại hàng khác nhau."""

    def _rule_block(self) -> str:
        prompt = rag_service.SYSTEM_PROMPT_TEMPLATE
        start = prompt.find("MẪU LÀM SẴN")
        assert start != -1, "Không còn khối quy tắc 'mẫu làm sẵn' trong prompt."
        rest = prompt[start:]
        end = rest.find("\n## ")
        return rest if end == -1 else rest[:end]

    def test_prompt_noi_ro_mau_lam_san_ban_ngay(self):
        block = self._rule_block()
        assert "bán **ngay**" in block or "bán ngay" in block

    def test_prompt_noi_ro_hai_moc_cho_mau_dat(self):
        block = self._rule_block()
        assert "24 giờ" in block
        assert "48 giờ" in block

    def test_prompt_nhac_doc_custom_design_allowed(self):
        assert "custom_design_allowed" in rag_service.SYSTEM_PROMPT_TEMPLATE

    def test_prompt_chi_dan_theo_ten_truong(self):
        block = self._rule_block()
        assert "custom_design_allowed" in block
        assert "check_bake_time" in block

    def test_prompt_cam_doan_khi_gap(self):
        """Không được để trợ lý hứa làm mọi mẫu khi khách cần gấp."""
        assert "KHÔNG" in self._rule_block()

    def test_prompt_khong_bat_doan(self):
        """Trợ lý phải gọi công cụ, không được tự kết luận gấp hay không."""
        assert "check_bake_time" in rag_service.SYSTEM_PROMPT_TEMPLATE
