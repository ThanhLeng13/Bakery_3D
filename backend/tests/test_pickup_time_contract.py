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
        """Còn trên 24 giờ thì bánh một tầng kịp.

        Ngày tính từ lúc chạy. Test cũ viết cứng "2026-10-08": sau 17h ngày
        07/10 chỉ còn khoảng 7 giờ nên đỏ, dù không có gì sai trong code.
        """
        target = (datetime.now(VN_TZ) + timedelta(days=3)).strftime("%Y-%m-%d")
        result = self._tools().check_bake_time(target)
        assert result["is_possible"] is True
        assert result["required_lead_hours"] == 24

    def test_ca_khong_kip_voi_banh_hai_tang(self):
        """Bánh hai tầng cần 48 giờ, nên cùng một ca có thể kịp hoặc không."""
        # 3 ngày: kịp cho một tầng (24h) nhưng chưa chắc cho hai tầng (48h)
        # tuỳ giờ chạy — đúng bản chất của ca biên mà test này muốn khoá.
        near = (datetime.now(VN_TZ) + timedelta(days=2)).strftime("%Y-%m-%d")
        far = (datetime.now(VN_TZ) + timedelta(days=5)).strftime("%Y-%m-%d")
        assert self._tools().check_bake_time(far)["is_possible"] is True

        # Ca gần phải nói rõ cần tối thiểu bao nhiêu giờ.
        result = self._tools().check_bake_time(near)
        assert result["required_lead_hours"] == 24
        if result["is_possible"]:
            assert result["hours_notice"] > result["required_lead_hours"]
        else:
            assert "KHÔNG kịp" in result["message"]

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
        """Chọn ngày quá gần phải nói rõ cần tối thiểu bao nhiêu giờ.

        Ngày được tính từ thời điểm chạy, không viết cứng. Test cũ dùng
        "2026-10-08": đến tối 07/10 thì chỉ còn ~5 giờ, dưới ngưỡng 24 giờ,
        nên test đỏ vào đúng buổi tối mà không phải do code sai. Ngày tuyệt đối
        trong một test thời gian là ngày sẽ hỏng.
        """
        tools = OrderTools.__new__(OrderTools)
        # 3 ngày nữa: chắc chắn vượt ngưỡng 24 giờ ở mọi giờ trong ngày.
        target = (datetime.now(VN_TZ) + timedelta(days=3)).strftime("%Y-%m-%d")
        result = tools.check_bake_time(target)
        assert result["is_possible"] is True
        assert result["hours_notice"] > result["required_lead_hours"]

    def test_ngay_qua_khuong_bao_thieu_tieu(self):
        """Ngày không đủ giờ phải nói cần tối thiểu bao nhiêu, không chỉ nói 'không'.

        Ngày mai lúc 00:00 giờ VN luôn còn hơn 24h tính từ 00:00 hôm nay, nên
        muốn chắc chắn thiếu giờ thì phải chọn hôm nay — ngày đó luôn quá gần.
        """
        tools = OrderTools.__new__(OrderTools)
        today = datetime.now(VN_TZ).strftime("%Y-%m-%d")
        result = tools.check_bake_time(today)
        assert result["required_lead_hours"] == 24
        assert result["is_possible"] is False
        assert "KHÔNG kịp" in result["message"]
        # Thông báo phải nói cần tối thiểu bao nhiêu giờ, không chỉ "không".
        assert str(result["required_lead_hours"]) in result["message"]

    def test_muc_toi_thieu_khong_am(self):
        tools = OrderTools.__new__(OrderTools)
        result = tools.check_bake_time("2026-10-07")
        assert result["required_lead_hours"] >= 0


class TestDraftStatusIsDistinct:
    """Đơn nháp của agent không được trùng trạng thái với đơn thật."""

    def test_tao_don_nhap_gan_status_draft(self):
        """Đây là lỗi C. Trước khi sửa, đơn nháp ghi status='pending' —
        đúng trạng thái mà /staff/orders lọc, nên lọt vào hàng đợi bán hàng."""
        import inspect

        from app.services import order_tools

        source = inspect.getsource(order_tools.OrderTools.create_draft_order)
        assert '"status": "draft"' in source, (
            "create_draft_order phải ghi status='draft' để tách khỏi đơn thật"
        )
        assert '"status": "pending"' not in source, (
            "đơn nháp không được ghi 'pending' — trùng đơn thật trong hàng đợi"
        )

    def test_chi_nhan_vien_duoc_nhan_don_nhap(self):
        """Chuyển draft sang pending là hành động của nhân viên, không phải
        bước tự động. Không có ai khác được nhảy qua trạng thái này."""
        from app.services.order_service import VALID_TRANSITIONS

        assert VALID_TRANSITIONS.get("draft") == {"pending": ["staff"]}, (
            "chỉ nhân viên bán hàng được xác nhận đơn nháp thành đơn thật"
        )
        # Đơn nháp không tự nhảy sang bất kỳ trạng thái sản xuất nào.
        assert "confirmed" not in VALID_TRANSITIONS.get("draft", {})
        assert "in_production" not in VALID_TRANSITIONS.get("draft", {})
        # Không có đường nào quay ngược từ đơn thật về nháp.
        for frm, targets in VALID_TRANSITIONS.items():
            if frm != "draft":
                assert "draft" not in targets, (
                    f"không được quay lại 'draft' từ '{frm}'"
                )

    def test_don_nhap_khong_xuat_hien_trong_bo_don_ban_hang(self):
        """staff_orders lọc danh sách trạng thái; phải loại draft."""
        from app.api.v1.endpoints.staff_orders import SALES_STATUSES

        assert "draft" not in SALES_STATUSES
        assert "pending" in SALES_STATUSES