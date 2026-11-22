# Danh mục nguồn và quyền sử dụng sáu hiện vật (bản 19/11/2026, cập nhật 22/11/2026)

Tài liệu này trả lời yêu cầu 3 của ban tổ chức: nguồn và quyền sử dụng sáu hiện vật, cách ghi công, lịch sử các bước chỉnh sửa do người làm, và nhãn nội dung có hỗ trợ AI.

## 1. Nguồn dữ liệu hiện vật

Sáu hiện vật là sáu vật của bộ dữ liệu LR3D-CULT2 (mô hình 3D, ảnh render đa góc và texture). Bộ dữ liệu có DOI và giấy phép công bố CC BY 4.0 nên nguồn kiểm chứng được. Mỗi hiện vật có hai ảnh:

- Ảnh render cả bình từ mô hình 3D (camera 1, khung 1), để hiển thị và nhận diện.
- Mảng texture phẳng của cùng vật, là đầu vào đưa vào mô hình sinh.

## 2. Bộ dữ liệu nguồn

- **Tên:** LR3D-CULT2, Vietnamese Ceramic Cultural Artifacts (mô hình 3D, ảnh render đa góc và texture).
- **Tác giả:** Nguyen Le Huu Bao, Nguyen Van Nhat Nam, Nguyen The Trong Nha, Bui Cao Vu (theo trang dataset; đơn vị ghi trên trang: FPT University, Hà Nội).
- **Trang dataset:** <https://data.mendeley.com/datasets/jr23fnrvx2/1>, DOI `10.17632/jr23fnrvx2.1`, công bố ngày 2/3/2026.
- **Giấy phép công bố của bộ dữ liệu:** CC BY 4.0, theo trang dataset.
- **Xuất xứ theo mô tả của bộ dữ liệu:** một phần mô hình được quét quang trắc tại các làng gốm Bát Tràng và Thanh Hà, một phần lấy từ Sketchfab theo giấy phép dùng cho học thuật. Trang không chỉ ra vật nào thuộc nguồn nào, và metadata từng vật chỉ có tên, tâm vật thể, vị trí camera.

## 3. Sáu hiện vật đang dùng

| Mã trong hệ thống | Vật trong dataset | File texture gốc | Cách cắt mảng phẳng | Kích thước mảng phẳng | Trạng thái |
|---|---|---|---|---|---|
| `LR3D_33` | `ceramic_vases_33` | `ceramic_vases_33.png` | Đảo UV nhiều nét mực lam nhất, khung [4000, 3556, 8185, 8151], thu 0,446 lần | 1865×2048 | CC BY 4.0 (cấp bộ dữ liệu); xuất xứ từng vật chưa xác minh |
| `LR3D_61` | `ceramic_vases_61` | `ceramic_vases_61.png` | Khung [38, 2274, 3862, 4057], thu 0,536 lần | 2048×955 | Như trên |
| `LR3D_50` | `ceramic_vases_50` | `ceramic_vases_50.png` | Khung [96, 2492, 4761, 8123], thu 0,364 lần | 1697×2048 | Như trên |
| `LR3D_38` | `ceramic_vases_38` | `ceramic_vases_38.png` | Khung [6, 6, 2107, 3253], thu 0,631 lần. Còn dính một đĩa nhỏ có nhãn kiểm kê ở đáy | 1325×2048 | Như trên |
| `LR3D_97` | `ceramic_vases_97` | `ceramic_vases_97.png` | Khung [3108, 48, 4074, 2252], thu 0,929 lần. Nét lam thưa | 898×2048 | Như trên |
| `LR3D_124` | `ceramic_vases_124` | `ceramic_vases_124.jpeg` | Khung [1182, 314, 2276, 2806], thu 0,822 lần | 899×2048 | Như trên |

**Ảnh hiện vật mặc định** của mỗi mã là ảnh render cả bình (512×512, nền xám) lấy từ ảnh render đa góc của dataset: camera 1, khung 1, góc cố định cho cả sáu vật, không chọn tay. File ở `data/heritage/LR3D_<số>.png`, tên file gốc trong dataset ghi ở trường `render_source` của `lr3d_crops.json`. Mảng phẳng ở `data/heritage/panels/LR3D_<số>.png`.

Thông số đầy đủ (phương pháp mặt nạ, độ phủ UV, số đảo tìm được) ở `data/heritage/lr3d_crops.json`. Kho phần tử cắt từ các mảng này ở `data/elements/` (không commit), mỗi phần tử có bản ghi trong `index.json` kèm mã vật nguồn, DOI và trạng thái giấy phép.

## 3b. Thông tin cho người xem: sổ hoa văn ở Studio (21/11/2026)

**Lưu ở đâu.** Khối `artifact_info` của từng hiện vật trong `data/heritage/metadata.json` (danh mục duy nhất mà API và giao diện đọc). Nguồn dùng chung nằm ở `_meta.artifact_info_sources`, mỗi ý nghĩa hoa văn trỏ tới một khóa nguồn. API `/heritage` trả trường `info`; `scripts/demo/export_demo_data.py` xuất trường này sang `web_ui/data/heritage.json`.

**Hiển thị ra sao:** ở Studio, dưới tên hiện vật có nút "Xem ý nghĩa hoa văn". Bấm vào mở một cuốn sổ hai trang nổi trên trang (không chuyển trang): trang trái là ảnh tĩnh của hiện vật (ảnh tách nền từ `data/heritage/cutouts/`, không dùng khung 3D), tên và dáng bình; trang phải là một đoạn mô tả ngắn về hoa văn và ý nghĩa (`motif_text`), nguồn ảnh (bộ dữ liệu, DOI) và giấy phép CC BY 4.0. Sổ không hiện nguồn của từng ý nghĩa, đối chiếu bảo tàng hay ghi chú kỹ thuật; các căn cứ đó vẫn lưu trong `artifact_info` (từng hoa văn kèm khóa nguồn, `comparison`, `origin`, `origin_note`) và trong mục này, để kiểm chứng khi cần.

**Nguyên tắc biên soạn.**

- Ý nghĩa hoa văn chỉ ghi khi có nguồn bảo tàng: rồng, mây, mẫu đơn (USC Pacific Asia Museum, *Symbols in Chinese Art*); sen (The Met, chú giải hiện vật 1984.297); vân như ý (The Met, chú giải hiện vật 26.271.1a, b: hoa văn cổ áo mây trên vải vóc, y phục). Lá chuối, cây hoa, hoa lá cách điệu chưa tìm được nguồn đáng tin nên chỉ ghi vị trí.
- "Tương đồng" là so sánh phong cách với hiện vật bảo tàng có hồ sơ, không khẳng định niên đại hay nơi làm của vật.
- Xuất xứ từng vật ghi "Chưa xác định". Tên tệp ảnh render gốc của cả sáu vật trong bộ dữ liệu đều có tiền tố `sketchfab_collection_` (trường `render_source` trong `lr3d_crops.json`), nên nhiều khả năng cả sáu thuộc nhóm lấy từ Sketchfab, không phải nhóm quét ở Bát Tràng, Thanh Hà. Đây là suy luận từ tên tệp, chưa được tác giả bộ dữ liệu xác nhận.
- Trước đây nhóm gọi băng hoa văn ở chân bình #124 là "lông vũ"; ngày 22/11/2026 nhóm thống nhất gọi băng này là "lá chuối" (tên quen dùng trên gốm hoa lam; Mia mô tả "plantain leaves" ở bình #97 có cùng dạng) và đã sửa `team_description`, ô thông tin và tên hiện vật #124 cho khớp. Cần chuyên gia chốt tên gọi.

| Hiện vật | Phong cách (tương đồng) | Hiện vật đối chiếu |
|---|---|---|
| `LR3D_33` | Hoa lam Trung Hoa thời Nguyên, thế kỷ 14 | The Met 26.271.1a, b, *Bottle with Peony Scroll* |
| `LR3D_61` | Hoa lam Trung Hoa đầu thời Minh, thế kỷ 15 | The Met 37.191.1, *Jar with dragon*, niên hiệu Tuyên Đức |
| `LR3D_50` | Hoa lam Trung Hoa thời Thanh | The Met 14.40.309, *Bottle with lotus scrolls*, niên hiệu Khang Hy |
| `LR3D_38` | Chưa xác định | Chưa tìm được |
| `LR3D_97` | Hoa lam Việt Nam thế kỷ 15 | Minneapolis Institute of Art 2007.19.2, *Bottle Vase (Yu-hu chun)*, Việt Nam, cuối thế kỷ 15 |
| `LR3D_124` | Chưa xác định, cách vẽ gần hoa lam Trung Hoa | Chưa tìm được |

Bối cảnh Việt Nam lấy từ Bảo tàng Lịch sử Quốc gia: gốm hoa lam Việt xuất hiện từ thời Trần thế kỷ 14, đỉnh cao ở thế kỷ 15 (bài *Bảo vật quốc gia: Bình gốm hoa lam vẽ thiên nga*, 2017); dáng yuhuchun được gọi là bình hình tỳ bà (bài *Đồ gốm Đông Nam Á thế kỷ 15*).

## 4. Cách ghi công

Khi hiển thị hoặc công bố, ghi:

> Hoa văn lấy từ bộ dữ liệu LR3D-CULT2 (Nguyen Le Huu Bao, Nguyen Van Nhat Nam, Nguyen The Trong Nha, Bui Cao Vu), Mendeley Data, phiên bản 1, DOI 10.17632/jr23fnrvx2.1, giấy phép CC BY 4.0. Một phần dữ liệu quét tại Bát Tràng và Thanh Hà, một phần lấy từ Sketchfab; xuất xứ từng vật chưa xác định. Ảnh thiết kế do hệ thống có hỗ trợ AI tạo ra.

Nhãn hiển thị trong ứng dụng: "Gốm men lam · LR3D-CULT2 (Bát Tràng, Thanh Hà)", kèm ghi chú giấy phép ở trường `licenseNote`. Nhãn này lặp lại mô tả của bộ dữ liệu, không khẳng định từng vật là Bát Tràng.

## 5. Lịch sử các bước do người làm

| Ngày | Bước | Người làm |
|---|---|---|
| 18/11/2026 | Quét 120 vật thể, chọn bằng mắt 14 vật có mảng lam trắng sạch | Trợ lý AI đề xuất theo bảng ảnh thu nhỏ |
| 19/11/2026 | Chọn 6 vật trong 14, chọn nhãn nguồn, quyết định thay hiện vật, chọn dùng ảnh render cả bình làm đầu vào mặc định | Nhóm |
| 18 đến 19/11/2026 | Viết mô tả hiện vật (`team_description`) và mô tả cho prompt (`prompt_terms.json`) từ quan sát ảnh | Trợ lý AI, **chưa có người rà soát** (`reviewed_by_human: false`) |

Các bước sau do hệ thống làm tự động, không có chỉnh sửa tay lên ảnh: cắt mảng texture, cắt phần tử, lọc phần tử, sinh họa tiết, ghép lên áo.

## 6. Việc chưa làm

- Nhóm cho biết ngày 19/11/2026 đã được phép dùng bộ dữ liệu cho mục đích phi thương mại. **Hồ sơ chưa lưu bằng chứng**: điền bảng bên dưới và đính kèm thư hoặc tin nhắn xác nhận. Phạm vi cho phép chưa rõ: có gồm hiển thị hoặc cho tải mô hình 3D trên trang công khai không. Giấy phép của bộ dữ liệu là CC BY 4.0 (trang Mendeley Data, xác nhận 21/11/2026), đã ghi cho cả 6 vật kèm ghi công tác giả. Nhóm chưa xác minh riêng nguồn của từng vật (một phần mô hình có thể lấy từ Sketchfab theo giấy phép học thuật).

| Mục | Nội dung cần ghi |
|---|---|
| Người cấp phép (tên, đơn vị) | Chưa ghi |
| Ngày và hình thức (thư điện tử, tin nhắn, trang giấy phép) | Chưa ghi |
| Phạm vi: dùng nội bộ, hiển thị công khai, cho tải mô hình 3D, đăng ảnh kết quả | Chưa ghi |
| Điều kiện kèm theo (cách ghi công, thời hạn) | Chưa ghi |
| File bằng chứng đính kèm | Chưa có |

Các việc khác chưa làm:

- Chưa có chuyên gia di sản hoặc thiết kế xem xét mẫu.
- Nhãn nguồn trong giao diện web (tiêu đề trang, chân trang, các đoạn giới thiệu) vẫn ghi chung "Bát Tràng" ở chín chỗ, chưa đối chiếu với tuyên bố ở mục 4.

## 7. Design Passport: nguồn và thành phẩm (cập nhật 22/11/2026)

Design Passport là file JSON đi kèm mỗi thiết kế, ghi chuỗi các bước từ ảnh nguồn đến thành phẩm. Bộ nộp có 24 file ở `outputs/passports/` (6 hiện vật, mỗi hiện vật 4 mức sáng tạo).

**Các trường liên quan đến nguồn và phiên bản:**

| Trường trong Passport | Nội dung |
|---|---|
| `heritage` | Mã hiện vật, tên, nguồn (`source_title`, `source_url`), đơn vị giữ, giấy phép (`license`), ghi công (`attribution`), mã băm ảnh nguồn (`source_image_sha256`) |
| `artifacts` | Từng file trung gian và thành phẩm: ảnh nguồn, canny, hoa văn, áo thô, áo cuối. Mỗi file có đường dẫn và SHA-256 |
| `process_steps` | Từng bước: ai làm (`ai`, `system`, `human`), công cụ, mã băm đầu vào và đầu ra |
| `versions` | Danh sách phiên bản thiết kế, mỗi bản có mã băm của bản cha (`parent_sha256`). Bản V1 do pipeline sinh, `parent_version` rỗng |
| `edits` | Lịch sử sửa tay. Hiện rỗng ở cả 24 file vì chưa có thiết kế nào được sửa tay |
| `ai_disclosure` | Nhãn "Thiết kế được tạo với sự hỗ trợ của AI" và danh sách bước do AI, người, hệ thống |
| `ledger` | Sổ cái nối mã băm: mỗi dòng chứa mã băm dòng trước. Sửa một dòng thì các dòng sau hỏng |
| `rights` | Kết quả cổng quyền theo mục đích: hiển thị demo, xuất bản công khai, thương mại |

**Kiểm tra toàn vẹn** (ngày 22/11/2026: 24/24 đạt). Chạy tại gốc repo:

```powershell
uv run python -c "import glob, json; from pathlib import Path; from tsds.provenance import passport as P; fs = sorted(glob.glob('outputs/passports/*.json')); ok = sum(bool(P.verify(json.load(open(f, encoding='utf-8')), Path('.'))['ok']) for f in fs); print(ok, '/', len(fs), 'Passport toàn vẹn')"
```

**Giới hạn cần nêu trung thực:**

- Bước `collect_image` (thu thập ảnh) chưa có ngày tải bộ dữ liệu. Passport ghi chú "cần điền".
- Chưa có Passport nào có bước sửa tay (`edits` rỗng). Chức năng có và có test, nhưng chưa có ví dụ trong bộ nộp.
- Hai trường `tool` và `actor` trong một số bước còn ghi đường dẫn mã cũ (ví dụ `scripts/07_describe_heritage.py`, `generation/controlnet.py`) vì Passport được sinh ngày 21/11, trước khi nhóm đổi cấu trúc thư mục. Không sửa tay vì sẽ làm hỏng chuỗi mã băm. Đường dẫn hiện tại: `scripts/data_prep/describe_heritage.py`, `tsds/generation/pattern/controlnet.py`.
- Quyền thương mại: giấy phép CC BY 4.0 của ảnh hiện vật cho phép thương mại, nhưng trọng số LoRA áo dài huấn luyện từ ảnh VietFashion giấy phép CC BY-NC 4.0 (chỉ phi thương mại, xem `docs/ai_disclosure.md`). LoRA có trong mọi thiết kế nên cả hệ thống **chỉ dùng phi thương mại**. Ngày 22/11/2026 nhóm đã sửa cổng quyền (`tsds/provenance/registry.py`, hằng `SYSTEM_NONCOMMERCIAL_REASON`) để `commercial_use` luôn bị chặn, và cập nhật khối `rights` của 24 Passport. Các khối này không nằm trong chuỗi mã băm nên chuỗi vẫn toàn vẹn (24/24). Hiển thị và xuất bản công khai kèm ghi công vẫn được phép.
