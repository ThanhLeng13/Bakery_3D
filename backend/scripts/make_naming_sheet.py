"""Liệt kê 101 ảnh kèm mô tả đặc điểm, để bạn đặt tên nhanh.

VÌ SAO CÓ SCRIPT NÀY
    Tên file gốc là số (1790085326705_9170768128432834209_...jpg) nên không cho
    biết ảnh là bánh gì. Script này tạo một bảng CSV để bạn điền tên vào, thay vì
    phải mở từng ảnh và tự gõ tên file.

CÁCH DÙNG
    1. Chạy:  python scripts/make_naming_sheet.py
    2. Mở file backend/naming_sheet.csv bằng Excel
    3. Điền cột `ten_banh` cho từng dòng (cột gợi ý đã có sẵn đặc điểm nhìn thấy)
    4. Lưu lại, rồi chạy:  python scripts/apply_names.py

    Cột `ten_banh` để trống thì ảnh đó bị bỏ qua, không nhập vào hệ thống.

CỘT `goi_y` LÀ GÌ
    Là đặc điểm tôi nhìn thấy khi mở ảnh: màu kem, hoa, hình dạng, chữ trên bánh.
    Đây chỉ là GỢI Ý để bạn nhớ ảnh nào là ảnh nào — KHÔNG phải tên chính thức.
    Bạn cứ đặt tên theo cách tiệm vẫn gọi.
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
IMAGE_ROOT = ROOT.parent / "image_bake"
OUT_CSV = ROOT / "naming_sheet.csv"

# Quy ước đặt tên gợi ý cho bạn tham khảo — sửa thoải mái.
NAMING_HELP = """
  CÁCH ĐẶT TÊN ĐỀ XUẤT
  ─────────────────────
  Công thức:  <Loại> <Đặc điểm chính> <Chi tiết phụ>

  Ví dụ tốt (ngắn, khách hiểu ngay):
    Bánh kem hoa tươi pastel
    Bánh kem hoa hồng đen
    Bánh kem bé gái công chúa hồng
    Bánh mousse chanh dây trái cây
    Bánh tart trứng phủ kem xanh
    Bánh kem chúc mừng sinh nhật ông bà

  Nên:
    - Bắt đầu bằng "Bánh kem" hoặc "Bánh" để khách tìm thấy
    - Nêu ĐẶC ĐIỂM NHÌN THẤY (hoa, màu, hình, số tầng) — vì khách tìm bằng ảnh
    - Ngắn gọn, dưới 40 ký tự
    - Không ghi giá vào tên

  Tránh:
    - Tên chung chung: "Bánh kem 1", "Mẫu A"
    - Ghi ngày tháng, mã đơn hàng
    - Trùng tên nhau (hệ thống cần tên duy nhất)
"""


def main() -> int:
    if not IMAGE_ROOT.exists():
        print(f"LOI: Khong tim thay thu muc anh: {IMAGE_ROOT}")
        return 1

    rows = []
    for folder in sorted(d for d in IMAGE_ROOT.iterdir() if d.is_dir()):
        files = sorted(
            f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
        )
        for f in files:
            rows.append({
                "thu_muc": folder.name,
                "file": f.name,
                "ten_banh": "",          # <- BẠN ĐIỀN CỘT NÀY
                "gia": "",               # <- tùy chọn
                "mo_ta": "",             # <- tùy chọn
                "goi_y": "",             # gợi ý tự động (xem dưới)
            })

    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=["thu_muc", "file", "ten_banh", "gia", "mo_ta", "goi_y"])
        writer.writeheader()
        writer.writerows(rows)

    print("=" * 74)
    print("DA TAO BANG DAT TEN")
    print("=" * 74)
    print(f"  File    : {OUT_CSV}")
    print(f"  So anh  : {len(rows)}")

    from collections import Counter
    for name, count in Counter(r["thu_muc"] for r in rows).items():
        print(f"    {name}: {count} anh")
    print()
    print(NAMING_HELP)
    print("  BƯỚC TIẾP THEO")
    print("  1. Mo file CSV bang Excel")
    print("  2. Dien cot 'ten_banh' (bat buoc) va 'gia' (tuy chon)")
    print("  3. Luu lai")
    print("  4. Chay:  python scripts/apply_names.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
