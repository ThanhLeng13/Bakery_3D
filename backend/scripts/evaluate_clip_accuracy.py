"""Đo độ chính xác CLIP trên bộ ảnh truy vấn độc lập.

BỘ ẢNH (đo được trên đĩa, xem `manifest.json` và `manifest_3d.json`)
    trong_kho        18 ảnh — món CÓ trong kho (Wikimedia Commons)
    mo_hinh_3d      30 ảnh — 6 kiểu thân, render từ GLB của chính dự án
    ngoai_kho       10 ảnh — LÀ bánh nhưng kho không có món đó
    ngoai_mien_banh 16 ảnh — KHÔNG phải bánh (đồ ăn khác, đồ vật)

VÌ SAO TÁCH 4 NHÓM
    Nhóm "trong_kho" đo độ đúng (top-1/top-3).
    Nhóm "ngoai_mien_banh" đo khả năng TỪ CHỐI — ảnh không phải bánh thì hệ
    thống phải cho điểm thấp. Đây là ngưỡng chặn "match bừa".
    Nhóm "ngoai_kho" đo khả năng "đúng một món khác": vẫn là bánh, nhưng kho
    không có → hệ thống nên trả về món gần nhất chứ không phải im lặng.
    Nhóm "mo_hinh_3d" đo việc nhận dạng KIỂU THÂN — dùng để kiểm tra chế độ
    tìm mẫu 3D có thực sự tìm ra mẫu 3D đúng không.

LƯU Ý VỀ ẢNH "TRONG KHO"
    Đo được trên CSDL thật: 121 dòng `cake_embeddings` trùng khớp 121 dòng
    `product_images` (cùng URL) — mỗi sản phẩm CHỈ có một ảnh, và ảnh đó
    đã được embed. Vì vậy ảnh "trong_kho" ở đây là ảnh TẢI TỪ WIKIMEDIA,
    không phải ảnh trong kho: đó mới là ảnh truy vấn độc lập.

CÁCH DÙNG
    python scripts/evaluate_clip_accuracy.py
"""

from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _configure_stdout() -> None:
    """Dùng UTF-8 khi chạy script trực tiếp, không đổi stdout lúc được import.

    Import-time mutation trước đây làm test không thể import script an toàn:
    pytest/capsys đang sở hữu `sys.stdout`, còn script thay nó bằng wrapper mới.
    """
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.services.clip_service import (  # noqa: E402
    ClipSearchService,
    embed_image_bytes,
)

TEST_DIR = Path(__file__).resolve().parent.parent / "test_images"

GROUPS = {
    "trong_kho": "mon co trong kho",
    "mo_hinh_3d": "mo hinh 3D (6 kieu than)",
    "ngoai_kho": "la banh nhung kho khong co",
    "ngoai_mien_banh": "khong phai banh",
}


def load_manifest() -> list[dict]:
    items: list[dict] = []
    for name in ("manifest.json", "manifest_3d.json"):
        path = TEST_DIR / name
        if not path.exists():
            continue
        for item in json.loads(path.read_text(encoding="utf-8")):
            # Manifest ghi duong dan POSIX ("ngoai_kho/x.jpg"). Khi chay tren
            # Windows, `Path` / "ngoai_kho/x.jpg" tao ra "ngoai_kho\\x.jpg" —
            # dung khi nen chuan hoa ve "ngoai_kho/x.jpg" de chay duoc ca hai.
            item["file"] = item["file"].replace("\\", "/")
            item["_manifest"] = name
            items.append(item)
    return items


def main() -> int:
    manifest = load_manifest()
    if not manifest:
        print("  Chua co manifest. Chay collect_test_images.py truoc.")
        return 1

    service = ClipSearchService()

    by_group = {g: [m for m in manifest if m["group"] == g] for g in GROUPS}

    print("=" * 78)
    print("DO DO CHINH XAC CLIP — BO ANH TRUY VAN DOC LAP")
    print("=" * 78)
    for g, desc in GROUPS.items():
        print(f"  {g:18s} {len(by_group[g]):3d} anh   ({desc})")
    print()

    # ─── Phần 1: ảnh thuộc món có trong kho → đo top-1/top-3 ────────────────
    print("=" * 78)
    print("PHAN 1: ANH THUOC MON CO TRONG KHO (do top-1/top-3)")
    print("=" * 78)
    print(f"  {'Anh':34s} {'Mong doi':24s} {'Top-1 tra ve':24s} {'sim':>6s} {'KQ':>5s}")
    print("  " + "-" * 74)

    top1 = top3 = total = 0
    rows: list[dict] = []
    sims_hit: list[float] = []

    for item in by_group["trong_kho"]:
        path = TEST_DIR / item["file"]
        if not path.exists():
            continue
        try:
            result = service.search_by_image(path.read_bytes(), match_count=6, match_threshold=0.0)
        except Exception as exc:
            print(f"  {path.name[:32]:34s} LOI: {type(exc).__name__}")
            continue
        results = result["results"]
        if not results:
            continue

        expected = item["label"]
        missing = [k for k in ("name", "similarity") if k not in results[0]]
        if missing:
            print(f"  LOI: ket qua thieu truong {missing}. Co: {sorted(results[0])}")
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
        print(f"  {short[:34]:36s} {expected[:24]:26s} {names[0][:24]:26s} "
              f"{results[0]['similarity']:6.3f} {mark:>5s}")
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

    # ─── Phần 2: ảnh ngoài miền bánh → đo khả năng từ chối ──────────────────
    print("=" * 78)
    print("PHAN 2: ANH NGOAI MIEN BANH (do kha nang tu choi)")
    print("=" * 78)
    print(f"  {'Anh':26s} {'Top-1 (gan nhat)':28s} {'sim':>8s}")
    print("  " + "-" * 74)

    sims_ood: list[float] = []
    ood_rows: list[dict] = []
    for item in by_group["ngoai_mien_banh"]:
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
        sims_ood.append(results[0]["similarity"])
        ood_rows.append({
            "file": item["file"], "label": item["label"],
            "top1": results[0]["name"], "sim1": results[0]["similarity"],
        })
        print(f"  {item['label'][:24]:26s} {results[0]['name'][:26]:28s} "
              f"{results[0]['similarity']:8.3f}")

    print("  " + "-" * 74)

    # ─── Phần 3: ảnh là bánh nhưng ngoài kho ──────────────────────────────────
    print()
    print("=" * 78)
    print("PHAN 3: ANH LA BANH NHUNG KHO KHONG CO (do do phu hop)")
    print("=" * 78)
    sims_out: list[float] = []
    for item in by_group["ngoai_kho"]:
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
        sims_out.append(results[0]["similarity"])
        print(f"  {item['label'][:24]:26s} {results[0]['name'][:26]:28s} "
              f"{results[0]['similarity']:8.3f}")
    print("  " + "-" * 74)

    # ─── Phần 4: ảnh mô hình 3D → đo nhận dạng kiểu thân ────────────────────
    print()
    print("=" * 78)
    print("PHAN 4: ANH MO HINH 3D (do nhan dang kieu than)")
    print("=" * 78)
    print(f"  {'Kieu than':16s} {'Top-1':30s} {'sim':>6s}  {'co mo hinh 3D':>14s}")
    print("  " + "-" * 74)

    # `body_hits` = top-1 KHOP KIỂU THÂN (slug của mô hình trùng nhãn ảnh).
    # `viewable` = top-1 có mô hình 3D mở được, KHÔNG quan tâm đúng kiểu.
    # Hai thứ này khác nhau: đo gộp chung sẽ báo "nhận dạng kiểu thân"
    # trong khi thực ra chỉ đo được "có mô hình 3D hay không".
    body_hits = 0
    body_total = 0
    viewable = 0
    filtered_hits = 0
    filtered_total = 0
    with3d = 0
    body_rows: list[dict] = []
    for item in by_group["mo_hinh_3d"]:
        path = TEST_DIR / item["file"]
        if not path.exists():
            continue
        try:
            image_bytes = path.read_bytes()
        except OSError as exc:
            print(f"  {item['label'][:24]:26s} LOI DOC ANH: {type(exc).__name__}")
            continue

        # ĐO ĐỘC LẬP chế độ lọc 3D trước lượt đo không lọc bên dưới. Một lỗi
        # hoặc kết quả rỗng của lượt không lọc không được làm mất mẫu số của
        # điều khoản "Chỉ mẫu có 3D": ảnh vẫn có sẵn để thử đúng chế độ đó.
        # `filtered_total` đếm MỌI lượt lọc đã thử, kể cả lượt lỗi/rỗng.
        filtered_total += 1
        try:
            fresult = service.search_by_image(
                image_bytes, match_count=6, product_type="cake",
                has_3d_model=True,
            )
        except Exception as exc:
            print(f"  {item['label'][:24]:26s} LOI (loc 3D): {type(exc).__name__}")
            fresult = None
        if fresult is not None:
            fres = fresult["results"]
            if fres and all(r.get("three_d_model") for r in fres):
                filtered_hits += 1

        # Đo xếp hạng kiểu thân là chỉ số RIÊNG. Lỗi/rỗng chỉ loại ảnh khỏi
        # mẫu số `body_total`, không ảnh hưởng phép đo lọc 3D đã chạy ở trên.
        try:
            result = service.search_by_image(
                image_bytes, match_count=6, product_type="cake"
            )
        except Exception as exc:
            print(f"  {item['label'][:24]:26s} LOI: {type(exc).__name__}")
            continue
        results = result["results"]
        if not results:
            continue
        body_total += 1
        top = results[0]
        n3d = sum(1 for r in results if r.get("three_d_model"))
        with3d += n3d
        # HIT = kết quả đầu có mô hình 3D đúng kiểu thân của ảnh truy vấn.
        # Chỉ có mô hình 3D thôi là chưa đủ — mô hình sai kiểu vẫn là sai.
        top_model = top.get("three_d_model") or {}
        top_slug = top_model.get("slug")
        hit = bool(top_slug) and top_slug == item["label"]
        body_hits += int(hit)
        viewable += int(bool(top_slug))
        print(f"  {item['label'][:16]:16s} {top['name'][:28]:30s} "
              f"{top['similarity']:6.3f}  {n3d}/{len(results):>12}  "
              f"{'HIT' if hit else 'truot'}  slug={top_slug or '-'}")
        body_rows.append({
            "file": item["file"], "body": item["label"],
            "top1": top["name"], "sim1": top["similarity"],
            "n_results_with_3d": n3d, "hit": hit, "top_slug": top_slug,
        })

    print("  " + "-" * 74)
    if body_total:
        print(f"  Top-1 KHOP KIỂU THÂN (slug == nhãn) : {body_hits}/{body_total} = "
              f"{body_hits / body_total * 100:.1f}%")
        print(f"  Top-1 có mô hình 3D mở được       : {viewable}/{body_total} = "
              f"{viewable / body_total * 100:.1f}%")
    if filtered_total:
        print(f"  Chế độ lọc 3D — mọi kết quả mở được viewer: "
              f"{filtered_hits}/{filtered_total}")

    # ─── Tổng hợp ────────────────────────────────────────────────────────────
    print()
    print("=" * 78)
    print("TONG HOP")
    print("=" * 78)
    if total:
        print(f"  Top-1 accuracy (trong kho)   : {top1 / total * 100:.1f}%  ({top1}/{total})")
        print(f"  Top-3 accuracy (trong kho)   : {top3 / total * 100:.1f}%  ({top3}/{total})")
    if body_total:
        print(f"  Nhận dạng kiểu thân (slug khớp): {body_hits / body_total * 100:.1f}%  "
              f"({body_hits}/{body_total})")
        print(f"  Top-1 có mô hình 3D mở được   : {viewable / body_total * 100:.1f}%  "
              f"({viewable}/{body_total})")
    if filtered_total:
        print(f"  Chế độ lọc 3D — kết quả mở được viewer: "
              f"{filtered_hits}/{filtered_total}")

    def avg(xs):
        return sum(xs) / len(xs) if xs else None

    for label, xs in (
        ("trong kho", sims_hit),
        ("ngoai kho", sims_out),
        ("ngoai mien banh", sims_ood),
    ):
        if xs:
            print(f"  Similarity TB ({label:16s}) : {avg(xs):.3f}  "
                  f"(min {min(xs):.3f}, max {max(xs):.3f})")

    if sims_hit and sims_ood:
        threshold = (avg(sims_hit) + avg(sims_ood)) / 2
        print()
        print(f"  Khoang cach trong-kho vs ngoai-mien: {avg(sims_hit) - avg(sims_ood):+.3f}")
        print(f"  Nguong goi y                   : {threshold:.3f} (trung diem hai nhom)")
        overlap = [s for s in sims_ood if s >= threshold]
        missed = [s for s in sims_hit if s < threshold]
        print(f"    - Anh ngoai mien bi nhan nham : {len(overlap)}/{len(sims_ood)}")
        print(f"    - Anh trong kho bi bo sot     : {len(missed)}/{len(sims_hit)}")

    out = {
        "model": "ViT-B-32 / laion2b_s34b_b79k",
        "embedding_dim": 512,
        "top1_accuracy": (top1 / total * 100) if total else None,
        "top3_accuracy": (top3 / total * 100) if total else None,
        "n_in_catalog": total,
        "n_out_of_catalog_cake": len(sims_out),
        "n_out_of_domain": len(sims_ood),
        "n_3d_body": body_total,
        "body_3d_hit_rate": (body_hits / body_total * 100) if body_total else None,
        "body_3d_viewable_rate": (viewable / body_total * 100) if body_total else None,
        # Mẫu số riêng của phép đo lọc 3D: không đồng nhất với `n_3d_body`,
        # vì một lượt không lọc có thể lỗi/rỗng nhưng lượt lọc vẫn đã được thử.
        "filtered_3d_attempts": filtered_total,
        "filtered_3d_all_viewable_rate": (
            (filtered_hits / filtered_total * 100) if filtered_total else None
        ),
        "sim_avg_in": avg(sims_hit),
        "sim_avg_out": avg(sims_out),
        "sim_avg_out_of_domain": avg(sims_ood),
        "details": rows,
        "details_out_of_domain": ood_rows,
        "details_3d_body": body_rows,
    }
    report = TEST_DIR / "accuracy_report.json"
    report.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"  Bao cao chi tiet: {report}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    _configure_stdout()
    raise SystemExit(main())
