# 03. BPMN 2.0: quy trình end-to-end

Tệp:

| Tệp | Nội dung |
|---|---|
| `diagrams/tsds_to_be.bpmn` | TO-BE, BPMN 2.0 XML có phần sơ đồ (DI). Mở được bằng Camunda Modeler, bpmn.io, Signavio |
| `diagrams/tsds_as_is.bpmn` | AS-IS (bản 09/2026) |
| `diagrams/bpmn_to_be.svg`, `bpmn_as_is.svg` | Ảnh xuất từ cùng mô hình, để xem nhanh |
| `scripts/12_build_diagrams.py` | Mã sinh cả XML và SVG từ một mô hình duy nhất, nên hai bản không lệch nhau |

Kiểm tra: cả hai tệp `.bpmn` được nạp bằng `bpmn-moddle` (thư viện đọc metamodel BPMN 2.0 của bpmn.io) và không có cảnh báo nào. Bộ kiểm thử `tests/test_diagrams.py` kiểm tra lại cấu trúc mỗi lần chạy.

## Pool và lane

| Pool / lane | Loại | Vì sao tách như vậy |
|---|---|---|
| Nền tảng Tái Sinh Di Sản Số | Pool có quy trình | Mọi việc do nhóm và hệ thống của nhóm kiểm soát |
| → Nhà thiết kế | Lane | Người dùng chính: chọn hiện vật, điều chỉnh, chọn phương án, sửa tay |
| → Hệ thống AI (GPU) | Lane | Việc do mô hình chạy: trích đặc trưng, sinh hoa văn, ghép, img2img, sửa tự động |
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
| 4. Trích xuất đặc trưng | Trích xuất đặc trưng: tách nền, Canny, bảng màu | Service Task | AI |
| 5. Sinh họa tiết | Sinh họa tiết SD1.5 + ControlNet, có boundary error event "Lỗi GPU" | Service Task | AI |
| 6. Kiểm tra chất lượng họa tiết | Cổng G2 → "Hoa văn đạt?" | Service Task + Exclusive Gateway | QC |
| 7–8. Chuyển sang thiết kế, ghép vào áo | Chọn bố cục, ghép tất định lên áo mẫu → Hoàn thiện img2img | Service Task | AI |
| 9–10. Kiểm tra thiết kế cuối, đo giữ họa tiết và dáng áo | Cổng G3 → "Kết quả G3?" (Đạt / Cảnh báo / Không đạt) | Service Task + Exclusive Gateway | QC |
| 11. Không đạt thì quay lại bước phù hợp | G2 không đạt → sinh lại (dưới 3 lần) hoặc Nhà thiết kế điều chỉnh (đủ 3 lần); G3 không đạt → Sửa: khoá họa tiết hoặc giảm strength | Vòng lặp | AI, Nhà thiết kế |
| 12. Đạt thì chuyển chuyên gia | Xem bộ thiết kế, chọn phương án đề cử → Gửi yêu cầu thẩm định ẩn danh | User Task + Send Task, message flow | Nhà thiết kế, QC |
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
| Đạt tiêu chí tuyển ảnh? | C1, C2 không FAIL | `provenance/registry.py::assess_selection` |
| Tình trạng quyền? | `rights_status`: bị từ chối → kết thúc; chưa xác minh → gửi thư xin phép, gắn nhãn phi thương mại, vẫn được thử nghiệm; hợp lệ → đi tiếp | `provenance/registry.py::rights_gate` |
| Hoa văn đạt? | G2; đếm số lần, đủ 3 lần thì chuyển người | `quality/gate.py::evaluate_pattern`, `config/quality_gate.json` (`max_retries`) |
| Kết quả G3? | PASS / WARN / FAIL | `quality/gate.py::evaluate_final` |
| QC quyết định? | Chuyển chuyên gia hoặc trả về sửa | `POST /passports/{id}/qc` |
| Kết quả thẩm định? | approve / revise / reject | `POST /passports/{id}/reviews` |
| Quyền cho phép xuất bản? | Cổng quyền mục đích `publish_public` | `POST /passports/{id}/publish` |

Hai gateway không nhãn trong sơ đồ là **gateway hợp nhất** (merge): nhánh "chưa xác minh" và "hợp lệ" gặp lại nhau trước khi trích đặc trưng. BPMN 2.0 cho phép hợp nhất bằng exclusive gateway khi chỉ một nhánh đến tại một thời điểm.

## Nhánh lỗi và vòng lặp

- **Boundary error event** trên "Sinh họa tiết": máy hết bộ nhớ GPU hoặc mô hình lỗi → kết thúc lỗi, job ghi trạng thái `failed` và loại lỗi vào nhật ký. Mã: `generation/streamlit_runner.py` bắt lỗi theo từng biến thể, một biến thể lỗi không làm hỏng ba biến thể còn lại.
- **Vòng G2**: sinh lại tối đa 3 lần với seed khác hoặc trọng số thấp hơn một mức; quá 3 lần thì Nhà thiết kế quyết định.
- **Vòng G3**: sửa tự động (khoá họa tiết hoặc giảm strength) rồi đo lại.
- **Vòng thẩm định**: chuyên gia yêu cầu sửa → sửa tay → **quay lại G3** → thẩm định lại. API thực hiện đúng vòng này: tải bản sửa lên thì hệ thống chạy G3 trên bản sửa trước khi đưa về hàng đợi.

## Sequence flow và message flow

- Sequence flow chỉ nằm trong một pool.
- Message flow (nét đứt) chỉ đi giữa các pool: "Thư đề nghị cấp phép" (đến chủ sở hữu ảnh), "Yêu cầu thẩm định" và "Phiếu thẩm định" (với hội đồng chuyên gia).

## AS-IS

Luồng bản 09/2026 có 3 lane (Người dùng, Web UI + API, Pipeline AI), không có gateway: người dùng chọn 1 trong 6 hiện vật, bấm "Tạo thiết kế", API chặn job thứ hai (HTTP 409), pipeline sinh 4 hoa văn với seed 42, ghép, img2img, **ghi đè ảnh cũ cùng tên tệp**, trả 4 ảnh và độ tương đồng của hoa văn, người dùng xem Passport 4 trường. So với TO-BE: thiếu 7 gateway quyết định, thiếu pool chuyên gia, thiếu mọi nhánh lỗi và vòng sửa.
