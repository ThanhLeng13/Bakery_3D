"""Quy tắc: đặt trong ngày thì chỉ bán bánh sẵn, đặt xa ngày mới nhận đặt mẫu.

Bối cảnh
-------
Trợ lý AI từng không phân biệt hai kiểu khách. Khách cần bánh **gấp** (trong
ngày) mà em vẫn hỏi "anh muốn màu gì, hoa văn gì ạ" rồi nhận đặt mẫu riêng —
làm mẫu mới không kịp, khách đến nhận không có bánh. Ngược lại, khách đặt trước
vài ngày thì lại chỉ được giới thiệu mẫu có sẵn, bỏ lỡ đơn thiết kế riêng.

Quy tắc của tiệm: còn dưới 24 giờ thì chỉ bán bánh sẵn trong danh mục; từ 24
giờ trở lên mới nhận đặt theo mẫu khách chọn.

Cách cài đặt: `check_bake_time` trả thêm `custom_design_allowed`, và prompt của
trợ lý bảo em đọc trường đó rồi hành xử theo.

Test này khoá cả hai nửa: con số do code tính, và prompt phải nhắc trợ lý dùng
con số đó. Thiếu một nửa là luật chỉ tồn tại trên giấy.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.order_tools import SAME_DAY_NOTICE_HOURS, OrderTools
from app.services import rag_service

VN_TZ = timezone(timedelta(hours=7))

FREEZE = datetime(2026, 10, 7, 16, 22, tzinfo=VN_TZ)


def _tools(monkeypatch) -> OrderTools:
    """OrderTools không khởi tạo CSDL, và thời gian được cố định."""
    monkeypatch.setattr("app.services.order_tools._vn_now", lambda: FREEZE)
    return OrderTools.__new__(OrderTools)


class TestCustomDesignFlag:
    """`custom_design_allowed` phải đúng theo ngày nhận."""

    def test_trong_ngay_thi_khong_nhan_dat_mau(self, monkeypatch):
        """Còn 5 giờ — cần gấp, chỉ bán được bánh sẵn."""
        near = (FREEZE + timedelta(hours=5)).strftime("%Y-%m-%d")
        result = _tools(monkeypatch).check_bake_time(near)
        assert result["custom_design_allowed"] is False

    def test_cach_mot_ngay_thi_nhan_dat_mau(self, monkeypatch):
        """Cách 3 ngày — được đặt mẫu."""
        far = (FREEZE + timedelta(days=3)).strftime("%Y-%m-%d")
        result = _tools(monkeypatch).check_bake_time(far)
        assert result["custom_design_allowed"] is True

    def test_dung_moc_24_gio(self, monkeypatch):
        """Đúng ở ranh giới: 23 tiếng thì chưa, 25 tiếng thì được.

        Cố định ngày có kèm giờ để không phụ thuộc giờ chạy test.
        """
        just_under = (FREEZE + timedelta(hours=SAME_DAY_NOTICE_HOURS - 1)).strftime(
            "%Y-%m-%dT%H:%M"
        )
        just_over = (FREEZE + timedelta(hours=SAME_DAY_NOTICE_HOURS + 1)).strftime(
            "%Y-%m-%dT%H:%M"
        )
        tools = _tools(monkeypatch)
        assert tools.check_bake_time(just_under)["custom_design_allowed"] is False
        assert tools.check_bake_time(just_over)["custom_design_allowed"] is True

    def test_ngay_qua_khu_thi_cung_khong_nhan_dat_mau(self, monkeypatch):
        """Ngày đã trôi qua — tất nhiên không nhận đặt mẫu."""
        past = (FREEZE - timedelta(days=2)).strftime("%Y-%m-%d")
        result = _tools(monkeypatch).check_bake_time(past)
        assert result["custom_design_allowed"] is False
        assert result["is_possible"] is False

    def test_moc_dat_mau_khac_moc_lam_banh(self, monkeypatch):
        """Hai mốc này trả lời hai câu hỏi khác nhau, không được trộn.

        Bánh 2 tầng cần 48 giờ để làm (`required_lead_hours`), nhưng đặt mẫu
        chỉ cần 24 giờ (`custom_design_allowed`). Nếu lấy 48 làm ngưỡng đặt mẫu
        thì từ chối oan khách đặt trước 30 giờ và chọn mẫu có sẵn — đơn đó bán
        được.
        """
        target = (FREEZE + timedelta(hours=30)).strftime("%Y-%m-%dT%H:%M")
        result = _tools(monkeypatch).check_bake_time(
            target, items=[{"name": "bánh 2 tầng", "size": "2-tier"}]
        )
        assert result["required_lead_hours"] == 48
        assert result["is_possible"] is False
        # Nhưng khách vẫn được đặt theo mẫu, và bánh 1 tầng thì vẫn kịp làm.
        assert result["custom_design_allowed"] is True


class TestPromptNoiQuyTacVoiTroLy:
    """Prompt phải bắt trợ lý đọc `custom_design_allowed` rồi hành xử theo.

    Con số mà không ai dùng thì vô nghĩa. Phần này chống việc sửa prompt sau này
    làm luật biến mất mà test vẫn xanh.
    """

    def _prompt(self) -> str:
        return rag_service.SYSTEM_PROMPT_TEMPLATE

    def _rule_block(self) -> str:
        """Khoản prompt nói về đặt trong ngày.

        Phải lấy ĐÚNG khối này, không phải toàn bộ prompt. Lý do đã đo: khi xoá
        riêng khối này thì câu "trong 24 giờ thì KHÔNG, chỉ có bánh sẵn" ở mục
        "Câu hỏi thường gặp" vẫn còn, nên một test chỉ kiểm "prompt có nhắc
        custom_design_allowed" vẫn xanh — tức là test không bắt được việc mất
        luật. Kiểm trong khối thì bắt được.
        """
        prompt = self._prompt()
        start = prompt.find("ĐẶT TRONG NGÀY")
        assert start != -1, "Không còn khối quy tắc 'đặt trong ngày' trong prompt."
        rest = prompt[start:]
        end = rest.find("\n## ")
        return rest if end == -1 else rest[:end]

    def test_prompt_nhac_doc_custom_design_allowed(self):
        assert "custom_design_allowed" in self._prompt(), (
            "prompt không nhắc trợ lý đọc custom_design_allowed"
        )

    def test_khoi_quy_tac_noi_ro_khi_nao_chi_banh_san(self):
        block = self._rule_block()
        assert "24 giờ" in block, "khối quy tắc phải nêu rõ mốc 24 giờ"
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
