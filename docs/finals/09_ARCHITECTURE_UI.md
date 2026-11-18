# 09. Kiến trúc module và giao diện

## Kiến trúc

Giữ nguyên lựa chọn công nghệ của bản 09/2026: Python + FastAPI, pipeline Diffusers, giao diện HTML/CSS/JS tĩnh, dữ liệu dạng tệp JSON/CSV (không cơ sở dữ liệu). Phần mới là ba gói Python và một bộ chạy thí nghiệm.

```
generation/         (có sẵn) sinh hoa văn, ghép áo, img2img — chạy trên GPU
  streamlit_runner  viết lại: mỗi lần chạy một thư mục riêng, gọi cổng quyền, chất lượng, Passport
quality/            (mới) metrics.py · gate.py · repair.py · assess.py — chỉ cần CPU
provenance/         (mới) registry.py · passport.py · builder.py · labeling.py · hashing.py
evaluation/
  experiment.py     (mới) kế hoạch, kiểm tra đơn biến, chạy, chấm mù, thống kê
  experiments/*.json  đặc tả EXP-A, EXP-B, EXP-C
api/                main.py (v1.1.0) · store.py · audit.py
config/             heritage_selection.json · quality_gate.json · expert_rubric.json
web_ui/             giao diện chung kết (giao diện 09/2026 lưu ở archive/web_ui_2026-09/)
scripts/            08 chuyển schema · 09 nạp ảnh hiện vật · 10 dựng lại 24 thiết kế · 11 xuất dữ liệu trình diễn · 12 dựng sơ đồ
tests/              130 ca pytest
```

Luồng dữ liệu một lần chạy:

```
POST /generate ─► cổng quyền (thử nghiệm) ─► outputs/runs/R<thời điểm>-<mã>/
                     │                         00_reference · 01_canny · V1..V4_pattern · _aodai_raw · _aodai
                     ▼
               quality/assess (G2, G3, khoá họa tiết nếu cần)
                     ▼
               provenance/builder ─► outputs/passports/DP-<mã>-<ngày>-V<i>.json (sổ cái băm)
                     ▼
               manifest.json (SHA-256 từng tệp) ─► kết quả job: trạng thái từng phương án
```

### Khả năng mở rộng

- Ngưỡng cổng, tiêu chí tuyển ảnh, bộ tiêu chí chuyên gia đều là tệp cấu hình có phiên bản; đổi ngưỡng không cần sửa mã và Passport cũ vẫn ghi phiên bản đã dùng.
- Thêm thí nghiệm mới = thêm một tệp JSON; bộ kiểm tra đơn biến áp dụng tự động.
- Thêm hiện vật = thêm một mục trong danh mục; cổng C1–C4 và cổng quyền áp dụng tự động.
- Lưu trữ đi qua `api/store.py` (ghi tệp tạm rồi đổi tên, có khoá luồng). Khi cần nhiều người dùng đồng thời, thay lớp này bằng cơ sở dữ liệu mà không đổi API.
- Giới hạn hiện tại: một tiến trình API, một GPU, job giữ trong bộ nhớ (khởi động lại mất trạng thái job đang chạy, không mất Passport đã ghi).

### API

Endpoint cũ giữ nguyên đường dẫn và các trường trả về (có ca kiểm thử hồi quy). `/heritage` mặc định chỉ trả hiện vật đang dùng; thêm `?include_retired=true` để xem cả hiện vật ngừng dùng.

| Nhóm | Endpoint |
|---|---|
| Có từ bản cũ | `GET /health`, `GET /heritage`, `GET /heritage/{id}`, `GET /media/heritage/{id}`, `POST /generate`, `GET /generate/{job}`, `POST /audit`, `GET /media/variant/{tệp}` |
| Nguồn gốc | `GET /heritage/{id}/provenance`, `GET /provenance/catalog` |
| Lần chạy | `GET /runs`, `GET /runs/{id}`, `GET /media/run/{id}/{tệp}`, `GET /media/artifact?path=` (chỉ trong `outputs/`, `data/heritage/`, `web_ui/assets/images/`) |
| Passport | `GET /passports`, `GET /passports/{id}` (kèm dòng thời gian, kết quả kiểm tra toàn vẹn), `GET /passports/{id}/export` |
| Ghi (cần `X-API-Key` khi đặt `TSDS_WRITE_KEY`) | `POST /passports/{id}/qc`, `/reviews`, `/edits`, `/publish` |
| Chất lượng, thí nghiệm | `GET /quality/legacy`, `GET /experiments` |

Bảo vệ: giới hạn 6 lần sinh/giờ/IP (`TSDS_GENERATE_PER_HOUR`), danh sách sự kiện audit được phép, kiểm tra mã định danh bằng biểu thức chính quy, chặn đường dẫn ra ngoài thư mục cho phép, ảnh chỉnh sửa ≤ 8 MB và phải là ảnh hợp lệ. Khi máy chủ không có PyTorch/GPU, `/generate` trả 503 với thông báo rõ thay vì lỗi 500.

## Giao diện

### Hướng thiết kế

Bối cảnh là một xưởng thiết kế làm việc với hiện vật gốm, không phải trang quản trị dữ liệu. Nền màu giấy dó (`#F4F0E6`) và men trắng (`#FCFBF7`); ba màu nhấn lấy từ gốm Bát Tràng: **lam** men cobalt (`#24508A`) cho hành động chính, **ngọc** (`#2E7A64`) cho "đạt", **nâu đất** (`#8B5E3C`) cho chi tiết phụ. Màu cảnh báo và không đạt dùng riêng (`#8A6400`, `#A3392B`), luôn đi kèm biểu tượng và chữ, không truyền nghĩa bằng màu đơn thuần. Kiểu chữ (cập nhật 18/11/2026) tham khảo cách các trang di sản lớn trình bày (đo trực tiếp trên trang): The Met dùng chữ có chân nét thanh-đậm, độ đậm thường cho tiêu đề lớn và chữ không chân cho phần còn lại; British Museum và V&A để chữ thân 16–17px, khoảng dòng 1,5–1,65; Rijksmuseum dùng nhãn nhỏ viết hoa giãn chữ. Áp dụng: tiêu đề trang, tiêu đề mục, số liệu lớn và mã Passport dùng **Noto Serif Display** (500); tên hiện vật dùng **Literata** (500); nội dung và điều khiển dùng **Be Vietnam Pro**, chữ thân 16px / 1,6; nhãn nhóm menu viết hoa 11px giãn 0,09em. Phân cấp bằng cỡ chữ, không bằng độ đậm. Cả ba font đều có bộ dấu tiếng Việt; khoảng dòng tiêu đề ≥ 1,2 để dấu chồng (Ầ, Ữ) không bị cắt.

Điểm nhấn duy nhất là **chuỗi truy vết**: một dải ngang hiện vật → Canny → hoa văn → bản ghép → bản cuối → bản sửa, mỗi mắt xích có mã băm rút gọn. Dải này xuất hiện ở Studio và Design Passport, trả lời trực tiếp câu hỏi "thiết kế này đi từ đâu" của BTC.

### Bố cục "triển lãm số" và chuyển động (bản 3, 18/11/2026)

Lấy cảm hứng từ cách các nền tảng di sản trực tuyến kể chuyện (ảnh bìa tràn màn hình, chương đánh số, băng thẻ ảnh cuộn ngang), không sao chép giao diện hay thương hiệu của nền tảng nào. Khung trang ở `web_ui/assets/css/exhibit.css`, chuyển động ở `web_ui/assets/js/lib/motion.js`, ảnh bìa ở `web_ui/assets/js/lib/hero.js`.

| Thành phần | Mô tả |
|---|---|
| Điều hướng trên cùng | Trong suốt trên ảnh bìa, chuyển nền giấy mờ khi cuộn; 5 khu vực chính + nút "Danh mục" |
| Menu toàn màn hình | 4 chương đánh số 01–04 (Sáng tạo, Kiểm soát, Truy vết, Quản trị), mở bằng hiệu ứng vòng tròn lan, các chương trồi lên so le; Esc để đóng; chứa nhãn chế độ và nguồn dữ liệu |
| Ảnh bìa Thư viện | Nền lam cobalt có vân vòng tròn xoay chậm; "quạt thẻ" Hiện vật → Hoa văn → Áo dài tự chuyển giữa các hiện vật đang dùng, nghiêng theo chuột; chú thích dẫn tới Passport kèm trạng thái phê duyệt thật |
| Ảnh bìa các khu vực khác | Số chương lớn viền mảnh, băng ảnh thiết kế trôi chậm phía sau (có dòng ghi "thiết kế có hỗ trợ AI"); Studio hiện hiện vật tách nền lơ lửng; Passport chi tiết hiện bản thiết kế mới nhất |
| Thư viện | Hành trình 5 chặng (thẻ ảnh đánh số), băng thẻ hiện vật trên bệ, dải trích dẫn nguyên tắc cổng chất lượng, thẻ tiêu chí C1–C4 |
| Chuyển động chung | Tiêu đề trồi lên từng từ; khối nội dung hiện dần khi cuộn; số liệu đếm lên tới giá trị thật; thanh tỉ lệ và biểu đồ mọc dần; sợi chỉ lam báo tiến độ cuộn; ngăn kéo trượt vào |

Nguyên tắc: chỉ dùng `transform`/`opacity`; khi hệ điều hành bật giảm chuyển động (`prefers-reduced-motion`) thì mọi hiệu ứng tắt và nội dung hiện ngay. Số đếm chỉ là hiệu ứng hiển thị — giá trị cuối luôn là số liệu thật. Mọi ảnh do AI hỗ trợ tạo đều mang nhãn "AI hỗ trợ tạo".

### Chín khu vực

| Nhóm | Khu vực | Việc chính | Trạng thái đặc biệt |
|---|---|---|---|
| Sáng tạo | Thư viện di sản | Xem hiện vật, nguồn, quyền, kết quả C1–C4; lọc đang dùng / ngừng dùng | Hiện vật ngừng dùng hiện lý do |
| | Studio thiết kế | Chọn hiện vật, nhập seed, sinh 4 phương án, xem cổng chất lượng của từng phương án | Không có GPU → nút sinh bị khoá kèm lý do; đang chạy → thanh tiến độ; lỗi → thông báo cụ thể |
| Kiểm soát | Kiểm định chất lượng | Phân bố PASS/WARN/FAIL, PPS trước và sau sửa, bảng ngưỡng, chi tiết 24 thiết kế | |
| | Phòng thử nghiệm | Ba thí nghiệm, kế hoạch, kết quả EXP-C kèm ảnh; so sánh hai cấu hình và cảnh báo khi khác nhau nhiều hơn một tham số | Thí nghiệm chưa chạy hiện "chờ GPU" |
| | Thẩm định chuyên gia | Hàng đợi chờ chuyên gia / chờ QC / đã quyết định; phiếu chấm mù 5 tiêu chí | Chấm mù: ẩn mã Passport (mã chứa số biến thể), xếp theo mã ẩn danh |
| Truy vết | Design Passport | Toàn vẹn, chuỗi truy vết, "ai làm gì", tham số, phiên bản, chỉnh sửa, cổng, phiếu, quyền, dòng thời gian | Kiểm tra toàn vẹn không đạt → báo đỏ kèm danh sách lỗi |
| | Nguồn và bản quyền | Danh mục 10 trường (ô thiếu tô đỏ), thư xin phép tạo sẵn, bảng quy tắc quyền | |
| Quản trị | Tổng quan | Chỉ số và bảng KPI có mã khớp [08_KPI.md](08_KPI.md) | Ô chưa đo hiện "Mục tiêu cần đo" |
| | Quy trình nghiệp vụ | BPMN TO-BE, AS-IS, Use Case; xem cỡ thật hoặc thu vừa khung | |

### Hai chế độ

- **Trực tiếp**: có API chạy cùng máy (`localhost`) → đọc và ghi qua API. Nhãn góc phải cho biết có GPU hay không.
- **Trình diễn**: không có API (ví dụ bản đưa lên Vercel) → đọc dữ liệu đã xuất trong `web_ui/data/` bằng `scripts/11_export_demo_data.py` từ dữ liệu thật. Các nút ghi (phiếu thẩm định, quyết định QC) không giả vờ ghi: chúng xuất tệp JSON để nhóm nhập sau, và giao diện nói rõ điều đó.

Không có nút nào bấm mà không làm gì. Chức năng chưa có máy chủ (sinh ảnh, ghi chỉnh sửa) hiện lý do bị khoá.

### Chất lượng giao diện

- Không dùng `innerHTML` với dữ liệu; mọi phần tử tạo bằng hàm `h()` (có ca kiểm thử).
- Bàn phím: điều hướng bằng liên kết, nút chấm điểm là `role="radio"`; nền tảng tôn trọng `prefers-reduced-motion`.
- Responsive: dưới 980 px chỉ còn nút "Danh mục"; đã kiểm tra không tràn ngang ở bề rộng 375 px trên cả 9 khu vực (bản 3).
- Ảnh trình diễn nén WebP; mã băm trong Passport tính trên tệp PNG gốc.

## Chạy

```bash
pip install -r requirements.txt            # máy có GPU: đủ để sinh ảnh
uvicorn api.main:app --port 8000           # API
python -m http.server 5500                 # mở http://localhost:5500/web_ui/
python scripts/11_export_demo_data.py      # cập nhật dữ liệu cho chế độ trình diễn
pip install -r requirements-dev.txt && pytest   # kiểm thử, không cần GPU
```
