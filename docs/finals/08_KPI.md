# 08. Bảng KPI và cơ chế đo

Quy ước: cột **Hiện tại** chỉ ghi số đã đo được từ dữ liệu trong repo, kèm nguồn. Chỗ chưa có dữ liệu ghi "Chưa đo". Cột **Mục tiêu** là đề xuất của nhóm, chưa phải kết quả; chỗ chưa đủ cơ sở để đặt số thì ghi "Đặt sau khi có dữ liệu".

Mã quy trình L3 tham chiếu [02_APQC.md](02_APQC.md).

## Chất lượng thiết kế (yêu cầu BTC 1)

| Mã | KPI | Công thức | Hiện tại | Mục tiêu | Nguồn, cách đo | L3 | Chủ |
|---|---|---|---|---|---|---|---|
| K01 | Tỉ lệ thiết kế qua G3 ngay lần đầu | Số thiết kế có G3 = PASS / tổng | 20/24 (83%) bộ demo seed 42 (20/11/2026), 55/72 (76%) cả ba seed; mọi thiết kế không đạt G3 đều do giữ chi tiết mịn dưới 0,85 (thấp nhất 0,625); bộ 19/11/2026: 14/24 (58%); bản 06/09/2026: 0/24 | Đặt sau khi hiệu chỉnh ngưỡng với phiếu chuyên gia | Passport mục `quality`; `GET /quality/designs` | 2.5, 3.1 | QC Officer |
| K02 | Tỉ lệ sửa tự động thành công | Số thiết kế G3 FAIL trở thành không FAIL sau khoá họa tiết / số thiết kế được sửa | Khoá họa tiết đã thành bước mặc định của luồng; không còn thiết kế G3 FAIL (0/24 ở bộ seed 42, 0/72 cả ba seed). Bản 06/09/2026: 19/19 sau sửa (10 PASS, 9 WARN) | Giữ 0 thiết kế G3 FAIL, **và** chuyên gia không đánh giá bản có khoá kém bản không khoá | Passport; [05](05_QUALITY_ASSURANCE.md) | 3.2 | QC Officer |
| K03 | Mức giữ họa tiết của thiết kế được chuyển chuyên gia | Trung vị PPS của phiên bản mới nhất | 0,953 (n = 24, thấp nhất 0,903; cả 72 thiết kế: 0,952). PPS cao một phần do cách làm (khoá họa tiết chép lại nét bản ghép), xem [05](05_QUALITY_ASSURANCE.md). Bản 06/09/2026: 0,36 trước sửa | ≥ 0,60 (ngưỡng cảnh báo hiện hành) | Passport, mục `quality` | 3.2 | QC Officer |
| K04 | Tỉ lệ hoa văn rò dáng bình | Số G2 FAIL do VLS / tổng | 0/24 (VLS lớn nhất 0,221, 3 thiết kế ở mức cảnh báo). G2 FAIL chung 2/24, cả 2 do đường nối (hiện vật LR3D_124); cả ba seed: 0/72 do VLS (lớn nhất 0,362, dưới ngưỡng lỗi 0,40), 4/72 FAIL đều do đường nối ở LR3D_124. VLS **bỏ sót** hoa văn mang dáng cả bình khi bình choán đầy khung (xem [05](05_QUALITY_ASSURANCE.md)). Bản 06/09/2026: 2/24 do VLS | Đặt sau EXP-A | như K01 | 2.4 | Hệ thống |
| K05 | Đồng thuận giữa cổng tự động và chuyên gia | Cohen's kappa giữa "cổng cho chuyển chuyên gia" và "chuyên gia duyệt" | Chưa đo (0 phiếu) | Đo khi ≥ 30 phiếu; κ ≥ 0,40 mới giữ phép đo ở vai trò chặn | Passport `quality` + `reviews` | 5.4 | BA, QC Officer |
| K06 | Độ tin cậy giữa người chấm | Krippendorff's alpha (khoảng) theo tiêu chí | Chưa đo | α ≥ 0,667 trước khi dùng điểm trung bình để kết luận | `outputs/experiments/*/summary.json` | 3.3 | QC Officer |
| K14 | Tỉ lệ được phê duyệt sau thẩm định | Số "đạt" / số phiếu | Chưa đo | Đặt sau khi có dữ liệu | Passport `reviews` | 3.4 | Chuyên gia |

## Thử nghiệm có kiểm soát (yêu cầu BTC 2)

| Mã | KPI | Công thức | Hiện tại | Mục tiêu | Nguồn, cách đo | L3 | Chủ |
|---|---|---|---|---|---|---|---|
| K07 | Dao động theo seed | Hệ số biến thiên (sd / trung bình) của PPS theo seed ở từng mức trọng số | EXP-A (5 seed, 6 hiện vật): hệ số biến thiên của PPS theo seed trong mỗi ô trung bình 2,1% ở trọng số 0,85, 2,4% ở 0,65, 2,8% ở 0,45, 2,9% ở 0,25 (tính từ `outputs/experiments/EXP-A/results.csv`, chưa có script riêng). Bộ demo 3 seed (42, 43, 44; 24 ô × 3 seed): trung bình 0,95 đến 1,6% theo mức sáng tạo, lớn nhất 4,0% (tính từ Passport) | Báo cáo kèm mọi kết luận; không đặt ngưỡng | `outputs/experiments/EXP-A/summary.json` | 1.1 | BA |
| K08 | Tỉ lệ thí nghiệm hợp lệ đơn biến | Kế hoạch qua `validate_plan` / kế hoạch dùng làm bằng chứng | 7/7 (EXP-A đến EXP-G) | 100% | `python -m tsds.evaluation.experiment plan …` | 1.1 | BA |
| K18 | Số lượt chạy hoàn tất theo kế hoạch | Lượt `completed` / lượt trong `plan.csv` | EXP-B 126/126; EXP-C 24/24; EXP-D 60/60; EXP-E 36/36; EXP-F 36/36; EXP-G 126/126; EXP-A 120/120 | 100% trước khi phân tích | `results.csv` | 1.1 | BA |

## Nguồn gốc và bản quyền (yêu cầu BTC 3)

| Mã | KPI | Công thức | Hiện tại | Mục tiêu | Nguồn, cách đo | L3 | Chủ |
|---|---|---|---|---|---|---|---|
| K09 | Độ đầy đủ hồ sơ nguồn | Số trường bắt buộc có giá trị / 10, theo hiện vật | 8/10 ở cả 6 hiện vật đang dùng (thiếu giấy phép từng vật và ngày thu thập) | 10/10 với mọi hiện vật đang dùng | `tsds/provenance/registry.py::completeness` | 4.1, 4.2 | Quản trị dữ liệu |
| K10 | Tỉ lệ hiện vật đang dùng được phép xuất bản | Hiện vật `active` qua cổng `publish_public` / số hiện vật `active` | 0/6 | 100% trước khi xuất bản công khai bất kỳ thiết kế nào | `GET /provenance/catalog` | 2.2 | Quản trị dữ liệu |
| K11 | Toàn vẹn Passport | Passport qua `verify` / tổng | 24/24 bộ demo; 72/72 kể cả bộ nhiều seed | 100%, kiểm mỗi lần chạy bộ kiểm thử | `tests/test_passport.py` | 4.3, 4.4 | Hệ thống |
| K16 | Ảnh xuất có nhãn AI | Ảnh xuất qua API có dải nhãn và siêu dữ liệu / ảnh xuất qua API | 100% (theo thiết kế: endpoint xuất luôn gắn nhãn; có ca kiểm thử) | 100% | `tests/test_api.py` | 4.4 | Hệ thống |
| K19 | Thư xin phép đã gửi | Hiện vật `active` có `permission_request` khác `not_sent` / số hiện vật `active` chưa có quyền | 0/6 | 100% trong 1 tuần | `data/heritage/metadata.json` | 2.2 | Quản trị dữ liệu |

## Vận hành

| Mã | KPI | Công thức | Hiện tại | Mục tiêu | Nguồn, cách đo | L3 | Chủ |
|---|---|---|---|---|---|---|---|
| K12 | Thời gian sinh hoa văn một thiết kế (giai đoạn 1) | Trung vị `generation.duration_s` trong Passport | 10,96 giây (n = 24, thấp nhất 10,11, cao nhất 16,90; RTX 4060 Laptop 8 GB, ngày 20/11/2026; cả 72 thiết kế: 11,75). Bản 06/09/2026: 5,62 giây, tức 1,95 lần, trong mức mục tiêu 2 lần nhưng sát giới hạn | Không tăng quá 2 lần khi thêm cổng chất lượng | Passport; manifest lần chạy | 2.4, 2.5 | Hệ thống |
| K20 | Thời gian sinh một bộ 4 thiết kế | Khoảng cách giữa hai lần chạy liên tiếp của `scripts/demo/generate_demo_set.py` (gồm sinh áo LoRA, 4 hoa văn, ghép, polish, khoá họa tiết, cổng, Passport) | 112 đến 142 giây (n = 5 khoảng, RTX 4060 Laptop 8 GB, ngày 20/11/2026). Lượt có sinh lại hoa văn nhiều lần mất lâu hơn: LR3D_124 (4 lần sinh lại cho 3 thiết kế) mất 199 giây | Đặt sau khi có dữ liệu | Thư mục `outputs/runs/R<thời điểm>-<mã>` | 2.4, 2.5 | Hệ thống |
| K13 | Thời gian chờ thẩm định | Thời điểm phiếu − thời điểm chuyển "chờ chuyên gia" | Chưa đo | Đặt sau khi có dữ liệu | Thời điểm trong sổ cái Passport | 3.3 | QC Officer |
| K17 | Số lần sinh lại trước khi qua G2 | Trung bình số lần sinh lại / thiết kế | 0,375 lần sinh lại mỗi thiết kế ở bộ seed 42 (21 thiết kế đạt ngay, 3 thiết kế dùng đủ 3 lần sinh lại, đều của LR3D_124); 0,347 ở cả 72 thiết kế (61 đạt ngay) | ≤ 1; vượt 3 lần thì chuyển người (đã thực thi) | Sổ cái Passport | 2.4 | Hệ thống |
| K15 | Phản hồi người dùng | Tỉ lệ phiên người dùng chọn được phương án đề cử | Chưa đo (chưa có phiếu phản hồi) | Đặt sau khi có dữ liệu | Nhật ký audit + phiếu phản hồi (kế hoạch) | 1.2, 5.3 | BA |

## Cơ chế đo

- **Tự động**: các KPI K01–K04, K09–K12, K16–K18, K20 đọc thẳng từ tệp CSV/JSON do hệ thống ghi. Không có bước nhập tay.
- **Theo sự kiện**: K13, K17 tính từ thời điểm trong sổ cái Passport (mỗi sự kiện có thời điểm và đã được băm nối chuỗi nên không sửa lùi được mà không bị phát hiện).
- **Theo phiếu**: K05, K06, K14 cần phiếu chuyên gia. Bộ phân tích `tsds/evaluation/experiment.py analyze` tính alpha; kappa tính khi hiệu chỉnh ngưỡng ([05](05_QUALITY_ASSURANCE.md)).
- Giao diện web cho người xem không còn trang "Tổng quan" (đã gỡ ngày 19/11/2026). Số liệu KPI vẫn được xuất vào `web_ui/data/dashboard.json` bằng `scripts/demo/export_demo_data.py`; ô chưa đo ghi "Mục tiêu cần đo", không ghi số.
