"""Retrospective, source-isolated threshold evaluation from saved CLIP scores.

No network, database writes, or new CLIP inference. The old dataset has already
been inspected: this is NOT a pristine prospective test. Freeze the split before
collecting new images if an unbiased confirmation is required.

Run from backend: python scripts/evaluate_clip_holdout.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import unquote

TEST_DIR = Path(__file__).resolve().parent.parent / "test_images"
SEED = "bakery-clip-retrospective-v1"
GROUPS = ("trong_kho", "ngoai_mien_banh")


def normalized(value: str) -> str:
    return unquote(value).replace("\\", "/").strip()


def build_split(items: list[dict], root: Path) -> list[dict]:
    """Keep label, source, and byte-identical images on the same side.

    Use connected components because a source can connect two labels, while a
    label connects multiple sources. Splitting either independently leaks.
    Assignment depends on identifiers only, never similarity or correctness.
    """
    selected = [dict(item) for item in items if item["group"] in GROUPS]
    parent = list(range(len(selected)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, item in enumerate(selected):
        item["file"] = normalized(item["file"])
        source = normalized(item.get("source", ""))
        if source in ("", "?"):
            raise ValueError(f"Unverified source: {item['file']}")
        digest = hashlib.sha256((root / item["file"]).read_bytes()).hexdigest()
        item["sha256"] = digest
        item["source"] = source
        tokens = (
            "label:" + item["label"], "source:" + source, "bytes:" + digest,
        )
        for token in tokens:
            if token in seen:
                parent[find(i)] = find(seen[token])
            else:
                seen[token] = i

    components = {}
    for i, item in enumerate(selected):
        components.setdefault(find(i), []).append(item)
    partitions = {}
    for members in components.values():
        signature = "\n".join(sorted(m["sha256"] + ":" + m["file"] for m in members))
        key = hashlib.sha256((SEED + signature).encode()).hexdigest()
        strata = tuple(sorted({m["group"] for m in members}))
        partitions.setdefault(strata, []).append((key, members))
    for buckets in partitions.values():
        buckets.sort(key=lambda pair: pair[0])
        if len(buckets) < 2:
            raise ValueError("Not enough independent components for both partitions")
        cut = len(buckets) // 2
        for i, (key, members) in enumerate(buckets):
            for item in members:
                item["component"] = key
                item["split"] = "calibration" if i < cut else "test"
    return sorted(selected, key=lambda item: item["file"])


def metrics(rows: list[dict], threshold: float) -> dict:
    positive = [r for r in rows if r["group"] == "trong_kho"]
    negative = [r for r in rows if r["group"] == "ngoai_mien_banh"]
    if not positive or not negative:
        raise ValueError("Each partition needs both query classes")
    accepted = sum(r["score"] >= threshold for r in positive)
    rejected = sum(r["score"] < threshold for r in negative)
    return {
        "n_in_catalog": len(positive), "n_out_of_domain": len(negative),
        "accepted_in_catalog": accepted, "rejected_out_of_domain": rejected,
        "in_catalog_acceptance_rate": accepted / len(positive),
        "out_of_domain_rejection_rate": rejected / len(negative),
        "balanced_accuracy": (accepted / len(positive) + rejected / len(negative)) / 2,
    }


def choose_threshold(calibration: list[dict]) -> float:
    """Maximise calibration balanced accuracy; ties use the smaller threshold."""
    scores = sorted({r["score"] for r in calibration})
    if not scores:
        raise ValueError("No calibration scores")
    candidates = [scores[0]] + [
        (a + b) / 2 for a, b in zip(scores, scores[1:])
    ] + [scores[-1] + 1e-9]
    return max(candidates, key=lambda t: (metrics(calibration, t)["balanced_accuracy"], -t))


def evaluate(items: list[dict], report: dict, root: Path) -> dict:
    split = build_split(items, root)
    scores = {}
    for row in report["details"] + report["details_out_of_domain"]:
        key = normalized(row["file"])
        if key in scores:
            raise ValueError(f"Duplicate score: {key}")
        scores[key] = row["sim1"]
    for row in split:
        if row["file"] not in scores:
            raise ValueError(f"Missing query score (do not silently drop failures): {row['file']}")
        row["score"] = scores[row["file"]]
    calibration = [r for r in split if r["split"] == "calibration"]
    test = [r for r in split if r["split"] == "test"]
    threshold = choose_threshold(calibration)
    return {
        "protocol": SEED,
        "retrospective": True,
        "limitations": [
            "Existing query set already inspected; not a pristine prospective test.",
            "Threshold is offline analysis, not deployed rejection behaviour.",
            "Uses saved top-1 similarity, not classification confidence.",
            "Small sample; no claim of production readiness or generalisation.",
        ],
        "threshold_selection": "max calibration balanced accuracy; ties: lower threshold",
        "threshold": threshold,
        "calibration": metrics(calibration, threshold),
        "test": metrics(test, threshold),
        "queries": split,
    }


def main() -> int:
    manifest_path = TEST_DIR / "manifest.json"
    report_path = TEST_DIR / "accuracy_report.json"
    result = evaluate(
        json.loads(manifest_path.read_text(encoding="utf-8")),
        json.loads(report_path.read_text(encoding="utf-8")), TEST_DIR,
    )
    result["input_sha256"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (manifest_path, report_path)
    }
    path = TEST_DIR / "threshold_holdout_report.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("RETROSPECTIVE ONLY - not an unseen prospective test")
    print(f"threshold={result['threshold']:.6f}")
    for side in ("calibration", "test"):
        print(side, result[side])
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
