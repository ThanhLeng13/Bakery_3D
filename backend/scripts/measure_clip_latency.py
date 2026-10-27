"""Đo độ trễ CLIP: cold/warm, p50/p95, và tách riêng từng bước.

ĐO TRÊN MÁY THẬT (CPU), không ước lượng:
  - COLD: lần đầu tiến trình nạp model (nạp trọn ~45s + ~350 MB RAM)
  - WARM: các lần sau, model đã nằm trong RAM
  - p50/p95: phân vị của thời gian sinh vector (embed) và của thời gian
    tìm trong kho (search, gồm cả gọi RPC `match_cakes`)

CÁCH DÙNG
    python scripts/measure_clip_latency.py
"""

from __future__ import annotations

import io
import json
import statistics
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.services import clip_service  # noqa: E402
from app.services.clip_service import ClipSearchService, embed_image_bytes  # noqa: E402

TEST_DIR = Path(__file__).resolve().parent.parent / "test_images"


def pct(values: list[float], p: float) -> float:
    """Phân vị p (0..1) theo cách gần nhất."""
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((len(s) - 1) * p))))
    return s[k]


def main() -> int:
    print("=" * 74)
    print("DO DO TRI CLIP — MAY CPU")
    print("=" * 74)

    # Ảnh test: dùng ảnh trong kho (đã có sẵn trên đĩa).
    images = sorted((TEST_DIR / "trong_kho").glob("*.jpg"))
    if not images:
        print("  Khong co anh test. Chay collect_test_images.py truoc.")
        return 1
    print(f"  So anh dung de do: {len(images)}")
    print()

    # ── COLD: lần đầu nạp model ─────────────────────────────────────────────
    print("  ĐO COLD (nap model lan dau)...")
    t0 = time.perf_counter()
    clip_service._model = None       # ép nạp lại
    clip_service._preprocess = None
    vector = embed_image_bytes(images[0].read_bytes())
    cold_s = time.perf_counter() - t0
    print(f"    cold total      : {cold_s:.2f} s")
    print()

    # ── WARM: sinh vector cho từng ảnh ───────────────────────────────────────
    print("  ĐO WARM (sinh vector)...")
    embed_ms: list[float] = []
    for img in images:
        raw = img.read_bytes()
        t = time.perf_counter()
        embed_image_bytes(raw)
        embed_ms.append((time.perf_counter() - t) * 1000)
    print(f"    so anh          : {len(embed_ms)}")
    print(f"    p50             : {pct(embed_ms, 0.50):.0f} ms")
    print(f"    p95             : {pct(embed_ms, 0.95):.0f} ms")
    print(f"    trung binh      : {statistics.mean(embed_ms):.0f} ms")
    print(f"    nhanh nhat      : {min(embed_ms):.0f} ms")
    print(f"    cham nhat       : {max(embed_ms):.0f} ms")
    print()

    # ── SEARCH: gọi RPC match_cakes ─────────────────────────────────────────
    print("  ĐO SEARCH (goi RPC match_cakes)...")
    service = ClipSearchService()
    search_ms: list[float] = []
    for img in images:
        raw = img.read_bytes()
        t = time.perf_counter()
        service.search_by_image(raw, match_count=6, product_type="cake")
        search_ms.append((time.perf_counter() - t) * 1000)
    print(f"    so lan          : {len(search_ms)}")
    print(f"    p50             : {pct(search_ms, 0.50):.0f} ms")
    print(f"    p95             : {pct(search_ms, 0.95):.0f} ms")
    print(f"    trung binh      : {statistics.mean(search_ms):.0f} ms")
    print(f"    nhanh nhat      : {min(search_ms):.0f} ms")
    print(f"    cham nhat       : {max(search_ms):.0f} ms")
    print()

    # ── END-TO-END: tổng thời gian khách chờ ─────────────────────────────────
    print("  ĐO END-TO-END (embed + search, model da nap)...")
    e2e_ms: list[float] = []
    for img in images:
        raw = img.read_bytes()
        t = time.perf_counter()
        service.search_by_image(raw, match_count=6, product_type="cake")
        e2e_ms.append((time.perf_counter() - t) * 1000)
    print(f"    p50             : {pct(e2e_ms, 0.50):.0f} ms")
    print(f"    p95             : {pct(e2e_ms, 0.95):.0f} ms")
    print(f"    trung binh      : {statistics.mean(e2e_ms):.0f} ms")
    print()

    out = {
        "model": "ViT-B-32 / laion2b_s34b_b79k",
        "embedding_dim": 512,
        "device": "cpu",
        "n_images": len(images),
        "cold_seconds": round(cold_s, 2),
        "embed_ms": {
            "p50": round(pct(embed_ms, 0.50), 1),
            "p95": round(pct(embed_ms, 0.95), 1),
            "mean": round(statistics.mean(embed_ms), 1),
            "min": round(min(embed_ms), 1),
            "max": round(max(embed_ms), 1),
        },
        "search_ms": {
            "p50": round(pct(search_ms, 0.50), 1),
            "p95": round(pct(search_ms, 0.95), 1),
            "mean": round(statistics.mean(search_ms), 1),
            "min": round(min(search_ms), 1),
            "max": round(max(search_ms), 1),
        },
        "end_to_end_ms": {
            "p50": round(pct(e2e_ms, 0.50), 1),
            "p95": round(pct(e2e_ms, 0.95), 1),
            "mean": round(statistics.mean(e2e_ms), 1),
        },
        "how_to_reproduce": (
            "cd backend && python scripts/measure_clip_latency.py "
            "(cần ảnh trong backend/test_images/trong_kho/)"
        ),
    }
    report = TEST_DIR / "latency_report.json"
    report.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Bao cao: {report}")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
