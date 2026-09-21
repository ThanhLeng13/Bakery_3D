"""Thử nghiệm tiền xử lý ảnh để cải thiện độ chính xác CLIP.

VẤN ĐỀ ĐANG GIẢI QUYẾT
    Ảnh trong kho là ảnh quảng cáo: logo Bơ Nơ, tên sản phẩm cỡ lớn, số điện
    thoại và địa chỉ. CLIP nhúng TOÀN BỘ ảnh nên vector bị pha loãng — đo được
    tiramisu chỉ đạt 0.268 với chính nó nhưng 0.633 với Dark Oreo.

    Ảnh khách gửi thì sạch, không logo. Nên có sự lệch phân bố giữa hai phía.

CÁCH TIẾP CẬN
    Thử nhiều cách tiền xử lý ảnh KHO để xem cách nào làm vector tập trung vào
    phần bánh. Đo bằng chính bộ test ngoài kho đã có, nên so sánh được với
    baseline 22.2%.

    Mỗi cách đều tính embedding lại cho cả 18 ảnh kho — không sửa dữ liệu thật,
    chỉ giữ trong RAM để so sánh.

CÁCH DÙNG
    python scripts/try_preprocessing.py
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import urllib.request  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from app.services.clip_service import embed_image_bytes  # noqa: E402

TEST_DIR = Path(__file__).resolve().parent.parent / "test_images"


def crop_frac(raw: bytes, frac: float, anchor: str = "center") -> bytes:
    """Cắt vùng vuông chiếm `frac` cạnh ngắn, theo vị trí `anchor`."""
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = im.size
    side = int(min(w, h) * frac)
    if anchor == "center":
        left, top = (w - side) // 2, (h - side) // 2
    elif anchor == "bottom":  # bỏ logo trên, giữ phần bánh dưới
        left, top = (w - side) // 2, h - side
    elif anchor == "upper":
        left, top = (w - side) // 2, 0
    else:
        left, top = 0, 0
    im = im.crop((left, top, left + side, top + side))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def crop_band(raw: bytes, top_frac: float, bot_frac: float) -> bytes:
    """Cắt bỏ `top_frac` phía trên và `bot_frac` phía dưới, giữ phần giữa."""
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = im.size
    im = im.crop((0, int(h * top_frac), w, int(h * (1 - bot_frac))))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=92)
    return buf.getvalue()


# Mỗi chiến lược: tên -> hàm biến đổi bytes ảnh kho
STRATEGIES = {
    "baseline (khong xu ly)": lambda raw: raw,
    "crop 70% giua": lambda raw: crop_frac(raw, 0.70, "center"),
    "crop 55% giua": lambda raw: crop_frac(raw, 0.55, "center"),
    "crop 45% giua": lambda raw: crop_frac(raw, 0.45, "center"),
    "crop 70% duoi (bo logo)": lambda raw: crop_frac(raw, 0.70, "bottom"),
    "bo 20% tren + 12% duoi": lambda raw: crop_band(raw, 0.20, 0.12),
    "bo 26% tren + 12% duoi": lambda raw: crop_band(raw, 0.26, 0.12),
    "bo 32% tren + 14% duoi": lambda raw: crop_band(raw, 0.32, 0.14),
}


def main() -> int:
    manifest = json.loads((TEST_DIR / "manifest.json").read_text(encoding="utf-8"))
    in_test = [m for m in manifest if m["group"] == "trong_kho"]

    # Tải ảnh kho về RAM (cache lại, không ghi ra đĩa)
    from supabase import create_client  # noqa: E402
    import os  # noqa: E402

    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    products = {p["id"]: p["name"] for p in client.table("products").select("id,name").execute().data}
    rows = client.table("cake_embeddings").select("product_id,image_url").execute().data

    catalog: dict[str, list[bytes]] = {}
    print("Dang tai anh kho...")
    for row in rows:
        name = products[row["product_id"]]
        try:
            req = urllib.request.Request(row["image_url"], headers={"User-Agent": "BakeryThesis/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                catalog.setdefault(name, []).append(resp.read())
        except Exception as exc:
            print(f"  loi tai {name}: {type(exc).__name__}")
    print(f"  {sum(len(v) for v in catalog.values())} anh / {len(catalog)} mon")
    print()

    # Embedding anh test (sạch) — chỉ tính MỘT lần, dùng cho mọi chiến lược
    print("Dang tinh embedding anh test...")
    test_vecs = []
    for item in in_test:
        path = TEST_DIR / item["file"]
        if not path.exists():
            continue
        test_vecs.append((item["label"], np.array(embed_image_bytes(path.read_bytes()), dtype=np.float32)))
    print(f"  {len(test_vecs)} anh test")
    print()

    results = []
    for name, fn in STRATEGIES.items():
        catalog_vecs: dict[str, list[np.ndarray]] = {}
        errors = 0
        for product, raws in catalog.items():
            vecs = []
            for raw in raws:
                try:
                    vecs.append(np.array(embed_image_bytes(fn(raw)), dtype=np.float32))
                except Exception:
                    errors += 1
            if vecs:
                catalog_vecs[product] = vecs
        if not catalog_vecs:
            print(f"  {name}: KHONG co embedding nao")
            continue

        names = list(catalog_vecs.keys())
        top1 = top3 = 0
        for expected, tv in test_vecs:
            scored = []
            for product in names:
                best = max(float(np.dot(tv, v)) for v in catalog_vecs[product])
                scored.append((best, product))
            scored.sort(reverse=True)
            ranked = [p for _, p in scored]
            top1 += int(ranked[0] == expected)
            top3 += int(expected in ranked[:3])
        n = len(test_vecs)
        acc1, acc3 = top1 / n * 100, top3 / n * 100
        results.append((name, acc1, acc3, errors))
        print(f"  {name:28s} top-1 {acc1:5.1f}%   top-3 {acc3:5.1f}%"
              + (f"   ({errors} loi)" if errors else ""))

    print()
    print("=" * 74)
    best = max(results, key=lambda r: (r[1], r[2]))
    base = results[0]
    print(f"  Baseline : top-1 {base[1]:.1f}%  top-3 {base[2]:.1f}%")
    print(f"  Tot nhat : {best[0]}  ->  top-1 {best[1]:.1f}%  top-3 {best[2]:.1f}%")
    print(f"  Chenh lech top-1: {best[1] - base[1]:+.1f} diem")
    print("=" * 74)

    out = TEST_DIR / "preprocessing_results.json"
    out.write_text(json.dumps(
        [{"strategy": n, "top1": a1, "top3": a3, "errors": e} for n, a1, a3, e in results],
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Luu: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
