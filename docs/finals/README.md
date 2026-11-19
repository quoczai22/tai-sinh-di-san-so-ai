# Hồ sơ vòng chung kết — Tái Sinh Di Sản Số

Nhóm 3 chàng hiệp sĩ mộng mơ · Cuộc thi Sáng tạo trẻ Quốc gia về Trí tuệ nhân tạo 2026, Bảng C.

Bộ tài liệu này chỉ phục vụ vòng chung kết và tập trung vào ba yêu cầu cải tiến của Ban tổ chức (BTC). Mọi con số trong tài liệu đều đọc từ tệp trong repo; chỗ chưa có dữ liệu được ghi là "chưa đo" hoặc "mục tiêu cần đo".

## Đọc theo thứ tự

| Tài liệu | Nội dung |
|---|---|
| [01_AUDIT.md](01_AUDIT.md) | Rà soát bản 09/2026: 13 phát hiện có bằng chứng (dữ liệu lịch sử, xem commit `b1192b0`) |
| [02_APQC.md](02_APQC.md) | AS-IS/TO-BE theo APQC PCF, 6 mục tiêu, 5 nguyên tắc, 5 luồng, danh mục quy trình L3 |
| [03_BPMN.md](03_BPMN.md) | BPMN 2.0 end-to-end, giải thích pool, lane, gateway, nhánh lỗi |
| [04_USE_CASE.md](04_USE_CASE.md) | UML Use Case, lý do include/extend, mô tả ca sử dụng |
| [05_QUALITY_ASSURANCE.md](05_QUALITY_ASSURANCE.md) | Cổng G2/G3, phép đo, ngưỡng, vòng thử lại, kết quả bộ demo 19/11/2026, bộ tiêu chí chuyên gia |
| [06_EXPERIMENTS.md](06_EXPERIMENTS.md) | Thí nghiệm có kiểm soát EXP-A đến EXP-E, thử cách hoàn thiện ảnh |
| [07_PROVENANCE_COPYRIGHT.md](07_PROVENANCE_COPYRIGHT.md) | Danh mục nguồn, tiêu chí tuyển ảnh, cổng quyền, Design Passport, nhãn AI |
| [08_KPI.md](08_KPI.md) | Bảng KPI và cơ chế đo |
| [09_ARCHITECTURE_UI.md](09_ARCHITECTURE_UI.md) | Kiến trúc module, API, giao diện |
| [10_TEST_REPORT.md](10_TEST_REPORT.md) | 249 ca kiểm thử, lỗi phát hiện và đã sửa |
| [11_CHANGELOG.md](11_CHANGELOG.md) | So sánh với bản 09/2026, việc còn lại |
| `diagrams/` | BPMN 2.0 XML, SVG, PlantUML |

## Đối chiếu yêu cầu BTC → tính năng → bằng chứng

### 1. Đánh giá chất lượng thiết kế cuối

| BTC yêu cầu | Đã làm | Bằng chứng |
|---|---|---|
| Đo mức giữ hoa văn và hình dáng áo sau khi hoàn thiện ảnh | Cổng G3: PPS (giữ họa tiết), IoU dáng áo, độ nét, giữ chi tiết mịn, lệch màu, đo trên thiết kế cuối; 24 thiết kế bộ demo đều có kết quả | `quality/`, `outputs/passports/` (mục `quality`), `GET /quality/designs` |
| Tiêu chí loại hoặc thử lại | Ngưỡng PASS/WARN/FAIL có giải thích; vòng thử lại polish (đổi seed, hạ độ nhiễu, trả bản ghép thô); kiểm tra áo nền (tối đa 6 ứng viên); G2 lỗi được phân loại, chưa tự sinh lại | `config/quality_gate.json`, `quality/retry.py`, `generation/garment_lora.py` |
| Chuyên gia di sản và thiết kế đánh giá | Bộ tiêu chí 5 mục, phiếu chấm, gói chấm mù, API ghi phiếu (`POST /passports/{id}/reviews`). Giao diện web không còn trang thẩm định (gỡ 19/11/2026); việc xem xét là bước ngoài hệ thống, kết quả đưa vào báo cáo. **Chưa có phiếu của người thật** | `config/expert_rubric.json`, `outputs/experiments/EXP-D/blind/` |
| Bộ hiện vật – hoa văn – thiết kế cuối kèm phiếu | 24 thiết kế mới, mỗi lần chạy có ảnh hiện vật (`00_reference.png`), hoa văn (`V<n>_pattern.png`), bản ghép thô và thiết kế cuối (`V<n>_aodai.png`); 24 Passport | `outputs/runs/`, `outputs/passports/` |
| Ví dụ bị loại và được sửa | 3 thiết kế của hiện vật HV12 bị G2 loại (đường nối); polish 0,30 làm mất họa tiết được đổi sang 0,20 kèm khoá họa tiết; khoá họa tiết cũ làm mất nét mảnh được sửa (`dog_sigma_low` 0,3) | [05](05_QUALITY_ASSURANCE.md) mục "Ví dụ", `evaluation/polish_finish_trial.csv` |

### 2. Đối chứng có kiểm soát và nhiều seed

| BTC yêu cầu | Đã làm | Bằng chứng |
|---|---|---|
| Cố định prompt và bảng màu, chỉ đổi một yếu tố | EXP-A chỉ đổi ControlNet; EXP-B bước hoàn thiện; EXP-C bước ghép; EXP-D nguồn áo nền; EXP-E nguồn ảnh nạp. Kế hoạch đổi hơn một yếu tố bị mã từ chối | `evaluation/experiments/`, `tests/test_experiment.py` |
| Nhiều seed | EXP-A 5 seed, EXP-B 3, EXP-D 5, EXP-E 3 | `outputs/experiments/EXP-*/plan.csv` |
| Đánh giá mù | Gói chấm mù có mã ẩn danh, thứ tự xáo theo người chấm (EXP-D, 60 ảnh); ảnh của gói không đưa vào repo | `outputs/experiments/EXP-D/blind/` |
| CSV cấu hình, bảng điểm người chấm, thống kê độ phân tán | `plan.csv`, `results.csv`, `ratings_*.csv`, `summary.json` (trung bình, độ lệch chuẩn, KTC 95%, hệ số biến thiên, alpha, kiểm định cặp) | `outputs/experiments/` |
| Trạng thái thật | EXP-B, C, D, E đã chạy; EXP-A chưa chạy; chưa có phiếu chấm mù | [06](06_EXPERIMENTS.md) |

### 3. Bản quyền, nguồn gốc, truy vết biên tập

| BTC yêu cầu | Đã làm | Bằng chứng |
|---|---|---|
| Nguồn và giấy phép của 6 hiện vật đang dùng (LR3D-CULT2) và của LoRA | Danh mục 10 trường, trường thiếu được ghi là thiếu; Passport ghi nguồn dữ liệu và giấy phép CC BY-NC 4.0 của LoRA, trích dẫn VietFashion | `data/heritage/metadata.json`, `data/lora/README.md`, `GET /provenance/catalog` |
| Ghi công | Câu ghi công từng hiện vật, in vào nhãn khi xuất | `attribution`, `provenance/labeling.py` |
| Lịch sử biên tập thủ công | Mỗi lần sửa là phiên bản mới có băm cha, ghi người sửa, công cụ, nội dung; chạy lại G3 | `POST /passports/{id}/edits`, mục `edits`, `versions` |
| Nhãn "có hỗ trợ AI" | Dải nhãn nhìn thấy được + siêu dữ liệu PNG | `GET /passports/{id}/export` |
| Danh mục nguồn và Design Passport nguồn → sản phẩm | Passport có chuỗi truy vết và sổ cái băm; 24/24 hợp lệ. Giao diện web không còn trang Passport (gỡ 19/11/2026); Passport đọc qua API và tệp JSON | `outputs/passports/`, `GET /passports/{id}` |
| Rủi ro còn lại | Chưa hiện vật nào có giấy phép từng vật (0/6); cổng quyền đang chặn xuất bản công khai; trọng số LoRA chỉ dùng phi thương mại | [07](07_PROVENANCE_COPYRIGHT.md) |

## Tự đánh giá

| Tiêu chí | Mức đạt | Còn thiếu |
|---|---|---|
| UI/UX | 3 trang cho người xem (Trang chủ, Studio đầu vào → đầu ra, Bộ sưu tập), kiểm tra ở 1440 px và 390 px | Chưa thử với người dùng thật |
| Quy trình nghiệp vụ | 18 bước đều có phần tử BPMN; mỗi gateway gắn với mã | – |
| BPMN | XML chuẩn BPMN 2.0, đọc được bằng bpmn-moddle không cảnh báo; có kiểm thử ngữ nghĩa | – |
| UML | 7 tác nhân, 19 ca, include/extend có lý do | 3 ca mới là kế hoạch hoặc chạy một phần |
| APQC | Tham chiếu PCF 7.4 ở cấp hạng mục và nhóm, có AS-IS/TO-BE, chủ, kiểm soát, KPI | Mã PCF sâu hơn cần đối chiếu bản chính thức |
| Chất lượng AI | Đo được thiết kế cuối, có chỉ số giữ chi tiết mịn, có định tuyến và vòng thử lại | Ngưỡng chưa hiệu chỉnh với chuyên gia; còn mất khoảng 13 đến 14% chi tiết mịn so với bản ghép thô |
| Thí nghiệm | Có kiểm soát bằng mã, bốn thí nghiệm đã chạy (B, C, D, E) | EXP-A chưa chạy; phiếu chấm mù chưa có |
| Nguồn gốc | Truy vết đầy đủ, phát hiện sửa trái phép | Băm đầu chuỗi chưa neo ra ngoài |
| Bản quyền | Minh bạch, hệ thống tự chặn | Chưa có giấy phép từng vật; LoRA chỉ dùng phi thương mại |
| Độ tin cậy | Không vỡ endpoint cũ, 249 ca kiểm thử | Sinh ảnh GPU chỉ kiểm thử thủ công |
| Mở rộng | Cấu hình có phiên bản, lớp lưu trữ tách riêng | Một tiến trình, một GPU |
