# Triển khai giao diện mới qua Vercel và Modal

Ngày cập nhật: 22/11/2026. Backend dùng Modal workspace doandt0612; các mốc kiểm thử ngày 21/11 ở dưới là lịch sử, không thay thế việc xác nhận trạng thái production hiện tại trên dashboard.

## Quyết định

- Project Vercel chính thức: tai-sinh-di-san-so-ai. Cần kiểm tra liên kết .vercel/project.json trước khi deploy CLI từ thư mục web_ui.
- Mục tiêu là sinh trực tiếp qua Modal. Dữ liệu thật đã sinh sẵn trong web_ui/data là lớp dự phòng.
- Chỉ bật live sau khi chủ tài khoản xác nhận Spend limit = $0 trên Modal. Nếu đến 24/11 chưa nối cổng xong thì nộp bản demo.
- UptimeRobot chỉ ping /health của Vercel. Route này và /api/live/health đều chạy CPU, không đánh thức Modal.

## Luồng giao diện

1. Trang đọc web_ui/data và gọi /api/live/health. Health chỉ cho biết đã cấu hình MODAL_URL và MODAL_KEY; nó không chứng minh GPU đang chạy.
2. Khi bấm Tạo thiết kế, UI gửi POST /api/live/generate với heritage_id và seed. Gateway giới hạn 10 lượt/IP/giờ, gắn X-API-Key phía server rồi gọi Modal.
3. Modal nhận tối đa ba lượt cùng lúc: một lượt sinh trên T4, hai lượt chờ theo thứ tự. UI hỏi GET /api/live/generate/{job_id}?heritage_id=..., hiện vị trí chờ và tiến độ, tối đa 20 phút. Mã job được lưu trong localStorage để quay lại cùng trình duyệt và cùng domain có thể tiếp tục theo dõi; kết quả job hoàn tất được lưu vào Modal Volume. Hàng chờ đầy trả 429 để người dùng thử lại, không chuyển sang ảnh demo. Nếu container bị dừng giữa lúc sinh, lượt đang chạy và chờ bị gián đoạn, UI báo lỗi và cho người dùng tạo lại.
4. Nếu Modal lỗi, timeout hoặc chạm rate limit, gateway trả backend=demo. UI dùng dữ liệu đã sinh sẵn và hiện nhãn “Kết quả đã sinh sẵn — không phải sinh trực tiếp”.
5. Sau khi sinh xong, UI lấy Passport qua /api/live/passports và ảnh PNG qua /api/live/media/artifact. Gateway chỉ cho các route đọc cần thiết; các route ghi Passport/QC không được chuyển tiếp.

## Lưu ảnh

Modal gắn Volume tại /data/outputs. Docker image phải để trống đường dẫn này trước khi mount. Khi khởi động, modal_app.py nối /app/outputs tới Volume vì tsds/pipeline/run.py và tsds/api/store.py đều dùng /app/outputs. Mount và khởi động T4 đã kiểm chứng. Bốn Passport và ảnh V1 vẫn đọc được với cùng SHA-256 sau khi dừng app rồi deploy lại; chưa chờ scaledown tự động. Cấu hình giữ T4 sau lượt dùng cuối là 420 giây (7 phút); `timeout=900` là giới hạn thời gian xử lý, không phải thời gian chờ.

Backend đặt TSDS_GENERATE_PER_HOUR=1000 mặc định để gateway kiểm soát theo IP người dùng. Giới hạn gateway là giới hạn mềm, lưu trong RAM từng Vercel Function instance.

## Biến cần cấu hình

Trên Vercel: MODAL_URL, MODAL_KEY, MODAL_TIMEOUT_MS (mặc định 25000), RATE_LIMIT_PER_HOUR (mặc định 10), ALERT_DISCORD_WEBHOOK_URL, ALERT_COOLDOWN_MIN (mặc định 30). Không đặt khóa trong frontend.

Trên Modal: secret tai-sinh-di-san-secret chứa DH_API_KEY, bằng MODAL_KEY trên Vercel. DH_REQUIRE_API_KEY được modal_app.py đặt bằng 1.

Người dùng tự nhập giá trị secret trên dashboard hoặc terminal riêng. Sau khi đổi biến Vercel phải redeploy.

## Kiểm tra chưa tốn GPU

- node tests/manual/test_live_gateway.js
- Đặt PYTHON_EXECUTABLE trỏ tới .venv rồi chạy node tests/manual/test_live_gateway_mock.js
- Python từ .venv chạy tests/manual/test_api_key_guard.py, tests/manual/test_acceptance_1_8.py, tests/manual/test_alert_webhook.py, tests/manual/test_worker_resilience.py và pytest.
- python scripts/web/ui_index.py rồi kiểm tra diff của web_ui/index.html.

Ngày 21/11: /health của Modal trả cuda=true, device=Tesla T4; /heritage trả 6 hiện vật; POST /generate không có X-API-Key trả 401. Preview Vercel xác nhận /health và rewrite /api/live/health, /api/live/heritage. Job qua gateway cho LR3D_61, seed 20261121, run R20261120T171657-HV08 hoàn tất 4/4; cả bốn PNG tải được qua /api/live/media/artifact, mỗi ảnh có SHA-256 khác nhau. Bốn Passport mới được trả về. V1 vẫn có SHA-256 tiền tố 46F2E2E8784D2B1F sau khi dừng rồi deploy lại Modal. Chưa đo chính xác cold start, thời gian sinh, chi phí; chưa xác nhận scaledown tự động hoặc kiểm tra tương tác trực quan trên Preview.

Sau lượt thử trên trình duyệt, phát hiện reload lúc job còn chạy làm mất job ID trong bộ nhớ trang; POST tiếp theo nhận 409 nhưng gateway gắn nhầm nhãn demo. Đã sửa gateway trả 409 rõ ràng và sessionStorage tiếp tục polling job cũ. Trình duyệt đã kiểm tra reload giữa lúc sinh rồi hoàn tất 4 ảnh không có nhãn demo trên Preview. Tiếp đó sửa việc reload trang Kết quả luôn quay lại demo: sessionStorage giữ run_id và trang Kết quả chọn đúng run của phiên. Khi health tạm chậm, trang vẫn thử đọc run đã lưu trước khi dùng demo. Bài kiểm thử `node --experimental-default-type=module tests/manual/test_live_session.mjs` đạt, xác nhận khôi phục run kể cả khi health lỗi và không POST thêm. Bản sửa cuối đã deploy Preview tại https://tai-sinh-di-san-so-15v9tig4g-quoczai22s-projects.vercel.app; health và tệp JS mới đã xác nhận qua CLI. Chưa kiểm tra trực quan bản Preview cuối vì in-app browser yêu cầu đăng nhập Vercel.

Sau đó bổ sung hàng chờ trong cùng container Modal: một job chạy, tối đa hai job chờ. Lượt đến sau nhận `queue_position`, không nhận 409; hàng đầy trả 429 và không chuyển sang demo. Job lỗi không chặn các job sau. Trạng thái cuối được lưu vào Volume để đọc lại sau khi container đổi; job mất khi đang chạy hoặc chờ được báo gián đoạn thay vì hiện nhầm kết quả cũ. Kiểm thử cục bộ xác nhận giới hạn ba lượt và khôi phục trạng thái; GPU thật đã kiểm tra hai lượt như ghi bên dưới.

Ngày 21/11: triển khai Preview `https://tai-sinh-di-san-so-25905pxi8-quoczai22s-projects.vercel.app` và Modal `doandt0612`. Qua Preview, hai lượt `8b83857ddd5d4532883fa6a02c13264f` và `aa68e7a41fa94cc19fcced3a2030ca06` được nhận liên tiếp; lúc lượt đầu `running` 10%, lượt sau `queued` vị trí 1. Sau 45 giây không polling, lượt đầu hoàn tất 4/4, lượt sau chuyển sang `running`. Sau đó cả hai hoàn tất 4/4 với run lần lượt `R20261121T110841-HV08` và `R20261121T111024-HV08`. PNG V1 của hai lượt tải qua Preview, chữ ký PNG đúng, SHA-256 tiền tố khác nhau (`E15750E8B8ECE13B`, `C9B3B978FD795890`). Modal Volume có hai tệp JSON job tương ứng. Chưa kiểm tra trực quan UI Preview vì bảo vệ Vercel Authentication; chưa thử ba người dùng thật hoặc khởi động lại container sau khi job xong. Bản production chưa thay đổi.

Tối ưu thời gian hiện ảnh sau khi job hoàn tất: job trả sẵn bốn `variant` và đường ảnh, nên trang Kết quả dùng trực tiếp thay vì quét lại toàn bộ Passport; giữ cache hiện vật đã tải ở Studio, bắt đầu tải bốn PNG song song và đặt ảnh card live ở chế độ eager. Log trước khi sửa có một lượt `GET /passports` mất 7,35 giây và bốn `GET /media/artifact` mất đến 3,20 giây để về đủ. Bài kiểm thử `tests/manual/test_live_session.mjs` xác nhận bốn ảnh bắt đầu tải trước khi điều hướng và đúng URL của run. Chưa đo thời gian hiển thị trực quan sau sửa.

## Cảnh báo vận hành

Hai lớp cảnh báo độc lập: Discord webhook báo lỗi từ gateway; UptimeRobot kiểm tra Vercel khi gateway không thể tự báo. `GET /health` và `GET /api/live/health` chỉ chạy trên CPU, không gọi Modal. Bài thử `node tests/manual/test_health_cpu.js` xác nhận điều này. Webhook có cooldown mặc định 30 phút trong RAM của từng Vercel instance; nhiều instance có thể gửi hơn một tin cho cùng một sự cố.

Zalo Bot hai chiều chỉ bật khi Vercel có `ALERT_ZALO_WEBHOOK_SECRET`. Khi gọi API `setWebhook` của Zalo, đặt `url` là `https://tai-sinh-di-san-so-ai.vercel.app/api/live/zalo-webhook` và `secret_token` bằng đúng giá trị đó. Zalo gửi secret qua header `X-Bot-Api-Secret-Token`; không đưa secret vào URL. Đặt `ALERT_ZALO_USER_CHAT_ID` cho người vận hành duy nhất được nhắn lệnh kiểm tra/đánh thức GPU; `ALERT_ZALO_CHAT_ID` cho nhóm chỉ được hỏi tình trạng. Thiếu các biến này thì webhook từ chối hoặc bỏ qua tin nhắn. Lệnh “đánh thức GPU” chỉ gọi `/health`, có thể khởi động container và tiêu credit; không tự sửa lỗi hay xác nhận sinh ảnh thành công. Chạy `node tests/manual/test_zalo_bot_guard.js` trước khi phát hành.

Nếu webhook đã được đăng ký và chưa biết ID chat riêng, sau khi phát hành bản có xác thực hãy nhắn riêng bot `/id`. Bot chỉ trả ID của chính cuộc chat đó, không gọi AI hoặc Modal. Dùng ID nhận được để đặt `ALERT_ZALO_USER_CHAT_ID`; không cần xóa webhook hay gọi `getUpdates`.

`/api/warmup` chỉ nhận POST với `X-Warmup-Key` khớp biến `WARMUP_KEY` trên Vercel; nếu chưa đặt khóa thì endpoint từ chối mọi yêu cầu. Không dùng nó làm URL giám sát định kỳ. Chạy `node tests/manual/test_warmup_guard.js` để kiểm tra.

Tin Discord có gợi ý xử lý theo mã lỗi để nhóm tra cứu nhanh trên điện thoại. Gateway thử lại đúng một lần các yêu cầu đọc GET khi gặp lỗi mạng hoặc HTTP 502/503/504. Không thử lại timeout dài, 401/403, hoặc POST `/generate`; tránh gửi hai lượt sinh ảnh và dùng GPU ngoài ý muốn. Khi vẫn lỗi, giao diện dùng cơ chế dự phòng và gửi cảnh báo như trước.

Nhóm tự cấu hình theo thứ tự:

1. Trong Discord, mở **Edit Channel → Integrations → Webhooks → New Webhook** và sao chép URL trong kênh riêng của nhóm. Không gửi URL vào chat hay commit.
2. Trong Vercel project `tai-sinh-di-san-so-ai`, đặt biến production `ALERT_DISCORD_WEBHOOK_URL` và `ALERT_COOLDOWN_MIN` bằng `30`, sau đó **Redeploy** để biến mới có hiệu lực.
3. Trên máy của người vận hành, điền URL vào `ALERT_DISCORD_WEBHOOK_URL` trong `.env.local` ở gốc repo (tệp này đã được Git bỏ qua), rồi chạy `node scripts/deploy/test_alert.js` đúng một lần. Script tự đọc tệp và chỉ in trạng thái gửi hoặc mã HTTP, không in URL.
4. Trong UptimeRobot, chọn **Add New Monitor → HTTP(s)**, URL `https://tai-sinh-di-san-so-ai.vercel.app/health`, chu kỳ 5 phút và email cho 2–3 thành viên. Không tạo monitor trỏ vào Modal, `/api/warmup` hoặc endpoint sinh ảnh.
5. Trên bản Vercel **Preview**, tạm bỏ `MODAL_URL`, redeploy Preview và bấm Tạo. Xác nhận Discord nhận tin và giao diện hiện nhãn bản demo. Khôi phục `MODAL_URL` rồi redeploy Preview. Không thử bằng cách xóa biến production.

| Tín hiệu | Nguyên nhân có thể | Xử lý |
| --- | --- | --- |
| Email UptimeRobot | Vercel hoặc route `/health` không phản hồi | Mở Vercel Deployments/Runtime Logs, kiểm tra domain và deployment mới nhất; rollback deployment lỗi nếu cần. |
| Discord “Modal lỗi” | Timeout, 5xx, lỗi mạng, thiếu cấu hình hoặc job thất bại | Xem endpoint và thời gian trong tin, đối chiếu Vercel Runtime Logs và Modal Logs; kiểm tra container, Volume, secret và trạng thái job trước khi deploy lại. |
| Discord “sai khóa 401” | `MODAL_KEY` ở Vercel không khớp `DH_API_KEY` trong Modal secret | Người có quyền kiểm tra hai giá trị trong dashboard riêng, cập nhật đúng secret/biến rồi redeploy phần bị đổi; không gửi khóa qua chat. |
| Modal hết credit | GPU không khởi động hoặc Modal trả lỗi trong lúc sinh | Kiểm tra Billing, Usage, Spend limit và workspace; giữ giao diện demo dự phòng cho người xem, chỉ bật live khi chủ tài khoản xác nhận giới hạn chi tiêu. |

CI `Modal backend checks` kiểm tra bằng mock CPU; nó không xác nhận GPU thật hoặc tự deploy Modal. Trước production, chạy thử 1 job sinh bốn ảnh và kiểm tra đường ảnh trên Vercel sau khi deploy Modal thủ công.
