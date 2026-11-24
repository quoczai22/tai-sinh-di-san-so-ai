# Kế hoạch cải tiến: Tái Sinh Di Sản Số

- **Ngày lập:** 18/11/2026
- **Hạn nộp minh chứng:** hết ngày 25/11/2026
- **Trạng thái repo khi lập:** nhánh `nhanh_Doan`, commit `fcbcce8` ("final fix"), không có thay đổi chưa commit.
- **Mục tiêu:** đáp ứng đủ ba yêu cầu cải tiến của ban tổ chức, có link để ban tổ chức thử nghiệm, và cải thiện việc giữ chính xác họa tiết gốc (ưu tiên của nhóm).

Tài liệu viết ngắn. Mỗi thuật ngữ được giải thích ở lần đầu xuất hiện. Con số nào chưa đo thì ghi rõ "ước lượng".

---

## 0. Tóm tắt

Ban tổ chức yêu cầu ba việc. Mỗi việc có phần đã sửa được ngay trong code và phần cần người thật.

| Yêu cầu | Việc chính | Minh chứng nộp |
|---|---|---|
| 1. Đánh giá thiết kế cuối | Chỉ số đo trên ảnh áo cuối, quy tắc loại và thử lại, người am hiểu xem xét | Bộ ảnh (đầu vào, hoa văn, áo cuối), phiếu nhận xét, ví dụ bị loại hoặc sửa |
| 2. Đối chứng có kiểm soát, nhiều seed | Giữ cố định mọi thứ trừ một yếu tố, 5 seed, chấm mù | CSV cấu hình, bảng điểm người chấm, thống kê dao động |
| 3. Bản quyền, nguồn gốc, truy vết | Danh mục nguồn và giấy phép, Design Passport có phiên bản, nhãn AI | Danh mục nguồn, Passport có bước nguồn đến thành phẩm |
| Link thử nghiệm | Giao diện tĩnh luôn chạy, sinh ảnh trực tiếp qua đường hầm về máy GPU | Link và hướng dẫn một trang |

**Điều tôi cần bạn xác nhận trước khi làm (có ở các mục sau):**

1. Lịch chung kết. Bản `CLAUDE.md` đầu phiên làm việc ghi vòng chung kết 20 đến 22/11, sớm hơn hạn 25/11. Bản `CLAUDE.md` hiện trên đĩa không còn dòng này.
2. Có đồng ý đặt ngưỡng loại ảnh cho lỗi kỹ thuật (mục 3.3) không.
3. Có dùng lại mã đã viết trước đây (bản sao lưu, mục 6.3) hay viết lại gọn hơn.
4. Có làm nhánh giữ chính xác họa tiết (mục 6) hay chỉ đo và báo cáo giới hạn trên pipeline hiện tại.
5. Môi trường: `CLAUDE.md` yêu cầu `uv` và `pyproject.toml`, repo đang dùng `requirements.txt` và `scripts/01_setup_env.ps1`. Cần chọn một.

---

## 1. Đối chiếu yêu cầu của ban tổ chức

### Yêu cầu 1: đánh giá chất lượng thiết kế cuối

- **Vấn đề ban tổ chức nêu:** sau img2img toàn ảnh, dáng áo và hoa văn gốc có thể bị biến dạng; CLIP chưa phản ánh đủ sự phù hợp văn hóa.
- **Cần có:** kiểm tra độ giữ họa tiết và hình dáng áo sau xuất; tiêu chí loại hoặc thử lại; người am hiểu di sản và thiết kế xem xét mẫu trước khi giới thiệu.
- **Minh chứng:** bộ ảnh đầu vào, hoa văn, áo cuối, có phiếu nhận xét và ví dụ bị loại hoặc sửa.

### Yêu cầu 2: đối chứng có kiểm soát, nhiều seed

- **Vấn đề:** một seed và đổi nhiều tham số cùng lúc thì không quy được ảnh hưởng cho từng phương pháp.
- **Cần có:** giữ cố định prompt và bảng màu khi đổi riêng ControlNet hoặc bước ghép; nhiều seed trên cùng hiện vật; đánh giá mù theo tiêu chí rõ.
- **Minh chứng:** CSV cấu hình, bảng điểm từ người đánh giá, thống kê mức dao động.

### Yêu cầu 3: bản quyền, nguồn gốc, truy vết

- **Vấn đề:** hồ sơ có hiện vật chưa điền URL; Design Passport chưa chứng minh theo dõi đủ sau khi sửa tay.
- **Cần có:** nguồn và quyền sử dụng sáu hiện vật, cách ghi công; lịch sử các bước sửa thủ công; nhãn nội dung do AI hỗ trợ tạo.
- **Minh chứng:** danh mục nguồn và giấy phép; Design Passport có phiên bản từ nguồn đến thành phẩm.

---

## 2. Hiện trạng (đã kiểm tra trong code, commit `fcbcce8`)

| Quan sát | Vị trí |
|---|---|
| Bước hoàn thiện ("polish", img2img chạy sau khi ghép hoa văn lên áo) chạy trên cả ảnh, không có mặt nạ, độ nhiễu 0,40. Chính chú thích trong hàm ghi vùng an toàn là 0,25 đến 0,35 và trên 0,45 thì họa tiết biến dạng. | `generation/garment.py:270`, `evaluation/variants.py:40` |
| Similarity (độ giống CLIP) đo giữa ảnh gốm và hoa văn phẳng, không đo trên áo cuối. Cột CSV tên `similarity_pattern_vs_ceramic`. | `evaluation/variants.py:132`, `generation/streamlit_runner.py:65` |
| Điểm thẩm mỹ là proxy CLIP so với 4 câu mô tả, không phải bộ dự đoán LAION. CSV ghi `clip_proxy_NOT_laion`. Cả 24 dòng nằm trong khoảng 7,68 đến 8,48 nên gần như không phân biệt được ảnh. | `evaluation/intensity_sweep.py`, `evaluation/variants.csv` |
| Bốn biến thể khác nhau cùng lúc ở trọng số ControlNet, bảng màu, bố cục (do CLIP tự chọn) và cụm từ trong prompt. Ở 5 trong 6 hiện vật, Similarity không giảm đều theo 4 mức. | `evaluation/variants.py:47`, `evaluation/variants.csv` |
| Chỉ một seed (42) cho cả sinh hoa văn và polish. | `evaluation/variants.py:39`, `generation/streamlit_runner.py:11` |
| Không có bước kiểm tra nào sau polish, ảnh nào cũng được trả cho người dùng. | `generation/streamlit_runner.py` |
| Hai file metadata lệch nhau: file code đọc (`data/heritage/metadata.json`) để URL trống cho cả 6 mục; file `data/metadata.json` có URL nhưng không được dùng. | `streamlit_ui/heritage_data.py:19` |
| Cả 6 ảnh gốc lấy từ trang bán hàng (4 từ `fullhome-decor.com`, 1 từ `battrangceramica.com.vn`, 1 từ `xuonggomsuviet.vn`), giấy phép đều `unverified`. | `data/metadata.json` |
| `items.json` ghi nguồn "Bảo tàng Lịch sử Quốc gia" và niên hiệu cho chính các ảnh sản phẩm đó, không có căn cứ trong repo. Không file mã nào đọc `items.json`. | `data/heritage/items.json` |
| `team_description` của mục sen mực trùng gần nguyên văn một dòng trên trang sản phẩm của cửa hàng (tôi mới mở 1 trong 6 trang để kiểm tra). | `data/heritage/metadata.json` |
| 3 trong 6 ảnh có cạnh ngắn dưới 1024px (300, 600, 324), trái ràng buộc cứng của dự án. | `data/heritage/` |
| Audit log chỉ ghi bắt đầu, xong, lỗi theo `job_id`; không ghi seed, prompt, tham số, mã băm. | `api/main.py`, `api/audit.py` |
| Design Passport trên web chỉ hiện tên, Similarity, tên biến thể, bố cục. Không có seed, mã băm, nhãn AI, nguồn ảnh. | `web_ui/assets/js/ui/passport.js` |
| Chưa có `docs/ai_disclosure.md` dù chú thích trong code ghi cần có (safety checker đang tắt). | `generation/stable_diffusion.py:75` |
| Hàm `make_template` gọi `PANEL_FILE` và `DEFAULT_PANEL` chưa định nghĩa, sẽ lỗi `NameError`. | `generation/garment.py:315` |
| Giao diện gọi API ở `127.0.0.1:8000`; khi API không có thì danh mục hiện vật trống. Thẻ biến thể hiện số Similarity viết cứng (88,4%, 76,2%...). | `web_ui/assets/js/config.js`, `ui/curate.js:8` |
| API chạy một job GPU một lúc (người thứ hai nhận lỗi 409), job lưu trong bộ nhớ, không có mã truy cập hay giới hạn tần suất. | `api/main.py:33`, `:108` |

---

## 3. Yêu cầu 1: kiểm tra thiết kế cuối

### 3.1. Sửa polish: chỉ tác động vùng áo **[P0]**

1. Thêm `polish_masked()` trong `generation/garment.py`: dùng inpaint của SD 1.5 với mặt nạ vùng áo (`garment_mask()` tính trên ảnh áo trắng), độ nhiễu mặc định 0,30.
2. Sau khi sinh, ghép lại ở mức pixel: `ảnh cuối = polish × mặt nạ mềm + ảnh ghép thô × (1 − mặt nạ mềm)`. Bắt buộc vì bộ mã hóa ảnh (VAE) làm đổi nhẹ cả vùng ngoài mặt nạ.
3. Nếu hoa văn vẫn bị vẽ lại: thêm ControlNet Canny lấy từ chính ảnh ghép thô để khóa nét (dùng lại model Canny đã tải; VRAM đỉnh hiện 3,33 GB nên còn dư).
4. Đưa độ nhiễu polish về một chỗ cấu hình dùng chung cho `variants.py` và `streamlit_runner.py`.

**Xong khi:** pixel ngoài mặt nạ của ảnh cuối trùng ảnh ghép thô (sai khác bằng 0).

### 3.2. Bốn chỉ số trên áo cuối **[P0]**

Tạo `evaluation/final_metrics.py`. Đầu vào: ảnh gốm, hoa văn, áo ghép thô, áo cuối, mặt nạ.

| Mã | Chỉ số | Cách tính |
|---|---|---|
| M1 | Giữ dáng áo | Độ trùng (IoU) của bóng người tách bằng `rembg` giữa ảnh ghép thô và áo cuối. Không dùng `garment_mask()` cho áo cuối vì nó dựa vào vải trắng, sai khi đã in hoa văn. |
| M2 | Trôi ngoài vùng áo | Sai khác tuyệt đối trung bình ở vùng ngoài mặt nạ. Kỳ vọng 0 khi polish có mặt nạ. |
| M3 | Giữ họa tiết qua polish | LPIPS hoặc DreamSim (hai thước đo độ giống gần với cảm nhận người) giữa ảnh ghép thô và áo cuối trên vùng in; thêm số điểm đặc trưng SIFT còn khớp. |
| M4 | Trung thành với hiện vật | DreamSim giữa ảnh gốm và vùng in trên áo cuối. Chỉ hiển thị tham khảo, vì có lệch miền do nếp vải và tỉ lệ lát. |

Điểm thẩm mỹ: thay proxy CLIP bằng bộ dự đoán LAION (cột CSV `aesthetic_impl` ghi đúng tên). Giữ nguyên các cột cũ để so sánh.

Các thư viện mới (LPIPS, DreamSim, `rembg`, bộ dự đoán LAION) **chưa kiểm tra giấy phép**, cần xem trước khi thêm vào môi trường.

### 3.3. Quy tắc loại và thử lại **[P0]**

1. Sau polish tính M1, M2, M3.
2. Nếu M1 hoặc M3 vượt ngưỡng lỗi: thử lại với seed polish kế tiếp, tối đa 3 lần.
3. Vẫn lỗi: hạ độ nhiễu một bậc (0,30 xuống 0,22), thử thêm 1 lần.
4. Vẫn lỗi: trả ảnh ghép thô kèm nhãn "chưa qua bước hoàn thiện", không trả ảnh lỗi.
5. Mọi lần loại ghi vào `outputs/qc/rejects.csv` (ảnh, chỉ số, ngưỡng, lý do, hành động tiếp theo) và lưu cả ảnh bị loại. Đây chính là "ví dụ bị loại hoặc sửa" cho minh chứng.

**Cách đặt ngưỡng, không bịa số:** sinh khoảng 60 ảnh từ thí nghiệm ở mục 4; hai thành viên gắn nhãn tay "lỗi rõ" hoặc "chấp nhận được" (dáng áo có sai không, hoa văn có bị vẽ thành thứ khác không); chọn ngưỡng tách hai nhóm tốt nhất và báo số ảnh bị phân loại sai.

**Cần bạn quyết định:** nguyên tắc dự án là Similarity và Aesthetic không có ngưỡng đạt hay không đạt. Đề xuất: ngưỡng chỉ áp cho **lỗi kỹ thuật** (M1, M3); M4 và điểm thẩm mỹ vẫn chỉ hiển thị tham khảo.

### 3.4. Người am hiểu xem xét mẫu **[P0 phần mời người, P1 phần đưa vào hệ thống]**

"Xem xét mẫu trước khi giới thiệu" nghĩa là: trước khi đưa thiết kế ra cho ban tổ chức hay người xem, phải có người am hiểu kiểm tra từng mẫu. Minh chứng cần phiếu do người thật điền. Một trang trống không thay được phiếu.

**Ai là "am hiểu":** nghệ nhân hoặc người làm gốm, giảng viên mỹ thuật hoặc thiết kế, người làm áo dài. Không cần chuyên gia nổi tiếng. Cần ít nhất 1 người về gốm hoặc di sản và 1 người về dáng áo dài.

**Cách tìm khi chưa quen ai:**

1. Chính các cơ sở gốm đang có ảnh trong bộ dữ liệu (Full Home, Bát Tràng Ceramica, Xưởng Gốm Sứ Việt). Gửi một thư vừa xin phép dùng ảnh (mục 5) vừa hỏi có nghệ nhân nào xem 6 mẫu trong 15 phút không.
2. Giảng viên khoa mỹ thuật, thiết kế, văn hóa học, lịch sử ở trường của nhóm.
3. Ban tổ chức: hỏi họ có giới thiệu chuyên gia không, và mức tối thiểu họ chấp nhận.
4. Người làm hoặc học thiết kế áo dài, cho phần dáng áo.

**Phiếu (Google Form, 15 đến 20 phút mỗi người):**

| # | Câu hỏi | Thang |
|---|---|---|
| 1 | Hoa văn trên áo còn nhận ra là của hiện vật gốc không? | 1 đến 5 |
| 2 | Có chi tiết nào bị biến dạng, cắt cụt hoặc dùng sai ngữ cảnh văn hóa không? | Có hoặc Không, kèm mô tả |
| 3 | Dáng áo dài đúng không (cổ, tay, tà)? | 1 đến 5 |
| 4 | Vị trí và tỉ lệ hoa văn trên áo có hợp lý không? | 1 đến 5 |
| 5 | Có nên giới thiệu mẫu này công khai không? | Nên, Cần sửa, Không nên |
| 6 | Nhận xét và đề xuất sửa | Tự do |

**Đưa vào hệ thống:** Design Passport có trường `review_status` (`chua_tham_dinh`, `da_tham_dinh_dat`, `can_sua`, `khong_gioi_thieu`) kèm vai trò người xem và ngày. Trang giới thiệu chỉ hiện mẫu `da_tham_dinh_dat`.

**Nếu đến hạn vẫn không có ai:** giữ `chua_tham_dinh`, không ghi "đã thẩm định". Nhờ bất kỳ người có hiểu biết liên quan và ghi đúng vai trò của họ. Lưu bằng chứng đã liên hệ (thư, thời điểm, người nhận) và nêu trong hồ sơ: đã liên hệ X nơi, chưa nhận được phản hồi trước hạn, thẩm định là hạng mục tiếp theo. Tự đánh giá của nhóm ghi riêng, không gọi là chuyên gia.

### 3.5. Minh chứng

```
docs/evidence/req1/
  sheets/<heritage_id>_L<n>.png     bảng ghép: gốm | Canny | hoa văn | ghép thô | áo cuối, kèm chỉ số
  rejects/ + rejects.csv            ảnh bị loại và ảnh thay thế
  review/phieu_tham_dinh.md         mẫu phiếu
  review/ket_qua_tham_dinh.csv      câu trả lời
  final_metrics.csv
```

Các ảnh trung gian (`_00_ref`, `_01_canny`, `_pattern`, `_aodai_raw`, `_aodai`) đã có sẵn trong `outputs/variants/`, nên bảng ghép chỉ cần một script nhỏ.

---

## 4. Yêu cầu 2: đối chứng có kiểm soát

### 4.1. Cấu hình cố định (mọi thí nghiệm)

| Tham số | Giá trị cố định |
|---|---|
| Prompt | `assemble_pattern(name_en, base_description)`, **không** có cụm từ theo mức |
| Negative prompt | `NEG_PATTERN` |
| Bảng màu | `original` (qua `match_palette`) |
| Bố cục | `front_panel`, không để CLIP tự chọn |
| Bước, guidance, bộ lấy mẫu | 25, 7,5, UniPC |
| Polish | có mặt nạ, độ nhiễu 0,30 |

### 4.2. Các thí nghiệm, mỗi lần đổi đúng một yếu tố

| Mã | Yếu tố đổi | Giá trị | Trả lời câu hỏi |
|---|---|---|---|
| A | Trọng số ControlNet | 0 (không ControlNet), 0,25, 0,45, 0,65, 0,85 | Riêng ControlNet ảnh hưởng độ trung thành thế nào |
| B | Bước ghép, trên cùng một hoa văn (trọng số 0,65) | ghép thô, polish toàn ảnh 0,40 (hiện tại), polish toàn ảnh 0,30, polish có mặt nạ 0,30 | Riêng bước ghép ảnh hưởng dáng áo và hoa văn thế nào |
| C | Cụm từ theo mức trong prompt, trọng số cố định 0,45 | không có, "modern simplified interpretation", "bold contemporary reinterpretation" | Tách ảnh hưởng của chữ khỏi ảnh hưởng của trọng số |
| E (chỉ nếu làm mục 6) | Cách tạo họa tiết | sinh lại bằng ControlNet 0,85, trích xuất | Trích xuất giữ họa tiết hơn sinh lại bao nhiêu |

**Quy mô:** 3 hiện vật có cạnh ngắn đủ 1024px (`BT_Hac_XP` 1746, `MB_2C_XP_31` 1191, sen dát vàng 1024) nhân 5 seed (42 đến 46). Ảnh hoa văn: A = 75, B = 60, C = 45. Tốc độ đo được khoảng 6 giây một ảnh hoa văn. Seed sinh hoa văn và seed polish ghi thành hai cột riêng.

**Mã:** `evaluation/ablation.py` đọc cấu hình từ `evaluation/configs/ablation.csv`, ghi `evaluation/results/ablation_runs.csv`. Thêm tham số `use_modifier` cho `pattern.build_prompt()` để tắt cụm từ theo mức. Sửa danh sách hiện vật mặc định của `intensity_sweep.py` (đang trỏ `BT001`, `BT008`, `BT010`, không có trong dữ liệu).

### 4.3. Đánh giá mù

1. `evaluation/make_blind_set.py`: sao chép ảnh sang `outputs/blind/`, đổi tên thành mã ngẫu nhiên, xáo thứ tự, ghi `blind_key.csv` giữ riêng.
2. 3 đến 5 người chấm, không tham gia sinh ảnh. Mỗi người chấm khoảng 60 ảnh.
3. Tiêu chí, thang 1 đến 5, có mô tả:

| Tiêu chí | Mức 1 | Mức 5 |
|---|---|---|
| Nhận ra hoa văn gốc (xem kèm ảnh gốm) | Không liên quan | Rõ ràng cùng hoa văn |
| Dáng áo dài | Sai dáng, biến dạng | Đúng và tự nhiên |
| Tự nhiên như vải in | Như hình dán | Như in trên vải thật |
| Thẩm mỹ tổng thể | Rất kém | Rất đẹp |
| Có lỗi rõ (tay, mặt, vệt lạ) | | Có hoặc Không |

4. Thiếu người: dùng so sánh cặp (hai ảnh cạnh nhau, xáo trái phải) cho thí nghiệm B, vì câu "bên nào giữ hoa văn tốt hơn" dễ đồng thuận hơn thang điểm.

### 4.4. Thống kê

`evaluation/analyze.py`: trung bình, độ lệch chuẩn, nhỏ nhất, lớn nhất **theo seed** cho từng cấu hình và từng chỉ số; hệ số biến thiên (độ lệch chuẩn chia trung bình) để nêu "mức dao động chất lượng"; độ đồng thuận giữa người chấm (Krippendorff's alpha); tương quan Spearman giữa chỉ số tự động và điểm người; biểu đồ hộp.

**Cách trình bày:** quan sát trên 3 hiện vật nhân 5 seed, không khẳng định quy luật chung.

### 4.5. Minh chứng

```
docs/evidence/req2/
  ablation_configs.csv, ablation_runs.csv, ratings.csv, blind_key.csv, summary.csv, plots/
```

---

## 5. Yêu cầu 3: nguồn, bản quyền, truy vết

### 5.1. Làm sạch nguồn dữ liệu **[P0]**

Đây là mục rủi ro cao nhất và phụ thuộc người ngoài, nên bắt đầu ngay.

1. **Gộp metadata về một file:** chuyển URL từ `data/metadata.json` sang `data/heritage/metadata.json`, rồi xóa hoặc đánh dấu lỗi thời file kia. Xóa khoảng trắng thừa cuối URL của `BT_Hac_XP`.
2. **Sửa `items.json`:** bỏ nguồn bảo tàng và niên hiệu không có căn cứ, hoặc xóa file. Rà hồ sơ, slide, video xem có chỗ nào đã dùng các thông tin này.
3. **Gọi đúng tên dữ liệu:** sáu ảnh là sản phẩm gốm Bát Tràng đương đại mang hoa văn truyền thống, không phải hiện vật bảo tàng.
4. **Viết lại `team_description`** bằng lời của nhóm, hoặc giữ nguyên văn nhưng ghi rõ trích từ trang người bán kèm URL. Kiểm tra cả 6 mục xem có trùng trang nguồn không.
5. **Quyền dùng ảnh, theo thứ tự ưu tiên:**

| Phương án | Việc làm | Bằng chứng lưu |
|---|---|---|
| A. Xin phép | Gửi thư cho 3 đơn vị nêu mục đích dự thi phi thương mại, xin phép dùng ảnh và cách ghi công | Thư gửi và thư trả lời, lưu PDF vào `docs/evidence/req3/permissions/` |
| B. Tự chụp | Chụp sản phẩm hoặc hiện vật có sự đồng ý của nơi chụp, cạnh ngắn từ 1024px | Ảnh gốc có EXIF, ghi ngày và địa điểm |
| C. Kho ảnh mở | Thay bằng ảnh gốm Việt Nam có giấy phép rõ (Wikimedia Commons, kho mở của bảo tàng) | URL trang ảnh và tên giấy phép |

Chạy A và B song song. Mục nào chưa có quyền rõ ràng thì thay bằng B hoặc C, hoặc rút khỏi bộ giới thiệu công khai. Đây không phải tư vấn pháp lý; nên hỏi người có chuyên môn của trường.

6. **Ba ảnh dưới 1024px:** xin ảnh độ phân giải cao khi liên hệ, hoặc thay ảnh.

**Schema mới cho mỗi mục trong `data/heritage/metadata.json`:**

```json
{
  "heritage_id": "BT_Hac_XP",
  "object_type": "san_pham_duong_dai",
  "image_path": "data/heritage/BT_Hac_XP.png",
  "image_sha256": "<64 ký tự>",
  "image_size_px": [1746, 1746],
  "image_source_url": "https://...",
  "source_holder": "Tên đơn vị giữ ảnh",
  "accessed_on": "2026-09-06",
  "license": "permission_granted | own_photo | CC-BY-4.0 | unverified",
  "license_evidence": "docs/evidence/req3/permissions/BT_Hac_XP.pdf",
  "usage_scope": "Dự thi, phi thương mại",
  "credit_line": "Ảnh: <đơn vị>, dùng với sự cho phép",
  "team_description": "...",
  "team_description_origin": "team_written | quoted_from_source"
}
```

Thêm kiểm tra vào `load_heritage_metadata()`: cảnh báo khi `license` là `unverified` hoặc cạnh ngắn dưới 1024px.

### 5.2. Design Passport có phiên bản **[P0]**

Passport là hồ sơ đi kèm mỗi thiết kế. Tạo `api/passport.py`; mỗi thiết kế có `outputs/passports/<design_id>.json`, gồm chuỗi bước nối nhau bằng mã băm SHA256 đầy đủ (64 ký tự):

`nguồn` → `canny` → `hoa văn` → `khớp màu` → `ghép` → `polish` → (tùy chọn) `sửa tay`

Mỗi bước ghi: mã băm file, mã băm của bước cha, tham số (seed, trọng số, prompt, độ nhiễu), `by` là `ai`, `deterministic` hoặc `human`. Bước `sửa tay` ghi người sửa (vai trò), công cụ, ghi chú, thời điểm. Thêm `ai_label`, `review_status`, các chỉ số M1 đến M4, và `qc.rejected_attempts`.

**Việc làm:**
1. Gọi `passport.create()` từ `streamlit_runner.generate_design_set()` và `variants.py`, để luồng API cũng ghi đủ tham số (hiện chỉ ghi `job_id`). Lưu mọi ảnh trung gian.
2. Lệnh `python -m api.passport add-edit` thêm bước `sửa tay`, tăng số phiên bản, giữ nguyên các bước cũ.
3. Lệnh `python -m api.passport verify` tính lại mã băm các file và báo chỗ nào chuỗi bị đứt.
4. Ảnh áo mẫu cũng do SD sinh: ghi mã băm và đánh dấu AI.
5. Endpoint `GET /passport/{design_id}` và cập nhật `passport.js` để hiện nguồn, ghi công, seed, tham số, mã băm rút gọn, phiên bản, lịch sử bước, trạng thái thẩm định.

### 5.3. Nhãn AI **[P0 nhãn nhìn thấy, P1 metadata, P2 chữ ký C2PA]**

- Nhãn nhìn thấy: "Nội dung do AI hỗ trợ tạo" trên thẻ biến thể, trong Passport, trên ảnh xuất.
- Metadata trong file PNG: `ai_generated`, `design_id`, mã băm Passport.
- C2PA (chuẩn ký nguồn gốc nội dung số) bằng `c2pa-python`: chỉ làm nếu còn thời gian; chứng thư tự ký đủ cho minh họa.
- Căn cứ pháp lý để trích: Luật Trí tuệ nhân tạo số 134/2025/QH15 (hiệu lực 01/3/2026), chi tiết ở Nghị định 142/2026/NĐ-CP. Thông tin này lấy từ các bài tổng hợp, **cần đối chiếu văn bản gốc** trước khi đưa vào hồ sơ.
- Khôi phục ghi chú "mô tả nội bộ, không phải trích dẫn học thuật" trong modal chi tiết của web.

### 5.4. Minh chứng

```
docs/evidence/req3/
  danh_muc_nguon.md, permissions/, passports/ (ít nhất 2 ví dụ, 1 có bước sửa tay), verify_output.txt
docs/ai_disclosure.md   công cụ AI đã dùng (SD 1.5, ControlNet, CLIP, mô hình viết mô tả), việc tắt safety checker và lý do
```

---

## 6. Giữ chính xác họa tiết gốc (ưu tiên cải tiến của nhóm)

Mục này không bắt buộc theo yêu cầu của ban tổ chức, nhưng là ưu tiên của nhóm và làm yêu cầu 1 có nội dung thật hơn.

### 6.1. Bằng chứng họa tiết bị mất

Xem ảnh gốc, bản đồ Canny và 4 mức hoa văn của cả 6 hiện vật trong `outputs/variants/` (đánh giá bằng mắt trên ảnh thu nhỏ, chưa có số đo):

| Hiện vật | Mức 1 (trọng số 0,85) | Mức 2 | Mức 3 và 4 |
|---|---|---|---|
| Cúc dây | Giữ tốt | Giữ tốt | Còn tinh thần, chi tiết khác |
| Sen mực | Giữ tốt | Giữ một phần | Mất sen |
| Thuyền | Giữ, nhưng có viền hình bát | Giữ khá | Mức 4 vô nghĩa |
| Sen dát vàng | Giữ một phần, lẫn mảng hình bình | Tương tự | Mất |
| Công và sen lam | Ra cả hình cái bình trên nền xám | Tương tự | Mức 3 còn chim, mức 4 mất |
| **Công vàng** | **Biến dạng:** đầu to, thân phủ ô tổ ong, mất đuôi xòe; nền hồng trong khi gốc vàng | **Mất hẳn** | **Mất hẳn** |

**Nguyên nhân (suy từ ảnh và code):** ControlNet Canny chỉ giữ đường nét thô, chi tiết còn lại do SD tự vẽ; Canny của cánh hoa nhỏ thành mạng ô nên model vẽ thành vảy; nguồn thấp phân giải; bề mặt bình cong làm họa tiết ở mép bị nén; hàm khớp màu mức 1 khớp trung bình và độ lệch trong không gian LAB nên nền vàng ra hồng; mức 2 đến 4 mất họa tiết là do thiết kế.

### 6.2. Đánh giá kiến trúc bốn khối của nhóm và đề xuất chỉnh

| Khối | Đánh giá | Chỉnh |
|---|---|---|
| 1. Tách vật bằng SAM hoặc U2-Net và trải phẳng bình (OpenCV) | Tốt, đã thử (mục 6.3) | Giữ |
| 2. Khóa dáng áo: SD 1.5 sinh một sketch mỗi lần rồi áp ý tưởng TexControl | **Rủi ro cao.** SD 1.5 không đảm bảo dáng áo dài (chú thích trong `prompt_template.py`: thiếu mô tả cấu trúc thì seed 44 trôi sang sườn xám, mẫu thử chỉ 3 seed). Sketch sai thì ControlNet bám đúng cái sai. Chuỗi ảnh, sketch, ảnh còn mất thông tin | Dùng ảnh áo trơn cố định (hoặc sinh bằng SD rồi kiểm tra), lấy Canny hoặc Depth làm khung, bỏ bước sketch. Muốn mỗi lần một dáng: sketch tham số hoặc bộ phác thảo nhóm tự vẽ, có kiểm tra tự động |
| 3. ControlNet Lineart cộng IP-Adapter để chuyển họa tiết và màu men | **Khó giữ chính xác họa tiết.** ControlNet bám theo vị trí trong ảnh, nên nét họa tiết phẳng bị hiểu là viền áo (đúng lỗi v6: xác suất ra áo dài bằng 0,000 ở trọng số 0,85). IP-Adapter chỉ giữ cảm giác chung, mất chi tiết (bài AM-Adapter, Ctrl-X). Bài Ulos SDXL cho thấy chồng nhiều điều kiện có thể tệ hơn | Đặt họa tiết **tất định** lên áo trước (phần tử đã cắt hoặc ô lát), rồi ControlNet Lineart lấy nét từ **ảnh đã ghép**. IP-Adapter chỉ để chỉnh màu men, trọng số thấp, có đo |
| 4. Mặt nạ vùng tà áo và phóng to | Đúng hướng. Bản đo cho thấy họa tiết trên ảnh áo 512px bị thu nhỏ 3,8 đến 5 lần, nên độ phân giải là nút thắt thật | Mặt nạ có sẵn (mục 3.1); xử lý độ phân giải (mục 6.5) |

TexControl (bài trong `docs/paper tham khảo/`) điều khiển chất liệu bằng **chữ** ("fur cloth"), không bằng ảnh mẫu, và chỉ đánh giá bằng mắt trên 50 sketch. Ý hai giai đoạn (khóa viền rồi làm chất liệu) là phần đáng giữ.

### 6.3. Đã thử trước đó (mã hiện không có trong repo)

Trong phiên làm việc trước tôi đã viết và thử một bộ mã cho khối 1 và phần ghép. Toàn bộ đã bị xóa khỏi repo theo yêu cầu quay về commit `fcbcce8`. Bản sao lưu nằm ngoài repo, trong thư mục tạm của phiên (`...\scratchpad\backup_2A\`: file `.bundle` chứa 3 commit, bản vá sửa chưa commit, 8 file mới). Thư mục tạm có thể bị dọn, nên nếu cần dùng lại thì sao chép sớm.

| Việc đã thử | Kết quả | Mức tin cậy |
|---|---|---|
| Trải phẳng bình theo silhouette | Hình trụ tổng hợp ô vuông 30px ra đúng 30 x 30px. Trên ảnh thật, họa tiết ở sườn bình trở lại đúng tỉ lệ. Lần đầu chỉ lấy dải bình rộng từ 85% nên **cắt mất thân thuyền**; sửa bằng tỉ lệ ngang theo từng hàng và hạ xuống 60% | Chạy được; kết luận về ảnh thật dựa trên xem bằng mắt |
| Tách họa tiết (Grounded-SAM: Grounding DINO tiny 659MB và SAM ViT-base 358MB, ghi Apache-2.0 trên Hub) | Thuyền, bông sen, bông cúc tách tốt. Công vàng bị lẫn hoa và sóng. Silhouette bằng SAM sửa được lỗi bóng sàn của bình sen dát vàng | Xem bằng mắt, không có mặt nạ chuẩn |
| Ghép một họa tiết chính lên áo (mức 1) | Chạy 6/6. Họa tiết chiếm 6% đến 15% diện tích áo, thu nhỏ 3,8 đến 5 lần ở ảnh 512px | Số đo, nhưng ảnh trông như huy hiệu nhỏ |
| Thư viện phần tử (SAM tự phân đoạn) | 131 phần tử từ 6 hiện vật, chỉ 45 dùng được; 71 cặp gần trùng; chỉ 4 hình chính nguyên vẹn; ô nền lát có độ gián đoạn 1,8 đến 2,25 ở 5/6 bình (số này lớn hơn 1 nghĩa là nối vòng chưa khớp) | Số đo |
| Ảnh áo mẫu 1024px bằng hires fix (phóng 2 lần rồi SD img2img kèm ControlNet Canny) | Sinh được ở độ nhiễu 0,3: 23,4 giây, VRAM đỉnh 7,1 GB. Với CPU offload thì hết RAM (máy chỉ còn 4,4 GB trống) | **Chưa xem ảnh kết quả**, chưa kiểm dáng áo và khuôn mặt |
| 36 test pytest | Đạt. Hai subagent kiểm tra (đọc logic, và tính trước kết quả từ đặc tả) tìm ra lỗi thật, đã sửa | Test chỉ kiểm hàm và số học, không kiểm chất lượng hình |

**Bài học:** hai subagent không bắt được việc mất thân thuyền, vì chúng kiểm logic chứ không kiểm hình. Lỗi do người nhìn ảnh gốc phát hiện. Nên có bước xem lại bằng mắt ở mỗi hiện vật.

### 6.4. Các bước làm (nếu đồng ý làm)

| Bước | Việc | Xong khi | Ước lượng |
|---|---|---|---|
| B1 | Trải phẳng bình, tách silhouette | Selftest hình trụ đạt; 6 hiện vật có ảnh phẳng, xem bằng mắt | 1 ngày |
| B2 | Tách phần tử họa tiết chính (Grounded-SAM, cụm danh từ rút từ `prompt_terms.json`) | Mỗi hiện vật có mặt nạ họa tiết chính, xem bằng mắt | 1 ngày |
| B3 | Ghép họa tiết chính lên áo (in vị trí), kèm polish có mặt nạ (mục 3.1) | Ảnh áo cuối cho 6 hiện vật, qua M1 đến M4 | 1 đến 2 ngày |
| B4 | Ảnh áo mẫu độ phân giải cao (mục 6.5) | Họa tiết trên áo thu nhỏ dưới 3 lần | 1 ngày |

Ước lượng là của tôi, chưa đo. Nếu dùng lại bản sao lưu thì B1, B2 và một phần B3 có thể rút ngắn.

**Nếu thiếu thời gian, cắt theo thứ tự:** B4, rồi B3. Không cắt B1 và B2 nếu đã chọn làm nhánh này. Nếu không làm nhánh này, các chỉ số ở mục 3 và đối chứng ở mục 4 chạy trên pipeline hiện tại, và hồ sơ nêu thẳng giới hạn ở mục 6.1.

### 6.5. Độ phân giải ảnh áo

Ảnh áo mẫu chỉ 512x512, thân áo rộng khoảng 90px. Họa tiết trích chính xác đến đâu cũng bị thu nhỏ khi ghép. Hướng: sinh ảnh áo mẫu 1024px một lần (hires fix, mục 6.3), dùng lại cho mọi thiết kế. Cần xem ảnh kết quả, kiểm dáng áo, khuôn mặt, bàn tay trước khi dùng. Ảnh này do AI sinh nên ghi mã băm, tham số vào Passport và gắn nhãn AI.

### 6.6. Giới hạn cần nêu thẳng trong hồ sơ

- Chính xác không vượt quá ảnh nguồn; ba ảnh dưới 1024px bị giới hạn.
- Bình hồ lô hoặc hình cầu thì trải phẳng sai ở vai và đáy.
- Bóng men phản chiếu bị trải theo hoa văn rồi in lên vải thành vệt sáng.
- Họa tiết bị che khuất (hoa che trước con công) cho mặt nạ lẫn tạp.
- Trên áo, họa tiết đã thu nhỏ, uốn theo nếp vải và nhân đổ bóng, nên không còn đúng từng pixel. Độ đúng pixel chỉ áp cho lớp trích xuất.

### 6.7. Không làm trong kế hoạch này (đưa vào "Hướng phát triển" của hồ sơ)

| Hướng | Lý do |
|---|---|
| SD 1.5 sinh sketch áo mỗi lần chạy | Tính ngẫu nhiên vào chỗ cần cố định (mục 6.2) |
| IP-Adapter để giữ hình họa tiết | Mất chi tiết theo các bài đã đọc |
| LoRA học hoa văn hoặc áo dài | Dữ liệu chưa có giấy phép; 6 ảnh quá ít; làm nhiễu đối chứng. Các bài tham khảo dùng từ khoảng 70 đến 1200 ảnh |
| Dữ liệu VietFashion để huấn luyện | Ảnh do AI sinh, giấy phép dữ liệu chưa rõ (giấy phép CC BY-NC-ND ghi trong bài báo, không chắc áp dụng cho dữ liệu); chỉ nên trích dẫn hoặc xin phép tác giả |
| Sinh áo mỗi lần chạy không cần ảnh mẫu | Cần thử xác suất thành công trước (20 seed) |
| Dựng áo 3D (CLO 3D) | Ngoài khung thời gian, chi phí phần mềm chưa kiểm tra |

---

## 7. Link thử nghiệm cho ban tổ chức

### 7.1. Kiến trúc hai lớp

Mô hình sinh ảnh chạy trên GPU 8GB của máy nhóm, nên link không thể phụ thuộc hoàn toàn vào máy đó.

```text
Ban tổ chức ---> https://<tên>.vercel.app      LỚP 1, luôn hoạt động
                  giao diện tĩnh + kết quả sinh sẵn + Passport
                  |
                  +-- kiểm tra /health ---> https://<api>    LỚP 2, trong khung giờ trực
                      đường hầm HTTPS ---> FastAPI trên máy GPU, sinh ảnh trực tiếp
```

- **Lớp 1 (trưng bày, 24/7):** dữ liệu tĩnh xuất từ pipeline (6 hiện vật, 4 mức, Passport, kết quả đối chiếu). Máy GPU tắt thì link vẫn có nội dung. Bỏ số Similarity viết cứng trong `curate.js`.
- **Lớp 2 (sinh trực tiếp):** giao diện gọi `/health`; sống thì bật nút "Tạo thiết kế", chết thì báo ngoại tuyến và giữ chế độ trưng bày.
- **Đường hầm (tunnel):** Cloudflare Tunnel nếu nhóm có tên miền riêng, nếu không thì ngrok với tên miền tĩnh. Điều khoản gói miễn phí tôi nêu theo hiểu biết sẵn có, chưa tra lại.
- **Phương án dự phòng trên mây:** Hugging Face Spaces có GPU. Đi ngược nguyên tắc chạy local và tốn phí, chỉ làm nếu ban tổ chức yêu cầu sinh ảnh bất kỳ lúc nào.

### 7.2. Việc phải làm trước khi mở link

- **Quyền dùng ảnh (mục 5.1):** mục nào chưa có quyền thì không đưa vào bản deploy; bật mật khẩu hoặc mã truy cập cho đến khi xong.
- **Nhãn AI hiển thị** trên mọi ảnh sinh ra.
- **Gia cố API:** hàng đợi thay cho lỗi 409; mã truy cập cho ban tổ chức; giới hạn tần suất theo phiên; lưu job xuống đĩa (JSON); thời gian chờ tối đa mỗi job và giải phóng VRAM khi lỗi; đặt `WEB_UI_ORIGINS` theo tên miền Vercel; đặt `DH_API_BASE` theo môi trường; không ghi địa chỉ IP vào audit log; nếu thêm ô yêu cầu tự do thì giới hạn độ dài và kiểm ngân sách token.
- **Vận hành máy GPU:** chạy API và đường hầm như dịch vụ tự khởi động lại, tắt chế độ ngủ, nạp sẵn model, giám sát `/health`.

### 7.3. Kiểm thử trước khi gửi link

| # | Kiểm thử | Kỳ vọng |
|---|---|---|
| 1 | Mở link bằng mạng di động, máy GPU tắt | Thấy hiện vật, kết quả sinh sẵn, Passport, thông báo ngoại tuyến |
| 2 | Máy GPU bật, bấm "Tạo thiết kế" | Đủ 4 kết quả kèm Passport, không lỗi CORS hay trộn nội dung |
| 3 | Ba người bấm sinh cùng lúc | Xếp hàng lần lượt, không ai nhận lỗi |
| 4 | Sinh liên tiếp 20 lượt | Không tràn VRAM, thời gian ổn định |
| 5 | Khởi động lại API giữa chừng | Kết quả cũ vẫn xem được |
| 6 | Mở trên điện thoại và trình duyệt khác | Dùng được |
| 7 | Đo thời gian một lượt đủ 4 mức | Ghi số thật vào hướng dẫn |

### 7.4. Tài liệu gửi kèm link

`docs/HUONG_DAN_THU_NGHIEM.md` (một trang): link và mã truy cập; khung giờ sinh trực tiếp; ba bước thử (chọn hiện vật, bấm "Tạo thiết kế", xem 4 kết quả và Passport); thời gian chờ đo được và giới hạn đã biết; đầu mối liên hệ; link video trình diễn làm phương án cuối.

---

## 8. Lịch 18 đến 25/11

Vai trò theo nhóm: **AI** (kỹ sư AI và dữ liệu), **DEV** (backend, giao diện), **BA** (tuyển ảnh, viết mô tả, tổ chức chấm và thẩm định, viết hồ sơ).

| Ngày | AI | DEV | BA |
|---|---|---|---|
| 18/11 (nay) | Chốt các quyết định ở mục 0; polish có mặt nạ | Gộp metadata, schema nguồn, kiểm tra giấy phép và độ phân giải | Gửi thư xin phép 3 đơn vị; mời người thẩm định và người chấm; sửa `items.json` |
| 19/11 | Chỉ số M1 đến M4, bộ dự đoán thẩm mỹ LAION | `api/passport.py`: tạo, mã băm đầy đủ, lưu ảnh trung gian | Viết lại 6 `team_description`; soạn phiếu thẩm định và phiếu chấm |
| 20/11 | Cổng loại và thử lại; `ablation.py`; chạy thí nghiệm A | Tích hợp Passport vào API; nhãn AI hiển thị; lớp 1 lên Vercel có mật khẩu | Chụp ảnh thay thế (phương án B) nếu chưa có phản hồi |
| 21/11 | Thí nghiệm B, C; `make_blind_set.py` | `add-edit`, `verify`; giao diện Passport đầy đủ | Gửi bộ ảnh mù và phiếu cho người chấm và người thẩm định |
| 22/11 | Gắn nhãn tay khoảng 60 ảnh, hiệu chỉnh ngưỡng; nhánh mục 6 (B1, B2) nếu chọn | Đường hầm, CORS, hàng đợi, mã truy cập, lưu job | Theo dõi thu phiếu; chốt danh mục nguồn, thay hoặc rút mục chưa có quyền |
| 23/11 | `analyze.py`; B3 nếu chọn | Dịch vụ tự khởi động, giám sát; kiểm thử 1 đến 7 | Tổng hợp thẩm định, đánh dấu `review_status` |
| 24/11 | Viết phần phương pháp và kết quả cho hồ sơ | Đóng gói `docs/evidence/`, tải lên Drive, mở quyền truy cập | Hướng dẫn thử nghiệm, `ai_disclosure.md`, cập nhật hồ sơ và slide |
| 25/11 | Dự phòng, kiểm tra chéo | Gửi link, cập nhật tài liệu dự án | Rà soát cuối, tập trả lời câu hỏi |

**Cắt theo thứ tự nếu thiếu thời gian:** B4, B3, thí nghiệm C, chữ ký C2PA, biểu đồ. **Không cắt:** polish có mặt nạ, M1 đến M4, thí nghiệm A và B với 5 seed, danh mục nguồn, Passport có bước sửa tay, link ở chế độ trưng bày.

Dưới 7 ngày cho cả ba nhóm việc là rất sát. Việc phụ thuộc người ngoài (thư xin phép, người thẩm định, người chấm) phải gửi ngay hôm nay.

---

## 9. Rủi ro và điều chưa kiểm chứng

| Rủi ro | Giảm thiểu |
|---|---|
| Không xin được quyền dùng ảnh kịp | Phương án B hoặc C; rút mục chưa có quyền; mật khẩu cho link |
| Không có người am hiểu xem mẫu | Mục 3.4: giữ `chua_tham_dinh`, ghi đúng sự thật, lưu bằng chứng liên hệ |
| Người chấm không đủ hoặc không đồng thuận | Chấm cặp cho thí nghiệm B; báo cáo độ đồng thuận thật |
| Ngưỡng loại ảnh đặt tùy tiện | Đặt theo nhãn tay của 60 ảnh, báo số phân loại sai |
| Máy GPU tắt hoặc mất mạng lúc ban tổ chức thử | Lớp 1 trưng bày luôn chạy; video trình diễn làm phương án cuối |
| Hết RAM hoặc VRAM khi nạp thêm model | Nạp tuần tự rồi giải phóng; đo trước (máy hiện chỉ còn khoảng 4,4 GB RAM trống) |
| Thư viện mới vướng giấy phép | Kiểm tra trước khi thêm |

**Những điều tôi chưa kiểm chứng:** giấy phép các thư viện LPIPS, DreamSim, `rembg`, bộ dự đoán LAION; chất lượng ảnh áo 1024px; điều khoản gói miễn phí của đường hầm; việc 5 trang nguồn còn lại có trùng `team_description` không; nội dung văn bản gốc của luật và nghị định về nhãn AI; ngưỡng loại ảnh.

---

## 10. Danh sách minh chứng nộp

| Yêu cầu | Minh chứng | Vị trí | Xong |
|---|---|---|---|
| 1 | Bộ ảnh đầu vào, hoa văn, áo cuối | `docs/evidence/req1/sheets/` | |
| 1 | Phiếu nhận xét | `docs/evidence/req1/review/` | |
| 1 | Ví dụ bị loại hoặc sửa | `docs/evidence/req1/rejects/` | |
| 2 | CSV cấu hình | `docs/evidence/req2/ablation_configs.csv` | |
| 2 | Bảng điểm người đánh giá | `ratings.csv`, `blind_key.csv` | |
| 2 | Thống kê mức dao động | `summary.csv`, `plots/` | |
| 3 | Danh mục nguồn và giấy phép | `docs/evidence/req3/danh_muc_nguon.md`, `permissions/` | |
| 3 | Passport có phiên bản nguồn đến thành phẩm, có bước sửa tay | `docs/evidence/req3/passports/`, `verify_output.txt` | |
| 3 | Kê khai công cụ AI | `docs/ai_disclosure.md` | |
| Link | Link, mã truy cập, hướng dẫn, qua 7 kiểm thử | `docs/HUONG_DAN_THU_NGHIEM.md` | |

---

## 11. Quy trình làm việc theo CLAUDE.md và cập nhật tài liệu

- **Quy trình cho mỗi module lớn:** (1) một subagent chỉ đọc kiểm tra logic, (2) một subagent tính trước kết quả mong đợi từ đặc tả rồi so với kết quả chạy thật, (3) viết và chạy pytest, (4) tự rà soát lại toàn bộ thay đổi. Thêm bước **xem ảnh kết quả bằng mắt** vì hai subagent không bắt được lỗi hình (mục 6.3).
- **Git:** chỉ commit khi nhóm yêu cầu; thông điệp ngắn bằng tiếng Anh; không có dòng đồng tác giả.
- **Tài liệu sau khi xong:** cập nhật `README.md` và `docs/mvp_spec.md` (đánh dấu phần cũ lỗi thời, không xóa); cập nhật mô tả kiến trúc hai giai đoạn trong `CLAUDE.md` nếu còn nhắc kiến trúc một giai đoạn hoặc 13 hiện vật (repo có 6 hiện vật); nếu làm mục 6 thì sửa dòng "4 mức Creative Intensity, ControlNet weight tương ứng" cho khớp cách tạo họa tiết mới, kèm bằng chứng ở mục 6.1.
- **Môi trường:** `CLAUDE.md` yêu cầu `uv` và `pyproject.toml`; repo đang dùng `requirements.txt` (ghim torch 2.11.0 kênh cu128) trong khi số đo cũ chạy với torch 2.13.0 kênh cu126. Mọi so sánh trong thí nghiệm đối chứng phải chạy trên **một môi trường duy nhất**; nên sinh file khóa phiên bản trên máy chạy số liệu cuối.

---

## 12. Tài liệu tham khảo

Các bài trong `docs/paper tham khảo/` (đã đọc phần tóm tắt, phương pháp và đoạn liên quan; chưa đọc từng trang). Số liệu trích từ văn bản tôi trích xuất từ PDF, cần đối chiếu bản gốc trước khi đưa vào hồ sơ.

| Tài liệu | Dùng để |
|---|---|
| TexControl (sketch cộng ControlNet hai giai đoạn) | Ý khóa viền rồi làm chất liệu; lỗi sinh nhầm thân người |
| Differential Diffusion | Mức thay đổi theo từng vùng, khóa vùng giữ nguyên |
| Texture-Preserving Diffusion (TPD) | Mặt nạ chính xác giữ da và tay; ablation về mặt nạ (FID 27,24 khi bỏ mặt nạ tăng cường so với 8,54) |
| Tiled Diffusion, Structured Pattern Expansion | Lát liền mạch; mở rộng từ mẫu đặt giữa canvas |
| Kizil, Dunhuang, Blue Calico, Ulos (SDXL và StyleGAN) | Hoa văn di sản bằng diffusion; Blue Calico dùng 73 ảnh cho LoRA; Ulos SDXL cho thấy chồng điều kiện có thể tệ hơn |
| VietFashion | Bảng thuộc tính áo dài; không dùng ảnh |
| Verifiable Human Evaluation, Imagen 3, WISE | Chấm cặp mù, báo độ đồng thuận; WiScore chỉ dùng phụ (bài toán tri thức, chưa kiểm cho áo dài) |

Các nguồn đã tra qua tìm kiếm và đọc trang tóm tắt, chưa đọc toàn văn:

| Nguồn | Dùng để |
|---|---|
| Grounded SAM (arXiv 2401.14159) | Tách họa tiết theo từ khóa |
| AM-Adapter (arXiv 2412.03150), Ctrl-X (arXiv 2406.07540) | Bằng chứng IP-Adapter mất chi tiết |
| RePaint (arXiv 2201.09865) | Inpaint giữ vùng đã biết |
| FabricDiffusion (arXiv 2410.01801), Zhang và cộng sự 2011 (ICCV) | Trải phẳng texture từ ảnh chụp |
| Sartor và Peers 2024, ControlMat | Lát texture từ ảnh bằng khuếch tán |
| DreamSim (`ssnl/dreamsim`) | Chỉ số M3, M4 |
| `c2pa-python` | Chữ ký nguồn gốc nội dung (tùy chọn) |

Nêu theo hiểu biết sẵn có, chưa tra lại trong phiên: SAM (Kirillov và cộng sự 2023), Real-ESRGAN, LPIPS, `rembg`, bộ dự đoán thẩm mỹ LAION, Cloudflare Tunnel, ngrok, Vercel. Điều khoản gói miễn phí của các dịch vụ có thể đã đổi.
