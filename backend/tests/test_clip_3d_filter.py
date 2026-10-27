"""Chế độ tìm mẫu 3D: chỉ trả sản phẩm có mô hình hợp lệ.

Bối cảnh
---------
Đề tài yêu cầu: "tải ảnh lên dẫn tới mẫu 3D xem được". Trước đây
`search_by_image` trả về MỌI sản phẩm trong kho, kể cả sản phẩm không gắn
mô hình 3D nào. Khách bấm vào kết quả đó, tới trang sản phẩm, và không thấy
viewer — hứa một đằng, làm một nẻo.

Đo được trên CSDL thật (26/10): kho có 101 bánh sinh nhật đang bán nhưng chỉ
**3** sản phẩm có mapping 3D. Tức là 98/101 kết quả tìm ảnh trước đây không
mở được viewer.

"Hợp lệ" nghĩa là đủ ba điều kiện:
    - sản phẩm còn đang bán
    - mô hình còn active
    - có mapping trỏ tới mô hình thật

Thiếu một điều kiện thì viewer không mở được, nên phải loại mẫu đó.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.clip_service import ClipSearchService, ClipServiceError


def _png() -> bytes:
    """Ảnh PNG hợp lệ, nhỏ nhất có thể."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
        b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _embedding() -> list[float]:
    return [0.1] * 512


def _row(pid: str, name: str, similarity: float = 0.8) -> dict:
    return {
        "product_id": pid,
        "product_name": name,
        "image_url": f"https://img.test/{pid}.jpg",
        "category": "sinh nhat",
        "product_type": "cake",
        "base_price": 350000,
        "similarity": similarity,
    }


def _link(pid: str, slug: str, glb: str, is_active: bool = True,
          is_primary: bool = True) -> dict:
    return {
        "product_id": pid,
        "sort_order": 0,
        "is_primary": is_primary,
        "cake_3d_models": {
            "id": f"model-{slug}",
            "slug": slug,
            "name": slug,
            "glb_url": glb,
            "thumbnail_url": None,
            "is_active": is_active,
        },
    }


def _service(rows, links) -> ClipSearchService:
    """Service với RPC trả `rows` và bảng mapping trả `links`."""
    client = MagicMock()
    client.rpc.return_value.execute.return_value = MagicMock(data=rows)
    client.table.return_value.select.return_value.in_.return_value.execute.return_value = (
        MagicMock(data=links)
    )
    return ClipSearchService(client)


def _search(service, **kwargs):
    with patch(
        "app.services.clip_service.embed_image_bytes", return_value=_embedding()
    ):
        return service.search_by_image(_png(), **kwargs)


class TestChiTraSanPhamCo3D:
    """Lọc theo mô hình 3D."""

    def test_loai_bo_san_pham_khong_co_mapping(self):
        service = _service(
            [_row("p1", "Bánh A"), _row("p2", "Bánh B")],
            [_link("p1", "round-1-tier", "/models/a.glb")],
        )
        result = _search(service, has_3d_model=True)
        names = [r["name"] for r in result["results"]]
        assert names == ["Bánh A"], f"phai chi con san pham co 3D, got {names}"

    def test_khong_loc_thi_van_tra_tat_ca(self):
        """Mặc định không lọc — hành vi cũ phải giữ nguyên."""
        service = _service(
            [_row("p1", "Bánh A"), _row("p2", "Bánh B")],
            [_link("p1", "round-1-tier", "/models/a.glb")],
        )
        result = _search(service)
        assert result["count"] == 2

    def test_ket_qua_mang_thong_tin_3d(self):
        """Kết quả phải mang mô hình để mở được viewer."""
        service = _service(
            [_row("p1", "Bánh A")],
            [_link("p1", "round-1-tier", "/models/a.glb")],
        )
        result = _search(service, has_3d_model=True)
        model = result["results"][0]["three_d_model"]
        assert model is not None
        assert model["slug"] == "round-1-tier"
        assert model["glb_url"] == "/models/a.glb"

    def test_ma_3d_hoi_trong_ket_qua_khong_co_3d(self):
        """Không lọc nhưng vẫn báo mô hình nếu có, để giao diện hiện nút."""
        service = _service(
            [_row("p1", "Bánh A"), _row("p2", "Bánh B")],
            [_link("p1", "round-1-tier", "/models/a.glb")],
        )
        result = _search(service)
        by_id = {r["product_id"]: r for r in result["results"]}
        assert by_id["p1"]["three_d_model"] is not None
        assert by_id["p2"]["three_d_model"] is None


class TestMappingHopLe:
    """Ba điều kiện của một mapping hợp lệ."""

    def test_mo_hinh_khong_active_thi_loai(self):
        """Mô hình đã ngừng hoạt động thì không xem được."""
        service = _service(
            [_row("p1", "Bánh A")],
            [_link("p1", "heart-1-tier", "/models/h.glb", is_active=False)],
        )
        result = _search(service, has_3d_model=True)
        assert result["count"] == 0

    def test_mo_hinh_co_nhieu_mapping_thi_uu_tien_primary(self):
        service = _service(
            [_row("p1", "Bánh A")],
            [
                _link("p1", "square-1-tier", "/models/s.glb", is_primary=False),
                _link("p1", "round-1-tier", "/models/r.glb", is_primary=True),
            ],
        )
        result = _search(service, has_3d_model=True)
        assert result["results"][0]["three_d_model"]["slug"] == "round-1-tier"

    def test_khong_co_bang_mapping_thi_tra_rong(self):
        """Migration chưa chạy thì không được lỗi 500."""
        client = MagicMock()
        client.rpc.return_value.execute.return_value = MagicMock(
            data=[_row("p1", "Bánh A")]
        )
        client.table.return_value.select.return_value.in_.return_value.execute.side_effect = (
            Exception("relation does not exist")
        )
        service = ClipSearchService(client)
        result = _search(service, has_3d_model=True)
        assert result["count"] == 0

    def test_lỗi_kết_nối_thì_phải_nổi_lên_không_phải_rỗng(self):
        """Mất mạng KHÔNG được biến thành "không có kết quả".

        Nuốt lỗi sẽ khiến chế độ chỉ-mẫu-3D trả HTTP 200 với 0 kết quả, khách
        tưởng kho không có mẫu 3D nào — trong khi thực ra là hỏng đường truyền.
        """
        client = MagicMock()
        client.rpc.return_value.execute.return_value = MagicMock(
            data=[_row("p1", "Bánh A")]
        )
        client.table.return_value.select.return_value.in_.return_value.execute.side_effect = (
            Exception("connection refused")
        )
        service = ClipSearchService(client)
        with pytest.raises(ClipServiceError) as exc:
            _search(service, has_3d_model=True)
        assert exc.value.status_code == 503

    def test_lỗi_mapping_không_chặn_kết_quả_khi_không_lọc_3d(self):
        """Không lọc 3D: mapping chỉ là thông tin phụ, hỏng thì bỏ qua.

        Khác với trường hợp lọc 3D ở trên. Ở đây khách vẫn phải thấy danh sách
        sản phẩm — chỉ là không có nút "Xem 3D" để bấm. Chặn cả danh sách vì
        một bảng phụ đọc hỏng là đánh đổi sai.
        """
        client = MagicMock()
        client.rpc.return_value.execute.return_value = MagicMock(
            data=[_row("p1", "Bánh A"), _row("p2", "Bánh B")]
        )
        client.table.return_value.select.return_value.in_.return_value.execute.side_effect = (
            Exception("connection refused")
        )
        service = ClipSearchService(client)

        result = _search(service)  # không truyền has_3d_model
        assert result["count"] == 2
        assert all(r["three_d_model"] is None for r in result["results"])

    def test_lỗi_mapping_không_chặn_khi_lọc_kiểu_sản_phẩm(self):
        """Lọc theo `product_type` nhưng KHÔNG lọc 3D: cũng phải bỏ qua lỗi."""
        client = MagicMock()
        client.rpc.return_value.execute.return_value = MagicMock(
            data=[_row("p1", "Bánh A")]
        )
        client.table.return_value.select.return_value.in_.return_value.execute.side_effect = (
            Exception("connection refused")
        )
        service = ClipSearchService(client)

        result = _search(service, product_type="cake")
        assert result["count"] == 1


class TestPhanLoaiLoi:
    """`_is_missing_table_error` chỉ nhận lỗi BẢNG không tồn tại.

    Phân loại sai ở đây rất tốn kém: nuốt lỗi cột/hàm không tồn tại thành
    "bảng chưa có" sẽ che mất lỗi schema thật, và hệ thống im lặng trả về 0
    mô hình 3D thay vì báo cho người vận hành biết migration hỏng.
    """

    @pytest.mark.parametrize(
        "message",
        [
            "PGRST205: Could not find the table 'public.product_3d_models'",
            "could not find the table",
            "42P01",
            'relation "product_3d_models" does not exist',
            "table does not exist",
        ],
    )
    def test_nhan_dung_loi_bang_khong_ton_tai(self, message):
        from app.services.clip_service import _is_missing_table_error

        assert _is_missing_table_error(Exception(message)) is True

    @pytest.mark.parametrize(
        "message",
        [
            # Lỗi CỘT — không phải bảng. Nuốt nhầm là che mất lỗi migration.
            "column cake_3d_models.slug does not exist",
            # Lỗi HÀM — RPC sai chữ ký.
            "function match_cakes(vector, int) does not exist",
            "connection refused",
            "ReadTimeout",
            "WinError 10054 An existing connection was forcibly closed",
            "invalid API key",
        ],
    )
    def test_khong_nhan_nham_loi_khac(self, message):
        from app.services.clip_service import _is_missing_table_error

        assert _is_missing_table_error(Exception(message)) is False


class TestLocFalse:
    """`has_3d_model=False` = chỉ mẫu KHÔNG có 3D."""

    def test_false_giu_san_pham_khong_co_3d(self):
        service = _service(
            [_row("p1", "Bánh A"), _row("p2", "Bánh B")],
            [_link("p1", "round-1-tier", "/models/a.glb")],
        )
        result = _search(service, has_3d_model=False)
        names = [r["name"] for r in result["results"]]
        assert names == ["Bánh B"], f"phai chi giu san pham KHONG co 3D, got {names}"

    def test_false_bo_san_pham_co_3d(self):
        service = _service(
            [_row("p1", "Bánh A"), _row("p2", "Bánh B")],
            [_link("p1", "round-1-tier", "/models/a.glb")],
        )
        result = _search(service, has_3d_model=False)
        assert all(r["three_d_model"] is None for r in result["results"])

    def test_none_thi_khong_loc(self):
        """None = không lọc — hành vi cũ phải giữ nguyên."""
        service = _service(
            [_row("p1", "Bánh A"), _row("p2", "Bánh B")],
            [_link("p1", "round-1-tier", "/models/a.glb")],
        )
        result = _search(service, has_3d_model=None)
        assert result["count"] == 2


class TestQuetSauHon:
    """Lọc 3D phải quét sâu hơn `match_count`."""

    def test_loc_3d_van_lay_du_so_ket_qua(self):
        """Chỉ 3/101 bánh có mô hình 3D; top-6 thường không chứa cả 3.

        Nếu cắt còn `match_count` dòng rồi mới lọc, chế độ "chỉ mẫu có 3D"
        trả về 0-1 món dù kho có 3 mẫu. Phải quét sâu hơn mới lấy đủ.
        """
        rows = [_row(f"p{i}", f"Bánh {i}", 0.9 - i * 0.01) for i in range(1, 13)]
        # Chỉ 2 sản phẩm có 3D, nằm ở CUỐI bảng điểm.
        links = [
            _link("p11", "round-1-tier", "/models/a.glb"),
            _link("p12", "round-2-tier", "/models/b.glb"),
        ]
        service = _service(rows, links)
        result = _search(service, has_3d_model=True, match_count=6)
        names = sorted(r["name"] for r in result["results"])
        assert names == ["Bánh 11", "Bánh 12"], (
            f"phai quet sau hon match_count de lay du 2 mau co 3D, got {names}"
        )

    def test_khong_loc_thi_van_cung_match_count(self):
        """Không lọc 3D thì hành vi cũ: cắt còn đúng match_count."""
        rows = [_row(f"p{i}", f"Bánh {i}") for i in range(1, 13)]
        service = _service(rows, [])
        result = _search(service, match_count=4)
        assert result["count"] == 4


class TestKhongLamSaiKetQua:
    """Lọc 3D không được làm hỏng những gì đã chạy được."""

    def test_khong_loc_thi_van_biet_mau_nao_co_3d(self):
        """Không lọc thì vẫn phải mang mapping: giao diện cần biết mẫu nào
        mở được viewer để bật nút xem 3D.
        """
        service = _service(
            [_row("p1", "Bánh A")],
            [_link("p1", "round-1-tier", "/models/a.glb")],
        )
        result = _search(service)
        assert result["results"][0]["three_d_model"]["slug"] == "round-1-tier"
    def test_so_ket_qua_khong_vuot_match_count(self):
        service = _service(
            [_row("p1", "Bánh A"), _row("p2", "Bánh B"), _row("p3", "Bánh C")],
            [_link("p1", "round-1-tier", "/models/a.glb")],
        )
        result = _search(service, has_3d_model=True, match_count=6)
        assert result["count"] <= 6
