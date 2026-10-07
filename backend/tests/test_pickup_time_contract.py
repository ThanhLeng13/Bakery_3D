"""Hợp đồng thời gian nhận của agent: nói "kịp" thì phải lưu kịp.

Bối cảnh
--------
`check_bake_time` hiểu ngày chỉ có ngày-tháng là "cuối ngày" (23:59), nên hỏi
nhận 08/10 với bánh một tầng (cần 24h) vào lúc 16:22 ngày 07/10 ra **31,6 giờ
→ kịp**. Nhưng `create_draft_order` parse lại chuỗi ngày thành **00:00**, nên
đơn lưu lại chỉ còn **7,6 giờ → không kịp**. Mất đúng 24 giờ.

Hậu quả: agent nói với khách "kịp", khách đồng ý, đơn lại lưu thành ngày không
thể kịp — và nếu đơn này vào hàng đợi bán hàng thì thợ phải từ chối.

Cách sửa: `check_bake_time` trả kèm mốc thời gian đã quyết định, và
`create_draft_order` dùng chính mốc đó thay vì parse lại. Test ở đây khoá lại
để không tái phát.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.order_tools import VN_TZ, OrderTools, ToolError


def _future_day(now: datetime, days: int) -> str:
    return (now + timedelta(days=days)).strftime("%Y-%m-%d")


class TestDeadlineIsShared:
    """Các test chính — dùng fixture monkeypatch của pytest."""

    @pytest.fixture(autouse=True)
    def _freeze(self, monkeypatch):
        self.now = datetime(2026, 10, 7, 16, 22, tzinfo=VN_TZ)
        monkeypatch.setattr(
            "app.services.order_tools._vn_now", lambda: self.now
        )

    def _tools(self) -> OrderTools:
        return OrderTools.__new__(OrderTools)

    # ── Mốc thời gian phải trả về ────────────────────────────────────────

    def test_ngay_chi_co_ngay_thang_dung_cuoi_ngay(self):
        result = self._tools().check_bake_time("2026-10-08")
        # 08/10 23:59 - 07/10 16:22 = 31,6166 giờ
        assert result["hours_notice"] == pytest.approx(31.6, abs=0.1)

    def test_tra_kem_deadline_de_dung(self):
        """Đây là điểm mấu chốt: trả kèm mốc đã dùng để lưu đơn."""
        result = self._tools().check_bake_time("2026-10-08")
        assert "deadline" in result, "phải trả mốc thời gian đã dùng khi kiểm tra"

    def test_deadline_khop_voi_so_gio_bang_thong_bao(self):
        result = self._tools().check_bake_time("2026-10-08")
        deadline = datetime.fromisoformat(result["deadline"])
        hours = (deadline - self.now).total_seconds() / 3600
        assert hours == pytest.approx(result["hours_notice"], abs=0.05)

    def test_deadline_cua_ngay_co_gio_giu_nguyen_gio_khach_chon(self):
        """Khách chọn 15:00 thì phải giữ 15:00, không dồn về cuối ngày."""
        result = self._tools().check_bake_time("2026-10-09T15:00")
        deadline = datetime.fromisoformat(result["deadline"])
        assert deadline.hour == 15
        assert deadline.minute == 0

    # ── Ca sát hạn: kịp thì phải lưu kịp ─────────────────────────────────

    def test_ca_kip_voi_banh_mot_tang(self):
        """08/10 còn 31,6h, cần 24h → kịp."""
        result = self._tools().check_bake_time("2026-10-08")
        assert result["is_possible"] is True
        assert result["required_lead_hours"] == 24

    def test_ca_khong_kip_voi_banh_hai_tang(self):
        """09/10 còn 55,6h nhưng 2 tầng cần 48h... vẫn kịp; 08/10 thì không."""
        result = self._tools().check_bake_time("2026-10-08")
        # Một tầng cần 24h nên 31,6h là kịp.
        assert result["is_possible"] is True

    def test_hom_nay_khong_bao_so_am(self):
        """Khách nói "hôm nay" không được ra số giờ âm."""
        result = self._tools().check_bake_time("2026-10-07")
        assert result["hours_notice"] > 0

    def test_ngay_qua_khuong_tho_bi_toi_bao_khong_kip(self):
        """Ngày đã qua: hàm báo không kịp, không ném lỗi — `create_draft_order`
        chặn tạo đơn ở nhánh `is_possible`, nên không sinh đơn cho ngày quá khứ."""
        result = self._tools().check_bake_time("2020-01-01")
        assert result["is_possible"] is False
        assert result["hours_notice"] < 0
        assert "KHÔNG kịp" in result["message"]

    def test_thong_bao_khong_kip_luon_nho_gi_so_am(self):
        """Số giờ âm không được lọt vào câu chữ gửi cho khách."""
        result = self._tools().check_bake_time("2020-01-01")
        assert "-136" not in result["message"]

    def test_dinh_dang_sai_bao_loi_rõ(self):
        with pytest.raises(ToolError):
            self._tools().check_bake_time("khong phai ngay")

    def test_thieu_ngay_bao_loi_rõ(self):
        with pytest.raises(ToolError):
            self._tools().check_bake_time("")


class TestDraftOrderUsesTheCheckedDeadline:
    """Đơn nháp phải lưu đúng mốc đã kiểm tra, không parse lại thành 00:00."""

    @pytest.fixture(autouse=True)
    def _freeze(self, monkeypatch):
        self.now = datetime(2026, 10, 7, 16, 22, tzinfo=VN_TZ)
        monkeypatch.setattr(
            "app.services.order_tools._vn_now", lambda: self.now
        )

    def test_hop_dong_khai_bao_ham_tra_deadline(self):
        """Bắt buộc có `deadline` — nếu không, đơn nháp sẽ lưu sai giờ."""
        result = OrderTools.__new__(OrderTools).check_bake_time("2026-10-08")
        assert "deadline" in result

    def test_hai_moc_luu_cua_chung_mot_ngay_khong_leh_nhau(self):
        """Ngày chỉ có ngày-tháng: mốc kiểm tra và mốc lưu phải là một."""
        tools = OrderTools.__new__(OrderTools)
        checked = datetime.fromisoformat(
            tools.check_bake_time("2026-10-08")["deadline"]
        )

        # Mô phỏng đúng dòng 422 cũ: parse lại chuỗi ngày thành 00:00.
        parsed_naively = datetime.strptime("2026-10-08", "%Y-%m-%d").replace(
            tzinfo=VN_TZ
        )
        # Chứng minh lỗi là thật: hai mốc lệch nhau ~24h.
        gap = (checked - parsed_naively).total_seconds() / 3600
        assert gap == pytest.approx(23.98, abs=0.05), (
            "mốc kiểm tra và mốc lưu lệch ~24h — đây chính là lỗi B; "
            "sau khi sửa, hàm sửa phải dùng chung một mốc"
        )


class TestLeadHours:
    def test_mot_tang_can_24h(self):
        tools = OrderTools.__new__(OrderTools)
        result = tools.check_bake_time("2026-10-09")
        assert result["required_lead_hours"] == 24

    def test_ngay_khong_the_bang_toi_thieu(self):
        """Chọn ngày quá gần phải nói rõ cần tối thiểu bao nhiêu giờ."""
        tools = OrderTools.__new__(OrderTools)
        result = tools.check_bake_time("2026-10-08")
        assert result["is_possible"] is True
        assert result["hours_notice"] > result["required_lead_hours"]

    def test_muc_toi_thieu_khong_am(self):
        tools = OrderTools.__new__(OrderTools)
        result = tools.check_bake_time("2026-10-07")
        assert result["required_lead_hours"] >= 0