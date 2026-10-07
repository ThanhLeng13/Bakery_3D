"""Hợp đồng báo giá: cùng một cấu hình phải cho cùng một giá ở mọi nơi.

Bối cảnh
--------
Studio (price-calculator.ts) hiển thị 20cm + hoa + viền rosettes là 480.000đ
(350.000 size + 80.000 flowers + 50.000 rosettes), nhưng `cake_price('20cm')` ở
backend chỉ trả 350.000đ, và checkout cũng chỉ lấy giá theo size. Khách thấy
480.000đ rồi bị tính 350.000đ — chênh 130.000đ.

Quyết định nghiệp vụ 07/10/2026: **server là nguồn quyết định**, và server phải
tính đầy đủ size + topping + trang trí như Studio. Giao diện không tự giữ bảng
tiền riêng.

Các test ở đây khoá lại hợp đồng đó. Chạy trước khi sửa để thấy thất bại, sau khi
sửa để thấy đạt.
"""

from app.services.pricing import (
    CAKE_DECORATION_COSTS,
    CAKE_SIZE_PRICES,
    CAKE_TOPPING_COSTS,
    cake_price,
    normalize_size,
    price_breakdown,
)


# Cấu hình mà tài liệu kiểm kê nêu đang lệch 130.000đ.
CAU_HINH_20CM = {
    "size": "20cm",
    "topping_type": ["flowers"],
    "zones": {"border": {"decoration": "rosettes"}},
}

GIA_DOI_CHIEU = {
    "basePrice": 350_000,
    "toppingCost": 80_000,
    "decorationCost": 50_000,
    "totalPrice": 480_000,
}


class TestPriceContract:
    def test_cau_hinh_20cm_khong_con_rosettes_khong_con_hoa(self):
        """Cơ sở: chỉ size thì giá đúng bảng size."""
        assert cake_price("20cm") == 350_000

    def test_bang_gia_khop_voi_dien_toan_tay(self):
        """Giá phải cộng đúng từng khoản, không dùng số may mắn."""
        bd = price_breakdown(CAU_HINH_20CM)
        assert bd["base_price"] == GIA_DOI_CHIEU["basePrice"]
        assert bd["topping_cost"] == GIA_DOI_CHIEU["toppingCost"]
        assert bd["decoration_cost"] == GIA_DOI_CHIEU["decorationCost"]
        assert bd["total"] == sum(
            [bd["base_price"], bd["topping_cost"], bd["decoration_cost"]]
        )

    def test_cau_hinh_da_quet_phai_ra_480_000(self):
        """Đây là lỗi A. Trước khi sửa, hàm này trả về giá chỉ theo size."""
        assert price_breakdown(CAU_HINH_20CM)["total"] == GIA_DOI_CHIEU["totalPrice"]

    def test_tong_khong_phu_thuoc_thu_tu_khoa(self):
        """Cùng cấu hình, khác thứ tự key → cùng giá."""
        a = price_breakdown(CAU_HINH_20CM)
        b = price_breakdown(
            {
                "zones": CAU_HINH_20CM["zones"],
                "topping_type": CAU_HINH_20CM["topping_type"],
                "size": CAU_HINH_20CM["size"],
            }
        )
        assert a == b


class TestToppingAndDecoration:
    def test_topping_lap_lai_chi_tinh_mot_lan(self):
        """Khách chọn trùng không được bị tính hai lần."""
        bd = price_breakdown(
            {"size": "20cm", "topping_type": ["flowers", "flowers", " Flowers "]}
        )
        assert bd["topping_cost"] == 80_000

    def test_vien_ba_vien_duoc_tinh(self):
        """Trang trí tính trên cả ba vùng."""
        bd = price_breakdown(
            {
                "size": "20cm",
                "zones": {
                    "top": {"decoration": "piping"},
                    "body": {"decoration": "rosettes"},
                    "border": {"decoration": "pearls"},
                },
            }
        )
        assert bd["decoration_cost"] == 30_000 + 50_000 + 45_000

    def test_topping_khong_ho_p_le_gi_dinh_0(self):
        bd = price_breakdown({"size": "16cm"})
        assert bd["topping_cost"] == 0
        assert bd["decoration_cost"] == 0
        assert bd["total"] == 250_000

    def test_thieu_size_va_size_la_null_va_tinh_theo_kich_thuoc_mac_dinh(self):
        """Bánh không cần size vẫn phải có giá, không được lỗi."""
        for design in ({"size": None}, {}):
            assert price_breakdown(design)["total"] == 350_000

    def test_size_khong_hop_le_bao_loi_thay_vi_giu_gia_mac_dinh(self):
        """Kích cỡ lạ phải báo lỗi rõ, không âm thầm ra giá mặc định."""
        try:
            price_breakdown({"size": "ban-mot-met"})
        except ValueError:
            pass
        else:
            raise AssertionError("size không hỗ trợ phải ném ValueError")

    def test_kich_thuoc_hoa_thuong_va_viet_thuong_cho_cung_gia(self):
        assert price_breakdown({"size": "20CM"})["base_price"] == 350_000
        assert price_breakdown({"size": " 20cm "})["base_price"] == 350_000


class TestTwoTierLeadTime:
    def test_2_tang_duoc_nhan_dien_voi_moi_chu_hoa_khoang_trang(self):
        from app.services.pricing import is_two_tier

        assert is_two_tier("2-tier")
        assert is_two_tier(" 2-Tier ")
        assert not is_two_tier("20cm")
        assert not is_two_tier(None)


class TestTables:
    def test_bang_gia_size_dung_bon_kich_thuoc(self):
        assert CAKE_SIZE_PRICES == {
            "16cm": 250_000,
            "20cm": 350_000,
            "24cm": 450_000,
            "2-tier": 650_000,
        }

    def test_bang_topping_viend_co_bat_buoc(self):
        """Thêm topping mới phải cập nhật bảng, không rơi vào giá 0 âm thầm."""
        assert CAKE_TOPPING_COSTS["flowers"] == 80_000
        assert CAKE_DECORATION_COSTS["rosettes"] == 50_000
        assert all(v > 0 for v in CAKE_TOPPING_COSTS.values())
        assert all(v > 0 for v in CAKE_DECORATION_COSTS.values())

    def test_normalize_size_tra_chuoi_rong_khi_khong_dung_duoc(self):
        assert normalize_size(None) == ""
        assert normalize_size("") == ""
        assert normalize_size(123) == ""
        assert normalize_size(" 2-Tier ") == "2-tier"
