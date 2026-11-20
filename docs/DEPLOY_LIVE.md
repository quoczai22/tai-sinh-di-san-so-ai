# Triển khai giao diện mới qua Vercel và Modal

Ngày cập nhật: 20/11/2026. Tài liệu này mô tả nhánh deploy/live-gateway; chưa triển khai thật trên Modal hoặc Vercel.

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

Modal gắn Volume tại /data/outputs. Khi khởi động, modal_app.py nối /app/outputs tới Volume vì generation/streamlit_runner.py và api/store.py đều dùng /app/outputs. Theo tài liệu Modal, Volume tự commit định kỳ và khi container tắt; chưa kiểm chứng bằng GPU thật hoặc scale-down thật.

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

Các bài kiểm tra mock không chứng minh GPU T4 chạy được. Cold start, thời gian sinh bốn ảnh, chi phí, và ảnh sau scale-down: chưa đo.
Rewrite động của Vercel chưa được chạy trong một Vercel deployment; cần kiểm chứng /api/live/health trên preview trước production.
