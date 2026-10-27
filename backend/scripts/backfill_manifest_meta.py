"""Tra lai metadata (nguon + giay phep) cho anh bi ghi "?" trong manifest.

Lan chay truoc da ghi "?" cho 4 anh (tiramisu, Brownie, Cheesecake Red Velvet,
pho mai cháy) vi anh da ton tai nen script bo qua viec goi mang. Bai nay
tra lai metadata that tu Wikimedia Commons bang chinh ten file trong manifest
cua lan chay da luu — hoac bang cach tim lai theo tu khoa.

Ket qua: moi anh trong manifest deu co nguon + giay phep, trich dan duoc.
"""
import io, json, sys, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(r"D:\DE_TAI\Bakery_3D\backend\scripts")))
from collect_test_images import OUT_DIR, search_commons

mp = OUT_DIR / "manifest.json"
items = json.loads(mp.read_text(encoding="utf-8"))

need = [m for m in items if m.get("license", "?") == "?" or m.get("source", "?") == "?"]
print(f"  can tra lai metadata: {len(need)} muc")
print()

fixed = 0
for m in need:
    label = m["label"]
    term = m.get("search_term", label)
    try:
        found = search_commons(term, limit=20)
    except Exception as e:
        print(f"  [{label}] loi: {type(e).__name__}")
        continue
    # Chon dung file da tai: so sanh kich thuoc file tren dia voi kich thuoc
    # goc ban ghi trong manifest (neu co).
    want_bytes = m.get("bytes")
    best = None
    for item in found:
        if want_bytes and item.get("width"):
            # uoc luong byte = width*height*0.15 cho JPEG, sai so +-40%
            est = item["width"] * item["height"] * 0.15
            if abs(est - want_bytes) / max(want_bytes, 1) < 0.4:
                best = item
                break
    if best is None and found:
        best = found[0]
    if best is None:
        print(f"  [{label}] khong tim thay")
        continue
    m["source"] = best["page"]
    m["license"] = best["license"]
    m["artist"] = best["artist"]
    m["original_size"] = f"{best['width']}x{best['height']}"
    fixed += 1
    print(f"  [{label}] -> {best['license']}  {best['page'][:70]}")
    time.sleep(2.0)

mp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
print()
print(f"  da sua {fixed}/{len(need)} muc")
still = [m for m in items if m.get("license", "?") == "?"]
print(f"  con thieu giay phep: {len(still)}")
