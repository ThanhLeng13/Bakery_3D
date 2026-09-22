"""Định giá bánh theo giá thị trường Đà Nẵng.

NGUỒN DỮ LIỆU
    Giá lấy từ các tiệm bánh sinh nhật đang bán tại Đà Nẵng, khảo sát ngày
    2026-09. Đây là giá NIÊM YẾT công khai trên website, không phải giá thương
    lượng. Ghi lại nguồn để trích dẫn được trong luận văn.

    banhkemsinhnhat.com/da-nang  (Bếp Bánh — có niêm yết giá công khai)
        Bánh sinh nhật cơ bản         300.000 - 400.000
        Bánh vẽ hình / sticker        399.000 - 429.000
        Bánh phụ kiện (ô tô, tiền)    399.000
        Bánh bông lan trứng muối      429.000
        Bánh trái cây tươi            429.000
        Bánh 2 tầng                   550.000 - 700.000

    miacake.vn, channocake.com  (không niêm yết — "Giá: Liên hệ")
        Xác nhận rằng phần lớn tiệm Đà Nẵng báo giá theo yêu cầu, nên KHÔNG có
        bảng giá chuẩn cho từng mẫu. Đây là lý do phải suy ra giá theo LOẠI
        bánh chứ không tra cứu được từng mẫu.

CÁCH SUY RA GIÁ
    Mỗi mẫu bánh được chấm điểm theo các đặc điểm nhìn thấy trong ảnh (số tầng,
    hoa, figure, chữ, trái cây...), rồi cộng dồn vào giá gốc. Cách này cho ra
    dải giá khớp với giá thị trường, thay vì gán một giá cho tất cả.

    Đây là GIÁ THAM KHẢO, không phải giá thật của tiệm Bơ Nơ. Tiệm cần sửa lại.

CÁCH DÙNG
    python scripts/price_cakes.py                 # xem trước
    python scripts/price_cakes.py --apply         # ghi vào Supabase
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

from supabase import create_client  # noqa: E402

NAMES_CSV = ROOT / "names_review.csv"

# Giá gốc theo nhóm, lấy từ khảo sát thị trường.
BASE = {
    "bánh Kem": 350000,   # bánh kem sinh nhật 1 tầng, trang trí đơn giản
    "bánh Âu":  150000,   # bánh tart / mousse / bánh ngọt cỡ nhỏ
}

# Quy tắc cộng/trừ giá, dựa trên đặc điểm nhìn thấy trong ảnh.
#
# Thứ tự QUAN TRỌNG: quy tắc đầu tiên khớp sẽ được áp dụng cho mỗi NHÓM, các
# quy tắc sau trong cùng nhóm bị bỏ qua. Không làm vậy thì "lịch tháng" vừa
# khớp "lịch" vừa khớp "tháng" và bị cộng tiền hai lần.
#
# Cú pháp: (từ khoá, số tiền, nhóm). Cùng nhóm = chỉ lấy cái khớp đầu tiên.
RULES: list[tuple[str, int, str]] = [
    # Cấu trúc — ảnh hưởng nhiều nhất
    ("3 tầng",        +600000, "tang"),
    ("2 tầng",        +250000, "tang"),

    # Trang trí tốn công
    ("cưới",          +150000, "dip"),
    ("cầu hôn",       +80000,  "dip"),
    ("kỷ niệm",       +50000,  "dip"),
    ("figure",        +150000, "hinh"),
    ("con vật",       +120000, "hinh"),
    ("hình con",      +120000, "hinh"),
    ("bóng đá",       +100000, "hinh"),
    ("công chúa",     +100000, "hinh"),
    ("xe hơi",        +80000,  "hinh"),
    ("vẽ hình",       +60000,  "hinh"),
    ("hoa tươi",      +120000, "hoa"),
    ("hoa tulip",     +100000, "hoa"),
    ("hoa hồng",      +80000,  "hoa"),
    ("hoa cúc",       +60000,  "hoa"),
    ("hoa kem",       +60000,  "hoa"),
    ("hoa dại",       +50000,  "hoa"),
    ("hoa",           +60000,  "hoa"),
    ("trái cây",      +80000,  "qua"),
    ("dâu",           +50000,  "qua"),
    ("kiwi",          +50000,  "qua"),
    ("việt quất",     +50000,  "qua"),
    ("chanh dây",     +50000,  "qua"),
    ("socola",        +40000,  "vi"),
    ("matcha",        +50000,  "vi"),
    ("phô mai",       +30000,  "vi"),
    ("dừa",           +30000,  "vi"),
    ("mousse",        +40000,  "vi"),
    ("cuộn",          +30000,  "vi"),
    ("lịch",          +40000,  "chu"),   # "lịch tháng" chỉ tính 1 lần
    ("chữ",           +20000,  "chu"),
    ("tiền",          +50000,  "pt"),
    ("nơ",            +30000,  "pt"),
    ("voan",          +30000,  "pt"),
    ("tart",          +20000,  "pt"),
]

# Sàn và trần hợp lý — tránh ra giá vô lý do cộng dồn nhiều quy tắc.
FLOOR = {"bánh Kem": 250000, "bánh Âu": 80000}
CEIL = 1800000

# Làm tròn về mức giá "đẹp" như các tiệm vẫn dùng.
NICE_STEPS = [0, 20000, 29000, 39000, 49000, 50000, 90000]


def round_price(value: int) -> int:
    """Làm tròn về mức tiệm hay dùng: 300.000 / 350.000 / 399.000 / 429.000..."""
    # Mốc 1.000 cho dễ đọc
    rounded = round(value / 10000) * 10000
    # Chỉnh về đuôi 9.000 nếu gần, để giống giá thị trường (399k, 429k)
    for step in (99000, 90000, 50000, 0):
        cand = (rounded // 100000) * 100000 + step
        if abs(cand - value) <= 15000:
            return cand
    return rounded


def price_for(name: str, folder: str) -> tuple[int, list[str]]:
    base = BASE.get(folder, 300000)
    total = base
    applied = []
    seen_groups: set[str] = set()
    lowered = name.lower()
    for keyword, delta, group in RULES:
        if keyword in lowered and group not in seen_groups:
            total += delta
            seen_groups.add(group)
            applied.append(f"{keyword} {delta:+,}")
    floor = FLOOR.get(folder, 50000)
    total = max(total, floor)
    total = min(total, CEIL)
    return round_price(total), applied


def main() -> int:
    parser = argparse.ArgumentParser(description="Định giá bánh theo thị trường")
    parser.add_argument("--apply", action="store_true", help="Ghi vào Supabase")
    args = parser.parse_args()

    if not NAMES_CSV.exists():
        print(f"LOI: khong thay {NAMES_CSV}")
        return 1

    with NAMES_CSV.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    print("=" * 78)
    print("DINH GIA BANH THEO THI TRUONG DA NANG")
    print("=" * 78)
    print(f"  Che do: {'GHI THAT' if args.apply else 'XEM TRUOC'}")
    print(f"  Nguon : banhkemsinhnhat.com (Bep Banh, Da Nang) + miacake.vn + channocake.com")
    print()

    priced = []
    for row in rows:
        name = (row.get("ten_banh") or "").strip()
        if not name:
            continue
        folder = row["thu_muc"]
        price, applied = price_for(name, folder)
        priced.append((name, folder, price, applied))

    # Thống kê theo dải giá
    from collections import Counter
    buckets = Counter()
    for _n, _f, p, _a in priced:
        lo = (p // 50000) * 50000
        buckets[lo] += 1

    print("  PHAN BO GIA:")
    total_val = 0
    for lo in sorted(buckets):
        bar = "#" * buckets[lo]
        print(f"    {lo//1000:4d}k - {(lo+50000)//1000:4d}k : {buckets[lo]:3d}  {bar}")
        total_val += lo * buckets[lo]
    prices = [p for *_ , p, _ in [(n,f,p,a) for n,f,p,a in priced]]
    print()
    print(f"  Thap nhat : {min(prices):,}d")
    print(f"  Cao nhat  : {max(prices):,}d")
    print(f"  Trung binh: {sum(prices)/len(prices):,.0f}d")
    print()
    print("  SO SANH THI TRUONG (Bep Banh, Da Nang):")
    print("    Banh sinh nhat co ban      300.000 - 400.000")
    print("    Banh ve hinh / sticker     399.000 - 429.000")
    print("    Banh 2 tang                550.000 - 700.000")
    print()
    print("  VI DU CACH TINH:")
    for name, folder, p, applied in priced[:4]:
        base = BASE.get(folder, 300000)
        print(f"    {name[:46]}")
        print(f"      goc {base:,}  {'  '.join(applied[:5])}")
        print(f"      => {p:,}d")

    if args.apply:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            print("LOI: thieu SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
            return 2
        client = create_client(url, key)
        existing = {p["name"]: p["id"] for p in
                    (client.table("products").select("id,name").execute().data or [])}

        updated = 0
        failed = 0
        for name, _folder, price, _applied in priced:
            pid = existing.get(name)
            if not pid:
                continue
            try:
                client.table("products").update({"base_price": price}).eq("id", pid).execute()
                updated += 1
            except Exception as exc:
                failed += 1
                print(f"    ! {name[:40]}: {type(exc).__name__}")
        print()
        print("=" * 78)
        print(f"  Da cap nhat : {updated}")
        print(f"  Loi         : {failed}")
        print("=" * 78)
    else:
        print()
        print("  XEM TRUOC: chua ghi gi. Them --apply de ghi that.")

    # Luu CSV de review
    out = ROOT / "prices_review.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["ten_banh", "nhom", "gia_de_xuat", "dac_diem_cong_them"])
        for name, folder, p, applied in priced:
            w.writerow([name, folder, p, "; ".join(applied)])
    print(f"  Bang gia: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
