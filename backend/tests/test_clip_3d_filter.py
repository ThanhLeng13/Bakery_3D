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

from app.services.clip_service import ClipSearchService


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
