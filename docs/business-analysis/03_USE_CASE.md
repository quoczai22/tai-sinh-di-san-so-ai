# 03. Use Case UML 2.5: AS-IS, TO-BE và đặc tả

Sơ đồ: `diagrams/UC-AS-IS_use-case.(svg|png|puml)`, `diagrams/UC-TO-BE_use-case.(svg|png|puml)`. Tệp `.puml` mở và sửa
được bằng PlantUML; ảnh sinh từ cùng mô hình `tools/ucgen.py`.

## 1. Ranh giới và tác nhân

Subject (ranh giới): **Nền tảng Tái Sinh Di Sản Số** gồm ứng dụng web, cổng Vercel, API và pipeline AI. Pipeline AI và
máy GPU nằm **trong** ranh giới (là phần mềm của nhóm chạy trên hạ tầng thuê), nên không phải tác nhân.

| Tác nhân | Phân loại | Mục tiêu với hệ thống | AS-IS | TO-BE |
|---|---|---|---|---|
| Nhà thiết kế (người dùng web) | Primary | Tìm hiểu hiện vật, tạo, tải, sửa thiết kế | Có | Có |
| QC Officer | Primary | Xử lý cảnh báo kỹ thuật, điều phối thẩm định, xuất bản, thử nghiệm | Có | Có |
| Chuyên gia thẩm định | Primary | Chấm mù, ra quyết định văn hoá và thẩm mỹ | Có | Có |
| Người quản lý dữ liệu | Primary | Đưa hiện vật vào thư viện, quản lý quyền | Có | Có |
| Người vận hành | Primary | Biết sự cố GPU, xem tình trạng hệ thống | Có | Có |
| Google Forms | External System (Supporting) | Thu phiếu chấm | Có | Bỏ (thay bằng cổng thẩm định) |
| Zalo | External System (Supporting) | Kênh cảnh báo và lệnh tra cứu | Có | Có |
| Chủ sở hữu ảnh | Secondary | Nhận đề nghị cấp phép, nhắc lại | — (email ngoài hệ thống) | Có |
| Nhân sự nội bộ | Tác nhân trừu tượng (cha) | Đăng nhập theo vai trò | — | Có |

Tổng quát hoá chỉ dùng ở TO-BE: QC Officer, Chuyên gia, Người vận hành, Người quản lý dữ liệu **kế thừa** "Nhân sự nội
bộ" vì cùng có hành vi "Đăng nhập theo vai trò". AS-IS không có tổng quát hoá: không vai trò nào có hành vi khác nhau do
phân quyền (hệ thống không có tài khoản).

## 2. Danh sách ca sử dụng

| Mã | Ca sử dụng | Tác nhân chính | Hỗ trợ | AS-IS | TO-BE | Căn cứ (AS-IS) |
|---|---|---|---|---|---|---|
| UC01 | Tra cứu hiện vật | Nhà thiết kế | — | Có | Giữ | `GET /heritage`, Trang chủ, Studio |
| UC02 | Xem ý nghĩa hoa văn | (extend UC01) | — | Có | Giữ | `artifact-book.js` |
| UC03 | Tạo thiết kế áo dài | Nhà thiết kế | — | Có | Giữ | `POST /generate` |
| UC04 | Xem lại thiết kế đã tạo | Nhà thiết kế | — | Có | Giữ | `views/mine.js` |
| UC05 | Tải thiết kế có nhãn AI | Nhà thiết kế | — | Có | Đổi: kèm mã Passport | `core/download.js` |
| UC06 | Tải lên bản chỉnh sửa | Nhà thiết kế | QC Officer | Có | Giữ | `POST /passports/{id}/edits` |
| UC07 | Kiểm tra quyền sử dụng | (include) | — | Có | Giữ | `registry.py::rights_gate` |
| UC08 | Kiểm định chất lượng tự động (G2, G3) | (include) | — | Có | Giữ | `quality/gate.py`, `assess.py` |
| UC09 | Ghi Design Passport | (include) | — | Có | Giữ | `provenance/builder.py`, `passport.py` |
| UC10 | Xử lý cảnh báo chất lượng | QC Officer | — | Qua API | Bảng QC | `POST /passports/{id}/qc` |
| UC11 | Điều phối thẩm định mù | QC Officer | Google Forms | Có (script) | Đổi: Theo dõi hàng đợi thẩm định | `scripts/eval/` |
| UC12 | Chấm mù thiết kế | Chuyên gia | Google Forms | Ngoài hệ thống | Đổi: chấm trên cổng thẩm định | `build_google_form.py`, `POST /reviews` |
| UC13 | Xuất bản thiết kế | QC Officer | — | Qua API | Tự động khi đủ điều kiện | `POST /passports/{id}/publish` |
| UC14 | Tra cứu Design Passport | QC Officer | — | Qua API | Giữ | `GET /passports/{id}` |
| UC15 | Tiếp nhận hiện vật mới | Người quản lý dữ liệu | — | Có (script) | Giữ | `ingest_heritage_image.py` |
| UC16 | Cập nhật quyền sử dụng hiện vật | Người quản lý dữ liệu | — | Sửa tay JSON | Đổi: Quản lý đề nghị cấp phép | `metadata.json` |
| UC17 | Chạy thử nghiệm có kiểm soát | QC Officer | — | Có (CLI) | Giữ | `tsds/evaluation/experiment.py` |
| UC18 | Giám sát vận hành | Người vận hành | Zalo | Có | Giữ | `_shared.js`, `bot_ops_commands.js` |
| UC19 | Đăng nhập theo vai trò | Nhân sự nội bộ | — | — | **Mới** | Đề xuất |
| UC20 | Đề cử thiết kế đi thẩm định | Nhà thiết kế | — | — | **Mới** | Đề xuất |
| UC21 | Theo dõi trạng thái thiết kế | (extend UC04) | — | — | **Mới** | Đề xuất |

Đối chiếu với báo cáo cũ (Bảng 3.2):

| Ca cũ | Xử lý | Lý do |
|---|---|---|
| UC01 Đăng ký và đăng nhập, UC17 Quản lý người dùng | Bỏ khỏi AS-IS; TO-BE thành UC19 | Không có tài khoản trong mã (U01) |
| UC02 Xem danh mục hiện vật | → UC01 | Đổi tên theo mục tiêu |
| UC03 Tải lên hiện vật | → UC15, tác nhân Người quản lý dữ liệu | U07 |
| UC04 Kiểm tra nguồn gốc, UC18 Kiểm tra quyền | → UC07 (một ca include) | C1–C4 nằm trong UC15; cổng quyền dùng chung là UC07 |
| UC05 Quản lý giấy phép | → UC16 | Tên đúng việc đang làm |
| UC06 Phân tích họa tiết, UC07 Sinh họa tiết AI | Gộp vào UC03 | Bước nội bộ, không phải mục tiêu tác nhân (U03) |
| UC08 Tạo thiết kế | → UC03 | — |
| UC09 Chỉnh sửa thiết kế | → UC06 Tải lên bản chỉnh sửa | Sửa ảnh làm ngoài hệ thống; hệ thống nhận bản sửa |
| UC10 Đánh giá chất lượng | Tách: UC08 (tự động, include) và UC10 (QC xử lý cảnh báo) | Hai mục tiêu khác nhau |
| UC11 So sánh phiên bản, UC15 Xem lịch sử | Gộp vào UC14 | Không có giao diện so sánh (U08) |
| UC12 Thẩm định chuyên gia | Tách: UC11 (QC điều phối) và UC12 (chuyên gia chấm) | Hai tác nhân, hai mục tiêu (U05) |
| UC13 Phê duyệt thiết kế | Bỏ | Phê duyệt là kết quả của UC12 (U04) |
| UC14 Quản lý Design Passport | → UC09 (include) | Hệ thống tạo, người dùng không quản lý (U09) |
| UC16 Xuất thiết kế | → UC05 | — |
| UC19 Thử nghiệm có kiểm soát | → UC17 | — |

## 3. Quan hệ include, extend

| Quan hệ | Loại | Vì sao |
|---|---|---|
| UC03 → UC07, UC08, UC09 | «include» | Mỗi lần tạo thiết kế luôn kiểm tra quyền mục đích thử nghiệm, luôn chạy G2/G3, luôn lập Passport (`run.py`) |
| UC06 → UC08, UC09 | «include» | Mỗi bản sửa luôn ghi phiên bản và chạy lại G3 (`submit_edit`) |
| UC13 → UC07 | «include» | Xuất bản luôn chạy cổng quyền `publish_public` |
| UC15 → UC07 | «include» | Tiếp nhận luôn xác định tình trạng quyền (C3) |
| UC02 → UC01 | «extend» | Extension point "Xem chi tiết hiện vật"; điều kiện: người xem bấm "Xem ý nghĩa hoa văn" |
| UC21 → UC04 (TO-BE) | «extend» | Extension point "Mở bộ thiết kế"; điều kiện: thiết kế đã đề cử hoặc đã có kết luận |

Không vẽ: UC06 «extend» UC03 như báo cáo cũ, vì sửa ảnh là mục tiêu riêng, bắt đầu từ trang Kết quả hoặc Thiết kế đã
tạo, không chen vào giữa luồng tạo thiết kế. UC17 không include UC03: thí nghiệm dùng bộ chạy riêng, ảnh thí nghiệm
không vào kho sản phẩm.

## 4. Đặc tả ca sử dụng chính

### UC03 — Tạo thiết kế áo dài

| Mục | Nội dung |
|---|---|
| 1. ID | UC03 |
| 2. Tên | Tạo thiết kế áo dài |
| 3. Mô tả | Từ một hiện vật trong thư viện, hệ thống sinh bốn phương án áo dài, kiểm định từng phương án và lập Design Passport |
| 4. Tác nhân chính | Nhà thiết kế (người dùng web) |
| 5. Tác nhân hỗ trợ | Người vận hành (nhận cảnh báo qua Zalo khi lỗi) |
| 6. Kích hoạt | Bấm "Tạo thiết kế" ở trang chi tiết hiện vật trong Studio |
| 7. Tiền điều kiện | Hiện vật `active`; quyền không ở `permission_denied` |
| 8. Hậu điều kiện | Thư mục lần chạy có manifest; tối đa 4 Passport, trạng thái do cổng đặt (không bao giờ là "đã phê duyệt"); bộ thiết kế lưu vào danh sách "Thiết kế đã tạo" của trình duyệt |
| 9. Luồng chính | 1. Người dùng bấm Tạo. 2. Hệ thống kiểm tra máy GPU sẵn sàng, chuyển yêu cầu. 3. API kiểm tra hạn mức, xếp hàng chờ. 4. Kiểm tra quyền mục đích thử nghiệm (UC07). 5. Chuẩn bị hoa văn, sinh áo dài nền (LoRA, SAM). 6. Lặp 4 lần: sinh hoa văn, G2, ghép, hoàn thiện, G3 (UC08). 7. Lập Passport, gán trạng thái duyệt (UC09). 8. Trang Kết quả hiện 4 thiết kế |
| 10. Luồng thay thế | A1. Máy GPU không sẵn sàng: trả bộ sinh sẵn, ghi nhãn "Kết quả đã sinh sẵn — không phải sinh trực tiếp". A2. G2 lỗi: sinh lại tối đa 3 lần, rồi giữ bản ít lỗi nhất, gắn `qa_failed`. A3. G3 lỗi: thử lại hoàn thiện, hết lượt dùng bản ghép thô |
| 11. Luồng ngoại lệ | E1. Vượt hạn mức hoặc hàng chờ đầy: 429, báo thử lại, cảnh báo vận hành. E2. Quyền bị từ chối: job thất bại, báo lý do. E3. Một phương án lỗi GPU: phương án đó `failed`, các phương án khác tiếp tục. E4. Không phương án nào thành công: job thất bại, cảnh báo vận hành |
| 12. Quy tắc | BR-01, BR-02, BR-03, BR-05, BR-06, BR-07, BR-08 |
| 13. Dữ liệu vào | `heritage_id`; (seed tuỳ chọn, web không gửi) |
| 14. Dữ liệu ra | `job_id`, tiến độ; 4 ảnh thiết kế; 4 Design Passport; manifest lần chạy |
| 15. Ca liên quan | UC01 (trước), UC04, UC05, UC06 (sau), UC07, UC08, UC09 (include) |
| 16. Ưu tiên | Rất cao (luồng giá trị chính) |

### UC06 — Tải lên bản chỉnh sửa

| Mục | Nội dung |
|---|---|
| 1–2 | UC06 — Tải lên bản chỉnh sửa |
| 3. Mô tả | Người dùng tải ảnh đã sửa bằng công cụ đồ họa, khai báo nội dung sửa; hệ thống lưu thành phiên bản mới có truy vết và chạy lại G3 |
| 4. Tác nhân chính | Nhà thiết kế |
| 5. Tác nhân hỗ trợ | QC Officer (cũng được phép tải bản sửa, vai trò `qc_officer`) |
| 6. Kích hoạt | Bấm "Tải lên chỉnh sửa" trong cửa sổ phóng to một thiết kế |
| 7. Tiền điều kiện | Thiết kế tạo trực tiếp trên máy chủ, còn Passport |
| 8. Hậu điều kiện | Passport có phiên bản mới loại "chỉnh sửa thủ công" mang băm phiên bản trước; trạng thái duyệt đặt lại theo G3; thiết kế mang nhãn "Đã chỉnh sửa" |
| 9. Luồng chính | 1. Mở trang Chỉnh sửa. 2. Chọn PNG, nhập ID (bắt đầu TSDS), vai trò, nội dung sửa, công cụ. 3. Biểu mẫu kiểm tra từng trường, bật nút Lưu. 4. Xác nhận lưu. 5. Cổng web kiểm tra chữ ký PNG, kích thước, hạn mức. 6. API lưu ảnh, băm, tạo phiên bản (UC09), chạy G3 (UC08). 7. Thông báo "Đã cập nhật bản chỉnh sửa" |
| 10. Luồng thay thế | A1. Huỷ: cảnh báo bản sửa sẽ không lưu; đồng ý thì quay về trang Kết quả |
| 11. Luồng ngoại lệ | E1. Không phải PNG, quá 3 MB hoặc cạnh dài quá 4096 px: từ chối. E2. Quá 5 lần/giờ/IP: báo thử lại. E3. Thiết kế sinh sẵn: nút bị khoá kèm lý do. E4. Không đủ dữ liệu chạy G3: trạng thái `qa_warning`, QC xem thủ công |
| 12. Quy tắc | BR-09, BR-10, BR-11, BR-12 |
| 13. Dữ liệu vào | Ảnh PNG; `editor_id`, `editor_role`, `description`, `tool` |
| 14. Dữ liệu ra | Mã bản sửa, kết quả G3, trạng thái duyệt mới |
| 15. Ca liên quan | UC04, UC08, UC09; sau đó BP-03 (UC10 hoặc UC12) |
| 16. Ưu tiên | Cao |

### UC12 — Chấm mù thiết kế (AS-IS và TO-BE)

| Mục | AS-IS | TO-BE (đề xuất) |
|---|---|---|
| 1–2 | UC12 — Chấm mù thiết kế | UC12 — Chấm mù trên cổng thẩm định |
| 3. Mô tả | Chuyên gia chấm 5 tiêu chí thang 1–5 và chọn Đạt / Cần sửa / Loại trên Google Form hoặc phiếu; QC nhập lại | Như AS-IS, chấm trên trang web của hệ thống; phiếu ghi thẳng vào Passport |
| 4. Tác nhân chính | Chuyên gia thẩm định | Chuyên gia thẩm định |
| 5. Hỗ trợ | Google Forms; QC Officer (nhập kết quả) | Không |
| 6. Kích hoạt | Nhận link phiếu từ QC | Nhận link phiếu do hệ thống gửi |
| 7. Tiền điều kiện | Thiết kế `pending_expert_review` hoặc `revision_requested` (API chặn trạng thái khác) | Như AS-IS; link còn hiệu lực |
| 8. Hậu điều kiện | Passport có phiếu; trạng thái `approved`, `revision_requested` hoặc `rejected` | Như AS-IS; thời điểm phiếu được ghi để đo K13 |
| 9. Luồng chính | 1. Mở phiếu. 2. Xem ảnh hiện vật và thiết kế, không thấy mã phương án, tham số hay điểm của máy. 3. Chấm, chọn quyết định, nhận xét. 4. Gửi. 5. QC nhập vào Passport (`POST /reviews`) | Bước 1–4 như AS-IS; 5. Hệ thống ghi phiếu, tổng hợp theo quy tắc ER-1.0 |
| 10. Thay thế | A1. Đạt nhưng có tiêu chí < 3 hoặc "Phù hợp văn hoá" < 4: ghi theo quyết định, đánh dấu mâu thuẫn. A2. Không đồng ý lưu tên: chỉ lưu mã | A1 chuyển QC xem lại và chốt kết luận; A2 như AS-IS |
| 11. Ngoại lệ | E1. Tiêu chí không có trong bộ tiêu chí: từ chối (422). E2. Trạng thái không cho thẩm định: 409 | E1, E2 như AS-IS; E3. Quá 7 ngày chưa đủ phiếu: nhắc chuyên gia, báo QC |
| 12. Quy tắc | BR-13, BR-14, BR-15, BR-16 | Thêm BR-21, BR-22 |
| 13. Vào | Điểm 5 tiêu chí, quyết định, nhận xét, mã người chấm, vai trò, đồng ý lưu tên | Như AS-IS |
| 14. Ra | Phiếu trong Passport, cờ `rule_conflict` | Như AS-IS, thêm kết luận tổng hợp |
| 15. Liên quan | UC11, UC13, UC14 | UC11, UC13 |
| 16. Ưu tiên | Rất cao (yêu cầu chuyên gia là bắt buộc, AI không thay chuyên gia) | Rất cao |

### UC13 — Xuất bản thiết kế

| Mục | Nội dung |
|---|---|
| 1–3 | UC13 — Xuất bản thiết kế. Công bố thiết kế đã được chuyên gia phê duyệt, kèm nhãn AI và ghi công nguồn |
| 4. Tác nhân chính | AS-IS: QC Officer gọi `POST /publish`. TO-BE: hệ thống tự chạy khi đủ điều kiện, QC Officer giám sát |
| 5. Hỗ trợ | — |
| 6. Kích hoạt | AS-IS: QC gọi API. TO-BE: kết luận thẩm định là Đạt |
| 7. Tiền điều kiện | Trạng thái `approved` |
| 8. Hậu điều kiện | Sự kiện `published` và `published_at` trong Passport; hoặc giữ "đã phê duyệt, chờ giấy phép" |
| 9. Luồng chính | 1. Kiểm tra trạng thái. 2. Kiểm tra quyền `publish_public` (UC07). 3. Ghi sự kiện xuất bản |
| 10. Thay thế | A1. Quyền chưa cho phép: không xuất bản, giữ phi thương mại |
| 11. Ngoại lệ | E1. Chưa được phê duyệt: 409. E2. Quyền chặn: 403 kèm lý do |
| 12. Quy tắc | BR-17, BR-18 |
| 13–14 | Vào: mã Passport. Ra: thời điểm xuất bản, kết quả cổng quyền |
| 15. Liên quan | UC12, UC07 |
| 16. Ưu tiên | Trung bình |

### UC15 — Tiếp nhận hiện vật mới

| Mục | Nội dung |
|---|---|
| 1–3 | UC15 — Tiếp nhận hiện vật mới. Đưa ảnh hoặc mô hình hiện vật vào thư viện sau khi kiểm tra chất lượng ảnh và quyền |
| 4. Tác nhân chính | Người quản lý dữ liệu |
| 5. Hỗ trợ | Chủ sở hữu ảnh (TO-BE, khi cần xin phép) |
| 6. Kích hoạt | Có ảnh hoặc mô hình hiện vật mới |
| 7. Tiền điều kiện | Có URL nguồn, đơn vị lưu giữ, tình trạng quyền |
| 8. Hậu điều kiện | Mục mới trong `metadata.json` (`active` hoặc `retired` kèm lý do), SHA-256 ảnh, kết quả C1–C4 |
| 9. Luồng chính | 1. Chuẩn bị ảnh, khai báo nguồn. 2. Chạy script tiếp nhận: SHA-256, tách nền, C1–C4. 3. Xác định tình trạng quyền (UC07). 4. Ghi danh mục. 5. Viết mô tả, ý nghĩa hoa văn có nguồn. 6. Xuất dữ liệu web, mô hình 3D |
| 10. Thay thế | A1. Quyền chưa xác minh: gửi đề nghị cấp phép (UC16), hiện vật vẫn dùng được cho thử nghiệm và trình diễn phi thương mại |
| 11. Ngoại lệ | E1. C1 hoặc C2 không đạt: ghi `retired`. E2. Quyền bị từ chối: không dùng |
| 12. Quy tắc | BR-19, BR-20, BR-03 |
| 13–14 | Vào: ảnh, nguồn, đơn vị lưu giữ, giấy phép. Ra: mục danh mục, ảnh tách nền, kết quả tiêu chí |
| 15. Liên quan | UC07, UC16, UC01 |
| 16. Ưu tiên | Cao |
