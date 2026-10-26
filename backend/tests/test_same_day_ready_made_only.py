"""Quy tắc: đặt gấp thì chỉ bán bánh sẵn, đặt xa ngày mới nhận đặt mẫu.

Bối cảnh
-------
Trợ lý AI từng không phân biệt hai kiểu khách. Khách cần bánh **gấp** mà em
vẫn hỏi "anh muốn màu gì, hoa văn gì ạ" rồi nhận đặt mẫu riêng — làm mẫu mới
không kịp, khách đến nhận không có bánh. Ngược lại, khách đặt trước vài ngày
thì lại chỉ được giới thiệu mẫu có sẵn, bỏ lỡ đơn thiết kế riêng.

Quy tắc của tiệm, do chủ tiệm xác nhận:
- Bánh **đơn giản** (một tầng) cần **24 giờ**.
- Bánh **phức tạp** (hai tầng, hình dáng) cần **48 giờ**.
- Còn ít hơn mốc đó thì chỉ bán được bánh sẵn trong danh mục.

Một mốc duy nhất, tính theo độ phức tạp của đơn. `check_bake_time` trả thêm
`custom_design_allowed`, và prompt của trợ lý bảo em đọc trường đó rồi hành
xử theo.

Test này khoá cả hai nửa: con số do code tính, và prompt phải nhắc trợ lý dùng
con số đó. Thiếu một nửa là luật chỉ tồn tại trên giấy.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.order_tools import OrderTools
from app.services import rag_service

VN_TZ = timezone(timedelta(hours=7))

FREEZE = datetime(2026, 10, 7, 16, 22, tzinfo=VN_TZ)

SIMPLE = [{"name": "bánh kem dâu", "size": "20cm"}]
COMPLEX = [{"name": "bánh hai tầng", "size": "2-tier"}]


def _tools(monkeypatch) -> OrderTools:
    """OrderTools không khởi tạo CSDL, và thời gian được cố định."""
    monkeypatch.setattr("app.services.order_tools._vn_now", lambda: FREEZE)
    return OrderTools.__new__(OrderTools)


def _at(hours: float) -> str:
    """Ngày nhận cách mốc hiện tại đúng số giờ yêu cầu, kèm giờ cụ thể."""
    return (FREEZE + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M")


class TestBanhDonGianCan24Gio:
    """Bánh một tầng: 24 giờ là đủ."""

    def test_du_24_gio_thi_nhan_dat_mau(self, monkeypatch):
        result = _tools(monkeypatch).check_bake_time(_at(24), items=SIMPLE)
        assert result["required_lead_hours"] == 24
        assert result["custom_design_allowed"] is True

    def test_thieu_24_gio_thi_chi_banh_san(self, monkeypatch):
        result = _tools(monkeypatch).check_bake_time(_at(23), items=SIMPLE)
        assert result["custom_design_allowed"] is False

    def test_ranh_gioi_dung_24(self, monkeypatch):
        """23h59 thì chưa, 24h01 thì được."""
        tools = _tools(monkeypatch)
        assert tools.check_bake_time(_at(23.5), items=SIMPLE)[
            "custom_design_allowed"
        ] is False
        assert tools.check_bake_time(_at(24.5), items=SIMPLE)[
            "custom_design_allowed"
        ] is True


class TestBanhPhucTapCan48Gio:
    """Bánh hai tầng: phải có 48 giờ, không phải 24.

    Đây là chỗ dễ sai nhất: nếu ngưỡng đặt mẫu vẫn là 24 giờ thì một bánh hai
    tầng đặt trước 30 giờ sẽ bị nhận — rồi không kịp làm.
    """

    def test_30_gio_khong_du_cho_banh_hai_tang(self, monkeypatch):
        result = _tools(monkeypatch).check_bake_time(_at(30), items=COMPLEX)
        assert result["required_lead_hours"] == 48
        assert result["is_possible"] is False
        assert result["custom_design_allowed"] is False, (
            "bánh hai tầng đặt trước 30 giờ phải bị từ chối, vì chỉ 48 giờ mới"
            " kịp làm"
        )

    def test_du_48_gio_thi_nhan_dat_mau(self, monkeypatch):
        result = _tools(monkeypatch).check_bake_time(_at(48), items=COMPLEX)
        assert result["required_lead_hours"] == 48
        assert result["custom_design_allowed"] is True

    def test_ranh_gioi_dung_48(self, monkeypatch):
        tools = _tools(monkeypatch)
        assert tools.check_bake_time(_at(47), items=COMPLEX)[
            "custom_design_allowed"
        ] is False
        assert tools.check_bake_time(_at(49), items=COMPLEX)[
            "custom_design_allowed"
        ] is True

    def test_nguong_dat_mau_bang_nguong_lam_banh(self, monkeypatch):
        """Hai ngưỡng phải là MỘT, không phải hai.

        Trước đây tách ra: đặt mẫu 24 giờ, làm bánh 48 giờ. Sai, vì nhận đơn
        hai tầng rồi mới thấy không kịp làm — lỡ khách.
        """
        for hours in (5, 23, 30, 47, 48, 72):
            result = _tools(monkeypatch).check_bake_time(_at(hours), items=COMPLEX)
            assert result["custom_design_allowed"] == result["is_possible"], (
                f"ở {hours} giờ, đặt mẫu và làm bánh phải cùng kết luận"
            )


class TestDonNhieuMon:
    """Đơn nhiều món thì lấy mốc cao nhất."""

    def test_co_banh_hai_tang_thi_lay_48(self, monkeypatch):
        items = [
            {"name": "bánh kem dâu", "size": "20cm"},
            {"name": "bánh hai tầng", "size": "2-tier"},
        ]
        result = _tools(monkeypatch).check_bake_time(_at(30), items=items)
        assert result["required_lead_hours"] == 48
        assert result["custom_design_allowed"] is False


class TestKhongCoItems:
    """Khách chưa chọn kích cước thì dùng mức mặc định."""

    def test_khong_co_items_thi_dung_24(self, monkeypatch):
        result = _tools(monkeypatch).check_bake_time(_at(30))
        assert result["required_lead_hours"] == 24
        assert result["custom_design_allowed"] is True


class TestNgayQuaKhu:
    def test_ngay_qua_khu_thi_khong_nhan_dat_mau(self, monkeypatch):
        past = (FREEZE - timedelta(days=2)).strftime("%Y-%m-%d")
        result = _tools(monkeypatch).check_bake_time(past)
        assert result["custom_design_allowed"] is False
        assert result["is_possible"] is False


class TestPromptNoiQuyTacVoiTroLy:
    """Prompt phải bắt trợ lý đọc `custom_design_allowed` rồi hành xử theo.

    Con số mà không ai dùng thì vô nghĩa. Phần này chống việc sửa prompt sau này
    làm luật biến mất mà test vẫn xanh.
    """

    def _prompt(self) -> str:
        return rag_service.SYSTEM_PROMPT_TEMPLATE

    def _rule_block(self) -> str:
        """Khoản prompt nói về đặt gấp.

        Phải lấy ĐÚNG khối này, không phải toàn bộ prompt. Lý do đã đo: khi xoá
        riêng khối này thì câu "24 giờ" ở mục "Câu hỏi thường gặp" vẫn còn,
        nên một test chỉ kiểm "prompt có nhắc custom_design_allowed" vẫn xanh —
        tức là test không bắt được việc mất luật. Kiểm trong khối thì bắt được.
        """
        prompt = self._prompt()
        start = prompt.find("ĐẶT GẤP")
        assert start != -1, "Không còn khối quy tắc 'đặt gấp' trong prompt."
        rest = prompt[start:]
        end = rest.find("\n## ")
        return rest if end == -1 else rest[:end]

    def test_prompt_nhac_doc_custom_design_allowed(self):
        assert "custom_design_allowed" in self._prompt(), (
            "prompt không nhắc trợ lý đọc custom_design_allowed"
        )

    def test_khoi_quy_tac_noi_ro_hai_muc_thoi_gian(self):
        """Phải nêu CẢ HAI mốc: 24 cho đơn giản, 48 cho phức tạp."""
        block = self._rule_block()
        assert "24 giờ" in block, "phải nêu mốc 24 giờ cho bánh đơn giản"
        assert "48 giờ" in block, "phải nêu mốc 48 giờ cho bánh phức tạp"

    def test_khoi_quy_tac_noi_ro_khi_nao_chi_banh_san(self):
        block = self._rule_block()
        assert "bánh sẵn" in block.lower(), "khối quy tắc phải nói rõ bán bánh sẵn"
        assert "mẫu riêng" in block, "khối quy tắc phải nói rõ không nhận đặt mẫu riêng"

    def test_khoi_quy_tac_chi_dan_theo_ten_truong(self):
        """Phải chỉ đường đọc `custom_design_allowed`, không bắt trợ lý tự đoán."""
        block = self._rule_block()
        assert "custom_design_allowed" in block
        assert "check_bake_time" in block

    def test_prompt_cam_doan_khi_gap(self):
        """Không được để trợ lý hứa làm mọi mẫu khi khách cần gấp."""
        assert "KHÔNG" in self._rule_block()

    def test_prompt_khong_bat_doan_gap_hay_khong(self):
        """Trợ lý phải gọi công cụ, không được tự kết luận."""
        assert "check_bake_time" in self._prompt()
