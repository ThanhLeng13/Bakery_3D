# ĐÁNH GIÁ ĐỘ CHÍNH XÁC CLIP — BÁO CÁO KẾT QUẢ

Ngày đo: 2026-09-21
Model: `ViT-B-32` / `laion2b_s34b_b79k`, vector 512 chiều, cosine similarity
Kho: 22 sản phẩm, 20 embedding trên 18 sản phẩm

---

## 1. VẤN ĐỀ VỚI CON SỐ "100%" TRƯỚC ĐÓ

Con số 100% từng báo cáo là **self-match**: lấy ảnh trong kho, đưa lại chính ảnh
đó vào hệ thống, rồi kiểm tra xem có tìm ra không. Vector truy vấn **trùng khít**
vector đã lưu nên cosine = 1.0. Đây là trường hợp tầm thường, **không có giá trị
khoa học** vì không mô phỏng việc khách chụp ảnh ngoài đời.

Báo cáo này thay bằng ảnh **tải từ Wikimedia Commons** — khác nguồn, khác góc
chụp, khác ánh sáng, khác nền.

---

## 2. BỘ DỮ LIỆU TEST

| Nhóm | Số ảnh | Mục đích |
|---|---|---|
| Thuộc món có trong kho | 18 | Đo top-1 / top-3 accuracy |
| Không thuộc kho (pizza, sushi, xe hơi…) | 8 | Đo khả năng KHÔNG match bừa |

Ảnh đều có giấy phép CC (CC0, CC BY, CC BY-SA), nguồn và tác giả ghi trong
`backend/test_images/manifest.json` để trích dẫn.

---

## 3. KẾT QUẢ

### 3.1 Ảnh thuộc món có trong kho

| Chỉ số | Kết quả |
|---|---|
| **Top-1 accuracy** | **22.2%** (4/18) |
| **Top-3 accuracy** | **55.6%** (10/18) |

### 3.2 Ảnh KHÔNG thuộc kho

| Ảnh | Top-1 trả về | Similarity |
|---|---|---|
| pizza | Bánh tart trứng | 0.550 |
| hamburger | Bánh phomai sợi dẻo | 0.477 |
| sushi | Bánh Dark Oreo | 0.520 |
| bánh mì | Bánh phomai sợi dẻo | 0.496 |
| phở | Bánh phô mai cháy | 0.462 |
| salad | Bánh kem cốm dẻo | 0.464 |
| cà phê | Bánh phô mai cháy | 0.419 |
| xe hơi | Bánh Dark Oreo | 0.216 |

### 3.3 Phân bố similarity

| Nhóm | Trung bình | Min | Max |
|---|---|---|---|
| Trong kho | 0.554 | 0.355 | 0.687 |
| Ngoài kho | 0.450 | 0.216 | 0.550 |

Khoảng cách hai nhóm: **+0.103** — hẹp.

Với ngưỡng trung điểm 0.502:
- Ảnh ngoài kho bị nhận nhầm: **2/8**
- Ảnh trong kho bị bỏ sót: **3/18**

---

## 4. NGUYÊN NHÂN GỐC — ĐÃ KIỂM CHỨNG BẰNG ẢNH

Đây **không phải lỗi model**. Nguyên nhân là **ảnh trong kho không phải ảnh chụp
sản phẩm thuần túy**, mà là ảnh quảng cáo có gắn thương hiệu.

Kiểm tra trực tiếp ảnh kho của "Bánh tiramisu truyền thống" và "Bánh crepe sầu
riêng", cả hai đều chứa:

1. **Logo Bơ Nơ lớn** ở giữa phía trên
2. **Tên sản phẩm cỡ lớn** ("TIRAMISU TRUYỀN THỐNG", "CREPE SẦU RIÊNG")
3. **Số điện thoại + địa chỉ** ở đáy: "0905 884 857 / 234 Đống Đa, TP.Đà Nẵng"
4. Nền xám, khay gỗ, thìa trang trí

Nghĩa là **khoảng một nửa diện tích ảnh là chữ và logo**, không phải bánh. CLIP
nhúng **toàn bộ ảnh**, nên vector bị pha loãng bởi văn bản, logo, nền và đạo cụ.

### Bằng chứng định lượng

So similarity của ảnh test (sạch, không logo) với **chính** ảnh kho của cùng món,
đối chiếu với món khác gần nhất:

| Món | sim với CHÍNH nó | sim với món KHÁC cao nhất | Kết luận |
|---|---|---|---|
| Bánh Brownie | 0.542 | 0.530 (Rau câu flan cheese) | sát nút |
| Bánh tart trứng | 0.638 | 0.562 (Bánh phô mai cháy) | đúng |
| Bánh tiramisu truyền thống | **0.268** | **0.633** (Bánh Dark Oreo) | **nhầm** |
| Bánh su kem | **0.356** | **0.577** (Bánh tart trứng) | **nhầm** |
| Bánh crepe sầu riêng | **0.274** | **0.581** (Rau câu flan cheese) | **nhầm** |
| Bánh phô mai cháy | **0.558** | **0.588** (Bánh Dark Oreo) | **nhầm** |

Với tiramisu: ảnh test giống **Bánh Dark Oreo gấp 2,4 lần** so với chính ảnh
tiramisu trong kho. Điều này vô lý về mặt thị giác — tiramisu và Dark Oreo là hai
loại bánh khác nhau. Nó chỉ hợp lý khi vector của ảnh kho bị chi phối bởi thứ
khác ngoài cái bánh.

### Kiểm chứng bằng cách cắt bỏ phần thương hiệu

Giả thuyết: nếu vector bị pha loãng bởi logo và chữ, thì cắt bỏ chúng phải làm
vector tập trung vào bánh hơn, và accuracy phải tăng.

Đã thử **8 cách tiền xử lý** khác nhau trên ảnh kho, đo lại toàn bộ bằng chính bộ
test ngoài kho (`scripts/try_preprocessing.py`):

| Cách xử lý ảnh kho | Top-1 | Top-3 |
|---|---|---|
| **Không xử lý (baseline)** | **22.2%** | **55.6%** |
| Cắt 70% giữa | 16.7% | 44.4% |
| Cắt 55% giữa | 22.2% | 33.3% |
| Cắt 45% giữa | 22.2% | 50.0% |
| Cắt 70% phần dưới (bỏ logo) | 16.7% | 50.0% |
| Bỏ 20% trên + 12% dưới | 27.8% | 44.4% |
| Bỏ 26% trên + 12% dưới | 22.2% | 44.4% |
| Bỏ 32% trên + 14% dưới | 11.1% | 55.6% |

**Kết luận: tiền xử lý KHÔNG cải thiện được gì.**

Cách tốt nhất theo top-1 ("bỏ 20% trên + 12% dưới") đạt 27.8%, tức **+5.6 điểm**.
Nhưng chính cách đó lại làm **top-3 GIẢM 11.2 điểm** (55.6% → 44.4%). Với bộ test
18 ảnh, **một ảnh đổi kết quả = 5.6 điểm**, nên mức +5.6 này **nằm trong nhiễu**,
không phải tiến bộ thật.

Đây là lý do báo cáo này **không** khuyến nghị cắt logo như một giải pháp. Giả
thuyết "vector bị pha loãng bởi thương hiệu" có bằng chứng gián tiếp mạnh (mục
4), nhưng **cách sửa bằng cắt ảnh đã bị thực nghiệm bác bỏ**.

Nguyên nhân có thể: cắt ảnh làm mất luôn ngữ cảnh (khay, nền, bố cục) — những
thứ giúp ích cho việc nhận diện — trong khi phần chữ chỉ chiếm một phần nhỏ vector.

---

## 5. HẠN CHẾ CỦA BÁO CÁO NÀY

Cần nói rõ để không báo cáo quá mức:

1. **Bộ test nhỏ**: 18 ảnh trong kho, 8 ảnh ngoài kho. Sai số thống kê lớn —
   một ảnh đổi kết quả làm accuracy đổi 5,6 điểm phần trăm.
2. **Nhãn do người viết gán**, dựa trên từ khoá tìm kiếm, chưa được kiểm duyệt
   độc lập. Ảnh tìm bằng từ khoá "banana cake" có thể không đúng là bánh chuối
   nướng nước dừa của tiệm.
3. **Khác biệt phân bố là thật**: ảnh Wikimedia là ảnh stock quốc tế, còn kho là
   bánh Việt Nam. Một phần sai số đến từ đây, không phải từ model.
4. **4 sản phẩm loại `cake` không có ảnh** nên không thể match: Bánh kem vanilla
   classic, socola sinh nhật, matcha, 2 tầng hoa hồng.

---

## 6. KHUYẾN NGHỊ

Thứ tự dưới đây xếp theo **tác động đã đo được**, không theo mức độ dễ làm.

### Ưu tiên 1 — Sửa dữ liệu kho (tác động lớn nhất, CHƯA đo được mức cải thiện)

Ảnh kho cần là **ảnh chụp sản phẩm thuần**: không logo, không chữ, không
watermark. Đây là nguyên nhân gốc (mục 4).

**Nhưng phải nói thật:** giả thuyết này **chưa được chứng minh là sửa được**.
Cách sửa rẻ nhất — cắt ảnh — đã bị thực nghiệm **bác bỏ** (mục 4). Cách còn lại là
**chụp lại ảnh mới**, và chưa có dữ liệu để biết nó cải thiện bao nhiêu.

Đây là việc nên làm, nhưng **không nên hứa hẹn con số** trước khi đo.

### Ưu tiên 2 — Bổ sung ảnh cho 4 bánh kem còn thiếu

Hiện CLIP **không thể** match nhóm này. Đây là nhóm khách tìm nhiều nhất (bánh
sinh nhật). Việc này chắc chắn có tác động, vì hiện tại 4 sản phẩm này chắc chắn
0% — thêm ảnh là từ 0 lên có.

### Ưu tiên 3 — Nâng lên ViT-L-14 (đã đo, +22.2 điểm top-1)

Đây là cải thiện **đã đo được, không phải phỏng đoán**. Đánh đổi:
- Chậm hơn 9,2 lần (97ms → 894ms/ảnh)
- RAM 1,4 GB → 3,6 GB
- Cần đổi cột `embedding` từ `vector(512)` sang `vector(768)` và **nhúng lại
  toàn bộ kho**
- **Vẫn không sửa được vấn đề gốc** và vẫn không đủ tách nhóm để đặt ngưỡng

### Ưu tiên 4 — Thêm ảnh mỗi sản phẩm (nhiều góc)

Mỗi sản phẩm nên có 3–5 ảnh ở các góc/ánh sáng khác nhau. Hiện chỉ 2 sản phẩm có
2 ảnh. Chưa đo được tác động vì kho hiện quá ít ảnh.

### Ưu tiên 5 — Hiển thị top-3 kèm phần trăm, đừng khẳng định

Với khoảng cách hai nhóm gần bằng 0 (−0.006 với ViT-B-32, +0.021 với ViT-L-14),
**không ngưỡng nào tách sạch được**. Nên:
- Hiển thị **top-3 kèm % giống** để khách tự chọn
- Ghi rõ **"kết quả gần đúng"**, không khẳng định "đây là bánh bạn muốn"
- Đây là cách trung thực với người dùng khi model chưa đủ tin cậy

### Hướng cải thiện model (nếu còn thời gian)

Đã thử nghiệm thật, không chỉ đề xuất suông (`scripts/compare_models.py`):

| Model | Vector | Top-1 | Top-3 | ms/ảnh | RAM |
|---|---|---|---|---|---|
| **ViT-B-32** (đang dùng) | 512 | 22.2% | 55.6% | **97** | **1.4 GB** |
| **ViT-L-14** | 768 | **44.4%** | **66.7%** | 894 | 3.6 GB |

**ViT-L-14 gấp đôi top-1 (+22.2 điểm) và tăng top-3 (+11.1 điểm).**

Nhưng phải đọc con số này cho đúng — ba điều cần lưu ý:

1. **Chậm hơn 9,2 lần** (97ms → 894ms mỗi ảnh trên CPU). Tìm kiếm ảnh sẽ từ
   ~0,4 giây thành ~4 giây.
2. **Tốn RAM gấp 2,6 lần** (1,4 GB → 3,6 GB). Cần kiểm tra máy chủ triển khai
   có đủ không.
3. **KHÔNG sửa được vấn đề gốc.** Kiểm tra lại từng món với ViT-L-14:

   | Món | sim với CHÍNH nó | sim với món KHÁC |
   |---|---|---|
   | Bánh tiramisu | 0.376 | 0.608 (Dark Oreo) — **vẫn nhầm** |
   | Bánh crepe sầu riêng | 0.374 | 0.613 (Rau câu flan) — **vẫn nhầm** |
   | Bánh su kem | 0.513 | 0.615 (Bánh tart trứng) — **vẫn nhầm** |

   Đúng những món thất bại với ViT-B-32 **vẫn thất bại** với ViT-L-14. Model to
   hơn chỉ **may mắn đúng ở nhiều món khác hơn**, chứ không tạo ra ranh giới rõ
   ràng hơn giữa "có trong kho" và "không có".

   Bằng chứng: khoảng cách similarity giữa nhóm trong kho và ngoài kho chỉ đi từ
   **−0.006** lên **+0.021**. Vẫn gần như bằng 0. Nghĩa là **vẫn không thể đặt
   ngưỡng từ chối đáng tin cậy** dù dùng model nào.

**Kết luận về model:** nâng lên ViT-L-14 là một cải thiện **có thật và đo được**,
đáng làm **nếu** máy chủ chịu được 3,6 GB RAM và độ trễ 4 giây. Nhưng nó **không
thay thế được việc sửa dữ liệu** — vẫn phải làm Khuyến nghị 1 và 2 bên dưới.

### Hướng khác chưa thử

- `ViT-H-14` (vector 1024) — còn lớn hơn nữa, RAM có thể vượt 6 GB
- `SigLIP` — huấn luyện trên dữ liệu lớn hơn, có thể nhạy với ảnh sản phẩm hơn
- Fine-tune trên chính ảnh của tiệm — hiệu quả nhất nhưng cần nhiều ảnh có nhãn,
  mà hiện kho chỉ có 20 ảnh

---

## 7. CÁCH TÁI LẬP KẾT QUẢ

```bash
cd backend
python scripts/collect_test_images.py      # tải bộ ảnh test (cần mạng)
python scripts/evaluate_clip_accuracy.py   # đo accuracy: top-1 22.2%
python scripts/try_preprocessing.py        # thử 8 cách tiền xử lý ảnh
python scripts/compare_models.py           # so ViT-B-32 với ViT-L-14
```

Kết quả chi tiết:
- `backend/test_images/accuracy_report.json` — từng ảnh, top-1/top-3
- `backend/test_images/preprocessing_results.json` — 8 chiến lược tiền xử lý
- `backend/test_images/model_comparison.json` — so sánh hai model

Lưu ý: `compare_models.py` tải ViT-L-14 (~1,6 GB) ở lần chạy đầu.
