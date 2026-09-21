"""Đo độ chính xác CLIP bằng ảnh NGOÀI kho.

VÌ SAO KHÁC BÀI TEST CŨ
    Bài test cũ lấy ảnh trong kho rồi tìm lại chính nó — luôn ra 100%, vì vector
    truy vấn TRÙNG KHÍT vector đã lưu. Con số đó không nói lên điều gì về việc
    khách chụp ảnh ngoài đời rồi tìm.

    Script này dùng ảnh tải từ Wikimedia Commons: khác nguồn, khác góc chụp, khác
    ánh sáng, khác nền. Đây mới là tình huống thật.

ĐO HAI THỨ
    1. Top-1 / Top-3 accuracy trên ảnh thuộc món CÓ trong kho.
    2. Phân bố similarity trên ảnh KHÔNG thuộc kho (pizza, xe hơi…). Hệ thống
       tốt phải cho điểm thấp ở nhóm này; nếu vẫn cao thì nó đang "match bừa".

CÁCH DÙNG
    python scripts/evaluate_clip_accuracy.py
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.services.clip_service import (  # noqa: E402
    ClipSearchService,
    embed_image_bytes,
)

TEST_DIR = Path(__file__).resolve().parent.parent / "test_images"


def load_manifest() -> list[dict]:
    path = TEST_DIR / "manifest.json"
    if not path.exists():
        print("  Chua co manifest.json. Chay collect_test_images.py truoc.")
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    manifest = load_manifest()
    if not manifest:
        return 1

    service = ClipSearchService()

    in_catalog = [m for m in manifest if m["group"] == "trong_kho"]
    out_catalog = [m for m in manifest if m["group"] == "ngoai_kho"]

    print("=" * 78)
    print("DO DO CHINH XAC CLIP BANG ANH NGOAI KHO")
    print("=" * 78)
    print(f"  Anh thuoc mon co trong kho : {len(in_catalog)}")
    print(f"  Anh KHONG thuoc kho        : {len(out_catalog)}")
    print()

    # ─── Phần 1: ảnh thuộc món có trong kho ──────────────────────────────────
    print("=" * 78)
    print("PHAN 1: ANH THUOC MON CO TRONG KHO")
    print("=" * 78)
    print(f"  {'Anh':38s} {'Mong doi':26s} {'Top-1 tra ve':26s} {'sim':>6s} {'KQ':>4s}")
    print("  " + "-" * 74)

    top1 = top3 = total = 0
    rows: list[dict] = []
    sims_hit: list[float] = []

    for item in in_catalog:
        path = TEST_DIR / item["file"]
        if not path.exists():
            continue
        raw = path.read_bytes()
        try:
            result = service.search_by_image(raw, match_count=6, match_threshold=0.0)
        except Exception as exc:
            print(f"  {path.name[:36]:38s} LOI: {type(exc).__name__}")
            continue

        results = result["results"]
        if not results:
            continue

        expected = item["label"]
        # Kiểm tra khoá tồn tại thay vì đoán: nếu tầng service đổi tên trường,
        # script phải báo rõ chứ không được âm thầm cho điểm sai.
        missing = [k for k in ("name", "similarity") if k not in results[0]]
        if missing:
            print(f"  LOI: ket qua thieu truong {missing}. "
                  f"Cac truong co: {sorted(results[0])}")
            return 1
        names = [r["name"] for r in results]
        hit1 = names[0] == expected
        hit3 = expected in names[:3]
        top1 += int(hit1)
        top3 += int(hit3)
        total += 1
        sims_hit.append(results[0]["similarity"])

        mark = "OK" if hit1 else ("top3" if hit3 else "TRUOT")
        short = path.name.replace("__", " #").replace(".jpg", "")
        print(f"  {short[:36]:38s} {expected[:24]:26s} {names[0][:24]:26s} "
              f"{results[0]['similarity']:6.3f} {mark:>4s}")
        rows.append({
            "file": item["file"], "expected": expected,
            "top1": names[0], "top3": names[:3],
            "sim1": results[0]["similarity"],
            "correct_top1": hit1, "correct_top3": hit3,
        })

    print("  " + "-" * 74)
    if total:
        print(f"  Top-1 accuracy : {top1}/{total} = {top1 / total * 100:.1f}%")
        print(f"  Top-3 accuracy : {top3}/{total} = {top3 / total * 100:.1f}%")
    print()

    # ─── Phần 2: ảnh KHÔNG thuộc kho ─────────────────────────────────────────
    print("=" * 78)
    print("PHAN 2: ANH KHONG THUOC KHO (do kha nang KHONG match bua)")
    print("=" * 78)
    print(f"  {'Anh':26s} {'Top-1 (gan nhat)':28s} {'sim cao nhat':>12s}")
    print("  " + "-" * 74)

    sims_miss: list[float] = []
    for item in out_catalog:
        path = TEST_DIR / item["file"]
        if not path.exists():
            continue
        try:
            result = service.search_by_image(
                path.read_bytes(), match_count=1, match_threshold=0.0
            )
        except Exception as exc:
            print(f"  {item['label'][:24]:26s} LOI: {type(exc).__name__}")
            continue
        results = result["results"]
        if not results:
            continue
        sims_miss.append(results[0]["similarity"])
        print(f"  {item['label'][:24]:26s} {results[0]['name'][:26]:28s} "
              f"{results[0]['similarity']:12.3f}")

    print("  " + "-" * 74)

    # ─── Tổng hợp ────────────────────────────────────────────────────────────
    print()
    print("=" * 78)
    print("TONG HOP")
    print("=" * 78)
    if total:
        print(f"  Top-1 accuracy            : {top1 / total * 100:.1f}%  ({top1}/{total})")
        print(f"  Top-3 accuracy            : {top3 / total * 100:.1f}%  ({top3}/{total})")

    if sims_hit:
        print(f"  Similarity TB (trong kho) : {sum(sims_hit) / len(sims_hit):.3f}  "
              f"(min {min(sims_hit):.3f}, max {max(sims_hit):.3f})")
    if sims_miss:
        print(f"  Similarity TB (ngoai kho) : {sum(sims_miss) / len(sims_miss):.3f}  "
              f"(min {min(sims_miss):.3f}, max {max(sims_miss):.3f})")

    if sims_hit and sims_miss:
        avg_hit = sum(sims_hit) / len(sims_hit)
        avg_miss = sum(sims_miss) / len(sims_miss)
        print(f"  Khoang cach hai nhom      : {avg_hit - avg_miss:+.3f}")
        print()
        # Ngưỡng gợi ý: nằm giữa hai nhóm. Nếu hai nhóm chồng lấn nhiều thì
        # không ngưỡng nào tách sạch được, và đó là điều cần nói thật.
        threshold = (avg_hit + avg_miss) / 2
        print(f"  Nguong goi y              : {threshold:.3f} "
              f"(trung diem hai nhom)")
        overlap = [s for s in sims_miss if s >= threshold]
        missed = [s for s in sims_hit if s < threshold]
        print(f"    - Anh ngoai kho bi nhan nham : {len(overlap)}/{len(sims_miss)}")
        print(f"    - Anh trong kho bi bo sot    : {len(missed)}/{len(sims_hit)}")

    # Lưu kết quả để đưa vào luận văn
    out = {
        "top1_accuracy": (top1 / total * 100) if total else None,
        "top3_accuracy": (top3 / total * 100) if total else None,
        "n_in_catalog": total,
        "n_out_catalog": len(sims_miss),
        "sim_avg_in": (sum(sims_hit) / len(sims_hit)) if sims_hit else None,
        "sim_avg_out": (sum(sims_miss) / len(sims_miss)) if sims_miss else None,
        "details": rows,
    }
    report = TEST_DIR / "accuracy_report.json"
    report.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"  Bao cao chi tiet: {report}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
