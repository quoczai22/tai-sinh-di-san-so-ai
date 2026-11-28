# Cổng kiểm tra ảnh đầu vào

Cổng này chặn ảnh không thuộc miền gốm và hoa văn trước khi ảnh đi vào pipeline. Mã ở `tsds/quality/input_gate.py`, cấu hình ở `config/input_gate.json`.

## Phạm vi

- **Ảnh được kiểm:** ảnh nạp vào ControlNet, gồm ảnh hiện vật trong `data/heritage/` và phần tử trong `data/elements/`. Cổng chạy ở đầu `generate_design_set`, trước khi sinh áo, nên ảnh xấu dừng trước khi tốn GPU.
- **Ảnh không được kiểm:** ảnh người dùng tải lên ở `POST /passports/{id}/edits`. `POST /generate` chỉ nhận `heritage_id` và `seed`, nên người dùng không đưa ảnh vào pipeline. Cổng bảo vệ kho dữ liệu của nhóm (nhầm file, thay file, nạp hiện vật mới), không phải chặn tấn công từ người dùng ngoài.
- **Đây là cổng "liên quan miền", không phải bộ lọc an toàn.** Ảnh nhạy cảm chưa được đo. Bộ lọc ảnh đầu ra vẫn cần (xem `docs/ai_disclosure.md` mục 4).

## Cách chấm

Ảnh được đặt lên nền trắng (nếu có kênh trong suốt), đệm vuông, nhúng bằng CLIP ViT-B/32 chạy trên CPU. Cổng chỉ dùng **cách nguyên mẫu (P)**:

- Điểm `s_proto` là trung bình `k` (hiện là 3) độ giống cosine cao nhất giữa ảnh và các ảnh tham chiếu trong kho (6 ảnh hiện vật và tối đa 10 phần tử mỗi bình, khoảng 90 ảnh).
- Có **một ngưỡng** `t`. `s_proto` lớn hơn hoặc bằng `t` là pass, nhỏ hơn là block. Không có vùng warn.

Cách chấm bằng từ khóa (T: so ảnh với câu mô tả trong miền và ngoài miền) đã được thử rồi bỏ. Lý do ở mục Kết quả.

## Hành vi khi chạy

| Kết quả | Việc xảy ra |
|---|---|
| pass | Chạy tiếp như cũ. Passport có khối `generation.input_gate` ghi điểm từng ảnh |
| block | Ghi log, ném `InputRejected`, lượt sinh dừng trước khi sinh áo. API trả job `failed` với thông báo chung, không nêu điểm hay ngưỡng. File trong kho **không bị xóa hay di chuyển** |
| Cổng lỗi | Chặn như block, ghi `input_gate_error`. Ảnh do nhóm kiểm soát nên chọn an toàn thay vì cho qua |

Log ở `outputs/audit/input_gate.jsonl`, mỗi dòng là một JSON: `event` (`input_blocked`, `input_gate_error`; ảnh pass không ghi log), `heritage_id`, `label`, `sha256` của ảnh, `s_proto`, `verdict`, `config_version`. `config_version` có hậu tố ghi cách chấm (hiện là `input-gate/20261128-proto`, chỉ nguyên mẫu); đổi cách chấm thì đổi hậu tố, để mỗi dòng log cho biết bản cổng nào đã ghi nó. Không ghi IP và không ghi nội dung ảnh. Cổng tự ghi log vì tầng `quality` không được import tầng `api` (xem `tests/test_layering.py`).

Khối `generation.input_gate` cũng được ghi vào sổ cái của Passport, nên `verify()` báo lỗi nếu sửa khối này. Passport tạo từ bản cổng cũ (có `margin_T`, `verdict_T`, vùng warn) vẫn đọc và kiểm được.

## Tập thử và cách đo

Tập thử ở `data/eval/input_filter/` (ảnh không commit, `labels.csv` và `meta_*.json` commit được). Dựng bằng `uv run python scripts/eval/prepare_input_gate_data.py --step all`.

| Nhóm | Nội dung | Nhãn đúng |
|---|---|---|
| A | 6 ảnh hiện vật và 24 phần tử (3 mỗi bình) | pass |
| B | 20 ảnh render của bình chưa dùng trong LR3D-CULT2 (112 bình còn lại) | pass |
| C | 40 bản biến dạng của A (đổi sáng, nén JPEG, xoay, cắt lệch, đổi nền, thu nhỏ) | pass |
| D | 39 ảnh lạc đề vô hại từ 4 bộ Roboflow Universe (đều CC BY 4.0): 10 thuốc lá (người đang hút), 10 selfie, 9 đồ ăn, 10 phương tiện giao thông. Mỗi bộ lấy ngẫu nhiên 10 ảnh từ tập train (seed 2026), nguồn và tệp gốc ghi ở `images/D/sources.csv`. Đã bỏ `food_04` (họa tiết nho trên bề mặt giống đĩa sứ, nhãn "chặn" không chắc đúng) | block |

Chạy đo: `uv run python scripts/eval/run_input_gate_eval.py` (thêm `--write-config` để ghi ngưỡng). Đo kiểu "bỏ một bình ra": ảnh của bình X được chấm với nguyên mẫu đã loại hết ảnh của bình X, nên điểm nhóm A và C luôn là điểm với bình chưa từng thấy. Ngưỡng chọn trên nửa `tune`: điểm giữa của phân vị 10% điểm ảnh hợp lệ và phân vị 90% điểm ảnh lạc đề. Bảng báo trên nửa `test` kèm khoảng tin cậy Wilson 95%. Kết quả: `outputs/experiments/input_gate/results.csv` và `summary.json`.

## Kết quả

Đo ngày 2026-11-28, chỉ cách P, một ngưỡng `t` = 0.7115 (`k` = 3). Bảng là nửa `test`.

| Nhóm | Nhãn đúng | n | pass | block | Tỉ lệ đúng |
|---|---|---|---|---|---|
| A | pass | 15 | 15 | 0 | 100% (80% đến 100%) |
| B | pass | 10 | 10 | 0 | 100% (72% đến 100%) |
| C | pass | 20 | 20 | 0 | 100% (84% đến 100%) |
| D | block | 16 | 0 | 16 | 100% (81% đến 100%) |

Trên nửa `tune` kết quả cũng không có ảnh nào sai (D chặn 23/23).

Lý do bỏ cách T: trên cùng dữ liệu, T riêng lẻ chặn nhầm 2/15 ảnh A và 3/20 ảnh C ở `test` (ví dụ `E_ceramic_vases_15_e017`, điểm gần 0), trong khi P không chặn nhầm ảnh nào. Gộp T với P theo "cả hai cùng chặn" làm lọt 2 ảnh xe buýt ở `tune`, còn gộp theo "một cách chặn là chặn" thì chặn nhầm ảnh hợp lệ như T. Cả hai cách gộp đều không tốt hơn P riêng lẻ.

Cần đọc kèm: mỗi nhóm chỉ vài chục ảnh (D có 16 ở `test`), khoảng tin cậy còn rộng, và ngưỡng chọn trên nửa `tune` nên con số 100% có thể cao hơn thực tế.

## Giới hạn đã biết

- Đo bằng CLIP B/32, hiểu biết văn hóa Việt hạn chế, và CLIP bị đánh lừa được bằng nhiễu đối kháng hoặc chữ chèn trong ảnh. Không dùng cổng này như biện pháp chống tấn công có chủ đích.
- Cách P so với **ảnh mẫu trong kho**. Hiện vật mới có kiểu dáng hoặc hoa văn khác hẳn kho có thể bị chặn nhầm. Đo kiểu "bỏ một bình ra" ước lượng được điều này với 8 bình hiện có, nhưng chưa thử với loại gốm khác (men rạn, gốm đất nung, sứ Huế). Khi nạp hiện vật mới nên chạy lại bước đo và cập nhật nguyên mẫu.
- Nhóm B cùng bộ dữ liệu, cùng camera và ánh sáng với nhóm A, nên dễ hơn ảnh gốm chụp ngoài đời.
- Nhóm D toàn ảnh lạc đề dễ, chỉ 4 chủ đề, 39 ảnh. Chưa đo ảnh gần miền nhưng sai (sườn xám, kimono, sứ Trung Hoa), ảnh có chữ đánh lừa, vật nhỏ ghép vào ảnh hợp lệ, ảnh nhạy cảm.
- Ảnh người trong D (thuốc lá, selfie) là ảnh người thật. Chúng nằm ngoài repo (`.gitignore`), không đưa vào báo cáo hay trang web.
- Ảnh **panel** (đầu vào mặc định của pipeline) chưa có trong nhóm A và chưa có trong nguyên mẫu. Cổng cho panel pass ở lượt sinh thật, nhưng độ chính xác với loại ảnh này chưa được đo có hệ thống. Panel ngang (2048 x 955) bị đệm vuông nên mép trên dưới là khoảng trắng.
- Ngưỡng chọn trên nửa `tune` nhỏ (15 ảnh A, 10 B, 20 C, 23 D), nên trong mẫu. `calibrated: true` chỉ có nghĩa đã đo với D từ 30 ảnh, không có nghĩa ngưỡng đã được kiểm chứng ngoài kho này.
- Không có vùng warn: ảnh sát ngưỡng bị quyết định ngay là pass hoặc block, không có bước QC xem lại.
- **Thay đổi hành vi:** trước đây file phần tử bị hỏng thì `generate_design_set` quay về ảnh hiện vật mặc định. Nay cổng mở mọi ảnh trước, nên file hỏng làm cổng lỗi và lượt sinh bị chặn (cổng lỗi thì chặn). Nhánh quay về ảnh mặc định chỉ còn tác dụng với lỗi xảy ra sau cổng.
- Khi cùng một đường dẫn có nhiều nhãn (ví dụ `panel` lặp 4 lần), kết quả chỉ ghi nhãn đầu tiên.
- Log `input_gate.jsonl` chưa có `job_id`, khó nối với job trong API.
- Bộ nhớ đệm nguyên mẫu ở `outputs/input_gate/` nằm theo `OUTPUTS_DIR`, còn log theo biến `DH_OUTPUT_DIR`. Hai chỗ có thể lệch nhau khi triển khai.
- Lượt sinh đầu tiên sau khi khởi động tính nguyên mẫu (khoảng 90 ảnh trên CPU, cỡ chục giây), các lượt sau dùng đệm.

## Hướng phát triển sau

- Thêm nhóm E (gần miền nhưng sai), F (chữ đánh lừa), G (vật nhỏ ghép vào ảnh hợp lệ), H (ảnh nhạy cảm, cần nguồn dữ liệu học thuật có điều khoản sử dụng, lưu ngoài repo), I (tệp bất thường).
- Thêm 6 ảnh panel vào nhóm A và nguyên mẫu.
- Chia ảnh thành ô và lấy điểm xấu nhất để bắt vật nhỏ. Thử CLIP ViT-L/14.
- Cổng cho `POST /passports/{id}/edits` với miền áo dài và độ giống phiên bản cha.
- Gộp log vào `audit.jsonl`. Bộ nhớ đệm kết quả theo SHA-256 của ảnh.
- Hiệu chỉnh ngưỡng bằng dữ liệu thật; hai người gắn nhãn độc lập; thay nhóm C giả lập bằng bản chỉnh sửa thật.
- Thử lại cách từ khóa (T) với câu mô tả tốt hơn nếu cần bắt ảnh gần miền.
- Bộ lọc đầu ra và bộ lọc prompt.
