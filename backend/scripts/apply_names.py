"""Đọc bảng đặt tên, tạo sản phẩm, tải ảnh lên, sinh embedding — một lệnh.

QUY TRÌNH ĐẦY ĐỦ
    1. python scripts/make_naming_page.py     # tạo trang đặt tên
    2. Mở naming_page.html, gõ tên, bấm "Tải CSV"
    3. Lưu CSV đè vào backend/naming_sheet.csv
    4. python scripts/apply_names.py --dry-run   # xem trước
    5. python scripts/apply_names.py             # làm thật

    Script tự làm cả 3 việc: tạo sản phẩm, tải ảnh lên Storage, ghi
    product_images. Embedding sinh riêng bằng embed_catalog.py vì bước đó cần
    nạp model CLIP (~45 giây).

XỬ LÝ TRÙNG TÊN
    Nhiều ảnh có thể cùng tên (ví dụ 3 bánh đều là "Bánh kem hoa tươi").
    Script KHÔNG báo lỗi mà gộp lại: 3 ảnh đó thành 3 ảnh của CÙNG một sản phẩm.
    Đây thường là điều bạn muốn — nhiều góc của cùng một mẫu bánh giúp CLIP
    nhận diện tốt hơn. Nếu muốn tách riêng, đặt tên khác nhau.
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

IMAGE_ROOT = ROOT.parent / "image_bake"
DEFAULT_SHEET = ROOT / "naming_sheet.csv"
BUCKET = "product-images"

# Giá mặc định khi bạn không điền cột `gia` trong CSV.
# Đặt theo loại bánh để trang sản phẩm không hiện "Liên hệ" ở mọi chỗ.
DEFAULT_PRICE = {"bánh Kem": 350000, "bánh Âu": 120000}


def read_sheet(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(
            f"LOI: Khong tim thay {path}\n"
            "Hay chay scripts/make_naming_page.py roi dat ten truoc."
        )
    # utf-8-sig để đọc được BOM do Excel/trang HTML ghi ra.
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    named = []
    for r in rows:
        name = (r.get("ten_banh") or "").strip()
        if not name:
            continue

        folder = (r.get("thu_muc") or "").strip()
        filename = (r.get("file") or "").strip()
        image_path = IMAGE_ROOT / folder / filename
        if not image_path.exists():
            print(f"  ! Khong thay file, bo qua: {folder}/{filename}")
            continue

        price_raw = (r.get("gia") or "").strip().replace(".", "").replace(",", "").replace("đ", "")
        try:
            price = int(price_raw) if price_raw else DEFAULT_PRICE.get(folder, 300000)
        except ValueError:
            price = DEFAULT_PRICE.get(folder, 300000)

        named.append({
            "name": name,
            "folder": folder,
            "file": filename,
            "path": image_path,
            "price": price,
            "description": (r.get("mo_ta") or "").strip(),
        })
    return named


def main() -> int:
    parser = argparse.ArgumentParser(description="Áp dụng tên bánh và nhập ảnh")
    parser.add_argument("--sheet", type=Path, default=DEFAULT_SHEET,
                        help="File CSV chứa tên bánh")
    parser.add_argument("--dry-run", action="store_true",
                        help="Chỉ xem trước, không ghi lên Supabase")
    args = parser.parse_args()

    rows = read_sheet(args.sheet)

    # Gộp theo tên: nhiều ảnh cùng tên = nhiều góc của cùng một sản phẩm.
    grouped: dict[str, list[dict]] = {}
    for r in rows:
        grouped.setdefault(r["name"], []).append(r)

    print("=" * 74)
    print("AP DUNG TEN BANH")
    print("=" * 74)
    print(f"  Che do        : {'DRY RUN (khong ghi gi)' if args.dry_run else 'THAT'}")
    print(f"  Anh co ten    : {len(rows)}")
    print(f"  San pham      : {len(grouped)} (gop anh cung ten)")
    print()

    multi = {n: v for n, v in grouped.items() if len(v) > 1}
    if multi:
        print(f"  Co {len(multi)} ten xuat hien nhieu lan (gop thanh nhieu goc):")
        for name, items in sorted(multi.items(), key=lambda x: -len(x[1]))[:8]:
            print(f"    {len(items)}x  {name}")
        if len(multi) > 8:
            print(f"    ... va {len(multi) - 8} ten khac")
        print()

    # Canh bao ten qua giong nhau — de gay nham lan khi tim kiem
    names = list(grouped.keys())
    clashes = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a != b and (a in b or b in a):
                clashes.append((a, b))
    if clashes:
        print(f"  LUU Y: {len(clashes)} cap ten gan giong nhau:")
        for a, b in clashes[:5]:
            print(f"    '{a}'  vs  '{b}'")
        print("    Ten qua giong lam ket qua tim kiem de nham. Nen dat cu the hon.")
        print()

    if args.dry_run:
        print("  Danh sach san pham se tao:")
        for i, name in enumerate(sorted(grouped), 1):
            items = grouped[name]
            print(f"    {i:3d}. {name[:52]:54s} {len(items)} anh  {items[0]['price']:,}d")
        print()
        print("  DRY RUN: khong ghi gi. Bo --dry-run de chay that.")
        return 0

    # Chỉ cần thông tin đăng nhập khi THỰC SỰ ghi lên Supabase. Kiểm tra sớm
    # (trước cả --dry-run) sẽ khiến xem trước vô dụng khi chưa cấu hình .env.
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("LOI: Thieu SUPABASE_URL hoac SUPABASE_SERVICE_ROLE_KEY trong backend/.env")
        return 2

    client = create_client(url, key)

    # Sản phẩm đã có sẵn — để chạy lại không tạo trùng.
    existing = client.table("products").select("id,name").execute().data or []
    id_by_name = {p["name"]: p["id"] for p in existing}

    existing_imgs = client.table("product_images").select("product_id,url").execute().data or []
    have_url = {r["url"] for r in existing_imgs}

    created = reused = uploaded = img_failed = 0

    for name in sorted(grouped):
        items = grouped[name]
        price = items[0]["price"]

        product_id = id_by_name.get(name)
        if product_id:
            reused += 1
            print(f"  = {name[:52]} (da co)")
        else:
            try:
                res = client.table("products").insert({
                    "name": name,
                    "description": items[0]["description"] or None,
                    "base_price": price,
                    "category": "bánh âu" if items[0]["folder"] == "bánh Âu" else "bánh kem",
                    "product_type": "cake",
                    "is_active": True,
                }).execute()
                product_id = res.data[0]["id"]
                id_by_name[name] = product_id
                created += 1
                print(f"  + {name[:52]} ({len(items)} anh, {price:,}d)")
            except Exception as exc:
                print(f"  ! Tao san pham '{name}' loi: {type(exc).__name__} {str(exc)[:70]}")
                continue

        for item in items:
            path = item["path"]
            ext = path.suffix.lower().lstrip(".")
            ctype = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
            object_path = f"{product_id}/{path.stem[:60]}.{ext}"

            try:
                client.storage.from_(BUCKET).upload(
                    object_path, path.read_bytes(), {"content-type": ctype}
                )
            except Exception as exc:
                msg = str(exc)
                # Đã có trên Storage thì bỏ qua, không phải lỗi thật.
                if "already exists" not in msg and "Duplicate" not in msg:
                    print(f"      ! upload loi: {type(exc).__name__} {msg[:60]}")
                    img_failed += 1
                    continue

            public_url = client.storage.from_(BUCKET).get_public_url(object_path)
            if public_url in have_url:
                continue
            try:
                client.table("product_images").insert({
                    "product_id": product_id,
                    "url": public_url,
                }).execute()
                have_url.add(public_url)
                uploaded += 1
            except Exception as exc:
                print(f"      ! ghi product_images loi: {type(exc).__name__}")
                img_failed += 1

    print()
    print("=" * 74)
    print(f"  San pham tao moi : {created}")
    print(f"  San pham da co   : {reused}")
    print(f"  Anh da them      : {uploaded}")
    print(f"  Anh loi          : {img_failed}")
    print("=" * 74)

    if uploaded:
        print()
        print("  BUOC TIEP THEO — sinh embedding cho CLIP:")
        print("    python scripts/embed_catalog.py")
        print()
        print("  Roi do lai do chinh xac:")
        print("    python scripts/evaluate_clip_accuracy.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
