"""Kiem chung endpoint POST /api/v1/search/by-image voi loc 3D tren API that."""
import json
import os
import sys
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
import supabase  # noqa: E402

API = "http://127.0.0.1:8000"
c = supabase.create_client(
    os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
)


def post_image(image_bytes: bytes, **fields):
    boundary = uuid.uuid4().hex
    parts = []
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="t.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'
        ).encode()
        + image_bytes
        + b"\r\n"
    )
    for k, v in fields.items():
        parts.append(
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'
            ).encode()
        )
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(
        f"{API}/api/v1/search/by-image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.load(resp)


# Anh thật của các sản phẩm CÓ mapping 3D.
links = (
    c.table("product_3d_models").select("product_id").execute().data or []
)
pids = [l["product_id"] for l in links]
imgs = (
    c.table("product_images").select("product_id,url").in_("product_id", pids).execute().data or []
)
prods = {
    p["id"]: p
    for p in (c.table("products").select("id,name").in_("id", pids).execute().data or [])
}

for im in imgs:
    raw = urllib.request.urlopen(im["url"], timeout=30).read()
    name = prods.get(im["product_id"], {}).get("name", "?")
    print()
    print(f"  {name[:60]}")

    r_all = post_image(raw, match_count=6, product_type="cake")
    r_3d = post_image(raw, match_count=6, product_type="cake", has_3d_model="true")
    print(f"    khong loc : {r_all['count']} ket qua, "
          f"{sum(1 for x in r_all['results'] if x.get('three_d_model'))} co mo hinh 3D")
    print(f"    loc 3D    : {r_3d['count']} ket qua")
    for x in r_3d["results"]:
        m = x.get("three_d_model") or {}
        print(f"       - {x['name'][:38]:38s} sim={x['similarity']:.3f} "
              f"3D={m.get('slug')} orderable={m.get('is_orderable')}")

    # Ảnh không phải bánh → phải trả rỗng, không vỡ.
    fake = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
    try:
        r_fake = post_image(fake, match_count=6, product_type="cake")
        print(f"    anh gia (khong phai anh that): count={r_fake['count']}")
    except urllib.error.HTTPError as e:
        print(f"    anh gia -> HTTP {e.code} (bi chan, dung)")
