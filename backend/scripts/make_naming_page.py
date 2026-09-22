"""Tạo trang HTML để bạn xem ảnh và đặt tên trực tiếp.

VÌ SAO CẦN
    Bảng CSV chỉ có tên file dạng số, bạn không biết dòng nào là ảnh nào. Trang
    HTML này hiện ảnh thật cạnh ô nhập tên, nên bạn nhìn thấy bánh rồi gõ tên.

CÁCH DÙNG
    1. Chạy:  python scripts/make_naming_page.py
    2. Mở file backend/naming_page.html bằng Chrome
    3. Gõ tên cho từng ảnh (ảnh nào không dùng thì bỏ trống)
    4. Bấm nút "Tải CSV" ở cuối trang -> lưu đè vào backend/naming_sheet.csv
    5. Chạy:  python scripts/apply_names.py --sheet backend/naming_sheet.csv

    Trang này lưu tên vào bộ nhớ trình duyệt, nên lỡ đóng tab vẫn còn.
"""

from __future__ import annotations

import base64
import csv
import html
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
IMAGE_ROOT = ROOT.parent / "image_bake"
OUT_HTML = ROOT / "naming_page.html"

# Ảnh nhúng thẳng vào HTML dạng base64 để mở file là xem được ngay, không cần
# chạy web server. Đổi lại file HTML sẽ nặng (~6 MB cho 101 ảnh).
THUMB_MAX = 300


def thumb_b64(path: Path) -> str:
    from PIL import Image
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((THUMB_MAX, THUMB_MAX))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=72)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> int:
    if not IMAGE_ROOT.exists():
        print(f"LOI: Khong tim thay thu muc anh: {IMAGE_ROOT}")
        return 1

    items = []
    for folder in sorted(d for d in IMAGE_ROOT.iterdir() if d.is_dir()):
        files = sorted(
            f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
        )
        for f in files:
            items.append((folder.name, f))

    print(f"  Dang tao trang cho {len(items)} anh...")

    cards = []
    for idx, (folder, path) in enumerate(items):
        try:
            b64 = thumb_b64(path)
        except Exception as exc:
            print(f"    ! bo qua {path.name}: {type(exc).__name__}")
            continue
        safe_folder = html.escape(folder)
        safe_file = html.escape(path.name)
        cards.append(f"""
    <div class="card" data-folder="{safe_folder}" data-file="{safe_file}">
      <div class="num">{idx + 1}</div>
      <img src="data:image/jpeg;base64,{b64}" loading="lazy" alt="">
      <div class="meta">{safe_folder}</div>
      <input type="text" placeholder="Tên bánh..." data-role="name">
      <input type="text" class="price" placeholder="Giá (tùy chọn)" data-role="price">
    </div>""")

    doc = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>Đặt tên bánh — Bơ Nơ</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px;
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    background: #FAF8F5; color: #1F1B1A;
  }}
  header {{
    position: sticky; top: 0; z-index: 10;
    background: #FAF8F5; border-bottom: 1px solid #E8E3DC;
    padding: 16px 0 16px; margin: -24px -24px 24px; padding-left: 24px; padding-right: 24px;
  }}
  h1 {{ font-size: 22px; margin: 0 0 6px; }}
  .hint {{ color: #6B6560; font-size: 14px; margin: 0 0 12px; line-height: 1.6; }}
  .bar {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
  button {{
    padding: 10px 20px; border-radius: 10px; border: 0; cursor: pointer;
    background: #1F1B1A; color: #fff; font-size: 14px; font-weight: 600;
  }}
  button.ghost {{ background: #fff; color: #1F1B1A; border: 1px solid #E8E3DC; }}
  #count {{ font-size: 14px; color: #6B6560; }}
  .grid {{
    display: grid; gap: 18px;
    grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  }}
  .card {{
    background: #fff; border: 1px solid #E8E3DC; border-radius: 14px;
    padding: 12px; position: relative;
  }}
  .card.done {{ border-color: #1F1B1A; background: #fff; }}
  .num {{
    position: absolute; top: 18px; left: 18px; z-index: 2;
    background: rgba(31,27,26,.82); color: #fff; font-size: 12px; font-weight: 700;
    padding: 3px 9px; border-radius: 999px;
  }}
  .card img {{
    width: 100%; aspect-ratio: 3/4; object-fit: cover;
    border-radius: 9px; background: #F3EFE9; display: block;
  }}
  .meta {{ font-size: 11px; color: #6B6560; margin: 8px 0 6px; letter-spacing: .02em; }}
  input[type=text] {{
    width: 100%; padding: 9px 11px; border-radius: 9px;
    border: 1px solid #E8E3DC; font-size: 14px; font-family: inherit;
    background: #FAF8F5;
  }}
  input[type=text]:focus {{ outline: 2px solid #1F1B1A; outline-offset: 1px; background: #fff; }}
  input.price {{ margin-top: 6px; font-size: 13px; }}
  .card.done input[type=text][data-role=name] {{ border-color: #1F1B1A; background: #fff; }}
</style>
</head>
<body>
<header>
  <h1>Đặt tên cho {len(items)} ảnh bánh</h1>
  <p class="hint">
    Gõ tên bánh vào ô dưới mỗi ảnh. <strong>Ảnh nào không dùng thì để trống</strong> — sẽ bị bỏ qua.<br>
    Đặt tên theo đặc điểm <em>nhìn thấy được</em> (hoa, màu, số tầng, hình dạng) vì khách tìm bằng ảnh.<br>
    Ví dụ: <em>Bánh kem hoa tươi pastel</em> · <em>Bánh kem hoa hồng đen</em> · <em>Bánh mousse chanh dây</em>
  </p>
  <div class="bar">
    <button onclick="download()">⬇ Tải CSV</button>
    <button class="ghost" onclick="clearAll()">Xóa hết</button>
    <span id="count">0 / {len(items)} đã đặt tên</span>
  </div>
</header>
<div class="grid">{''.join(cards)}</div>

<script>
const KEY = 'bonobakery_naming_v1';
const cards = [...document.querySelectorAll('.card')];

// Khôi phục tên đã gõ (lỡ đóng tab vẫn còn)
let saved = {{}};
try {{ saved = JSON.parse(localStorage.getItem(KEY) || '{{}}'); }} catch (e) {{}}

cards.forEach(c => {{
  const id = c.dataset.folder + '/' + c.dataset.file;
  if (saved[id]) {{
    c.querySelector('[data-role=name]').value = saved[id].name || '';
    c.querySelector('[data-role=price]').value = saved[id].price || '';
  }}
}});

function persist() {{
  const out = {{}};
  cards.forEach(c => {{
    const id = c.dataset.folder + '/' + c.dataset.file;
    const name = c.querySelector('[data-role=name]').value.trim();
    const price = c.querySelector('[data-role=price]').value.trim();
    if (name || price) out[id] = {{ name, price }};
  }});
  localStorage.setItem(KEY, JSON.stringify(out));
  return out;
}}

function refresh() {{
  let n = 0;
  cards.forEach(c => {{
    const v = c.querySelector('[data-role=name]').value.trim();
    c.classList.toggle('done', !!v);
    if (v) n++;
  }});
  document.getElementById('count').textContent = n + ' / {len(items)} đã đặt tên';
}}

cards.forEach(c => {{
  c.querySelectorAll('input').forEach(i => {{
    i.addEventListener('input', () => {{ persist(); refresh(); }});
  }});
}});
refresh();

function clearAll() {{
  if (!confirm('Xóa hết tên đã gõ?')) return;
  localStorage.removeItem(KEY);
  location.reload();
}}

function download() {{
  const data = persist();
  const rows = [['thu_muc', 'file', 'ten_banh', 'gia']];
  cards.forEach(c => {{
    const id = c.dataset.folder + '/' + c.dataset.file;
    rows.push([c.dataset.folder, c.dataset.file,
               (data[id] && data[id].name) || '',
               (data[id] && data[id].price) || '']);
  }});
  // BOM để Excel đọc đúng tiếng Việt
  const csv = '\\ufeff' + rows.map(r =>
    r.map(x => '"' + String(x).replace(/"/g, '""') + '"').join(',')
  ).join('\\r\\n');

  const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'naming_sheet.csv';
  a.click();
}}
</script>
</body>
</html>"""

    OUT_HTML.write_text(doc, encoding="utf-8")
    size_mb = OUT_HTML.stat().st_size / 1024 / 1024
    print("=" * 74)
    print("DA TAO TRANG DAT TEN")
    print("=" * 74)
    print(f"  File : {OUT_HTML}")
    print(f"  Size : {size_mb:.1f} MB ({len(cards)} anh)")
    print()
    print("  BƯỚC TIẾP THEO")
    print("  1. Mo file HTML bang Chrome (nhan doi vao file)")
    print("  2. Go ten cho tung anh")
    print("  3. Bam 'Tai CSV' -> luu de vao backend/naming_sheet.csv")
    print("  4. Chay:  python scripts/apply_names.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
