"""Collect unverified new Commons candidates; NEVER run CLIP or approve labels.

Each saved record remains label_verified=false until real visual review.
Do not interpret a successful download as a correct class label.
"""
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import unquote

from PIL import Image
from collect_test_images import OUT_DIR, _fetch, search_commons

QUERIES = [
    ("trong_kho", "Bánh Brownie", "chocolate brownie dessert"),
    ("trong_kho", "Bánh tart trứng", "Portuguese egg tart"),
    ("trong_kho", "Bánh su kem", "cream puff choux pastry"),
    ("trong_kho", "Bánh tiramisu truyền thống", "tiramisu slice dessert"),
    ("trong_kho", "Bánh phô mai cháy", "Basque burnt cheesecake"),
    ("trong_kho", "Cheesecake Red Velvet", "red velvet cheesecake"),
    ("trong_kho", "Bánh crepe sầu riêng", "durian crepe cake"),
    ("trong_kho", "Bánh chuối nướng nước dừa", "Vietnamese banana cake"),
    ("trong_kho", "Bánh kem trứng dừa nướng", "coconut custard cake"),
    ("trong_kho", "Bánh Brownie", "brownie chocolate squares"),
    ("ngoai_mien_banh", "bicycle", "bicycle parked"),
    ("ngoai_mien_banh", "cat", "domestic cat sitting"),
    ("ngoai_mien_banh", "dog", "dog standing"),
    ("ngoai_mien_banh", "chair", "wooden chair furniture"),
    ("ngoai_mien_banh", "tree", "oak tree"),
    ("ngoai_mien_banh", "apple", "red apple fruit"),
    ("ngoai_mien_banh", "orange", "orange fruit whole"),
    ("ngoai_mien_banh", "shoe", "leather shoe"),
    ("ngoai_mien_banh", "watch", "wristwatch"),
    ("ngoai_mien_banh", "car", "parked automobile"),
]


def main():
    dest = OUT_DIR / "prospective_candidates"
    dest.mkdir(exist_ok=True)
    manifest = dest / "manifest_candidates.json"
    old = json.loads((OUT_DIR / "manifest.json").read_text(encoding="utf-8"))
    saved = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else []
    sources = {unquote(m["source"]) for m in old + saved}
    hashes = {hashlib.sha256((OUT_DIR / m["file"].replace("\\", "/")).read_bytes()).hexdigest()
              for m in old + saved}
    for i, (group, label, term) in enumerate(QUERIES):
        key = f"candidate_{i:02d}.jpg"
        if any(Path(m["file"]).name == key for m in saved):
            continue
        try:
            found = search_commons(term, limit=8)
            for candidate in found:
                if unquote(candidate["page"]) in sources or candidate["license"] in ("?", ""):
                    continue
                path = dest / key
                try:
                    raw = _fetch(candidate["url"], timeout=30)
                    digest = hashlib.sha256(raw).hexdigest()
                    if digest in hashes:
                        continue
                    path.write_bytes(raw)
                    with Image.open(path) as image:
                        image.verify()
                except Exception as exc:
                    # This candidate failed, not the whole search query.
                    # Only remove the exact candidate path inside our output dir.
                    if path.resolve().parent != dest.resolve():
                        raise ValueError("Unexpected candidate cleanup path") from exc
                    path.unlink(missing_ok=True)
                    print(f"SKIP {i}: {type(exc).__name__}: {str(exc)[:120]}", flush=True)
                    continue
                saved.append({
                    "group": group, "label": label, "search_term": term,
                    "file": path.relative_to(OUT_DIR).as_posix(),
                    "source": candidate["page"], "download_url": candidate["url"],
                    "license": candidate["license"], "artist": candidate["artist"],
                    "source_title": candidate["title"], "sha256": digest,
                    "label_verified": False, "verified_by": "",
                    "review_note": "Candidate only; verify content, catalogue label, and embedding independence before inference",
                })
                sources.add(unquote(candidate["page"]))
                hashes.add(digest)
                manifest.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"SAVED {i}: {label} / {candidate['title']}", flush=True)
                break
        except Exception as exc:
            print(f"FAILED {i}: {type(exc).__name__}: {str(exc)[:120]}", flush=True)
        time.sleep(1)
    print(f"TOTAL {len(saved)} unverified candidates", flush=True)


if __name__ == "__main__":
    main()
