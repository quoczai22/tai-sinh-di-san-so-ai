# 03. BPMN 2.0: quy trình end-to-end

Tệp:

| Tệp | Nội dung |
|---|---|
| `diagrams/tsds_to_be.bpmn` | TO-BE, BPMN 2.0 XML có phần sơ đồ (DI). Mở được bằng Camunda Modeler, bpmn.io, Signavio |
| `diagrams/tsds_as_is.bpmn` | AS-IS (bản 09/2026) |
| `diagrams/bpmn_to_be.svg`, `bpmn_as_is.svg` | Ảnh xuất từ cùng mô hình, để xem nhanh |
| `scripts/docs/build_diagrams.py` | Mã sinh cả XML và SVG từ một mô hình duy nhất, nên hai bản không lệch nhau |

Kiểm tra: cả hai tệp `.bpmn` được nạp bằng `bpmn-moddle` (thư viện đọc metamodel BPMN 2.0 của bpmn.io) và không có cảnh báo nào. Bộ kiểm thử `tests/test_diagrams.py` kiểm tra lại cấu trúc mỗi lần chạy.

## Pool và lane

| Pool / lane | Loại | Vì sao tách như vậy |
|---|---|---|
| Nền tảng Tái Sinh Di Sản Số | Pool có quy trình | Mọi việc do nhóm và hệ thống của nhóm kiểm soát |
| → Nhà thiết kế | Lane | Người dùng chính: chọn hiện vật, điều chỉnh, chọn phương án, sửa tay |
| → Hệ thống AI (GPU) | Lane | Việc do mô hình chạy: trích đặc trưng, sinh hoa văn, sinh áo dài nền (LoRA), ghép, polish, khoá họa tiết |
| → Kiểm soát chất lượng | Lane | Cổng G2, G3 (hệ thống) và QC Officer (người) cùng một lane vì cùng chịu trách nhiệm "đủ điều kiện kỹ thuật chưa" |
| → Dữ liệu và Passport | Lane | Kiểm tra nguồn gốc, quyền, lưu phiên bản, cổng xuất bản |
| Hội đồng chuyên gia | Pool riêng | Chuyên gia di sản và thiết kế **không thuộc** nhóm; tách pool để thể hiện tính độc lập. Giữa hai pool chỉ có message flow, đúng ngữ nghĩa BPMN |
| Chủ sở hữu ảnh | Pool hộp đen | Nhóm không biết và không kiểm soát quy trình bên trong của chủ sở hữu ảnh; chỉ gửi thư đề nghị cấp phép |

## Đối chiếu 18 bước nghiệp vụ với phần tử BPMN

| Bước | Phần tử TO-BE | Loại | Lane |
|---|---|---|---|
| 1. Chọn hoặc tải lên hiện vật | Chọn hoặc tải lên hiện vật gốm | User Task | Nhà thiết kế |
| 2. Kiểm tra dữ liệu và nguồn gốc | Kiểm tra dữ liệu, nguồn gốc (C1–C4) → cổng "Đạt tiêu chí tuyển ảnh?" | Service Task + Exclusive Gateway | Dữ liệu |
| 3. Kiểm tra quyền và bản quyền | Kiểm tra quyền sử dụng, giấy phép → cổng "Tình trạng quyền?" (3 nhánh) | Service Task + Exclusive Gateway | Dữ liệu |
| 4. Trích xuất đặc trưng | Trích xuất đặc trưng: tách nền, Canny, bảng màu → Sinh áo dài nền (LoRA), tách vùng áo (SAM) | Service Task | AI |
| 5. Sinh họa tiết | Sinh họa tiết SD1.5 + ControlNet, có boundary error event "Lỗi GPU" | Service Task | AI |
| 6. Kiểm tra chất lượng họa tiết | Cổng G2 → "Hoa văn đạt?" | Service Task + Exclusive Gateway | QC |
| 7–8. Chuyển sang thiết kế, ghép vào áo | Chọn bố cục (CLIP), ghép hoa văn lên áo do LoRA sinh → Hoàn thiện chỉ vùng áo, khoá họa tiết | Service Task | AI |
| 9–10. Kiểm tra thiết kế cuối, đo giữ họa tiết và dáng áo | Cổng G3 → "Kết quả G3?" (Đạt / Cảnh báo / Không đạt) | Service Task + Exclusive Gateway | QC |
| 11. Không đạt thì quay lại bước phù hợp | G2 không đạt → sinh lại với seed kế tiếp (dưới 3 lần); đủ 3 lần → giữ bản ít lỗi nhất, gắn cờ `qa_failed` (`tsds/quality/pattern_retry.py`). G3 không đạt → thử lại hoàn thiện: đổi seed, hạ độ nhiễu, cuối cùng trả bản ghép thô (`tsds/quality/retry.py`); vẫn lỗi → QC Officer xem | Vòng lặp | AI, QC |
| 12. Đạt thì chuyển chuyên gia | Xem bộ 4 thiết kế (trang Kết quả) → Lập gói chấm mù, gửi chuyên gia (`scripts/eval/build_blind_review.py`) | User Task + Send Task, message flow | Nhà thiết kế, QC |
| 13. Chuyên gia đánh giá | Nhận yêu cầu → Chấm mù 5 tiêu chí → Ghi quyết định và lý do → Gửi phiếu | Message Start, User Task, Message End | Pool chuyên gia |
| 14. Không đạt thì ghi lý do, sửa, thẩm định lại | "Kết quả thẩm định?" → Cần sửa → Ghi lý do vào Passport → Chỉnh sửa thủ công → Tải bản sửa lên → quay lại cổng G3 | Service Task, **Manual Task**, User Task | QC, Nhà thiết kế |
| 15. Đạt thì phê duyệt | Phê duyệt, cập nhật Design Passport | Service Task | Dữ liệu |
| 16–17. Tạo Passport, lưu phiên bản, seed, checksum, cấu hình, lịch sử | Lưu phiên bản, seed, checksum, cấu hình | Service Task | Dữ liệu |
| 18. Xuất bản hoặc tải xuống | "Quyền cho phép xuất bản?" → Xuất bản kèm nhãn AI, ghi công / Cho tải xuống, nhãn phi thương mại | Exclusive Gateway + Service Task | Dữ liệu |

Ghi chú: Passport thực tế được **tạo ngay sau lần chạy** (để cổng chất lượng có chỗ ghi kết quả) và được **cập nhật** ở bước 15–17. Sơ đồ thể hiện bước cập nhật vì đó là thời điểm Passport có giá trị pháp lý (đã phê duyệt).

## Vì sao có từng gateway

Mỗi gateway tương ứng một quyết định có thật trong mã hoặc trong phiếu chuyên gia. Không có gateway trang trí.

| Gateway | Điều kiện | Ở đâu trong mã |
|---|---|---|
| Đạt tiêu chí tuyển ảnh? | C1, C2 không FAIL | `tsds/provenance/registry.py::assess_selection` |
| Tình trạng quyền? | `rights_status`: bị từ chối → kết thúc; chưa xác minh → gửi thư xin phép, gắn nhãn phi thương mại, vẫn được thử nghiệm; hợp lệ → đi tiếp | `tsds/provenance/registry.py::rights_gate` |
| Hoa văn đạt? | G2; đếm số lần, dưới 3 lần thì sinh lại với seed kế tiếp, đủ 3 lần thì giữ bản ít lỗi nhất và gắn cờ `qa_failed` | `tsds/quality/gate.py::evaluate_pattern`, `tsds/quality/pattern_retry.py`, `config/quality_gate.json` (`max_retries`) |
| Kết quả G3? | PASS / WARN / FAIL | `tsds/quality/gate.py::evaluate_final` |
| QC quyết định? | Chuyển chuyên gia (chỉ thiết kế ở mức cảnh báo; API chặn thiết kế `qa_failed`) hoặc trả về sửa | `POST /passports/{id}/qc` |
| Kết quả thẩm định? | approve / revise / reject | `POST /passports/{id}/reviews` |
| Quyền cho phép xuất bản? | Cổng quyền mục đích `publish_public` | `POST /passports/{id}/publish` |

Hai gateway không nhãn trong sơ đồ là **gateway hợp nhất** (merge): nhánh "chưa xác minh" và "hợp lệ" gặp lại nhau trước khi trích đặc trưng. BPMN 2.0 cho phép hợp nhất bằng exclusive gateway khi chỉ một nhánh đến tại một thời điểm.

## Nhánh lỗi và vòng lặp

- **Boundary error event** trên "Sinh họa tiết": máy hết bộ nhớ GPU hoặc mô hình lỗi → kết thúc lỗi, job ghi trạng thái `failed` và loại lỗi vào nhật ký. Mã: `tsds/pipeline/run.py` bắt lỗi theo từng biến thể, một biến thể lỗi không làm hỏng ba biến thể còn lại.
- **Vòng G2**: sinh lại tối đa 3 lần, mỗi lần seed tăng 1, giữ nguyên prompt, trọng số ControlNet và bảng màu; quá 3 lần thì giữ bản ít lỗi nhất, Passport ghi `qa_failed` (mã không có bước người chỉnh tham số).
- **Vòng G3**: khoá họa tiết là bước mặc định của luồng; vòng thử lại polish (đổi seed, hạ độ nhiễu, cuối cùng trả bản ghép thô) rồi đo lại; vẫn lỗi thì QC Officer xem và chỉ được trả về sửa.
- **Vòng thẩm định**: chuyên gia yêu cầu sửa → sửa tay → **quay lại G3** → thẩm định lại. API thực hiện đúng vòng này: tải bản sửa lên thì hệ thống chạy G3 trên bản sửa trước khi đưa về hàng đợi.

## Sequence flow và message flow

- Sequence flow chỉ nằm trong một pool.
- Message flow (nét đứt) chỉ đi giữa các pool: "Thư đề nghị cấp phép" (đến chủ sở hữu ảnh), "Yêu cầu thẩm định" và "Phiếu thẩm định" (với hội đồng chuyên gia).

## Đối chiếu sơ đồ với mã (rà soát 21/11/2026)

Sơ đồ TO-BE được sửa để khớp mã hiện tại. Những chỗ đã sửa:

| Trước | Mã thực tế | Sửa trong sơ đồ |
|---|---|---|
| Ghép lên "áo mẫu" cố định | Áo dài nền sinh mới bằng LoRA mỗi lượt, vùng áo tách bằng SAM (`tsds/generation/garment/garment_lora.py`, `tsds/pipeline/run.py`) | Thêm bước "Sinh áo dài nền (LoRA), tách vùng áo (SAM)" |
| "Hoàn thiện img2img" toàn ảnh | Hoàn thiện chỉ vùng áo, khoá họa tiết (`garment.polish_locked`) | Đổi tên bước |
| G2 lỗi đủ 3 lần → Nhà thiết kế điều chỉnh tham số | Hệ thống giữ bản ít lỗi nhất, gắn cờ `qa_failed` (`tsds/quality/pattern_retry.py`) | Thay bằng Service Task ở lane Kiểm soát chất lượng |
| "Sửa: khoá họa tiết hoặc giảm strength" | Thử lại hoàn thiện: đổi seed, hạ độ nhiễu, cuối cùng trả bản ghép thô (`tsds/quality/retry.py`) | Đổi tên; G3 vẫn lỗi sau thử lại thì chuyển QC Officer |
| QC "trả về sửa" → sửa tự động | `POST /passports/{id}/qc` ghi `qa_failed` kèm lý do, chờ sửa tay rồi tải lên (`POST /passports/{id}/edits`) | Nhánh "Trả về sửa" đi tới "Ghi lý do yêu cầu sửa vào Passport" |
| "Chọn phương án đề cử", "Gửi yêu cầu thẩm định ẩn danh" | Mã không có bước đề cử; gói chấm mù lập bằng `scripts/eval/build_blind_review.py` | Đổi tên hai bước |

Những điểm sơ đồ cố ý không vẽ vì là chi tiết kỹ thuật, không phải quyết định nghiệp vụ:

- **Hàng chờ GPU**: `POST /generate` nhận tối đa 3 lượt đang chờ hoặc đang chạy (`TSDS_MAX_ACTIVE_JOBS`), quá thì trả 429; giới hạn 6 lượt/giờ/IP ở API, 10 lượt/giờ/IP ở cổng Vercel.
- **Dự phòng khi máy GPU lỗi**: cổng `web_ui/api/live.js` trả bộ thiết kế đã sinh sẵn, trang Kết quả ghi rõ "Kết quả đã sinh sẵn — không phải sinh trực tiếp".
- **Seed**: web không cho nhập seed. Áo nền dùng seed ngẫu nhiên mỗi lượt (`garment_lora.pick_seed`), hoa văn dùng seed mặc định 42 rồi tăng dần khi sinh lại; cả hai ghi vào Passport.
- **C1–C4** chạy khi nạp ảnh (`scripts/data_prep/ingest_heritage_image.py`); hiện vật không đạt ở trạng thái `retired` nên không xuất hiện ở Studio. Kiểm tra quyền mục đích "thử nghiệm" chạy lại ở đầu mỗi lượt sinh (`tsds/pipeline/run.py.py`; quyền bị từ chối thì job thất bại).

Khoảng trống còn lại giữa quy trình và giao diện web (không sửa trong đợt này):

- Các bước của QC Officer, chuyên gia, chỉnh sửa tay và xuất bản chạy qua API, **chưa có giao diện web** (khu vực chuyên môn đã gỡ khỏi web ngày 19/11/2026).
- Nút "Tải xuống" ở trang Kết quả tải ảnh thiết kế **không kèm nhãn AI**; tệp có nhãn AI và mã Passport chỉ có qua `GET /passports/{id}/export`.

## AS-IS

Luồng bản 09/2026 có 3 lane (Người dùng, Web UI + API, Pipeline AI), không có gateway: người dùng chọn 1 trong 6 hiện vật, bấm "Tạo thiết kế", API chặn job thứ hai (HTTP 409), pipeline sinh 4 hoa văn với seed 42, ghép, img2img, **ghi đè ảnh cũ cùng tên tệp**, trả 4 ảnh và độ tương đồng của hoa văn, người dùng xem Passport 4 trường. So với TO-BE: thiếu 7 gateway quyết định, thiếu pool chuyên gia, thiếu mọi nhánh lỗi và vòng sửa.
