"""Thu thập ảnh bánh NGOÀI kho để đo độ chính xác CLIP.

VÌ SAO CẦN
    Con số "100%" hiện tại là self-match: lấy ảnh trong kho rồi tìm lại chính nó.
    Đó là trường hợp tầm thường, không nói lên điều gì về việc khách chụp ảnh
    ngoài đời rồi tìm. Script này lấy ảnh THẬT từ Wikimedia Commons — khác nguồn,
    khác góc chụp, khác ánh sáng — để có con số bảo vệ được.

CÁCH DÙNG
    python scripts/collect_test_images.py

Ảnh lưu vào backend/test_images/<nhom>/<ten>.jpg kèm file manifest.json ghi lại
nguồn gốc và giấy phép, để trích dẫn được trong luận văn.
"""

from __future__ import annotations

import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

OUT_DIR = Path(__file__).resolve().parent.parent / "test_images"
UA = "BakeryThesis/1.0 (university research; contact: student)"

# Wikimedia giới hạn tần suất khá gắt. Đã gặp HTTP 429 sau 4 món, nên mọi lời
# gọi mạng đều phải thử lại với backoff — nếu không, script chết giữa chừng và
# bộ ảnh test bị thiếu, dẫn tới số liệu accuracy sai lệch mà không ai biết.
_MAX_RETRIES = 4
_BASE_DELAY = 3.0
# Nghỉ giữa các món để không dồn dập vào API.
_DELAY_BETWEEN_ITEMS = 2.0

# Nhóm 1: món CÓ trong kho — để đo top-1/top-3 accuracy.
# Tên khoá là tên sản phẩm trong DB, giá trị là từ khoá tìm ảnh.
IN_CATALOG = {
    "Bánh tiramisu truyền thống": "tiramisu dessert",
    "Bánh Brownie": "chocolate brownie",
    "Cheesecake Red Velvet": "red velvet cake",
    "Bánh phô mai cháy": "basque burnt cheesecake",
    "Bánh tart trứng": "egg tart custard",
    "Bánh su kem": "cream puff choux",
    "Bánh mousse chanh dây": "passion fruit mousse cake",
    "Bánh kem trứng dừa nướng": "coconut custard cake",
    "Bánh chuối nướng nước dừa": "banana cake",
    "Bánh crepe sầu riêng": "crepe cake",
}

# Nhóm 2: món KHÔNG có trong kho — để đo khả năng từ chối / không match bừa.
# Hệ thống tốt phải trả similarity thấp, chứ không được tự tin gán vào bánh nào đó.
OUT_CATALOG = {
    "pizza": "pizza margherita",
    "hamburger": "hamburger",
    "sushi": "sushi plate",
    "banh mi": "banh mi vietnamese sandwich",
    "pho": "pho noodle soup",
    "salad": "green salad bowl",
    "cafe": "espresso coffee cup",
    "oto": "automobile car",
}

# Lọc kết quả rác: Wikimedia hay trả về tên file không liên quan
# (ví dụ tìm "brownie" ra máy ảnh Kodak Brownie).
BAD_WORDS = [
    "kodak", "camera", "box", "logo", "map", "diagram", "chart",
    "stamp", "coin", "poster", "screenshot", "sign", "building",
    "car", "train", "aircraft", "portrait", "monument",
]


def _fetch(url: str, timeout: int = 30) -> bytes:
    """Tải URL, thử lại khi bị giới hạn tần suất hoặc lỗi mạng tạm thời."""
    last: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            last = exc
            # 429 = quá nhiều request, 5xx = lỗi tạm thời phía server.
            # Các mã khác (404, 403…) thì thử lại cũng vô ích.
            if exc.code not in (429, 500, 502, 503, 504):
                raise
        except Exception as exc:
            last = exc
        delay = _BASE_DELAY * (2 ** attempt)
        print(f"      thu lai sau {delay:.0f}s ({type(last).__name__})")
        time.sleep(delay)
    raise last if last else RuntimeError("khong tai duoc")


def search_commons(term: str, limit: int = 12) -> list[dict]:
    """Tìm ảnh trên Wikimedia Commons."""
    query = urllib.parse.urlencode({
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {term}",
        "gsrlimit": limit,
        "gsrnamespace": 6,
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiurlwidth": 800,
    })
    url = "https://commons.wikimedia.org/w/api.php?" + query
    data = json.loads(_fetch(url))

    results = []
    for page in (data.get("query", {}).get("pages", {}) or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        thumb = info.get("thumburl")
        if not thumb:
            continue
        title = page.get("title", "")
        if any(bad in title.lower() for bad in BAD_WORDS):
            continue
        meta = info.get("extmetadata", {}) or {}
        results.append({
            "title": title,
            "url": thumb,
            "width": info.get("width"),
            "height": info.get("height"),
            "license": (meta.get("LicenseShortName", {}) or {}).get("value", "?"),
            "artist": (meta.get("Artist", {}) or {}).get("value", "?")[:120],
            "page": f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(title)}",
        })
    return results


def download(url: str, dest: Path) -> tuple[bool, int]:
    """Tải ảnh, trả (thành công, số byte)."""
    try:
        raw = _fetch(url, timeout=60)
    except Exception as exc:
        print(f"      loi tai: {type(exc).__name__}")
        return False, 0
    # Xác nhận đúng là ảnh, không phải trang HTML lỗi.
    if len(raw) < 2048:
        return False, len(raw)
    dest.write_bytes(raw)
    return True, len(raw)


def collect(group: str, mapping: dict[str, str], per_item: int = 2) -> list[dict]:
    manifest = []
    for label, term in mapping.items():
        safe = label.replace(" ", "_").replace("/", "-")
        existing = sorted((OUT_DIR / group).glob(f"{safe}__*.jpg"))
        if len(existing) >= per_item:
            # Đã có đủ ảnh từ lần chạy trước: ghi lại manifest mà không gọi mạng.
            print(f"  [{group}] {label}  (da co {len(existing)} anh, bo qua)")
            for path in existing[:per_item]:
                manifest.append({
                    "group": group, "label": label, "search_term": term,
                    "file": str(path.relative_to(OUT_DIR)),
                    "bytes": path.stat().st_size,
                    "source": "(xem manifest.json lan chay truoc)",
                    "license": "?", "artist": "?", "original_size": "?",
                })
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
        saved = 0
        for item in found:
            if saved >= per_item:
                break
            dest = OUT_DIR / group / f"{safe}__{saved + 1}.jpg"
            dest.parent.mkdir(parents=True, exist_ok=True)
            ok, nbytes = download(item["url"], dest)
            if not ok:
                continue
            saved += 1
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
        if saved == 0:
            print("      khong tai duoc anh nao")
        time.sleep(_DELAY_BETWEEN_ITEMS)
    return manifest


def main() -> int:
    print("=" * 74)
    print("THU THAP ANH TEST NGOAI KHO (Wikimedia Commons)")
    print("=" * 74)
    print()

    manifest: list[dict] = []
    manifest += collect("trong_kho", IN_CATALOG, per_item=2)
    print()
    manifest += collect("ngoai_kho", OUT_CATALOG, per_item=1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print()
    print("=" * 74)
    print(f"  Tong so anh : {len(manifest)}")
    print(f"  Thu muc     : {OUT_DIR}")
    print("  Manifest    : manifest.json (co nguon + giay phep de trich dan)")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
