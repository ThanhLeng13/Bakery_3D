"""Kiem tra anh san pham that tren CDN + anh embed co dung image_url khong."""
import json, os, sys, urllib.request
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
import supabase

c = supabase.create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

emb = (c.table("cake_embeddings").select("product_id, image_url").execute().data or [])
emb_urls = {e["image_url"] for e in emb}

imgs = (c.table("product_images").select("product_id, url").execute().data or [])
prod_imgs = {i["url"] for i in imgs}

print("  cake_embeddings:", len(emb), " anh duy nhat:", len(emb_urls))
print("  product_images :", len(imgs), " anh duy nhat:", len(prod_imgs))
print("  giao 2 nguon   :", len(emb_urls & prod_imgs))
print()

# Cac san pham co mapping 3D: anh nao dung cho embedding?
links = (c.table("product_3d_models").select("product_id").execute().data or [])
pids = [l["product_id"] for l in links]
names = {p["id"]: p["name"] for p in (c.table("products").select("id,name").in_("id", pids).execute().data or [])}
for pid in pids:
    rows = [e for e in emb if e["product_id"] == pid]
    print(f"  {names.get(pid,'?')[:46]:46s} embed={len(rows)}")
    for r in rows:
        same = "TRUNG" if r["image_url"] in prod_imgs else "KHAC"
        print(f"      {same}  {r['image_url'][:95]}")
    for i in imgs:
        if i["product_id"] == pid:
            print(f"      prod_img    {i['url'][:95]}")
