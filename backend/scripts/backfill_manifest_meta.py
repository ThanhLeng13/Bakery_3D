"""Tra lai metadata (nguon + giay phep) cho anh bi ghi "?" trong manifest.

Lan chay truoc da ghi "?" cho 4 anh (tiramisu, Brownie, Cheesecake Red Velvet,
pho mai cháy) vi anh da ton tai nen script bo qua viec goi mang. Bai nay
tra lai metadata that tu Wikimedia Commons bang chinh ten file trong manifest
cua lan chay da luu — hoac bang cach tim lai theo tu khoa.

Ket qua: moi anh trong manifest deu co nguon + giay phep, trich dan duoc.
"""
import hashlib, io, json, sys, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_test_images import OUT_DIR, _fetch, search_commons

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
    # Chon DUNG file da tai: phai co bang chung doi chieu, khong phai do.
    #
    # Cach cu: uoc luong byte theo width*height*0.15 (sai so +-40%), roi lay
    # `found[0]` khi khong tim duoc. Ca hai deu SAI: uoc luong co sai so lon,
    # va `found[0]` co the la mot anh hoan toan khac — gan nguon/giay phep
    # sai cho anh do. Trong luan van, trich dan sai la loi nghiem trong.
    #
    # Cach dung: tai `thumburl` cua tung candidate roi so SANH BYTE voi file
    # da luu. Chi khi trung byte moi gan metadata.
    img_path = OUT_DIR / m["file"]
    if not img_path.exists():
        print(f"  [{label}] khong tim thay file anh tren dia")
        continue
    local = hashlib.sha256(img_path.read_bytes()).hexdigest()

    best = None
    for item in found:
        try:
            blob = _fetch(item["url"], timeout=60)
        except Exception:
            continue
        if hashlib.sha256(blob).hexdigest() == local:
            best = item
            break
    if best is None:
        # KHONG gan metadata tu candidate nao khong xac minh duoc. Giu nguyen
        # "?" de bao cao thang nhap thieu giay phep — hon la trich dan sai.
        print(f"  [{label}] khong xac minh duoc anh nao (giu nguyen '?')")
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
