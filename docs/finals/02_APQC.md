# 02. Rà soát quy trình theo APQC PCF: AS-IS và TO-BE

## Cách đọc tài liệu này

Tài liệu mượn cách tổ chức của bộ tài liệu "Quy trình mua hàng" mà nhóm tham khảo: đi từ **mục tiêu quản trị** → **nguyên tắc vận hành** → **logic ba lớp** (cơ sở thiết kế, cách thực hiện, sản phẩm bàn giao) → **các luồng end-to-end** và **số điểm kiểm soát** của từng luồng → **danh mục quy trình cấp 3 (L3)** có chủ, rủi ro, điểm kiểm soát và KPI. Nội dung là của Tái Sinh Di Sản Số; chỉ cấu trúc là mượn.

APQC PCF chỉ dùng làm **khung phân loại** để gọi tên và xếp nhóm quy trình, không bê nguyên quy trình của doanh nghiệp lớn. Nhóm chỉ ghi mã PCF ở cấp hạng mục (category, ví dụ 2.0) và nhóm quy trình (process group, ví dụ 13.3). Mã sâu hơn được đánh dấu *cần đối chiếu bản PCF chính thức* vì nhóm chưa đối chiếu từng dòng.

- Bản tham chiếu: APQC PCF Cross-Industry 7.4 (08/2024). APQC đã phát hành bản 8.0 vào 02/2026; khi nộp chính thức nên đối chiếu lại tên nhóm theo bản 8.0.
- Ghi công theo điều kiện sử dụng của APQC: *Tham chiếu APQC Process Classification Framework® (PCF) Cross-Industry, © APQC. Dùng và chỉnh sửa theo giấy phép miễn phí của APQC.*
- Số liệu: chỉ ghi số đã đo được từ dữ liệu trong repo. Chỗ chưa có dữ liệu ghi "Mục tiêu cần đo" và để trống giá trị. Bảng KPI đầy đủ ở [08_KPI.md](08_KPI.md).

## Lớp A. Cơ sở thiết kế

### Khung tham chiếu APQC dùng đến

| Nhóm nghiệp vụ của sản phẩm | Hạng mục / nhóm quy trình PCF | Vì sao chọn |
|---|---|---|
| 1. Chiến lược và đổi mới | 2.0 Develop and Manage Products and Services: nhóm 2.1 (quản trị chương trình phát triển sản phẩm), 2.2 (tạo và định nghĩa ý tưởng) | Sản phẩm là một chương trình phát triển nhỏ; không cần 1.0 (chiến lược doanh nghiệp) |
| 2. Phát triển sản phẩm | 2.0, nhóm 2.3 (phát triển sản phẩm: thiết kế, làm mẫu, thử nghiệm) | Toàn bộ chuỗi từ hiện vật đến thiết kế áo dài |
| 3. Quản lý chất lượng | 13.0 Develop and Manage Business Capabilities, nhóm 13.3 Manage enterprise quality (xác lập yêu cầu chất lượng, đánh giá theo yêu cầu, xử lý không phù hợp) | Cổng G2/G3, QC, thẩm định chuyên gia, sửa/sinh lại |
| 4. Tri thức và thông tin | 13.0, nhóm 13.5 (năng lực quản lý tri thức); 8.0 Manage Information Technology ở phần quản lý dữ liệu | Danh mục hiện vật, nguồn, phiên bản, Design Passport |
| 5. Khách hàng và bên liên quan | 6.0 Manage Customer Service (phản hồi); 12.0 Manage External Relationships (chuyên gia, chủ sở hữu ảnh, vấn đề pháp lý và đạo đức) | Chuyên gia là bên ngoài; quyền ảnh là quan hệ pháp lý với bên ngoài |
| Xuyên suốt: quyền sử dụng | 11.0 Manage Enterprise Risk, Compliance, Remediation, and Resiliency; nhóm về pháp lý và sở hữu trí tuệ trong 12.0 (*cần đối chiếu mã nhóm*) | Cổng quyền theo mục đích sử dụng |

### Sáu mục tiêu quản trị

| Mã | Mục tiêu | Nội dung |
|---|---|---|
| M1 | Giữ bản sắc họa tiết đến tận thiết kế cuối | Họa tiết của hiện vật phải còn nhận ra được trên áo dài sau mọi bước AI; không chỉ đo ở hoa văn trung gian. |
| M2 | Kết luận dựa trên đối chứng | Mọi nhận định "tham số X tốt hơn" phải đến từ thí nghiệm đổi một yếu tố, nhiều seed, chấm mù. |
| M3 | Quyền sử dụng minh bạch trước khi dùng | Biết nguồn, chủ sở hữu, giấy phép của từng ảnh; hệ thống tự chặn mục đích sử dụng chưa được phép. |
| M4 | Truy vết xuyên suốt | Một chuỗi mã nối hiện vật → lần chạy → thiết kế → phiên bản → phê duyệt; mỗi tệp có SHA-256. |
| M5 | Phân vai rõ giữa người và máy | AI và hệ thống đo kỹ thuật, chuyển tiếp; chuyên gia quyết định văn hoá và thẩm mỹ; không chỉ số nào tự phê duyệt. |
| M6 | Vận hành vừa sức nhóm | Một GPU laptop 8 GB, dữ liệu dạng tệp JSON/CSV; không thêm bước nào không gắn với một rủi ro cụ thể. |

### Năm nguyên tắc vận hành

| Nguyên tắc | Nội dung | Vì sao | Mục tiêu |
|---|---|---|---|
| Phân luồng ngay từ đầu vào | Mỗi yêu cầu thuộc đúng một luồng (hiện vật có sẵn, hiện vật mới tải lên, thí nghiệm, biên tập thủ công, xuất bản), xác định bằng nguồn ảnh và mục đích. | Hiện vật mới phải qua thêm cổng nguồn gốc; thí nghiệm không được lẫn với sản phẩm. | M3, M6 |
| Một mã định danh đi suốt chuỗi | `HV08` → `R20261119T161848-HV08` → `DP-HV08-20261119T161848-V2` → phiên bản `v1`, `v2` (mỗi bản có mã băm và mã băm bản cha). | Từ một ảnh xuất ra, lần ngược được hiện vật, tham số, người sửa. | M4 |
| Kiểm soát tại cổng, do hệ thống thực thi | Tiêu chí tuyển ảnh C1–C4, cổng quyền, G2, G3, cổng xuất bản đều là mã chạy được, không phải danh sách kiểm tra trên giấy. | Ngăn lỗi từ đầu vào, không phụ thuộc trí nhớ của người làm. | M1, M3 |
| Điểm số quyết định chuyển tiếp, không quyết định phê duyệt | Kết quả cổng chỉ chọn đường đi tiếp: sinh lại, sửa, QC xem, chuyển chuyên gia. Phê duyệt chỉ đến từ phiếu chuyên gia. | Tách câu hỏi "đủ điều kiện kỹ thuật chưa" khỏi câu hỏi "có đúng văn hoá, có đẹp không". | M5 |
| Mỗi bước và mỗi điểm bàn giao có chủ rõ | Nhà thiết kế, Hệ thống AI, QC Officer, Chuyên gia di sản, Quản trị dữ liệu; điểm bàn giao giữa hai lane là một trạng thái phê duyệt cụ thể trong Passport. | Không bỏ trống, không chồng chéo trách nhiệm. | M4, M5 |

## Lớp B. Cách thực hiện

1. **Khảo sát hiện trạng**: đọc mã nguồn, dữ liệu 06/09/2026 và góp ý của BTC → [01_AUDIT.md](01_AUDIT.md).
2. **Phân tích vấn đề và rủi ro**: đo 24 thiết kế của bản 06/09/2026 bằng cổng mới để có số liệu nền, rồi đo lại bằng bộ demo ngày 20/11/2026 (mục "Số liệu nền" bên dưới).
3. **Thiết kế hệ luồng vận hành**: năm luồng end-to-end, cây phân luồng ở đầu vào → BPMN [03_BPMN.md](03_BPMN.md).
4. **Kiến trúc quy trình**: danh mục L3 có chủ, rủi ro, điểm kiểm soát, KPI (mục Lớp C).
5. **Kiến trúc bằng chứng**: mỗi điểm kiểm soát sinh ra một bằng chứng có thể mở được (CSV, JSON, ảnh, sổ cái băm).
6. **Bàn giao và hiệu chỉnh**: ngưỡng cổng đang ở trạng thái tạm thời; hiệu chỉnh khi đủ phiếu chuyên gia ([05](05_QUALITY_ASSURANCE.md)).

### Số liệu nền (đo trên dữ liệu thật trong repo)

| Chỉ số | Bản 06/09/2026 (lịch sử, commit `b1192b0`) | Bộ demo 20/11/2026 (seed 42) |
|---|---|---|
| Thiết kế đo | 24 (6 hiện vật cũ × 4 biến thể) | 24 (6 hiện vật LR3D-CULT2 × 4 mức sáng tạo) |
| G2 hoa văn: PASS / WARN / FAIL | 21 / 1 / 2 | 16 / 6 / 2 |
| G3 thiết kế cuối: PASS / WARN / FAIL | 0 / 4 / 20 | 24 / 0 / 0 |
| PPS (giữ họa tiết) | trung vị 0,36 trước sửa | trung bình 0,945 (khoá họa tiết là bước mặc định) |
| Thiết kế được sửa tự động | 19; G3 sau sửa: 10 PASS, 9 WARN | không còn thiết kế G3 FAIL để sửa |
| Hiện vật có quyền sử dụng đã xác minh | 0/6 | 0/6 |
| Trường nguồn gốc điền được | 7/10 ở cả 6 hiện vật | 8/10 ở cả 6 hiện vật (thiếu giấy phép từng vật và ngày thu thập) |

Nguồn của bộ demo: Passport trong `outputs/passports/` (`GET /quality/designs`); nguồn của bản 06/09/2026: `evaluation/quality_gate_legacy.csv` ở commit `b1192b0`.

## Lớp C. Sản phẩm bàn giao

### Năm luồng end-to-end

| Luồng | Đặc điểm | Điểm yếu chính ở AS-IS | Điểm kiểm soát ở TO-BE | Trạng thái |
|---|---|---|---|---|
| L-1. Thiết kế từ hiện vật có sẵn | Người dùng chọn hiện vật trong thư viện, hệ thống sinh 4 phương án | Không đo thiết kế cuối; ghi đè ảnh cũ; không có thẩm định | 10: cổng quyền theo mục đích, G2, vòng thử lại polish, G3, QC xem cảnh báo, chấm mù chuyên gia, kiểm tra điểm mâu thuẫn quyết định, cổng xuất bản, nhãn AI khi xuất, sổ cái băm | Đã chạy (sinh ảnh cần máy có GPU) |
| L-2. Thiết kế từ hiện vật mới | Đưa ảnh hiện vật mới vào thư viện rồi đi tiếp như L-1 | Không có tiêu chí tuyển ảnh; ảnh 300×300 vẫn được dùng | 6 điểm thêm trước L-1: C1 độ phân giải, C2 mật độ nét, C3 quyền, C4 tính xác thực di sản, đủ 10 trường nguồn gốc, SHA-256 ảnh gốc | Một phần: chạy bằng dòng lệnh, chưa có nút tải lên trên giao diện |
| L-3. Thí nghiệm có kiểm soát | So sánh cấu hình để ra quyết định cải tiến | Bốn yếu tố đổi cùng lúc, một seed | 7: kiểm tra kế hoạch đơn biến, ghi kế hoạch trước khi chạy, ghi cấu hình và SHA-256 từng lượt, che danh tính biến thể, xáo thứ tự theo người chấm, tối thiểu 3 người chấm, đo độ đồng thuận trước khi kết luận | EXP-C đã chạy, chờ phiếu; EXP-A, EXP-B đã lập kế hoạch, chờ GPU |
| L-4. Biên tập thủ công | Nhà thiết kế sửa ảnh ngoài hệ thống rồi tải lên | Không ghi nhận | 6: chỉ nhận ảnh hợp lệ ≤ 8 MB, khai báo người sửa và nội dung sửa, phiên bản mới mang mã băm bản cha, chạy lại G3, thẩm định lại, sổ cái băm | Đã chạy qua API |
| L-5. Xuất bản và tải xuống | Đưa thiết kế ra ngoài | Không phân biệt mục đích; không nhãn AI | 4: chỉ thiết kế đã phê duyệt, cổng quyền "xuất bản công khai", nhãn AI nhìn thấy được và nằm trong siêu dữ liệu PNG, ghi công nguồn ảnh | Đã chạy; hiện cổng quyền chặn xuất bản vì chưa hiện vật nào có giấy phép |

### Danh mục quy trình L3: AS-IS → TO-BE

#### Nhóm 1. Chiến lược và đổi mới (PCF 2.1, 2.2)

| Mã | Quy trình | AS-IS | Điểm nghẽn, rủi ro | TO-BE | Giá trị cải tiến |
|---|---|---|---|---|---|
| 1.1 | Quản lý đổi mới sản phẩm | Đổi tham số theo cảm nhận sau khi xem ảnh | Kết luận sai vì nhiều yếu tố đổi cùng lúc | Mỗi đề xuất cải tiến thành một thí nghiệm có câu hỏi, biến độc lập, biến cố định, số seed, chỉ số ([06](06_EXPERIMENTS.md)) | Quyết định có bằng chứng, lặp lại được |
| 1.2 | Nghiên cứu nhu cầu người dùng | Ghi sự kiện bấm nút vào nhật ký audit | Nhật ký không cho biết người dùng hài lòng hay không | Giữ nhật ký (đã giới hạn danh sách sự kiện được phép); bổ sung phiếu phản hồi sau khi xem bộ thiết kế (kế hoạch) | Biết phương án nào được chọn và vì sao |
| 1.3 | Quản lý danh mục thiết kế | 24 ảnh trong thư mục, không trạng thái | Không biết thiết kế nào dùng được | Mỗi thiết kế có trạng thái phê duyệt trong Passport; bảng tổng quan theo trạng thái | Chỉ đưa thiết kế đã duyệt ra ngoài |

| Mã | Chủ | Đầu vào → Đầu ra | Điểm kiểm soát | KPI | Triển khai |
|---|---|---|---|---|---|
| 1.1 | BA / trưởng nhóm | Đề xuất cải tiến → tệp kế hoạch thí nghiệm, kết quả, quyết định | Bộ kiểm tra kế hoạch từ chối kế hoạch đổi hơn một yếu tố | K08 | Đã chạy |
| 1.2 | BA | Nhật ký audit, phiếu phản hồi → báo cáo nhu cầu | Danh sách sự kiện audit được phép | K15 | Một phần |
| 1.3 | BA | Passport → danh mục theo trạng thái | Trạng thái chỉ đổi qua API có kiểm tra điều kiện | K14 | Đã chạy |

#### Nhóm 2. Phát triển sản phẩm (PCF 2.3)

| Mã | Quy trình | AS-IS | Điểm nghẽn, rủi ro | TO-BE | Giá trị cải tiến |
|---|---|---|---|---|---|
| 2.1 | Tiếp nhận hiện vật | Tự tìm ảnh trên web bán gốm | Ảnh nhỏ, nén nặng, không rõ quyền | Tuyển ảnh theo C1–C4; ưu tiên ảnh bảo tàng có giấy phép mở | Hoa văn sinh từ ảnh đủ chi tiết |
| 2.2 | Kiểm tra nguồn gốc và quyền sử dụng | Ghi chú "chưa xác minh" | Dùng ảnh vào mục đích chưa được phép | Danh mục nguồn 10 trường; cổng quyền theo 4 mục đích (thử nghiệm, trình diễn, xuất bản, thương mại) | Hệ thống tự chặn, có lý do rõ |
| 2.3 | Phân tích đặc trưng họa tiết | Canny + bảng màu | Không biết ảnh có đủ nét không | Đo mật độ nét (C2) so với mốc; lưu ảnh Canny và mã băm | Có ngưỡng loại ảnh nghèo chi tiết |
| 2.4 | Sinh họa tiết AI | 4 biến thể, seed 42 | Hoa văn có thể là ảnh nguyên chiếc bình | Cổng G2 (VLS, đường nối); FAIL thì đánh dấu và gợi ý sinh lại (chưa tự động); nạp mảng hoa văn phẳng | Chặn lỗi "áo in hình cái bình" |
| 2.5 | Ghép họa tiết vào áo dài | Ghép tất định + img2img 0,40 toàn ảnh | img2img vẽ lại họa tiết | Áo dài do LoRA sinh, ghép tất định, polish chỉ vùng áo 0,20, khoá họa tiết, vòng thử lại, cổng G3 | Họa tiết sống sót đến thiết kế cuối |
| 2.6 | Bàn giao sang kiểm soát chất lượng | Không có | – | Passport sinh ngay sau lần chạy với trạng thái từ cổng kỹ thuật | Không thiết kế nào lọt qua mà không đo |

| Mã | Chủ | Đầu vào → Đầu ra | Điểm kiểm soát | KPI | Triển khai |
|---|---|---|---|---|---|
| 2.1 | Quản trị dữ liệu | Ảnh ứng viên → mục hiện vật `active` hoặc bị từ chối | C1, C2 tự động; C4 do người xác nhận | K09 | Đã chạy (dòng lệnh) |
| 2.2 | Quản trị dữ liệu | Hồ sơ nguồn → `rights_status`, kết quả cổng quyền | Cổng quyền chạy trong API trước khi sinh và trước khi xuất bản | K10 | Đã chạy |
| 2.3 | Hệ thống AI | Ảnh 512 → Canny, bảng màu | Ngưỡng C2 = 60% mốc | K09 | Đã chạy |
| 2.4 | Hệ thống AI | Canny + prompt → hoa văn phẳng | G2 | K04 | Đã chạy |
| 2.5 | Hệ thống AI | Hoa văn + áo LoRA → bản ghép, bản cuối | G3 | K01, K02, K03 | Đã chạy |
| 2.6 | Hệ thống | Kết quả lần chạy → Passport | Trạng thái do cổng đặt, không bao giờ là "đã phê duyệt" | K11 | Đã chạy |

#### Nhóm 3. Quản lý chất lượng (PCF 13.3)

| Mã | Quy trình | AS-IS | Điểm nghẽn, rủi ro | TO-BE | Giá trị cải tiến |
|---|---|---|---|---|---|
| 3.1 | Kiểm thử chất lượng hình ảnh | Không có | Ảnh mờ, lệch màu không bị phát hiện | G3: độ nét so với bản ghép, lệch màu ΔE | Phát hiện lỗi kỹ thuật trước khi người xem |
| 3.2 | Kiểm tra toàn vẹn họa tiết và dáng áo | CLIP hoa văn với ảnh gốm | Không đo trên áo | G3: PPS (giữ họa tiết), IoU dáng áo | Đo đúng chỗ BTC yêu cầu |
| 3.3 | Đánh giá phù hợp văn hoá | Không có | Biểu tượng dùng sai ngữ cảnh | Chuyên gia di sản chấm mù 5 tiêu chí, ghi lý do | Văn hoá do người có chuyên môn quyết định |
| 3.4 | Phê duyệt hoặc yêu cầu tạo lại | Không có | – | Phiếu chuyên gia: duyệt / sửa / loại; hệ thống cảnh báo nếu "duyệt" mâu thuẫn với điểm | Không duyệt nhầm thiết kế điểm thấp |

| Mã | Chủ | Đầu vào → Đầu ra | Điểm kiểm soát | KPI | Triển khai |
|---|---|---|---|---|---|
| 3.1 | Hệ thống, QC Officer | Bản ghép + bản cuối → kết quả G3 | Ngưỡng trong `config/quality_gate.json` (tạm thời) | K01 | Đã chạy |
| 3.2 | Hệ thống, QC Officer | như trên | PPS, IoU | K02, K03 | Đã chạy |
| 3.3 | Chuyên gia di sản | Thiết kế ẩn danh + ảnh hiện vật → phiếu chấm | Chấm mù; tiêu chí "phù hợp văn hoá" ≥ 4 | K05, K06 | Đã chạy (form + API), chưa có phiếu thật |
| 3.4 | Chuyên gia di sản | Phiếu → trạng thái phê duyệt | Chỉ nhận phiếu khi thiết kế đã qua cổng/QC | K14 | Đã chạy |

#### Nhóm 4. Tri thức và thông tin (PCF 13.5; 8.0)

| Mã | Quy trình | AS-IS | Điểm nghẽn, rủi ro | TO-BE | Giá trị cải tiến |
|---|---|---|---|---|---|
| 4.1 | Quản lý dữ liệu hiện vật | Hai tệp siêu dữ liệu lệch nhau | Không biết bản nào đúng | Một tệp `data/heritage/metadata.json` schema 2.0; bản cũ lưu trữ | Một nguồn sự thật |
| 4.2 | Quản lý nguồn tham khảo | URL trong tệp Word | Không có ghi công chuẩn | Danh mục nguồn, câu ghi công, cờ rà soát | Ghi công đúng mỗi khi hiển thị |
| 4.3 | Quản lý phiên bản thiết kế | Ghi đè tệp | Mất bản cũ | Thư mục riêng mỗi lần chạy; phiên bản v1, v2… có mã băm cha | Tái lập được |
| 4.4 | Quản lý Design Passport | 4 trường | Không chứng minh được gì | Passport đầy đủ + sổ cái băm nối chuỗi | Phát hiện sửa trái phép |
| 4.5 | Lưu lịch sử chỉnh sửa | Không có | – | Ghi ai, lúc nào, công cụ, nội dung, băm trước/sau | Minh bạch phần do người làm |

| Mã | Chủ | Đầu vào → Đầu ra | Điểm kiểm soát | KPI | Triển khai |
|---|---|---|---|---|---|
| 4.1 | Quản trị dữ liệu | Hồ sơ hiện vật → mục danh mục | Kiểm tra 10 trường bắt buộc | K09 | Đã chạy |
| 4.2 | Quản trị dữ liệu | URL, giấy phép → câu ghi công | Hiển thị cảnh báo khi thiếu trường | K09 | Đã chạy |
| 4.3 | Hệ thống | Lần chạy → manifest + ảnh | SHA-256 đầy đủ trong manifest | K11 | Đã chạy |
| 4.4 | Hệ thống | Sự kiện → sổ cái | Băm nối chuỗi, có hàm kiểm tra | K11 | Đã chạy |
| 4.5 | Nhà thiết kế | Ảnh sửa → phiên bản mới | Bắt buộc khai báo nội dung sửa | K11 | Đã chạy |

#### Nhóm 5. Khách hàng và bên liên quan (PCF 6.0, 12.0)

| Mã | Quy trình | AS-IS | Điểm nghẽn, rủi ro | TO-BE | Giá trị cải tiến |
|---|---|---|---|---|---|
| 5.1 | Quản lý người dùng | Không có tài khoản | Không phân biệt ai được ghi | Khoá ghi (`TSDS_WRITE_KEY`) cho thao tác ghi; tài khoản theo vai trò là kế hoạch | Ngăn ghi trái phép khi chạy công khai |
| 5.2 | Quản lý chuyên gia thẩm định | Không có | – | Mã người chấm, đồng ý lưu tên, chấm mù, ít nhất 3 người cho thí nghiệm | Giữ được tính độc lập của phiếu |
| 5.3 | Tiếp nhận phản hồi | Không có | – | Phiếu chuyên gia có nhận xét; phản hồi người dùng (kế hoạch) | Có dữ liệu để cải tiến |
| 5.4 | Cải tiến sản phẩm từ kết quả đánh giá | Không có | Ngưỡng đặt theo cảm tính | Hiệu chỉnh ngưỡng cổng theo mức đồng thuận với chuyên gia khi đủ ≥ 30 phiếu | Ngưỡng có cơ sở |

| Mã | Chủ | Đầu vào → Đầu ra | Điểm kiểm soát | KPI | Triển khai |
|---|---|---|---|---|---|
| 5.1 | Quản trị viên | Yêu cầu ghi → chấp nhận/từ chối | Khoá ghi, giới hạn 6 lần sinh/giờ | – | Một phần |
| 5.2 | Quản trị viên | Danh sách chuyên gia → gói chấm | Gói chấm không chứa mã biến thể | K06 | Đã chạy |
| 5.3 | BA | Phiếu, phản hồi → tổng hợp | – | K15 | Một phần |
| 5.4 | BA, QC Officer | Phiếu chuyên gia + kết quả cổng → ngưỡng mới (phiên bản cấu hình mới) | Ngưỡng mới là bản cấu hình mới, không sửa đè | K05 | Kế hoạch (chờ phiếu) |

## Đối chiếu với tài liệu "Quy trình mua hàng"

| Thành phần trong tài liệu mua hàng | Cách áp dụng ở đây |
|---|---|
| 6 mục tiêu quản trị chung | 6 mục tiêu M1–M6 |
| 5 nguyên tắc vận hành (nội dung, vì sao, mục tiêu) | 5 nguyên tắc giữ đúng cột |
| "Một mã định danh đi suốt chuỗi" (PR → PO) | Mã hiện vật → mã lần chạy → mã Passport → phiên bản |
| "Kiểm soát tại cổng, do hệ thống thực thi" | Cổng C1–C4, quyền, G2, G3, xuất bản là mã chạy được |
| "Giá trị quyết định cấp duyệt, không quyết định luồng" | "Điểm số quyết định chuyển tiếp, không quyết định phê duyệt" |
| Logic 3 lớp: cơ sở thiết kế → cách thực hiện → sản phẩm bàn giao | Giữ nguyên ba lớp A, B, C |
| 5 luồng E2E kèm điểm yếu và số điểm kiểm soát | 5 luồng L-1 đến L-5 |
| Danh mục L3 gắn rủi ro, kiểm soát | Bảng L3 theo 5 nhóm, có chủ, đầu vào/đầu ra, KPI |

## Nguồn

- [APQC Process Classification Framework (PCF) Cross-Industry, PDF Version 7.4](https://www.apqc.org/resource-library/resource-listing/apqc-process-classification-framework-pcf-cross-industry-pdf-12)
- [APQC: Quality Key Benchmarks, mô tả nhóm 13.3 Manage enterprise quality](https://www.apqc.org/resource-library/resource-listing/quality-key-benchmarks-cross-industry)
- [Hướng dẫn dùng APQC PCF, ghi nhận bản 7.4 (08/2024) và 8.0 (02/2026)](https://resources.rework.com/libraries/process-management/apqc-process-classification-framework)
- Tài liệu "Quy trình mua hàng" (nhóm cung cấp) — chỉ mượn cấu trúc.
