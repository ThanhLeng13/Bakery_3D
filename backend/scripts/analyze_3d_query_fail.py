"""Giai thich ket qua 0/30 cua nhom anh mo hinh 3D.

Gia thuyet: anh render 3D la banh TRANG khong hoa van, nen CLIP khong gan
duoc voi anh san pham thật (anh co hoa van, mau, chu). Do do nhom nay KHONG
do duoc kha nang "tim mau 3D tu anh" ma chi do duoc kha nang phan biet.
"""
import io, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.services.clip_service import ClipSearchService  # noqa: E402

T = Path(__file__).resolve().parent.parent / "test_images"
items = json.loads((T / "manifest_3d.json").read_text(encoding="utf-8"))
service = ClipSearchService()

print("  Xep hang cua san pham CO mapping 3D trong ket qua cua anh 3D:")
print("  (match_count=20 — trần cua search_by_image; 30 se bi clamp ve 20)")
print()
rank_data = []
for it in items:
    p = T / it["file"]
    if not p.exists():
        continue
    res = service.search_by_image(p.read_bytes(), match_count=20, product_type="cake")
    names = [r["name"] for r in res["results"]]
    # San pham 3D trong kho: "2 tang hoa hong", "trai tim figure", "trai tim Happy"
    hits = [i for i, n in enumerate(names) if "2 tầng" in n or "trái tim" in n]
    sims = [r["similarity"] for r in res["results"]]
    best = hits[0] if hits else None
    rank_data.append((it["label"], best, names, sims))
    if best is not None:
        print(f"    {it['label']:16s} -> '{names[best][:34]}'  hang {best+1}  "
              f"sim={sims[best]:.3f}  (top1 sim={sims[0]:.3f})")
    else:
        print(f"    {it['label']:16s} -> khong tim thay san pham 3D trong top 20  "
              f"(top1 sim={sims[0]:.3f})")

print()
found = [r for r in rank_data if r[1] is not None]
print(f"  San pham co mapping 3D nam trong top-20: {len(found)}/{len(rank_data)}")
if found:
    ranks = [r[1] + 1 for r in found]
    sims = [r[3][r[1]] for r in found]
    print(f"    hang trung binh: {sum(ranks)/len(ranks):.1f}  (nho la tot)")
    print(f"    similarity trung binh tai vi tri do: {sum(sims)/len(sims):.3f}")
print()
all_sims = [s for r in rank_data for s in r[3]]
top1s = [r[3][0] for r in rank_data]
print(f"  Similarity top-1 cua nhom anh 3D      : TB {sum(top1s)/len(top1s):.3f} "
      f"(min {min(top1s):.3f}, max {max(top1s):.3f})")
maxes = [max(r[3]) for r in rank_data]
print(f"  Similarity max cua nhom anh 3D         : TB {sum(maxes)/len(maxes):.3f}")
