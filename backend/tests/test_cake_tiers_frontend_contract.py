"""Kiểm tra cấu trúc: Studio không được có "2 tầng" trong danh sách kích thước.

Số tầng thuộc về mẫu thân bánh (`CakeModelPicker`), nên mọi bảng lựa chọn kích
thước chỉ được chứa đường kính. Test này đọc mã nguồn vì lỗi gốc là một mục
thừa trong danh sách UI, và trình duyệt không cần chạy để phát hiện.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    """Đọc một file UTF-8 trong repo."""
    return (ROOT / relative).read_text(encoding="utf-8")


class TestSizeListsContainOnlyDiameters:
    def test_size_selector_khong_co_2_tang(self):
        src = _read("frontend/src/components/cake-builder/SizeSelector.tsx")
        assert 'value: "2-tier"' not in src, (
            "SizeSelector không được có '2 tầng': số tầng do mẫu bánh quyết định"
        )
        for diameter in ('"16cm"', '"20cm"', '"24cm"'):
            assert diameter in src

    def test_configurator_rail_khong_co_2_tang_trong_size_options(self):
        src = _read("frontend/src/components/cake-builder/ConfiguratorRail.tsx")
        size_block = src[src.index("const SIZE_OPTIONS"):src.index("const FLAVOR_OPTIONS")]
        assert '"2-tier"' not in size_block, (
            "SIZE_OPTIONS chỉ được chứa đường kính, không chứa số tầng"
        )

    def test_mau_hai_tang_cho_phep_duong_kinh(self):
        """Mẫu `round-2-tier` vẫn phải chọn được 16/20/24cm."""
        src = _read("frontend/src/lib/cake-body-models.ts")
        start = src.index('"round-2-tier": {')
        block = src[start:src.index('"round-3-tier": {')]
        assert '"2-tier"' not in block, "kích thước của mẫu 2 tầng phải là đường kính"
        for diameter in ('"16cm"', '"20cm"', '"24cm"'):
            assert diameter in block

    def test_doi_mau_khong_ep_size_2_tier(self):
        src = _read("frontend/src/hooks/useCakeBuilder.ts")
        assert 'modelSlug === "round-2-tier" ? "2-tier"' not in src, (
            "đổi mẫu không được tự gán kích thước '2-tier'"
        )


class TestTierEditingStillWorks:
    def test_3d_doc_so_tang_tu_mau(self):
        src = _read("frontend/src/components/cake-builder/Cake3D.tsx")
        # Mã thật gán `const tiers = tiersForDesign(design)` rồi so `tiers >= 2`.
        assert "tiersForDesign(design)" in src, (
            "khung 3D phải đọc số tầng từ mẫu, không từ kích thước"
        )
        assert "tiers >= 2" in src, "nhánh dựng bánh nhiều tầng phải theo số tầng"

    def test_checkout_doc_so_tang_tu_mau(self):
        src = _read("frontend/src/app/checkout/page.tsx")
        assert "tiersForDesign(cakeDesign) >= 2" in src, (
            "mốc 24/48 giờ ở checkout phải theo số tầng của mẫu"
        )


class TestOutlineMeasurementNeverThrows:
    def test_do_viền_bánh_khong_nem_loi_lam_sap_trang(self):
        """Lỗi 'Cannot measure cake outline at N' từng làm trắng cả trang Studio."""
        src = _read("frontend/src/components/cake-builder/cake-decoration-surface.ts")
        # Kiểm LỆNH ném lỗi, không kiểm chữ trong comment giải thích: comment
        # có nhắc lại thông điệp cũ nên so khớp chuỗi thô sẽ báo sai.
        assert "throw new Error(`Cannot measure cake outline" not in src, (
            "không được ném lỗi khi tia đo viền trượt mesh"
        )
        assert "if (!hit) {" in src, "phải xử lý trường hợp tia trượt"
        assert "fallbackRadius" in src, "phải có bán kính dự phòng khi tia trượt"
