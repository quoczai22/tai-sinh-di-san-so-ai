# 02. Bộ BPMN 2.0: AS-IS và TO-BE

Tệp sơ đồ ở `diagrams/`. Mỗi sơ đồ có ba dạng: `.bpmn` (BPMN 2.0 XML có phần hình DI, mở bằng Camunda Modeler hoặc
demo.bpmn.io), `.svg` và `.png` (ảnh để chèn báo cáo). Cả ba sinh từ một mô hình duy nhất
`tools/models.py`, nên ảnh và XML không lệch nhau. Sinh lại: xem [README.md](README.md#sinh-lại-sơ-đồ).

## 1. Quy ước

| Ký hiệu | Ý nghĩa |
|---|---|
| Pool | Một bên tham gia. "Nền tảng Tái Sinh Di Sản Số" là pool có quy trình; Chủ sở hữu ảnh, Người vận hành (Zalo) là pool hộp đen (không biết quy trình bên trong). Hội đồng chuyên gia được mở ra vì có tác vụ cần mô tả |
| Lane | Vai trò hoặc thành phần thực hiện: người (Nhà thiết kế, QC Officer, Người quản lý dữ liệu) hoặc hệ thống (ứng dụng web, cổng Vercel, API, pipeline AI) |
| Màu vàng | Tác vụ người (User Task, Manual Task) |
| Màu xanh lam | Tác vụ hệ thống (Service, Send, Receive, Script Task, tiểu quy trình) |
| Màu tím | Business Rule Task: quyết định theo quy tắc có phiên bản (cổng G2, G3, quyền, trạng thái duyệt) |
| Màu xanh lá | Phần tử **mới** trong TO-BE (đề xuất) |
| Màu đỏ | Kết thúc lỗi (Error End Event) |
| Nét đứt có vòng tròn | Message flow, chỉ nối giữa hai pool |
| Nét chấm | Liên kết dữ liệu tới kho (Data Store) |

Mọi cổng rẽ nhánh đều có tên câu hỏi và mỗi nhánh ra có nhãn cộng biểu thức điều kiện (`conditionExpression`) lấy
đúng tên trường trong mã, ví dụ `approval.status = qa_warning`.

## 2. Danh sách sơ đồ

| Mã | Tên | AS-IS | TO-BE | Thay đổi |
|---|---|---|---|---|
| BP-00 | Bản đồ quy trình | `BP-00_ban-do-quy-trinh_AS-IS` | `BP-00_ban-do-quy-trinh_TO-BE` | BP-03 khởi động theo sự kiện thay vì đợt thủ công |
| BP-01 | Tạo thiết kế áo dài | `BP-01_tao-thiet-ke` | Giữ nguyên | Đã tự động hoá, có dự phòng; không đổi |
| BP-01a | Tạo một phương án (lặp 4 lần) | `BP-01a_tao-mot-phuong-an` | Giữ nguyên | Vòng thử lại đã có giới hạn; không đổi |
| BP-02 | Xem, tải và chỉnh sửa thiết kế | `BP-02_xem-tai-chinh-sua_AS-IS` | `BP-02_xem-tai-chinh-sua_TO-BE` | Tải tệp có mã Passport; đề cử thẩm định |
| BP-03 | Kiểm soát chất lượng, thẩm định, xuất bản | `BP-03_kiem-soat-tham-dinh-xuat-ban_AS-IS` | `…_TO-BE` | Hàng đợi tự động, cổng thẩm định web, hạn 7 ngày, xử lý mâu thuẫn, xuất bản tự động có kiểm soát |
| BP-04 | Tiếp nhận hiện vật, quản lý quyền | `BP-04_tiep-nhan-hien-vat_AS-IS` | `…_TO-BE` | Theo dõi đề nghị cấp phép có hạn, nhắc lại; tự xuất dữ liệu web |

BP-01 và BP-01a không vẽ bản TO-BE riêng: luồng đã tự động hoá hết các bước có thể tự động, mỗi vòng lặp đều có giới
hạn, mỗi lỗi đều có nhánh xử lý. Thay đổi chỉ để giảm số bước thì không tạo giá trị (nguyên tắc 6 của yêu cầu).

## 3. BP-00 Bản đồ quy trình

Bốn quy trình nối với nhau qua hai kho dữ liệu: **Danh mục hiện vật** (`metadata.json`) và **Kho Design Passport**
(`outputs/passports`). Các tiểu quy trình vẽ dạng Call Activity (viền đậm, dấu +).

- **AS-IS**: BP-03 có sự kiện bắt đầu riêng "QC mở đợt thẩm định (thủ công)". Giữa BP-01/02 và BP-03 chỉ có kho dữ
  liệu, không có luồng điều khiển. Đây là lý do 13 thiết kế đang "chờ chuyên gia" mà chưa có phiếu nào.
- **TO-BE**: BP-03 bắt đầu bằng sự kiện điều kiện "Thiết kế đổi trạng thái duyệt" (Conditional Start Event), do hệ
  thống phát hiện, không chờ người mở đợt.

## 4. BP-01 Tạo thiết kế áo dài (AS-IS = TO-BE)

Pool Nền tảng gồm ba lane: Nhà thiết kế (web), Ứng dụng web và cổng Vercel, API và pipeline AI. Pool hộp đen: Người
vận hành (Zalo).

| Phần tử | Loại | Căn cứ trong mã |
|---|---|---|
| Chọn hiện vật, xem mô hình 3D và sổ hoa văn | User Task | `views/studio.js`, `components/artifact-book.js` |
| Máy GPU sẵn sàng? | Exclusive Gateway | `core/data.js::canGenerate` đọc `health.generation_available` |
| Trả bộ thiết kế sinh sẵn, ghi nhãn "đã sinh sẵn" | Service Task | `web_ui/api/live.js` (dự phòng), `result.js` |
| Chuyển yêu cầu sinh tới API (10 lượt/giờ/IP) | Service Task | `live.js`, `_shared.js::checkRateLimit` |
| Trong hạn mức, hàng chờ còn chỗ? | Exclusive Gateway | `main.py::rate_limit` (6/giờ/IP), `MAX_ACTIVE_JOBS = 3` |
| Trả lỗi 429, cảnh báo vận hành | Send Task + message | `live.js` gọi `alertModalIssue('hàng chờ đầy (HTTP 429)')` |
| Kiểm tra quyền mục đích "thử nghiệm" → Được phép? | Business Rule Task + Gateway | `run.py`: `rights_gate(item, "experiment")`, `PermissionError` |
| Chuẩn bị hoa văn; Sinh áo dài nền (LoRA, SAM) | Service Task | `run.py` (`cn.prepare`, `garment_lora.generate_garment`) |
| Tạo 4 phương án (BP-01a) | Tiểu quy trình đa thể hiện tuần tự | `run.py` vòng `for index, variant` |
| Không phương án nào thành công | Error Boundary Event | `run.py`: `RuntimeError("Không biến thể nào sinh thành công.")` |
| Báo lỗi trên trang, cảnh báo vận hành | Send Task + message | `live.js` (`job failed`) |
| Lập Design Passport; Gán trạng thái duyệt theo G2, G3 | Service + Business Rule Task | `builder.py`, `assess.py::approval_from_assessment` |
| Kho Design Passport | Data Store | `outputs/passports/*.json` |

## 5. BP-01a Tạo một phương án (AS-IS = TO-BE)

Lane Sinh ảnh và Cổng chất lượng tự động. Hai vòng lặp đều có điều kiện dừng:

- G2 lỗi dưới 3 lần → đổi seed (+1), giữ prompt và trọng số, sinh lại; đủ 3 lần → giữ bản ít lỗi nhất, gắn cờ
  `qa_failed` (`pattern_retry.py`, `config/quality_gate.json` `max_retries = 3`).
- G3 lỗi còn lượt → đổi seed, hạ độ nhiễu, hoàn thiện lại; hết lượt → dùng bản ghép thô (`quality/retry.py`).
- Lỗi GPU khi sinh hoa văn → Error Boundary Event, phương án ghi `failed`, ba phương án còn lại vẫn chạy.

## 6. BP-02 Xem, tải và chỉnh sửa thiết kế

**AS-IS** (`views/result.js`, `mine.js`, `edit.js`, `core/download.js`, `api/edit.js`, `main.py::submit_edit`):

1. Nhà thiết kế phóng to một thiết kế, chọn: Tải xuống, Chỉnh sửa hoặc Xong.
2. Tải xuống: trình duyệt in nhãn "Hỗ trợ bởi AI" lên ảnh, lưu PNG (Script Task, chạy ở trình duyệt).
3. Chỉnh sửa: chỉ thiết kế tạo trực tiếp trên máy chủ; thiết kế sinh sẵn bị khoá nút kèm lý do.
4. Sửa ảnh ngoài hệ thống (Manual Task), tải PNG lên, khai báo ID TSDS, vai trò, nội dung, công cụ, xác nhận lưu hoặc huỷ.
5. Cổng web kiểm tra tệp và hạn mức (Business Rule Task); không hợp lệ thì quay lại bước tải lên.
6. API lưu phiên bản mới (SHA-256, băm cha), chạy G3 cho bản sửa, đặt lại trạng thái duyệt.

**TO-BE** (phần tử xanh lá):

| Thay đổi | Lý do nghiệp vụ | Vấn đề xử lý |
|---|---|---|
| Tải xuống gọi `GET /passports/{id}/export`: tệp có nhãn AI **và** mã Passport, SHA-256, ghi công trong siêu dữ liệu PNG | Ảnh rời hệ thống vẫn truy được nguồn; một cơ chế xuất duy nhất cho web và API | G05 |
| Sau khi xem hoặc sửa: "Đề cử đi thẩm định?" → Đề cử thiết kế → ghi đề cử vào Passport, đưa vào hàng đợi BP-03 | Chuyên gia chỉ chấm thiết kế người dùng thật sự muốn đưa ra; nối BP-02 với BP-03 | G01 |

## 7. BP-03 Kiểm soát chất lượng, thẩm định và xuất bản

**AS-IS** (pool Nền tảng: lane QC Officer, lane API và kho Passport; pool Hội đồng chuyên gia):

1. QC mở đợt thẩm định thủ công, lấy danh sách thiết kế (`GET /passports`).
2. Định tuyến theo trạng thái: `qa_failed` không đưa đi; `qa_warning` → QC quyết định qua `POST /qc` (chuyển chuyên gia
   hoặc trả về sửa); `pending_expert_review` → đi tiếp.
3. QC chạy script lập gói chấm mù (`build_blind_review.py` / `build_google_form.py`), gửi link cho chuyên gia.
4. Chuyên gia chấm mù 5 tiêu chí trên Google Form hoặc phiếu, gửi lại (message flow).
5. QC nhận phiếu, **nhập lại** vào Passport (`POST /reviews`); hệ thống ghi phiếu, đánh dấu mâu thuẫn quy tắc.
6. Quyết định chuyên gia: Cần sửa (không ai báo nhà thiết kế) / Loại / Đạt → QC gọi `POST /publish` → kiểm tra quyền
   xuất bản công khai → xuất bản hoặc giữ phi thương mại.

**TO-BE**:

| Thay đổi | Lý do nghiệp vụ | Vấn đề xử lý |
|---|---|---|
| Khởi động bằng sự kiện điều kiện khi trạng thái duyệt đổi hoặc có đề cử | Không phụ thuộc QC mở đợt; thiết kế không bị bỏ quên | G01, B09 |
| Hệ thống tự xếp hàng đợi, tạo phiếu chấm mù theo vai trò, gửi link | Bỏ hai bước thủ công của QC (lập gói, gửi) | G02 |
| Chuyên gia chấm trên **cổng thẩm định web** (phiếu mù, link có mã riêng); phiếu ghi thẳng vào Passport | Bỏ bước QC nhập lại, giảm rủi ro nhập sai; Hội đồng là pool đa thể hiện (≥ 2 người) | G02, U05 |
| Cổng sự kiện: "Nhận đủ phiếu" hoặc "Quá 7 ngày" → nhắc chuyên gia, chờ tiếp; đã nhắc 2 lần thì QC mời chuyên gia khác | Có hạn xử lý, có điểm dừng, đo được K13 | G03 |
| Tổng hợp phiếu theo quy tắc ER-1.0; "Có mâu thuẫn quy tắc?" → QC xem lại, chốt kết luận | Mâu thuẫn không còn bị bỏ qua; QC chỉ can thiệp khi có ngoại lệ | G04 |
| "Cần sửa" → ghi lý do, mở lại để sửa, hiện ở trang Thiết kế đã tạo | Người dùng ẩn danh vẫn biết thiết kế bị trả (không cần thu thông tin liên hệ) | B06 |
| "Đạt" → kiểm tra quyền → xuất bản tự động kèm nhãn AI; quyền chưa cho phép → "Đã phê duyệt, chờ giấy phép" | Hai điều kiện kiểm soát (chuyên gia, quyền) đã đủ; bỏ bước gọi API thủ công mà không mất kiểm soát | B10 |

QC Officer giữ hai việc có giá trị kiểm soát: xử lý cảnh báo kỹ thuật và xem lại phiếu mâu thuẫn.

## 8. BP-04 Tiếp nhận hiện vật và quản lý quyền

**AS-IS**: người quản lý dữ liệu chuẩn bị ảnh, chạy script tiếp nhận (SHA-256, tách nền, C1–C4). Không đạt C1/C2 → ghi
`retired`. Tình trạng quyền: bị từ chối → không dùng; chưa xác minh → soạn và gửi đề nghị cấp phép bằng email, rồi
**sửa tay** trạng thái quyền trong `metadata.json`; mở / đã cấp phép / tự chụp → đi tiếp. Ghi danh mục, viết mô tả và ý
nghĩa hoa văn có nguồn (`artifact_info`), chạy script xuất dữ liệu web và mô hình 3D.

**TO-BE**:

| Thay đổi | Lý do | Vấn đề xử lý |
|---|---|---|
| Ghi `permission_requested` và ngày gửi ngay khi gửi đề nghị | Trạng thái quyền phản ánh đúng thực tế | G06 |
| Cổng sự kiện "Nhận phản hồi" / "Quá 14 ngày" → nhắc lại tối đa 2 lần → đóng đề nghị, giữ "chưa xác minh" | Có hạn, có điểm dừng, không treo vô thời hạn | G06 |
| Ghi phản hồi (cấp phép, từ chối, phạm vi) qua biểu mẫu quyền thay vì sửa tệp JSON | Tránh sai cú pháp, có kiểm tra trường `scope` mà cổng quyền đọc | G06 |
| Danh mục đổi thì CI tự xuất dữ liệu web và mô hình 3D | Bỏ một bước thủ công dễ quên | — |

## 9. Kiểm định

Kết quả nạp bằng bpmn-js và kiểm tra ngữ nghĩa: [06_KIEM_DINH.md](06_KIEM_DINH.md).
