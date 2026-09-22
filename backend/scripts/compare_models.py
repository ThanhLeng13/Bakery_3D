"""So sanh model CLIP: ViT-B-32 (dang dung) voi ViT-L-14 (lon hon).

VÌ SAO
    Thử tiền xử lý ảnh (cắt logo, cắt viền) KHÔNG cải thiện được gì — xem
    preprocessing_results.json. Cách tốt nhất chỉ +5.6 điểm top-1 nhưng mất
    11.2 điểm top-3, tức là nhiễu chứ không phải tiến bộ.

    Nên câu hỏi tiếp theo là: model lớn hơn có phân biệt tốt hơn không?
    ViT-L-14 dùng vector 768 chiều (so với 512), tham số ~428M (so với ~151M).

LƯU Ý VỀ CHI PHÍ
    ViT-L-14 nặng ~1.7 GB và chậm hơn đáng kể trên CPU. Script này đo luôn thời
    gian suy luận để có số liệu đánh đổi, không chỉ accuracy.

CÁCH DÙNG
    python scripts/compare_models.py
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import numpy as np  # noqa: E402
import open_clip  # noqa: E402
import torch  # noqa: E402
from PIL import Image  # noqa: E402

TEST_DIR = Path(__file__).resolve().parent.parent / "test_images"

# (ten model, pretrained, so chieu vector)
MODELS = [
    ("ViT-B-32", "laion2b_s34b_b79k", 512),   # dang dung
    ("ViT-L-14", "laion2b_s32b_b82k", 768),   # lon hon
]


def embed_with(model, preprocess, raw: bytes, device: str = "cpu") -> np.ndarray:
    """Nhúng một ảnh, trả vector đã chuẩn hoá L2."""
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    tensor = preprocess(image).unsqueeze(0).to(device)
    with torch.no_grad():
        features = model.encode_image(tensor)
    features = features / features.norm(dim=-1, keepdim=True)
    return features.squeeze(0).cpu().numpy().astype(np.float32)


def main() -> int:
    manifest = json.loads((TEST_DIR / "manifest.json").read_text(encoding="utf-8"))
    in_test = [m for m in manifest if m["group"] == "trong_kho"]
    out_test = [m for m in manifest if m["group"] == "ngoai_kho"]

    from supabase import create_client  # noqa: E402

    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    products = {p["id"]: p["name"] for p in client.table("products").select("id,name").execute().data}
    rows = client.table("cake_embeddings").select("product_id,image_url").execute().data

    print("Dang tai anh kho...")
    catalog: dict[str, list[bytes]] = {}
    for row in rows:
        name = products[row["product_id"]]
        try:
            req = urllib.request.Request(row["image_url"], headers={"User-Agent": "BakeryThesis/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                catalog.setdefault(name, []).append(resp.read())
        except Exception as exc:
            print(f"  loi tai {name}: {type(exc).__name__}")
    n_cat = sum(len(v) for v in catalog.values())
    print(f"  {n_cat} anh / {len(catalog)} mon")

    test_items = []
    for item in in_test:
        p = TEST_DIR / item["file"]
        if p.exists():
            test_items.append((item["label"], p.read_bytes()))
    out_items = []
    for item in out_test:
        p = TEST_DIR / item["file"]
        if p.exists():
            out_items.append((item["label"], p.read_bytes()))
    print(f"  {len(test_items)} anh test trong kho, {len(out_items)} anh ngoai kho")
    print()

    summary = []
    for model_name, pretrained, dim in MODELS:
        print("=" * 74)
        print(f"MODEL: {model_name} / {pretrained}  (vector {dim} chieu)")
        print("=" * 74)
        t0 = time.perf_counter()
        try:
            model, _, preprocess = open_clip.create_model_and_transforms(
                model_name, pretrained=pretrained, device="cpu"
            )
            model.eval()
        except Exception as exc:
            print(f"  KHONG TAI DUOC MODEL: {type(exc).__name__}: {str(exc)[:120]}")
            print()
            continue
        load_s = time.perf_counter() - t0
        print(f"  Tai model: {load_s:.1f}s")

        # Embedding kho
        t0 = time.perf_counter()
        catalog_vecs: dict[str, list[np.ndarray]] = {}
        for name, raws in catalog.items():
            vecs = []
            for raw in raws:
                try:
                    vecs.append(embed_with(model, preprocess, raw))
                except Exception:
                    pass
            if vecs:
                catalog_vecs[name] = vecs
        cat_s = time.perf_counter() - t0
        n_done = sum(len(v) for v in catalog_vecs.values())
        print(f"  Nhung {n_done} anh kho: {cat_s:.1f}s  ({cat_s / max(n_done,1)*1000:.0f} ms/anh)")

        if not catalog_vecs:
            # Kho rong => `names` rong => `ranked[0]` ben duoi se IndexError.
            # Thuong do khong tai duoc anh kho (mang/Storage). Bo qua model nay
            # thay vi do ra loi khong lien quan den model.
            print("  KHONG nhung duoc anh kho nao — bo qua model nay.")
            print("  Kiem tra ket noi Supabase Storage va manifest.json.")
            print()
            continue

        # Embedding test
        t0 = time.perf_counter()
        test_vecs = [(lab, embed_with(model, preprocess, raw)) for lab, raw in test_items]
        emb_s = time.perf_counter() - t0
        print(f"  Nhung {len(test_vecs)} anh test: {emb_s:.1f}s  "
              f"({emb_s / max(len(test_vecs),1)*1000:.0f} ms/anh)")

        # Do accuracy
        names = list(catalog_vecs.keys())
        top1 = top3 = 0
        for expected, tv in test_vecs:
            scored = sorted(
                ((max(float(np.dot(tv, v)) for v in catalog_vecs[p]), p) for p in names),
                reverse=True,
            )
            ranked = [p for _, p in scored]
            top1 += int(ranked[0] == expected)
            top3 += int(expected in ranked[:3])
        n = len(test_vecs)
        if n == 0:
            # Chia cho 0 se no ra ZeroDivisionError giua luc dang in ket qua.
            # Bao ro nguyen nhan thay vi de no no ra kho hieu.
            print("  KHONG co anh test nao dung duoc — bo qua model nay.")
            print("  Kiem tra manifest.json va thu muc test_images/ con du khong?")
            continue
        acc1, acc3 = top1 / n * 100, top3 / n * 100

        # Similarity nhom ngoai kho
        miss_sims = []
        for _lab, raw in out_items:
            tv = embed_with(model, preprocess, raw)
            best = max(float(np.dot(tv, v)) for p in names for v in catalog_vecs[p])
            miss_sims.append(best)
        hit_sims = [max(float(np.dot(tv, v)) for v in catalog_vecs[lab])
                    for lab, tv in test_vecs if lab in catalog_vecs]

        print()
        print(f"  Top-1 accuracy            : {acc1:.1f}%  ({top1}/{n})")
        print(f"  Top-3 accuracy            : {acc3:.1f}%  ({top3}/{n})")
        if hit_sims:
            print(f"  Similarity TB (trong kho) : {sum(hit_sims)/len(hit_sims):.3f}")
        if miss_sims:
            print(f"  Similarity TB (ngoai kho) : {sum(miss_sims)/len(miss_sims):.3f}")
        if hit_sims and miss_sims:
            gap = sum(hit_sims)/len(hit_sims) - sum(miss_sims)/len(miss_sims)
            print(f"  Khoang cach hai nhom      : {gap:+.3f}")
        print()

        summary.append({
            "model": model_name, "pretrained": pretrained, "dim": dim,
            "top1": acc1, "top3": acc3, "load_s": round(load_s, 1),
            "ms_per_image": round(emb_s / max(len(test_vecs), 1) * 1000, 1),
            "sim_in": (sum(hit_sims)/len(hit_sims)) if hit_sims else None,
            "sim_out": (sum(miss_sims)/len(miss_sims)) if miss_sims else None,
        })

    print("=" * 74)
    print("TONG HOP")
    print("=" * 74)
    print(f"  {'Model':14s} {'Top-1':>8s} {'Top-3':>8s} {'ms/anh':>8s} {'sim vao':>9s} {'sim ra':>8s}")
    for s in summary:
        print(f"  {s['model']:14s} {s['top1']:7.1f}% {s['top3']:7.1f}% "
              f"{s['ms_per_image']:8.0f} {s['sim_in'] or 0:9.3f} {s['sim_out'] or 0:8.3f}")
    if len(summary) == 2:
        d1 = summary[1]["top1"] - summary[0]["top1"]
        d3 = summary[1]["top3"] - summary[0]["top3"]
        print()
        print(f"  Chenh lech top-1: {d1:+.1f} diem")
        print(f"  Chenh lech top-3: {d3:+.1f} diem")
        print(f"  Cham hon        : {summary[1]['ms_per_image'] / max(summary[0]['ms_per_image'],1):.1f}x")

    (TEST_DIR / "model_comparison.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"  Luu: {TEST_DIR / 'model_comparison.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
