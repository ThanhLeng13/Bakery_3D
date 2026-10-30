"""Validate new query data BEFORE inference; do not infer labels from filenames.

python scripts/validate_clip_prospective.py path/to/new_manifest.json
Uses the frozen protocol, old manifest, and real image bytes. Does not call
CLIP or write Supabase. Human visual verification must be recorded separately.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent / "test_images"


def source_key(value: str) -> str:
    return unquote(value).replace("_", " ").strip()


def validate(new_items: list[dict], old_items: list[dict], root: Path, protocol: dict) -> dict:
    sources = {source_key(item.get("source", "")) for item in old_items}
    hashes = {hashlib.sha256((root / item["file"].replace("\\", "/")).read_bytes()).hexdigest()
              for item in old_items}
    counts = Counter()
    rows = []
    for item in new_items:
        if item.get("group") not in protocol["groups"]:
            raise ValueError("Unsupported query group")
        if item.get("label_verified") is not True or not item.get("verified_by", "").strip():
            raise ValueError("Human label verification is required before inference")
        if not item.get("label", "").strip():
            raise ValueError("Missing label")
        license_value = item.get("license")
        if not isinstance(license_value, str) or license_value.strip() in ("", "?"):
            raise ValueError("Missing license")
        source = source_key(item.get("source", ""))
        if source in ("", "?") or source in sources:
            raise ValueError("Missing or duplicate source")
        relative = Path(item["file"].replace("\\", "/"))
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Query path must stay inside test_images")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in hashes:
            raise ValueError("Duplicate image bytes")
        sources.add(source)
        hashes.add(digest)
        counts[item["group"]] += 1
        rows.append({"file": relative.as_posix(), "sha256": digest, "source": source})
    if any(counts[group] < protocol["minimum_per_group"] for group in protocol["groups"]):
        raise ValueError("Insufficient verified queries per group")
    return {"counts": dict(counts), "files": rows,
            "warning": "Source/hash separation does not prove semantic or embedding independence"}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_clip_prospective.py NEW_MANIFEST.json")
        return 2
    manifest = Path(sys.argv[1])
    protocol = ROOT / "prospective_clip_protocol.json"
    result = validate(
        json.loads(manifest.read_text(encoding="utf-8")),
        json.loads((ROOT / "manifest.json").read_text(encoding="utf-8")), ROOT,
        json.loads(protocol.read_text(encoding="utf-8")),
    )
    result["protocol_sha256"] = hashlib.sha256(protocol.read_bytes()).hexdigest()
    result["manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
