"""Kiem chung che do 'chi tra san pham co 3D' tren CSDL THAT."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.services.clip_service import ClipSearchService  # noqa: E402

TEST_DIR = Path(__file__).resolve().parent.parent / "test_images"

# Anh trong kho: dung anh THAT cua san pham co mapping 3D.
# Lay truc tiep tu CSDL de khong doan.
from app.core.dependencies import get_supabase_client  # noqa: E402

client = get_supabase_client(use_service_role=True)

print("=" * 72)
print("SAN PHAM CO MAPPING 3D TREN CSDL THAT")
print("=" * 72)
links = (
    client.table("product_3d_models")
    .select("product_id, is_primary, cake_3d_models(slug, glb_url, is_active)")
    .execute()
).data or []
prod_ids = [l["product_id"] for l in links]
prods = (
    client.table("products")
    .select("id, name, is_active, product_type, base_price")
    .in_("id", prod_ids)
    .execute()
).data or []
pinfo = {p["id"]: p for p in prods}

for l in links:
    m = l["cake_3d_models"] or {}
    p = pinfo.get(l["product_id"], {})
    print(f"  {p.get('name','?')[:42]:42s} -> {m.get('slug','?'):14s}"
          f" active_model={m.get('is_active')} active_prod={p.get('is_active')}")

# Anh trong kho cua cac san pham nay
imgs = (
    client.table("product_images")
    .select("product_id, url")
    .in_("product_id", prod_ids)
    .execute()
).data or []
img_by = {}
for im in imgs:
    img_by.setdefault(im["product_id"], im["url"])

print()
print("=" * 72)
print("DO KET QUA TIM ANH TRUOC / SAU KHI LOC THEO 3D")
print("=" * 72)

service = ClipSearchService()
for pid, url in img_by.items():
    p = pinfo.get(pid, {})
    name = p.get("name", "?")
    try:
        raw = __import__("urllib.request", fromlist=["x"]).urlopen(url, timeout=30).read()
    except Exception as e:
        print(f"  {name[:38]:38s} KHONG TAI DUOC ANH: {type(e).__name__}")
        continue

    r_all = service.search_by_image(raw, match_count=6, product_type="cake")
    r_3d = service.search_by_image(raw, match_count=6, product_type="cake",
                                   has_3d_model=True)

    ids_all = [x["product_id"] for x in r_all["results"]]
    ids_3d = [x["product_id"] for x in r_3d["results"]]
    n_with3d = sum(1 for x in r_all["results"] if x.get("three_d_model"))
    print()
    print(f"  {name[:60]}")
    print(f"    khong loc : {len(ids_all)} ket qua, {n_with3d} co mo hinh 3D")
    print(f"    loc 3D    : {len(ids_3d)} ket qua")
    for x in r_3d["results"]:
        m = x.get("three_d_model") or {}
        print(f"       - {x['name'][:40]:40s} sim={x['similarity']:.3f} 3D={m.get('slug')}")
