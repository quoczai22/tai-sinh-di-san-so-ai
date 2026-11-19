# 10. Báo cáo kiểm thử

Chạy: `pip install -r requirements-dev.txt && pytest`. Không cần PyTorch/GPU.

Lần chạy mới nhất (tối 18/11/2026, sau khi làm lại giao diện): **130 ca, 111 đạt, 19 bỏ qua** — 19 ca kiểm tra cú pháp JS cần Node.js, máy chạy không cài Node; không ca nào lỗi.

Kết quả lần chạy trước đó ngày 18/11/2026: **123/126 ca đạt**, khoảng 9 giây (Python 3.13, FastAPI 0.163, NumPy 2.5, OpenCV 5.0, scikit-image 0.26, SciPy 1.18, Node 22 cho kiểm tra cú pháp JS).

Nguyên tắc: kiểm thử **không sửa dữ liệu thật**. Các ca ghi (thẩm định, QC, chỉnh sửa, xuất bản) chạy trên bản sao Passport trong thư mục tạm; ca cuối của `test_api.py` kiểm tra lại rằng Passport thật không đổi. Nhật ký audit được thay bằng danh sách trong bộ nhớ.

## Phạm vi

| Tệp | Số ca | Kiểm tra gì |
|---|---|---|
| `test_registry.py` | 23 | 6 hiện vật, 3 đang dùng; hiện vật ngừng dùng có lý do; báo thiếu tác giả/giấy phép/ngày thu thập; ma trận cổng quyền 10 tổ hợp; giấy phép NC chặn thương mại; phạm vi cấp phép; C1 trên ảnh thật (HV01 đạt, HV02 và HV05 không đạt, HV03 cảnh báo); mốc C2 = 20.092; bộ nạp Streamlit ẩn hiện vật ngừng dùng |
| `test_passport.py` | 13 | JSON chuẩn hoá; Passport mới hợp lệ; **5 kiểu sửa trái phép đều bị phát hiện** (sửa nội dung sự kiện, đảo thứ tự, tự đổi trạng thái thành "đã phê duyệt", đổi băm phiên bản, xoá phiếu); chỉnh sửa tạo phiên bản con; trạng thái và loại tác nhân không hợp lệ bị từ chối; 24 Passport thật hợp lệ kể cả băm tệp; không Passport nào "đã phê duyệt" mà thiếu phiếu chuyên gia; nhãn AI đọc lại được từ PNG |
| `test_quality.py` | 21 | Phân loại ngưỡng hai chiều; NaN không thành PASS; cấu hình ghi "tạm thời" và cổng không bao giờ tự phê duyệt; định tuyến 4 nhánh; PPS = 1 khi giống hệt, < 0,4 khi họa tiết bị vẽ lại; khoá họa tiết tăng PPS; đường nối: nhiễu tuần hoàn đạt, mép vỡ không đạt; độ nét phát hiện ảnh nhoè; **hồi quy**: đếm 21/1/2 (G2), 0/4/20 (G3), 10/9 (sau sửa) và đo lại 3 thiết kế thật ra đúng số đã ghi |
| `test_experiment.py` | 11 | EXP-A/B/C sinh đúng 60/36/24 lượt, khoá duy nhất; thí nghiệm GPU chỉ dùng hiện vật đang dùng; **dựng lại bộ V1–V4 cũ và xác nhận bị từ chối**; kế hoạch không đổi biến độc lập bị từ chối; thống kê mô tả và KTC; Krippendorff alpha khớp ví dụ chuẩn (0,849); Wilcoxon theo cặp; gói chấm mù không lộ mức, thứ tự khác nhau theo người chấm, không có điểm điền sẵn, dựng lại cho ra đúng gói cũ |
| `test_api.py` | 28 | **Hồi quy bản 09/2026**: `/health`, `/heritage` (đủ 10 trường cũ), `/heritage/{id}`, ảnh hiện vật, `/generate` (503 khi không có GPU, 404 với hiện vật ngừng dùng), `/generate/{job}`, `/media/variant`; giới hạn tần suất; 5 kiểu đường dẫn vượt thư mục bị chặn; mã định danh sai bị từ chối; danh sách audit; khoá ghi; QC không chuyển thiết kế FAIL; không thẩm định khi chưa qua cổng; tiêu chí lạ bị từ chối; cờ "mâu thuẫn quy tắc"; không lưu tên khi không đồng ý; chưa duyệt thì không xuất bản, quyền chưa rõ thì 403; ảnh xuất có nhãn; **chỉnh sửa thủ công chạy lại G3** (bản sửa giữ họa tiết → PASS, bản sửa làm nhoè → FAIL); tệp không phải ảnh bị từ chối |
| `test_diagrams.py` | 8 | BPMN có đủ loại phần tử bắt buộc, có error boundary và ≥ 3 message flow; có đủ lane yêu cầu; sequence flow không vượt pool, message flow chỉ giữa hai pool; mọi gateway rẽ nhánh có ≥ 2 nhánh ghi điều kiện; mọi phần tử có hình trong DI; có vòng G2 → sinh lại và vòng sửa tay → G3; Use Case có 7 tác nhân, đủ 17 ca được yêu cầu, include/extend, kế thừa tác nhân |
| `test_ingest.py` | 3 | Nạp ảnh hiện vật mới: chạy thử tách nền đúng vùng hiện vật, C3/C4 đạt với ảnh CC0 bảo tàng có niên đại, **không ghi gì vào danh mục khi chạy thử**; SHA-1 sai thì dừng; không kích hoạt mục chưa rà soát |
| `test_frontend.py` | 19 | Cú pháp 15 tệp JS (ES module); mọi trang có tệp view; dữ liệu trình diễn khớp Passport trong repo; không còn số Similarity viết cứng của giao diện cũ; không dùng `innerHTML` |

## Lỗi phát hiện nhờ kiểm thử và đã sửa

| Lỗi | Phát hiện bởi | Sửa |
|---|---|---|
| Cổng quyền hiểu phạm vi "non-commercial display" là cho phép thương mại (so chuỗi con `"commercial" in scope`) | `test_rights_gate_permission_scope` | So theo từ nguyên vẹn trong danh sách phạm vi |
| API bỏ mất 3 trường cũ (`colors`, `colorNames`, `variantImageBase`) mà giao diện cũ dùng | so sánh trường API cũ và mới | Trả lại 3 trường |
| Chỉnh sửa thủ công đưa thẳng về "chờ chuyên gia" mà không chạy G3, trái với BPMN | đối chiếu BPMN với API | `quality.assess.assess_edit`, API chạy G3 trên bản sửa |
| Sửa thẳng trạng thái phê duyệt trong tệp (không qua sổ cái) không bị phát hiện | `test_tampering_is_detected[approval]` | `verify` đối chiếu trạng thái, phiên bản, số phiếu với sổ cái |
| Hàng đợi chấm mù hiện mã Passport (chứa số biến thể V1–V4) | rà soát giao diện | Ẩn mã, xếp theo mã ẩn danh khi chấm mù |
| Trang tràn ngang 1.628 px trên màn hình 390 px | kiểm tra bằng trình duyệt tự động | Cột lưới `minmax(0, 1fr)`, giới hạn bề rộng ô nhập |
| EXP-C ghi `stage2_finish = img2img_0.40` trong khi không chạy img2img | `test_exp_c_results_and_blind_packet_hide_identity` | Cố định `stage2_finish: none`, chạy lại EXP-C (ảnh không đổi, gói chấm mù dựng lại giống hệt) |

## Chưa kiểm thử tự động

- Sinh ảnh thật trên GPU (`generation/`, `evaluation/experiment.py::run_gpu`): cần máy có GPU NVIDIA và mô hình đã tải. Kiểm thử thủ công: `python scripts/04_test_controlnet.py`, sau đó gọi `POST /generate` và kiểm tra thư mục `outputs/runs/` mới có `manifest.json` và 4 Passport hợp lệ.
- Hiển thị trên trình duyệt: kiểm tra bằng ảnh chụp tự động ở 1440 px và 390 px trong quá trình làm, chưa đưa vào pytest.
