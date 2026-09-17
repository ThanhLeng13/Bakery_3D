# HƯỚNG DẪN CÀI ĐẶT & KIỂM THỬ

> Dành cho người kiểm thử (giảng viên, thành viên nhóm, hoặc người review).
> Mọi lệnh dưới đây đã được chạy thử và xác minh hoạt động.

---

## 1. YÊU CẦU MÔI TRƯỜNG

| Phần mềm | Phiên bản | Ghi chú |
|----------|-----------|---------|
| Node.js | 20 trở lên | Frontend |
| Python | 3.11 – 3.13 | Backend. Bản phát triển dùng 3.13 |
| Git | bất kỳ | |

Kiểm tra nhanh:

```bash
node --version    # >= v20
python --version  # >= 3.11
```

---

## 2. CÀI ĐẶT

### Bước 1 — Lấy mã nguồn

```bash
git clone https://github.com/ThanhLeng13/Bakery_3D.git
cd Bakery_3D
git checkout fix/ci-and-runtime-performance
```

### Bước 2 — Backend

```bash
cd backend

# Tạo môi trường ảo
python -m venv venv

# Kích hoạt
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

# Cài thư viện
pip install -r requirements.txt
pip install pytest==9.0.3 pytest-asyncio==1.3.0
```

### Bước 3 — Cấu hình biến môi trường

Tạo file `backend/.env`:

```env
SUPABASE_URL=https://azdfyzfpwsdgzpfjivtb.supabase.co
SUPABASE_KEY=<anon key>
SUPABASE_SERVICE_ROLE_KEY=<service role key>
JWT_SECRET=<chuỗi bí mật bất kỳ>
GROQ_API_KEY=<Groq API key>
```

> **Lưu ý:** các key này **không có trong repo** (đã được `.gitignore`).
> Liên hệ chủ dự án để lấy, hoặc dùng project Supabase riêng.

Tạo file `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://azdfyzfpwsdgzpfjivtb.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
```

### Bước 4 — Frontend

```bash
cd frontend
npm ci
```

---

## 3. CHẠY ỨNG DỤNG

Cần **2 cửa sổ terminal**.

**Terminal 1 — Backend:**

```bash
cd backend
venv\Scripts\activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Kiểm tra: mở http://localhost:8000/docs — phải thấy Swagger UI.

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

Mở http://localhost:3000

---

## 4. CHẠY KIỂM THỬ TỰ ĐỘNG

Đây là phần **quan trọng nhất** — không cần đọc code, chỉ cần chạy và xem kết quả.

### Backend (199 bài kiểm thử)

```bash
cd backend
python -m pytest -q --no-header
```

**Kết quả mong đợi:**

```
199 passed
```

### Frontend — kiểm tra kiểu dữ liệu

```bash
cd frontend
npx tsc --noEmit
```

**Kết quả mong đợi:** không in gì, exit code 0.

### Frontend — kiểm tra quy tắc code

```bash
cd frontend
npx next lint --max-warnings=0
```

**Kết quả mong đợi:** `✔ No ESLint warnings or errors`

### Frontend — build production

```bash
cd frontend
npx next build
```

**Kết quả mong đợi:** `✓ Compiled successfully`, First Load JS khoảng **87.5 kB**.

---

## 5. KIỂM THỬ TRÊN GITHUB (không cần cài đặt)

Vào tab **Actions** của repo:

https://github.com/ThanhLeng13/Bakery_3D/actions

Mỗi lần push, GitHub tự chạy 2 job:

| Job | Nội dung |
|-----|----------|
| Backend tests (pytest) | Cài thư viện, chạy 199 bài test |
| Frontend typecheck and lint | `tsc` + `lint` + `build` |

Dấu ✅ xanh = đạt. Dấu ❌ đỏ = có lỗi, bấm vào để xem chi tiết.

---

## 6. DANH SÁCH KIỂM TRA CHỨC NĂNG

### 6.1 Trang chủ — `/`

- [ ] Logo "Bơ Nơ Bakery" hiển thị đúng, không méo
- [ ] **Không có màu cam / hồng / nâu / kem** — toàn bộ là tông xám trung tính
- [ ] Tiêu đề lớn (hero) hiển thị cỡ 56–64px trên màn hình rộng
- [ ] Nút **"Thiết kế bánh ngay"**: nền đen, chữ trắng
- [ ] Di chuột vào nút → nền chuyển xám đậm hơn, **chữ vẫn đọc rõ**
- [ ] 3 thẻ tính năng có viền và bóng, không dính vào nhau
- [ ] Thu nhỏ cửa sổ xuống 375px → bố cục không vỡ

### 6.2 Đăng nhập — `/auth/login`

- [ ] Nhập sai mật khẩu → hiện thông báo lỗi, **không lộ chi tiết kỹ thuật**
      (không được thấy chữ `Postgres`, `relation`, `LINE 1`, hay tên bảng)
- [ ] Đăng nhập đúng → chuyển trang theo vai trò
- [ ] Nhấn Enter ở ô mật khẩu → đăng nhập được

### 6.3 Tìm bánh bằng hình ảnh — *chưa có*

> Tính năng CLIP nằm trong giai đoạn tiếp theo, chưa triển khai ở nhánh này.

### 6.4 Menu bánh — `/products`

- [ ] Danh sách bánh hiển thị, có **22 sản phẩm**
- [ ] Ảnh bánh tải được
- [ ] Thẻ bánh có viền, di chuột vào viền đổi màu
- [ ] Tìm kiếm và lọc theo loại hoạt động

### 6.5 Thiết kế bánh — `/cake-builder`

- [ ] Bánh 3D hiển thị và **xoay được bằng chuột**
- [ ] Chọn màu / chọn topping → bánh 3D cập nhật ngay
- [ ] Giá tiền thay đổi tương ứng khi đổi kích thước
- [ ] **Lưu ý:** màu của bánh (hồng, nâu socola) là **màu thật của bánh**,
      không phải lỗi — đây là chủ ý thiết kế

### 6.6 Tích điểm — `/loyalty`

- [ ] Cần đăng nhập bằng tài khoản `customer` mới xem được
- [ ] Hiển thị số điểm, lịch sử giao dịch
- [ ] **Đã biết lỗi:** bấm "Đổi điểm" sẽ lỗi, do bảng `vouchers` chưa được
      tạo trong database. Cần chạy `backend/migrations/add_loyalty_system.sql`
      trong Supabase SQL Editor.

### 6.7 Kiểm tra hiệu năng

- [ ] Mở DevTools (F12) → tab **Network** → tải lại trang
- [ ] Tổng dung lượng JS tải về **dưới 150 kB** cho trang chủ
- [ ] Mở tab **Performance** → ghi lại khi chuyển trang → không có khựng rõ rệt
- [ ] **Quan trọng:** thư viện 3D (`three`, ~600 kB) **chỉ được tải ở trang
      `/cake-builder`**, không tải ở trang chủ. Kiểm tra bằng cách xem tab
      Network khi mở trang chủ — không được thấy file chunk lớn.

### 6.8 Kiểm tra giao diện, không phụ thuộc chức năng

- [ ] **Nhất quán bo góc:** quan sát kỹ, hiện dùng 5 hệ bo góc khác nhau
      (`rounded-full`, `xl`, `lg`, `2xl`, `md`) — đây là **hạn chế đã biết**,
      chưa chuẩn hóa
- [ ] **Nhất quán màu:** không có phần tử nào mang màu xanh lá / cam / hồng
      ở giao diện (ngoại trừ màu bánh và màu trạng thái như sao vàng)
- [ ] Thu nhỏ xuống 375px và phóng to 1440px → không tràn ngang, không vỡ chữ

---

## 7. LỖI ĐÃ BIẾT

| Lỗi | Nguyên nhân | Cách khắc phục |
|-----|-------------|----------------|
| Bấm "Đổi điểm" báo lỗi | Bảng `vouchers` chưa tồn tại trong database | Chạy `backend/migrations/add_loyalty_system.sql` trong Supabase SQL Editor |
| Không đăng nhập được tài khoản mới đăng ký | Supabase đang bật xác nhận email | Xác nhận qua email, hoặc tắt trong Supabase → Authentication → Providers |
| Bo góc không nhất quán | 5 hệ bo góc đang dùng song song | Chưa xử lý, cần thống nhất một hệ |

---

## 8. CẤU TRÚC MÃ NGUỒN

```
Bakery_3D/
├── backend/                    FastAPI + Python
│   ├── app/
│   │   ├── api/v1/endpoints/   Các route API
│   │   ├── services/           Nghiệp vụ
│   │   ├── schemas/            Kiểu dữ liệu vào/ra
│   │   └── core/               Cấu hình, bảo mật
│   ├── tests/                  199 bài kiểm thử
│   └── migrations/             SQL tạo bảng
├── frontend/                   Next.js 14 + TypeScript
│   └── src/
│       ├── app/                Các trang (App Router)
│       ├── components/         Thành phần giao diện
│       ├── contexts/           Trạng thái toàn cục
│       └── lib/                Tiện ích
└── KE_HOACH.md                 Kế hoạch 11 tuần
```

---

## 9. CÔNG NGHỆ SỬ DỤNG

| Lớp | Công nghệ |
|-----|-----------|
| Giao diện | Next.js 14.2, React 18, TypeScript 5, Tailwind CSS 3.4 |
| 3D | three.js 0.184, @react-three/fiber 8.18, @react-three/drei 9.121 |
| Backend | FastAPI, Python, Pydantic 2 |
| Dữ liệu | Supabase (PostgreSQL + Auth + Storage) |
| AI hội thoại | Groq API — Llama 3.3 70B |
| Kiểm thử | pytest 9.0.3, pytest-asyncio 1.3.0 |
| CI/CD | GitHub Actions |
