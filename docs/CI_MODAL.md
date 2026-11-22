# Kiểm tra CI cho backend Modal

Workflow `Modal backend checks` chạy khi mở pull request, push lên `main` với các tệp backend/gateway liên quan, hoặc bấm chạy thủ công trong GitHub Actions. Nó chỉ dùng CPU và mock backend; không gọi Modal, không tải model và không tiêu GPU credit.

| Kết quả | Việc cần làm |
| --- | --- |
| `API, queue and Modal package` đỏ | Xem bước thất bại: cú pháp/đóng gói, endpoint và Passport, khóa API, hàng đợi hoặc worker. Sửa rồi chạy lại trước khi deploy Modal. |
| `Vercel gateway and live session` đỏ | Kiểm tra giao tiếp gateway với API mock, failover và khả năng nối lại job sau khi rời trang. Không coi luồng live là đã sẵn sàng. |
| Cả hai xanh, mã backend thay đổi | Xem `Next action` trong run. Người vận hành quyết định `modal deploy modal_app.py` sau khi kiểm tra workspace, secret `DH_API_KEY`, Spend limit và bản cần phát hành. Sau deploy, thử `/health`, một job sinh 4 ảnh và đường dẫn ảnh qua Vercel. |
| Cả hai xanh, chỉ gateway/test thay đổi | Vercel tự cập nhật từ `main`; không cần deploy lại Modal nếu mã và cấu hình backend không đổi. |

CI không xác nhận GPU, model tải được, Modal Volume hoặc credit. Bài thử live sau deploy mới xác nhận các phần đó. Nếu live lỗi, xem log Modal và gateway; giao diện có thể dùng dữ liệu demo theo cơ chế dự phòng đã thiết kế. Không đưa khóa API vào workflow hoặc log.
