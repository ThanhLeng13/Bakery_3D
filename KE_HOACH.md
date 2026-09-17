# KẾ HOẠCH XÂY DỰNG — BƠ NƠ BAKERY 3D

> **Tài liệu này viết cho cả người và AI agent.** Nếu bạn là AI được giao tiếp tục dự án này,
> đọc hết mục 1–3 trước khi viết bất kỳ dòng code nào. Mục 4 là kế hoạch thi công.

**Mã đề tài:** Xây dựng website bán bánh kem có tích hợp mô hình 3D và AI hai lớp
**Thời gian:** 15/09 → 01/12 (11 tuần)
**Trạng thái cập nhật:** Giai đoạn 0 — đang thực hiện

---

## 1. ĐỀ TÀI YÊU CẦU GÌ

Đề tài có **3 trụ cột kỹ thuật**, không phải một website bán hàng thông thường:

| # | Trụ cột | Mô tả |
|---|---------|-------|
| 1 | **Mô hình 3D** | Khách xem sản phẩm trực quan trên trình duyệt |
| 2 | **AI lớp 1 — CLIP** | Khách tải ảnh bánh yêu thích → hệ thống dùng mô hình thị giác CLIP tìm mẫu 3D gần giống nhất trong kho |
| 3 | **AI lớp 2 — Agent** | Trợ lý đặt hàng có khả năng tự tìm mẫu, tính giá, kiểm tra thời gian làm bánh, tạo đơn nháp qua hội thoại tự nhiên |

**Từ khóa bắt buộc có trong báo cáo:** CLIP, vector embedding, image similarity search,
function calling / tool use, agent loop, draft order.

---

## 2. HIỆN TRẠNG (đã kiểm tra bằng truy vấn database thật)

### 2.1 Đối chiếu đề tài

| Trụ cột | Trạng thái | Bằng chứng |
|---------|-----------|------------|
| **1. 3D** | ⚠️ Một phần | `Cake3D.tsx` (27KB) dựng hình bằng `cylinderGeometry`/`torusGeometry`. **Không có file `.glb` nào** trong `public/` → chưa có "kho mẫu 3D" |
| **2. CLIP** | ❌ Chưa có | Grep `clip\|embedding\|pgvector` trong `backend/app` → chỉ khớp `clipRule` của SVG. RPC `match_cakes`/`match_products`/`match_documents` đều trả HTTP 404 |
| **3. Agent** | ❌ Chưa có | Grep `tool_call\|tools=\|function_call` trong `backend/app` → **0 kết quả**. Hiện là chatbot + trích JSON bằng **regex** (`extract_recommendations`, `extract_ai_summary` trong `chat_service.py`) |

> **Điểm lệch quan trọng nhất:** hiện tại là *chatbot*, chưa phải *agent*.
> Chatbot: gửi prompt → nhận text → regex bóc JSON. Rất dễ vỡ khi LLM đổi format.
> Agent: LLM gọi tool → nhận kết quả → gọi tiếp → trả lời. Đây là yêu cầu của đề tài.

### 2.2 Hạ tầng đã có sẵn (tận dụng, không làm lại)

**Stack:** Next.js 14.2 (App Router) · React 18 · TypeScript · Tailwind 3.4 · FastAPI · Supabase (Postgres + Auth + Storage) · Groq (Llama 3.3 70B)

**Đã cài trong `frontend/package.json`:** `three@0.184`, `@react-three/fiber@8.18`, `@react-three/drei@9.121`

**Database thật — 22 bảng:**

| Bảng | Số dòng | Dùng cho |
|------|---------|----------|
| `products` | 22 | Catalog. Cột: `id, name, description, category, base_price, sizes, flavors, is_active, product_type` |
| `product_images` | có | **Ảnh thật trên Supabase Storage → nguyên liệu để sinh CLIP embedding** |
| `orders` | 9 | Đơn hàng |
| `users` | 11 | Vai trò **trước migration** `add_staff_role.sql`: `customer` / `baker` / `admin`. **Sau migration**: thêm `staff` |
| `purchases` | 10 | Bán tại quầy |
| `loyalty_points` / `loyalty_transactions` | 8 tx | Tích điểm |
| `cake_options` | 5 size | `price_modifier`: 4inch=0, 6inch=+100k, 8inch=+200k, 10inch=+350k, 2tầng=+500k → **agent tính giá được** |
| `cake_customizations` | có | `customization_json` + `preview_image_url` → **nền tảng cho kho mẫu 3D** |
| `reviews` | 3 | Đánh giá |
| `chat_sessions` / `chat_messages` | có | `customer_id, message_count` / `session_id, role, content` |

**Lỗ hổng hạ tầng AI:** không có cột `vector`, không bật extension `pgvector`, không có RPC `match_*`.

**Lỗ hổng schema:** bảng `vouchers` **KHÔNG tồn tại** (dù `backend/migrations/add_loyalty_system.sql` có định nghĩa). Hai hàm `increment_loyalty_points` và `rpc_redeem_points` cũng **thiếu** (HTTP 404). → Trang `/loyalty` sẽ lỗi khi bấm "Đổi điểm".

### 2.3 Kết nối Supabase từ môi trường dev

> ⚠️ **Quan trọng cho AI agent tiếp theo:** `curl.exe` và PowerShell **KHÔNG ra được Internet**
> trong sandbox này (luôn trả `HTTP 000`). **Chỉ Python trong `backend/venv` ra được.**
> Dùng mẫu này để truy vấn Supabase:

```python
# Đặt file .py ở thư mục gốc repo, chạy: .\backend\venv\Scripts\python.exe <file>.py
import io, json, ssl, sys, urllib.request
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

env = {}
for line in Path("backend/.env").read_text(encoding="utf-8").splitlines():
    if line.strip() and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")

url, svc = env["SUPABASE_URL"].rstrip("/"), env["SUPABASE_SERVICE_ROLE_KEY"]
req = urllib.request.Request(f"{url}/rest/v1/products?select=*&limit=3",
                             headers={"apikey": svc, "Authorization": f"Bearer {svc}"})
print(urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=30).read().decode())
```

**Giới hạn:** PostgREST **không chạy được DDL** (`CREATE TABLE`). Muốn đổi schema phải:
(a) dán SQL vào Supabase Dashboard → SQL Editor, hoặc
(b) có `DATABASE_URL` (mật khẩu DB) để nối Postgres pooler `aws-0-ap-southeast-1.pooler.supabase.com:6543`, hoặc
(c) có Supabase Personal Access Token cho Management API.

Key hiện có: `SUPABASE_KEY` (anon, `sb_publishable_…`) và `SUPABASE_SERVICE_ROLE_KEY` (`sb_secret_…`).
**Cả hai đều KHÔNG chạy được DDL.**

### 2.4 Checklist migration — chạy THEO THỨ TỰ trước khi dùng tính năng

| # | File migration | Tạo ra | Phải chạy trước khi |
|---|----------------|--------|---------------------|
| 1 | `backend/migrations/add_loyalty_system.sql` | Bảng `vouchers`, hàm `increment_loyalty_points`, `rpc_redeem_points` | Bấm "Đổi điểm" ở `/loyalty` |
| 2 | `backend/migrations/add_staff_role.sql` | Thêm giá trị `staff` vào vai trò người dùng | **Gán vai trò `staff` cho bất kỳ user nào** |

⚠️ **Thứ tự bắt buộc:** phải chạy migration số 2 **trước khi** gán vai trò `staff`.
Nếu gán `staff` khi enum chưa có giá trị này, database sẽ từ chối và tài khoản
đó không đăng nhập được vào `/staff/sales`.

---

## 3. QUY TẮC LÀM VIỆC (BẮT BUỘC — ĐỌC KỸ)

### 3.1 Bài học đã trả giá

Một lần dùng PowerShell `Get-Content -Raw` + `Set-Content -Encoding UTF8` để sửa hàng loạt
**đã phá hủy tiếng Việt** trên 22 file (`"Điều hướng"` → `"Äiá»u hÆ°á»›ng"`).

**Hệ quả kép:** phải `git checkout` để khôi phục → **mất toàn bộ công sức đổi palette**
(vì chưa commit). Bài học: *công việc chưa commit sẽ mất khi revert.*

### 3.2 Quy tắc bắt buộc

1. **Sửa file nguồn CHỈ bằng tool `edit`/`write`.** Không bao giờ dùng PowerShell để ghi file source. PowerShell chỉ để đọc/kiểm tra.
2. **`git commit` sau mỗi mốc hoàn thành.** Đừng để công sức uncommitted.
3. **Tắt dev server trước khi sửa hàng loạt.** File-watcher giữ lock gây lỗi `ReplaceFileW EIO (Win32 1175)`.
4. **Khởi động server cần `sandbox_permissions: danger-full-access`.** Nếu không sẽ lỗi `spawn EPERM` (sandbox chặn named pipes).
5. **Kiểm tra `npx tsc --noEmit` sau mỗi nhóm thay đổi.** Phải trả exit 0.
6. **Không đoán — truy vấn database thật.** Dùng mẫu Python ở mục 2.3.

### 3.3 Quy tắc thiết kế (từ `taste-skill`)

- **Một hệ bo góc duy nhất** (Shape Consistency Lock). Dự án đang trộn `rounded-full`/`rounded-xl`/`rounded-2xl`/`rounded-lg` → cần chuẩn hóa.
- **Nút phải đạt WCAG AA 4.5:1.** `#8F8F8E` + chữ `#2B2B2A` chỉ đạt **3.9:1** → không dùng cho text nhỏ.
- **Cấm palette kem/nâu/coral.** Đây chính là bảng màu cũ của dự án.
- **Typography hero:** `text-4xl md:text-6xl` (56–64px desktop).

---

## 4. KẾ HOẠCH THI CÔNG

### Bảng màu chuẩn (theo logo — logo là chữ xám trung tính trên nền trắng)

| Token | Hex | Dùng cho |
|-------|-----|----------|
| `background` | `#FFFFFF` / `#FAFAF9` | Nền trang |
| `brand` | `#8F8F8E` | Accent, viền nút phụ |
| `brand-soft` | `#6B6B6A` | Hover của nút — **đạt AA với chữ trắng** |
| `ink` | `#2B2B2A` | Chữ chính |
| `muted` | `#6B6B6A` | Chữ phụ |
| `line` | `#E5E5E3` | Viền, divider |
| `surface` / `subtle` | `#FAFAF9` / `#F5F5F4` | Nền card |
| `action` | `#2B2B2A` | CTA chính (nền đậm, chữ trắng) |

**Nguyên tắc:** màu **ngữ nghĩa** (sao vàng, cảnh báo sắp hết hàng, xác nhận thành công) thì **GIỮ**.
Màu **trang trí** (avatar nhiều màu, gradient hồng) thì **BỎ**.

---

### GIAI ĐOẠN 0 — Dọn nền (15/09 → 21/09) ← ĐANG LÀM

- [x] Đo quy mô: **1.027 chỗ** dùng class màu cũ (`text-mocha` 505, `bg-pink-pastel` 113, `border-mocha` 106, `bg-cream` 90, `text-pink-pastel` 68, `border-pink-pastel` 55, `bg-mocha` 36, gradient 3)
- [x] **Tạo alias Tailwind** trong `tailwind.config.ts`: `mocha→#2B2B2A`, `pink-pastel→#2B2B2A`, `cream→#FAFAF9`
      → toàn bộ 1.027 chỗ đổi màu ngay, **zero rủi ro mojibake**. Đã xác minh CSS sinh ra đúng.
- [x] Dọn màu trang trí lệch tông trong `ProductDetailClient.tsx` (avatar 6 màu → thang xám; 3 khối gradient → `bg-surface`)
- [x] `npx tsc --noEmit` → exit 0
- [ ] **Chạy migration `vouchers`** (người dùng tự dán SQL vào Dashboard)
- [ ] Sửa từng file để bỏ dần tên class cũ, theo thứ tự: `checkout` → `orders` → `auth` → `cake-builder` → `admin`/`baker`
- [ ] Khi `grep -r "mocha\|pink-pastel\|cream"` = 0 → **XOÁ khối LEGACY ALIASES**
- [ ] Dọn dữ liệu test rác (12 user auth, nhiều tài khoản `abc`, `testuser99@example.com`, `testcart_debug@`)

**Đầu ra:** giao diện nhất quán tông logo; trang `/loyalty` chạy được.

---

### GIAI ĐOẠN 1 — Kho mẫu 3D (22/09 → 12/10)

**Vấn đề:** đề tài nói "tìm mẫu 3D gần giống nhất **trong kho**" nhưng chưa có kho.

- [ ] Thiết kế bảng `cake_3d_models`: `id, name, glb_url, thumbnail_url, tags[], category, created_at`
- [ ] Tạo 10–15 mẫu `.glb` (xem mục 5 về nguồn model)
- [ ] Chuyển `Cake3D.tsx` sang load `.glb` bằng `useGLTF` của `@react-three/drei` (**đã cài sẵn**)
- [ ] Giữ nguyên trình cấu hình hiện có, chỉ đổi nguồn model
- [ ] Thêm nút chuyển 2D/3D, lazy-load để không chặn first paint

**Đầu ra:** trang chi tiết xoay được mẫu 3D thật.
**Rủi ro:** làm model tốn thời gian → phương án lùi: 5 mẫu cơ bản + biến thể màu/trang trí.

---

### GIAI ĐOẠN 2 — CLIP image search (13/10 → 02/11) ⭐ ƯU TIÊN NẾU THIẾU THỜI GIAN

**Trụ cột số 2 của đề tài — hoàn toàn chưa có.**

- [ ] Bật extension `vector` (pgvector) trên Supabase
- [ ] Bảng `cake_embeddings`: `id, cake_id, source_image_url, embedding vector(512)`
- [ ] Thêm `open_clip_torch` (hoặc `sentence-transformers`) vào `backend/requirements.txt`
- [ ] Dùng model **ViT-B-32** (embedding 512 chiều, chạy CPU đủ nhanh)
- [ ] Script `backend/scripts/embed_catalog.py`: quét `product_images` → sinh embedding → upsert
- [ ] RPC `match_cakes(query_embedding, match_threshold, match_count)` theo
      [Supabase Vector docs](https://supabase.com/docs/guides/ai/vector-columns)
- [ ] Endpoint `POST /api/v1/search/by-image` (nhận upload → chuẩn hóa ảnh → embedding → top-K)
- [ ] Frontend: nút "Tìm bánh bằng ảnh" + kéo thả + lưới kết quả kèm % tương đồng
- [ ] Đo và ghi lại: thời gian embed, độ chính xác top-3 trên 10 ảnh test ← **số liệu cho báo cáo**

**Ghi chú kỹ thuật:** dùng `open_clip` (nhiều model, nhanh) thay vì `clip` gốc của OpenAI.
Chuẩn hóa ảnh đầu vào về RGB 224×224 trước khi embed, và **dùng cùng phép biến đổi** cho cả
ảnh catalog lẫn ảnh truy vấn — nếu lệch, độ tương đồng sẽ sai.

---

### GIAI ĐOẠN 3 — Agent đặt hàng (03/11 → 23/11)

**Trụ cột số 3 — nâng chatbot regex lên agent thật.**

Định nghĩa 5 tool cho LLM:

| Tool | Tham số | Trả về |
|------|---------|--------|
| `search_cakes` | `query, filters` | danh sách mẫu khớp |
| `calculate_price` | `size, toppings, decorations` | giá VND |
| `check_capacity` | `pickup_date` | tiệm còn nhận đơn không |
| `create_draft_order` | `items, pickup_date` | `draft_order_id` |
| `get_loyalty_info` | `user_id` | điểm hiện có |

- [ ] Chuyển `chat_service.py` sang **Groq function calling** (Llama 3.3 70B hỗ trợ tool use)
- [ ] Vòng lặp agent: LLM gọi tool → nhận kết quả → gọi tiếp → trả lời (đặt `max_iterations` để tránh lặp vô hạn)
- [ ] **XOÁ `extract_recommendations` và `extract_ai_summary`** (regex — nguồn gốc lỗi)
- [ ] Bảng `draft_orders` — khách xác nhận mới thành đơn thật
- [ ] **Log mọi tool call** → đây là bằng chứng cho luận điểm "dựa trên quy trình vận hành thực tế"
- [ ] Xử lý lỗi: tool thất bại → agent phải nói được lý do, không bịa

**Đầu ra:** khách chat *"bánh 20cm cho 10 người, thứ 7 tuần sau"* → agent tự tra giá, kiểm tra lịch, tạo đơn nháp.

---

### GIAI ĐOẠN 4 — Tối ưu & báo cáo (24/11 → 01/12)

**Điểm người dùng chưa hài lòng (cần xử lý):**

- [ ] **Hiệu năng — chậm và lag.** Việc cần làm:
      - Đo trước khi sửa: Lighthouse, bundle size (`next build` output), xem route nào nặng
      - Kiểm tra nguyên nhân thường gặp: ảnh không dùng `next/image`, component nặng không lazy-load
        (`Cake3D` kéo theo cả `three` ~600KB!), fetch thừa, re-render do context
      - `three` + `r3f` chỉ nên nạp ở route có 3D, dùng `dynamic(() => import(...), { ssr: false })`
- [ ] **Thiết kế đơn điệu, chưa sang.** Hướng xử lý:
      - Tăng tương phản thị giác bằng **khoảng trắng** và **thang chữ**, không thêm màu
      - Dùng ảnh chất lượng cao, tỉ lệ nhất quán
      - Áp pre-flight checklist của `taste-skill`
- [ ] Kiểm thử: unit test cho 5 tool; test CLIP với 10 ảnh mẫu
- [ ] Đo hiệu năng: thời gian embed, độ trễ agent, kích thước model
- [ ] Viết báo cáo + quay video demo

---

## 5. NGUỒN MODEL 3D — KHUYẾN NGHỊ

Câu hỏi: *"lấy mấy model trên mạng có ổn không?"*
**Trả lời: ỔN — nhưng phải kiểm tra giấy phép.** Với đồ án học thuật, dùng model có giấy phép
mở là hoàn toàn hợp lệ, miễn ghi nguồn trong báo cáo.

### Tiêu chí chọn model

1. **Định dạng `.glb`** (không phải `.fbx`/`.blend`) — three.js load trực tiếp
2. **Dung lượng < 5MB** mỗi model — nếu nặng hơn, phải nén bằng Draco hoặc meshopt
3. **Giấy phép:** CC0 / Public Domain (tốt nhất) > CC-BY (phải ghi nguồn) > CC-BY-NC (phi thương mại)
4. **Số tam giác < 50k** — model quá chi tiết sẽ lag trên máy yếu
5. **Ưu tiên model có cấu trúc tách rời** (đế / thân / mặt / kem) → dễ đổi màu từng phần như trình cấu hình hiện tại

### Nguồn cụ thể

| Nguồn | Giấy phép | Ghi chú |
|-------|-----------|---------|
| **Poly Pizza** (poly.pizza) | CC0 / CC-BY | Model low-poly, nhẹ, nhiều đồ ăn. **Phù hợp nhất cho đồ án** |
| **Sketchfab** (sketchfab.com) | Lọc theo CC | Bật filter "Downloadable" + "CC0". Nhiều bánh đẹp nhưng phải kiểm tra từng model |
| **Quaternius** (quaternius.com) | CC0 | Gói low-poly, miễn phí hoàn toàn |
| **Kenney** (kenney.nl) | CC0 | Asset game, có gói food |
| **CGTrader / TurboSquid** | Trả tiền | Chất lượng cao, nếu cần bánh photorealistic |

### Khuyến nghị cho đồ án này

**Phương án A (khuyến nghị):** 5–8 model low-poly CC0 từ Poly Pizza + Quaternius,
mỗi model tách phần (đế/thân/mặt) → **dùng chính trình cấu hình hiện có để đổi màu và trang trí**.
Cách này biến 8 model thành hàng trăm biến thể, và **thể hiện được đúng tinh thần đề tài**
(khách tự thiết kế bánh), không chỉ là xem ảnh 3D tĩnh.

**Phương án B:** nếu cần hình ảnh chân thực để gây ấn tượng khi bảo vệ → 2–3 model trả phí
+ phần còn lại low-poly.

**Phương án C (không khuyến nghị):** tiếp tục dựng bằng code như hiện tại. Chất lượng trung bình
và **không khớp đề tài** (đề tài nói "kho mẫu 3D", không phải "sinh hình bằng code").

### Nếu model quá nặng

```bash
npx gltf-transform optimize input.glb output.glb --compress draco --texture-compress webp
```

---

## 6. VIỆC KHÔNG PHỤ THUỘC QUYẾT ĐỊNH — LÀM ĐƯỢC NGAY

1. Chạy migration `vouchers` (cần người dùng dán SQL vào Dashboard)
2. Sửa dần 1.027 chỗ class màu cũ theo từng file
3. Đo hiệu năng hiện tại (Lighthouse, bundle size) — **cần làm trước khi tối ưu**
4. Viết script `embed_catalog.py` (không cần chờ có model 3D)

---

## 7. RỦI RO & PHƯƠNG ÁN LÙI

| Rủi ro | Xác suất | Phương án lùi |
|--------|----------|---------------|
| Không kịp làm model 3D đẹp | Cao | Dùng 5 model low-poly CC0 + biến thể màu |
| CLIP tìm không chính xác | Trung bình | Thử model lớn hơn (ViT-L/14), thêm lọc theo category |
| Agent gọi tool sai | Trung bình | Giới hạn tool, thêm validate tham số trước khi thực thi |
| Hết thời gian | Trung bình | **Ưu tiên CLIP trước Agent** (theo yêu cầu người dùng) |
| Supabase hết quota | Thấp | Dữ liệu nhỏ (22 sản phẩm), rủi ro không đáng kể |

---

## 8. THỨ TỰ ƯU TIÊN KHI THIẾU THỜI GIAN

Theo yêu cầu người dùng — **ưu tiên CLIP trước**:

1. **CLIP image search** (trụ cột đề tài, chưa có gì) ← quan trọng nhất
2. **Kho mẫu 3D** (nền tảng để CLIP có ý nghĩa — không có kho thì CLIP tìm gì?)
3. **Agent đặt hàng** (nâng cấp từ chatbot đã có)
4. **Tối ưu hiệu năng + thẩm mỹ** (cải thiện cái đang có)
5. **Dọn palette** (đã có alias, không chặn gì)
