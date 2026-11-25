# Báo cáo cải tiến (LaTeX, đưa lên Overleaf)

Thư mục này là một dự án LaTeX của báo cáo cải tiến Tái sinh Di sản Số. **Toàn bộ nội dung nằm trong một tệp `main.tex`**, không chia chương thành tệp riêng. Hình nằm trong `figures/`.

## Đưa lên Overleaf

1. Nén cả thư mục `docs/report` thành một tệp `.zip` (gồm `main.tex`, `latexmkrc`, `figures/`).
2. Trên Overleaf: New Project, Upload Project, chọn tệp zip.
3. Tệp chính là `main.tex`. Trình biên dịch phải là **XeLaTeX** (Menu, Compiler). Tệp `latexmkrc` và dòng `% !TEX program = xelatex` đầu `main.tex` đã đặt sẵn, nhưng nếu Overleaf vẫn dùng pdfLaTeX thì đổi tay.
4. Bấm Recompile.

Phông chữ dùng TeX Gyre Termes, TeX Gyre Heros và Latin Modern Mono, đều có sẵn trên Overleaf và có đủ dấu tiếng Việt. Dự án chưa được biên dịch thử trên máy này vì máy chưa cài LaTeX. Nếu Overleaf báo lỗi, gửi lại dòng lỗi để sửa.

## Cấu trúc của main.tex

Các phần cách nhau bằng dòng chú thích `% CHƯƠNG ...` (tìm bằng Ctrl+F).

| Phần | Nội dung |
|---|---|
| Đầu tệp | Gói lệnh, các lệnh dùng chung (`\hinh`, `\hinhngang`, `\hinhrong`, `\hinhcao`, `\chuahoanthien`), trang bìa, mục lục |
| Tóm tắt | Bảng ba yêu cầu của ban tổ chức |
| Chương 1 | Bối cảnh và mục tiêu |
| Chương 2 | Pipeline AI sinh ảnh thiết kế |
| Chương 3, 4, 5 | Ba cải tiến theo yêu cầu của ban tổ chức: đánh giá thiết kế cuối; đối chứng nhiều seed và chấm mù; nguồn gốc, bản quyền, truy vết |
| Chương 6 | Giới hạn và hướng tiếp theo |
| Phụ lục A | Phân tích và thiết kế hệ thống: use case, BPMN, kiến trúc thành phần, mô hình dữ liệu Design Passport, trạng thái phê duyệt |
| Phụ lục F | Khoảng trống quy trình và đề xuất cải tiến |
| Cuối tệp | Tài liệu tham khảo |

## Phần chưa hoàn thiện

Phần nào chưa hoàn thiện đều hiện **khung vàng** có chữ **[CHƯA HOÀN THIỆN]** trong bản PDF, kèm việc cần làm. Tìm trong mã nguồn bằng từ khóa `chuahoanthien`.

Hình chưa có không làm hỏng bản dịch: lệnh `\hinh` hiện khung vàng thay thế. Đặt đúng tên tệp vào thư mục `figures/` là hình tự hiện, không cần sửa `.tex`. Các hình còn thiếu:

| Tệp cần thêm | Nội dung |
|---|---|
| `figures/ui/trang_chu.png` | Ảnh chụp trang Trang chủ |
| `figures/ui/studio.png` | Ảnh chụp trang Studio |
| `figures/ui/ket_qua.png` | Ảnh chụp trang Kết quả |
| `figures/ui/thiet_ke_da_tao.png` | Ảnh chụp trang Thiết kế đã tạo |
| `figures/ui/chinh_sua.png` | Ảnh chụp trang chỉnh sửa |
| `figures/ui/hop_xac_nhan.png` | Ảnh chụp hộp xác nhận khi lưu |
| `figures/diagrams/component.png` | Sơ đồ thành phần |
| `figures/diagrams/class_passport.png` | Sơ đồ lớp của Design Passport |
| `figures/diagrams/state_approval.png` | Sơ đồ trạng thái phê duyệt |
| `figures/diagrams/sequence_tao_thiet_ke.png` | Sơ đồ tuần tự: tạo thiết kế |
| `figures/diagrams/sequence_chinh_sua.png` | Sơ đồ tuần tự: tải bản chỉnh sửa |
| `figures/diagrams/deployment.png` | Sơ đồ triển khai |

## Hình đã có

| Thư mục | Nội dung |
|---|---|
| `figures/pipeline/` | 11 ảnh các bước pipeline của một lần chạy thật (không có chữ trong ảnh) |
| `figures/passport/lan1/` | Các đoạn của một Design Passport trước khi sửa tay |
| `figures/passport/lan2/` | Các đoạn của cùng Passport sau khi sửa tay, ảnh trước và sau, mã băm |
| `figures/design/` | Ảnh tải về từ giao diện, có nhãn AI và nhãn Đã chỉnh sửa |
| `figures/diagrams/` | Use case AS-IS (`uc_as_is.png`, kèm `.puml`), bản đồ quy trình BP-00, và bốn quy trình BP-01, BP-01a, BP-02, BP-03, BP-04 (đều là hệ thống đúng như mã đang chạy) |

Hình Passport là ảnh vẽ lại từ nội dung tệp JSON bằng `scripts/docs/build_passport_snippets.py`. Hình pipeline do `scripts/docs/build_pipeline_figure.py` tạo. Sơ đồ use case và BPMN lấy từ `docs/business-analysis/diagrams/` (sinh bằng công cụ trong `docs/business-analysis/tools/`); các bản TO-BE (đề xuất) không đưa vào báo cáo.

## Nguồn dữ liệu

Số liệu của báo cáo lấy từ Design Passport, kết quả thí nghiệm và tài liệu triển khai trong kho mã. Số liệu có ngày tháng được ghi ngay trong câu. Khi dữ liệu đổi (ví dụ có thêm phiếu chuyên gia), cập nhật phần tương ứng trong `main.tex`.
