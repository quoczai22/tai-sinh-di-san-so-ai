# 09. Kiến trúc module và giao diện

## Kiến trúc

Giữ nguyên lựa chọn công nghệ của bản 09/2026: Python + FastAPI, pipeline Diffusers, giao diện HTML/CSS/JS tĩnh, dữ liệu dạng tệp JSON/CSV (không cơ sở dữ liệu). Phần mới là ba gói Python và một bộ chạy thí nghiệm.

```
generation/         sinh hoa văn, sinh áo dài nền bằng LoRA, tách vùng áo bằng SAM, ghép áo, polish, khoá họa tiết (chạy trên GPU)
  streamlit_runner  viết lại: mỗi lần chạy một thư mục riêng, gọi cổng quyền, chất lượng, Passport
quality/            (mới) metrics.py · gate.py · repair.py · assess.py — chỉ cần CPU
provenance/         (mới) registry.py · passport.py · builder.py · labeling.py · hashing.py
evaluation/
  experiment.py     (mới) kế hoạch, kiểm tra đơn biến, chạy, chấm mù, thống kê
  experiments/*.json  đặc tả EXP-A đến EXP-G
api/                main.py (v1.1.0) · store.py · audit.py
config/             heritage_selection.json · quality_gate.json · expert_rubric.json
web_ui/             giao diện cho người xem: Trang chủ, Studio, Kết quả (giao diện 09/2026 lưu ở archive/web_ui_2026-09/)
scripts/            08 chuyển schema, trích LR3D · 09 nạp ảnh hiện vật · 10 tạo hiện vật từ LR3D · 11 xuất dữ liệu trình diễn, lọc VietFashion · 12 dựng sơ đồ, xuất tập LoRA · 13 huấn luyện LoRA · 14 sinh bộ demo
tests/              322 ca pytest
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
| Có từ bản cũ | `GET /health`, `GET /heritage`, `GET /heritage/{id}`, `GET /media/heritage/{id}` (trả ảnh đã tách nền trong `data/heritage/cutouts/` nếu có), `POST /generate`, `GET /generate/{job}`, `POST /audit`, `GET /media/variant/{tệp}` |
| Nguồn gốc | `GET /heritage/{id}/provenance`, `GET /provenance/catalog` |
| Lần chạy | `GET /runs`, `GET /runs/{id}`, `GET /media/run/{id}/{tệp}`, `GET /media/artifact?path=` (chỉ trong `outputs/`, `data/heritage/`, `web_ui/assets/images/`) |
| Passport | `GET /passports`, `GET /passports/{id}` (kèm dòng thời gian, kết quả kiểm tra toàn vẹn), `GET /passports/{id}/export` |
| Ghi (cần `X-API-Key` khi đặt `TSDS_WRITE_KEY`) | `POST /passports/{id}/qc`, `/reviews`, `/edits`, `/publish` |
| Chất lượng, thí nghiệm | `GET /quality/designs`, `GET /experiments` |

Bảo vệ: giới hạn 6 lần sinh/giờ/IP (`TSDS_GENERATE_PER_HOUR`), danh sách sự kiện audit được phép, kiểm tra mã định danh bằng biểu thức chính quy, chặn đường dẫn ra ngoài thư mục cho phép, ảnh chỉnh sửa ≤ 8 MB và phải là ảnh hợp lệ. Khi máy chủ không có PyTorch/GPU, `/generate` trả 503 với thông báo rõ thay vì lỗi 500.

## Giao diện

### Hướng thiết kế

Bối cảnh là một xưởng thiết kế làm việc với hiện vật gốm, không phải trang quản trị dữ liệu. Nền màu giấy dó (`#F4F0E6`) và men trắng (`#FCFBF7`); ba màu nhấn lấy từ gốm Bát Tràng: **lam** men cobalt (`#24508A`) cho hành động chính, **ngọc** (`#2E7A64`) cho "đạt", **nâu đất** (`#8B5E3C`) cho chi tiết phụ. Màu cảnh báo và không đạt dùng riêng (`#8A6400`, `#A3392B`), luôn đi kèm biểu tượng và chữ, không truyền nghĩa bằng màu đơn thuần. Kiểu chữ (cập nhật 18/11/2026) tham khảo cách các trang di sản lớn trình bày (đo trực tiếp trên trang): The Met dùng chữ có chân nét thanh-đậm, độ đậm thường cho tiêu đề lớn và chữ không chân cho phần còn lại; British Museum và V&A để chữ thân 16–17px, khoảng dòng 1,5–1,65; Rijksmuseum dùng nhãn nhỏ viết hoa giãn chữ. Áp dụng: tiêu đề trang, tiêu đề mục, số liệu lớn và mã Passport dùng **Noto Serif Display** (500); tên hiện vật dùng **Literata** (500); nội dung và điều khiển dùng **Be Vietnam Pro**, chữ thân 16px / 1,6; nhãn nhóm menu viết hoa 11px giãn 0,09em. Phân cấp bằng cỡ chữ, không bằng độ đậm. Cả ba font đều có bộ dấu tiếng Việt; khoảng dòng tiêu đề ≥ 1,2 để dấu chồng (Ầ, Ữ) không bị cắt.

Điểm nhấn duy nhất là **chuỗi truy vết**: một dải ngang hiện vật → Canny → hoa văn → bản ghép → bản cuối → bản sửa, mỗi mắt xích có mã băm rút gọn. Dải này xuất hiện ở Studio và Design Passport, trả lời trực tiếp câu hỏi "thiết kế này đi từ đâu" của BTC.

### Bố cục "triển lãm số" và chuyển động (bản 3, 18/11/2026)

Lấy cảm hứng từ cách các nền tảng di sản trực tuyến kể chuyện (ảnh bìa tràn màn hình, chương đánh số, băng thẻ ảnh cuộn ngang), không sao chép giao diện hay thương hiệu của nền tảng nào. Khung trang ở `web_ui/assets/css/exhibit.css`, chuyển động ở `web_ui/assets/js/lib/motion.js`, ảnh bìa ở `web_ui/assets/js/lib/hero.js`.

| Thành phần | Mô tả |
|---|---|
| Điều hướng | Logo hoa sen ở giữa; trái: Trang chủ, Studio; phải: nút menu ☰ (menu có Trang chủ và Studio; trang Kết quả chỉ vào qua nút Tạo thiết kế) |
| Trang chủ | Ảnh bìa với quạt thẻ Hiện vật → Hoa văn → Áo dài; chim phượng và câu mở đầu; Hành trình 3 chặng; lưới hiện vật; lưới áo dài; mặt trống đồng và lời kết |
| Studio | Chọn hiện vật (Đầu vào) rồi nút Tạo thiết kế; tạo xong tự chuyển sang trang Kết quả. Có GPU: sinh thật kèm tiến độ. Không có GPU: mở bộ đã tạo trước trên GPU (từ 20/11/2026 giao diện không còn dòng ghi chú ngày tạo, nên báo cáo phải nêu rõ đây là bộ có sẵn khi chạy ngoại tuyến), không giả lập việc sinh |
| Kết quả (`#/result/<mã hiện vật>`) | Bốn tà áo của bộ thiết kế mới nhất của hiện vật, nhãn AI; nút Tạo lại và Chọn hiện vật khác. Không có khung chi tiết hay chỉ số kỹ thuật |
| Chuyển động | Theo vị trí cuộn (chim phượng, câu mở đầu sáng dần, hiện vật nổi lên); chỉ chuyển động tự chạy dừng khi hệ điều hành bật giảm chuyển động; có nút tắt chuyển động trong menu |

### Phạm vi giao diện web (19/11/2026)

Web chỉ dành cho người xem: **Trang chủ · Studio · Kết quả**. Các chức năng nghiệp vụ không còn là trang web mà nằm ở:

| Chức năng | Nằm ở |
|---|---|
| Kiểm định chất lượng G2/G3 | `quality/`, `config/quality_gate.json`, `GET /quality/designs` |
| Thí nghiệm EXP-A đến EXP-G | `evaluation/experiment.py`, `evaluation/exp_g.py`, `outputs/experiments/`, `GET /experiments` |
| Thẩm định chuyên gia | `config/expert_rubric.json`, `POST /passports/{id}/reviews`, gói chấm mù nhiều seed `outputs/blind_review/` (`scripts/18_build_blind_review.py`) |
| Design Passport | `outputs/passports/`, `GET /passports/{id}`, `GET /passports/{id}/export` |
| Nguồn và bản quyền | `data/heritage/metadata.json`, `GET /provenance/catalog`, [07](07_PROVENANCE_COPYRIGHT.md) |
| KPI, BPMN, Use Case | [08](08_KPI.md), [03](03_BPMN.md), [04](04_USE_CASE.md), `docs/finals/diagrams/` |

### Hai chế độ

- **Trực tiếp**: có API chạy cùng máy (`localhost`) → đọc và ghi qua API. Nhãn góc phải cho biết có GPU hay không.
- **Trình diễn**: không có API (ví dụ bản đưa lên Vercel) → đọc dữ liệu đã xuất trong `web_ui/data/` bằng `scripts/11_export_demo_data.py` từ dữ liệu thật. Riêng trang Kết quả đọc bộ riêng `web_ui/data/result/` và `web_ui/assets/images/result/` (xuất bằng `--only-result`, qua `data.resultPassports()`), nên bộ demo seed 42 mới chỉ đổi ở trang này; trang chủ, Thư viện, Studio và bảng chất lượng giữ dữ liệu cũ. Chạy lệnh không có cờ sẽ ghi lại toàn bộ `web_ui/data/`. Các nút ghi (phiếu thẩm định, quyết định QC) không giả vờ ghi: chúng xuất tệp JSON để nhóm nhập sau, và giao diện nói rõ điều đó.

Không có nút nào bấm mà không làm gì. Chức năng chưa có máy chủ (sinh ảnh, ghi chỉnh sửa) hiện lý do bị khoá.

### Chất lượng giao diện

- Không dùng `innerHTML` với dữ liệu; mọi phần tử tạo bằng hàm `h()` (có ca kiểm thử).
- Bàn phím: điều hướng bằng liên kết, nút chấm điểm là `role="radio"`; nền tảng tôn trọng `prefers-reduced-motion`.
- Responsive: dưới 980 px chỉ còn nút menu; đã kiểm tra không tràn ngang ở bề rộng 390 px.
- Ảnh trình diễn nén WebP; mã băm trong Passport tính trên tệp PNG gốc.

## Chạy

```bash
pip install -r requirements.txt            # máy có GPU: đủ để sinh ảnh
uvicorn api.main:app --port 8000           # API
python -m http.server 5500                 # mở http://localhost:5500/web_ui/
python scripts/11_export_demo_data.py      # cập nhật dữ liệu cho chế độ trình diễn
pip install -r requirements-dev.txt && pytest   # kiểm thử, không cần GPU
```

## Khung xem 3D (trang Studio của từng hiện vật)

- `web_ui/assets/js/lib/viewer3d.js` dựng khung xoay 3D bằng Three.js (bản chép sẵn trong `assets/js/vendor/three/`, giấy phép MIT, nạp qua importmap trong `index.html`). Thư viện chỉ tải khi mở trang Studio của một hiện vật.
- Mô hình là `assets/models/<mã hiện vật>.glb`, tạo bằng `scripts/16_export_heritage_glb.py` từ mô hình gốc trong `data/lr3d_src/` (thư mục này bị `.gitignore`).
- Thao tác: kéo chuột để xoay, lăn chuột để thu phóng, tự xoay nhẹ và dừng khi đang kéo. Nền canvas trong suốt nên khung nền be của trang hiện phía sau.
- Thẻ trong lưới (Thư viện và lưới chọn của Studio): `hoverSpin()` dựng bình 3D đứng yên khi thẻ sắp vào màn hình (trong lúc chờ vẫn hiện ảnh phẳng). Bình tự xoay cùng tốc độ như trang riêng khi rê chuột hoặc focus bàn phím vào thẻ, rê ra thì dừng vòng vẽ và canvas giữ nguyên góc đang xoay. Thẻ không kéo xoay được để bấm vào vẫn mở Studio. Bật "giảm chuyển động" thì bình vẫn hiện 3D nhưng không xoay khi rê chuột.
- Dự phòng: không có WebGL hoặc không có file GLB thì giữ ảnh phẳng đã tách nền. Ảnh bìa, thẻ Hành trình và trang Kết quả không dùng 3D.

## Trang Kết quả: cửa sổ xem và tải thiết kế

- Bấm vào một trong 4 ảnh (hoặc Enter, phím cách khi đang chọn ảnh) thì mở cửa sổ phóng to ảnh đó, có nhãn AI.
- Phóng to thu nhỏ từ 100% đến 400%: kéo thanh trượt dưới ảnh, bấm nút − hoặc + ở hai đầu thanh (mỗi lần 25%), hoặc lăn chuột trên ảnh (phóng về phía con trỏ, nhanh hơn thanh trượt). Bấm đúp để phóng 2 lần, bấm đúp lần nữa để về 100%. Khi đã phóng thì kéo chuột để xê dịch ảnh, ảnh không rời khỏi khung. Thanh trượt cũng dùng được bằng bàn phím.
- Nút TẢI XUỐNG (vàng, có biểu tượng tải bên trái) lấy ảnh dạng blob rồi lưu về máy với tên `thiet-ke-<mã hiện vật>-<số thứ tự>`. File tải về luôn là PNG (hoặc JPEG), không bao giờ là WebP. Chế độ trực tiếp: bản PNG gốc từ máy chủ. Chế độ trình diễn: bản PNG gốc do `scripts/11_export_demo_data.py` chép vào `web_ui/assets/images/variants/`. Nếu chỉ có bản WebP (thiết kế đã được hệ thống sửa) thì trình duyệt đổi sang PNG trước khi lưu. Nếu trình duyệt không cho lấy ảnh thì mở ảnh ở thẻ mới để lưu tay.
- Nút QUAY LẠI (viền) và dấu X ở góc trên bên phải đều đóng cửa sổ và trở về 4 mẫu. Esc và bấm ra ngoài cũng đóng. Tiêu điểm bàn phím nằm trong cửa sổ khi mở và trở về ảnh đã bấm khi đóng.

