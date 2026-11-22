# 01. Rà soát hiện trạng (bản 09/2026, trước cải tiến)

Phạm vi: chỉ phục vụ vòng chung kết. Đối tượng rà soát là mã nguồn và dữ liệu nhóm nộp tháng 09/2026 (bản gốc nằm trong lịch sử repo), cùng ba yêu cầu cải tiến của Ban tổ chức (BTC).

Mỗi phát hiện dưới đây có bằng chứng là tệp trong repo. Không phát hiện nào dựa trên ước đoán.

Lưu ý: tài liệu này mô tả bản 09/2026 nên các số liệu là số liệu lịch sử. Ngày 19/11/2026 nhóm xoá khỏi cây làm việc mọi ảnh và Passport dựng trên áo mẫu cố định (24 thiết kế của bản 06/09/2026), vì nhóm chỉ dùng ảnh do LoRA sinh. Dữ liệu đó khôi phục được từ commit `b1192b0`. Kết quả của bản hiện tại ở [05](05_QUALITY_ASSURANCE.md).

## Kết quả rà soát

| Mã | Hiện trạng | Bằng chứng | Hệ quả | Yêu cầu BTC | Xử lý ở bản chung kết |
|---|---|---|---|---|---|
| A1 | Chỉ đo hoa văn trung gian: độ tương đồng CLIP giữa hoa văn và ảnh gốm. Thiết kế áo dài cuối cùng không được đo. Cột "aesthetic" là CLIP proxy, không phải mô hình thẩm mỹ LAION. | bản nộp 09/2026: cột `similarity_pattern_vs_ceramic`, `aesthetic_impl = clip_proxy_NOT_laion` | Không biết img2img có phá họa tiết hay dáng áo không. | 1 | Cổng G3 đo thiết kế cuối (`quality/`), xem [05](05_QUALITY_ASSURANCE.md) |
| A2 | Lượt img2img strength 0,40 chạy trên toàn ảnh, không kiểm tra sau đó. | Đo lại 24 thiết kế (số liệu lịch sử, commit `b1192b0`): 20/24 có PPS < 0,40 | Họa tiết bị vẽ lại ở phần lớn thiết kế. | 1 | Polish chỉ vùng áo độ nhiễu 0,20, khoá họa tiết, cổng G3 (kể cả chỉ số giữ chi tiết mịn), vòng thử lại; thí nghiệm EXP-B |
| A3 | Hoa văn có thể là ảnh nguyên chiếc bình đặt trên nền trơn thay vì hoa văn phẳng. | Bản nộp 09/2026, hai biến thể V1, V2 của một hiện vật: VLS 0,56 và 0,67 | Áo dài in hình cái bình. | 1 | Cổng G2 đánh dấu và gợi ý sinh lại (chưa tự động); mặc định nạp mảng hoa văn phẳng thay cho ảnh bình (EXP-E) |
| A4 | Bốn biến thể V1–V4 đổi cùng lúc bốn yếu tố: trọng số ControlNet (0,85→0,25), cụm từ prompt theo mức, bảng màu (V1 giữ màu gốc), bố cục do CLIP chọn. Chỉ chạy một seed (42). | bản nộp 09/2026: các cột `controlnet_weight`, `positive_prompt`, `palette_mode`, `layout`, `seed` | Không quy được khác biệt cho trọng số ControlNet; không biết dao động do seed. | 2 | Module thí nghiệm đơn biến, nhiều seed, chấm mù ([06](06_EXPERIMENTS.md)) |
| A5 | Mỗi lần gọi API ghi đè `outputs/variants/<id>_V<n>_aodai.png`. Mã băm thiết kế bị cắt còn 16 ký tự. | `tsds/pipeline/run.py` bản gốc; cột `sha256_design` | Không tái lập được ảnh của một lần chạy cũ; không đối chiếu được toàn vẹn tệp. | 3 | Mỗi lần chạy có thư mục riêng `outputs/runs/R<thời điểm>-<mã>/`, SHA-256 đầy đủ |
| A6 | Design Passport là cửa sổ 4 trường, không có phiên bản, lịch sử chỉnh sửa, phê duyệt hay nhãn AI. | `archive/web_ui_2026-09/components/overlays/modals.html` | Không chứng minh được thiết kế đi từ nguồn nào, ai sửa gì. | 3 | Passport có sổ cái băm nối chuỗi, phiên bản, nhãn AI ([07](07_PROVENANCE_COPYRIGHT.md)) |
| A10 | Giao diện là một trang trình diễn kèm cửa sổ bật lên; không có màn hình kiểm định, thẩm định, thí nghiệm, nguồn gốc. | `archive/web_ui_2026-09/` | Không thể hiện được vai trò QC, chuyên gia, dữ liệu. | 1–3 | Giao diện mới, nay rút gọn còn 3 trang cho người xem ([09](09_ARCHITECTURE_UI.md)) |
| A11 | `make_template` trong `tsds/generation/garment/garment.py` dùng hằng chưa khai báo (`PANEL_FILE`, `DEFAULT_PANEL`). | `tsds/generation/garment/garment.py` bản gốc | Lỗi khi gọi tạo mẫu áo. | – | Đã sửa, không đổi hành vi mặc định |
| A12 | Không có kiểm thử tự động. | Không có thư mục `tests/` | Nâng cấp dễ làm hỏng chức năng cũ mà không biết. | – | Bộ pytest chức năng và hồi quy ([10](10_TEST_REPORT.md)) |
| A13 | Giao diện cũ hiển thị 4 giá trị "Similarity" viết cứng (88,4% / 76,2% / 68,5% / 54,1%) thay vì số đo thật; chèn dữ liệu API bằng `innerHTML`. | `archive/web_ui_2026-09/assets/js/ui/curate.js` | Số liệu trình diễn không khớp dữ liệu; rủi ro chèn mã. | 1 | Giao diện mới chỉ đọc số từ dữ liệu; có ca kiểm thử chặn số viết cứng và `innerHTML` |

## Những gì giữ nguyên

- Kiến trúc hai giai đoạn: SD 1.5 + ControlNet Canny sinh hoa văn phẳng, ghép tất định lên áo dài, hoàn thiện bằng img2img. Phần thay đổi: áo nền do LoRA sinh thay cho áo mẫu cố định, ảnh nạp là mảng hoa văn phẳng, polish chỉ vùng áo kèm khoá họa tiết.
- Các endpoint cũ (`/health`, `/heritage`, `/heritage/{id}`, `/media/heritage/{id}`, `/generate`, `/generate/{job}`, `/audit`) giữ nguyên đường dẫn và dạng trả về; chỉ bổ sung trường mới. Riêng `/media/variant/{f}` đã bỏ ngày 19/11/2026 vì thư mục `outputs/variants/` không còn.
- Giao diện cũ được lưu trữ ở `archive/web_ui_2026-09/` để đối chiếu trước/sau.
