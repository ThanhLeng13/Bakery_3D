"""Sinh CLIP embedding cho toàn bộ ảnh sản phẩm trong kho.

Chạy một lần sau khi migration `add_clip_image_search.sql` đã được áp dụng:

    python backend/scripts/embed_catalog.py

Script sẽ:
    1. Đọc bảng `product_images` (ảnh thật trên Supabase Storage)
    2. Tải từng ảnh về, sinh vector 512 chiều bằng CLIP ViT-B-32
    3. Upsert vào `cake_embeddings`

Đặc điểm:
    - Idempotent: chạy lại chỉ ghi đè, không tạo trùng (UNIQUE product_id,image_url)
    - `--skip-existing`: bỏ qua ảnh đã có embedding → chạy lại rất nhanh
    - `--limit N`: chỉ xử lý N ảnh đầu (để thử nghiệm)
    - In bảng thống kê cuối cùng — dùng làm số liệu cho báo cáo

LƯU Ý: script cần `SUPABASE_URL` và `SUPABASE_SERVICE_ROLE_KEY` trong backend/.env
"""

import argparse
import io
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Đảm bảo in được tiếng Việt trên Windows console.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from supabase import create_client  # noqa: E402

from app.services.clip_service import (  # noqa: E402
    MODEL_NAME,
    ClipServiceError,
    embed_image_bytes,
)


def fetch_image(url: str, timeout: int = 30) -> Optional[bytes]:
    """Tải ảnh từ URL. Trả về None nếu lỗi (script bỏ qua ảnh hỏng)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Bakery3D-embed/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        print(f"    ! Không tải được ảnh: {type(exc).__name__}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Sinh CLIP embedding cho kho bánh")
    parser.add_argument("--limit", type=int, default=0, help="Chỉ xử lý N ảnh đầu")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Bỏ qua ảnh đã có embedding (chạy lại nhanh)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ liệt kê việc cần làm, không gọi model",
    )
    args = parser.parse_args()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("LOI: Thiếu SUPABASE_URL hoặc SUPABASE_SERVICE_ROLE_KEY trong backend/.env")
        return 2

    client = create_client(url, key)

    # ─── Đọc kho ảnh ─────────────────────────────────────────────────────────
    try:
        images = client.table("product_images").select("*").execute().data or []
    except Exception as exc:
        print(f"LOI: Không đọc được product_images: {type(exc).__name__}")
        return 1

    products = client.table("products").select("id,name").execute().data or []
    name_by_id = {p["id"]: p["name"] for p in products}

    print("=" * 74)
    print("SINH CLIP EMBEDDING CHO KHO BÁNH")
    print("=" * 74)
    print(f"  Model          : {MODEL_NAME} (vector 512 chiều)")
    print(f"  Ảnh trong kho  : {len(images)}")
    print(f"  Sản phẩm       : {len(products)}")
    print()

    # Ảnh đã có embedding (nếu bảng tồn tại)
    existing: set[tuple[str, str]] = set()
    try:
        rows = client.table("cake_embeddings").select("product_id,image_url").execute().data or []
        existing = {(r["product_id"], r["image_url"]) for r in rows}
        print(f"  Đã có embedding: {len(existing)}")
    except Exception:
        print("  Bảng cake_embeddings chưa tồn tại.")
        print("  → Chạy migration add_clip_image_search.sql trước.")
        return 1
    print()

    todo = images
    if args.skip_existing:
        todo = [i for i in images if (i["product_id"], i["url"]) not in existing]
        # Đếm số ảnh bị bỏ qua NGAY TẠI ĐÂY, trước khi áp --limit.
        # Nếu tính sau khi cắt --limit thì ảnh bị cắt cũng bị tính nhầm là
        # "đã có embedding" — ví dụ 20 ảnh, 18 đã có, --limit 1 sẽ báo bỏ qua 19
        # trong khi sự thật là 18.
        skipped = len(images) - len(todo)
    else:
        # Không bật --skip-existing thì không có ảnh nào bị bỏ qua.
        skipped = 0

    # --limit áp SAU cùng: nó chỉ giới hạn số việc làm, không phải lý do bỏ qua.
    if args.limit:
        todo = todo[: args.limit]

    if not todo:
        print("Không có ảnh nào cần xử lý. Kho đã đầy đủ embedding.")
        return 0

    print(f"  Cần xử lý      : {len(todo)} ảnh")
    if args.dry_run:
        for img in todo:
            print(f"    - {name_by_id.get(img['product_id'], '?')}")
        return 0
    print()

    # ─── Xử lý từng ảnh ──────────────────────────────────────────────────────
    # `skipped` đã được tính ở trên; ở đây chỉ khởi tạo ok/failed.
    ok = failed = 0
    embed_times: list[float] = []
    started_all = time.perf_counter()

    for index, img in enumerate(todo, start=1):
        product_id = img["product_id"]
        image_url = img["url"]
        product_name = name_by_id.get(product_id, "(không rõ)")

        print(f"  [{index}/{len(todo)}] {product_name}")

        raw = fetch_image(image_url)
        if raw is None:
            failed += 1
            continue

        try:
            embed_started = time.perf_counter()
            vector = embed_image_bytes(raw)
            elapsed_ms = (time.perf_counter() - embed_started) * 1000
            embed_times.append(elapsed_ms)
        except ClipServiceError as exc:
            print(f"    ! Bỏ qua: {exc.message}")
            failed += 1
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"    ! Lỗi không mong đợi: {type(exc).__name__}")
            failed += 1
            continue

        try:
            client.table("cake_embeddings").upsert(
                {
                    "product_id": product_id,
                    "image_url": image_url,
                    "embedding": vector,
                    "model_name": MODEL_NAME,
                },
                on_conflict="product_id,image_url",
            ).execute()
            ok += 1
            print(f"    OK  {elapsed_ms:.0f} ms")
        except Exception as exc:  # noqa: BLE001
            print(f"    ! Lỗi ghi database: {type(exc).__name__}")
            failed += 1

    total_seconds = time.perf_counter() - started_all

    # ─── Thống kê (số liệu cho báo cáo) ──────────────────────────────────────
    print()
    print("=" * 74)
    print("KẾT QUẢ")
    print("=" * 74)
    print(f"  Thành công     : {ok}")
    print(f"  Bỏ qua         : {skipped}")
    print(f"  Thất bại       : {failed}")
    print(f"  Tổng thời gian : {total_seconds:.1f} s")
    if embed_times:
        avg = sum(embed_times) / len(embed_times)
        print(f"  Thời gian embed: trung bình {avg:.0f} ms/ảnh"
              f" (min {min(embed_times):.0f}, max {max(embed_times):.0f})")
    print()

    try:
        final = client.table("cake_embeddings").select("id", count="exact").execute()
        print(f"  Tổng embedding trong kho: {final.count}")
    except Exception:
        pass

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
