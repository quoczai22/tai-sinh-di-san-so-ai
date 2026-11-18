# 07. Nguồn gốc, bản quyền và truy vết khi biên tập

Trả lời yêu cầu cải tiến 3 của BTC: **nguồn và giấy phép của các hiện vật, ghi công, lịch sử biên tập thủ công, nhãn "có hỗ trợ AI"**.

Nói thẳng hiện trạng: **chưa hiện vật nào đang dùng có quyền sử dụng đã được xác minh**. Cả 6 ảnh ban đầu lấy từ website bán gốm. Phần việc của bản chung kết là (1) ghi đầy đủ và trung thực những gì đã biết, (2) để hệ thống tự chặn những mục đích chưa được phép, (3) chuẩn bị thay ảnh bằng nguồn có giấy phép rõ, (4) truy vết mọi thay đổi trên thiết kế.

## 1. Danh mục nguồn (schema 2.0)

Tệp `data/heritage/metadata.json`. Bản cũ (schema 1) lưu ở `data/archive/2026-09_schema1/`, chuyển đổi bằng `scripts/08_migrate_heritage_metadata_v2.py`.

Mười trường nguồn gốc bắt buộc (`provenance/registry.py::REQUIRED_PROVENANCE`): tên hiện vật, nguồn, URL, đơn vị lưu giữ hoặc đăng ảnh, tác giả ảnh, tình trạng quyền, giấy phép, cách ghi công, ngày thu thập, phiên bản dữ liệu gốc (mã băm ảnh gốc). Hệ thống **không tự điền** trường nào nhóm không biết; trường thiếu hiện màu đỏ ở khu vực "Nguồn và bản quyền".

| Mã | Hiện vật | Trạng thái | Đơn vị đăng ảnh | Quyền | Trường còn thiếu |
|---|---|---|---|---|---|
| HV01 | Bình gốm dáng tỏi hút lộc | Đang dùng | fullhome-decor.com | Chưa xác minh | Tác giả, giấy phép, ngày thu thập |
| HV02 | Bình gốm hoa sen mực đen | Ngừng dùng | fullhome-decor.com | Chưa xác minh | như trên |
| HV03 | Bình gốm chim công phong thuỷ | Đang dùng | fullhome-decor.com | Chưa xác minh | như trên |
| HV04 | Bình gốm thuyền buồm | Đang dùng | fullhome-decor.com | Chưa xác minh | như trên |
| HV05 | Bình gốm cúc vạn thọ | Ngừng dùng | battrangceramica.com.vn | Chưa xác minh | như trên |
| HV06 | Bình hoa sứ trắng sen dát vàng 24k | Ngừng dùng | xuonggomsuviet.vn | Chưa xác minh | như trên |

Ngày thu thập không còn biết chính xác; danh mục ghi "trước 06/09/2026" (ngày lần chạy đầu tiên) thay vì bịa một ngày.

Mô tả hiện vật: HV02 có đoạn mô tả trùng 121/121 cụm 8 từ với văn bản trang nguồn, nên được đánh dấu là **trích từ trang nguồn** (`description_origin: source_page_text`) và chỉ hiển thị kèm ghi nguồn. Phần tóm tắt thị giác mới do nhóm viết và được đánh dấu "Claude hỗ trợ soạn câu chữ, bản nháp cần nhóm rà soát".

Cờ rà soát đang mở: HV01 được mô tả cho mô hình là "peacock" (chim công) trong khi đường dẫn nguồn ghi "bach-hac" (bạch hạc). Cờ này chờ chuyên gia xác nhận; nếu là hạc, tạo phiên bản prompt mới và chạy lại thí nghiệm, không sửa đè bản cũ.

## 2. Tiêu chí tuyển ảnh và kết quả rà soát 6 ảnh

Tệp `config/heritage_selection.json` (HS-2.0), chạy bằng `provenance/registry.py::assess_selection`.

| Tiêu chí | Quy tắc | Loại |
|---|---|---|
| C1. Độ phân giải | Cạnh ngắn ảnh gốc ≥ 512 px **và** cạnh dài vùng hiện vật ≥ 512 px (cảnh báo nếu < 768), để không phải phóng to khi đưa về 512×512 | Bắt buộc |
| C2. Mật độ nét hoa văn | Số pixel cạnh Canny ≥ 60% mốc 20.092 px của HV01, tức ≥ 12.055 px | Bắt buộc |
| C3. Quyền | Có URL, đơn vị đăng ảnh, tình trạng quyền; chỉ phạm vi công cộng, giấy phép mở, đã được cấp phép, hoặc ảnh tự chụp mới được xuất bản | Bắt buộc |
| C4. Tính di sản | Ưu tiên hiện vật do bảo tàng lưu giữ, có niên đại công bố; sản phẩm thương mại đương đại chỉ dùng khi có phép của cơ sở sản xuất | Khuyến nghị |

| Mã | Ảnh gốc | Vùng hiện vật | C1 | Nét (C2) | C2 | Kết luận |
|---|---|---|---|---|---|---|
| HV01 | 1746×1746 | 1344×1546 | Đạt | 20.092 | Đạt | Giữ |
| HV02 | 300×300 | 138×242 | **Không đạt** (phải phóng to ×1,98) | 15.525 | Đạt | **Ngừng dùng** |
| HV03 | 600×600 | 313×527 | Cảnh báo (< 768) | 31.000 | Đạt | Giữ, ưu tiên thay khi có ảnh tốt hơn |
| HV04 | 1191×1191 | 519×1074 | Đạt | 23.838 | Đạt | Giữ |
| HV05 | 324×617, JPEG 32 KB | 311×599 | **Không đạt** (cạnh ngắn < 512) | 14.915 | Đạt | **Ngừng dùng** |
| HV06 | 1024×1024 | 721×886 | Đạt | 14.479 (thấp nhất) | Đạt | **Ngừng dùng** vì C4: sản phẩm thương mại đương đại của xưởng, rủi ro quyền tác giả cao; hoa văn V1, V2 ra mảnh thân bình |

Cả 6 ảnh đều ở mức cảnh báo C3 (quyền chưa xác minh) và C4 (đơn vị đăng ảnh là cửa hàng). "Ngừng dùng" nghĩa là không chạy sản phẩm mới, không hiển thị như hiện vật đang có; ảnh và 12 thiết kế cũ của 3 hiện vật này **vẫn được giữ** làm minh chứng.

### Ảnh thay thế

Ứng viên tra cứu ngày 18/11/2026 qua API của Wikimedia Commons, lưu ở `data/heritage/sources/commons_candidates_2026-11-18.json`. Tất cả là ảnh hiện vật Bát Tràng trưng bày tại bảo tàng ở Hà Nội, do Daderot chụp và phát hành **CC0 1.0**; hiện vật thời Nguyễn (thế kỷ 19) đủ cũ để thuộc phạm vi công cộng. Mỗi ứng viên có mã SHA-1 do Commons công bố để kiểm tra tệp tải về.

| Ứng viên | Hiện vật | Bảo tàng | Kích thước | Dự kiến thay |
|---|---|---|---|---|
| DSC05640 | Chum vẽ sơn thuỷ và linh vật, thời Gia Long | Bảo tàng Lịch sử Quốc gia | 3648×5472 | HV02 |
| DSC05328 | Bình vẽ tích "Ngư ông đắc lợi", thế kỷ 19 | Bảo tàng Mỹ thuật Việt Nam | 3509×5000 | HV05 |
| DSC05637 hoặc DSC05641 | Chậu hoa lam / hiện vật hoa lam thời Gia Long | Bảo tàng Lịch sử Quốc gia | 3558×3519 / 3562×4055 | HV06 |

Trạng thái: **chưa nạp vào thư viện**. Máy dựng bản này không tải được tệp từ Commons (mạng bị chặn), nên cần nhóm tải 4 tệp và chạy công cụ nạp `scripts/09_ingest_heritage_image.py`:

1. Kiểm SHA-1 tệp khớp mã Commons công bố; sai là dừng.
2. Lưu bản gốc vào `data/heritage/sources/originals/` (không commit).
3. Tách nền (GrabCut + mô hình nền khớp theo viền ảnh), cắt sát, thu về cạnh dài ≤ 1.600 px, lưu PNG trong suốt; ghi mọi bước biến đổi và mã băm bản gốc, bản dẫn xuất vào `derived_from`.
4. Xuất ảnh xem trước mặt nạ tách nền vào `docs/evidence/ingest/` để người kiểm tra.
5. Chạy C1–C4; không đạt C1/C2 thì không nạp.
6. Ghi danh mục ở trạng thái `pending_ingest` với `holder_type: museum`, `rights_status: public_domain`, ghi công "Ảnh: Daderot / Wikimedia Commons, CC0 1.0. Hiện vật: <tên bảo tàng>".
7. Chỉ chuyển sang `active` (`--activate`) khi đã có mô tả prompt do nhóm viết, tóm tắt thị giác, và mọi cờ rà soát đã đóng. Sau đó chạy pipeline trên máy GPU.

```bash
python scripts/09_ingest_heritage_image.py --file TSDS_DSC05640.jpg --candidate DSC05640 \
    --heritage-id BT_Chum_GiaLong --name "Chum vẽ sơn thuỷ và linh vật" \
    --dating "Thời Nguyễn, niên hiệu Gia Long (1802–1819)" --replaces HSBT_XP-300x300 --dry-run
```

## 3. Cổng quyền theo mục đích sử dụng

`provenance/registry.py::rights_gate`. Cổng được gọi trong mã, không phải hướng dẫn trên giấy.

| Mục đích | Chưa xác minh | Đã gửi đề nghị | Đã cấp phép / giấy phép mở / CC0 / tự chụp | Bị từ chối | Hiện vật ngừng dùng |
|---|---|---|---|---|---|
| Thử nghiệm nội bộ | Cho phép, cảnh báo | Cho phép, cảnh báo | Cho phép | Chặn | Cho phép (để tái lập minh chứng) |
| Hiển thị trình diễn phi thương mại | Cho phép kèm nhãn "chưa xác minh quyền" | như bên trái | Cho phép kèm ghi công | Chặn | Chặn |
| Xuất bản công khai | **Chặn** | **Chặn** | Cho phép kèm ghi công | Chặn | Chặn |
| Thương mại | Chặn | Chặn | CC0 / tự chụp: cho phép; giấy phép mở không có NC: cho phép kèm điều kiện; cấp phép: chỉ khi phạm vi ghi "commercial" | Chặn | Chặn |

Nơi gọi cổng: trước khi sinh (`generation/streamlit_runner.py`, mục đích thử nghiệm), khi xuất ảnh (`GET /passports/{id}/export`, mục đích trình diễn), khi xuất bản (`POST /passports/{id}/publish`).

### Thư đề nghị cấp phép

Khu vực "Nguồn và bản quyền" tạo sẵn thư cho từng hiện vật chưa xác minh (điền tên đơn vị, tên hiện vật, URL). Nội dung xin phép dùng cho nghiên cứu, thi đấu, trình diễn phi thương mại, kèm cách ghi công, và cam kết gỡ ảnh nếu bị từ chối. Trạng thái gửi thư được theo dõi bằng trường `permission_request` (hiện là `not_sent` cho cả 6). Khi gửi, đổi `rights_status` thành `permission_requested`; khi có trả lời, ghi `permission` (người trả lời, ngày, phạm vi, tệp bằng chứng).

## 4. Design Passport

`provenance/passport.py`, `provenance/builder.py`. Mỗi thiết kế có một Passport JSON trong `outputs/passports/`, mã dạng `DP-<hiện vật>-<ngày>-V<biến thể>`.

| Phần | Nội dung |
|---|---|
| `heritage` | Hiện vật, nguồn, câu ghi công, tình trạng quyền tại thời điểm chạy |
| `artifacts` | Mọi tệp liên quan (ảnh gốc, ảnh 512, Canny, hoa văn, bản ghép, bản cuối, bản sửa) với SHA-256 đầy đủ, kích thước |
| `generation` | Mô hình, phiên bản thư viện, GPU, seed, số bước, guidance, trọng số ControlNet, prompt, bảng màu, bố cục và cách chọn bố cục, tham số img2img |
| `process_steps` | Từng bước: ai làm (AI, hệ thống, người), công cụ, băm đầu vào và đầu ra |
| `ai_disclosure` | Danh sách việc do AI làm, do hệ thống làm, do người làm |
| `versions` | v1, v2… mỗi bản có loại (`ai_generated`, `system_repair`, `human_edit`), mã băm, mã băm bản cha |
| `edits` | Chỉnh sửa thủ công: ai, lúc nào, công cụ, sửa gì, băm trước và sau |
| `quality`, `reviews`, `approval` | Kết quả cổng (kèm phiên bản cấu hình ngưỡng), phiếu chuyên gia, trạng thái phê duyệt |
| `rights` | Kết quả cổng quyền cho từng mục đích |
| `ledger` | Sổ cái sự kiện có băm nối chuỗi |

### Sổ cái băm nối chuỗi

Mỗi sự kiện ghi `seq`, thời điểm, loại sự kiện, người/hệ thống thực hiện, băm của nội dung sự kiện và băm của sự kiện trước; băm của sự kiện là SHA-256 của các trường đó ở dạng JSON chuẩn hoá. Hàm `verify` kiểm tra: chuỗi băm liền mạch, nội dung từng sự kiện chưa bị sửa, các trường tóm tắt (trạng thái phê duyệt, danh sách phiên bản, số phiếu thẩm định) khớp với sổ cái, và băm của từng tệp trên đĩa khớp với băm đã ghi. Kết quả hiện tại: 24/24 Passport đạt.

Giới hạn cần nói rõ: sổ cái giúp **phát hiện** sửa đổi khi đã biết băm đầu chuỗi; người có quyền ghi tệp vẫn có thể viết lại cả chuỗi. Để chống việc đó, cần neo băm đầu chuỗi ra ngoài (ví dụ ghi vào commit Git đã đẩy lên, hoặc in vào hồ sơ nộp BTC). Bộ kiểm thử có ca sửa một sự kiện và xác nhận `verify` báo lỗi.

### Nhãn "Thiết kế hỗ trợ bởi AI"

Khi xuất ảnh (`GET /passports/{id}/export`), `provenance/labeling.py` thêm:

- Dải nhãn nhìn thấy được ở chân ảnh: "Thiết kế hỗ trợ bởi AI", mã Passport; nếu quyền ảnh nguồn chưa xác minh thì thêm "Ảnh nguồn chưa xác minh quyền — không dùng thương mại".
- Siêu dữ liệu PNG (iTXt): mã Passport, SHA-256 của thiết kế, tên hiện vật, câu ghi công, cờ cảnh báo quyền. Siêu dữ liệu vẫn còn nếu dải nhãn bị cắt khỏi ảnh.

### Chỉnh sửa thủ công

`POST /passports/{id}/edits`: nhận ảnh (≤ 8 MB, phải là ảnh hợp lệ), mã người sửa, vai trò, công cụ, mô tả. Hệ thống lưu ảnh vào `outputs/edits/<mã Passport>/`, tạo phiên bản mới mang băm bản cha, ghi sự kiện vào sổ cái, **chạy lại cổng G3 trên bản sửa**, rồi đặt trạng thái theo kết quả. Phiên bản cũ không bị ghi đè.

## 5. Bằng chứng theo yêu cầu BTC

| BTC yêu cầu | Ở đâu |
|---|---|
| Danh mục nguồn và giấy phép của 6 hiện vật | `data/heritage/metadata.json`; khu vực "Nguồn và bản quyền"; `GET /provenance/catalog` |
| Ghi công | Trường `attribution` của từng hiện vật; in trong nhãn khi xuất ảnh |
| Lịch sử biên tập thủ công | Mục `edits`, `versions`, `ledger` của Passport; dòng thời gian ở khu vực "Design Passport" |
| Nhãn "có hỗ trợ AI" | Ảnh xuất từ API; mục `ai_disclosure` |
| Passport đi từ nguồn đến sản phẩm qua các phiên bản | `outputs/passports/DP-*.json`; chuỗi truy vết trên giao diện |
