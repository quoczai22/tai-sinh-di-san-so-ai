# Triển khai giao diện mới qua Vercel và Modal

Ngày cập nhật: 21/11/2026. Tài liệu này mô tả nhánh deploy/live-gateway. Backend đã triển khai trên Modal workspace doandt0612; Vercel Preview đã kiểm chứng, production chưa thay đổi.

## Quyết định

- Project Vercel chính thức: tai-sinh-di-san-so-ai. Cần kiểm tra liên kết .vercel/project.json trước khi deploy CLI từ thư mục web_ui.
- Mục tiêu là sinh trực tiếp qua Modal. Dữ liệu thật đã sinh sẵn trong web_ui/data là lớp dự phòng.
- Chỉ bật live sau khi chủ tài khoản xác nhận Spend limit = $0 trên Modal. Nếu đến 24/11 chưa nối cổng xong thì nộp bản demo.
- UptimeRobot chỉ ping /health của Vercel. Route này và /api/live/health đều chạy CPU, không đánh thức Modal.

## Luồng giao diện

1. Trang đọc web_ui/data và gọi /api/live/health. Health chỉ cho biết đã cấu hình MODAL_URL và MODAL_KEY; nó không chứng minh GPU đang chạy.
2. Khi bấm Tạo thiết kế, UI gửi POST /api/live/generate với heritage_id và seed. Gateway giới hạn 10 lượt/IP/giờ, gắn X-API-Key phía server rồi gọi Modal.
3. UI hỏi GET /api/live/generate/{job_id}?heritage_id=... cho đến khi hoàn tất hoặc quá 8 phút.
4. Nếu Modal lỗi, timeout hoặc chạm rate limit, gateway trả backend=demo. UI dùng dữ liệu đã sinh sẵn và hiện nhãn “Kết quả đã sinh sẵn — không phải sinh trực tiếp”.
5. Sau khi sinh xong, UI lấy Passport qua /api/live/passports và ảnh PNG qua /api/live/media/artifact. Gateway chỉ cho các route đọc cần thiết; các route ghi Passport/QC không được chuyển tiếp.

## Lưu ảnh

Modal gắn Volume tại /data/outputs. Docker image phải để trống đường dẫn này trước khi mount. Khi khởi động, modal_app.py nối /app/outputs tới Volume vì generation/streamlit_runner.py và api/store.py đều dùng /app/outputs. Mount và khởi động T4 đã kiểm chứng. Bốn Passport và ảnh V1 vẫn đọc được với cùng SHA-256 sau khi dừng app rồi deploy lại; chưa chờ scaledown tự động 900 giây.

Backend đặt TSDS_GENERATE_PER_HOUR=1000 mặc định để gateway kiểm soát theo IP người dùng. Giới hạn gateway là giới hạn mềm, lưu trong RAM từng Vercel Function instance.

## Biến cần cấu hình

Trên Vercel: MODAL_URL, MODAL_KEY, MODAL_TIMEOUT_MS (mặc định 25000), RATE_LIMIT_PER_HOUR (mặc định 10), ALERT_DISCORD_WEBHOOK_URL, ALERT_COOLDOWN_MIN (mặc định 30). Không đặt khóa trong frontend.

Trên Modal: secret tai-sinh-di-san-secret chứa DH_API_KEY, bằng MODAL_KEY trên Vercel. DH_REQUIRE_API_KEY được modal_app.py đặt bằng 1.

Người dùng tự nhập giá trị secret trên dashboard hoặc terminal riêng. Sau khi đổi biến Vercel phải redeploy.

## Kiểm tra chưa tốn GPU

- node scripts/test_live_gateway.js
- Đặt PYTHON_EXECUTABLE trỏ tới .venv rồi chạy node scripts/test_live_gateway_mock.js
- Python từ .venv chạy scripts/test_api_key_guard.py, scripts/test_acceptance_1_8.py, scripts/test_alert_webhook.py, scripts/test_worker_resilience.py và pytest.
- python scripts/ui_index.py rồi kiểm tra diff của web_ui/index.html.

Ngày 21/11: /health của Modal trả cuda=true, device=Tesla T4; /heritage trả 6 hiện vật; POST /generate không có X-API-Key trả 401. Preview Vercel xác nhận /health và rewrite /api/live/health, /api/live/heritage. Job qua gateway cho LR3D_61, seed 20261121, run R20261120T171657-HV08 hoàn tất 4/4; cả bốn PNG tải được qua /api/live/media/artifact, mỗi ảnh có SHA-256 khác nhau. Bốn Passport mới được trả về. V1 vẫn có SHA-256 tiền tố 46F2E2E8784D2B1F sau khi dừng rồi deploy lại Modal. Chưa đo chính xác cold start, thời gian sinh, chi phí; chưa xác nhận scaledown tự động hoặc kiểm tra tương tác trực quan trên Preview.

Sau lượt thử trên trình duyệt, phát hiện reload lúc job còn chạy làm mất job ID trong bộ nhớ trang; POST tiếp theo nhận 409 nhưng gateway gắn nhầm nhãn demo. Đã sửa gateway trả 409 rõ ràng và sessionStorage tiếp tục polling job cũ. Trình duyệt đã kiểm tra reload giữa lúc sinh rồi hoàn tất 4 ảnh không có nhãn demo trên Preview. Tiếp đó sửa việc reload trang Kết quả luôn quay lại demo: sessionStorage giữ run_id và trang Kết quả chọn đúng run của phiên. Khi health tạm chậm, trang vẫn thử đọc run đã lưu trước khi dùng demo. Bài kiểm thử `node --experimental-default-type=module scripts/test_live_session.mjs` đạt, xác nhận khôi phục run kể cả khi health lỗi và không POST thêm. Bản sửa cuối đã deploy Preview tại https://tai-sinh-di-san-so-15v9tig4g-quoczai22s-projects.vercel.app; health và tệp JS mới đã xác nhận qua CLI. Chưa kiểm tra trực quan bản Preview cuối vì in-app browser yêu cầu đăng nhập Vercel.
