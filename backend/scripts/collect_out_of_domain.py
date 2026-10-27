"""Tải thêm ảnh NGOÀI MIỀN BÁH (không phải bánh) để đủ ngưỡng 10 ảnh.

Hiện nhóm `ngoai_kho` lẫn hai loại: món KHÔNG có trong kho (pizza, ô tô…)
và món CÓ LÀ BÁNH nhưng không có trong kho (donut, bánh mặn). Đề tài yêu cầu
"ít nhất 10 ảnh ngoài miền bánh" — nghĩa là thứ KHÔNG PHẢI BÁNH. Tách ra
thành nhóm riêng để đo đúng ý nghĩa:

  ngoai_mien_banh  — không phải bánh (đồ ăn khác, đồ vật) → hệ thống phải từ chối
  ngoai_kho        — có là bánh nhưng kho không có món đó → hệ thống phải gần đúng

CÁCH DÙNG
    python scripts/collect_out_of_domain.py
"""

from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

# KHÔNG bọc stdout ở đây: `collect_test_images` (import bên dưới) đã tự bọc,
# và bọc hai lần sẽ đóng luôn stdout của script này.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from collect_test_images import (  # noqa: E402
    OUT_DIR,
    download,
    search_commons,
)

# 14 món KHÔNG PHẢI Bánh. Chọn cả món ăn (dễ nhầm với bánh) lẫn đồ vật
# (rõ ràng không phải bánh) để đo được cả hai kiểu từ chối.
OUT_OF_DOMAIN = {
    "pizza": "pizza margherita",
    "hamburger": "hamburger sandwich",
    "sushi": "sushi plate",
    "pho": "pho noodle soup",
    "salad": "green salad bowl",
    "cafe": "espresso coffee cup",
    "oto": "automobile car",
    "banh mi": "banh mi vietnamese sandwich",
    "bun bo": "beef noodle soup bowl",
    "goi cuon": "summer rolls rice paper",
    "cha": "cup of tea",
    "dau an": "fruit juice glass",
    "banh bao": "steamed bun dim sum",
    "xuc xich": "sausage grilled food",
}


def main() -> int:
    group = "ngoai_mien_banh"
    out_dir = OUT_DIR / group
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 74)
    print(f"THU THAP ANH NGOAI MIEN BAH ({len(OUT_OF_DOMAIN)} muc)")
    print("=" * 74)
    print()

    manifest: list[dict] = []
    for label, term in OUT_OF_DOMAIN.items():
        safe = label.replace(" ", "_").replace("/", "-")
        dest = out_dir / f"{safe}__1.jpg"
        if dest.exists():
            print(f"  [{group}] {label}  (da co, bo qua)")
            continue
        print(f"  [{group}] {label}")
        try:
            found = search_commons(term)
        except Exception as exc:
            print(f"      loi tim kiem: {type(exc).__name__}")
            continue
        if not found:
            print("      khong tim thay ket qua")
            continue
        for item in found:
            ok, nbytes = download(item["url"], dest)
            if not ok:
                continue
            manifest.append({
                "group": group,
                "label": label,
                "search_term": term,
                "file": str(dest.relative_to(OUT_DIR)),
                "bytes": nbytes,
                "source": item["page"],
                "license": item["license"],
                "artist": item["artist"],
                "original_size": f"{item['width']}x{item['height']}",
            })
            print(f"      luu {dest.name}  ({nbytes // 1024} KB, {item['license']})")
            break
        time.sleep(2.0)

    # Gộp vào manifest chính nếu có.
    main_manifest = OUT_DIR / "manifest.json"
    if main_manifest.exists():
        existing = json.loads(main_manifest.read_text(encoding="utf-8"))
        have = {m.get("file") for m in existing}
        for m in manifest:
            if m["file"] not in have:
                existing.append(m)
        main_manifest.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n  manifest.json: {len(existing)} muc")
    else:
        (OUT_DIR / "manifest_out_of_domain.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n  manifest_out_of_domain.json: {len(manifest)} muc")

    print(f"  thu muc: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
