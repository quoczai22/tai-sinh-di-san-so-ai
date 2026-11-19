# Hồ sơ vòng chung kết — Tái Sinh Di Sản Số

Nhóm 3 chàng hiệp sĩ mộng mơ · Cuộc thi Sáng tạo trẻ Quốc gia về Trí tuệ nhân tạo 2026, Bảng C.

Bộ tài liệu này chỉ phục vụ vòng chung kết và tập trung vào ba yêu cầu cải tiến của Ban tổ chức (BTC). Mọi con số trong tài liệu đều đọc từ tệp trong repo; chỗ chưa có dữ liệu được ghi là "chưa đo" hoặc "mục tiêu cần đo".

## Đọc theo thứ tự

| Tài liệu | Nội dung |
|---|---|
| [01_AUDIT.md](01_AUDIT.md) | Rà soát bản 09/2026: 13 phát hiện có bằng chứng |
| [02_APQC.md](02_APQC.md) | AS-IS/TO-BE theo APQC PCF, 6 mục tiêu, 5 nguyên tắc, 5 luồng, danh mục quy trình L3 |
| [03_BPMN.md](03_BPMN.md) | BPMN 2.0 end-to-end, giải thích pool, lane, gateway, nhánh lỗi |
| [04_USE_CASE.md](04_USE_CASE.md) | UML Use Case, lý do include/extend, mô tả ca sử dụng |
| [05_QUALITY_ASSURANCE.md](05_QUALITY_ASSURANCE.md) | Cổng G2/G3, phép đo, ngưỡng, kết quả 24 thiết kế, bộ tiêu chí chuyên gia |
| [06_EXPERIMENTS.md](06_EXPERIMENTS.md) | Thí nghiệm có kiểm soát EXP-A, EXP-B, EXP-C |
| [07_PROVENANCE_COPYRIGHT.md](07_PROVENANCE_COPYRIGHT.md) | Danh mục nguồn, tiêu chí tuyển ảnh, cổng quyền, Design Passport, nhãn AI |
| [08_KPI.md](08_KPI.md) | Bảng KPI và cơ chế đo |
| [09_ARCHITECTURE_UI.md](09_ARCHITECTURE_UI.md) | Kiến trúc module, API, giao diện |
| [10_TEST_REPORT.md](10_TEST_REPORT.md) | 130 ca kiểm thử, lỗi phát hiện và đã sửa |
| [11_CHANGELOG.md](11_CHANGELOG.md) | So sánh với bản 09/2026, việc còn lại |
| `diagrams/` | BPMN 2.0 XML, SVG, PlantUML |

## Đối chiếu yêu cầu BTC → tính năng → bằng chứng

### 1. Đánh giá chất lượng thiết kế cuối

| BTC yêu cầu | Đã làm | Bằng chứng |
|---|---|---|
| Đo mức giữ hoa văn và hình dáng áo sau img2img | Cổng G3: PPS (giữ họa tiết), IoU dáng áo, độ nét, lệch màu, đo trên thiết kế cuối | `quality/`, `evaluation/quality_gate_legacy.csv` |
| Tiêu chí loại hoặc sinh lại | Ngưỡng PASS/WARN/FAIL có giải thích; định tuyến sinh lại (tối đa 3 lần) hoặc sửa | `config/quality_gate.json` |
| Chuyên gia di sản và thiết kế đánh giá | Bộ tiêu chí 5 mục, chấm mù, API ghi phiếu | `config/expert_rubric.json`, khu vực "Thẩm định chuyên gia" |
| Bộ hiện vật – hoa văn – thiết kế cuối kèm phiếu | 24 ảnh đối chiếu, 24 Passport | `docs/evidence/quality_gate/`, `outputs/passports/` |
| Ví dụ bị loại và được sửa | HV01 V1, V2 bị G2 loại; 19 thiết kế được khoá họa tiết, 10 đạt sau sửa | [05](05_QUALITY_ASSURANCE.md) mục "Ví dụ" |

### 2. Đối chứng có kiểm soát và nhiều seed

| BTC yêu cầu | Đã làm | Bằng chứng |
|---|---|---|
| Cố định prompt và bảng màu, chỉ đổi ControlNet hoặc bước ghép | EXP-A chỉ đổi ControlNet; EXP-B chỉ đổi bước hoàn thiện; EXP-C chỉ đổi bước ghép. Kế hoạch đổi hơn một yếu tố bị mã từ chối | `evaluation/experiments/`, `tests/test_experiment.py` |
| Nhiều seed | EXP-A 5 seed, EXP-B 3 seed | `outputs/experiments/EXP-A/plan.csv`, `EXP-B/plan.csv` |
| Đánh giá mù | Gói chấm mù có mã ẩn danh, thứ tự xáo theo người chấm | `outputs/experiments/EXP-C/blind/` |
| CSV cấu hình, bảng điểm người chấm, thống kê độ phân tán | `plan.csv`, `results.csv`, `ratings_*.csv`, `summary.json` (trung bình, độ lệch chuẩn, KTC 95%, hệ số biến thiên, alpha, kiểm định cặp) | `outputs/experiments/` |
| Trạng thái thật | EXP-C đã chạy, chờ phiếu; EXP-A, EXP-B chờ GPU | [06](06_EXPERIMENTS.md) |

### 3. Bản quyền, nguồn gốc, truy vết biên tập

| BTC yêu cầu | Đã làm | Bằng chứng |
|---|---|---|
| Nguồn và giấy phép của 6 hiện vật | Danh mục 10 trường, trường thiếu được ghi là thiếu | `data/heritage/metadata.json`, khu vực "Nguồn và bản quyền" |
| Ghi công | Câu ghi công từng hiện vật, in vào nhãn khi xuất | `attribution`, `provenance/labeling.py` |
| Lịch sử biên tập thủ công | Mỗi lần sửa là phiên bản mới có băm cha, ghi người sửa, công cụ, nội dung; chạy lại G3 | `POST /passports/{id}/edits`, mục `edits`, `versions` |
| Nhãn "có hỗ trợ AI" | Dải nhãn nhìn thấy được + siêu dữ liệu PNG | `GET /passports/{id}/export` |
| Danh mục nguồn và Design Passport nguồn → sản phẩm | Passport có chuỗi truy vết và sổ cái băm; 24/24 hợp lệ | `outputs/passports/`, khu vực "Design Passport" |
| Rủi ro còn lại | Chưa hiện vật nào có giấy phép; cổng quyền đang chặn xuất bản công khai | [07](07_PROVENANCE_COPYRIGHT.md) |

## Tự đánh giá

| Tiêu chí | Mức đạt | Còn thiếu |
|---|---|---|
| UI/UX | 3 trang cho người xem (Trang chủ, Studio đầu vào → đầu ra, Bộ sưu tập), kiểm tra ở 1440 px và 390 px | Chưa thử với người dùng thật |
| Quy trình nghiệp vụ | 18 bước đều có phần tử BPMN; mỗi gateway gắn với mã | – |
| BPMN | XML chuẩn BPMN 2.0, đọc được bằng bpmn-moddle không cảnh báo; có kiểm thử ngữ nghĩa | – |
| UML | 7 tác nhân, 19 ca, include/extend có lý do | 3 ca mới là kế hoạch hoặc chạy một phần |
| APQC | Tham chiếu PCF 7.4 ở cấp hạng mục và nhóm, có AS-IS/TO-BE, chủ, kiểm soát, KPI | Mã PCF sâu hơn cần đối chiếu bản chính thức |
| Chất lượng AI | Đo được thiết kế cuối, có định tuyến | Ngưỡng chưa hiệu chỉnh với chuyên gia |
| Thí nghiệm | Có kiểm soát bằng mã, một thí nghiệm đã chạy | Hai thí nghiệm GPU và phiếu chuyên gia chưa có |
| Nguồn gốc | Truy vết đầy đủ, phát hiện sửa trái phép | Băm đầu chuỗi chưa neo ra ngoài |
| Bản quyền | Minh bạch, hệ thống tự chặn | Chưa có giấy phép thật |
| Độ tin cậy | Không vỡ endpoint cũ, 130 ca kiểm thử | Sinh ảnh GPU chỉ kiểm thử thủ công |
| Mở rộng | Cấu hình có phiên bản, lớp lưu trữ tách riêng | Một tiến trình, một GPU |
