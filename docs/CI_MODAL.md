# Kiểm tra CI cho backend Modal

Workflow `Modal backend checks` chạy khi mở pull request, push lên `main` với các tệp backend/gateway liên quan, hoặc bấm chạy thủ công trong GitHub Actions. Nó chỉ dùng CPU và mock backend; không gọi Modal, không tải model và không tiêu GPU credit.

| Kết quả | Việc cần làm |
| --- | --- |
| `API, queue and Modal package` đỏ | Xem bước thất bại: cú pháp/đóng gói, endpoint và Passport, khóa API, hàng đợi hoặc worker. Sửa rồi chạy lại trước khi deploy Modal. |
| `Vercel gateway and live session` đỏ | Kiểm tra giao tiếp gateway với API mock, failover và khả năng nối lại job sau khi rời trang. Không coi luồng live là đã sẵn sàng. |
| Cả hai xanh, mã backend thay đổi | Xem `Next action` trong run. Người vận hành quyết định `modal deploy modal_app.py` sau khi kiểm tra workspace, secret `DH_API_KEY`, Spend limit và bản cần phát hành. Sau deploy, thử `/health`, một job sinh 4 ảnh và đường dẫn ảnh qua Vercel. |
| Cả hai xanh, chỉ gateway/test thay đổi | Vercel tự cập nhật từ `main`; không cần deploy lại Modal nếu mã và cấu hình backend không đổi. |

CI không xác nhận GPU, model tải được, Modal Volume hoặc credit. Bài thử live sau deploy mới xác nhận các phần đó. Nếu live lỗi, xem log Modal và gateway; giao diện có thể dùng dữ liệu demo theo cơ chế dự phòng đã thiết kế. Không đưa khóa API vào workflow hoặc log.

## Phát hành Modal qua AWS CodeBuild

Token Modal không được lưu trên GitHub. Cấu hình CodeBuild nằm tại `scripts/deploy/aws-modal-cd.yaml`. Build chỉ chạy khi người vận hành bấm **Start build** trong AWS Console; không có EC2 chạy liên tục hay webhook tự deploy.

1. AWS Parameter Store giữ hai `SecureString` chuẩn: `/tai-sinh-di-san-so-ai/modal-cd/token-id` và `/tai-sinh-di-san-so-ai/modal-cd/token-secret`. Dùng token Modal riêng cho CD trong đúng workspace của nhóm; không chép token cá nhân đang lưu trên máy. Chỉ role CodeBuild của stack được đọc hai parameter này.
2. Sau khi merge vào `main`, xác nhận workflow **Modal backend checks** xanh. Có thể bấm **Check before AWS Modal deploy** trên `main` để chạy lại CI và lấy link CodeBuild. GitHub không nhận token Modal hoặc thông tin đăng nhập AWS.
3. Trong AWS Console, chọn project `tai-sinh-di-san-so-ai-modal-deploy` ở region `ap-southeast-2`, bấm **Start build**. CodeBuild lấy commit mới nhất của `main`, xác nhận CI đạt cho đúng SHA, rồi `modal deploy modal_app.py` trên T4 và xác nhận app tồn tại. Nếu CI chưa đạt, build dừng trước deploy.
4. CodeBuild không gọi `/health` hoặc tạo ảnh nên không tự đánh thức GPU. Bài thử live qua Vercel chỉ làm khi nhóm chấp nhận dùng credit. Nếu deploy lỗi, xem log CodeBuild. Quay về bản trước bằng `modal app rollback tai-sinh-di-san-so-api` sau khi kiểm tra job đang chạy.
5. Stack tạo Budget toàn tài khoản AWS tại 5 USD/tháng, gửi email khi chi phí thực tế vượt 80% và 100%. Budget là **cảnh báo, không khóa cứng chi tiêu**. CodeBuild chỉ cho một build đồng thời và tối đa 30 phút mỗi build; người vận hành vẫn cần theo dõi phí AWS và Modal riêng.

Trong chat Zalo đã được phép, gửi `ci` hoặc `cd` để xem lần CI mới nhất trên `main` và link mở CodeBuild. Bot chỉ đọc GitHub Actions công khai; trạng thái CodeBuild nằm trong AWS riêng tư nên bot không đoán hoặc tuyên bố đã deploy. Bot không được cấp token AWS/Modal và không kích hoạt CD.
