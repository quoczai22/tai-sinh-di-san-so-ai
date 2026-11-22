# 07. Nguồn gốc, bản quyền và truy vết khi biên tập

Trả lời yêu cầu cải tiến 3 của BTC: **nguồn và giấy phép của các hiện vật, ghi công, lịch sử biên tập thủ công, nhãn "có hỗ trợ AI"**.

Hiện trạng: từ 19/11/2026 dữ liệu chính là 6 hiện vật của bộ dữ liệu nghiên cứu LR3D-CULT2 (HV07 đến HV12). Trang Mendeley Data của bộ dữ liệu ghi giấy phép **CC BY 4.0** (xác nhận ngày 21/11/2026), nên nhóm ghi giấy phép này cho cả 6 vật và ghi công tác giả theo yêu cầu của giấy phép. Hạn chế còn lại: mô tả bộ dữ liệu nói một phần mô hình lấy từ Sketchfab theo giấy phép học thuật, nhóm chưa xác minh riêng nguồn của từng vật. 6 ảnh ban đầu lấy từ website bán gốm (HV01 đến HV06) đã ngừng dùng. Phần việc của bản chung kết là (1) ghi đầy đủ và trung thực những gì đã biết, (2) để hệ thống tự chặn những mục đích chưa được phép, (3) truy vết mọi thay đổi trên thiết kế, (4) ghi nguồn và giấy phép của dữ liệu huấn luyện LoRA.

## 1. Danh mục nguồn (schema 2.0)

Tệp `data/heritage/metadata.json`.

Mười trường nguồn gốc bắt buộc (`tsds/provenance/registry.py::REQUIRED_PROVENANCE`): tên hiện vật, nguồn, URL, đơn vị lưu giữ hoặc đăng ảnh, tác giả ảnh, tình trạng quyền, giấy phép, cách ghi công, ngày thu thập, phiên bản dữ liệu gốc (mã băm ảnh gốc). Hệ thống **không tự điền** trường nào nhóm không biết. Độ đầy đủ hiện là 8/10 ở cả 6 hiện vật đang dùng (thiếu giấy phép từng vật và ngày thu thập).

### Sáu hiện vật đang dùng (LR3D-CULT2)

Nguồn: bộ dữ liệu LR3D-CULT2 "Vietnamese Ceramic Cultural Artifacts" (Nguyen và cộng sự, Mendeley Data, DOI 10.17632/jr23fnrvx2.1, FPT University, Hà Nội). Theo mô tả của bộ dữ liệu, một phần mô hình 3D được quét tại các làng gốm Bát Tràng và Thanh Hà, một phần lấy từ Sketchfab theo giấy phép học thuật. Chưa xác định từng vật thuộc nguồn nào.

| Mã | Mã dữ liệu | Hiện vật | Quyền | Trường còn thiếu |
|---|---|---|---|---|
| HV07 | LR3D_33 | Men lam: huy hiệu, mẫu đơn và dây sen (#33) | Chưa xác minh | Giấy phép từng vật, ngày thu thập |
| HV08 | LR3D_61 | Men lam: rồng và mây (#61) | Chưa xác minh | như trên |
| HV09 | LR3D_50 | Men lam: dây hoa cuộn dày (#50) | Chưa xác minh | như trên |
| HV10 | LR3D_38 | Men lam: cây hoa (#38) | Chưa xác minh | như trên |
| HV11 | LR3D_97 | Men lam: nét lam thưa trên men kem (#97) | Chưa xác minh | như trên |
| HV12 | LR3D_124 | Men lam: huy hiệu rồng (#124) | Chưa xác minh | như trên |

Mỗi hiện vật có hai ảnh: ảnh render cả bình từ mô hình 3D (`data/heritage/LR3D_xx.png`, 512×512, để hiển thị và nhận diện) và **mảng hoa văn phẳng** là texture UV trải phẳng của mô hình (`data/heritage/panels/LR3D_xx.png`, cạnh dài khoảng 2.048 px, đưa vào mô hình sinh). Mô tả hiện vật do nhóm viết (`description_origin: team_written`). Ngày thu thập chưa có nhật ký (trường `collected_on` để trống và được ghi là cần điền).

## 2. Tiêu chí tuyển ảnh và kết quả rà soát

Tệp `config/heritage_selection.json` (HS-2.0), chạy bằng `tsds/provenance/registry.py::assess_selection`.

| Tiêu chí | Quy tắc | Loại |
|---|---|---|
| C1. Độ phân giải | Cạnh ngắn ảnh gốc ≥ 512 px **và** cạnh dài vùng hiện vật ≥ 512 px (cảnh báo nếu < 768), để không phải phóng to khi đưa về 512×512 | Bắt buộc |
| C2. Mật độ nét hoa văn | Số pixel cạnh Canny ≥ 60% mốc 20.092 px (mức chuẩn nhóm đặt ban đầu), tức ≥ 12.055 px | Bắt buộc |
| C3. Quyền | Có URL, đơn vị đăng ảnh, tình trạng quyền; chỉ phạm vi công cộng, giấy phép mở, đã được cấp phép, hoặc ảnh tự chụp mới được xuất bản | Bắt buộc |
| C4. Tính di sản | Ưu tiên hiện vật do bảo tàng lưu giữ, có niên đại công bố; sản phẩm thương mại đương đại chỉ dùng khi có phép của cơ sở sản xuất | Khuyến nghị |

### Kết quả cho 6 hiện vật đang dùng

| Mã | Vùng hiện vật trong ảnh render | C1 | Nét Canny | C2 | C3 | C4 |
|---|---|---|---|---|---|---|
| HV07 | 277×325, phóng ×1,50 | **Không đạt** | 26.400 | Đạt | Cảnh báo | Cảnh báo |
| HV08 | 296×327, phóng ×1,49 | **Không đạt** | 17.104 | Đạt | Cảnh báo | Cảnh báo |
| HV09 | 200×314, phóng ×1,55 | **Không đạt** | 13.827 | Đạt | Cảnh báo | Cảnh báo |
| HV10 | 102×310, phóng ×1,57 | **Không đạt** | 5.012 | **Không đạt** | Cảnh báo | Cảnh báo |
| HV11 | 165×326, phóng ×1,50 | **Không đạt** | 5.453 | **Không đạt** | Cảnh báo | Cảnh báo |
| HV12 | 129×309, phóng ×1,58 | **Không đạt** | 7.968 | **Không đạt** | Cảnh báo | Cảnh báo |

**Cần nói rõ giới hạn của kết quả này:** C1 và C2 được đo trên **ảnh render cả bình** (512×512), nên cả 6 hiện vật đều trượt C1 và 3 hiện vật trượt C2. Nhưng ảnh đưa vào mô hình sinh từ 19/11/2026 là **mảng hoa văn phẳng** (khoảng 2.048 px), chưa được chấm C1 và C2. Chưa có phép đo C1, C2 cho mảng phẳng; đây là việc còn lại. Cả 6 hiện vật ở mức cảnh báo C3 (quyền chưa xác minh) và C4 (nguồn là bộ dữ liệu nghiên cứu, không phải bảo tàng).

## 3. Cổng quyền theo mục đích sử dụng

`tsds/provenance/registry.py::rights_gate`. Cổng được gọi trong mã, không phải hướng dẫn trên giấy.

| Mục đích | Chưa xác minh | Đã gửi đề nghị | Đã cấp phép / giấy phép mở / CC0 / tự chụp | Bị từ chối | Hiện vật ngừng dùng |
|---|---|---|---|---|---|
| Thử nghiệm nội bộ | Cho phép, cảnh báo | Cho phép, cảnh báo | Cho phép | Chặn | Cho phép (để tái lập minh chứng) |
| Hiển thị trình diễn phi thương mại | Cho phép kèm nhãn "chưa xác minh quyền" | như bên trái | Cho phép kèm ghi công | Chặn | Chặn |
| Xuất bản công khai | **Chặn** | **Chặn** | Cho phép kèm ghi công | Chặn | Chặn |
| Thương mại | Chặn | Chặn | CC0 / tự chụp: cho phép; giấy phép mở không có NC: cho phép kèm điều kiện; cấp phép: chỉ khi phạm vi ghi "commercial" | Chặn | Chặn |

Nơi gọi cổng: trước khi sinh (`tsds/pipeline/run.py`, mục đích thử nghiệm), khi xuất ảnh (`GET /passports/{id}/export`, mục đích trình diễn), khi xuất bản (`POST /passports/{id}/publish`).

### Thư đề nghị cấp phép

Trang "Nguồn và bản quyền" của giao diện từng tạo sẵn thư cho từng hiện vật chưa xác minh (điền tên đơn vị, tên hiện vật, URL). Trang này đã gỡ khỏi web ngày 19/11/2026; mã còn trong lịch sử git (`web_ui/assets/js/views/sources.js`). Nội dung xin phép dùng cho nghiên cứu, thi đấu, trình diễn phi thương mại, kèm cách ghi công, và cam kết gỡ ảnh nếu bị từ chối. Trạng thái gửi thư được theo dõi bằng trường `permission_request` (hiện là `not_sent` cho cả 12 hiện vật, gồm 6 đang dùng). Khi gửi, đổi `rights_status` thành `permission_requested`; khi có trả lời, ghi `permission` (người trả lời, ngày, phạm vi, tệp bằng chứng).

## 4. Design Passport

`tsds/provenance/passport.py`, `tsds/provenance/builder.py`. Mỗi thiết kế có một Passport JSON trong `outputs/passports/`, mã dạng `DP-<hiện vật>-<ngày>-V<biến thể>`.

| Phần | Nội dung |
|---|---|
| `heritage` | Hiện vật, nguồn, câu ghi công, tình trạng quyền tại thời điểm chạy |
| `artifacts` | Mọi tệp liên quan (ảnh gốc, ảnh 512, Canny, hoa văn, ảnh áo và mặt nạ áo do LoRA sinh, bản ghép, bản cuối, bản sửa) với SHA-256 đầy đủ, kích thước |
| `generation` | Mô hình, phiên bản thư viện, GPU, seed, số bước, guidance, trọng số ControlNet, prompt, bảng màu, bố cục và cách chọn bố cục, tham số polish (độ nhiễu, polish chỉ vùng áo, trạng thái và số lần thử lại, khoá họa tiết `pattern_lock_v1`), và khối `garment`: nguồn áo, seed áo, các ứng viên đã thử và lý do loại, đường dẫn LoRA, mô hình gốc, dữ liệu huấn luyện, giấy phép, trích dẫn, cách tách mặt nạ (SAM) |
| `process_steps` | Từng bước: ai làm (AI, hệ thống, người), công cụ, băm đầu vào và đầu ra |
| `ai_disclosure` | Danh sách việc do AI làm, do hệ thống làm, do người làm |
| `versions` | v1, v2… mỗi bản có loại (`ai_generated`, `system_repair`, `human_edit`), mã băm, mã băm bản cha |
| `edits` | Chỉnh sửa thủ công: ai, lúc nào, công cụ, sửa gì, băm trước và sau |
| `quality`, `reviews`, `approval` | Kết quả cổng (kèm phiên bản cấu hình ngưỡng), phiếu chuyên gia, trạng thái phê duyệt |
| `rights` | Kết quả cổng quyền cho từng mục đích |
| `ledger` | Sổ cái sự kiện có băm nối chuỗi |

### Sổ cái băm nối chuỗi

Mỗi sự kiện ghi `seq`, thời điểm, loại sự kiện, người/hệ thống thực hiện, băm của nội dung sự kiện và băm của sự kiện trước; băm của sự kiện là SHA-256 của các trường đó ở dạng JSON chuẩn hoá. Hàm `verify` kiểm tra: chuỗi băm liền mạch, nội dung từng sự kiện chưa bị sửa, các trường tóm tắt (trạng thái phê duyệt, danh sách phiên bản, số phiếu thẩm định) khớp với sổ cái, và băm của từng tệp trên đĩa khớp với băm đã ghi. Kết quả hiện tại: 24/24 Passport của bộ demo đạt (72/72 kể cả 48 Passport của bộ seed 43, 44).

Giới hạn cần nói rõ: sổ cái giúp **phát hiện** sửa đổi khi đã biết băm đầu chuỗi; người có quyền ghi tệp vẫn có thể viết lại cả chuỗi. Để chống việc đó, cần neo băm đầu chuỗi ra ngoài (ví dụ ghi vào commit Git đã đẩy lên, hoặc in vào hồ sơ nộp BTC). Bộ kiểm thử có ca sửa một sự kiện và xác nhận `verify` báo lỗi.

### Nhãn "Thiết kế hỗ trợ bởi AI"

Khi xuất ảnh (`GET /passports/{id}/export`), `tsds/provenance/labeling.py` thêm:

- Dải nhãn nhìn thấy được ở chân ảnh: "Thiết kế hỗ trợ bởi AI", mã Passport; nếu quyền ảnh nguồn chưa xác minh thì thêm "Ảnh nguồn chưa xác minh quyền — không dùng thương mại".
- Siêu dữ liệu PNG (iTXt): mã Passport, SHA-256 của thiết kế, tên hiện vật, câu ghi công, cờ cảnh báo quyền. Siêu dữ liệu vẫn còn nếu dải nhãn bị cắt khỏi ảnh.

### Chỉnh sửa thủ công

`POST /passports/{id}/edits`: nhận ảnh (≤ 8 MB, phải là ảnh hợp lệ), mã người sửa, vai trò, công cụ, mô tả. Hệ thống lưu ảnh vào `outputs/edits/<mã Passport>/`, tạo phiên bản mới mang băm bản cha, ghi sự kiện vào sổ cái, **chạy lại cổng G3 trên bản sửa**, rồi đặt trạng thái theo kết quả. Phiên bản cũ không bị ghi đè.

## 5. Bằng chứng theo yêu cầu BTC

| BTC yêu cầu | Ở đâu |
|---|---|
| Danh mục nguồn và giấy phép của 6 hiện vật đang dùng | `data/heritage/metadata.json`; `GET /provenance/catalog` |
| Ghi công | Trường `attribution` của từng hiện vật; in trong nhãn khi xuất ảnh |
| Lịch sử biên tập thủ công | Mục `edits`, `versions`, `ledger` của Passport; dòng thời gian trong `GET /passports/{id}` |
| Nhãn "có hỗ trợ AI" | Ảnh xuất từ API; mục `ai_disclosure` |
| Passport đi từ nguồn đến sản phẩm qua các phiên bản | `outputs/passports/DP-*.json` (chuỗi truy vết trong `artifacts`, `process_steps`, `ledger`). Giao diện web cho người xem không còn trang Passport |

## 6. LoRA dáng áo dài và dữ liệu huấn luyện

Áo dài nền do Stable Diffusion 1.5 cộng một LoRA (lớp nhỏ gắn thêm vào mô hình để mô hình học dáng áo dài) sinh mỗi lần chạy. Nguồn và giấy phép của phần này:

| Mục | Nội dung |
|---|---|
| Dữ liệu huấn luyện | Bộ VietFashion, lọc còn 226 ảnh áo dài (cổ trụ, tay dài, dài quá gối; `scripts/data_prep/filter_vietfashion.py`, `scripts/data_prep/export_lora_set.py`). Ảnh nguồn nhỏ (256×344), do mô hình sinh tổng hợp |
| Giấy phép | CC BY-NC 4.0: **chỉ dùng phi thương mại**. Tác giả bộ dữ liệu đồng ý bằng email cho nhóm sử dụng |
| Ghi công | Cao, Bui, Vo, Tran, Le. VietFashion: Benchmarking Sketch-Text Composed Image Retrieval for Cultural Outfits. ICMR 2026. doi:10.1145/3805622.3810590 |
| Trọng số | `data/lora/aodai_r16_512/` (hạng 16, 400 bước, ảnh 512×688) dùng trong sản phẩm; `data/lora/aodai_r32_768/` (hạng 32, ảnh 768×1032) chỉ để đối chứng vì cho nền áo có sọc. Ghi chú giấy phép nằm ở `data/lora/README.md` và `config.json` của từng bản |
| Trong Passport | Khối `generation.garment.lora` ghi đường dẫn, mô hình gốc, dữ liệu huấn luyện, giấy phép và trích dẫn; bước `generate_garment` ghi giấy phép trong chú thích và có mặt trong nhãn AI |
| Việc còn lại | Cổng quyền `rights` của Passport hiện tính theo quyền của hiện vật gốm; **chưa chặn xuất bản thương mại theo giấy phép NC của LoRA**. Trọng số đang nằm trong repo; nếu đưa repo ra công khai, phải bảo đảm phù hợp thỏa thuận với tác giả bộ dữ liệu |
