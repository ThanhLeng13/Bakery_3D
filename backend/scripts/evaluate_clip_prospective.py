"""Run frozen-threshold evaluation ONLY after independent query label review.

python scripts/evaluate_clip_prospective.py NEW_MANIFEST.json OUTPUT.json
Does not tune the threshold or modify catalogue/embeddings. Output must not
already exist: keep individual runs, including failures, rather than overwrite.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from validate_clip_prospective import ROOT, validate


def evaluate(items, old_items, root, protocol, service):
    validation = validate(items, old_items, root, protocol)
    threshold = protocol["threshold"]
    totals = {g: {"attempts": 0, "failures": 0, "accepted": 0, "rejected": 0}
              for g in protocol["groups"]}
    rows = []
    for item, checked in zip(items, validation["files"]):
        group = totals[item["group"]]
        group["attempts"] += 1
        row = {**checked, "group": item["group"], "label": item["label"]}
        try:
            raw = (root / checked["file"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != checked["sha256"]:
                raise ValueError("Query changed after validation")
            result = service.search_by_image(raw, match_count=1, match_threshold=0.0)
            hits = result["results"]
            score = hits[0]["similarity"] if hits else None
            accepted = score is not None and score >= threshold
            group["accepted" if accepted else "rejected"] += 1
            row.update(status="accepted" if accepted else "rejected", score=score)
        except Exception as exc:
            # Failures are neither successful rejection nor acceptance.
            group["failures"] += 1
            row.update(status="error", error_type=type(exc).__name__)
        rows.append(row)
    positive = totals["trong_kho"]
    negative = totals["ngoai_mien_banh"]
    return {
        "protocol": protocol["protocol"], "threshold": threshold,
        "model": protocol["model"], "embedding_dim": protocol["embedding_dim"],
        "validation": validation, "groups": totals,
        "in_catalog_acceptance_rate": positive["accepted"] / positive["attempts"],
        "out_of_domain_rejection_rate": negative["rejected"] / negative["attempts"],
        "limitations": "Offline top-1 threshold analysis, not recognition accuracy or deployed rejection. Label review and embedding independence remain external requirements.",
        "queries": rows,
    }


def main():
    if len(sys.argv) != 3:
        print("Usage: evaluate_clip_prospective.py NEW_MANIFEST.json OUTPUT.json")
        return 2
    manifest, output = map(Path, sys.argv[1:])
    if output.exists():
        raise FileExistsError("Keep prior runs; choose a new output path")
    protocol_path = ROOT / "prospective_clip_protocol.json"
    protocol_bytes = protocol_path.read_bytes()
    manifest_bytes = manifest.read_bytes()
    items = json.loads(manifest_bytes)
    old_items = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    protocol = json.loads(protocol_bytes)
    # Fail before loading CLIP or making requests if data is not verified.
    validate(items, old_items, ROOT, protocol)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app.services.clip_service import ClipSearchService

    report = evaluate(items, old_items, ROOT, protocol, ClipSearchService())
    report["protocol_sha256"] = hashlib.sha256(protocol_bytes).hexdigest()
    report["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    # Exclusive creation also prevents a concurrent run overwriting evidence.
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(output)
    return 1 if any(g["failures"] for g in report["groups"].values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
