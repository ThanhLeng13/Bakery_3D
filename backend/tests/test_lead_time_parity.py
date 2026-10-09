"""Hợp đồng thời gian nhận: agent và checkout phải tính giống nhau.

Bối cảnh
--------
Trước đây có hai bản quy tắc tách rời:

* `order_tools._lead_hours(name)` suy ra độ phức tạp từ **tên sản phẩm**,
  tìm các từ khoá "2 tầng", "3 tầng", "figure"…
* `order_service._validate_pickup_date` suy ra từ **kích thước** khách chọn,
  qua `pricing.is_two_tier(size)`.

Hai nguồn đó không thuộc cùng một thứ, nên cùng một đơn cho ra hai đáp án khác
nhau — đo được 4/4 ca, mỗi ca lệch đúng 24 giờ:

| Tên sản phẩm (agent đọc) | Size (checkout đọc) | Agent | Checkout |
|---|---|---|---|
| Bánh kem 2 tầng hoa hồng phấn | 20cm | 48h | 24h |
| Bánh kem figure ông bà | 20cm | 48h | 24h |
| Bánh chocolate truyền thống | 2-tier | 24h | 48h |

Hậu quả: agent hứa khách "kịp" 48h rồi checkout từ chối, hoặc ngược lại agent
nói phải chờ 48h trong khi đơn lẽ ra chỉ cần 24h. Cả hai đều là thông tin sai
với khách.

Cách sửa: một nơi duy nhất quyết định — `order_service._validate_pickup_date`,
vì đó là nơi chặn đơn thật. Agent gọi chung hàm đó thay vì tự suy luận.
"""

from datetime import datetime, timedelta

import pytest

from app.services.order_service import (
    MIN_LEAD_HOURS,
    MIN_LEAD_HOURS_COMPLEX,
    OrderService,
    PickupDateValidationError,
)
from app.services.order_tools import OrderTools
from app.services.pricing import lead_hours_for_items

VN_TZ = __import__("datetime").timezone(timedelta(hours=7))


def _tools():
    return OrderTools.__new__(OrderTools)


def _hours_from_now(hours: float) -> str:
    """Ngày nhận cách 'bây giờ' đúng số giờ yêu cầu, định dạng ISO."""
    return (
        datetime.now(VN_TZ) + timedelta(hours=hours)
    ).isoformat()


class TestLeadHoursSingleSource:
    """Một quy tắc duy nhất, dùng chung cho agent và checkout."""

    def test_hang_so_dung_chung(self):
        """Hai hằng số phải là một, không phải hai bản chép rời."""
        assert MIN_LEAD_HOURS == 24
        assert MIN_LEAD_HOURS_COMPLEX == 48

    @pytest.mark.parametrize(
        "items, expected",
        [
            ([{"size": "20cm"}], MIN_LEAD_HOURS),
            ([{"size": "25cm"}], MIN_LEAD_HOURS),
            ([{"size": "2-tier"}], MIN_LEAD_HOURS_COMPLEX),
            ([{"size": "2-tier", "name": "Bánh tiramisu"}], MIN_LEAD_HOURS_COMPLEX),
            ([{"size": "20cm"}, {"size": "2-tier"}], MIN_LEAD_HOURS_COMPLEX),
            ([], MIN_LEAD_HOURS),
        ],
    )
    def test_lead_hours_theo_size(self, items, expected):
        """Quy tắc lấy từ size — cùng nguồn checkout dùng."""
        assert lead_hours_for_items(items) == expected

    def test_ten_san_pham_khong_con_quyet_dinh(self):
        """Tên có chữ '2 tầng' nhưng size 20cm thì vẫn là bánh một tầng.

        Trước đây agent đọc tên và tính 48h cho ca này, checkout tính 24h.
        """
        items = [{"size": "20cm", "name": "Bánh kem 2 tầng hoa hồng phấn"}]
        assert lead_hours_for_items(items) == MIN_LEAD_HOURS

    def test_size_2_tier_quy_dinh_du_khong_co_ten_phuc_tap(self):
        """Ngược lại: tên trông đơn giản nhưng size 2-tier thì vẫn 48h."""
        items = [{"size": "2-tier", "name": "Bánh chocolate truyền thống"}]
        assert lead_hours_for_items(items) == MIN_LEAD_HOURS_COMPLEX


class TestAgentAndCheckoutAgree:
    """Cùng một đơn, agent và checkout phải cho cùng một đáp án."""

    CASES = [
        ("Bánh kem 2 tầng hoa hồng phấn", "20cm"),
        ("Bánh kem figure ông bà chữ Happy", "20cm"),
        ("Bánh chocolate truyền thống", "2-tier"),
        ("Bánh tiramisu truyền thống", "25cm"),
    ]

    @pytest.mark.parametrize("name, size", CASES)
    def test_hai_noi_tinh_giong_nhau(self, name, size):
        """Cùng một đơn, hai nơi phải ra cùng một con số.

        Thử ở cả hai phía của ngưỡng: sớm hơn và muộn hơn. Chỉ cần một phía thì
        hàm nào trả về hằng số cũng "đúng", nên phải kiểm cả hai chiều mới lộ
        ra việc hai bên tính khác nhau.

        Lề nửa giờ mỗi phía là bắt buộc: `now` trong hàm được lấy sau khi test
        đã tính mốc, nên "đúng 24 giờ" thực tế là 23 giờ 59 giây 59.
        """
        items = [{"size": size, "name": name}]
        agent = lead_hours_for_items(items)
        service = _service_stub()

        for lead, verdict in (
            (agent + 0.5, "kịp"),
            (agent - 0.5, "không kịp"),
        ):
            try:
                service._validate_pickup_date(_in_hours(lead), items)
                actual = "kịp"
            except PickupDateValidationError:
                actual = "không kịp"
            assert actual == verdict, (
                f"{name} size={size}: nhận sau {lead}h, checkout nói {actual}, "
                f"agent nói cần {agent}h"
            )


def _in_hours(hours: float) -> datetime:
    return datetime.now(VN_TZ) + timedelta(hours=hours)


def _service_stub():
    """OrderService chỉ cần _validate_pickup_date, không cần kết nối CSDL."""
    return OrderService.__new__(OrderService)


class TestReasonAndSuggestion:
    """Không kịp thì phải nói rõ cần tối thiểu bao nhiêu và gợi ý ngày."""

    def test_thieu_gio_bi_loi_va_noi_ro_so_gio(self):
        service = _service_stub()
        with pytest.raises(PickupDateValidationError) as exc:
            service._validate_pickup_date(_in_hours(2), [{"size": "20cm"}])
        msg = str(exc.value)
        assert "24" in msg

    def test_banh_hai_tang_can_48h(self):
        service = _service_stub()
        with pytest.raises(PickupDateValidationError) as exc:
            service._validate_pickup_date(_in_hours(30), [{"size": "2-tier"}])
        assert "48" in str(exc.value)

    def test_agent_bao_khong_kip_theo_ngay_ban_chon(self):
        """`check_bake_time` dùng ngưỡng mặc định khi chưa biết khách chọn size.

        Hàm này chỉ nhận ngày, chưa nhận danh sách món, nên chỉ có thể dùng mức
        một tầng (24h). Mức 48h chỉ chốt được khi khách đã chọn 2-tier — và khi
        đó `create_draft_order` gọi lại `order_service` để kiểm. Ghi rõ giới
        hạn này thay vì giả định hàm đoán được theo tên.
        """
        tools = _tools()
        # Ba ngày nữa chắc chắn vượt 24h ở mọi giờ trong ngày.
        result = tools.check_bake_time(
            (datetime.now(VN_TZ) + timedelta(days=3)).strftime("%Y-%m-%d")
        )
        assert result["required_lead_hours"] == MIN_LEAD_HOURS
        assert result["is_possible"] is True

    def test_agent_bao_thieu_gio_bi_tu_choi(self):
        """Hôm nay không kịp và phải nói rõ cần tối thiểu bao nhiêu."""
        tools = _tools()
        today = datetime.now(VN_TZ).strftime("%Y-%m-%d")
        result = tools.check_bake_time(today)
        assert result["required_lead_hours"] == MIN_LEAD_HOURS
        assert result["is_possible"] is False
        assert "KHÔNG kịp" in result["message"]
        assert "24" in result["message"]