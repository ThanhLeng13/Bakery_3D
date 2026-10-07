"""Chặn đặt mẫu 3D chỉ-preview phải có hiệu lực ở server, không chỉ ở giao diện.

Bối cảnh
--------
Bốn mẫu chỉ xem (`heart-1-tier`, `round-3-tier`, `square-1-tier`,
`tall-1-tier`) chưa có giá và lead time được duyệt. Hai sản phẩm hình tim
đang trỏ tới `heart-1-tier` trong `product_3d_models`.

Nếu chỉ khoá nút "Thêm vào giỏ" thì gọi thẳng `POST /api/v1/orders` vẫn tạo
đơn được — và đơn đó thợ không làm được. Vì vậy ràng buộc nằm trong
`_catalog_price`, đúng bước mọi đơn đều phải đi qua.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.order_service import OrderService, OrderServiceError
from app.services.orderable_3d import ORDERABLE_MODEL_SLUGS

PRODUCT_ID = str(uuid4())


def _product_row(slug=None, base_price=690000, is_active=True):
    """Một sản phẩm kèm mô hình 3D (hoặc không có nếu slug=None)."""
    row = {"id": PRODUCT_ID, "base_price": base_price, "is_active": is_active}
    if slug is not None:
        row["product_3d_models"] = [{
            "is_primary": True,
            "cake_3d_models": {"id": str(uuid4()), "slug": slug},
        }]
    else:
        row["product_3d_models"] = []
    return row


class TestPreviewOnlyProductCannotBeOrdered:
    def test_san_pham_dung_mau_chi_xem_thi_bi_tu_choi(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value\
            .maybe_single.return_value.execute.return_value = MagicMock(
                data=_product_row("heart-1-tier")
            )
        service = OrderService(client)

        with pytest.raises(OrderServiceError) as exc:
            service._catalog_price(PRODUCT_ID)
        assert exc.value.status_code == 400
        assert "heart-1-tier" in exc.value.message

    def test_ma_lien_ket_tieu(self):
        """Không lọc nhầm khi model_id chỉ là vùng con của quan hệ."""
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value\
            .maybe_single.return_value.execute.return_value = MagicMock(
                data=_product_row("square-1-tier")
            )
        with pytest.raises(OrderServiceError):
            OrderService(client)._catalog_price(PRODUCT_ID)

    @pytest.mark.parametrize("slug", list(ORDERABLE_MODEL_SLUGS))
    def test_mau_duoc_duyet_thi_ban_duoc_va_dung_gia(self, slug):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value\
            .maybe_single.return_value.execute.return_value = MagicMock(
                data=_product_row(slug, base_price=690000)
            )
        assert OrderService(client)._catalog_price(PRODUCT_ID) == 690000

    def test_san_pham_khong_gan_mau_thi_ban_duoc(self):
        """Không có mô hình 3D là sản phẩm thường, không liên quan tới kho mô hình."""
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value\
            .maybe_single.return_value.execute.return_value = MagicMock(
                data=_product_row(None, base_price=275000)
            )
        assert OrderService(client)._catalog_price(PRODUCT_ID) == 275000


class TestPreviewCheckSeesThroughAFlagBypass:
    def test_khong_chon_primary_thi_van_bi_chan(self):
        """Dựa vào cờ is_primary là đủ để lách: phải kiểm tra mọi liên kết."""
        row = _product_row(None)
        row["product_3d_models"] = [{
            "is_primary": False,  # cố tình bỏ trống
            "cake_3d_models": {"id": str(uuid4()), "slug": "tall-1-tier"},
        }]
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value\
            .maybe_single.return_value.execute.return_value = MagicMock(data=row)

        with pytest.raises(OrderServiceError):
            OrderService(client)._catalog_price(PRODUCT_ID)

    def test_quan_he_tra_ve_danh_sach_thi_van_bi_chan(self):
        """PostgREST có thể trả phần tử quan hệ nhiều-một dưới dạng danh sách."""
        row = _product_row(None)
        row["product_3d_models"] = [{
            "is_primary": True,
            "cake_3d_models": [{"id": str(uuid4()), "slug": "round-3-tier"}],
        }]
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value\
            .maybe_single.return_value.execute.return_value = MagicMock(data=row)

        with pytest.raises(OrderServiceError):
            OrderService(client)._catalog_price(PRODUCT_ID)


class TestOrderPathRefusesPreviewOnlyProduct:
    """Chặn phải có hiệu lực khi tạo đơn, không chỉ khi đọc giá."""

    def _service(self, row):
        client = MagicMock()
        table = client.table.return_value
        table.select.return_value.eq.return_value.maybe_single.return_value\
            .execute.return_value = MagicMock(data=row)
        return OrderService(client), client

    def test_dat_hang_bang_mau_chi_xem_thi_that_bai(self):
        service, client = self._service(_product_row("heart-1-tier"))

        with pytest.raises(OrderServiceError):
            service.create_order(
                {
                    "full_name": "Test",
                    "phone": "0901234567",
                    "email": None,
                    "pickup_date": None,  # chặn trước cả kiểm tra ngày
                    "items": [{
                        "product_id": PRODUCT_ID,
                        "quantity": 1,
                        "unit_price": 1,
                    }],
                    "ai_summary": None,
                },
                {"id": str(uuid4())},
            )

        # Và không được ghi gì xuống CSDL.
        assert not client.rpc.call_args_list, "phải chặn trước khi ghi đơn"