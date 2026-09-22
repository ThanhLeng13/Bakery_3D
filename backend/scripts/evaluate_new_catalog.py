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

    # Nhúng embedding ảnh test, giữ KHOÁ ẢNH của chính ảnh đó.
    #
    # Không dùng `url_by_product` (chỉ giữ URL ĐẦU TIÊN của mỗi sản phẩm): sản
    # phẩm có nhiều ảnh sẽ bị lấy sai URL, dẫn tới loại nhầm ảnh — ảnh test vẫn
    # nằm trong kho và ta lại so ảnh với chính nó, đúng cái lỗi cần tránh.
    #
    # Tên file trên Storage là UUID ngẫu nhiên nên không mang thông tin ảnh gốc,
    # và thứ tự trong `cake_embeddings` cũng không đảm bảo khớp thứ tự trong
    # sheet. Nên chỉ xử lý sản phẩm có ĐÚNG 1 ảnh — khi đó URL là duy nhất và
    # không phải đoán gì cả.
    print("  Dang nhung anh test...")
    t0 = time.perf_counter()
    urls_by_product: dict[str, list[str]] = {}
    for row in rows:
        urls_by_product.setdefault(row["product_id"], []).append(row.get("image_url") or "")

    ambiguous = 0
    query_vecs = []
    for pid, item in queries:
        path = IMAGE_ROOT / item["thu_muc"] / item["file"]
        if not path.exists():
            continue
        urls = urls_by_product.get(pid, [])
        if len(urls) != 1:
            # Nhiều ảnh: không biết ảnh nào là ảnh test -> bỏ qua thay vì đoán.
            ambiguous += 1
            continue
        try:
            query_vecs.append((pid, item["ten_banh"], embed(path.read_bytes()), urls[0]))
        except Exception as exc:
            print(f"    ! {item['file'][:34]}: {type(exc).__name__}")
    print(f"  {len(query_vecs)} anh, {time.perf_counter()-t0:.1f}s")
    if ambiguous:
        print(f"  Bo qua {ambiguous} san pham co nhieu hon 1 anh (khong doan thu tu).")
    print()

    # Nhung lai toan bo kho, giu khoa anh de lat nua loai dung anh test.
    print("  Dang nhung lai kho (de loai anh test ra)...")
    t0 = time.perf_counter()
    catalog_by_image: dict[str, list[tuple[str, np.ndarray]]] = {}
    for row in rows:
        pid = row["product_id"]
        url = row.get("image_url") or ""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BakeryThesis/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
            vec = embed(raw)
        except Exception:
            continue
        catalog_by_image.setdefault(pid, []).append((url, vec))
    print(f"  {sum(len(v) for v in catalog_by_image.values())} embedding / "
          f"{len(catalog_by_image)} mon, {time.perf_counter()-t0:.1f}s")
    print()

    # Đo hold-out: bỏ ĐÚNG ảnh đang test ra khỏi kho, rồi mới tìm.
    #
    # Cách cũ SAI: khi sản phẩm chỉ có 1 embedding, nó lấy sims[0] — mà sims[0]
    # chính là ảnh test so với chính nó, nên luôn ~1.0 và cho ra 100% giả. Bản
    # trước báo "top-1 100%" nhưng thực chất chỉ là ảnh so với chính nó.
    #
    # Lần này loại theo KHOÁ ẢNH (image_url), không theo vị trí, và chỉ chấm điểm
    # khi sản phẩm còn ít nhất 1 ảnh khác. Sản phẩm chỉ có 1 ảnh thì BỎ QUA, vì
    # không còn gì để so — đưa vào sẽ thổi phồng kết quả.
    top1 = top3 = top5 = 0
    gaps = []
    details = []
    skipped_single = 0

    for pid, name, tv, query_url in query_vecs:
        entries = catalog_by_image.get(pid, [])
        # Bỏ ảnh đang test khỏi kho của chính sản phẩm đó.
        remaining = [(u, v) for (u, v) in entries if u != query_url]
        if not remaining:
            # Không còn ảnh nào khác -> không thể chấm điểm công bằng.
            skipped_single += 1
            continue

        scored = []
        for p, items in catalog_by_image.items():
            if p == pid:
                pool = [v for (u, v) in items if u != query_url]
                if not pool:
                    continue
            else:
                pool = [v for (_u, v) in items]
            if not pool:
                continue
            scored.append((max(float(np.dot(tv, v)) for v in pool), p))

        if not scored:
            skipped_single += 1
            continue

        scored.sort(reverse=True)
        ranked = [p for _, p in scored]

        own = next((s for s, p in scored if p == pid), None)
        others = [s for s, p in scored if p != pid]
        if own is None or not others:
            skipped_single += 1
            continue
        other = max(others)
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
            "predicted_id": ranked[0],
        })

    n = len(gaps)
    if n == 0:
        # Chia cho 0 / min() tren list rong se no ra loi kho hieu.
        print()
        print("  KHONG cham duoc anh nao — dung lai, khong ghi bao cao.")
        print(f"  Da bo qua {skipped_single} san pham vi chi co 1 anh duy nhat.")
        print("  Muon do duoc thi moi san pham can TU 2 ANH tro len:")
        print("  mot anh de trong kho, mot anh lam anh khach.")
        return 1

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
    if skipped_single:
        print()
        print(f"  BO QUA {skipped_single} san pham: chi co 1 anh trong kho, nen sau khi")
        print("  loai anh test ra thi khong con gi de so. Day la ly do con so nay")
        print("  KHONG con la 'anh so voi chinh no' nhu ban do truoc.")
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
        "skipped_single_image_products": skipped_single,
        "method": "loai anh test theo image_url; san pham chi co 1 anh bi bo qua",
        "limitation": "anh test chup cung buoi voi anh kho; khach chup tai nha se kho hon",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Luu: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
