#!/usr/bin/env node
/**
 * Chụp ảnh kiểm tra 6 mẫu bánh ở nhiều góc, bằng Chrome headless.
 *
 * Vì sao cần
 * -----------
Test hình học (`test-cake-decorations.cjs`) kiểm tra trang trí có nằm đúng
trên mặt bánh trong dữ liệu vị trí. Nó không kiểm tra bánh có hiện ra không —
một GLB tải lỗi hay camera hướng vào khoảng trống vẫn khiến test đó xanh.
 *
 * Script này chụp ảnh thật rồi đo: vùng giữa khung hình phải có nội dung khác
 * nền. Một canvas trắng, hoặc một cảnh không có bánh, sẽ hợp lệ về mặt kỹ
 * thuật nhưng báo động ở đây.
 *
 * Không thay thế việc người xem nhìn. Ảnh sinh tự động bắt được "trắng" và
 * "không render"; nó không bắt được "trông sai màu" hay "lệch 2mm".
 *
 * Dùng:  node scripts/capture-cake-shots.mjs
 * Ảnh:    tmp_shots/<slug>-<view>.png
 */

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import zlib from 'node:zlib';

const PORT = process.env.STUDIO_URL || 'http://localhost:3001';
const OUT = path.resolve(process.cwd(), 'tmp_shots');

const CHROME_PATHS = [
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
];

const MODELS = ['round-1-tier', 'round-2-tier', 'round-3-tier', 'square-1-tier', 'heart-1-tier', 'tall-1-tier'];
const VIEWS = ['front', 'top', 'side'];

function findChrome() {
  const found = CHROME_PATHS.find(p => fs.existsSync(p));
  if (!found) {
    console.error('Khong tim thay Chrome/Chromium. Bo qua phep chup anh.');
    process.exit(2);
  }
  return found;
}

/** Doc mot PNG 8-bit RGB/RGBA va tra ve pixel thao. */
function decodePng(buffer) {
  if (buffer.readUInt32BE(0) !== 0x89504e47) throw new Error('khong phai PNG');
  let offset = 8;
  let width = 0, height = 0, channels = 3;
  const idat = [];
  while (offset < buffer.length) {
    const length = buffer.readUInt32BE(offset);
    const type = buffer.toString('ascii', offset + 4, offset + 8);
    const data = buffer.subarray(offset + 8, offset + 8 + length);
    if (type === 'IHDR') {
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      const colorType = data[9];
      if (colorType !== 2 && colorType !== 6) throw new Error(`che do mau khong ho tro: ${colorType}`);
      channels = colorType === 6 ? 4 : 3;
    } else if (type === 'IDAT') {
      idat.push(data);
    } else if (type === 'IEND') break;
    offset += 12 + length;
  }
  const raw = zlib.inflateSync(Buffer.concat(idat));
  const stride = width * channels;
  const pixels = Buffer.alloc(height * stride);
  let previous = Buffer.alloc(stride);
  let position = 0;
  for (let y = 0; y < height; y++) {
    const filter = raw[position++];
    const line = raw.subarray(position, position + stride);
    position += stride;
    const current = Buffer.from(line);
    for (let x = 0; x < stride; x++) {
      const a = x >= channels ? current[x - channels] : 0;
      const b = previous[x];
      const c = x >= channels ? previous[x - channels] : 0;
      if (filter === 1) current[x] = (current[x] + a) & 255;
      else if (filter === 2) current[x] = (current[x] + b) & 255;
      else if (filter === 3) current[x] = (current[x] + ((a + b) >> 1)) & 255;
      else if (filter === 4) {
        const p = a + b - c;
        const pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
        current[x] = (current[x] + (pa <= pb && pa <= pc ? a : pb <= pc ? b : c)) & 255;
      }
    }
    current.copy(pixels, y * stride);
    previous = current;
  }
  return { width, height, channels, pixels };
}

/**
 * Do vung giua khung: co bao nhieu mau khac biet nhau, va lech bao nhieu so
 * voi mau nen o goc.
 *
 * Khong so sanh tung pixel voi nen: nen la gradient nen mot anh "co khong gia"
 * van khac nhau rat nhieu. So sanh so luac mau va do lech trung binh moi tach
 * duoc "co banh" khoi "trang".
 */
function analyse(file) {
  const { width, height, channels, pixels } = decodePng(fs.readFileSync(file));
  const at = (x, y) => {
    const i = (y * width + x) * channels;
    return [pixels[i], pixels[i + 1], pixels[i + 2]];
  };

  const corner = at(4, 4);
  const x0 = Math.floor(width * 0.3), x1 = Math.floor(width * 0.7);
  const y0 = Math.floor(height * 0.3), y1 = Math.floor(height * 0.7);

  const distinct = new Set();
  let samples = 0, totalDelta = 0;
  for (let y = y0; y < y1; y += 3) {
    for (let x = x0; x < x1; x += 3) {
      const [r, g, b] = at(x, y);
      distinct.add((r >> 4 << 8) | (g >> 4 << 4) | (b >> 4));
      totalDelta += (Math.abs(r - corner[0]) + Math.abs(g - corner[1]) + Math.abs(b - corner[2])) / 3;
      samples++;
    }
  }
  return {
    colors: distinct.size,
    delta: samples ? totalDelta / samples : 0,
    blank: distinct.size < 12 && totalDelta / Math.max(samples, 1) < 10,
  };
}

function shoot(chrome, url, file, view) {
  // Camera goc khac nhau doi qua tham so cua trang, de khong phai doi code app.
  const separator = url.includes('?') ? '&' : '?';
  const target = `${url}${separator}view=${view}`;
  execFileSync(chrome, [
    '--headless=new',
    '--disable-gpu',
    '--enable-unsafe-swiftshader',
    '--use-gl=swiftshader',
    '--no-sandbox',
    '--hide-scrollbars',
    '--window-size=1200,900',
    '--virtual-time-budget=25000',
    `--screenshot=${file}`,
    `--user-data-dir=${path.join(os.tmpdir(), 'cake-shots-profile')}`,
    target,
  ], { stdio: 'ignore', timeout: 120000 });
}

function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const chrome = findChrome();
  console.log(`Dung trinh duyet: ${chrome}`);
  console.log(` chup vao: ${OUT}\n`);

  let failed = 0, total = 0;
  for (const model of MODELS) {
    for (const view of VIEWS) {
      const file = path.join(OUT, `${model}-${view}.png`);
      try {
        shoot(chrome, `${PORT}/cake-builder?bare=1&model=${model}`, file, view);
      } catch (error) {
        console.log(`FAIL ${model} ${view}: chup that bai (${error.message.slice(0, 60)})`);
        failed++; total++;
        continue;
      }
      const result = analyse(file);
      total++;
      if (result.blank) {
        console.log(`FAIL ${model} ${view}: vung giua khong noi gi - man hinh trang`);
        failed++;
      } else {
        console.log(`PASS ${model} ${view}: ${result.colors} mau, lech nen ${result.delta.toFixed(1)}`);
      }
    }
  }

  console.log(`\n${total - failed}/${total} anh co noi dung.`);
  console.log('Xem thu bang mat: cac anh trong', OUT);
  if (failed) {
    console.log('Anh trang nghia la GLB khong render hoac camera huong sai.');
    process.exitCode = 1;
  }
}

main();