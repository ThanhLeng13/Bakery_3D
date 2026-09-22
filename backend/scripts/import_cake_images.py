"""Nhập ảnh bánh sinh nhật vào Supabase rồi sinh CLIP embedding.

QUY TRÌNH
    Bạn chỉ cần bỏ ảnh vào thư mục, đặt tên file đúng quy ước, rồi chạy script.
    Script tự làm hết phần còn lại: tải lên Storage, ghi vào `product_images`,
    rồi nhúng embedding.

QUY ƯỚC ĐẶT TÊN FILE
    backend/cake_images/<tên-sản-phẩm>/<số>.jpg

    Ví dụ:
        backend/cake_images/Bánh sinh nhật hoa tươi/1.jpg
        backend/cake_images/Bánh sinh nhật hoa tươi/2.jpg
        backend/cake_images/Bánh sinh nhật 2 tầng hoa hồng/1.jpg

    Thư mục con phải TRÙNG TÊN sản phẩm trong bảng `products`. Sai tên thì
    script báo rõ và bỏ qua, không âm thầm gán nhầm vào sản phẩm khác.

CÁCH DÙNG
    python scripts/import_cake_images.py --dry-run   # xem trước, không ghi gì
    python scripts/import_cake_images.py             # làm thật

LƯU Ý VỀ ẢNH
    Ảnh nên là ảnh CHỤP SẢN PHẨM THUẦN: không logo, không chữ, không watermark.
    Đo được ở bộ test ngoài kho rằng ảnh có logo/chữ làm giảm độ chính xác rõ
    rệt (xem test_images/BAO_CAO_DO_CHINH_XAC.md).
"""

from __future__ import annotations

import argparse
import hashlib
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

IMAGE_ROOT = ROOT / "cake_images"
BUCKET = "product-images"
VALID_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def check_image(path: Path) -> str | None:
    """Trả về thông báo lỗi, hoặc None nếu ảnh dùng được."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
        if min(w, h) < 224:
            return f"anh qua nho ({w}x{h}), can toi thieu 224x224"
        return None
    except Exception as exc:
        return f"khong doc duoc anh: {type(exc).__name__}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Nhập ảnh bánh sinh nhật")
    parser.add_argument("--dry-run", action="store_true",
                        help="Chỉ liệt kê, không ghi lên Supabase")
    args = parser.parse_args()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("LOI: Thieu SUPABASE_URL hoac SUPABASE_SERVICE_ROLE_KEY trong backend/.env")
        return 2

    if not IMAGE_ROOT.exists():
        print(f"Chua co thu muc anh: {IMAGE_ROOT}")
        print()
        print("Hay tao thu muc va bo anh vao theo quy uoc:")
        print(f"  {IMAGE_ROOT}\\<ten-san-pham>\\1.jpg")
        print()
        print("Vi du:")
        print(f"  {IMAGE_ROOT}\\Bánh sinh nhật hoa tươi\\1.jpg")
        print(f"  {IMAGE_ROOT}\\Bánh sinh nhật hoa tươi\\2.jpg")
        return 1

    client = create_client(url, key)

    # Đọc sản phẩm bánh kem đang bán
    products = (
        client.table("products")
        .select("id,name,product_type,is_active")
        .eq("product_type", "cake")
        .execute()
        .data
        or []
    )
    by_name = {p["name"]: p for p in products}

    # Đọc ảnh đang có để tránh thêm trùng.
    # Cột tên là `url`, KHÔNG phải `image_url` — đã kiểm chứng bằng cách đọc
    # schema thật từ PostgREST OpenAPI, sau khi đoán sai và bị lỗi 42703.
    existing_images = (
        client.table("product_images").select("product_id,url").execute().data or []
    )
    have_url: set[str] = {row["url"] for row in existing_images}

    print("=" * 74)
    print("NHAP ANH BANH SINH NHAT")
    print("=" * 74)
    print(f"  Che do          : {'DRY RUN (khong ghi gi)' if args.dry_run else 'THAT'}")
    print(f"  Thu muc anh     : {IMAGE_ROOT}")
    print(f"  Banh kem co CSDL: {len(products)}")
    print()

    folders = sorted(d for d in IMAGE_ROOT.iterdir() if d.is_dir())
    if not folders:
        print("  Khong co thu muc con nao trong cake_images/")
        return 1

    planned: list[tuple[Path, dict]] = []
    problems: list[str] = []

    for folder in folders:
        product = by_name.get(folder.name)
        if product is None:
            # Gợi ý tên gần đúng để người dùng sửa nhanh
            close = [n for n in by_name if folder.name.lower()[:12] in n.lower()]
            hint = f"  Y giong: {close[0]}" if close else ""
            problems.append(f"Thu muc '{folder.name}' khong khop san pham nao.{hint}")
            continue

        images = sorted(
            f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in VALID_EXT
        )
        if not images:
            problems.append(f"Thu muc '{folder.name}' khong co anh hop le.")
            continue

        for image in images:
            err = check_image(image)
            if err:
                problems.append(f"{folder.name}/{image.name}: {err}")
                continue
            planned.append((image, product))

    # ─── Báo cáo kế hoạch ────────────────────────────────────────────────────
    print(f"  Anh se nhap     : {len(planned)}")
    by_product: dict[str, int] = {}
    for _img, prod in planned:
        by_product[prod["name"]] = by_product.get(prod["name"], 0) + 1
    for name, count in sorted(by_product.items()):
        flag = "" if count >= 2 else "   (chi 1 anh — nen them goc khac)"
        print(f"    {name}: {count} anh{flag}")

    if problems:
        print()
        print(f"  VAN DE ({len(problems)}):")
        for p in problems:
            print(f"    ! {p}")

    missing = [p["name"] for p in products if p["name"] not in by_product]
    if missing:
        print()
        print(f"  CHUA CO ANH ({len(missing)}):")
        for name in missing:
            print(f"    - {name}")

    if args.dry_run:
        print()
        print("  DRY RUN: khong ghi gi. Bo --dry-run de chay that.")
        return 0

    if not planned:
        print()
        print("  Khong co anh nao de nhap.")
        return 1

    # ─── Tải lên Storage + ghi product_images ────────────────────────────────
    print()
    print("  Dang tai len Storage...")
    added = failed = reused = 0
    for image, product in planned:
        ext = image.suffix.lower().lstrip(".")
        # Băm ĐƯỜNG DẪN TƯƠNG ĐỐI bằng sha1, KHÔNG dùng hash() của Python.
        # hash() của str bị đổi theo tiến trình (PYTHONHASHSEED ngẫu nhiên), nên
        # mỗi lần chạy lại ra một đường dẫn khác -> tải lên trùng lặp, Storage
        # đầy rác và không thể chạy lại an toàn. Đã đo: 3 lần chạy ra 3 số khác
        # nhau. sha1 thì luôn cho cùng kết quả.
        try:
            rel = image.relative_to(IMAGE_ROOT).as_posix()
        except ValueError:
            rel = image.name
        digest = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:10]
        object_path = f"{product['id']}/{image.stem}-{digest}.{ext}"
        try:
            client.storage.from_(BUCKET).upload(
                object_path,
                image.read_bytes(),
                {"content-type": f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"},
            )
        except Exception as exc:
            # Đường dẫn đã tồn tại = lần chạy trước đã tải lên rồi. Đây là chạy
            # lại, không phải lỗi — dùng lại file cũ thay vì báo thất bại.
            if "already exists" in str(exc).lower() or "duplicate" in str(exc).lower():
                reused += 1
            else:
                failed += 1
                print(f"    ! {product['name']}/{image.name}: {type(exc).__name__}")
                continue
        try:
            public_url = client.storage.from_(BUCKET).get_public_url(object_path)
            if public_url in have_url:
                print(f"    = {product['name']}/{image.name} (da co, bo qua)")
                continue
            client.table("product_images").insert({
                "product_id": product["id"],
                "url": public_url,
            }).execute()
            added += 1
            print(f"    + {product['name']}/{image.name}")
        except Exception as exc:
            failed += 1
            print(f"    ! {product['name']}/{image.name}: {type(exc).__name__} {str(exc)[:80]}")

    print()
    print("=" * 74)
    print(f"  Da them : {added}")
    print(f"  Dung lai: {reused} (da co tren Storage tu lan chay truoc)")
    print(f"  That bai: {failed}")
    print("=" * 74)

    if added:
        print()
        print("  BUOC TIEP THEO — sinh embedding cho anh vua them:")
        print("    python scripts/embed_catalog.py")
        print()
        print("  Sau do do lai do chinh xac:")
        print("    python scripts/evaluate_clip_accuracy.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
