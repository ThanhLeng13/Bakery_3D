"""Kiem tra anh render 3D co that su co noi dung hay khong.

Dung thu vien chuan: khong them dependency. Doc PNG 8-bit RGB/RGBA, dem so mau
khac biet trong vung giua va so lech voi mau nen o goc. Anh trang thi ca hai
chi so deu nho.
"""
import struct
import sys
import zlib
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SHOT_DIR = Path(r"D:\DE_TAI\Bakery_3D\frontend\tmp_shots")


def decode_png(path: Path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("khong phai PNG")
    offset = 8
    width = height = 0
    channels = 3
    idat = []
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        ctype = data[offset + 4:offset + 8].decode("ascii")
        chunk = data[offset + 8:offset + 8 + length]
        if ctype == "IHDR":
            width = struct.unpack(">I", chunk[0:4])[0]
            height = struct.unpack(">I", chunk[4:8])[0]
            color_type = chunk[9]
            channels = 4 if color_type == 6 else 3
        elif ctype == "IDAT":
            idat.append(chunk)
        elif ctype == "IEND":
            break
        offset += 12 + length
    raw = zlib.decompress(b"".join(idat))
    stride = width * channels
    pixels = bytearray(height * stride)
    prev = bytearray(stride)
    pos = 0
    for y in range(height):
        filt = raw[pos]
        pos += 1
        line = raw[pos:pos + stride]
        pos += stride
        cur = bytearray(line)
        for x in range(stride):
            a = cur[x - channels] if x >= channels else 0
            b = prev[x]
            c = prev[x - channels] if x >= channels else 0
            if filt == 1:
                cur[x] = (cur[x] + a) & 255
            elif filt == 2:
                cur[x] = (cur[x] + b) & 255
            elif filt == 3:
                cur[x] = (cur[x] + ((a + b) >> 1)) & 255
            elif filt == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur[x] = (cur[x] + pred) & 255
        pixels[y * stride:(y + 1) * stride] = cur
        prev = cur
    return width, height, channels, bytes(pixels)


def analyse(path: Path):
    width, height, channels, pixels = decode_png(path)

    def at(x, y):
        i = (y * width + x) * channels
        return pixels[i], pixels[i + 1], pixels[i + 2]

    corner = at(4, 4)
    x0, x1 = int(width * 0.3), int(width * 0.7)
    y0, y1 = int(height * 0.3), int(height * 0.7)
    distinct = set()
    total = 0
    n = 0
    for y in range(y0, y1, 3):
        for x in range(x0, x1, 3):
            r, g, b = at(x, y)
            distinct.add((r >> 4 << 8) | (g >> 4 << 4) | (b >> 4))
            total += (abs(r - corner[0]) + abs(g - corner[1]) + abs(b - corner[2])) / 3
            n += 1
    delta = total / max(n, 1)
    return {
        "size": (width, height),
        "colors": len(distinct),
        "delta": round(delta, 1),
        "blank": len(distinct) < 12 and delta < 10,
    }


def main():
    files = sorted(SHOT_DIR.glob("*.png"))
    print(f"  thu muc: {SHOT_DIR}")
    print(f"  so anh: {len(files)}\n")
    ok = 0
    by_model = {}
    for f in files:
        try:
            r = analyse(f)
        except Exception as e:
            print(f"  LOI  {f.name}: {type(e).__name__}: {e}")
            continue
        model = f.stem.rsplit("-", 1)[0]
        by_model.setdefault(model, []).append((f.name, r))
        if r["blank"]:
            print(f"  TRANG {f.name}  {r['size'][0]}x{r['size'][1]}  colors={r['colors']} delta={r['delta']}")
        else:
            ok += 1
    print(f"\n  {ok}/{len(files)} anh co noi dung (khong trang).\n")
    print("  theo kieu than:")
    for model, items in sorted(by_model.items()):
        good = sum(1 for _, r in items if not r["blank"])
        avg_colors = sum(r["colors"] for _, r in items) / len(items)
        avg_delta = sum(r["delta"] for _, r in items) / len(items)
        print(f"    {model:16s} {good}/{len(items)} anh   mau trung binh={avg_colors:.0f}  lech nen={avg_delta:.1f}")


if __name__ == "__main__":
    main()
