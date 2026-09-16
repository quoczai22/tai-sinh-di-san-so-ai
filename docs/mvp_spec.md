# TÁI SINH DI SẢN SỐ — MVP SPECIFICATION v6.1
## Generate-and-Curate · Sản phẩm: Áo dài Việt Nam

> **Tagline:** "Một cú bấm ra cả bộ thiết kế từ hoa văn gốm — bạn chọn cái ưng ý."

**Sửa đổi 06/09/2026 so với v6.0.** Bản này viết lại cho khớp kiến trúc đã dựng và
đã đo, không phải kiến trúc dự kiến. Bốn thay đổi lớn:

1. **Bỏ Creative Intensity khỏi giao diện người dùng.** Người dùng không còn chọn
   "sáng tạo ít hay nhiều". Bấm một nút, hệ thống sinh cả bộ, người dùng chọn ảnh.
2. **Generation Layer tách làm hai giai đoạn** — sinh hoa văn phẳng, rồi ghép lên
   áo dài. v6.0 gộp làm một và **không chạy được** (đo được ở mục 5.1).
3. **Bố cục hoa văn do hệ thống tự chọn**, không khai báo cố định.
4. **Bỏ pilot áo dài** (v6.0 mục 5.4) — dáng áo nay đến từ ảnh mẫu, không do
   SD1.5 vẽ, nên rủi ro đó không còn.

**Hệ quả về định vị — cần nói rõ với đội.** v6.0 đặt giá trị ở *"người dùng kiểm
soát và thấy được đánh đổi"*. Bỏ nút chọn thì luận điểm đó không còn. Giá trị mới
nằm ở **pipeline sinh bộ thiết kế đa dạng có đo lường + người curate** — xem mục 13.

---

## 1. BỐI CẢNH & VẤN ĐỀ

### 1.1. Vấn đề
Hoa văn gốm Bát Tràng hiện tồn tại dưới dạng hiện vật trưng bày hoặc ảnh tư liệu
tĩnh. Chưa có công cụ nào giúp người trẻ đưa hoa văn đó lên một sản phẩm mặc được
mà không phải tự thiết kế lại từ đầu.

Công cụ AI tạo ảnh phổ thông cho một nút "Generate" và một kết quả. Người dùng
phải tự thử đi thử lại bằng cảm tính, và **không có gì đảm bảo dáng áo dài đúng**
hay hoa văn còn liên quan tới hiện vật gốc.

### 1.2. Mục tiêu MVP
Chọn hiện vật → bấm một nút → nhận **một bộ thiết kế áo dài đa dạng** → chọn cái
ưng ý → nhận Design Passport ghi lại toàn bộ quá trình.

---

## 2. KIẾN TRÚC — HAI GIAI ĐOẠN SINH + MỘT LỚP ĐÁNH GIÁ

```text
┌──────────────────────────────────────────────────────────┐
│  GIAI ĐOẠN 1 — SINH HOA VĂN PHẲNG                         │
│                                                            │
│  ảnh gốm ─► tách nền (alpha / màu viền suy từ mép)         │
│          ─► Canny CHỈ GIỮ HOA VĂN (bỏ đường bao món đồ)    │
│          ─► SD1.5 + ControlNet, circular padding           │
│             (4 mức weight nội bộ: 0,85 / 0,65 / 0,45 / 0,25)│
│          ─► [biến thể 1] khớp bảng màu hiện vật gốc         │
│          ─► HOA VĂN LẶP LIỀN MẠCH                          │
└───────────────────────────┬──────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│  GIAI ĐOẠN 2 — ĐƯA LÊN ÁO DÀI                             │
│                                                            │
│  ─► chấm điểm 7 bố cục, chọn cái hợp nhất (chưa dùng)      │
│  ─► ghép tất định: mask mềm + displacement + shading       │
│  ─► lượt hoàn thiện img2img (denoise 0,40)                 │
│  ─► 4 THIẾT KẾ ÁO DÀI                                      │
└───────────────────────────┬──────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│  LỚP ĐÁNH GIÁ & MINH BẠCH                                 │
│  Visual Similarity · Design Passport · Audit Log           │
└──────────────────────────────────────────────────────────┘
```

**Vì sao phải tách hai giai đoạn.** v6.0 mục 5.2 đưa ảnh gốm vào ControlNet đồng
thời bảo prompt vẽ áo dài. Hai điều kiện xung đột về **hình học**: Canny nói "dáng
bình, cổ hẹp, đế tròn", prompt nói "tà dài, mặc ngoài quần". Đo ngày 05/09:

| Creative Intensity | weight | P(áo dài) |
|---|---:|---:|
| 1 — Nguyên bản | 0,85 | **0,000** |
| 2 — Gần nguyên bản | 0,65 | **0,000** |
| 3 — Cân bằng | 0,45 | 0,016 |
| 4 — Tự do | 0,25 | 1,000 |

**Ba trong bốn mức không sinh ra áo dài.** Không có giá trị weight nào hoà giải
được — chỉnh weight chỉ là chọn xem bên nào thắng. Tách giai đoạn gỡ hẳn xung đột.

---

## 3. PHẠM VI MVP CỐ ĐỊNH

| Hạng mục | Quyết định |
|---|---|
| Di sản | Gốm Bát Tràng, **6 hiện vật** |
| Sản phẩm đầu ra | Áo dài Việt Nam (duy nhất) |
| Nguồn tư liệu | Không có RAG/trích dẫn học thuật — mô tả do nhóm chịu trách nhiệm |
| Governance | Không có gate tiền kiểm |
| Fine-tuning | Không |
| Mobile / Chatbot / Payment / Auth | Không |

**KHÔNG làm:** ❌ RAG ❌ Vector DB ❌ Constraint Validator ❌ Taxonomy 8 nhãn
❌ Người dùng chọn mức sáng tạo ❌ Pilot áo dài (không còn cần)

---

## 4. HERITAGE DATASET

```json
{
  "heritage_id": "BT_Hac_XP",
  "name": "Bình gốm hoa lam công và sen",
  "image_path": "data/heritage/BT_Hac_XP.png",
  "image_source_url": null,
  "license": "unverified",
  "license_note": "Ảnh tự thu thập, chưa xác minh bản quyền. Chỉ dùng nội bộ MVP.",
  "conditioning_mode": "whole_object",
  "team_description": "Mô tả nội bộ do nhóm biên soạn, không phải trích dẫn học thuật."
}
```

### 4.1. `conditioning_mode` — chốt dùng `whole_object`

Đã cân nhắc hai hướng và **chọn `whole_object`** (06/09/2026):

| | `whole_object` (đã chọn) | `ornament_crop` |
|---|---|---|
| Pixel cạnh hoa văn | 20.092 | 31.535 |
| Seam | 12,6 / mốc 13,6 | 6,8 / mốc 8,8 |
| Số ảnh dùng được | **6/6** | 3/6 |
| Lát ra trông như | có bóng dáng vật chứa | vải in liên tục |

`ornament_crop` thắng mọi chỉ số kỹ thuật nhưng **chỉ 3/6 ảnh đủ 512px để cắt
1:1** — ba ảnh còn lại (137–324px) cắt rồi phóng to sẽ mờ, tệ hơn cả bóng vật chứa.
Chọn `whole_object` để cả 6 mẫu được xử lý như nhau.

**Giới hạn phải thừa nhận:** hoa văn sinh ra còn bóng mờ dáng món đồ ở mức weight
cao. Đã đo và xác định **không gỡ được bằng xử lý ảnh**: dáng đó không tồn tại dưới
dạng một đường viền để lọc (650 thành phần liên thông, lớn nhất chỉ trải 33% khung),
mà nổi lên từ chỗ hoa văn phân bố theo mặt cong của món đồ.

### 4.2. Tiêu chí tuyển ảnh — KHÔNG dùng độ phân giải

Bỏ tiêu chí "≥1024px cạnh ngắn nhất" của v6.0. Đo được nó **sai**:

```
HSBT_XP-300x300    300px   77% mốc   ✅ hoa văn sắc nét, dùng tốt
lo-hoa-gom         768px   49% mốc   ❌ ra ảnh chụp cái bình
binh-hoa-su-trang 1024px   72% mốc   (đạt tiêu chí cũ mà kém hơn ảnh 300px)
```

Ảnh 300×300 cho kết quả tốt hơn ảnh 1024px, vì món đồ phủ kín khung nên toàn bộ
512 pixel dành cho hoa văn.

**Tiêu chí đúng: số pixel cạnh hoa văn sau khi bỏ nền và bóc đường bao, ≥60% của
một ảnh mốc đã kiểm.** Đo bằng `controlnet.prepare()`, tự động, và đúng với thứ
pipeline thật sự dùng.

---

## 5. GIAI ĐOẠN 1 — SINH HOA VĂN

### 5.1. Bóc đường bao khỏi bản đồ cạnh
Canny trả về cả đường viền món đồ lẫn nét hoa văn. ControlNet không phân biệt được,
nên ở weight cao nó ép đầu ra thành hình cái bình. Co mask món đồ vào trong 14px
rồi nhân với bản đồ cạnh → chỉ còn hoa văn bề mặt.

### 5.2. Sinh tile lặp liền mạch — circular padding
Hoa văn sẽ được lát kín vùng in ở giai đoạn 2, nên **phải lặp liền mạch**. Đổi
`padding_mode` của các lớp Conv2d sang `circular`.

**Chỉ áp lên UNet và VAE. KHÔNG áp lên ControlNet** — đo được:

```
áp cả ControlNet    seam = 94,3   (mốc 4,3)   CÒN đường nối
chỉ UNet + VAE      seam = 12,6   (mốc 13,6)  LIỀN MẠCH
```

Áp lên ControlNet làm seam **tệ hơn 20 lần**. Kết quả cuối: mép trái–phải chênh 1,9
trong khi hai cột kề nhau bên trong ảnh chênh 2,0 — không còn đường nối nào.

### 5.3. Prompt

```text
"a flat decorative pattern inspired by {name_en}, featuring {team_description},
 {intensity_modifier},
 hand-painted ceramic enamel style, bold outline linework, asymmetric composition,
 seamless repeating pattern."
```

**Không nhắc áo dài** — giai đoạn 1 chỉ sinh hoa văn.

Negative prompt **cố định trong code, LLM không được đụng**:
```text
vase, pot, jar, vessel, bottle, ceramic object, 3d render, photograph,
person, mannequin, garment,
kaleidoscope, mandala, mirror symmetry, radial symmetry,
neon colors, oversaturated, blurry, low quality, watermark, text, distorted
```
Nhóm `vase…` là chốt chặn: bỏ ra thì ControlNet kéo đầu ra về hình cái bình.
Nhóm `kaleidoscope…` chặn hoa văn đối xứng gương, xa nét vẽ men lam bất đối xứng.

**Kiểm 77 token trước khi nạp model.** CLIP cắt ở đó và không báo lỗi; vượt thì
ném exception ngay thay vì chờ nạp model rồi mới hỏng.

### 5.4. Bốn mức weight — nội bộ, KHÔNG phải lựa chọn của người dùng

```
0,85  ·  0,65  ·  0,45  ·  0,25
```

Đây là **trục tạo đa dạng cho bộ kết quả**, không phải tham số người dùng chỉnh.
Người dùng bấm một nút và nhận cả bốn.

Bốn giá trị này là **hằng số trong mã nguồn** (`evaluation/variants.py`), không đọc
từ cấu hình và không nhận từ giao diện — xem hợp đồng ở mục 7.1.

**Cần giãn khoảng.** Đo trên 6 hiện vật, bốn mức hiện chỉ tách thành hai nhóm:

| | weight | Similarity TB |
|---|---:|---:|
| V1 | 0,85 | 0,770 |
| V2 | 0,65 | 0,767 |
| V3 | 0,45 | 0,711 |
| V4 | 0,25 | 0,713 |

V1≈V2 và V3≈V4. Đề xuất đổi sang **0,90 / 0,70 / 0,40 / 0,15** để bốn kết quả khác
nhau rõ hơn — cần đo lại sau khi đổi.

### 5.5. Bảng màu — biến thể 1 giữ nguyên màu hiện vật
Không ép màu qua prompt (không đáng tin: cùng ảnh men lam có thể ra tím, xanh lá,
nâu tuỳ seed). Thay vào đó **khớp thống kê LAB sau khi sinh**, tất định.

Bắt buộc loại viền letterbox trắng khỏi thống kê, nếu không màu bị kéo về trắng.

---

## 6. GIAI ĐOẠN 2 — ĐƯA LÊN ÁO DÀI

### 6.1. Ảnh áo dài mẫu
Sinh **một lần** rồi dùng lại cho mọi thiết kế. Nhờ vậy dáng áo luôn đúng và không
phụ thuộc việc SD1.5 có "biết" áo dài hay không — rủi ro mà v6.0 mục 12 xếp mức Cao
được gỡ bằng kiến trúc, không phải bằng prompt engineering.

Áo giữ nguyên giữa mọi biến thể, nên khác biệt giữa chúng đến từ **hoa văn**, không
phải từ việc SD vẽ cái áo khác đi.

### 6.2. Bố cục do hệ thống tự chọn

Bảy bố cục khai báo trong `data/garment/layouts.json`: thân trước · phủ toàn thân ·
băng gấu tà · vai và ngực · vai + gấu tà · dải dọc lệch phải · ô giữa ngực.

Toạ độ theo **tỉ lệ hộp bao vùng áo**, không phải của cả ảnh — đổi ảnh mẫu vẫn đúng.

**Cách chọn:** ghép thử cả 7 rồi chấm bằng CLIP (khớp *"áo dài thanh lịch, hoa văn
đặt đẹp"* trừ khớp *"áo rối, hoa văn đặt bừa"*). Tốn **2,0 giây** cho cả 7 — ít hơn
một lần chạy SD.

Trong một bộ, **không lặp bố cục**: mỗi biến thể lấy bố cục điểm cao nhất chưa dùng.
Không có luật này thì cả 4 kết quả đặt hoa văn cùng một chỗ.

Đã kiểm: 6 hiện vật cho 6 bộ bố trí khác nhau.

**Điểm số này là xếp hạng, không phải phán quyết.** Biên độ chỉ 0,032 giữa cao nhất
và thấp nhất — xu hướng mềm. Người dùng vẫn là người chọn.

### 6.3. Ghép ảnh — bốn bước

1. **Mask mềm bo góc** (chuẩn Lp, p=4) giao với vùng áo tách bằng HSV. Hoa văn
   không thể tràn ra ngoài áo, và không có mép cắt vuông vức.
2. **Displacement map** — lấy đạo hàm độ sáng vải làm bản đồ độ dốc, uốn hoa văn
   theo nếp gấp. Đây là biến dạng *hình học*.
3. **Shading map** — chuẩn hoá độ sáng vùng vải quanh 1,0, khuếch đại ×1,9, nhân
   lên hoa văn. Đây là *truyền sáng*, thứ displacement map không làm được. Thiếu
   bước này hoa văn phẳng lì và trông như đề can dán.
4. **Color grade** — hạ bão hoà 20% và cân bằng trắng **chỉ trong kênh a/b của
   LAB**. Dịch cả ba kênh RGB sẽ kéo luôn độ sáng về phía nền và hoa văn bạc trắng.

### 6.4. Lượt hoàn thiện img2img (denoise 0,40)
Ghép ảnh tất định không làm được ba việc: hoà hoa văn vào sợi vải, phá tính lặp máy
móc, tạo biến thiên tự nhiên ở nếp gấp. img2img ở denoise thấp làm cả ba.

```
0,28   vẫn thấy các khối xếp chồng
0,40   liền một dải, vải rủ tự nhiên     ← chọn
>0,45  SD bắt đầu vẽ lại hoạ tiết thành thứ khác
```

**Bước này đưa lại tính bất định vào giai đoạn 2** — seed phải ghi vào Audit Log.
Giữ cả bản ghép thô (`_aodai_raw.png`) để đối chiếu.

---

## 7. UI/UX — LUỒNG NGƯỜI DÙNG

```text
1. Chọn hiện vật (6 mẫu, có ảnh + tên)
2. Xem mô tả nội bộ của nhóm  (kèm ghi chú "không phải trích dẫn học thuật")
3. Bấm TẠO THIẾT KẾ                    ← một nút duy nhất
4. Đợi ~45 giây
5. Xem 4 thiết kế, mỗi cái kèm chỉ số Similarity
6. CHỌN cái ưng ý
7. Nhận Design Passport của thiết kế đã chọn
```

**Không còn bước chọn mức sáng tạo.** Người dùng không phải hiểu "Creative
Intensity" là gì trước khi thấy kết quả — họ chọn bằng mắt, trên kết quả thật.

### 7.1. Hợp đồng "một nút" — bắt buộc, dev không được lệch

Giao diện gọi **đúng một hàm** và **không truyền tham số tinh chỉnh nào**:

```python
generate_set(heritage_id: str, seed: int = 42) -> list[Design]   # LUÔN trả 4 phần tử
```

| Quy tắc | Lý do |
|---|---|
| UI **không** truyền `weight`, `palette`, `layout`, `polish_strength` | Bốn thứ này do bảng cố định ở mục 7.2 quyết định. Phơi ra UI là quay lại v6.0 |
| **Không** có thanh trượt, không có ô "mức sáng tạo", không có nút "sinh thêm 1 ảnh" | Người dùng chọn trên kết quả thật, không chọn trên khái niệm |
| Cả 4 biến thể sinh trong **cùng một lần nạp model** | Nạp model tốn 6 s/lần; nạp lại 4 lần biến ~45 s thành ~65 s |
| Một biến thể lỗi → vẫn trả những biến thể còn lại kèm ghi chú lỗi | Hỏng 1 ảnh không được làm hỏng cả bộ |
| Bấm lại nút khi đang chạy → bị chặn | Tránh hai lượt sinh chồng nhau trên 8 GB VRAM |

### 7.2. Bảng 4 biến thể — cố định trong `evaluation/variants.py`

| Biến thể | ControlNet weight | Bảng màu | Bố cục |
|---|---:|---|---|
| 1 | 0,85 | **khớp hiện vật gốc** | điểm cao nhất |
| 2 | 0,65 | tự do | cao nhất **chưa dùng** |
| 3 | 0,45 | tự do | cao nhất **chưa dùng** |
| 4 | 0,25 | tự do | cao nhất **chưa dùng** |

Biến thể 1 luôn là **bản trung thành nhất**: weight cao nhất và giữ nguyên bảng màu
men gốc. Ba biến thể sau nới dần cả hai trục. Nhờ vậy bộ kết quả luôn có ít nhất một
ảnh "gần hiện vật" để người dùng đối chiếu.

**Trạng thái giao diện:**

```text
IDLE ──bấm──► GENERATING ──xong──► REVIEW ──chọn──► CHOSEN
              (4 bước tiến độ)     (4 ảnh)          (Design Passport)
                                        └──── chọn lại được ────┘
```

`GENERATING` phải hiện tiến độ theo từng biến thể (1/4 … 4/4), không phải một vòng
xoay không rõ còn bao lâu — chờ ~45 giây mà không có mốc thì người dùng tưởng treo.

---

## 8. LỚP ĐÁNH GIÁ & MINH BẠCH

### 8.1. Visual Similarity
CLIP image-image, đo giữa **hoa văn sinh ra** và **hoa văn hiện vật** — cả hai ở
giai đoạn 1, trước khi ghép áo. Nhờ vậy chỉ số không bị nhiễu bởi bố cục hay lượt
hoàn thiện.

**Không có ngưỡng đạt/không đạt.** Chỉ hiển thị số kèm chú thích cố định.

### 8.2. Design Passport

```text
╔══════════════════════════════════════╗
║           DESIGN PASSPORT              ║
╠══════════════════════════════════════╣
║ HOA VĂN                                ║
║ BT_Hac_XP — Bình gốm hoa lam công sen  ║
║ (Mô tả nội bộ nhóm, không phải trích   ║
║  dẫn học thuật)                        ║
║                                        ║
║ THIẾT KẾ BẠN ĐÃ CHỌN                   ║
║ Biến thể 2 / 4                         ║
║ Bố cục: Dải thân trước                 ║
║ Bảng màu: tự do                        ║
║                                        ║
║ ĐỘ TƯƠNG ĐỒNG VỚI HOA VĂN GỐC          ║
║              76% (tham khảo)           ║
║ *Đo bằng CLIP giữa hoa văn sinh ra và  ║
║  hoa văn hiện vật. Không phải chứng    ║
║  nhận văn hoá, không có ngưỡng đạt.*   ║
║                                        ║
║ BẢNG MÀU HIỆN VẬT                      ║
║ ■ #99a1a8  ■ #ccd5d8  ■ #3f4551        ║
╚══════════════════════════════════════╝
```

### 8.3. Audit Log
Ghi **cả 4 biến thể** cho mỗi lần bấm nút, đánh dấu cái người dùng chọn:

```
heritage_id · variant_index · chosen (bool)
controlnet_weight · palette_mode · seed
layout · layout_score · layout_ranking (đủ 7 bố cục kèm điểm)
positive_prompt · negative_prompt
similarity · polish_strength
sd_model_id · controlnet_id · torch/diffusers version · gpu
duration_s · sha256_output
```

**`chosen` là dữ liệu quý nhất của dự án** — nó ghi lại con người thật đã thích cái
gì, và đó là thứ không mô hình nào tự sinh ra được.

**Cột minh bạch bắt buộc:** `aesthetic_impl`, `translator_mode` — ghi rõ khâu nào
đang là giả lập, để nhật ký không bị đọc nhầm là đã chạy đủ pipeline.

---

## 9. THỰC NGHIỆM

**Câu hỏi:** ControlNet weight ảnh hưởng thế nào tới độ trung thành của hoa văn, và
người dùng thường chọn mức nào?

**Thiết kế một biến số:** cùng hiện vật, cùng seed, cùng ảnh điều kiện — chỉ đổi
weight. Similarity đo ở giai đoạn 1 nên bố cục và lượt hoàn thiện không gây nhiễu.

**Số đo hiện có** (6 hiện vật × 4 mức, 06/09/2026):

| weight | Similarity TB | thấp | cao |
|---:|---:|---:|---:|
| 0,85 | 0,770 | 0,668 | 0,926 |
| 0,65 | 0,767 | 0,655 | 0,914 |
| 0,45 | 0,711 | 0,637 | 0,773 |
| 0,25 | 0,713 | 0,633 | 0,782 |

**Phần thứ hai — thống kê lựa chọn của người dùng.** Đây là thực nghiệm mới mà kiến
trúc curate mở ra: ghi lại `chosen` qua nhiều lượt dùng để biết người thật thích mức
biến tấu nào. Trình bày như **quan sát sơ bộ trên tập mẫu nhỏ**, không phải kết luận
thống kê.

---

## 10. TEST CASES

| # | Test | Kết quả kỳ vọng |
|---|---|---|
| 1 | Bấm nút một lần | Ra đúng 4 thiết kế, 4 bố cục KHÁC nhau |
| 2 | Cùng hiện vật + seed, chạy lại | Hoa văn giai đoạn 1 giống hệt; thiết kế cuối giống nếu cùng seed hoàn thiện |
| 3 | Kiểm tile liền mạch | Chênh lệch mép trái–phải ≈ chênh lệch hai cột kề nhau bên trong |
| 4 | Ngân sách token | Mọi hiện vật × 4 mức đều ≤ 75 token, fail thì dừng hẳn |
| 5 | Similarity bất thường | UI chỉ hiện số + chú thích, không gắn nhãn đạt/không đạt |
| 6 | `team_description` hiển thị ở đâu | Luôn kèm ghi chú "mô tả nội bộ, không phải trích dẫn học thuật" |
| 7 | Người dùng chọn ảnh | Audit Log ghi `chosen=true` đúng biến thể, 3 biến thể còn lại `false` |
| 8 | UI gọi `generate_set()` | Chỉ truyền `heritage_id` (+ `seed`); không truyền weight/palette/layout |
| 9 | Một biến thể ném exception | Vẫn trả 3 biến thể còn lại, Audit Log ghi biến thể lỗi |
| 10 | Bấm nút hai lần liên tiếp | Lần thứ hai bị chặn khi trạng thái là `GENERATING` |

---

## 11. HIỆU NĂNG ĐÃ ĐO

RTX 4060 Laptop 8GB, SD1.5 fp16, 512×512, 25 step:

```
Nạp model                     6 s   (một lần)
Sinh 1 hoa văn              5,6 s
Chấm 7 bố cục               2,0 s
Ghép ảnh                  <0,1 s
Lượt hoàn thiện           ~5 s
────────────────────────────────
Một bộ 4 thiết kế          ~45 s
Đỉnh VRAM                3,33 GB / 8 GB
```

Còn dư VRAM để nâng lên 768px hoặc sinh nhiều biến thể hơn.

---

## 12. RỦI RO & GIỚI HẠN

| Rủi ro | Mức | Ghi chú |
|---|---|---|
| Hoa văn còn bóng dáng vật chứa ở weight cao | Trung bình | Đã đo, **không gỡ được bằng xử lý ảnh** (mục 4.1). Chấp nhận có ý thức |
| Aesthetic Score chưa dùng được | Trung bình | Đang là proxy CLIP, dao động 8,5–8,9 ở mọi biến thể — **không phân biệt được**. Cần LAION-Aesthetics thật, hoặc bỏ khỏi hồ sơ |
| Bốn mức weight chỉ tách thành hai nhóm | Trung bình | Cần giãn sang 0,90/0,70/0,40/0,15 rồi đo lại (mục 5.4) |
| Mô tả hiện vật do LLM sinh, chưa ai rà | Trung bình | `reviewed_by_human` phải đặt `true` từng mục trước khi vào hồ sơ |
| Ảnh chưa xác minh bản quyền | Cao — với hồ sơ dự thi | `license: unverified` phải hiển thị trung thực, không được ghi "free" |
| Lượt hoàn thiện làm giai đoạn 2 mất tính tất định | Thấp | Seed đã ghi log; giữ cả bản ghép thô |
| Ảnh áo dài mẫu do SD sinh, bị cắt đầu | Thấp | Sinh lại với seed khác nếu cần |

---

## 13. ĐỊNH VỊ — ĐÃ ĐỔI, CẦN ĐỘI THỐNG NHẤT

**v6.0 định vị:** *"người dùng chọn mức trung thành, hệ thống đo đánh đổi"*. Bỏ nút
chọn thì luận điểm này **không còn đứng được** — phải thay, không được giữ nguyên
slide cũ.

**Định vị mới — Core Innovation Statement:**

> Chúng tôi đề xuất một pipeline hai giai đoạn đưa hoa văn gốm truyền thống lên
> trang phục hiện đại: giai đoạn một tách hoa văn khỏi hình dáng hiện vật rồi sinh
> một hoa văn lặp liền mạch; giai đoạn hai ghép hoa văn lên áo dài bằng phép ghép
> ảnh tất định, nên dáng trang phục luôn đúng thay vì phó mặc cho mô hình sinh ảnh.
> Với mỗi lần yêu cầu, hệ thống tự sinh một bộ thiết kế đa dạng — khác nhau về mức
> biến tấu, bảng màu và bố cục do chính hệ thống chấm điểm chọn — rồi để con người
> quyết định. Mỗi thiết kế đi kèm chỉ số tương đồng thị giác với hoa văn gốc và một
> Design Passport ghi lại đầy đủ tham số, cho phép tái lập và truy vết.

**One-line Pitch:**
> Tái sinh Di sản Số — một cú bấm biến hoa văn gốm Bát Tràng thành bộ thiết kế áo
> dài đương đại, có đo lường và truy vết được, để bạn chọn.

**Từ khoá:** GENERATE — MEASURE — CURATE

**Điều gì thật sự là đóng góp kỹ thuật** (nói được khi giám khảo hỏi sâu):

1. Tách hai giai đoạn — giải quyết xung đột hình học giữa conditioning và sản phẩm,
   có số đo P(áo dài) 0,000 → 1,000 chứng minh.
2. Conditioning chỉ trên hoa văn, bóc đường bao hiện vật.
3. Sinh tile liền mạch bằng circular padding, và phát hiện **không được áp lên
   ControlNet** (seam tệ hơn 20 lần).
4. Chọn bố cục tự động bằng chấm điểm, rẻ hơn một lần chạy SD.
5. Ghép ảnh có displacement + shading + color grade — dáng áo đảm bảo đúng.

**Câu trả lời chuẩn nếu giám khảo hỏi "trách nhiệm văn hoá nằm ở đâu?":**
> "Ở phiên bản MVP này chúng tôi tập trung vào bài toán kỹ thuật: đưa hoa văn di sản
> lên trang phục sao cho đúng dáng, đo được độ trung thành, và tái lập được. Việc
> gắn kết với tư liệu học thuật có trích dẫn nằm ngoài phạm vi 21 ngày, đã cân nhắc
> và loại bỏ có chủ đích. Chúng tôi ghi rõ điều đó trong hồ sơ thay vì tuyên bố quá
> mức: mọi mô tả hiện vật đều đánh dấu là mô tả nội bộ của nhóm, và mọi ảnh đều ghi
> `license: unverified` cho tới khi xác minh được."

---

## 14. CẤU TRÚC MÃ NGUỒN

```text
generation/
├── controlnet.py        tách nền · alpha mask · Canny chỉ giữ hoa văn
├── prompt_template.py   prompt giai đoạn 1 · kiểm 77 token
├── pattern.py           GIAI ĐOẠN 1 — 4 mức weight nội bộ
├── palette.py           khớp bảng màu hiện vật · trích màu chủ đạo
├── garment.py           GIAI ĐOẠN 2 — mask, displacement, shading, grade, polish
├── layout_select.py     chấm điểm 7 bố cục, chọn cái hợp nhất
└── stable_diffusion.py  wrapper SD1.5 + ControlNet · circular padding

evaluation/
└── variants.py          sinh bộ 4 thiết kế, ghi variants.csv

scripts/
└── 07_describe_heritage.py   LLM thị giác viết mô tả — CHẠY OFFLINE MỘT LẦN

data/
├── heritage/            6 ảnh hiện vật
├── garment/             ảnh áo dài mẫu + layouts.json
├── prompt_terms.json    mô tả tiếng Anh, ≤21 token
└── metadata.json        Heritage Dataset (mục 4)
```

**LLM chỉ chạy offline.** Pipeline sinh ảnh đọc file, không gọi API — nên cùng hiện
vật + seed luôn cho cùng kết quả ở giai đoạn 1.

---

## 15. VIỆC CÒN LẠI

| # | Việc | Ai |
|---|---|---|
| 1 | Rà 6 mô tả do LLM sinh, đặt `reviewed_by_human: true` | BA |
| 2 | Xác minh nguồn/giấy phép 6 ảnh, thay `unverified` | BA |
| 3 | `data/metadata.json` theo schema mục 4 | AI/Data |
| 4 | Giãn 4 mức weight, đo lại | AI/Data |
| 5 | Thay Aesthetic proxy bằng LAION, hoặc bỏ khỏi hồ sơ | AI/Data |
| 6 | Streamlit UI theo luồng mục 7 | DevOps |
| 7 | Audit Log ghi `chosen` khi người dùng chọn | DevOps |
| 8 | `generate_set()` theo hợp đồng mục 7.1 (trả 4, chịu lỗi từng biến thể) | AI/Data |
