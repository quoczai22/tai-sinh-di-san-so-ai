# 06. Báo cáo kiểm định BPMN và UML

Ngày kiểm định: 24/11/2026. Công cụ: `tools/render.py` (nạp bằng bpmn-js 17.11.1 của bpmn.io, đọc theo metamodel BPMN
2.0, ghi mọi cảnh báo khi đọc) và `tools/check.py` (kiểm tra ngữ nghĩa). Kết quả máy ghi ở `diagrams/check_report.json`.

## 1. Kiểm định BPMN

| Tệp | Nạp bpmn-js (cảnh báo) | Kiểm tra ngữ nghĩa | Pool | Lane | Message flow |
|---|---|---|---|---|---|
| BP-00 AS-IS | 0 | Đạt | 3 | 4 | 3 |
| BP-00 TO-BE | 0 | Đạt | 3 | 4 | 3 |
| BP-01 | 0 | Đạt | 2 | 3 | 2 |
| BP-01a | 0 | Đạt | 1 | 2 | 0 |
| BP-02 AS-IS | 0 | Đạt | 1 | 3 | 0 |
| BP-02 TO-BE | 0 | Đạt | 1 | 3 | 0 |
| BP-03 AS-IS | 0 | Đạt | 2 | 3 | 2 |
| BP-03 TO-BE | 0 | Đạt | 2 | 3 | 3 |
| BP-04 AS-IS | 0 | Đạt | 2 | 2 | 1 |
| BP-04 TO-BE | 0 | Đạt | 2 | 2 | 3 |

Các điểm `check.py` kiểm tra cho từng process:

| Tiêu chí | Cách kiểm |
|---|---|
| Có sự kiện bắt đầu và kết thúc | Đếm `startEvent`, `endEvent` |
| Hoàn tất được | Mọi nút đi tới được từ một sự kiện bắt đầu (kể cả qua boundary event) và tới được một sự kiện kết thúc; không nút cụt |
| Cổng có điều kiện | Cổng XOR/OR có ≥ 2 nhánh ra thì mọi nhánh có tên **và** `conditionExpression`; cổng 1 vào 1 ra bị coi là cổng trang trí |
| Cổng sự kiện | Mọi nhánh ra dẫn tới sự kiện bắt hoặc tác vụ nhận |
| Sequence flow | Không vượt pool |
| Message flow | Luôn nối hai pool khác nhau |
| Boundary event | Gắn vào tác vụ có thật |
| Có hình | Mọi nút có `BPMNShape`, mọi luồng có `BPMNEdge` |

Đối chứng với tệp cũ: `docs/finals/diagrams/tsds_as_is.bpmn` đạt; `tsds_to_be.bpmn` có 18 nhánh ra của cổng có nhãn chữ
nhưng không có `conditionExpression`. Không phải lỗi đọc tệp, nhưng điều kiện rẽ nhánh không máy đọc được.

Các phần tử BPMN được dùng và lý do (không dùng phần tử nào chỉ để sơ đồ "đủ loại"):

| Phần tử | Dùng ở | Lý do |
|---|---|---|
| Pool, Lane | Mọi sơ đồ | Tách bên tham gia và vai trò |
| Start, End, Error End Event | Mọi sơ đồ | Điểm bắt đầu, kết thúc rõ, phân biệt kết thúc lỗi |
| Conditional Start Event | BP-00, BP-03 TO-BE | Quy trình chạy khi trạng thái dữ liệu đổi |
| Message Start / End, Intermediate Message Catch | BP-03, BP-04 | Trao đổi với chuyên gia, chủ sở hữu ảnh |
| Timer Intermediate Event | BP-03 TO-BE (7 ngày), BP-04 TO-BE (14 ngày) | Hạn xử lý |
| Error Boundary Event | BP-01, BP-01a | Lỗi GPU, mọi phương án lỗi |
| User, Manual, Service, Send, Receive, Script, Business Rule Task | Theo bản chất từng bước | Phân biệt người và hệ thống; quyết định theo quy tắc dùng Business Rule Task |
| Sub-process đa thể hiện tuần tự | BP-01 | 4 phương án chạy lần lượt trên một GPU |
| Call Activity | BP-00 | Gọi các quy trình chi tiết |
| Exclusive Gateway | Mọi quyết định | Mỗi quyết định chỉ một nhánh |
| Event-based Gateway | BP-03 TO-BE, BP-04 TO-BE | Chờ "phản hồi đến" hoặc "hết hạn", cái nào đến trước |
| Data Store | Mọi sơ đồ có ghi đọc dữ liệu | Danh mục hiện vật, kho Design Passport |
| Participant multiplicity | BP-03 TO-BE | Hội đồng ≥ 2 chuyên gia |

Không dùng **Parallel Gateway** và **Inclusive Gateway**: trong mã không có bước nào chạy song song thật (4 phương án chạy
tuần tự trên một GPU, `run.py`), và không có quyết định chọn nhiều nhánh cùng lúc. Vẽ thêm hai loại cổng này sẽ mô tả
sai hệ thống.

### Kiểm tra trình bày: chữ không bị chèn

Hai công cụ đo trên hình đã dựng thật (khung chữ do trình duyệt tính, không ước lượng):

- `tools/layoutfix.py` (bpmn-js Modeler 17.11.1) cho BPMN. Đo: nhãn đè hình, nhãn đè nhãn, nhãn đè đường nối, nhãn
  đè hoặc sát đường kẻ pool/lane (chừa 5 px), hai đường nối chồng lên nhau trên cùng một đoạn, đường nối chạy dọc đường
  kẻ pool/lane, đường nối xuyên qua hình không phải điểm đầu/cuối của nó, chữ trong ô tràn khỏi ô hoặc bị biểu tượng
  loại tác vụ che. Chạy với `--fix` thì tự đặt lại nhãn ngoài vào vị trí ít đè nhất.
- `tools/ucchk.py` cho Use Case. Đo: chữ đè chữ, đường đè chữ, nền nhãn «include»/«extend» che đường khác, đường xuyên
  qua elip không phải điểm đầu/cuối, chữ tràn khỏi elip của nó, chữ đè elip hoặc hộp hệ thống ngoài khác.

Lần soát ngày 24/11/2026 tìm và sửa các lỗi sau (ô tác vụ nới thành 164 × 92, đặt lại nhãn, dời một số phần tử):

| Loại lỗi | BPMN | Use Case |
|---|---|---|
| Biểu tượng loại tác vụ che dòng chữ đầu, chữ tràn ô | Có ở nhiều ô tác vụ | Không áp dụng |
| Nhãn sự kiện, cổng, luồng đè hình, đè nhãn khác hoặc đè đường nối | Có | Không áp dụng |
| Nhãn đè đường kẻ pool/lane | Có | Không áp dụng |
| Đường liên kết dữ liệu trùng đường luồng hoặc chạy dọc vạch lane | BP-00, BP-02 | Không áp dụng |
| Kho dữ liệu nằm đè đường nối | BP-03 TO-BE | Không áp dụng |
| Tiêu đề khung hệ thống đè elip hàng đầu | Không áp dụng | Có |
| Đường nối cắt qua tên tác nhân "Nhà thiết kế" | Không áp dụng | Có |
| Hai nhãn «include» chồng nhau, đường khác chạy qua nhãn «include» | Không áp dụng | Có |

Kết quả sau khi sửa: `layoutfix.py` đo 0 chỗ trên cả 10 tệp BPMN; `ucchk.py` đo 0 chỗ trên 2 sơ đồ Use Case; ảnh PNG
được xem lại bằng mắt từng tệp.

## 2. Kiểm định Use Case

| Tiêu chí | AS-IS (báo cáo cũ) | AS-IS (mới) | TO-BE |
|---|---|---|---|
| Tác nhân nằm ngoài ranh giới | Không ("Hệ thống xử lý AI" là thành phần bên trong) | Đạt | Đạt |
| Tác nhân có hành vi khác nhau thật | Không (Khách / Người dùng đã đăng ký / Nhà thiết kế không khác hành vi) | Đạt | Đạt |
| Tổng quát hoá có căn cứ | Không | Không dùng | Đạt ("Nhân sự nội bộ" — cùng đăng nhập theo vai trò) |
| Tên ca bắt đầu bằng động từ, là mục tiêu của tác nhân | 3 ca là bước nội bộ (UC06, UC07, UC14) | Đạt | Đạt |
| Ca có chức năng thật trong mã | 3 ca không có (UC01, UC13, UC17) | Đạt (18/18) | 18 có, 3 đề xuất ghi rõ |
| Chức năng trong mã có ca | Thiếu 6 (xem `01` U06) | Đạt | Đạt |
| «include» chỉ khi luôn chạy | Đạt phần lớn | Đạt | Đạt |
| «extend» có extension point và điều kiện | Chưa ghi điều kiện | Đạt | Đạt |
| Ca chồng lấn | UC11 "So sánh phiên bản" và UC15 "Xem lịch sử" cùng xem phiên bản Passport, không có giao diện riêng | Không | Không |

## 3. Đối chiếu chéo

| Đối chiếu | Kết quả |
|---|---|
| BPMN ↔ Use Case | Mọi hoạt động BPMN có Use Case hoặc thuộc ca include (bảng ở `04`) |
| Use Case ↔ chức năng | 18/18 ca AS-IS trỏ tới route, script hoặc trang có thật |
| Chức năng ↔ mã | 22/22 route của `tsds/api/main.py` được ánh xạ tới ca hoặc ghi rõ là route đọc phụ trợ |
| Dữ liệu ↔ kho | Hai kho trong BPMN khớp tệp thật: `data/heritage/metadata.json`, `outputs/passports/*.json` |
| Số liệu | Mọi con số AS-IS có nguồn (Passport, `08_KPI.md`); con số TO-BE ghi "mục tiêu đề xuất" |

## 4. Chất lượng trước và sau

| Tiêu chí | Báo cáo cũ (mục 2, 3) | Bộ mới |
|---|---|---|
| Sơ đồ BPMN | 3 hình TO-BE | 10 sơ đồ (5 AS-IS, 5 TO-BE kể cả BP-01/01a giữ nguyên), có tệp `.bpmn` |
| Lỗi BPMN mức Cao (bảng `01` mục 6.1) | 7 | 0 |
| Vòng lặp tự động có điều kiện dừng | 0/2 | 4/4 (G2, G3, nhắc chuyên gia, nhắc chủ sở hữu ảnh) |
| Kết thúc ngoại lệ, lỗi, từ chối | 3 (Dừng xử lý, Trả về chỉnh sửa, Bị loại) | 14 ở AS-IS, 17 ở TO-BE |
| Kiểm định tự động | Không | bpmn-js + `check.py`, 0 cảnh báo, 0 lỗi |
| Tác nhân / ca sử dụng | 7 / 19 | AS-IS 5 người + 2 hệ thống ngoài / 18; TO-BE 7 người + 1 hệ thống ngoài / 21 |
| Lỗi Use Case mức Cao (bảng `01` mục 6.2) | 4 | 0 |
| Đặc tả ca sử dụng | 3 ca, 6 mục | 5 ca, đủ 16 mục |
| Ma trận truy vết | Không | Có (34 dòng) |
| Quy tắc nghiệp vụ | Rải rác | 22 quy tắc có căn cứ + 5 đề xuất |
| AS-IS / TO-BE, so sánh | Không | Có |
