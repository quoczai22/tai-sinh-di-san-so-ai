# 05. So sánh AS-IS / TO-BE, APQC và lộ trình cải tiến

## 1. So sánh theo mô hình

Số phần tử đếm tự động từ mô hình (`diagrams/stats.json`). "Điểm chạm của người trên luồng chính" đếm tay theo đường đi
thành công phổ biến nhất của mỗi quy trình. Thời gian chỉ ghi khi có số đo trong repo; còn lại ghi rõ **mục tiêu đề xuất**.

| Quy trình | Chỉ số | AS-IS | TO-BE | Ghi chú |
|---|---|---|---|---|
| BP-01 Tạo thiết kế | Tác vụ (người / tự động) | 14 (3 / 11) | Giữ nguyên | Đã tự động hoá phần lõi |
| | Thời gian một bộ 4 thiết kế | 112–142 giây (đo, n = 5, RTX 4060 Laptop) | Giữ nguyên | `08_KPI.md` K20 |
| | Nhánh ngoại lệ có xử lý | 4 (429, quyền, lỗi phương án, mọi phương án lỗi) + dự phòng GPU | Giữ nguyên | |
| BP-02 Xem, tải, sửa | Tác vụ (người / tự động) | 10 (5 / 5) | 12 (6 / 6) | Thêm đề cử (tuỳ chọn) và xuất có Passport |
| | Điểm chạm của người: tải ảnh | 2 | 2 | Tệp TO-BE có mã Passport, SHA-256 |
| | Điểm chạm của người: sửa và lưu | 4 | 4 | |
| BP-03 QC, thẩm định, xuất bản | Tác vụ (người / tự động) | 11 (6 / 5) | 12 (4 / 8) | Tác vụ người còn lại đều là ngoại lệ (cảnh báo, mâu thuẫn, thay chuyên gia) hoặc chấm điểm |
| | Điểm chạm của người, luồng Đạt → xuất bản | **5** (QC 4, chuyên gia 1) | **1** (chuyên gia) | QC không còn lập gói, nhập lại, gọi xuất bản |
| | Chuyển giao giữa các vai trò người | 2 (QC → chuyên gia → QC) + 1 lần nhập lại dữ liệu | 0 trên luồng chính | QC chỉ vào khi có cảnh báo hoặc mâu thuẫn |
| | Khởi động | Thủ công, theo đợt | Theo sự kiện trạng thái | |
| | Hạn xử lý phiếu | Không có | 7 ngày, có nhắc (mục tiêu đề xuất) | Đo bằng K13 |
| | Xử lý phiếu mâu thuẫn quy tắc | Chỉ đánh dấu | QC xem lại, chốt | |
| BP-04 Tiếp nhận hiện vật | Điểm chạm của người, quyền đã mở | 3 | 2 | Bỏ bước chạy script xuất dữ liệu |
| | Điểm chạm của người, quyền chưa rõ | 5 | 4 | Bỏ sửa tay JSON; nhắc lại tự động |
| | Theo dõi phản hồi cấp phép | Không | 14 ngày, nhắc tối đa 2 lần (mục tiêu đề xuất) | |

Điểm nghẽn và rủi ro:

| Quy trình | Điểm nghẽn AS-IS (có số liệu) | Rủi ro nghiệp vụ AS-IS | TO-BE xử lý |
|---|---|---|---|
| BP-01 | GPU: một lượt chạy khoảng 2 phút trên máy đo; hàng chờ tối đa 3 | Thấp: có dự phòng, có cảnh báo | Không đổi |
| BP-02 | Không | Ảnh tải về không mang mã Passport, mất truy vết khi đăng lại | Xuất qua `/export` |
| BP-03 | 13/24 thiết kế "chờ chuyên gia", 9/24 "chờ QC", 0 phiếu ghi vào Passport (24/11/2026) | Thiết kế không bao giờ có kết luận; nhập tay sai điểm; mâu thuẫn quy tắc không ai xử lý | Hàng đợi tự động, cổng thẩm định, hạn 7 ngày, xử lý mâu thuẫn |
| BP-04 | Cả 6 hiện vật đang ở `open_license` (CC BY 4.0), `permission_request = not_sent`: nhánh xin phép chưa từng chạy | Khi có hiện vật quyền chưa rõ, không có hạn và nhắc; sửa JSON tay có thể làm hỏng cổng quyền | Biểu mẫu quyền, hạn và nhắc |

Khả năng mở rộng: AS-IS phụ thuộc một khoá API chung và thao tác dòng lệnh của QC, nên số chuyên gia và số thiết kế tăng
thì khối việc của QC tăng tuyến tính. TO-BE tách vai trò (UC19), để hệ thống xếp hàng và gửi phiếu, nên thêm chuyên gia
không thêm việc cho QC.

## 2. Phân tích Lean (giá trị gia tăng)

| Hoạt động AS-IS | Loại | Lý do | Xử lý ở TO-BE |
|---|---|---|---|
| Sinh hoa văn, ghép, hoàn thiện, cổng G2/G3 | Tạo giá trị | Tạo ra sản phẩm và bảo đảm chất lượng | Giữ |
| Chuyên gia chấm mù | Tạo giá trị (bắt buộc) | AI không thay chuyên gia | Giữ, làm trên cổng thẩm định |
| QC lập gói chấm mù bằng script | Không tạo giá trị, cần thiết | Chỉ là chuyển định dạng | Tự động hoá |
| QC nhập lại điểm từ Google Form | Lãng phí (xử lý thừa, rủi ro lỗi) | Dữ liệu đã có, gõ lại | Bỏ |
| Thiết kế chờ thẩm định không hạn | Lãng phí (chờ đợi) | Không ai bị nhắc | Hạn 7 ngày, nhắc |
| QC gọi API xuất bản | Không tạo giá trị | Điều kiện đã kiểm tra bằng cổng | Tự động khi đủ điều kiện |
| Sửa tay `metadata.json` để ghi trạng thái quyền | Lãng phí, rủi ro | Dễ sai cú pháp, không kiểm tra `scope` | Biểu mẫu quyền |
| Chạy script xuất dữ liệu web | Không tạo giá trị | Lặp lại, dễ quên | CI tự chạy |

## 3. Ánh xạ APQC PCF

Dùng cùng các nhóm PCF đã chọn trong `docs/finals/02_APQC.md` (2.0, 13.0, 11.0, 12.0) để hai tài liệu không lệch nhau.
Mã cấp 3 trở xuống là mã nội bộ của dự án, không phải mã PCF.

| Cấp 1 (Category) | Cấp 2 (Process Group) | Cấp 3 (Process) | Cấp 4 (Activity) | Cấp 5 (Task, ví dụ) |
|---|---|---|---|---|
| 2.0 Develop and Manage Products and Services | 2.3 Develop products and services | BP-01 Tạo thiết kế áo dài | Chuẩn bị hoa văn; Sinh áo dài nền; Tạo 4 phương án; Lập Passport | Sinh hoa văn; Ghép lên áo; Hoàn thiện vùng áo |
| 2.0 | 2.3 | BP-02 Xem, tải và chỉnh sửa thiết kế | Tải thiết kế; Tải lên bản sửa; Đề cử thẩm định | Kiểm tra tệp PNG; Ghi phiên bản |
| 13.0 Develop and Manage Business Capabilities | 13.3 Manage enterprise quality | BP-01a Cổng chất lượng tự động | Cổng G2; Cổng G3; Sinh lại có giới hạn | Đo rò dáng bình; Đổi seed |
| 13.0 | 13.3 | BP-03 Kiểm soát chất lượng và thẩm định | Xử lý cảnh báo; Điều phối thẩm định mù; Chấm mù; Tổng hợp phiếu | Tạo phiếu theo vai trò; Nhắc quá hạn |
| 13.0 | 13.5 Knowledge management capability | BP-04 Tiếp nhận hiện vật | Tiếp nhận ảnh; Viết mô tả, ý nghĩa hoa văn; Xuất dữ liệu web | Chạy C1–C4; Ghi `artifact_info` |
| 11.0 Manage Enterprise Risk, Compliance, Remediation, and Resiliency | (nhóm tuân thủ, mã cấp 2 cần đối chiếu bản PCF nhóm dùng) | Kiểm soát quyền sử dụng (UC07, xuyên suốt) | Cổng quyền theo mục đích; Xuất bản có điều kiện | Kiểm tra `publish_public` |
| 12.0 Manage External Relationships | (mã cấp 2 cần đối chiếu) | Quan hệ chủ sở hữu ảnh, hội đồng chuyên gia | Đề nghị cấp phép; Mời chuyên gia | Gửi lời nhắc |
| 8.0 Manage Information Technology | (vận hành dịch vụ IT) | Giám sát vận hành (UC18) | Cảnh báo sự cố; Tra cứu tình trạng | Gửi cảnh báo Zalo |

Quy trình cốt lõi tạo giá trị: BP-01, BP-01a, BP-03 (chất lượng và chuyên gia là cam kết của sản phẩm). Quy trình hỗ
trợ: BP-02, BP-04, giám sát vận hành.

## 4. Danh sách đề xuất cải tiến

| Mã | Đề xuất | Vấn đề | Ưu tiên | Quy mô (ước tính) | Phần cần làm (không sửa trong đợt này) |
|---|---|---|---|---|---|
| P1 | Hàng đợi thẩm định tự động khi trạng thái đổi hoặc có đề cử | G01, B09 | Cao | Vừa | Hook sau `P.set_approval`; bảng hàng đợi trong kho Passport |
| P2 | Cổng thẩm định web: phiếu mù theo vai trò, link có mã riêng, ghi thẳng `POST /reviews` | G02, U05 | Cao | Lớn | Trang mới trong `web_ui`, route ở cổng Vercel, token mỗi người chấm |
| P3 | Hạn 7 ngày và nhắc chuyên gia | G03 | Cao | Nhỏ | Tác vụ định kỳ đọc thời điểm gửi link |
| P4 | Phiếu mâu thuẫn quy tắc chuyển QC chốt | G04 | Cao | Nhỏ | Trường `rule_conflict` đã có; thêm trạng thái chờ QC |
| P5 | Tải xuống qua `/export` (mã Passport trong tệp) | G05 | Trung bình | Nhỏ | Mở route `passports/{id}/export` ở `live.js`; `download.js` gọi route này |
| P6 | Đề cử thiết kế đi thẩm định | G01 | Trung bình | Nhỏ | Nút trong cửa sổ phóng to; route ghi cờ đề cử |
| P7 | Hiện trạng thái duyệt ở trang Thiết kế đã tạo | B06 | Trung bình | Nhỏ | `views/mine.js` đọc `approval.status` |
| P8 | Biểu mẫu quyền, theo dõi đề nghị cấp phép 14 ngày | G06 | Trung bình | Vừa | Công cụ cho người quản lý dữ liệu; ghi `permission_request` |
| P9 | Khoá hoặc tài khoản theo vai trò thay khoá chung | G07, U01 | Trung bình | Lớn | Thay `DH_API_KEY` chung; gắn người thực hiện vào sự kiện Passport |
| P10 | Xuất bản tự động khi Đạt và quyền cho phép | B10 | Thấp | Nhỏ | Gọi logic `publish` sau khi kết luận Đạt |
| P11 | CI tự xuất dữ liệu web khi danh mục đổi | — | Thấp | Nhỏ | Bước trong GitHub Actions |

## 5. Hướng dẫn triển khai

Thứ tự đề xuất, mỗi giai đoạn kiểm chứng được trước khi sang giai đoạn sau:

1. **Giai đoạn 1 — Khép vòng thẩm định (P1, P3, P4, P7).** Thay đổi nhỏ, không đụng giao diện chuyên gia. Đo được ngay
   K13 (thời gian chờ thẩm định). Tiêu chí xong: không còn thiết kế "chờ chuyên gia" quá 7 ngày mà chưa được nhắc.
2. **Giai đoạn 2 — Cổng thẩm định (P2, P6).** Chuyên gia chấm trực tiếp, bỏ nhập lại. Giữ Google Form cho thí nghiệm
   (UC17) vì cần nhiều người chấm ẩn danh. Tiêu chí xong: phiếu trong Passport khớp 100 % phiếu đã gửi.
3. **Giai đoạn 3 — Truy vết khi tải (P5) và quyền (P8, P11).**
4. **Giai đoạn 4 — Vai trò (P9) rồi xuất bản tự động (P10).** Xuất bản tự động chỉ bật sau khi có xác thực theo vai trò,
   để mọi quyết định dẫn tới xuất bản đều gắn với người thật.

Mỗi thay đổi cần cập nhật song song: mô hình `tools/models.py` (sinh lại sơ đồ), bảng truy vết ở
[04_TRUY_VET_VA_QUY_TAC.md](04_TRUY_VET_VA_QUY_TAC.md), và kiểm thử trong `tests/`.
