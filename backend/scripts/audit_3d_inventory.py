"""Kiểm kê tồn kho 3D trên môi trường THẬT (Supabase), không giả định.

Kiểm tra chuỗi đầy đủ mà kế hoạch yêu cầu (Gói 3, mục 1):
    sản phẩm -> ảnh embed -> mô hình 3D -> file tải được

Chạy: python scripts/audit_3d_inventory.py
"""
import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Accept": "application/json"}

FRONTEND = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend", "public",
)


def rest(path):
    req = urllib.request.Request(URL + "/rest/v1/" + path, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "body": e.read().decode("utf-8", "replace")[:300]}


def head(url):
    """HEAD một URL tĩnh, trả (status, size, content-type)."""
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.headers.get("Content-Length"), r.headers.get("Content-Type")
    except urllib.error.HTTPError as e:
        return e.code, None, None
    except Exception as e:
        # `RemoteDisconnected` thuoc http.client, khong phai urllib.error, nen
        # phai bat rong o day — neu khong, audit se chet giua chung.
        return type(e).__name__, None, None


print("=" * 72)
print("1. BANG TON TAI TREN MOI TRUONG THAT")
print("=" * 72)
tables = ("cake_3d_models", "product_3d_models", "cake_embeddings", "products",
          "product_images", "orders", "order_items")
for tbl in tables:
    r = rest(f"{tbl}?select=*&limit=1")
    if isinstance(r, dict) and "__error__" in r:
        print(f"  {tbl:20s} KHONG TON TAI (HTTP {r['__error__']})")
    else:
        n = rest(f"{tbl}?select=id")
        cnt = len(n) if isinstance(n, list) else "?"
        print(f"  {tbl:20s} TON TAI")

print()
print("=" * 72)
print("2. cake_3d_models")
print("=" * 72)
models = rest("cake_3d_models?select=id,slug,name,glb_url,category,is_active&order=slug")
model_by_id = {}
if isinstance(models, list):
    print(f"  tong: {len(models)}")
    for m in models:
        model_by_id[m["id"]] = m
        print(f"  - {m['slug']:14s} active={str(m['is_active']):5s} {m['glb_url']}")
else:
    print("  LOI:", models)

print()
print("=" * 72)
print("3. FILE GLB THAT SU CO TREN DIA")
print("=" * 72)
if isinstance(models, list):
    for m in models:
        rel = m["glb_url"].split("?")[0].lstrip("/")
        path = os.path.join(FRONTEND, rel.replace("/", os.sep))
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  - {m['slug']:14s} CO   {size:>9,} bytes  {rel}")
        else:
            print(f"  - {m['slug']:14s} THIEU {'':>9} {rel}")

print()
print("=" * 72)
print("4. product_3d_models -> mapping hop le")
print("=" * 72)
links = rest("product_3d_models?select=product_id,model_id,sort_order,is_primary")
if isinstance(links, list):
    print(f"  tong mapping: {len(links)}")
    per = Counter(l["product_id"] for l in links)
    print(f"  san pham duoc lien ket: {len(per)}")
    print(f"  mapping co is_primary=True: {sum(1 for l in links if l.get('is_primary'))}")

    bad_model = [l for l in links if l["model_id"] not in model_by_id]
    print(f"  mapping tro toi model KHONG TON TAI: {len(bad_model)}")

    inactive = [l for l in links if l["model_id"] in model_by_id
                and not model_by_id[l["model_id"]]["is_active"]]
    print(f"  mapping tro toi model KHONG ACTIVE: {len(inactive)}")

    prod_ids = [l["product_id"] for l in links]
    prods = rest("products?select=id,name,is_active,product_type&id=in.("
                 + ",".join(prod_ids) + ")") if prod_ids else []
    prod_by_id = {p["id"]: p for p in prods} if isinstance(prods, list) else {}
    missing_prod = [l for l in links if l["product_id"] not in prod_by_id]
    print(f"  mapping tro toi san pham KHONG TON TAI: {len(missing_prod)}")
    inactive_prod = [l for l in links if l["product_id"] in prod_by_id
                     and not prod_by_id[l["product_id"]]["is_active"]]
    print(f"  mapping tro toi san pham KHONG ACTIVE: {len(inactive_prod)}")

    print()
    print("  chi tiet:")
    for l in links:
        p = prod_by_id.get(l["product_id"], {})
        m = model_by_id.get(l["model_id"], {})
        print(f"  - {p.get('name','?')[:38]:38s} -> {m.get('slug','?'):14s}"
              f" primary={str(l.get('is_primary')):5s} prod_active={p.get('is_active')}"
              f" type={p.get('product_type')}")
else:
    print("  LOI:", links)

print()
print("=" * 72)
print("5. SAN PHAM CO 3D TRONG DANH MUC (ke ca khong co mapping)")
print("=" * 72)
linked_pids = set(l["product_id"] for l in links) if isinstance(links, list) else set()

# Anh khong nam trong `products` — no nam o bang `product_images`.
imgs = rest("product_images?select=product_id,url,sort_order")
img_by_prod = {}
if isinstance(imgs, list):
    for im in imgs:
        img_by_prod.setdefault(im["product_id"], []).append(im.get("url"))
else:
    print("  LOI doc product_images:", imgs)

for label, ptype in (("cake", "cake"), ("sweet", "sweet")):
    rows = rest(f"products?select=id,name,is_active,product_type&product_type=eq.{ptype}")
    if not isinstance(rows, list):
        print(f"  {label}: LOI {rows}")
        continue
    act = [p for p in rows if p["is_active"]]
    with_img = [p for p in act if img_by_prod.get(p["id"])]
    with_3d = [p for p in act if p["id"] in linked_pids]
    print(f"  {label:6s} active={len(act):3d}  co anh={len(with_img):3d}  co 3D={len(with_3d):3d}")

print()
print("  San pham co mapping 3D (chi tiet):")
# `links` co the la dict khi truy van that bai (thi du bang khong ton tai).
# Khi do KHONG duyet — dung va in thong bao, phan con lai cua audit van chay.
if isinstance(links, list):
    for l in links:
        p = prod_by_id.get(l["product_id"], {})
        m = model_by_id.get(l["model_id"], {})
        n_img = len(img_by_prod.get(l["product_id"], []))
        print(f"  - {p.get('name','?')[:40]:40s} -> {m.get('slug','?'):14s} anh={n_img}")
else:
    print(f"  BO QUA chi tiet mapping: truy van that bai -> {links}")

print()
print("=" * 72)
print("6. cake_embeddings -> anh co that khong")
print("=" * 72)
emb = rest("cake_embeddings?select=product_id,image_url,embedding")
if isinstance(emb, list):
    print(f"  tong embedding: {len(emb)}")
    no_img = [e for e in emb if not e.get("image_url")]
    print(f"  embedding thieu image_url: {len(no_img)}")
    pids = set(e["product_id"] for e in emb if e.get("product_id"))
    print(f"  so san pham duoc embed: {len(pids)}")
    # anh trong kho vs anh ngoai kho
    ext = [e for e in emb if e.get("image_url") and "http" in str(e["image_url"])]
    print(f"  embedding tro toi URL ngoai: {len(ext)}")
    if ext:
        print("   (vi du)", ext[0]["image_url"][:90])
else:
    print("  LOI:", emb)

print()
print("=" * 72)
print("7. FILE GLB TRAI DUOC QUA HTTP (khong phai chi co tren dia)")
print("=" * 72)
BASE = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3100")
if isinstance(models, list):
    for m in models:
        st, size, ctype = head(BASE + m["glb_url"])
        flag = "OK " if st == 200 else "LOI"
        print(f"  {flag} {m['slug']:14s} HTTP {st}  size={size}  type={ctype}")
    print(f"  (frontend dang chay tai {BASE} — neu tat, se bao loi ket noi)")
