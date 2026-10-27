"""Xây bộ ảnh truy vấn phủ 6 kiểu thân từ ảnh render 3D của chính dự án.

VÌ SAO CẦN
    Đề tài yêu cầu bộ ảnh truy vấn độc lập phủ 6 kiểu thân. Kho ảnh sản phẩm
    KHÔNG phủ được: mỗi sản phẩm chỉ có đúng một ảnh, và ảnh đó đã được embed
    (đo được trên CSDL thật: 121 dòng `cake_embeddings` trùng khớp 121 dòng
    `product_images`, cùng URL). Lấy ảnh kho làm ảnh truy vấn thì đó là
    self-match — không đo được gì.

    Nguồn ảnh truy vấn độc lập, không phụ thuộc quyền bên ngoài: ẢNH RENDER TỪ
    FILE GLB CỦA CHÍNH DỰ ÁN. Mỗi file GLB là một kiểu thân (tròn 1/2/3 tầng,
    trái tim, vuông, cao); mỗi kiểu có nhiều góc nhìn. Ảnh này:
      - độc lập với ảnh trong kho (không phải ảnh đã embed)
      - phủ đủ 6 kiểu thân
      - quyền sử dụng thuộc về chính dự án → trích dẫn được trong luận văn

    Ảnh được render bằng `frontend/scripts/capture-cake-shots.mjs` (Chrome
    headless, WebGL qua SwiftShader).

CÁCH DÙNG
    python scripts/build_3d_query_set.py

ĐẦU RA
    backend/test_images/mo_hinh_3d/<slug>__<view>.jpg   (ảnh JPEG)
    backend/test_images/manifest_3d.json               (nhãn + nguồn + quyền)
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
SHOT_DIR = REPO / "frontend" / "tmp_shots"
OUT_DIR = BACKEND / "test_images" / "mo_hinh_3d"
MANIFEST = BACKEND / "test_images" / "manifest_3d.json"

# Kiểu thân → file GLB trong `frontend/public/models/`.
# Tên file là bằng chứng nguồn gốc: ảnh truy vấn render từ đúng file đó.
MODELS = {
    "round-1-tier": "cake-tron-1-tang.glb",
    "round-2-tier": "cake-tron-2-tang.glb",
    "round-3-tier": "cake-tron-3-tang.glb",
    "heart-1-tier": "cake-trai-tim.glb",
    "square-1-tier": "cake-vuong-1-tang.glb",
    "tall-1-tier": "cake-cao-1-tang.glb",
}

# 5 góc mỗi kiểu = 30 ảnh, đúng ngưỡng đề tài yêu cầu.
# Chọn góc đa dạng: 3 góc tĩnh khác nhau + 2 góc xoay, để ảnh truy vấn không
# phải lúc nào cũng đúng một góc cố định.
VIEWS = ["front", "top", "side", "spin-0", "spin-3"]


def main() -> int:
    from PIL import Image

    print("=" * 74)
    print("XAY BO ANH TRUY VAN PHU 6 KIEU THAN (TU GLB CUA CHINH DU AN)")
    print("=" * 74)
    print()

    if not SHOT_DIR.exists():
        print(f"  LOI: khong thay thu muc anh chup {SHOT_DIR}")
        print("       Chay truoc: cd frontend && node scripts/capture-cake-shots.mjs")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    missing: list[str] = []

    for slug, glb in MODELS.items():
        for view in VIEWS:
            src = SHOT_DIR / f"{slug}-{view}.png"
            if not src.exists():
                missing.append(src.name)
                continue

            dest = OUT_DIR / f"{slug}__{view}.jpg"
            with Image.open(src) as im:
                # JPEG chất lượng 92: giữ đủ chi tiết để CLIP nhìn ra hình dạng,
                # nhưng file nhỏ hơn PNG nhiều (PNG 1.5 MB -> JPEG ~120 KB).
                im.convert("RGB").save(dest, "JPEG", quality=92, optimize=True)

            manifest.append({
                "group": "mo_hinh_3d",
                "label": slug,
                "search_term": f"mo hinh 3D: {slug}",
                "file": dest.relative_to(BACKEND / "test_images").as_posix(),
                "bytes": dest.stat().st_size,
                "source": (
                    f"render trong {slug}-*.glb cua chinh du an "
                    f"(frontend/public/models/{glb}), chup bang Chrome headless"
                ),
                "source_file": f"frontend/public/models/{glb}",
                "license": "CC0 / thuoc ve chinh du an",
                "artist": "Do nhom phat trien du an render",
                "original_size": f"{im.width}x{im.height}",
                "view": view,
            })

    if missing:
        # KHONG ghi manifest khi con thieu anh: ban ghi ghi day so la "co du
        # anh" se khong khop anh thuc te, va moi lan do lai lai bang manifest
        # cu hon se lam hong ca bo do.
        print()
        print(f"  THIEU {len(missing)} anh chup (khong co de render):")
        for m in missing:
            print(f"    - {m}")
        print(f"  KHONG ghi {MANIFEST} de khong cong bo bo ban ghi thieu.")
        return 1

    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"  da tao {len(manifest)} anh trong {OUT_DIR}")
    per_model: dict[str, int] = {}
    for item in manifest:
        per_model[item["label"]] = per_model.get(item["label"], 0) + 1
    for slug in MODELS:
        print(f"    {slug:16s} {per_model.get(slug, 0)} anh")
    print()
    print(f"  manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
