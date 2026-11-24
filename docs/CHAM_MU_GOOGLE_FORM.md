# Chấm mù bằng Google Form

Công cụ: `scripts/eval/build_google_form.py`. Nó dựng ảnh và mã Google Apps Script để tự tạo Google Form chấm mù cho một thí nghiệm. Mặc định dùng thí nghiệm EXP-A (`outputs/experiments/EXP-A`).

## Hai lượt khảo sát tách biệt

Hai lượt có mục đích khác nhau, dựng bằng cùng một công cụ, **không gộp điểm vào một thống kê**.

| | Cộng đồng (`--audience community`, mặc định) | Chuyên gia (`--audience expert`) |
|---|---|---|
| Mục đích | Điểm số để thống kê, so các trọng số | Nhận xét chuyên môn và quyết định |
| Người chấm | Nhiều người, không cần chuyên môn | Ít nhất 1 chuyên gia di sản, 1 chuyên gia thiết kế |
| Số thiết kế | 48 ảnh (6 hiện vật x 4 trọng số x seed 42 và 7) | 12 ảnh (6 hiện vật x trọng số 0,85 và 0,25, seed 42) |
| Số form | 1 | 2, dùng chung ảnh: bản di sản, bản thiết kế |
| Câu hỏi | Lưới thang 1 đến 5, 4 tiêu chí | Lưới chỉ có tiêu chí thuộc vai, quyết định Đạt, Cần chỉnh sửa hoặc Loại, ô nhận xét, thông tin người thẩm định |
| Thư mục kết quả | `outputs/review/google_form_EXP-A/` | `outputs/review/google_form_EXP-A_expert/` |

**Vì sao 12 ảnh của lượt chuyên gia.** Quy tắc đặt trước: mỗi hiện vật lấy hai trọng số cực đoan (0,85 bám mảng phẳng nhất, 0,25 tự do nhất), cùng seed 42 là seed của bộ demo. Chọn theo mức trọng số, không chọn theo ảnh đẹp hay xấu, nên không thể bị nói là chọn ảnh để khoe. Kết quả cổng G2 của 12 ảnh: 1 loại (LR3D_124 ở 0,85), 5 cảnh báo, 6 đạt. Ảnh bị cổng loại vẫn cho chuyên gia chấm để đo cổng có đồng ý với người không. Muốn thêm ảnh, dùng `--levels 0.85,0.45,0.25`.

**File Word.** Lệnh `--audience expert` còn xuất hai file Word trong `outputs/review/google_form_EXP-A_expert/docx/`: `Phieu_chuyen_gia_di_san.docx` và `Phieu_chuyen_gia_thiet_ke.docx` (mã: `scripts/eval/build_expert_docx.py`, cần thư viện `python-docx`). Mỗi thiết kế một trang A4: ảnh ghép, bảng chấm bằng ô tích bấm được, quyết định, ô nhận xét. Đầu file có thông tin người thẩm định, cuối file có hai câu góp ý chung. Gửi file Word cho chuyên gia, họ điền rồi gửi lại. Dặn chuyên gia mở bằng Microsoft Word trên máy tính, vì Word web, Google Docs và WPS có thể không bấm được ô tích. Mỗi ô tích mang thẻ ẩn dạng `mã|tiêu chí|điểm` để đọc kết quả tự động sau này. Chạy riêng bước Word từ gói đã dựng: `uv run python scripts/eval/build_expert_docx.py`.

**Phiếu cho một người (`--audience expert --single`).** Khi chỉ gửi cho một chuyên gia, ví dụ một giảng viên khoa du lịch, dùng cờ `--single`. Chỉ có **một** file Word `Phieu_chuyen_gia.docx` trong `outputs/review/google_form_EXP-A_expert_single/docx/`, chấm đủ 4 tiêu chí (không tách vai di sản, thiết kế) và **không có hàng quyết định Đạt, Cần chỉnh sửa, Loại**. Việc loại ảnh do cổng chất lượng của hệ thống lo, người thẩm định chỉ chấm điểm và viết nhận xét. Vẫn 12 ảnh như trên.

Bản di sản chấm "nhận ra họa tiết gốc" và "phù hợp văn hóa". Bản thiết kế chấm "thẩm mỹ" và "toàn vẹn dáng áo dài". Tiêu chí lấy từ trường `owner` trong `config/expert_rubric.json`.

## Mỗi câu hỏi gồm gì

Một trang cho mỗi thiết kế. Trang có một ảnh ghép và một bảng chấm điểm.

Ảnh ghép đi theo chuỗi:

1. Đầu vào: mảng hoa văn đã ép phẳng (`data/heritage/panels/`). Đây là thứ duy nhất AI nhận vào.
2. Hoa văn do AI sinh ra (`*__pattern.png` trong thư mục thí nghiệm).
3. Áo dài kết quả (`*__final.png`).

Ảnh bình gốm (`data/heritage/cutouts/`) nằm ở góc trên phải, khung nét đứt, nhãn "tham chiếu". Nó chỉ để người chấm đối chiếu xem họa tiết có nhận ra được không, không nối mũi tên và không phải đầu vào.

Bảng chấm điểm là lưới thang 1 đến 5. Các hàng là tiêu chí lấy từ `metrics.human` trong đặc tả thí nghiệm, nội dung câu hỏi lấy từ `config/expert_rubric.json`. Với EXP-A có 4 tiêu chí: nhận ra họa tiết gốc, phù hợp văn hóa, thẩm mỹ, toàn vẹn dáng áo dài.

## Cách giữ tính mù

- Người chấm chỉ thấy mã ảnh dạng `B1234`. Ảnh không ghi trọng số, seed hay tên tệp gốc.
- Thứ tự các thiết kế xáo ngẫu nhiên cố định, nên hai thiết kế cùng hiện vật hiếm khi đứng liền nhau. Với `--rotate`, mỗi form chỉ có một thiết kế cho mỗi ô và seed xoay theo form.
- Mỗi người chỉ nhận một đường link.
- `key.csv` là khóa giải mã (mã ảnh, hiện vật, trọng số, seed, bản, vai). Chỉ nhóm giữ.
- Với chuyên gia: không nói ảnh nào ứng với trọng số nào, và không nói cổng chất lượng đã loại hay cảnh báo ảnh nào.

## Cách chạy

```powershell
uv run python scripts/eval/build_google_form.py
uv run python scripts/eval/build_google_form.py --audience expert
```

Mặc định dựng **một form** chứa mọi thiết kế của seed 42 và 7: 6 hiện vật x 4 trọng số x 2 seed = 48 thiết kế, 48 ảnh. Cả nhóm điền chung một link, mỗi người chấm hết 48 ảnh (khoảng 45 phút). Thêm seed bằng `--seeds 42,7,123` (mỗi seed thêm 24 ảnh). Muốn chia nhiều form, mỗi form 24 ảnh, thêm `--rotate`.

Kết quả nằm ở `outputs/review/google_form_EXP-A/` (thư mục này đã bị git bỏ qua). Làm tiếp theo `HUONG_DAN.md` trong thư mục đó: tải ảnh lên Drive, dán `Code.gs` vào script.google.com, chạy `createForms`, nhận link.

## Nhập kết quả vào repo

Sau khi thu phiếu, vào tab Câu trả lời của form, tải bảng Excel (.xlsx), đặt cạnh `key.csv` của gói form, rồi chạy:

```powershell
uv run python scripts/eval/import_google_form.py outputs/review/google_form_EXP-A/danh_gia_28_nguoi.xlsx
```

Script `scripts/eval/import_google_form.py` làm bốn việc:

1. Đổi bảng Excel thành `outputs/experiments/EXP-A/blind/key.csv` và `ratings_N01.csv`, `N02`, ... (người chấm đánh số theo thứ tự trong file, không lưu họ tên hay giờ nộp). Lần nhập sau xóa phiếu của lần trước.
2. Chạy `analyze` của `tsds/evaluation/experiment.py`: điểm trung bình theo mức và Krippendorff alpha ghi vào `summary.json`. Phần chỉ số tự động trong `summary.json` giữ nguyên.
3. Ghi `human_report.json`: người chấm gần như một mức (độ lệch chuẩn dưới 0,3), kiểm định Friedman và Wilcoxon trên điểm trung bình 4 tiêu chí, alpha khi bỏ nhóm người đó, alpha sau khi trừ mức dễ hay khó của từng người.
4. In tóm tắt ra màn hình.

Thí nghiệm khác EXP-A thì thêm `--exp`. Test: `tests/test_import_google_form.py`.

Kết quả EXP-A với 28 người (nộp 22 đến 23/11/2026, mọi người chọn "Người quan tâm"): alpha 0,028, thấp hơn nhiều mục tiêu 0,667. Vì vậy điểm trung bình chưa dùng để kết luận từng thiết kế. Chi tiết ở `docs/finals/06_EXPERIMENTS.md`.

## Giới hạn

- Google Form không tự xáo thứ tự ảnh theo từng người. Dùng nhiều bản để cân bằng thứ tự.
- Form chuyên gia thu họ tên, đơn vị, email. Giữ tệp kết quả trong `outputs/` (git bỏ qua), không đăng công khai.
- Câu quyết định Loại hoặc Cần chỉnh sửa không tự bắt buộc ghi lý do (Google Form không hỗ trợ điều kiện): tiêu đề ô nhận xét có nhắc.
- Mã Apps Script chưa chạy thử trên tài khoản Google thật khi viết tài liệu này.
