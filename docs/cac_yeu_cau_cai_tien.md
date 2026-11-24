# Các yêu cầu cải tiến của ban tổ chức

Tài liệu này gom ba yêu cầu cải tiến của ban tổ chức (BTC) và link thử nghiệm: đã làm gì, làm ở đâu, còn thiếu gì. README tổng của dự án không ghi phần này.

Số liệu cập nhật ngày 22/11/2026, đọc từ Passport và tệp kết quả trong repo. Phần còn thiếu ghi thẳng, không làm tròn thành "đã xong".

## 1. Tóm tắt

| # | BTC yêu cầu | Đã làm | Còn thiếu | Xem ở |
|---|---|---|---|---|
| 1 | Đánh giá **thiết kế cuối**, không chỉ hoa văn trung gian | Cổng chất lượng **G2** (hoa văn: rò dáng bình, đường nối) và **G3** (thiết kế cuối: giữ họa tiết PPS, IoU dáng áo, độ nét, chi tiết mịn, lệch màu ΔE). Hoàn thiện ảnh (polish) chỉ trong vùng áo, khoá họa tiết `pattern_lock_v1`. Vòng loại và thử lại: đổi seed, hạ độ nhiễu, cuối cùng trả bản ghép thô | Người am hiểu di sản và thiết kế xem mẫu, phiếu nhận xét | [05](finals/05_QUALITY_ASSURANCE.md), `config/quality_gate.json`, `tsds/quality/` |
| 2 | **Đối chứng có kiểm soát**, nhiều seed, chấm mù | Module thí nghiệm từ chối kế hoạch đổi hơn một yếu tố. Sáu thí nghiệm: EXP-A (trọng số ControlNet, 120 lượt, 5 seed), EXP-B (bước hoàn thiện, 126), EXP-D (nguồn áo nền, 60), EXP-E (nguồn ảnh nạp, 36), EXP-F (36), EXP-G (cách tạo ô hoa văn, 90). Thống kê Wilcoxon, Friedman, hệ số biến thiên theo seed. Gói chấm mù đã dựng sẵn | Có 28 phiếu chấm mù của người quan tâm nhưng độ đồng thuận thấp (alpha 0,03, mục tiêu từ 0,667); cần chấm lại với người có chuyên môn | [06](finals/06_EXPERIMENTS.md), `tsds/evaluation/`, `outputs/experiments/` |
| 3 | **Bản quyền, nguồn gốc, truy vết** | Danh mục nguồn có DOI và giấy phép CC BY 4.0 cho 6 hiện vật. Cổng quyền theo 4 mục đích. Design Passport có chuỗi mã băm, phiên bản có mã băm cha, bước sửa tay phải chạy lại G3. Nhãn "Hỗ trợ bởi AI" trên giao diện web và trên ảnh tải về; nhãn "Thiết kế hỗ trợ bởi AI" trên ảnh xuất qua API. Khai báo công cụ AI | Xác minh riêng nguồn từng vật; Passport chưa hiện trên giao diện web | [07](finals/07_PROVENANCE_COPYRIGHT.md), [ai_disclosure.md](ai_disclosure.md), `tsds/provenance/` |

## 2. Kết quả bộ demo hiện tại

Bộ 24 thiết kế (6 hiện vật × 4 mức sáng tạo, seed 42, sinh lại ngày 21/11/2026), đọc từ Passport:

- **G2 (hoa văn):** đạt 16, cảnh báo 6, loại 2. Cả 2 thiết kế bị loại đều do đường nối và đều của hiện vật LR3D_124.
- **G3 (thiết kế cuối):** đạt 20, cảnh báo 4, loại 0.
- **Giữ họa tiết (PPS):** trung bình 0,952. **Giữ chi tiết mịn:** trung vị 0,889.
- **Trạng thái duyệt:** 13 chờ chuyên gia thẩm định, 9 có cảnh báo, 2 không đạt. Chưa thiết kế nào được ghi là đã thẩm định.

Toàn vẹn chuỗi mã băm: 24/24 Passport. Cách tự kiểm tra có trong [evidence/README.md](evidence/README.md).

## 3. Còn thiếu để đủ bộ minh chứng

1. **Chấm mù:** đã thu 28 phiếu của người quan tâm (không phải chuyên gia) cho EXP-A, nhập bằng `scripts/eval/import_google_form.py`. Krippendorff alpha chỉ 0,03 (mục tiêu từ 0,667), nên chưa kết luận được "đẹp hơn" hay "giống vải in hơn" cho từng thiết kế. Chỉ thấy xu hướng chung: điểm trung bình giảm khi hạ trọng số ControlNet (3,72 xuống 3,38). Chi tiết ở [evidence/README.md](evidence/README.md).
2. **Thẩm định mẫu:** mời ít nhất một người am hiểu di sản và một người am hiểu thiết kế điền phiếu. Nếu hết hạn chưa có thì ghi đúng sự thật, không ghi "đã thẩm định".
3. **Nguồn từng vật:** 6 hiện vật thuộc bộ LR3D-CULT2 (CC BY 4.0), nhưng một phần mô hình trong bộ có thể lấy từ Sketchfab theo giấy phép học thuật. Chưa xác minh vật nào thuộc nguồn nào.
4. **Giao diện web:** chỉ còn 3 trang, chưa hiện Passport và chỉ số chất lượng. Nhãn "Hỗ trợ bởi AI" đã có trên ảnh.
5. **Link thử nghiệm:** xem mục 4.

## 4. Link thử nghiệm cho BTC

- Hướng dẫn một trang: [HUONG_DAN_THU_NGHIEM.md](HUONG_DAN_THU_NGHIEM.md).
- Cách triển khai và kiểm thử: [DEPLOY_LIVE.md](DEPLOY_LIVE.md). Bản Preview kiểm ngày 21/11/2026 (Vercel và Modal); production chưa chuyển; gói mã mới `tsds/` chưa deploy thử.
- Preview đang bật Vercel Authentication nên người ngoài chưa mở được. Cần chủ tài khoản tắt hoặc cấp quyền trước khi gửi link.

## 5. Chỉ mục tài liệu

| Tài liệu | Nội dung |
|---|---|
| [evidence/README.md](evidence/README.md) | Minh chứng theo từng yêu cầu: ở đâu, đã có hay chưa, cách tự kiểm tra |
| [ai_disclosure.md](ai_disclosure.md) | Công cụ AI đã dùng, nhãn AI, lý do tắt bộ lọc an toàn |
| [HUONG_DAN_THU_NGHIEM.md](HUONG_DAN_THU_NGHIEM.md) | Hướng dẫn BTC thử hệ thống |
| [finals/README.md](finals/README.md) | Hồ sơ vòng chung kết: đối chiếu yêu cầu BTC với tính năng và bằng chứng |
