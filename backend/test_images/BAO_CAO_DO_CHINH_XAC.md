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

Cắt phần trung tâm ảnh (bỏ logo trên, watermark dưới) rồi đo lại:

| Món | sim gốc | sim sau khi cắt |
|---|---|---|
| Bánh tiramisu truyền thống | 0.633 | **0.772** (+0.139) |
| Bánh su kem | 0.577 | **0.652** (+0.075) |
| Bánh crepe sầu riêng | 0.581 | 0.518 (−0.063) |
| Bánh Brownie | 0.542 | 0.426 (−0.116) |

Kết quả **không đồng nhất**: cắt giúp 2 món, làm tệ 2 món. Nên **không thể kết
luận đơn giản rằng "cắt logo là xong"**. Cần thử nghiệm đầy đủ trước khi kết luận.

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

### Ưu tiên 1 — Sửa dữ liệu kho (tác động lớn nhất)

Ảnh kho cần là **ảnh chụp sản phẩm thuần**, không logo, không chữ, không
watermark. Đây là nguyên nhân gốc đã kiểm chứng. Cách làm:
- Chụp lại ảnh sản phẩm trên nền trung tính, không chèn chữ
- Hoặc cắt bỏ phần chữ/logo trước khi embed — **nhưng phải đo lại đầy đủ**, vì
  thử nghiệm sơ bộ cho thấy cắt không phải lúc nào cũng tốt hơn

### Ưu tiên 2 — Bổ sung ảnh cho 4 bánh kem còn thiếu

Hiện CLIP **không thể** match nhóm này. Đây là nhóm khách tìm nhiều nhất (bánh
sinh nhật).

### Ưu tiên 3 — Thêm ảnh mỗi sản phẩm (nhiều góc)

Mỗi sản phẩm nên có 3–5 ảnh ở các góc/ánh sáng khác nhau, để embedding phủ được
nhiều biến thể. Hiện chỉ 2 sản phẩm có 2 ảnh.

### Ưu tiên 4 — Đặt ngưỡng từ chối

Với khoảng cách hai nhóm chỉ +0.103, **chưa nên** đặt ngưỡng tự tin. Nên:
- Hiển thị top-3 kèm **phần trăm giống** để khách tự chọn, thay vì chỉ trả 1 kết quả
- Ghi rõ "kết quả gần đúng" thay vì khẳng định đây là bánh khách muốn

### Hướng cải thiện model (nếu còn thời gian)

- Thử model lớn hơn: `ViT-L-14` (vector 768) — thường tốt hơn `ViT-B-32` rõ rệt
- Thử `SigLIP` — huấn luyện trên dữ liệu lớn hơn, nhạy với ảnh sản phẩm hơn
- **Nhưng phải sửa dữ liệu trước**, vì model tốt hơn vẫn bị ảnh có logo làm nhiễu

---

## 7. CÁCH TÁI LẬP KẾT QUẢ

```bash
cd backend
python scripts/collect_test_images.py      # tải bộ ảnh test (cần mạng)
python scripts/evaluate_clip_accuracy.py   # đo accuracy
```

Kết quả chi tiết lưu ở `backend/test_images/accuracy_report.json`.
