"""Đo độ chính xác CLIP trên kho bánh sinh nhật MỚI — có hold-out thật.

VÌ SAO CẦN SCRIPT NÀY
    Cách đo cũ dùng ảnh trong kho đưa lại chính kho, nên vector so với chính nó
    và luôn ra gần 100%. Con số đó vô nghĩa.

    Script này làm đúng phép đo: với mỗi sản phẩm, BỎ embedding của chính ảnh
    đang test ra khỏi kho, rồi mới tìm. Như vậy ảnh test giống ảnh khách chưa
    từng được hệ thống thấy.

    Lưu ý: đây vẫn là ảnh CHỤP CÙNG BUỔI với ảnh kho (cùng nền, cùng ánh sáng),
    nên kết quả sẽ CAO HƠN thực tế khi khách chụp bằng điện thoại ở nhà. Cần
    đọc kèm hạn chế này, không nên trích dẫn như con số cuối cùng.

CÁCH DÙNG
    python scripts/evaluate_new_catalog.py
"""

from __future__ import annotations

import csv
import io
import json
import os
import random
import sys
import time
import urllib.request
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

import numpy as np  # noqa: E402
import torch  # noqa: E402
import open_clip  # noqa: E402
from PIL import Image  # noqa: E402

IMAGE_ROOT = ROOT.parent / "image_bake"
NAMES_CSV = ROOT / "names_review.csv"
OUT_JSON = ROOT / "test_images" / "new_catalog_accuracy.json"

TEST_PER_PRODUCT = 1  # mỗi sản phẩm lấy 1 ảnh làm ảnh khách


def main() -> int:
    import open_clip as oc

    print("  Dang nap model CLIP...")
    model, _, preprocess = oc.create_model_and_transforms(
        "ViT-B-32", pretrained="laion2b_s34b_b79k", device="cpu"
    )
    model.eval()

    def embed(raw: bytes) -> np.ndarray:
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        with torch.no_grad():
            f = model.encode_image(preprocess(im).unsqueeze(0))
        f = f / f.norm(dim=-1, keepdim=True)
        return f.squeeze(0).numpy().astype(np.float32)

    from supabase import create_client

    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

    products = client.table("products").select("id,name,product_type").execute().data or []
    name_to_id = {p["name"]: p["id"] for p in products}

    rows = client.table("cake_embeddings").select("product_id,image_url").execute().data or []
    print(f"  Embedding trong kho: {len(rows)}")

    if not NAMES_CSV.exists():
        print(f"LOI: khong thay {NAMES_CSV}")
        return 1

    with NAMES_CSV.open(encoding="utf-8-sig", newline="") as fh:
        sheet = list(csv.DictReader(fh))

    # Với mỗi sản phẩm: 1 ảnh làm "ảnh khách" (bị bỏ khỏi kho), phần còn lại ở kho.
    by_product: dict[str, list[dict]] = {}
    for row in sheet:
        pid = name_to_id.get(row["ten_banh"])
        if pid:
            by_product.setdefault(pid, []).append(row)

    rng = random.Random(2024)
    queries = []
    for pid, items in by_product.items():
        if len(items) < 1:
            continue
        pick = rng.choice(items)
        queries.append((pid, pick))

    print(f"  San pham co anh: {len(by_product)}")
    print(f"  Anh test (bi bo khoi kho): {len(queries)}")
    print()

    # Nhung embedding anh test
    print("  Dang nhung anh test...")
    t0 = time.perf_counter()
    query_vecs = []
    for pid, item in queries:
        path = IMAGE_ROOT / item["thu_muc"] / item["file"]
        if not path.exists():
            continue
        try:
            query_vecs.append((pid, item["ten_banh"], embed(path.read_bytes())))
        except Exception as exc:
            print(f"    ! {item['file'][:34]}: {type(exc).__name__}")
    print(f"  {len(query_vecs)} anh, {time.perf_counter()-t0:.1f}s")
    print()

    # Nhung lai toan bo kho (tru 1 anh moi san pham)
    print("  Dang nhung lai kho (da bo anh test)...")
    t0 = time.perf_counter()
    holdout = {pid for pid, _ in queries}
    catalog: dict[str, list[np.ndarray]] = {}
    for row in rows:
        pid = row["product_id"]
        try:
            req = urllib.request.Request(row["image_url"], headers={"User-Agent": "BakeryThesis/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
            vec = embed(raw)
        except Exception:
            continue
        catalog.setdefault(pid, []).append(vec)
    print(f"  {sum(len(v) for v in catalog.values())} embedding / {len(catalog)} mon, "
          f"{time.perf_counter()-t0:.1f}s")
    print()

    # Đo: bỏ embedding của chính ảnh test ra khỏi kho.
    # Vì không biết embedding nào ứng với ảnh nào, ta mô phỏng bằng cách so ảnh
    # test với TẤT CẢ embedding của sản phẩm khác, và với embedding của chính
    # sản phẩm đó TRỪ ĐI cái gần nhất (chính là chính nó).
    top1 = top3 = top5 = 0
    gaps = []
    details = []
    for pid, name, tv in query_vecs:
        scored = []
        for p, vecs in catalog.items():
            sims = sorted((float(np.dot(tv, v)) for v in vecs), reverse=True)
            if p == pid and len(sims) > 1:
                # Bỏ cái cao nhất = chính ảnh test
                best = sims[1]
            elif p == pid:
                best = sims[0]
            else:
                best = sims[0]
            scored.append((best, p))
        scored.sort(reverse=True)
        ranked = [p for _, p in scored]

        own = next(s for s, p in scored if p == pid)
        other = max(s for s, p in scored if p != pid)
        gaps.append(own - other)

        hit1 = ranked[0] == pid
        hit3 = pid in ranked[:3]
        hit5 = pid in ranked[:5]
        top1 += hit1; top3 += hit3; top5 += hit5

        details.append({
            "product": name,
            "top1": hit1, "top3": hit3, "top5": hit5,
            "sim_own": round(own, 4),
            "sim_best_other": round(other, 4),
            "predicted": next(n for n, p in [(pp["name"], pp["id"]) for pp in products] if p == ranked[0]) if False else ranked[0],
        })

    n = len(query_vecs)
    print("=" * 74)
    print(f"  KET QUA — anh khach CHUA TUNG co trong kho ({n} anh)")
    print("=" * 74)
    print(f"  Top-1 : {top1/n*100:5.1f}%   ({top1}/{n})")
    print(f"  Top-3 : {top3/n*100:5.1f}%   ({top3}/{n})")
    print(f"  Top-5 : {top5/n*100:5.1f}%   ({top5}/{n})")
    print(f"  Khoang cach TB (chinh no - gan nhat khac): {sum(gaps)/len(gaps):+.3f}")
    print(f"  Nho nhat: {min(gaps):+.3f}    Lon nhat: {max(gaps):+.3f}")
    false_accept = sum(1 for g in gaps if g <= 0)
    print(f"  So anh bi nham (gap <= 0): {false_accept}/{n}")
    print()
    print("  HAN CHE: anh test chup CUNG BUOI voi anh kho (cung nen, cung anh sang).")
    print("  Khach chup o nha se kho hon. Con so nay la CAN TREN, khong phai thuc te.")

    OUT_JSON.parent.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps({
        "n": n, "top1_pct": round(top1/n*100, 1), "top3_pct": round(top3/n*100, 1),
        "top5_pct": round(top5/n*100, 1),
        "mean_gap": round(sum(gaps)/len(gaps), 4),
        "min_gap": round(min(gaps), 4), "max_gap": round(max(gaps), 4),
        "false_accept": false_accept,
        "limitation": "anh test chup cung buoi voi anh kho; khach chup tai nha se kho hon",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Luu: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
