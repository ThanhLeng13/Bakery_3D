"""Bảng đặt tên 101 ảnh do tôi xem và gõ tay.

TÔI ĐÃ MỞ TỪNG ẢNH
    Tên dưới đây do tôi nhìn ảnh mà đặt, KHÔNG phải đoán từ tên file (tên file
    chỉ là số). Cách làm: ghép ảnh thành 7 lưới có số thứ tự, mở từng lưới, rồi
    ghi lại đặc điểm nhìn thấy được của từng ô.

GIỚI HẠN — ĐỌC KỸ
    Tên này dựa trên ĐẶC ĐIỂM NHÌN THẤY (màu kem, hoa, hình dạng, số tầng, chữ
    trên bánh). Tôi KHÔNG biết tiệm gọi món đó là gì, và không biết giá thật.
    Bạn nên đọc lại và sửa những chỗ sai — đặc biệt là giá.

    Một số ảnh tôi không chắc chắn về nhân bánh (chỉ thấy mặt ngoài), nên tên
    chỉ mô tả phần nhìn thấy.

CÁCH DÙNG
    python scripts/apply_names.py --sheet backend/names_review.csv --dry-run
    python scripts/apply_names.py --sheet backend/names_review.csv
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
IMAGE_ROOT = ROOT.parent / "image_bake"
OUT = ROOT / "names_review.csv"

# (số thứ tự trong thư mục, tên bánh)
# Số thứ tự lấy theo bảng index sinh từ chính thư mục ảnh.
NAMES: dict[str, dict[int, str]] = {
    "bánh Kem": {
        1:  "Bánh kem lịch tháng màu xanh mint",
        2:  "Bánh kem lịch tháng nơ xanh dương",
        3:  "Bánh kem lịch tháng nơ hồng pastel",
        4:  "Bánh kem lịch tháng nơ đen",
        5:  "Bánh kem hoa cúc vàng xanh mint",
        6:  "Bánh kem hoa trắng chữ Mừng Sinh Nhật Mẹ",
        7:  "Bánh kem hoa kem xanh lá phủ túi lưới",
        8:  "Bánh kem hoa tím chữ Happy Birthday",
        9:  "Bánh kem hoa hồng phấn chữ Mừng Sinh Nhật",
        10: "Bánh kem hoa trắng tím chữ Mừng Sinh Nhật Mẹ",
        11: "Bánh kem nơ hồng chữ Happy Birthday",
        12: "Bánh kem hoa tulip trắng xanh lá",
        13: "Bánh kem hoa hồng xanh dương kỷ niệm",
        14: "Bánh kem vẽ hình cô dâu chú rể chúc mừng",
        15: "Bánh kem hoa hồng đỏ chữ Happy Birthday nền trắng",
        16: "Bánh kem figure ông bà chữ Happy Birthday",
        17: "Bánh kem hoa trắng thanh lịch",
        18: "Bánh kem vẽ hình ông bà Happy Birthday Chị",
        19: "Bánh kem hoa dại nhỏ nhiều màu",
        20: "Bánh kem figure ông bà bóng bay Mừng Sinh Nhật",
        21: "Bánh kem vẽ hình bé gái áo đỏ Các con cháu chúc",
        22: "Bánh kem hoa mai vàng trắng",
        23: "Bánh kem hoa hồng đỏ tầng diềm trắng Happy Birthday",
        24: "Bánh kem hoa hồng đỏ lớn Happy Birthday Anh",
        25: "Bánh kem hoa hồng trắng kem chữ Chúc Mừng",
        26: "Bánh kem trang trí xe hơi và tiền",
        27: "Bánh kem hoa xanh dương chữ Sinh Nhật",
        28: "Bánh kem trái cây dâu việt quất",
        29: "Bánh kem chữ Will you marry me cầu hôn",
        30: "Bánh kem bó hoa trắng phủ giấy voan",
        31: "Bánh kem bé gái nơ hồng kèm bánh tart mini",
        32: "Bánh kem hoa xanh dương pastel",
        33: "Bánh kem hoa quả dâu kèm bánh tart mini",
        34: "Bánh kem trái cây dâu kiwi việt quất",
        35: "Bánh kem hoa hồng phấn phủ giấy voan",
        36: "Bánh kem tart mini nhiều vị",
        37: "Bánh kem hoa hồng đen vẽ line đen",
        38: "Bánh kem hoa hồng đen chữ Happy Birthday Em",
        39: "Bánh kem tart mini trái cây và socola",
        40: "Bánh kem mặt hồng pastel hoa nhỏ",
        41: "Bánh kem hoa cúc trắng xanh chữ Happy Birthday",
        42: "Bánh kem trái cây xanh vàng",
        43: "Bánh kem hoa hồng phấn tầng diềm trắng",
        44: "Bánh kem hoa hồng phấn bọc voan trắng",
        45: "Bánh kem kem hồng viền socola đen",
        46: "Bánh kem hoa hồng phấn chữ Happy Teacher's Day",
        47: "Bánh kem hoa hồng phấn chữ Happy Birthday nền xanh",
        48: "Bánh kem bóng đá bé trai HAPPY BIRTHDAY",
        49: "Bánh kem hình con thú màu xám",
        50: "Bánh kem hoa hồng phấn chữ Happy Birthday nền trắng",
        51: "Bánh kem chấm bi trắng đen hoa nhỏ",
        52: "Bánh kem hoa vàng phủ giấy voan",
        53: "Bánh kem 2 tầng hoa hồng phấn",
        54: "Bánh kem hoa hồng kem cuộn tròn",
        55: "Bánh kem hình con ếch xanh",
        56: "Bánh kem hoa hồng phấn nơ trắng",
        57: "Bánh kem hoa hồng phấn kèm bánh tart mini",
        58: "Bánh kem bé gái công chúa nơ hồng",
    },
    "bánh Âu": {
        1:  "Bánh mousse chanh dây trái cây tươi",
        2:  "Bánh kem chữ Chúc Mừng Sinh Nhật Nhân",
        3:  "Bánh kem phủ sợi vàng chữ Happy Birthday",
        4:  "Bánh kem cuộn socola trắng",
        5:  "Bánh kem sợi vàng chữ Chúc Mừng Sinh Nhật",
        6:  "Bánh kem socola viên tròn",
        7:  "Bánh kem chanh dây chữ Chúc Mừng Sinh Nhật",
        8:  "Bánh mousse chanh dây trái cây nền gỗ",
        9:  "Bánh mousse chanh dây kiwi dâu",
        10: "Bánh kem dừa sợi chữ Happy Birthday",
        11: "Bánh mousse chanh dây dâu việt quất",
        12: "Bánh kem chanh dây chữ Happy Birthday",
        13: "Bánh kem trái cây dừa sợi",
        14: "Bánh kem hình trái tim chữ Happy Birthday",
        15: "Bánh kem trái tim figure ông bà",
        16: "Bánh kem chanh dây hoa quả",
        17: "Bánh tart mini nhiều vị phủ kem",
        18: "Bánh kem chanh dây socola dâu",
        19: "Bánh tart mini trái cây dâu xanh",
        20: "Bánh tart mini socola trái cây",
        21: "Bánh kem xanh lá trái cây tươi",
        22: "Bánh tart mini dâu việt quất",
        23: "Bánh tart mini phủ kem trắng",
        24: "Bánh tart mini socola dâu",
        25: "Bánh tart mini nhiều màu",
        26: "Bánh tart mini hồng phủ kem",
        27: "Bánh tart mini trái cây hỗn hợp",
        28: "Bánh kem trái cây kèm tart mini",
        29: "Bánh tart mini kem xanh lá",
        30: "Bánh tart mini kem hồng chữ Chúc Mừng",
        31: "Bánh kem dừa sợi kèm tart mini",
        32: "Bánh tart mini kem xanh chanh",
        33: "Bánh tart mini dâu phủ kem hồng",
        34: "Bánh tart mini kiwi việt quất",
        35: "Bánh mousse trái cây trong hộp",
        36: "Bánh mousse chanh dây trái cây nền trắng",
        37: "Bánh kem trái cây chữ Happy Birthday",
        38: "Bánh kem xanh lá trái cây dừa",
        39: "Bánh kem trái cây tươi nơ trắng",
        40: "Bánh mousse chanh dây trái cây nền ghế trắng",
        41: "Bánh kem trái cây dâu xanh",
        42: "Bánh kem hoa kem nhiều màu",
        43: "Bánh tart trái cây 4 ô vuông",
    },
}

# Giá mặc định theo nhóm
PRICE = {"bánh Kem": 350000, "bánh Âu": 120000}


def main() -> int:
    if not IMAGE_ROOT.exists():
        print(f"LOI: khong thay {IMAGE_ROOT}")
        return 1

    rows = []
    missing = []
    for folder in sorted(d for d in IMAGE_ROOT.iterdir() if d.is_dir()):
        files = sorted(
            f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
        )
        table = NAMES.get(folder.name, {})

        # Tên gắn theo VỊ TRÍ, không theo tên file (tên file chỉ là số). Thêm hay
        # bớt một ảnh trong thư mục sẽ làm MỌI tên phía sau lệch đi một bậc và
        # gán sai bánh. Không thể nhận ra bằng mắt vì tên vẫn "hợp lý".
        #
        # Nên chặn trước: nếu số ảnh khác với số tên đã đặt, dừng và báo rõ,
        # thay vì âm thầm ghi ra bảng tên sai.
        expected = max(table) if table else 0
        if table and len(files) != expected:
            print("=" * 74)
            print("LOI: SO ANH KHAC SO TEN — DUNG LAI")
            print("=" * 74)
            print(f"  Thu muc   : {folder.name}")
            print(f"  Anh hien co: {len(files)}")
            print(f"  Ten da dat : {expected} (danh so 1..{expected})")
            print()
            print("  Ten trong script nay gan theo VI TRI, nen lech so luong se lam")
            print("  moi ten sau diem lech bi gan sai banh.")
            print()
            print("  Cach sua: mo tang/giảm so trong NAMES['{0}'] cho khop,".format(folder.name))
            print("  hoac bo sung ten cho anh moi roi chay lai.")
            print()
            print("  Danh sach anh hien co:")
            for idx, f in enumerate(files, start=1):
                mark = "co ten" if idx <= expected else "THIEU TEN"
                print(f"    {idx:3d}. [{mark}] {f.name[:60]}")
            return 1

        for i, f in enumerate(files, start=1):
            name = table.get(i)
            if not name:
                missing.append(f"{folder.name} #{i} ({f.name})")
                name = ""
            # Ghi rõ ảnh nào là cùng một mẫu chụp nhiều góc — chưa xác định được
            # nên để mỗi ảnh một tên riêng, tránh gộp sai.
            rows.append({
                "thu_muc": folder.name,
                "file": f.name,
                "ten_banh": name,
                "gia": str(PRICE.get(folder.name, 300000)),
                "mo_ta": "",
            })

    with OUT.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["thu_muc", "file", "ten_banh", "gia", "mo_ta"])
        w.writeheader()
        w.writerows(rows)

    named = sum(1 for r in rows if r["ten_banh"])
    print("=" * 74)
    print("DA TAO BANG TEN")
    print("=" * 74)
    print(f"  File      : {OUT}")
    print(f"  Tong anh  : {len(rows)}")
    print(f"  Da dat ten: {named}")

    # Kiem tra trung ten
    from collections import Counter
    dupes = {n: c for n, c in Counter(r["ten_banh"] for r in rows if r["ten_banh"]).items() if c > 1}
    if dupes:
        print(f"  Ten trung : {len(dupes)}")
        for n, c in list(dupes.items())[:5]:
            print(f"    {c}x {n}")
    else:
        print("  Ten trung : 0 (moi anh mot san pham rieng)")

    if missing:
        print(f"  CHUA DAT  : {len(missing)}")
        for m in missing[:10]:
            print(f"    {m}")
    print()
    print("  BUOC TIEP THEO")
    print(f"    python scripts/apply_names.py --sheet {OUT.name} --dry-run")
    print(f"    python scripts/apply_names.py --sheet {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
