# 08. Bảng KPI và cơ chế đo

Quy ước: cột **Hiện tại** chỉ ghi số đã đo được từ dữ liệu trong repo, kèm nguồn. Chỗ chưa có dữ liệu ghi "Chưa đo". Cột **Mục tiêu** là đề xuất của nhóm, chưa phải kết quả; chỗ chưa đủ cơ sở để đặt số thì ghi "Đặt sau khi có dữ liệu".

Mã quy trình L3 tham chiếu [02_APQC.md](02_APQC.md).

## Chất lượng thiết kế (yêu cầu BTC 1)

| Mã | KPI | Công thức | Hiện tại | Mục tiêu | Nguồn, cách đo | L3 | Chủ |
|---|---|---|---|---|---|---|---|
| K01 | Tỉ lệ thiết kế qua G3 ngay lần đầu | Số bản img2img có G3 = PASS / tổng | 0/24 (0%), ngày 06/09/2026 | Đặt sau EXP-B (chọn strength) | `evaluation/quality_gate_legacy.csv`; Passport mới ghi tự động | 2.5, 3.1 | QC Officer |
| K02 | Tỉ lệ sửa tự động thành công | Số thiết kế G3 FAIL trở thành không FAIL sau khoá họa tiết / số thiết kế được sửa | 19/19 (10 PASS, 9 WARN) | Giữ ≥ 90%, **và** chuyên gia không đánh giá bản sửa kém hơn bản img2img (EXP-B) | như trên | 3.2 | QC Officer |
| K03 | Mức giữ họa tiết của thiết kế được chuyển chuyên gia | Trung vị PPS của phiên bản mới nhất | Trước sửa 0,36; sau sửa 0,80 (n = 19) — PPS sau sửa cao do cách làm, xem [05](05_QUALITY_ASSURANCE.md) | ≥ 0,60 (ngưỡng cảnh báo hiện hành) | Passport, mục `quality` | 3.2 | QC Officer |
| K04 | Tỉ lệ hoa văn rò dáng bình | Số G2 FAIL do VLS / tổng | 2/24 | Đặt sau EXP-A | như K01 | 2.4 | Hệ thống |
| K05 | Đồng thuận giữa cổng tự động và chuyên gia | Cohen's kappa giữa "cổng cho chuyển chuyên gia" và "chuyên gia duyệt" | Chưa đo (0 phiếu) | Đo khi ≥ 30 phiếu; κ ≥ 0,40 mới giữ phép đo ở vai trò chặn | Passport `quality` + `reviews` | 5.4 | BA, QC Officer |
| K06 | Độ tin cậy giữa người chấm | Krippendorff's alpha (khoảng) theo tiêu chí | Chưa đo | α ≥ 0,667 trước khi dùng điểm trung bình để kết luận | `outputs/experiments/*/summary.json` | 3.3 | QC Officer |
| K14 | Tỉ lệ được phê duyệt sau thẩm định | Số "đạt" / số phiếu | Chưa đo | Đặt sau khi có dữ liệu | Passport `reviews` | 3.4 | Chuyên gia |

## Thử nghiệm có kiểm soát (yêu cầu BTC 2)

| Mã | KPI | Công thức | Hiện tại | Mục tiêu | Nguồn, cách đo | L3 | Chủ |
|---|---|---|---|---|---|---|---|
| K07 | Dao động theo seed | Hệ số biến thiên (sd / trung bình) của PPS theo seed ở từng mức trọng số | Chưa đo (EXP-A chờ GPU) | Báo cáo kèm mọi kết luận; không đặt ngưỡng | `outputs/experiments/EXP-A/summary.json` | 1.1 | BA |
| K08 | Tỉ lệ thí nghiệm hợp lệ đơn biến | Kế hoạch qua `validate_plan` / kế hoạch dùng làm bằng chứng | 3/3 | 100% | `python -m evaluation.experiment plan …` | 1.1 | BA |
| K18 | Số lượt chạy hoàn tất theo kế hoạch | Lượt `completed` / lượt trong `plan.csv` | EXP-C 24/24; EXP-A 0/60; EXP-B 0/36 | 100% trước khi phân tích | `results.csv` | 1.1 | BA |

## Nguồn gốc và bản quyền (yêu cầu BTC 3)

| Mã | KPI | Công thức | Hiện tại | Mục tiêu | Nguồn, cách đo | L3 | Chủ |
|---|---|---|---|---|---|---|---|
| K09 | Độ đầy đủ hồ sơ nguồn | Số trường bắt buộc có giá trị / 10, theo hiện vật | 7/10 ở cả 6 hiện vật | 10/10 với mọi hiện vật đang dùng | `provenance/registry.py::completeness` | 4.1, 4.2 | Quản trị dữ liệu |
| K10 | Tỉ lệ hiện vật đang dùng được phép xuất bản | Hiện vật `active` qua cổng `publish_public` / số hiện vật `active` | 0/3 | 100% trước khi xuất bản công khai bất kỳ thiết kế nào | `GET /provenance/catalog` | 2.2 | Quản trị dữ liệu |
| K11 | Toàn vẹn Passport | Passport qua `verify` / tổng | 24/24 | 100%, kiểm mỗi lần chạy bộ kiểm thử | `tests/test_passport.py`, khu vực "Design Passport" | 4.3, 4.4 | Hệ thống |
| K16 | Ảnh xuất có nhãn AI | Ảnh xuất qua API có dải nhãn và siêu dữ liệu / ảnh xuất qua API | 100% (theo thiết kế: endpoint xuất luôn gắn nhãn; có ca kiểm thử) | 100% | `tests/test_api.py` | 4.4 | Hệ thống |
| K19 | Thư xin phép đã gửi | Hiện vật `active` có `permission_request` khác `not_sent` / số hiện vật `active` chưa có quyền | 0/3 | 100% trong 1 tuần | `data/heritage/metadata.json` | 2.2 | Quản trị dữ liệu |

## Vận hành

| Mã | KPI | Công thức | Hiện tại | Mục tiêu | Nguồn, cách đo | L3 | Chủ |
|---|---|---|---|---|---|---|---|
| K12 | Thời gian sinh một biến thể | Trung vị cột `duration_s` | 5,62 giây (n = 24, RTX 4060 Laptop 8 GB, ngày 06/09/2026) | Không tăng quá 2 lần khi thêm cổng chất lượng | `evaluation/variants.csv`; manifest lần chạy | 2.4, 2.5 | Hệ thống |
| K13 | Thời gian chờ thẩm định | Thời điểm phiếu − thời điểm chuyển "chờ chuyên gia" | Chưa đo | Đặt sau khi có dữ liệu | Thời điểm trong sổ cái Passport | 3.3 | QC Officer |
| K17 | Số lần sinh lại trước khi qua G2 | Trung bình số lần sinh lại / thiết kế | Chưa đo | ≤ 1; vượt 3 lần thì chuyển người (đã thực thi) | Sổ cái Passport | 2.4 | Hệ thống |
| K15 | Phản hồi người dùng | Tỉ lệ phiên người dùng chọn được phương án đề cử | Chưa đo (chưa có phiếu phản hồi) | Đặt sau khi có dữ liệu | Nhật ký audit + phiếu phản hồi (kế hoạch) | 1.2, 5.3 | BA |

## Cơ chế đo

- **Tự động**: các KPI K01–K04, K09–K12, K16–K18 đọc thẳng từ tệp CSV/JSON do hệ thống ghi. Không có bước nhập tay.
- **Theo sự kiện**: K13, K17 tính từ thời điểm trong sổ cái Passport (mỗi sự kiện có thời điểm và đã được băm nối chuỗi nên không sửa lùi được mà không bị phát hiện).
- **Theo phiếu**: K05, K06, K14 cần phiếu chuyên gia. Bộ phân tích `evaluation/experiment.py analyze` tính alpha; kappa tính khi hiệu chỉnh ngưỡng ([05](05_QUALITY_ASSURANCE.md)).
- Khu vực "Tổng quan" trên giao diện hiển thị cùng bảng này; ô chưa đo hiện chữ "Mục tiêu cần đo", không hiện số.
