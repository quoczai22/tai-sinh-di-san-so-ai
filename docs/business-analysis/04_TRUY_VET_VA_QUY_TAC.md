# 04. Ma trận truy vết và quy tắc nghiệp vụ

## 1. Ma trận truy vết BPMN ↔ Use Case ↔ chức năng ↔ mã

Cột "TT" là trạng thái: **A** có trong AS-IS và giữ ở TO-BE, **Đ** có trong AS-IS và đổi ở TO-BE, **M** mới ở TO-BE.

| Quy trình | Hoạt động BPMN | Tác nhân / lane | Use Case | Chức năng hệ thống | API / module | TT |
|---|---|---|---|---|---|---|
| BP-01 | Chọn hiện vật, xem mô hình 3D và sổ hoa văn | Nhà thiết kế | UC01, UC02 | Liệt kê hiện vật, xem 3D, sổ hoa văn | `GET /heritage`, `views/studio.js`, `artifact-book.js` | A |
| BP-01 | Máy GPU sẵn sàng? / Trả bộ sinh sẵn | Cổng Vercel | UC03 (A1) | Chọn chế độ, dự phòng | `GET /health`, `core/data.js::canGenerate`, `api/live.js` | A |
| BP-01 | Chuyển yêu cầu sinh; Trong hạn mức? | Cổng Vercel, API | UC03 (E1) | Hạn mức, hàng chờ | `POST /generate`, `main.py::rate_limit`, `MAX_ACTIVE_JOBS` | A |
| BP-01 | Trả lỗi 429, cảnh báo vận hành | API, cổng | UC03 (E1), UC18 | Cảnh báo Zalo | `_shared.js::alertModalIssue` | A |
| BP-01 | Kiểm tra quyền mục đích thử nghiệm | API | UC07 | Cổng quyền | `registry.py::rights_gate(experiment)` | A |
| BP-01 | Chuẩn bị hoa văn; Sinh áo dài nền | Pipeline AI | UC03 | Tách nền, Canny, LoRA, SAM | `pipeline/run.py`, `generation/garment/garment_lora.py` | A |
| BP-01a | Sinh hoa văn; Cổng G2; Đổi seed; Giữ bản ít lỗi nhất | Pipeline, cổng | UC08 | Sinh, đo, sinh lại | `generation/pattern/`, `quality/pattern_retry.py` | A |
| BP-01a | Ghép, hoàn thiện; Cổng G3; Thử lại; Bản ghép thô | Pipeline, cổng | UC08 | Hoàn thiện, đo, thử lại | `garment.py::polish_locked`, `quality/retry.py` | A |
| BP-01 | Lập Design Passport; Gán trạng thái duyệt | API | UC09, UC08 | Passport, định tuyến trạng thái | `provenance/builder.py`, `quality/assess.py` | A |
| BP-01 | Xem 4 thiết kế ở trang Kết quả | Nhà thiết kế | UC03, UC04 | Trang Kết quả, danh sách đã tạo | `views/result.js`, `views/mine.js` | A |
| BP-02 | Bấm Tải xuống; In nhãn AI, lưu PNG | Nhà thiết kế, trình duyệt | UC05 | Tải ảnh có nhãn | `core/download.js` | Đ |
| BP-02 | Xuất tệp có nhãn AI và mã Passport | Cổng, API | UC05 | Xuất tệp có siêu dữ liệu | `GET /passports/{id}/export`, `labeling.py` (cần mở route ở `live.js`) | M |
| BP-02 | Thiết kế tạo trực tiếp? / Khoá nút | Ứng dụng web | UC06 (E3) | Khoá sửa thiết kế sinh sẵn | `views/edit.js` | A |
| BP-02 | Sửa ảnh; Tải PNG lên, khai báo | Nhà thiết kế | UC06 | Biểu mẫu sửa | `components/edit-panel.js`, `core/edit-rules.js` | A |
| BP-02 | Kiểm tra PNG, hạn mức | Cổng Vercel | UC06 | Kiểm tra tệp | `web_ui/api/edit.js` | A |
| BP-02 | Lưu phiên bản; Chạy G3 cho bản sửa | API | UC06, UC08, UC09 | Phiên bản, G3 | `POST /passports/{id}/edits`, `assess.py::assess_edit` | A |
| BP-02 | Đề cử thiết kế; Ghi đề cử, đưa vào hàng đợi | Nhà thiết kế, API | UC20 | Hàng đợi thẩm định | Route mới, ví dụ `POST /passports/{id}/nominate` | M |
| BP-03 | Mở đợt; Lấy danh sách thiết kế | QC Officer | UC14, UC11 | Đọc Passport | `GET /passports` | Đ |
| BP-03 | Thiết kế đổi trạng thái; Định tuyến theo trạng thái | Hệ thống | UC11 | Sự kiện trạng thái | Hook sau `P.set_approval` hoặc tác vụ định kỳ | M |
| BP-03 | Xem cảnh báo, quyết định QC | QC Officer | UC10 | Quyết định QC | `POST /passports/{id}/qc` | Đ (thêm bảng QC) |
| BP-03 | Lập gói chấm mù; Gửi link | QC Officer → Hệ thống | UC11 | Gói chấm mù | `scripts/eval/build_blind_review.py`, `build_google_form.py` | Đ (tự động) |
| BP-03 | Chấm mù 5 tiêu chí | Chuyên gia | UC12 | Phiếu chấm | Google Form (AS-IS); cổng thẩm định web (TO-BE) | Đ |
| BP-03 | Nhận phiếu; Nhập kết quả vào Passport | QC Officer | UC11 | Ghi phiếu | `POST /passports/{id}/reviews`, `import_google_form.py` | Đ (bỏ nhập tay) |
| BP-03 | Quá 7 ngày; Đã nhắc 2 lần?; Nhắc chuyên gia; Mời chuyên gia khác | Hệ thống, QC | UC11 | Hạn xử lý | Mới (timer) | M |
| BP-03 | Tổng hợp phiếu; Có mâu thuẫn quy tắc?; Xem lại | Hệ thống, QC | UC12, UC11 | Quy tắc ER-1.0 | `config/expert_rubric.json`, `submit_review` (`rule_conflict`) | Đ |
| BP-03 | Kiểm tra quyền xuất bản; Xuất bản | QC (AS-IS) / Hệ thống (TO-BE) | UC13, UC07 | Xuất bản | `POST /passports/{id}/publish`, `rights_gate(publish_public)` | Đ |
| BP-04 | Chuẩn bị ảnh; Chạy script tiếp nhận; C1–C4 | Người quản lý dữ liệu, script | UC15 | Tiếp nhận | `scripts/data_prep/ingest_heritage_image.py`, `assess_selection` | A |
| BP-04 | Xác định tình trạng quyền | Script | UC07 | Cổng quyền C3 | `config/heritage_selection.json` `C3_rights` | A |
| BP-04 | Gửi đề nghị cấp phép; Cập nhật trạng thái quyền | Người quản lý dữ liệu | UC16 | Quản lý quyền | `metadata.json` `permission_request` (sửa tay) | Đ |
| BP-04 | Nhận phản hồi / Quá 14 ngày; Nhắc lại | Hệ thống | UC16 | Theo dõi đề nghị | Mới (timer, biểu mẫu quyền) | M |
| BP-04 | Ghi danh mục; Viết ý nghĩa hoa văn; Xuất dữ liệu web | Script, người quản lý | UC15 | Danh mục, dữ liệu web | `metadata.json` `artifact_info`, `scripts/demo/export_demo_data.py`, `scripts/web/export_heritage_glb.py` | Đ (tự xuất) |
| (ngoài BPMN) | Thử nghiệm có kiểm soát | QC Officer | UC17 | Thí nghiệm, phân tích | `tsds/evaluation/experiment.py` | A |
| (ngoài BPMN) | Lệnh tra cứu `/gpu`, `/runs`, `/usage` | Người vận hành | UC18 | Bot Zalo | `web_ui/api/bot_ops_commands.js` | A |
| (mọi quy trình) | Đăng nhập theo vai trò | Nhân sự nội bộ | UC19 | Khoá theo vai trò | Thay `DH_API_KEY` chung bằng khoá/tài khoản theo vai trò | M |

Kiểm tra mồ côi:

- Mọi hoạt động BPMN có Use Case hoặc là bước nội bộ của ca được include (UC07, UC08, UC09).
- Mọi Use Case có tác nhân, trừ ca include (UC07–UC09) và ca extend (UC02, UC21), đúng chuẩn UML.
- Chức năng trong mã không có hoạt động BPMN: UC17 (thí nghiệm, quy trình nghiên cứu riêng ở `docs/finals/06_EXPERIMENTS.md`)
  và lệnh tra cứu của UC18 (hỗ trợ vận hành). Cả hai cố ý không vẽ vì không thuộc luồng giá trị thiết kế.
- Route phụ trợ không cần ca riêng: `GET /health` (chọn chế độ, UC03), `GET /heritage/{id}`, `GET /heritage/{id}/provenance`,
  `GET /media/heritage/{id}` (UC01); `GET /media/run/...`, `GET /media/artifact` (ảnh cho UC03, UC04);
  `GET /runs`, `GET /runs/{id}`, `GET /quality/designs`, `GET /provenance/catalog` (UC14); `GET /experiments` (UC17);
  `POST /audit` (nhật ký sự kiện phục vụ KPI). Cùng 10 route nghiệp vụ (`GET /heritage`, `POST /generate`, `GET /generate/{id}`, `GET /passports`, `GET /passports/{id}`,
  `/qc`, `/reviews`, `/edits`, `/publish`, `/export`), đủ 22/22 route của `tsds/api/main.py`.

## 2. Quy tắc nghiệp vụ

| Mã | Quy tắc | Áp dụng ở | Căn cứ |
|---|---|---|---|
| BR-01 | Tối đa 6 lượt sinh/giờ/IP ở API, 10 lượt/giờ/IP ở cổng Vercel | BP-01 | `main.py` `TSDS_GENERATE_PER_HOUR`; `_shared.js` `RATE_LIMIT_PER_HOUR` |
| BR-02 | Hàng chờ GPU tối đa 3 lượt (đang chờ + đang chạy); đầy thì trả 429 | BP-01 | `main.py` `TSDS_MAX_ACTIVE_JOBS` |
| BR-03 | Cổng quyền theo mục đích: `retired` chỉ còn thử nghiệm; `permission_denied` chặn mọi mục đích; `unverified` được thử nghiệm và trình diễn phi thương mại; xuất bản cần `public_domain`, `open_license`, `permission_granted` hoặc `own_work`; thương mại bị chặn ở cấp hệ thống (LoRA phi thương mại) | BP-01, BP-03, BP-04 | `registry.py::rights_gate`, `heritage_selection.json` |
| BR-04 | Chỉ hiện vật `active` hiện ở Studio và được tạo thiết kế | BP-01 | `studio.js`, `main.py::generate_designs` (404) |
| BR-05 | G2 lỗi: sinh lại tối đa 3 lần, seed tăng 1, giữ prompt, trọng số, bảng màu; hết lượt giữ bản ít lỗi nhất, Passport `qa_failed` | BP-01a | `pattern_retry.py`, `quality_gate.json` `max_retries` |
| BR-06 | G3 lỗi: thử lại hoàn thiện (đổi seed, hạ độ nhiễu); hết lượt trả bản ghép thô | BP-01a | `quality/retry.py` |
| BR-07 | Trạng thái sau cổng: lỗi không sửa được → `qa_failed`; cảnh báo → `qa_warning`; còn lại → `pending_expert_review`; cổng kỹ thuật **không bao giờ** đặt `approved` | BP-01, BP-02 | `assess.py::approval_from_assessment` |
| BR-08 | Máy GPU không sẵn sàng: hiện bộ đã sinh sẵn kèm nhãn "Kết quả đã sinh sẵn — không phải sinh trực tiếp"; không giả lập việc sinh | BP-01 | `live.js` `DEMO_LABEL`, `studio.js` |
| BR-09 | Bản sửa: PNG thật, ≤ 3 MB (cổng web; API ≤ 8 MB), cạnh dài ≤ 4096 px, tối đa 5 lượt/giờ/IP | BP-02 | `api/edit.js`, `edit-rules.js`, `main.py` `MAX_EDIT_BYTES` |
| BR-10 | ID người sửa bắt đầu bằng TSDS, 5–24 ký tự; vai trò `designer` hoặc `qc_officer`; mô tả 5–500 ký tự; công cụ 2–80 ký tự; không thu họ tên | BP-02 | `edit-rules.js`, `EditRequest` |
| BR-11 | Chỉ thiết kế có Passport trên máy chủ mới được sửa; thiết kế sinh sẵn bị khoá kèm lý do | BP-02 | `views/edit.js` |
| BR-12 | Bản sửa là phiên bản mới mang băm phiên bản trước, phiên bản cũ giữ nguyên; luôn chạy lại G3 và đặt lại trạng thái duyệt | BP-02 | `main.py::submit_edit`, `passport.py` |
| BR-13 | Chỉ thẩm định thiết kế ở trạng thái `pending_expert_review` hoặc `revision_requested` | BP-03 | `submit_review` (409) |
| BR-14 | Quy tắc đạt ER-1.0: không tiêu chí nào < 3 và "Phù hợp văn hoá" ≥ 4. Quyết định cuối do chuyên gia chọn; quy tắc chỉ cảnh báo khi "Đạt" mâu thuẫn với điểm | BP-03 | `expert_rubric.json` `pass_rule`, `rule_conflict` |
| BR-15 | Chấm mù: người chấm không thấy mã phương án, trọng số, điểm AI, quyết định người khác; thứ tự xáo theo người chấm | BP-03 | `expert_rubric.json` `blind_protocol`, `build_blind_review.py` |
| BR-16 | Chỉ lưu tên người chấm khi người đó đồng ý | BP-03 | `ReviewRequest.consent_to_store_name` |
| BR-17 | Chỉ xuất bản thiết kế `approved` | BP-03 | `publish` (409) |
| BR-18 | Xuất bản cần cổng quyền `publish_public` cho phép | BP-03 | `publish` (403) |
| BR-19 | C1: cạnh ngắn ảnh và cạnh dài vật ≥ 512 px; C2: mật độ nét ≥ 12.055 px (60 % mốc 20.092); C1 hoặc C2 không đạt → `retired` | BP-04 | `heritage_selection.json` |
| BR-20 | C3: mỗi hiện vật phải có URL nguồn, đơn vị lưu giữ và tình trạng quyền | BP-04 | `heritage_selection.json` `C3_rights` |
| BR-23 | QC không được chuyển chuyên gia thiết kế `qa_failed`; chỉ được trả về sửa | BP-03 | `qc_decision` (409) |
| BR-24 | Mọi ảnh có AI tham gia mang nhãn "Hỗ trợ bởi AI" trên giao diện và trên tệp tải; tệp xuất qua API có mã Passport, SHA-256, ghi công trong siêu dữ liệu PNG | BP-02 | `badges.js`, `download.js`, `labeling.py` |

Quy tắc đề xuất cho TO-BE (chưa có trong mã):

| Mã | Quy tắc đề xuất | Áp dụng ở |
|---|---|---|
| BR-21 | Hạn phiếu thẩm định 7 ngày kể từ khi gửi link; quá hạn thì nhắc chuyên gia, tối đa 2 lần; sau đó QC mời chuyên gia khác | BP-03 |
| BR-22 | Phiếu có `rule_conflict = true` phải được QC xem lại và chốt kết luận trước khi xuất bản | BP-03 |
| BR-25 | Đề nghị cấp phép chưa có phản hồi sau 14 ngày thì nhắc lại, tối đa 2 lần; sau đó đóng đề nghị, giữ "chưa xác minh" | BP-04 |
| BR-26 | Chỉ thiết kế có Passport trên máy chủ và ở `pending_expert_review` mới được đề cử | BP-02 |
| BR-27 | Mỗi thao tác ghi gắn với người thực hiện đã xác thực (khoá hoặc tài khoản theo vai trò) | Mọi quy trình |

Ghi chú về con số: hạn 7 ngày, 14 ngày và 2 lần nhắc là **mục tiêu đề xuất**, chưa có số liệu đo. Nên điều chỉnh sau khi
có dữ liệu thời gian chờ thật (KPI K13 trong `docs/finals/08_KPI.md`).
