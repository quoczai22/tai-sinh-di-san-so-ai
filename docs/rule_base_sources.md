# Mapping mã nguồn (SRC) — Source-Grounded Cultural Rule Base

> File này là **nguồn sự thật duy nhất** cho ánh xạ `rule_sources` trong `data/rule_base.json`.
> Mọi mã `SRCxxx` xuất hiện trong `rule_base.json` PHẢI có một dòng tương ứng ở đây, và file
> tài liệu tương ứng PHẢI tồn tại trong `data/documents/`.
>
> Cập nhật lần cuối: 31/08/2026 (bổ sung SRC005, SRC006 sau vòng rà soát tài liệu chưa gán mã).

---

## 1. Bảng mã nguồn đang được sử dụng

| Mã | File trong `data/documents/` | Tác giả | Năm / ngày đăng | Nguồn gốc |
|---|---|---|---|---|
| **SRC001** | `Sưu tập đồ gốm men rạn Bát Tràng có minh văn.pdf` | TS. Nguyễn Đình Chiến | 22/04/2019 | [baotanglichsu.vn](https://baotanglichsu.vn/vi/Articles/3101/70736/suu-tap-djo-gom-men-ran-bat-trang-co-minh-van.html) |
| **SRC002** | `Gia đình tượng nhân Đỗ Phủ lưu danh trên gốm Bát Tràng thế kỷ 16 -17.pdf` | TS. Nguyễn Đình Chiến | 21/02/2019 | [baotanglichsu.vn](https://baotanglichsu.vn/vi/Articles/3101/69631/gia-djinh-tuong-nhan-djo-phu-luu-danh-tren-gom-bat-trang-the-ky-16-17.html) |
| **SRC003** | `Chỉ dấu niên đại trên gốm Bát Tràng thế kỷ 16 - 18.pdf` | TS. Nguyễn Đình Chiến | 06/09/2022 | [baotanglichsu.vn](https://baotanglichsu.vn/vi/Articles/3101/73367/chi-dau-nien-djai-tren-gom-bat-trang-the-ky-16-18.html) |
| **SRC004** | `14.pham-thi-oanh_ma_20122023162629.pdf` | Phạm Thị Oanh (Viện Nghiên cứu Kinh thành) | 2023, số 11(191), tr.104-114 | Tạp chí Khoa học xã hội Việt Nam — DOI `10.56794/KHXHVN.11(191).104-114` |
| **SRC005** | `Gốm cổ Bát Tràng trưng bày tại Bảo tàng Lịch sử quốc gia.pdf` | Tường Long (BTLSQG) | 07/06/2023 | [baotanglichsu.vn](https://baotanglichsu.vn/vi/Articles/3096/73977/gom-co-bat-trang-trung-bay-tai-bao-tang-lich-su-quoc-gia.html) |
| **SRC006** | `Giới thiệu sưu tập gốm Bát Tràng hiện đang được trưng bày tại Bảo tàng Lịch sử quốc gia.pdf` | Phan Thị Chiên (Phòng GDCC, BTLSQG) | 11/08/2014 | [baotanglichsu.vn](https://baotanglichsu.vn/vi/Articles/3096/16750/gioi-thieu-suu-tap-gom-bat-trang-hien-djang-djuoc-trung-bay-tai-bao-tang-lich-su-quoc-gia.html) |

**Tiêu đề đầy đủ SRC004:** *"Gốm men trắng thời Lê Trung hưng khu di tích Hoàng thành Thăng Long: Đặc trưng và giá trị"*.

### 1.1. Trọng số tin cậy của từng nguồn

Không phải mọi nguồn có sức nặng như nhau. Khi một quyết định `preserve` (BLOCK) chỉ dựa
vào nguồn nhóm B, phải ghi rõ điều đó trong `source_note`.

| Nhóm | Mã | Đặc điểm |
|---|---|---|
| **A — nghiên cứu chuyên khảo** | SRC001, SRC002, SRC003, SRC004 | Có tác giả chuyên ngành, mô tả hiện vật ở mức minh văn/kích thước, SRC004 có DOI và bình duyệt |
| **B — bài trưng bày/giới thiệu** | SRC005, SRC006 | Do bảo tàng xuất bản. SRC005 có 8 tài liệu dẫn (trong đó có Nguyễn Đình Chiến 1999 — cùng nền tảng với SRC001-003). SRC006 do Phòng Giáo dục Công chúng viết, **không có chú thích nguồn** |

**Quy tắc:** SRC006 chỉ dùng làm **nguồn củng cố**, không được là căn cứ duy nhất cho một `preserve`.

---

## 2. Tài liệu đã có nhưng CHƯA gán mã SRC

| File | Nguồn gốc | Lý do chưa gán |
|---|---|---|
| `Làng gốm Bát Tràng – Hồn đất Thăng Long trong ngọn lửa ngàn năm – Bảo tàng Hà Nội.pdf` | [baotanghanoi.com.vn](https://baotanghanoi.com.vn/lang-gom-bat-trang-hon-dat-thang-long-trong-ngon-lua-ngan-nam/) | Bài PR trưng bày. Rà toàn văn: **0 họa tiết được mô tả, 0 minh văn, 0 hiện vật định danh, 0 niên hiệu, 0 chú thích nguồn**. Không đủ tư cách chống đỡ bất kỳ quyết định preserve/modifiable nào. Chỉ dùng cho phần văn bản bối cảnh của Cultural Passport |

---

## 3. Mâu thuẫn đã biết trong tài liệu nguồn (phải giữ nguyên, không được "làm mượt")

1. **Bát bảo — Đạo giáo hay Nho giáo?**
   SRC001 thân bài: *"đề tài Bát bảo của **Đạo giáo**"*; tổng kết cùng tài liệu: *"bát bảo của **Nho giáo**"*.
   Ảnh hưởng: `BT007`.

2. **Hoa cúc — có phải biểu tượng Phật giáo?** *(đã xử lý — xem QĐ-02)*
   SRC001 tổng kết: *"hoa sen, **hoa cúc** biểu trưng của Phật giáo"*. SRC003 chỉ trình bày hoa cúc
   12 cánh nhọn như **chỉ dấu niên đại/tác giả**. Kết luận: đây là vấn đề **phạm vi phát biểu**
   chứ không phải mâu thuẫn thực sự — hai nguồn không nói về cùng một đối tượng. Ảnh hưởng: `BT010`.

3. **Bát quái không được gán tôn giáo ở bất kỳ tài liệu nào.**
   Cụm "Đạo giáo" chỉ xuất hiện 2 lần trong toàn bộ 7 tài liệu, cả 2 đều ở SRC001 và đều nói về đề tài
   khác (Bát bảo; Hà đồ - Lạc thư). SRC005 và SRC006 không nhắc tới bát quái.
   Ảnh hưởng: `BT006` (`symbolic_element` → `restricted`).

4. **Thành phần bộ tứ quý không thống nhất.**
   | Nguồn | Thành phần |
   |---|---|
   | SRC001 | tùng - cúc - trúc - mai |
   | SRC003 | tùng - cúc - trúc mai |
   | **SRC006** | **mai, lan, cúc, trúc** (dùng *lan* thay *tùng*) |

   Ảnh hưởng: `BT008`. Tên mục theo quy ước SRC001/SRC003; khi đối chiếu ảnh mẫu phải xác định
   đang dùng quy ước nào trước khi kết luận họa tiết có khớp hay không.

---

## 4. Nhật ký quyết định

### QĐ-01 — `material_texture` giữ nguyên `modifiable` (31/08/2026)

**Bằng chứng đối lập đã cân nhắc.** SRC005 khẳng định men rạn là dấu hiệu nhận dạng độc quyền
và có chủ đích của Bát Tràng:

> *"Các tài liệu gốm men cổ ở Việt Nam xác nhận **men rạn chỉ được sản xuất tại lò gốm Bát Tràng**
> từ cuối thế kỷ 16 và kéo dài tới cuối thế kỷ 19 đầu thế kỷ 20."*
>
> *"gốm men rạn Bát Tràng được **chủ động tạo ra và khống chế độ rạn**, hình dáng vết rạn thích hợp
> theo ý đồ mang tới một vẻ đẹp cổ kính, độc đáo cho sản phẩm."*

Theo đó, có cơ sở để nâng `material_texture` lên `restricted` cho các mục gốm men rạn
(BT001, BT006, BT007, BT008, BT009, BT011, BT012).

**Quyết định: KHÔNG nâng.** Chủ sở hữu Rule Base quyết định vẫn cho phép người dùng thay đổi
`material_texture` — giữ `modifiable` (ALLOW) cho toàn bộ 13 mục.

**Lý do ghi nhận:** sản phẩm đích của hệ thống là thiết kế in trên áo thun, nơi chất liệu men gốm
không được tái hiện vật lý; ràng buộc chất liệu ở đây không bảo vệ được giá trị mà tài liệu mô tả.
Bằng chứng vẫn được lưu lại ở đây để quyết định này truy ngược được, và để có thể đảo chiều
nếu phạm vi sản phẩm mở rộng sang vật phẩm gốm thật.

### QĐ-02 — `BT010.symbolic_element` trả về `modifiable` (31/08/2026)

**Tình huống.** BT010 (hoa cúc 12 cánh nhọn để mộc) từng được xếp `symbolic_element` vào
`restricted` vì hai nguồn tưởng như bất đồng:

- SRC003 khảo sát họa tiết này như **chỉ dấu niên đại/tác giả** của Đỗ Xuân Vy.
- SRC001 có câu *"hoa sen, hoa cúc biểu trưng của Phật giáo"*.

**Phân tích.** Hai phát biểu **khác phạm vi**, không thực sự đối đầu nhau:

| | Đối tượng phát biểu | Mức khảo sát |
|---|---|---|
| SRC001 | "hoa cúc" nói chung | Một vế trong câu liệt kê ở đoạn tổng kết |
| SRC003 | Đúng biến thể *12 cánh nhọn để mộc* | Một mục riêng, khảo sát 6 hiện vật mang họa tiết này |

SRC003 là nguồn **cụ thể hơn và trực tiếp hơn** cho đúng đối tượng mà BT010 mô tả.
SRC001 không khảo sát riêng biến thể 12 cánh nhọn.

**Quyết định: `symbolic_element` → `modifiable`**, gỡ `restricted`, gỡ `rule_sources`.
Chủ sở hữu Rule Base xác định hoa cúc 12 cánh nhọn để mộc không mang chức năng biểu tượng
tôn giáo trong phạm vi bộ dữ liệu này.

**Ranh giới không được vượt.** Rule Base **không** ghi mệnh đề *"hoa cúc không phải biểu tượng
Phật giáo"* — không tài liệu nào phát biểu điều đó, và viết vậy sẽ vi phạm quy tắc 3 ở mục 5.
File chỉ ghi lập luận phạm vi cùng quyết định này, để người đọc tự đánh giá được.

**Điều kiện xét lại.** Nếu tìm được nguồn khảo sát trực tiếp biến thể 12 cánh nhọn và gán cho nó
ý nghĩa Phật giáo, quyết định này phải được mở lại.

---

## 5. Quy tắc bắt buộc khi thêm/sửa rule

1. Mọi category trong `preserve` PHẢI có entry tương ứng trong `rule_sources`.
2. Mọi câu đặt trong dấu nháy đơn `'...'` ở `source_note` PHẢI là **trích dẫn nguyên văn**
   xuất hiện trong đúng file tài liệu được viện dẫn — không diễn giải, không ghép câu, không đảo thứ tự.
3. Không được suy ra khẳng định phủ định ("không mang ý nghĩa tôn giáo") từ việc tài liệu
   **không nhắc đến** ý nghĩa đó. Sự vắng mặt của ghi chú ≠ khẳng định phủ định.
4. Khi hai nguồn bất đồng → xếp category vào `restricted` (RESTRICT, cảnh báo) và ghi rõ
   mâu thuẫn trong `source_note`, thay vì chọn tùy ý một phía.
5. Không được suy ra hai hiện vật là một chỉ vì mô tả giống nhau. SRC006 mô tả một lư hương sen
   có tượng Phật Bà Quan Âm nhưng **không ghi niên hiệu**, nên không được đồng nhất với lư hương
   Vĩnh Thịnh của SRC001 (xem `source_note` của BT001).
6. `other_unclassified` KHÔNG khai báo trong từng heritage item — đây là nhãn fallback lúc
   runtime (xem spec mục 6.2), mọi giá trị ngoài 8 nhãn hoặc không map được đều rơi về đây → RESTRICT.

---

## 6. Lưu ý kỹ thuật cho pipeline ingest

**SRC006 dùng Unicode tổ hợp (NFD), khác 5 tài liệu còn lại (NFC).** Đo được 395 ký tự tổ hợp
trong văn bản trích xuất. Chuỗi hiển thị giống hệt nhau nhưng khác nhau ở mức byte, nên mọi
so khớp chuỗi và mọi phép chunk/embed sẽ **trượt âm thầm, không báo lỗi**.

Bắt buộc thêm `unicodedata.normalize('NFC', text)` vào bước cleaning trước khi chunk trong
RAG ingest pipeline, và trong mọi script đối chiếu trích dẫn.
