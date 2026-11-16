"""Khách khó tính — những câu mà trợ lý hay trả lời sai nhất.

Vì sao có file này
------------------
Prompt cũ chỉ dạy trợ lý tư vấn bánh bình thường. Khách thật thì mặc cả, đổi ý
liên tục, hỏi những thứ tiệm không biết, phàn nàn đơn cũ, doạ bỏ đi sang tiệm
khác. Không có quy tắc cho những câu đó thì mô hình tự chế — và cách chế nguy
hiểm nhất là **hứa**:

    "dạ em xin bớt cho anh 50k ạ"   → tiệm không có thẩm quyền đó
    "dạ có bánh ăn kiêng ạ"          → tiệm không làm
    "dạ hình như đơn anh bị trễ"     → trợ lý không tra được đơn cũ

File này khoá các quy tắc đó trong prompt. Đây là test nội dung prompt, không
phải test hội thoại thật — chạy hội thoại thật cần Groq API và tốn tiền, nên
phần đó để người dùng nghiệm thu tay.
"""

from pathlib import Path

import pytest

from app.services.rag_service import SYSTEM_PROMPT_TEMPLATE

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def prompt() -> str:
    """Prompt đã gộp khoảng trắng.

    Prompt xuống dòng theo văn bản (80 cột), nên một cụm từ có thể bị ngắt giữa
    hai dòng. So khớp trên chuỗi thô sẽ báo "thiếu" trong khi câu vẫn có đủ —
    đúng lỗi này đã làm 2 test đỏ lần đầu.
    """
    return " ".join(SYSTEM_PROMPT_TEMPLATE.split())


@pytest.fixture(scope="module")
def prompt_lower(prompt) -> str:
    return prompt.lower()


class TestKhachMacCa:
    def test_cam_tu_giam_gia(self, prompt):
        """Trợ lý không có thẩm quyền giảm giá. Hứa rồi không giữ là mất uy tín."""
        assert "KHÔNG được tự giảm giá" in prompt

    def test_cam_hoi_xin_bot(self, prompt):
        assert "em xin bớt cho anh/chị" in prompt

    def test_chi_ra_duong_giam_gia_that(self, prompt):
        """Đường giảm giá thật là voucher đổi từ điểm, không phải mặc cả."""
        assert "voucher" in prompt.lower()
        assert "100 điểm" in prompt

    def test_goi_y_mau_re_hon_trong_ngan_sach(self, prompt):
        """Cách xử lý đắt: gợi ý mẫu khác rẻ hơn, không phải hạ giá."""
        assert "`find_cakes` với `budget`" in prompt


class TestKhachDoiY:
    def test_dung_thong_tin_moi_nhat(self, prompt):
        assert "thông tin MỚI NHẤT" in prompt

    def test_khong_cai_lai_khach(self, prompt):
        assert 'Đừng cãi "lúc nãy anh nói khác"' in prompt
    def test_xac_nhan_lai_truoc_khi_chot(self, prompt):
        assert "xác nhận lại" in prompt.lower()


class TestCauHoiNgoaiHieuBiet:
    @pytest.mark.parametrize(
        "topic",
        ["ăn kiêng", "nguồn nguyên liệu", "hoá đơn", "hình theo ảnh"],
    )
    def test_co_liet_ke_loai_cau_khong_duoc_bia(self, prompt, topic):
        assert topic in prompt

    def test_cam_bia_khi_khong_biet(self, prompt):
        assert "KHÔNG được bịa" in prompt

    def test_tha_noi_chua_ro_con_hon_hua(self, prompt):
        assert "em chưa rõ" in prompt


class TestKhachPhanNan:
    def test_giu_binh_tinh_va_xin_loi(self, prompt):
        assert "xin lỗi" in prompt.lower()

    def test_khong_doan_don_cu(self, prompt):
        """Trợ lý không tra được đơn cũ trong khung chat này."""
        assert "không tra được đơn cũ" in prompt
        assert "đừng đoán" in prompt.lower()

    def test_de_nghi_chuyen_hotline(self, prompt):
        assert "hotline" in prompt


class TestKhachDoaBoDi:
    def test_khong_niu_keo_bang_ha_gia(self, prompt):
        assert "Đừng níu kéo bằng cách hạ giá" in prompt

    def test_neu_diem_khac_biet_co_that(self, prompt):
        assert "điểm khác biệt có thật" in prompt


class TestCauNhapNhang:
    def test_hoi_lai_mot_cau_lam_ro(self, prompt):
        assert "Hỏi lại MỘT câu" in prompt

    def test_nhung_co_manh_moi_thi_khong_hoi_lai(self, prompt):
        """Hỏi lại khi đã có thông tin là làm khách sốt ruột."""
        assert "đừng hỏi lại" in prompt


class TestDoiThutiemKhongBan:
    def test_noi_that_ve_pham_vi_ban_hang(self, prompt):
        assert "tiệm chỉ bán bánh" in prompt


class TestChotDonDuThongTin:
    """Yêu cầu trực tiếp của người dùng: chốt đơn phải có đủ thông tin."""

    @pytest.mark.parametrize(
        "required",
        ["Tên bánh cụ thể + số lượng", "Ngày nhận", "Tên khách",
         "Số điện thoại khách", "Hình thức nhận"],
    )
    def test_danh_sach_bat_buoc(self, prompt, required):
        assert required in prompt, required

    def test_ghi_ro_sau_thong_tin(self, prompt):
        assert "ĐỦ **6 thứ**" in prompt

    def test_hoi_tung_cau_khong_hoi_don(self, prompt):
        """Hỏi dồn 5 câu một lúc làm khách bỏ đi."""
        assert "chỉ hỏi **một** câu" in prompt.lower() or "đừng hỏi dồn" in prompt


class TestGiaoHangKhongCongThemGio:
    def test_giao_hang_khong_anh_huong_thoi_gian_lam(self, prompt):
        """Nếu cộng thêm giờ vì 'phải giao' thì trợ lý hứa sai ngày."""
        assert "KHÔNG ảnh hưởng thời gian làm" in prompt
        assert "Đừng cộng thêm giờ" in prompt


class TestChatServicePassesCustomerId:
    def test_customer_id_duoc_gan_cho_cong_cu_tao_don(self):
        """Đơn phải thuộc đúng người đang chat; LLM không được tự khai id."""
        src = (BACKEND / "app/services/chat_service.py").read_text(encoding="utf-8")
        assert 'if name == "create_draft_order":' in src
        assert 'arguments["customer_id"] = customer_id' in src
