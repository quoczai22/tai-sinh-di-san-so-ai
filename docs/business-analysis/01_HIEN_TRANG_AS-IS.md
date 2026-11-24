# 01. Phân tích hiện trạng (AS-IS) và danh sách vấn đề

Ngày khảo sát: 24/11/2026. Phạm vi: mã nguồn bản chung kết (gói `tai-sinh-di-san-so-ai-main (5)`), báo cáo
`Kiet_Giao_dien_BPMN_UseCase5.docx` (mục 2 BPMN, mục 3 Use Case) và hồ sơ `docs/finals/02_APQC.md`, `03_BPMN.md`,
`04_USE_CASE.md`, `08_KPI.md`.

Quy ước: **AS-IS** là hệ thống đúng như mã nguồn đang chạy (không phải bản 09/2026 như trong `docs/finals`);
**TO-BE** là đề xuất tối ưu. Mọi nhận định AS-IS đều có căn cứ (tệp, hàm, số liệu); điều gì là đề xuất thì ghi rõ
"đề xuất".

## 1. Tài liệu và mã đã khảo sát

| Nhóm | Nguồn | Dùng để xác định |
|---|---|---|
| Giao diện | `web_ui/assets/js/core/routes.js`, `views/studio.js`, `result.js`, `mine.js`, `edit.js`, `components/artifact-book.js`, `core/download.js`, `core/edit-rules.js` | Trang, thao tác người dùng, quy tắc biểu mẫu |
| Cổng web (Vercel) | `web_ui/api/live.js`, `edit.js`, `_shared.js`, `warmup.js`, `bot_*.js` | Route được mở cho web, hạn mức, dự phòng, cảnh báo Zalo |
| API | `tsds/api/main.py` (22 route), `jobs.py`, `store.py`, `audit.py` | Chức năng hệ thống, khoá API, trạng thái job |
| Pipeline AI | `tsds/pipeline/run.py`, `tsds/quality/pattern_retry.py`, `retry.py`, `assess.py`, `gate.py` | Các bước sinh ảnh, cổng G2/G3, vòng thử lại |
| Hồ sơ, quyền | `tsds/provenance/registry.py`, `passport.py`, `builder.py`, `data/heritage/metadata.json`, `config/heritage_selection.json`, `config/expert_rubric.json` | Cổng quyền, trạng thái duyệt, quy tắc đạt |
| Thẩm định | `scripts/eval/build_blind_review.py`, `build_google_form.py`, `import_google_form.py`, `build_expert_docx.py` | Cách chuyên gia chấm trong thực tế |
| Dữ liệu thật | `outputs/passports/*.json` (24 tệp), `outputs/experiments/EXP-A/human_report.json`, `docs/finals/08_KPI.md` | Số liệu hiện trạng |

"Database" của hệ thống là tệp: danh mục hiện vật `data/heritage/metadata.json` (schema 2.0), kho Design Passport
`outputs/passports/*.json`, trạng thái job `outputs/jobs`, nhật ký audit. Không có hệ quản trị cơ sở dữ liệu.

## 2. Bên liên quan và tác nhân

| Vai trò | Tương tác thực tế với hệ thống | Căn cứ |
|---|---|---|
| Nhà thiết kế (người dùng web) | Không đăng nhập. Xem hiện vật, tạo thiết kế, tải ảnh, tải lên bản sửa (tự khai ID bắt đầu bằng TSDS) | `routes.js`, `edit-rules.js` |
| QC Officer | Gọi API ghi (`/qc`, `/publish`, `/reviews`, `/edits`) bằng khoá chung `DH_API_KEY`; chạy script lập gói chấm mù, thử nghiệm | `main.py::verify_api_key`, `scripts/eval/` |
| Chuyên gia thẩm định (di sản, thiết kế) | Chấm trên Google Form hoặc phiếu HTML/Word ngoài hệ thống; **không** gọi API | `build_google_form.py`, `build_expert_docx.py` |
| Người quản lý dữ liệu | Chạy script tiếp nhận ảnh, sửa `metadata.json`, viết mô tả hoa văn | `scripts/data_prep/ingest_heritage_image.py` |
| Người vận hành | Nhận cảnh báo Zalo khi máy GPU lỗi, tra cứu `/gpu`, `/runs`, `/usage` qua bot | `web_ui/api/_shared.js::alertModalIssue`, `bot_ops_commands.js` |
| Chủ sở hữu ảnh / bộ dữ liệu | Nhận đề nghị cấp phép (email, ngoài hệ thống) | `metadata.json` → `permission_request` |
| Hệ thống ngoài | Modal (máy GPU chạy API), Zalo (kênh cảnh báo), Google Forms (phiếu chấm), GitHub Actions (CI) | `modal_app.py`, `docs/CI_MODAL.md` |

Ranh giới hệ thống: **Nền tảng Tái Sinh Di Sản Số** gồm ứng dụng web, cổng Vercel, API FastAPI và pipeline AI.
Modal là hạ tầng chạy pipeline của nhóm nên không vẽ thành tác nhân; Zalo và Google Forms là hệ thống ngoài có trao
đổi thông tin nên được vẽ.

## 3. Quy trình nghiệp vụ đang vận hành

| Mã | Quy trình | Khởi phát | Kết thúc | Nhận xét hiện trạng |
|---|---|---|---|---|
| BP-01 | Tạo thiết kế áo dài | Nhà thiết kế bấm Tạo | Bộ 4 thiết kế, 4 Passport | Tự động hoá gần hết; có dự phòng khi GPU lỗi |
| BP-01a | Tạo một phương án (lặp 4 lần) | BP-01 | Phương án hoàn tất / lỗi | Vòng sinh lại G2, thử lại G3 đều có giới hạn |
| BP-02 | Xem, tải và chỉnh sửa thiết kế | Mở trang Kết quả / Thiết kế đã tạo | Tải ảnh / lưu bản sửa / rời trang | Bản sửa chạy lại G3 |
| BP-03 | Kiểm soát chất lượng, thẩm định, xuất bản | QC mở đợt thủ công | Phê duyệt / sửa / loại / xuất bản | **Tách rời BP-01**; nhiều bước thủ công qua API |
| BP-04 | Tiếp nhận hiện vật, quản lý quyền | Có ảnh mới | Hiện vật có trên Studio | Theo dõi xin phép làm tay |

Số liệu hiện trạng (đọc từ 24 Design Passport trong `outputs/passports/`, 24/11/2026): 13 thiết kế "chờ chuyên gia",
9 "chờ QC xem cảnh báo", 2 "không đạt kiểm định"; **0 phiếu thẩm định, 0 bản sửa, 0 lần xuất bản** được ghi vào
Passport. Thẩm định thực tế chỉ diễn ra trong thí nghiệm EXP-A (28 người chấm qua Google Form, nhập bằng
`import_google_form.py`), không đi qua `POST /passports/{id}/reviews`. Thời gian sinh một bộ 4 thiết kế: 112 đến 142
giây (n = 5, RTX 4060 Laptop, `08_KPI.md` K20). Thời gian chờ thẩm định (K13): chưa đo.

## 4. Quy tắc, yêu cầu chức năng và phi chức năng

Danh sách quy tắc nghiệp vụ có mã BR-01 đến BR-27 nằm ở [04_TRUY_VET_VA_QUY_TAC.md](04_TRUY_VET_VA_QUY_TAC.md#2-quy-tắc-nghiệp-vụ).

Yêu cầu chức năng (FR) đang có trong mã:

| Mã | Yêu cầu | Căn cứ |
|---|---|---|
| FR-01 | Liệt kê hiện vật đang dùng, xem mô hình 3D, xem ý nghĩa hoa văn | `GET /heritage`, `artifact-book.js` |
| FR-02 | Sinh 4 thiết kế từ một hiện vật, có hàng chờ, tiến độ | `POST /generate`, `GET /generate/{id}` |
| FR-03 | Kiểm định G2, G3 tự động, sinh lại có giới hạn | `quality/` |
| FR-04 | Lập Design Passport cho từng thiết kế | `provenance/builder.py` |
| FR-05 | Tải ảnh PNG có nhãn "Hỗ trợ bởi AI" | `core/download.js` |
| FR-06 | Tải lên bản sửa, ghi phiên bản mới, chạy lại G3 | `POST /passports/{id}/edits` |
| FR-07 | QC xem cảnh báo, chuyển chuyên gia hoặc trả về | `POST /passports/{id}/qc` |
| FR-08 | Ghi phiếu thẩm định 5 tiêu chí, đánh dấu mâu thuẫn quy tắc | `POST /passports/{id}/reviews` |
| FR-09 | Xuất bản khi đã duyệt và quyền cho phép | `POST /passports/{id}/publish` |
| FR-10 | Xuất tệp có nhãn AI và mã Passport trong siêu dữ liệu PNG | `GET /passports/{id}/export` |
| FR-11 | Tiếp nhận hiện vật, chạy C1–C4, ghi danh mục | `ingest_heritage_image.py` |
| FR-12 | Cảnh báo vận hành qua Zalo, lệnh tra cứu | `_shared.js`, `bot_ops_commands.js` |
| FR-13 | Lập gói chấm mù, nhập điểm từ Google Form | `scripts/eval/` |

Yêu cầu phi chức năng (NFR):

| Mã | Yêu cầu | Căn cứ |
|---|---|---|
| NFR-01 Bảo mật | Khoá API bắt buộc khi triển khai (`DH_REQUIRE_API_KEY`), khoá giữ phía máy chủ Vercel | `main.py::_enforce_api_key_config` |
| NFR-02 Chống lạm dụng | 6 lượt sinh/giờ/IP (API), 10 lượt/giờ/IP (cổng), 5 lượt sửa/giờ/IP, hàng chờ tối đa 3 | `main.py`, `_shared.js`, `api/edit.js` |
| NFR-03 Sẵn sàng | Máy GPU lỗi thì trả bộ sinh sẵn kèm nhãn, cảnh báo vận hành | `live.js` |
| NFR-04 Riêng tư | Biểu mẫu sửa không thu họ tên; nhật ký chỉ ghi mã Passport | `api/edit.js` |
| NFR-05 Truy vết | SHA-256, phiên bản có băm cha, sổ cái sự kiện | `provenance/passport.py` |
| NFR-06 Minh bạch AI | Nhãn AI trên giao diện và trên tệp tải | `badges.js`, `download.js` |
| NFR-07 Hiệu năng | Bộ 4 thiết kế 112–142 giây trên RTX 4060 (đo) | `08_KPI.md` K20 |

## 5. Luồng dữ liệu chính

```
metadata.json ──(BP-04 ghi)──► danh mục hiện vật ──(GET /heritage)──► Studio
Studio ──POST /generate──► hàng chờ ──► pipeline ──► outputs/runs/<run> + outputs/passports/<id>.json
Trang Kết quả ──GET /passports──► Passport ──(BP-02)──► POST /edits ──► phiên bản mới + G3
QC ──GET /passports──► gói chấm mù ──► Google Form ──► Excel ──► import / POST /reviews ──► Passport
```

## 6. Danh sách vấn đề

Mức độ: **Cao** = sai logic hoặc mâu thuẫn với mã, có thể dẫn tới kết luận sai; **Trung bình** = thiếu sót làm mô hình
không đầy đủ; **Thấp** = trình bày, quy ước.

### 6.1. Vấn đề trong BPMN của báo cáo (Hình 2.1 đến 2.3)

| Mã | Vấn đề | Mức | Căn cứ | Cách xử lý |
|---|---|---|---|---|
| B01 | Message flow "Thư xin phép sử dụng ảnh" xuất phát từ giữa một sequence flow (Hình 2.1). BPMN chỉ cho message flow nối với pool, tác vụ hoặc sự kiện | Cao | Đặc tả BPMN 2.0, mục 9.3 | Gắn vào tác vụ gửi trong BP-04 |
| B02 | Thư xin phép được vẽ như việc **hệ thống** làm mỗi lần tạo thiết kế. Trong mã không có bước gửi thư; cả 6 hiện vật đang ở `open_license`, `permission_request.status = not_sent` | Cao | `metadata.json`, `registry.py::rights_gate` | Chuyển sang BP-04, là việc thủ công của người quản lý dữ liệu |
| B03 | Vòng "Chưa đạt → sinh lại" ở G2 và G3 không có giới hạn: quy trình có thể lặp vô hạn | Cao | `pattern_retry.py` (tối đa 3), `retry.py` (hết lượt thì dùng bản ghép thô) | Thêm điều kiện "dưới 3 lần / đủ 3 lần", "còn lượt / hết lượt" |
| B04 | Sau tiểu quy trình A, mọi thiết kế đều đi tiếp sang thẩm định. Mã định tuyến theo trạng thái: `qa_failed` không được chuyển chuyên gia, `qa_warning` phải qua QC | Cao | `assess.py::approval_from_assessment`, `main.py::qc_decision` | Thêm quy tắc gán trạng thái và cổng "Trạng thái duyệt?" |
| B05 | Trong tiểu quy trình B, kết quả G3 của bản sửa không rẽ nhánh: bản sửa lỗi G3 vẫn được gửi chuyên gia | Cao | `main.py::submit_edit` đặt lại trạng thái theo G3; `/reviews` chặn trạng thái khác "chờ chuyên gia" | Bản sửa đi lại cổng định tuyến |
| B06 | "Cần sửa" kết thúc bằng end event "Trả về chỉnh sửa", nhưng không ai được báo; người dùng web ẩn danh không biết thiết kế bị trả | Trung bình | Không có kênh thông báo trong mã | AS-IS ghi rõ; TO-BE hiện trạng thái ở "Thiết kế đã tạo" |
| B07 | Bốn phương án được vẽ như một lượt duy nhất; thiếu dấu đa thể hiện (lặp tuần tự 4 lần) | Trung bình | `run.py` vòng `for index, variant` | Tiểu quy trình đa thể hiện tuần tự BP-01a |
| B08 | Thiếu nhánh ngoại lệ: hàng chờ đầy (429), quyền bị từ chối, lỗi GPU, máy GPU không sẵn sàng (trả bộ sinh sẵn) | Trung bình | `main.py`, `live.js` | Thêm cổng và sự kiện lỗi |
| B09 | Thẩm định được vẽ như bước nối thẳng sau tạo thiết kế; thực tế là đợt riêng do QC mở, chuyên gia chấm ngoài hệ thống, QC nhập lại | Cao | Mục 3 (0 phiếu trong Passport), `scripts/eval/` | BP-03 có sự kiện bắt đầu riêng |
| B10 | Thiếu bước kiểm tra quyền xuất bản trước khi xuất bản | Cao | `main.py::publish` (403 nếu quyền không cho phép) | Thêm quy tắc và cổng "Được xuất bản?" |
| B11 | Thiếu kho dữ liệu (Design Passport, danh mục hiện vật) dù đây là xương sống truy vết | Thấp | `outputs/passports`, `metadata.json` | Thêm data store |
| B12 | Sơ đồ chỉ có TO-BE, không có AS-IS và bảng so sánh | Trung bình | Yêu cầu phân tích | Bổ sung bộ AS-IS / TO-BE |
| B13 | Sơ đồ là hình vẽ, không có tệp BPMN 2.0 XML tương ứng (riêng `docs/finals/diagrams/tsds_to_be.bpmn` có 18 nhánh cổng có nhãn nhưng thiếu biểu thức điều kiện) | Thấp | `check.py` | Xuất `.bpmn` có DI, kiểm định tự động |

### 6.2. Vấn đề trong Use Case của báo cáo (Hình 3.1, Bảng 3.1, 3.2)

| Mã | Vấn đề | Mức | Căn cứ | Cách xử lý |
|---|---|---|---|---|
| U01 | Tác nhân "Người dùng đã đăng ký", ca UC01 "Đăng ký và đăng nhập", UC17 "Quản lý người dùng": hệ thống không có tài khoản; chỉ có một khoá API chung | Cao | `main.py::verify_api_key`, `edit-rules.js` (ID tự khai) | AS-IS bỏ; TO-BE đề xuất "Đăng nhập theo vai trò" |
| U02 | Chuỗi tổng quát hoá Khách ← Người dùng đã đăng ký ← Nhà thiết kế không có khác biệt hành vi trong mã | Cao | Không có phân quyền | Gộp thành "Nhà thiết kế (người dùng web)" |
| U03 | UC06 "Phân tích họa tiết", UC07 "Sinh họa tiết AI" là bước nội bộ, không phải mục tiêu của tác nhân; "Hệ thống xử lý AI" là thành phần bên trong ranh giới, không phải tác nhân | Cao | UML 2.5: actor nằm ngoài subject | Gộp vào "Tạo thiết kế áo dài" |
| U04 | UC13 "Phê duyệt thiết kế" do QC thực hiện, «extend» UC12: trong mã, phê duyệt là hệ quả của quyết định chuyên gia (`decision = approve`), QC không có thao tác phê duyệt | Cao | `main.py::submit_review` | Bỏ; thay bằng "Xuất bản thiết kế" (có thật) |
| U05 | Chuyên gia được vẽ như dùng hệ thống trực tiếp; thực tế chấm qua Google Form, QC nhập lại | Trung bình | `scripts/eval/` | Thêm Google Forms là hệ thống ngoài; tách "Điều phối thẩm định mù" (QC) và "Chấm mù" (chuyên gia) |
| U06 | Thiếu ca có trong mã: Xem lại thiết kế đã tạo, Tải thiết kế có nhãn AI, Xem ý nghĩa hoa văn, Xử lý cảnh báo QC, Giám sát vận hành (Zalo), Tiếp nhận hiện vật | Trung bình | `mine.js`, `download.js`, `artifact-book.js`, `/qc`, `bot_*.js` | Bổ sung |
| U07 | UC03 "Tải lên hiện vật" gán cho Nhà thiết kế; thực tế người quản lý dữ liệu chạy script | Trung bình | `ingest_heritage_image.py` | Đổi tác nhân, đổi tên "Tiếp nhận hiện vật mới" |
| U08 | UC11 "So sánh các phiên bản" «extend» UC15 nhưng không có giao diện so sánh | Thấp | Không có trong web | Gộp vào "Tra cứu Design Passport" |
| U09 | UC14 "Quản lý Design Passport" cho Nhà thiết kế: Passport do hệ thống tạo và cập nhật, người dùng không quản lý | Trung bình | `builder.py` | Thành ca được include "Ghi Design Passport" |
| U10 | Mức "Đã triển khai" cho các ca chỉ chạy qua API, không có giao diện (QC, thẩm định, xuất bản) | Thấp | `routes.js` | Ghi "chạy qua API" |

### 6.3. Khoảng trống giữa quy trình và hệ thống (dùng cho TO-BE)

| Mã | Khoảng trống | Hệ quả | Căn cứ |
|---|---|---|---|
| G01 | Không có đường tự động từ thiết kế mới sang hàng đợi thẩm định | 13 thiết kế "chờ chuyên gia", 0 phiếu | Mục 3 |
| G02 | QC phải lập gói chấm mù và nhập lại điểm bằng tay | Chuyển giao thừa, rủi ro nhập sai | `scripts/eval/` |
| G03 | Không có hạn chờ phiếu, không nhắc | Thiết kế chờ không giới hạn | Không có timer trong mã |
| G04 | Mâu thuẫn quy tắc chỉ được đánh dấu, không có ai xử lý | Quyết định "Đạt" mâu thuẫn điểm vẫn có hiệu lực | `submit_review` (`rule_conflict`) |
| G05 | Ảnh tải ở web chỉ in nhãn AI, không kèm mã Passport; `/export` có đủ nhưng cổng web không mở route này | Ảnh rời khỏi hệ thống mất liên kết truy vết | `download.js`, `live.js` |
| G06 | Không theo dõi phản hồi đề nghị cấp phép (hiện chưa phát sinh: cả 6 hiện vật là `open_license`) | Khi có hiện vật quyền chưa rõ, trạng thái "chưa xác minh" có thể kéo dài không ai theo dõi | `permission_request` |
| G07 | Một khoá chung cho mọi thao tác ghi; ID người sửa tự khai | Không xác thực được ai duyệt, ai sửa | `verify_api_key` |
