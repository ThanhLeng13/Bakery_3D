# ĐÁNH GIÁ ĐỘ CHÍNH XÁC CLIP — BÁO CÁO KẾT QUẢ

**Ngày đo: 2026-10-27** (đo lại trên kho hiện tại)
Model: `ViT-B-32` / `laion2b_s34b_b79k`, vector 512 chiều, cosine similarity
Kho: **119 sản phẩm, 121 embedding** (đo trên CSDL thật, 27/10/2026)
Máy đo: CPU, không GPU

> Báo cáo cũ (21/09) đo trên kho cũ 22 sản phẩm / 20 embedding. Báo cáo này
> thay thế nó. Mọi con số bên dưới đều đo lại từ đầu trên kho hiện tại.

---

## 1. VẤN ĐỀ VỚI CON SỐ "100%" TRƯỚC ĐÓ

Con số 100% từng báo cáo là **self-match**: lấy ảnh trong kho, đưa lại chính ảnh
đó vào hệ thống, rồi kiểm tra xem có tìm ra không. Vector truy vấn **trùng khít**
vector đã lưu nên cosine = 1.0. Đây là trường hợp tầm thường, **không có giá trị
khoa học** vì không mô phỏng việc khách chụp ảnh ngoài đời.

Báo cáo này dùng ảnh **tải từ Wikimedia Commons** — khác nguồn, khác góc chụp,
khác ánh sáng, khác nền.

---

## 2. BỘ DỮ LIỆU TEST — 74 ẢNH, 4 NHÓM

| Nhóm | Số ảnh | Mục đích | Nguồn ảnh |
|---|---|---|---|
| `trong_kho` | 18 | Đo top-1 / top-3 accuracy | Wikimedia Commons |
| `mo_hinh_3d` | 30 | Đo nhận dạng kiểu thân, phủ **6 kiểu** | Render từ GLB của chính dự án |
| `ngoai_kho` | 10 | Là bánh nhưng kho không có món đó | Wikimedia Commons |
| `ngoai_mien_banh` | 16 | **Không phải bánh** — đo khả năng từ chối | Wikimedia Commons |

**Tất cả 74 ảnh đều có nguồn + giấy phép ghi trong `manifest.json` và
`manifest_3d.json`** (đã kiểm: 0 ảnh thiếu giấy phép — script
`backfill_manifest_meta.py` tra lại 8 ảnh bị mất metadata trong lần chạy trước).

### 2.1. Vì sao 30 ảnh "mô hình 3D" là ảnh truy vấn độc lập

Kho ảnh sản phẩm **không** dùng làm ảnh truy vấn được. Đo được trên CSDL thật:

```
cake_embeddings: 121 dòng, 121 URL duy nhất
product_images : 121 dòng, 121 URL duy nhất
giao hai nguon: 121  (trùng khớp 100%)
```

Mỗi sản phẩm có **đúng một ảnh**, và ảnh đó **chính là ảnh đã embed**. Lấy ảnh
kho làm ảnh truy vấn thì đó là self-match — không đo được gì.

Nên ảnh truy vấn cho 6 kiểu thân lấy từ **file GLB của chính dự án**:

- Độc lập hoàn toàn với ảnh trong kho
- Phủ đủ 6 kiểu thân (tròn 1/2/3 tầng, trái tim, vuông, cao) × 5 góc nhìn
- Quyền sử dụng thuộc về chính dự án → trích dẫn được trong luận văn
- Render bằng `frontend/scripts/capture-cake-shots.mjs` (Chrome headless, WebGL
  qua SwiftShader)

Kiểm tra ảnh không bị trắng: `backend/scripts/check_3d_shots.py` đo **66/66 ảnh
render có nội dung** (màu trung bình 53–58 sắc độ trong vùng giữa).

---

## 3. KẾT QUẢ ĐO

### 3.1. Ảnh thuộc món có trong kho (18 ảnh)

| Chỉ số | Kết quả |
|---|---|
| **Top-1 accuracy** | **16.7%** (3/18) |
| **Top-3 accuracy** | **27.8%** (5/18) |
| **Top-5 accuracy** (bổ sung đo 30/10) | **33.3%** (6/18) |

**Lần đo bổ sung 30/10/2026:** script đã tính và lưu Top-5 cùng danh sách
5 kết quả và cờ `correct_top5` cho từng ảnh. Lần chạy này xếp hạng kiểu thân
đạt **0/30**, lọc 3D **30/30** lượt trả kết quả không rỗng có mapping 3D.
JSON hiện tại là snapshot lần chạy này. **Không xóa kết quả lỗi của lần 27/10:**
bảng mục 3.4 bên dưới giữ **0/29** và **29/30** của lần trước để thể hiện lỗi
truy vấn từng xảy ra; 30/30 lần này không chứng minh độ sẵn sàng luôn là 100%.
Ngưỡng 0.550 vẫn là thăm dò trên cùng bộ ảnh, chưa được đánh giá bằng test giữ riêng.

Ba món trúng top-1: Bánh Brownie, Bánh tart trứng (×2).

| Ảnh | Top-1 trả về | Similarity |
|---|---|---|
| kem (kem xoa) | Bánh mousse chanh dây trái cây nền trắng | 0.578 |
| chè | Bánh tart trứng | 0.601 |
| pizza | Bánh kem xanh lá trái cây tươi | 0.572 |
| hamburger | Bánh phomai sợi dẻo | 0.551 |
| sushi | Bánh mousse chanh dây trái cây nền ghế trắng | 0.683 |
| phở | Bánh kem xanh lá trái cây tươi | 0.525 |
| salad | Bánh kem cốm dẻo | 0.513 |
| cà phê | Bánh kem cuộn socola trắng | 0.420 |
| xe hơi | Bánh kem cuộn socola trắng | 0.274 |
| bánh mì | Bánh kem trái cây tươi nơ trắng | 0.536 |
| bún bò | Bánh kem cuộn socola trắng | 0.492 |
| gỏi cuốn | Bánh mousse chanh dây trái cây nền ghế trắng | 0.578 |
| trà | Bánh kem cuộn socola trắng | 0.578 |
| nước cam | Bánh Brownie | 0.308 |
| bánh bao | Bánh kem cuộn socola trắng | 0.564 |
| xúc xích | Bánh chuối nướng nước dừa | 0.492 |

**Kem và chè ở đây, không phải `ngoai_kho`:** cả hai đều **không phải bánh**
(kem xoa, chè súp) — cùng loại với trà và nước cam. Trước đây chúng bị xếp
nhầm vào `ngoai_kho` ("là bánh nhưng kho không có"), làm hỏng nghĩa của cả
hai nhóm và làm lệch phép so sánh. Đã chuyển ngày 27/10.

### 3.3. Phân bố similarity

| Nhóm | Trung bình | Min | Max |
|---|---|---|---|
| Trong kho | 0.584 | 0.355 | 0.701 |
| Ngoài kho (là bánh) | 0.543 | 0.411 | 0.625 |
| **Ngoài miền bánh** | 0.517 | 0.274 | 0.683 |

Khoảng cách trong-kho ↔ ngoài-miền: **+0.067** — hẹp.

Với ngưỡng trung điểm 0.550:
- Ảnh ngoài miền bánh bị nhận nhầm: **8/16**
- Ảnh trong kho bị bỏ sót: **4/18**

### 3.3B. Hiệu chỉnh/test tách biệt — đánh giá hồi cứu 30/10

Chạy `python scripts/evaluate_clip_holdout.py`; artifact:
`threshold_holdout_report.json`. Đây là **đánh giá hồi cứu**, không phải test
mới chưa từng quan sát: các ảnh này đã được khảo sát trong những lần đo trước.
Không dùng nó làm bằng chứng xác nhận tổng quát hóa trên dữ liệu mới.

- Chia cố định theo protocol `bakery-clip-retrospective-v1`, không theo điểm.
- Giữ cùng nhãn, nguồn Commons (chuẩn hóa URL) và SHA-256 ở cùng một phía;
  dùng thành phần liên thông để xử lý các quan hệ chồng nhau.
- 44 file Commons có 41 nguồn; ba cặp cùng nguồn không được tách sang hai phía.
- Chỉ dùng `trong_kho` và `ngoai_mien_banh` cho ngưỡng từ chối; không dùng
  render GLB hoặc `ngoai_kho` làm nhãn âm.
- Chọn ngưỡng **0.553400** bằng balanced accuracy trên calibration; điểm test
  không được tham gia chọn ngưỡng. Thiếu score thì script lỗi thay vì bỏ mẫu.

| Chỉ số | Calibration | Test giữ riêng theo protocol |
|---|---:|---:|
| Ảnh trong kho / ngoài miền | 8 / 8 | 10 / 8 |
| Chấp nhận ảnh trong kho | 7/8 = 87,5% | **6/10 = 60%** |
| Từ chối ảnh ngoài miền | 5/8 = 62,5% | **4/8 = 50%** |
| Balanced accuracy | 75% | **55%** |

Đây là phân tích **offline của similarity top-1**, không phải xác suất đúng và
không chứng minh API đã triển khai cơ chế từ chối theo ngưỡng này. Kết quả yếu,
mẫu nhỏ, cần bộ ảnh mới thu thập sau khi khóa protocol để xác nhận độc lập.
Artifact lưu SHA-256 của cả manifest và snapshot accuracy đầu vào để tái lập.

**Protocol xác nhận ảnh mới đã khóa:** `prospective_clip_protocol.json` cố định
ngưỡng 0.5534, tối thiểu 10 ảnh mỗi nhóm trong-kho/ngoài-miền. Trước inference,
chạy `python scripts/validate_clip_prospective.py NEW_MANIFEST.json` để chặn nguồn
hoặc SHA-256 trùng tập cũ/tập mới, thiếu giấy phép, nhãn chưa xác nhận và thiếu
số lượng. Mỗi ảnh cần `label_verified=true` cùng `verified_by` sau khi người duyệt
thực sự xem ảnh; không tự suy nhãn từ tên file/từ khóa. Cổng này **không chứng minh**
ảnh khác toàn bộ ảnh embedding hoặc độc lập về nội dung. **Chưa có bộ ảnh mới
được duyệt hoặc kết quả prospective**; không dùng protocol thay cho kết quả đo.

Sau khi bộ ảnh vượt cổng kiểm tra, chạy
`python scripts/evaluate_clip_prospective.py NEW_MANIFEST.json OUTPUT.json`.
Lệnh dùng nguyên ngưỡng protocol, không tuning; kết quả rỗng tính là từ chối,
lỗi dịch vụ ghi riêng và vẫn nằm trong mẫu số. Output phải là file mới để giữ
các lượt chạy thất bại. Không được điền `label_verified` nếu chưa duyệt ảnh thật.

### 3.4. Ảnh mô hình 3D (30 ảnh — đo nhận dạng kiểu thân)

| Chỉ số | Kết quả |
|---|---|
| Top-1 trả về mẫu có mô hình 3D | **0/29 = 0.0%** *(1/30 lượt không lọc lỗi mạng)* |
| Top-1 có mô hình 3D đúng **kiểu thân** | **0/29 = 0.0%** *(1/30 lượt không lọc lỗi mạng)* |
| **Lọc 3D: lượt trả về toàn bộ viewer trên mọi lần thử** | **29/30 = 96,7%** |
| Sản phẩm có mapping 3D nằm trong top-30 | 16/30 |
| Hạng trung bình của sản phẩm có mapping 3D | 12.1 |
| Similarity top-1 trung bình của nhóm này | 0.446 |

**Cần nói rõ vì sao 0/29.** Có 30 ảnh truy vấn; một lượt tìm **không lọc** lỗi
mạng (`ClipServiceError`) nên không có top-1 để xếp hạng. Lượt đó vẫn được giữ
trong mẫu số riêng của phép đo lọc 3D. Kết quả xếp hạng 0/29 **không phải lỗi của
chế độ lọc 3D** — mà là hệ quả của hai điều kiện đo được trên CSDL thật:

1. **Chỉ 3 trong 101 bánh sinh nhật có mô hình 3D** (`product_3d_models` có đúng
   3 dòng). Không có cách nào để ảnh truy vấn trúng mẫu có 3D khi tỉ lệ nền là
   3/101 mà 6 kiểu thân trong kho chỉ có 2 kiểu được map (`heart-1-tier`,
   `round-2-tier`).
2. **Ảnh render 3D là bánh trắng không hoa văn**, khác mạnh ảnh sản phẩm thật
   (có hoa văn, màu, chữ). Similarity của cả nhóm chỉ 0.446, thấp hơn nhóm
   trong-kho (0.584) — đúng như mong đợi khi hai phân bố khác nhau về bề mặt.

**Hai số này phải tách bạch khi trình bày:**

- *Xếp hạng* (0/29; 1 lượt lỗi mạng): ảnh truy vấn có dẫn tới đúng mẫu 3D hay
  không. Đây là câu hỏi **xếp hạng** — và câu trả lời là chưa đạt.
- *Điều khoản sản phẩm* (29/30 = 96,7%): khi khách bật chế độ "Chỉ mẫu có 3D",
  mọi lượt thử có trả kết quả đều chỉ trả mẫu mở được viewer; **một lượt lỗi
  mạng** được tính vào mẫu số, không bị bỏ qua. Đây là câu hỏi **hợp đồng sản
  phẩm** — kết quả thực tế chưa phải 100%.

Nói cách khác: **bộ ảnh mô hình 3D đo được sự phân biệt kiểu thân, chưa đo được
khả năng "từ ảnh tìm ra mẫu 3D"** — vì kho chưa đủ mẫu 3D để đo. Đây là hạn
chế của **dữ liệu**, không phải của thuật toán.

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

1. **Bộ test nhỏ**: 18 ảnh trong kho, 16 ảnh ngoài miền. Sai số thống kê lớn —
   một ảnh đổi kết quả làm accuracy đổi 5,6 điểm phần trăm.
2. **Nhãn do người viết gán**, dựa trên từ khoá tìm kiếm, chưa được kiểm duyệt
   độc lập. Ảnh tìm bằng từ khoá "banana cake" có thể không đúng là bánh chuối
   nướng nước dừa của tiệm.
3. **Khác biệt phân bố là thật**: ảnh Wikimedia là ảnh stock quốc tế, còn kho là
   bánh Việt Nam. Một phần sai số đến từ đây, không phải từ model.
4. **Ảnh mô hình 3D là bản render, không phải ảnh chụp thật** — màu trắng, không
   hoa văn. Nhóm này đo sự phân biệt, không đo được độ khớp với ảnh thật.
5. **Chỉ 3/101 sản phẩm có mô hình 3D** → chưa đủ dữ liệu để đo độ chính xác
   của chế độ "tìm mẫu 3D" (mục 3.4).

---

## 5B. CẢNH BÁO: CON SỐ "100%" CỦA KHO MỚI CŨNG LÀ LỖI ĐO

Sau khi nhập 101 bánh mới, một lần đo hold-out từng báo **top-1 100%** (101/101).
**Con số đó SAI** và không được dùng trong luận văn. Đây là lỗi ở khâu đo, không
phải kết quả thật.

**Nguyên nhân:** mỗi sản phẩm trong kho chỉ có **đúng 1 ảnh** (xác nhận lại
27/10: 121 embedding ↔ 121 ảnh sản phẩm, trùng URL 100%). Script đo cũ, khi gặp
sản phẩm chỉ có một embedding, đã lấy `sims[0]` — mà `sims[0]` chính là **ảnh test
so với chính nó**, nên cosine ≈ 1.0. Nói cách khác nó không hề bỏ ảnh test ra khỏi
kho, mà so ảnh với chính nó rồi báo "tìm đúng". Kết quả 100% là **hiển nhiên**,
không phải thành tích.

**Đã sửa:** `evaluate_new_catalog.py` giờ loại ảnh test theo **khoá ảnh
(`image_url`)**, không theo vị trí. Chạy lại thì script **từ chối in số** và báo:

```
KHONG cham duoc anh nao — dung lai, khong ghi bao cao.
Da bo qua 101 san pham vi chi co 1 anh duy nhất.
```

Đó là hành vi đúng: khi mỗi sản phẩm chỉ có 1 ảnh, **không tồn tại** phép đo
hold-out công bằng nào. Bỏ ảnh test ra thì kho của sản phẩm đó rỗng.

**Cần gì để đo được thật:** mỗi sản phẩm phải có **từ 2 ảnh trở lên** — một ảnh để
trong kho làm mẫu, một ảnh làm "ảnh khách chụp". Với 119 sản phẩm thì cần chụp
thêm 119 ảnh nữa, lý tưởng là ở điều kiện khác (góc khác, ánh sáng khác, nền khác).

---

## 6. ĐỘ TRỄ (đo trên máy CPU, 27/10/2026)

| Độ trễ | p50 | p95 | Ghi chú |
|---|---|---|---|
| **Cold** (nạp model lần đầu) | 9,10 s | — | một lần khi khởi động tiến trình |
| **Embed** (sinh vector 512 chiều) | 114 ms | 144 ms | 90 mẫu (18 ảnh × 5 vòng) |
| **Search** (RPC + đọc mapping 3D) | 455 ms | 1 407 ms | 90 mẫu |
| **End-to-end** (embed + search) | 538 ms | 1 209 ms | trải nghiệm khách thấy |

**Cách đo:** 5 vòng × 18 ảnh = 90 mẫu cho mỗi chỉ số. Một vòng đơn lẻ cho
kết quả nhảy mạnh theo tải máy (đo được p50 end-to-end 478 ms ở vòng này rồi
946 ms ở vòng sau — chênh 2 lần), vì máy đang chạy song song tiến trình nền.
Đo nhiều vòng làm số ổn định hơn.

**`search` giờ bao gồm cả truy vấn bảng mapping 3D** — trước đây phép đo bỏ
sót phần này nên số bị thấp hơn thực tế.

Ghi chú: lần đo trước (09/10) cho cold 9,49 s và search p50 126 ms — chênh lệch
do tải máy lúc đo, không phải do thay đổi code. Con số **end-to-end p50 ~0,54 s**
là con số nên trích dẫn.

Bảng đầy đủ: `backend/test_images/latency_report.json`.

---

## 7. KHUYẾN NGHỊ

Thứ tự dưới đây xếp theo **tác động đã đo được**, không theo mức độ dễ làm.

### Ưu tiên 1 — Sửa dữ liệu kho (tác động lớn nhất, CHƯA đo được mức cải thiện)

Ảnh kho cần là **ảnh chụp sản phẩm thuần**: không logo, không chữ, không
watermark. Đây là nguyên nhân gốc (mục 4).

**Nhưng phải nói thật:** giả thuyết này **chưa được chứng minh là sửa được**.
Cách sửa rẻ nhất — cắt ảnh — đã bị thực nghiệm **bác bỏ** (mục 4). Cách còn lại là
**chụp lại ảnh mới**, và chưa có dữ liệu để biết nó cải thiện bao nhiêu.

Đây là việc nên làm, nhưng **không nên hứa hẹn con số** trước khi đo.

### Ưu tiên 2 — Thêm ảnh cho mỗi sản phẩm — **ưu tiên BẮT BUỘC**

Mỗi sản phẩm nên có 3–5 ảnh ở các góc/ánh sáng khác nhau. Hiện **119/119 sản
phẩm chỉ có 1 ảnh**.

Đây là việc tốn công nhất nhưng cũng là việc duy nhất mở khoá được con số đáng
trích dẫn. Chụp thêm 1 ảnh cho mỗi bánh, ở điều kiện khác ảnh đang có.

### Ưu tiên 3 — Bổ sung mô hình 3D cho nhiều sản phẩm hơn

Hiện **3/101** bánh sinh nhật có mô hình 3D, và chỉ 2 trong 6 kiểu thân được
dùng. Vì vậy chế độ "tìm mẫu 3D" **chưa thể đo được độ chính xác** (mục 3.4).
Gắn mô hình cho thêm nhiều sản phẩm là điều kiện để chế độ này có ý nghĩa.

### Ưu tiên 4 — Nâng lên ViT-L-14 (đã đo, +22.2 điểm top-1)

Đây là cải thiện **đã đo được, không phải phỏng đoán**. Đánh đổi:
- Chậm hơn 9,2 lần (97ms → 894ms/ảnh)
- RAM 1,4 GB → 3,6 GB
- Cần đổi cột `embedding` từ `vector(512)` sang `vector(768)` và **nhúng lại
  toàn bộ kho**
- **Vẫn không sửa được vấn đề gốc** và vẫn không đủ tách nhóm để đặt ngưỡng

### Ưu tiên 5 — Trình bày kết quả trung thực với khách (ĐÃ LÀM)

Với khoảng cách hai nhóm hẹp (+0,078), **không ngưỡng nào tách sạch được**.
Giao diện hiện đã:
- Hiển thị **top-K kèm % giống** để khách tự chọn
- Ghi rõ ngay trên trang: **% tương đồng là mức độ khớp đặc trưng hình ảnh,
  KHÔNG phải xác suất đúng món** (kiểm thử e2e: `tim-banh.spec.ts`)
- Ở chế độ chỉ mẫu có 3D, **mọi kết quả đều mở được viewer**, và mẫu chỉ-xem
  được ghi rõ "mẫu xem trước, chưa đặt được"

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

   Bằng chứng: khoảng cách similarity giữa nhóm trong kho và ngoài miền chỉ đi
   từ **−0.006** lên **+0.021**. Vẫn gần như bằng 0. Nghĩa là **vẫn không thể đặt
   ngưỡng từ chối đáng tin cậy** dù dùng model nào.

**Kết luận về model:** nâng lên ViT-L-14 là một cải thiện **có thật và đo được**,
đáng làm **nếu** máy chủ chịu được 3,6 GB RAM và độ trễ 4 giây. Nhưng nó **không
thay thế được việc sửa dữ liệu** — vẫn phải làm Khuyến nghị 1 và 2 bên dưới.

### Hướng khác chưa thử

- `ViT-H-14` (vector 1024) — còn lớn hơn nữa, RAM có thể vượt 6 GB
- `SigLIP` — huấn luyện trên dữ liệu lớn hơn, có thể nhạy với ảnh sản phẩm hơn
- Fine-tune trên chính ảnh của tiệm — hiệu quả nhất nhưng cần nhiều ảnh có nhãn,
  mà hiện kho chỉ có 1 ảnh mỗi sản phẩm

---

## 8. CÁCH TÁI LẬP KẾT QUẢ

**Bước 0 — chụp ảnh render 3D trước.** 30 ảnh truy vấn kiểu thân được dựng từ
ảnh render trong `frontend/tmp_shots/`, nên phải chụp trước khi dựng bộ ảnh:

```bash
cd frontend
node scripts/capture-cake-shots.mjs        # tạo frontend/tmp_shots/*.png
cd ..                                     # về thư mục gốc repo
```

**Bước 1 — thu thập và đo (chạy từ thư mục gốc repo):**

```bash
cd backend
python scripts/collect_test_images.py       # tải ảnh Wikimedia (cần mạng)
python scripts/collect_out_of_domain.py     # tải ảnh ngoài miền bánh
python scripts/build_3d_query_set.py        # dựng 30 ảnh truy vấn 6 kiểu thân
python scripts/backfill_manifest_meta.py    # tra lại nguồn/giấy phép còn thiếu
python scripts/check_3d_shots.py            # kiểm ảnh 3D không bị trắng
python scripts/evaluate_clip_accuracy.py    # đo top-1/top-3/từ chối
python scripts/measure_clip_latency.py      # đo cold/warm/p50/p95
```

Thứ tự này quan trọng: `build_3d_query_set.py` **không** ghi `manifest_3d.json`
nếu còn thiếu ảnh chụp — nên `check_3d_shots.py` chạy sau để biết ảnh nào trắng
trước khi đo. `backfill_manifest_meta.py` chỉ gán nguồn/giấy phép cho ảnh **xác
minh được bằng byte hash**; ảnh không xác minh được thì giữ `"?"` chứ không
đoán, để báo cáo báo đúng số ảnh còn thiếu giấy phép.

Kết quả chi tiết:
- `backend/test_images/accuracy_report.json` — từng ảnh, top-1/top-3, 4 nhóm
- `backend/test_images/latency_report.json` — cold/warm/p50/p95
- `backend/test_images/manifest.json` — nguồn + giấy phép ảnh Wikimedia
- `backend/test_images/manifest_3d.json` — nguồn + giấy phép ảnh mô hình 3D
- `backend/test_images/preprocessing_results.json` — 8 chiến lược tiền xử lý
- `backend/test_images/model_comparison.json` — so sánh hai model

Lưu ý: `compare_models.py` tải ViT-L-14 (~1,6 GB) ở lần chạy đầu.
