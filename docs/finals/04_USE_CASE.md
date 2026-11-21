# 04. UML Use Case

Tệp: `diagrams/use_case.svg` (ảnh), `diagrams/use_case.puml` (PlantUML, mở và sửa được). Cả hai sinh từ `scripts/12_build_diagrams.py`.

Ranh giới hệ thống: **Nền tảng Tái Sinh Di Sản Số (web + API)**. Máy GPU chạy mô hình là tác nhân phụ nằm ngoài ranh giới, vì nó là hệ thống riêng mà nền tảng gọi đến và có thể vắng mặt (khi đó API trả lỗi 503 rõ ràng, giao diện chuyển sang chế độ trình diễn).

Màu ca sử dụng trên sơ đồ cho biết mức triển khai thật: **xanh** đã chạy, **vàng nét đứt** chạy một phần (qua dòng lệnh hoặc tệp), **trắng chấm** là kế hoạch. Không ca nào được tô "đã chạy" nếu chưa có mã.

## Tác nhân

| Tác nhân | Loại | Mục tiêu | Kế thừa |
|---|---|---|---|
| Khách (Guest) | Chính | Xem thư viện hiện vật, xem thiết kế công khai | – |
| Người dùng đã đăng ký | Chính | Xem lịch sử chỉnh sửa của thiết kế | Kế thừa Khách |
| Nhà thiết kế | Chính | Tạo, chọn, chỉnh sửa, xuất thiết kế | Kế thừa Người dùng đã đăng ký |
| Chuyên gia di sản | Chính | Thẩm định văn hoá và thẩm mỹ | Kế thừa Người dùng đã đăng ký |
| QC Officer | Chính | Xem cảnh báo kỹ thuật, phê duyệt hoặc trả về, điều phối thử nghiệm | Kế thừa Người dùng đã đăng ký |
| Quản trị viên | Chính | Quản lý giấy phép, người dùng, dữ liệu | Kế thừa Người dùng đã đăng ký |
| Hệ thống xử lý AI (GPU) | Phụ | Phân tích, sinh họa tiết, đo chất lượng, chạy thí nghiệm | – |

Vì sao dùng **generalization** cho tác nhân: mọi vai trò nội bộ đều cần mọi thứ Người dùng đã đăng ký làm được (xem lịch sử chỉnh sửa, xem danh mục). Vẽ kế thừa một lần thay vì nối từng vai trò tới từng ca chung, sơ đồ bớt rối mà nghĩa không đổi.

## Ca sử dụng

| Mã | Ca sử dụng | Tác nhân | Triển khai | Mã nguồn / giao diện |
|---|---|---|---|---|
| UC01 | Đăng ký và đăng nhập | Người dùng đã đăng ký | Kế hoạch | Hiện chỉ có khoá ghi `TSDS_WRITE_KEY` |
| UC02 | Xem danh mục hiện vật | Khách | Đã chạy | `GET /heritage`, Trang chủ và lưới chọn ở Studio; sổ hoa văn ở Studio (ảnh tĩnh, ý nghĩa hoa văn, nguồn ảnh, đối chiếu bảo tàng) |
| UC03 | Tải lên hiện vật | Nhà thiết kế | Một phần | Ảnh mới đưa vào bằng dòng lệnh; chưa có nút tải lên |
| UC04 | Kiểm tra nguồn gốc hiện vật | (được include) | Đã chạy | `provenance/registry.py::assess_selection` |
| UC05 | Quản lý giấy phép và bản quyền | Quản trị viên | Một phần | Sửa `data/heritage/metadata.json`; giao diện chỉ xem |
| UC06 | Phân tích họa tiết | Hệ thống AI | Đã chạy | Canny, bảng màu, mật độ nét |
| UC07 | Sinh họa tiết AI | Hệ thống AI | Đã chạy | `generation/pattern.py` |
| UC08 | Tạo thiết kế áo dài | Nhà thiết kế | Đã chạy | `POST /generate`, Studio → trang Kết quả |
| UC09 | Chỉnh sửa thiết kế | Nhà thiết kế | Đã chạy | `POST /passports/{id}/edits` (chưa có giao diện web) |
| UC10 | Đánh giá chất lượng thiết kế | QC Officer, Hệ thống AI | Đã chạy | `quality/` (tự động trong mỗi lượt sinh); QC Officer dùng `POST /passports/{id}/qc` (chưa có giao diện web) |
| UC11 | So sánh các phiên bản | (extend UC15) | Đã chạy | Trường `versions` của `GET /passports/{id}` (chưa có giao diện web) |
| UC12 | Thẩm định chuyên gia | Chuyên gia di sản | Đã chạy | `POST /passports/{id}/reviews`; gói chấm mù `scripts/18_build_blind_review.py` (chưa có giao diện web) |
| UC13 | Phê duyệt thiết kế | QC Officer (và phiếu chuyên gia) | Đã chạy | Trạng thái `approved` trong Passport |
| UC14 | Quản lý Design Passport | Nhà thiết kế | Đã chạy | `provenance/passport.py`, `GET /passports/{id}` (chưa có giao diện web) |
| UC15 | Xem lịch sử chỉnh sửa | Người dùng đã đăng ký | Đã chạy | Trường `timeline` của `GET /passports/{id}` (chưa có giao diện web) |
| UC16 | Xuất thiết kế (gắn nhãn AI) | Nhà thiết kế | Đã chạy | `GET /passports/{id}/export`. Lưu ý: nút Tải xuống ở trang Kết quả tải ảnh chưa gắn nhãn AI |
| UC17 | Quản lý người dùng và dữ liệu | Quản trị viên | Kế hoạch | – |
| UC18 | Kiểm tra quyền sử dụng | (được include) | Đã chạy | `provenance/registry.py::rights_gate` |
| UC19 | Thử nghiệm có kiểm soát | QC Officer, Hệ thống AI | Một phần | `evaluation/experiment.py` (dòng lệnh), `GET /experiments` để xem |

Rà soát 21/11/2026: từ ngày 19/11/2026 web chỉ còn Trang chủ, Studio và trang Kết quả. Các ca của QC Officer, chuyên gia và quản lý Passport vẫn chạy thật qua API (có kiểm thử) nhưng chưa có giao diện web; cột cuối ghi rõ điều này.

UC18 và UC19 không có trong danh sách gợi ý ban đầu. Nhóm thêm vì chúng là hai việc BTC yêu cầu trực tiếp (yêu cầu 3 và yêu cầu 2) và có mã riêng.

## Quan hệ include và extend

Quy tắc dùng: **include** khi ca gốc *luôn luôn* phải chạy ca kia mới hoàn thành; **extend** khi ca mở rộng chỉ chạy *trong một điều kiện* và ca gốc vẫn hoàn chỉnh khi thiếu nó. (Giáo trình Tilley gọi include là quan hệ «uses».)

| Quan hệ | Lý do |
|---|---|
| Tải lên hiện vật «include» Kiểm tra nguồn gốc | Không hiện vật nào vào thư viện mà chưa qua C1–C4 |
| Kiểm tra nguồn gốc «include» Kiểm tra quyền sử dụng | Kiểm tra nguồn gốc luôn kết thúc bằng xác định tình trạng quyền |
| Xuất thiết kế «include» Kiểm tra quyền sử dụng | Mỗi lần xuất đều chạy cổng quyền theo mục đích (trình diễn hay xuất bản) |
| Tạo thiết kế «include» Sinh họa tiết AI | Không có thiết kế nào không có hoa văn |
| Sinh họa tiết AI «include» Phân tích họa tiết | Sinh hoa văn cần ảnh Canny và bảng màu |
| Tạo thiết kế «include» Đánh giá chất lượng thiết kế | Mọi thiết kế đều qua G2 và G3; không có đường tắt |
| Thẩm định chuyên gia «include» Quản lý Design Passport | Phiếu chấm được ghi vào Passport, đổi trạng thái phê duyệt |
| Chỉnh sửa thiết kế «extend» Tạo thiết kế | Chỉ xảy ra khi chuyên gia yêu cầu sửa hoặc nhà thiết kế muốn sửa; tạo thiết kế vẫn hoàn chỉnh khi không sửa |
| Quản lý giấy phép «extend» Kiểm tra quyền sử dụng | Chỉ khi quyền chưa xác minh hoặc có giấy phép mới cần cập nhật |
| So sánh các phiên bản «extend» Xem lịch sử chỉnh sửa | Chỉ khi thiết kế có từ hai phiên bản |
| Phê duyệt thiết kế «extend» Thẩm định chuyên gia | Chỉ khi quyết định của chuyên gia là "Đạt" |

Những nối kết **cố ý không vẽ**: Thử nghiệm có kiểm soát không include Tạo thiết kế, vì thí nghiệm dùng bộ chạy riêng (`evaluation/experiment.py`) và kết quả không đi vào danh mục sản phẩm. Nối hai ca này sẽ gợi ý sai rằng ảnh thí nghiệm có thể được xuất bản.

## Mô tả ca sử dụng (mẫu Tilley)

### UC08. Tạo thiết kế áo dài

| Mục | Nội dung |
|---|---|
| Tác nhân | Nhà thiết kế; Hệ thống xử lý AI (phụ) |
| Mô tả | Từ một hiện vật trong thư viện, hệ thống sinh 4 phương án áo dài, đo chất lượng từng phương án và tạo Design Passport cho mỗi phương án |
| Hoàn thành thành công | 1. Nhà thiết kế chọn hiện vật ở Studio (có thể mở sổ hoa văn), bấm Tạo thiết kế; không nhập seed. 2. Hệ thống xếp lượt vào hàng chờ GPU, kiểm tra quyền mục đích "thử nghiệm". 3. Hệ thống tạo thư mục lần chạy riêng. 4. Hệ thống sinh áo dài nền bằng LoRA (seed ngẫu nhiên mỗi lượt), rồi sinh hoa văn, ghép, hoàn thiện chỉ vùng áo có khoá họa tiết cho 4 phương án. 5. Hệ thống chạy G2 (lỗi thì sinh lại với seed kế tiếp, tối đa 3 lần) và G3 (lỗi thì thử lại hoàn thiện). 6. Hệ thống tạo Passport, trang Kết quả hiện 4 thiết kế |
| Thay thế | 2a. Hiện vật đã ngừng dùng hoặc quyền bị từ chối → báo lý do, không chạy. 2b. Hàng chờ đầy (3 lượt) hoặc vượt giới hạn lượt/giờ → trả 429, giao diện báo thử lại sau. 4a. Một phương án lỗi GPU → phương án đó ghi `failed`, ba phương án còn lại vẫn chạy. 4b. Máy chủ không có PyTorch/GPU → API trả 503 kèm thông báo "chưa có môi trường sinh ảnh", giao diện hiển thị kết quả đã sinh sẵn. 4c. Bản triển khai Vercel: máy GPU lỗi hoặc quá thời gian → cổng trả bộ đã sinh sẵn, trang Kết quả ghi "Kết quả đã sinh sẵn — không phải sinh trực tiếp" |
| Tiền điều kiện | Hiện vật ở trạng thái `active`; chưa vượt giới hạn 6 lần sinh/giờ/IP ở API (cổng Vercel: 10 lần/giờ/IP) |
| Hậu điều kiện | Có thư mục `outputs/runs/<mã lần chạy>/` với manifest; 4 Passport ở trạng thái do cổng đặt (không bao giờ là "đã phê duyệt") |
| Giả định | Mô hình SD 1.5 và ControlNet đã tải về máy |

### UC10. Đánh giá chất lượng thiết kế

| Mục | Nội dung |
|---|---|
| Tác nhân | Hệ thống xử lý AI; QC Officer |
| Mô tả | Đo kỹ thuật hoa văn (G2) và thiết kế cuối (G3), định tuyến thiết kế sang bước tiếp theo |
| Hoàn thành thành công | 1. Hệ thống tính VLS, tỉ lệ đường nối (G2). 2. Hệ thống căn chỉnh bản cuối với bản ghép, tính PPS, IoU dáng áo, tỉ lệ độ nét, lệch màu (G3). 3. Kết quả PASS → trạng thái "chờ chuyên gia" |
| Thay thế | 3a. WARN → "chờ QC"; QC Officer xem và chuyển chuyên gia hoặc trả về. 3b. G2 FAIL → sinh lại hoa văn với seed kế tiếp (tối đa 3 lần); vẫn FAIL → giữ bản ít lỗi nhất, ghi `qa_failed`. 3c. G3 FAIL → thử lại hoàn thiện (đổi seed, hạ độ nhiễu, cuối cùng bản ghép thô); vẫn FAIL → `qa_failed`, QC Officer chỉ được trả về sửa |
| Tiền điều kiện | Có ảnh hiện vật 512, hoa văn, bản ghép, bản cuối của cùng một lần chạy |
| Hậu điều kiện | Kết quả cổng ghi vào Passport kèm phiên bản cấu hình ngưỡng |
| Giả định | Ngưỡng đang ở trạng thái tạm thời, sẽ hiệu chỉnh theo phiếu chuyên gia |

### UC12. Thẩm định chuyên gia

| Mục | Nội dung |
|---|---|
| Tác nhân | Chuyên gia di sản |
| Mô tả | Chấm mù 5 tiêu chí theo thang 1–5 và ra quyết định duyệt, yêu cầu sửa hoặc loại |
| Hoàn thành thành công | 1. Chuyên gia mở hàng đợi, thấy ảnh hiện vật và thiết kế, không thấy mã biến thể, tham số hay điểm của máy. 2. Chấm 5 tiêu chí, chọn quyết định, ghi nhận xét. 3. Hệ thống ghi phiếu, đổi trạng thái Passport |
| Thay thế | 3a. Quyết định "Đạt" nhưng có tiêu chí < 3 hoặc "Phù hợp văn hoá" < 4 → hệ thống vẫn ghi theo quyết định của chuyên gia, đánh dấu "mâu thuẫn với quy tắc" để hội đồng xem lại. 3b. Chuyên gia không đồng ý lưu tên → chỉ lưu mã người chấm |
| Tiền điều kiện | Thiết kế ở trạng thái "chờ chuyên gia" hoặc "yêu cầu sửa" |
| Hậu điều kiện | Passport có thêm phiếu; trạng thái thành "đã phê duyệt", "yêu cầu sửa" hoặc "bị loại" |
| Giả định | Chuyên gia là người ngoài nhóm phát triển |

### UC09. Chỉnh sửa thiết kế

| Mục | Nội dung |
|---|---|
| Tác nhân | Nhà thiết kế |
| Mô tả | Ghi một lần chỉnh sửa thủ công thành phiên bản mới có truy vết |
| Hoàn thành thành công | 1. Nhà thiết kế tải ảnh đã sửa, nhập mã người sửa, công cụ, nội dung sửa. 2. Hệ thống kiểm tra ảnh, lưu, băm. 3. Hệ thống tạo phiên bản mới mang mã băm phiên bản trước. 4. Hệ thống chạy G3 trên bản sửa và đặt trạng thái theo kết quả |
| Thay thế | 2a. Tệp không phải ảnh hoặc quá 8 MB → từ chối. 4a. Không đủ dữ liệu để chạy G3 → trạng thái "chờ QC" |
| Tiền điều kiện | Passport tồn tại |
| Hậu điều kiện | Phiên bản cũ giữ nguyên; sổ cái có sự kiện "chỉnh sửa thủ công" |
| Giả định | Nhà thiết kế khai báo trung thực nội dung sửa (hệ thống chỉ chứng minh được *tệp* đã đổi) |

### UC16. Xuất thiết kế (gắn nhãn AI)

| Mục | Nội dung |
|---|---|
| Tác nhân | Nhà thiết kế |
| Mô tả | Tải xuống ảnh thiết kế kèm nhãn "Thiết kế hỗ trợ bởi AI" và mã Passport |
| Hoàn thành thành công | 1. Chọn phiên bản. 2. Hệ thống chạy cổng quyền mục đích "trình diễn". 3. Hệ thống thêm dải nhãn nhìn thấy được và siêu dữ liệu PNG (mã Passport, SHA-256, ghi công nguồn ảnh). 4. Trả tệp PNG |
| Thay thế | 2a. Quyền chưa xác minh → vẫn cho tải, nhãn ghi thêm "Ảnh nguồn chưa xác minh quyền — không dùng thương mại" |
| Tiền điều kiện | Passport có ít nhất một phiên bản |
| Hậu điều kiện | Nhật ký audit có sự kiện "design_exported" |
| Giả định | Người nhận tệp không cắt bỏ dải nhãn (siêu dữ liệu PNG vẫn còn khi dải nhãn bị cắt) |
