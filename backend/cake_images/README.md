# Ảnh bánh sinh nhật — nơi bạn bỏ ảnh vào

Thư mục này là nơi bạn đặt ảnh chụp bánh sinh nhật. Script sẽ tự tải lên
Supabase và sinh embedding cho CLIP.

## Quy ước đặt tên

```
backend/cake_images/<tên-sản-phẩm>/<số>.jpg
```

**Thư mục con phải TRÙNG TÊN sản phẩm** trong bảng `products`. Sai tên thì script
báo rõ và bỏ qua, không âm thầm gán nhầm sang sản phẩm khác.

Ví dụ:

```
backend/cake_images/Bánh sinh nhật hoa tươi/1.jpg
backend/cake_images/Bánh sinh nhật hoa tươi/2.jpg
backend/cake_images/Bánh sinh nhật hoa tươi/3.jpg
backend/cake_images/Bánh sinh nhật 2 tầng hoa hồng/1.jpg
backend/cake_images/Bánh sinh nhật matcha/1.jpg
```

## Danh sách 15 kiểu mẫu cần ảnh

Sau khi chạy `migrations/add_birthday_cake_catalog.sql`, đây là các thư mục cần tạo:

| # | Tên thư mục | Giá từ |
|---|---|---|
| 1 | `Bánh sinh nhật bé trai siêu nhân` | 320.000đ |
| 2 | `Bánh sinh nhật bé gái công chúa` | 320.000đ |
| 3 | `Bánh sinh nhật hoa tươi` | 420.000đ |
| 4 | `Bánh sinh nhật hoa buttercream` | 380.000đ |
| 5 | `Bánh sinh nhật 2 tầng hoa hồng` | 750.000đ |
| 6 | `Bánh sinh nhật 2 tầng tối giản` | 680.000đ |
| 7 | `Bánh sinh nhật trái cây tươi` | 400.000đ |
| 8 | `Bánh sinh nhật socola` | 380.000đ |
| 9 | `Bánh sinh nhật matcha` | 400.000đ |
| 10 | `Bánh sinh nhật red velvet` | 420.000đ |
| 11 | `Bánh sinh nhật minimal Hàn Quốc` | 360.000đ |
| 12 | `Bánh sinh nhật con vật đáng yêu` | 350.000đ |
| 13 | `Bánh sinh nhật số tuổi` | 340.000đ |
| 14 | `Bánh sinh nhật người lớn thanh lịch` | 450.000đ |
| 15 | `Bánh sinh nhật 3 tầng cưới hỏi` | 1.450.000đ |

Bốn bánh kem cũ cũng sẽ được bật lên, có thể thêm ảnh cho chúng:
`Bánh kem vanilla classic`, `Bánh kem socola sinh nhật`, `Bánh kem matcha`,
`Bánh kem 2 tầng hoa hồng`.

## Ảnh nên chụp thế nào

**Quan trọng — đã đo được, không phải phỏng đoán.** Ảnh kho hiện tại có logo và
chữ lớn đè lên, và điều đó làm hỏng việc tìm kiếm: đo được bánh tiramisu chỉ đạt
**0,268** độ tương đồng với chính ảnh của nó, nhưng đạt **0,633** với bánh Dark
Oreo. Vector bị chữ và logo chi phối. Chi tiết ở
`backend/test_images/BAO_CAO_DO_CHINH_XAC.md`.

Nên chụp:

- **Không logo, không chữ, không watermark, không số điện thoại**
- **Một bánh trên mỗi ảnh**, bánh chiếm phần lớn khung
- **Mỗi kiểu 3–5 ảnh** ở các góc khác nhau (chính diện, 45°, nhìn từ trên)
- Ánh sáng đều, nền trung tính (trắng, kem, gỗ)
- Tối thiểu **224×224** pixel, nên từ 800×800 trở lên
- Định dạng `.jpg`, `.jpeg`, `.png`, hoặc `.webp`

Nhiều góc quan trọng vì khách chụp ảnh ở góc nào cũng phải match được.

## Cách chạy

```bash
cd backend
python scripts/import_cake_images.py --dry-run   # xem trước, không ghi gì
python scripts/import_cake_images.py             # tải lên thật
python scripts/embed_catalog.py                  # sinh embedding cho CLIP
python scripts/evaluate_clip_accuracy.py         # đo lại độ chính xác
```

`--dry-run` chỉ liệt kê việc sẽ làm và cảnh báo ảnh quá nhỏ, tên thư mục sai, hay
sản phẩm còn thiếu ảnh. Nên chạy trước để phát hiện lỗi đặt tên.

## Ảnh không được đẩy lên Git

Thư mục này nằm trong `.gitignore` — ảnh dung lượng lớn không nên vào repository.
Ảnh được lưu trên Supabase Storage, Git chỉ giữ mã nguồn.
