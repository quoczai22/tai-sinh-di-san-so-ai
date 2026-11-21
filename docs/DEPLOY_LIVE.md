# Triển khai giao diện mới qua Vercel và Modal

Ngày cập nhật: 21/11/2026. Tài liệu này mô tả luồng vận hành giao diện mới qua cổng `/api/live/*` (`web_ui/api/live.js`) trên project Vercel chính thức `tai-sinh-di-san-so-ai` gọi backend GPU T4 trên Modal (app `tai-sinh-di-san-so-api`).

## Project Vercel chính thức

- **Project chính thức để nộp**: `tai-sinh-di-san-so-ai`, nối GitHub `quoczai22/tai-sinh-di-san-so-ai`, **Production Branch = `main`** ⇒ push lên `main` là tự deploy production.
- **Cấu hình build bắt buộc**: **Root Directory = `web_ui`**, **Framework = Other**. Trước ngày 20/11/2026, mọi build của project này đều lỗi vì Vercel nhận nhầm gốc repo là ứng dụng FastAPI (gốc có `requirements.txt` và `api/main.py`) và cố cài thư viện GPU (`pymeshlab` thất bại). Đã khắc phục bằng **Root Directory = `web_ui`**; nếu ai đổi lại cấu hình này, build sẽ hỏng lại.
- **Link công khai duy nhất để đưa giám khảo**: `https://tai-sinh-di-san-so-ai.vercel.app`.
- **Các đường dẫn không đưa cho giám khảo**: mọi địa chỉ khác của project (có `-quoczai22s-projects`, có `-git-main-`, hoặc link từng bản deploy) đều bị Vercel Authentication chặn (yêu cầu đăng nhập Vercel).
- **Project cũ không còn dùng**: `tai-sinh-di-san-so-design` (trước đây deploy tay bằng CLI) không còn dùng để nộp.

## Quyết định

- Kiến trúc chính thức: giám khảo → **Vercel** (`tai-sinh-di-san-so-ai`) → **Modal GPU T4** (`tai-sinh-di-san-so-api`) → nếu lỗi (trừ lỗi xác thực 401/403, hàng đầy 429, xung đột 409) thì hiển thị **kết quả đã sinh sẵn** (dữ liệu thật trong `web_ui/data`, kèm nhãn "Kết quả đã sinh sẵn — không phải sinh trực tiếp").
- Chỉ bật live sau khi chủ tài khoản xác nhận Spend limit = $0 trên Modal. Nếu đến 24/11 chưa ổn định live thì nộp bản demo.
- UptimeRobot chỉ ping `/health` của Vercel (`https://tai-sinh-di-san-so-ai.vercel.app/health`). Route `/health` và `/api/live/health` đều chạy trên CPU (`runtime: "vercel-cpu"`), không đánh thức Modal.

## Luồng giao diện

1. Trang đọc `web_ui/data` và gọi `GET /api/live/health`. Endpoint này chạy trên CPU và chỉ báo biến `MODAL_URL` và `MODAL_KEY` có được cấu hình hay không (`generation_available: true/false`); **không chứng minh** khoá đúng hay GPU sẵn sàng.
2. Khi bấm "Tạo thiết kế", UI gửi `POST /api/live/generate` với `heritage_id` và `seed`. Gateway kiểm tra giới hạn `RATE_LIMIT_PER_HOUR` (mặc định 10 lượt/IP/giờ), gắn header `X-API-Key` phía server rồi gọi Modal.
3. Modal nhận tối đa 3 lượt cùng lúc (`MAX_ACTIVE_JOBS = 3` trong `api/main.py`, `max_containers=1` trong `modal_app.py`): 1 lượt đang sinh trên T4, tối đa 2 lượt chờ theo thứ tự. UI hỏi `GET /api/live/generate/{job_id}?heritage_id=...` mỗi 1,2 giây, hiện vị trí chờ và tiến độ, tối đa 20 phút. Mã job được lưu trong `localStorage` (`dh:pending-generation`, thời hạn khôi phục 24 giờ) để quay lại cùng trình duyệt và cùng domain có thể tiếp tục theo dõi; kết quả job hoàn tất được lưu vào Modal Volume. Hàng chờ đầy trả `429` và xung đột trả `409` để người dùng thử lại, không chuyển sang demo. Nếu container bị dừng giữa lúc sinh và mất job (`404`), UI báo lỗi và cho người dùng tạo lại.
4. Xử lý lỗi xác thực và failover demo trong `web_ui/api/live.js`:
   - Nếu Modal trả HTTP `401` hoặc `403` (commit `a7c1b39`): gateway trả HTTP **503** kèm thông báo `"Máy sinh ảnh chưa xác thực được. Vui lòng báo nhóm vận hành."`, **không** âm thầm chuyển sang demo.
   - Nếu Modal lỗi kết nối, timeout, lỗi HTTP khác (5xx...), chưa cấu hình `MODAL_URL`/`MODAL_KEY` hoặc chạm rate limit: gateway trả `backend: "demo"` kèm `demo_label: "Kết quả đã sinh sẵn — không phải sinh trực tiếp"`.
5. Sau khi sinh xong, job trả sẵn 4 biến thể kèm đường ảnh `/media/run/{run_id}/{filename}` để UI hiển thị trực tiếp qua `/api/live/media/run/...`; khi tải lại trang Kết quả (`localStorage` khóa `dh:last-live-run`), UI lấy Passport qua `/api/live/passports` và ảnh PNG qua `/api/live/media/artifact`. Gateway chỉ chuyển tiếp các route đọc cần thiết và `POST /api/live/audit`; các route ghi Passport/QC/thẩm định/chỉnh sửa/xuất bản không được chuyển tiếp (trả 404).

## Lưu ảnh và cấu hình Modal

Trong `modal_app.py`:
- `APP_NAME = "tai-sinh-di-san-so-api"`, GPU mặc định `GPU_TYPE = os.environ.get("MODAL_GPU", "T4")`, `max_containers = 1`.
- Modal gắn Volume `tai-sinh-di-san-outputs` tại `/data/outputs` (`OUTPUT_VOLUME_MOUNT`). Docker image phải để trống đường dẫn này trước khi mount. Khi khởi động, `modal_app.py` tạo symlink `/app/outputs` → `/data/outputs` vì `generation/streamlit_runner.py` và `api/store.py` đều dùng `/app/outputs`. Trọng số model đọc thẳng từ `/cache/huggingface` (`BAKED_HF_CACHE`) đã tải sẵn trong Docker image.
- Thời gian giữ GPU chờ sau lượt dùng cuối: `SCALEDOWN_SECONDS = 420` (`scaledown_window=420`, tức 420 giây / 7 phút — **giá trị cấu hình, chưa đo**).
- Giới hạn thời gian xử lý mỗi phiên gọi: `timeout=900` (900 giây — giá trị cấu hình, là giới hạn thời gian xử lý, không phải thời gian giữ GPU chờ).
- `modal_app.py` đặt mặc định `TSDS_GENERATE_PER_HOUR=1000` (còn `api/main.py` mặc định 6 nếu chạy riêng) để gateway Vercel kiểm soát rate limit theo IP người dùng. Giới hạn ở gateway là giới hạn mềm, lưu trong RAM từng Vercel Function instance.

## Biến cần cấu hình

- **Trên Vercel** (project `tai-sinh-di-san-so-ai` → Settings → Environment Variables): `MODAL_URL`, `MODAL_KEY`, `MODAL_TIMEOUT_MS` (mặc định `25000`), `RATE_LIMIT_PER_HOUR` (mặc định `10`), `ALERT_DISCORD_WEBHOOK_URL`, `ALERT_COOLDOWN_MIN` (mặc định `30`). Không đặt khoá trong frontend.
- **Trên Modal**: secret `tai-sinh-di-san-secret` chứa `DH_API_KEY`, phải khớp với `MODAL_KEY` trên Vercel. `DH_REQUIRE_API_KEY=1` đã được đặt sẵn trong `Dockerfile` và `modal_app.py` (chế độ fail-closed: thiếu `DH_API_KEY` sẽ từ chối khởi động).
- Người vận hành tự nhập giá trị khoá trên giao diện web Vercel/Modal hoặc trong terminal riêng — **tuyệt đối không dán khoá vào chat, tài liệu hay commit**. Sau khi đổi biến trên Vercel phải **Redeploy**.

## Sự cố thường gặp: khoá Vercel và Modal không khớp (401)

Sự cố thực tế xảy ra ngày 21/11/2026 trên production và đã được khắc phục kèm phòng ngừa ở commit `a7c1b39` (`web_ui/api/live.js`).

- **Triệu chứng**:
  - *Trước commit `a7c1b39`*: bấm "Tạo thiết kế" trên production thì lập tức chuyển sang trang kết quả với ảnh có sẵn, trông như bản deploy tĩnh, không có GPU nào chạy.
  - *Từ commit `a7c1b39`*: gateway không âm thầm chuyển sang demo mà trả HTTP **503** kèm thông báo `"Máy sinh ảnh chưa xác thực được. Vui lòng báo nhóm vận hành."` tại trang Studio.
- **Nguyên nhân**: khoá `MODAL_KEY` trên Vercel không khớp `DH_API_KEY` trong secret Modal `tai-sinh-di-san-secret`, nên Modal trả HTTP `401`.
- **Các bước khắc phục (theo đúng thứ tự)**:
  1. Người vận hành tự nhập lại cùng một giá trị khoá trên giao diện web hoặc terminal riêng của mình (**tuyệt đối không dán khoá vào chat, tài liệu hay commit**):
     - Cập nhật `DH_API_KEY` trong secret Modal `tai-sinh-di-san-secret`.
     - Cập nhật `MODAL_KEY` trong Environment Variables của project Vercel `tai-sinh-di-san-so-ai`.
  2. **Deploy lại Modal** (`modal deploy modal_app.py` từ gốc repo) để container nạp secret mới.
  3. **Redeploy Vercel** (Vercel Dashboard → Deployments → Redeploy bản production) để gateway nạp biến `MODAL_KEY` mới.
- **Cách kiểm tra**:
  - `GET /api/live/health` **không đủ** để xác nhận: endpoint này chỉ chạy trên CPU và chỉ kiểm tra `MODAL_URL` và `MODAL_KEY` có được cấu hình hay không (`generation_available`), không gọi Modal và không xác minh khoá đúng hay GPU sẵn sàng.
  - Phải chạy **một lượt sinh thật** trên `https://tai-sinh-di-san-so-ai.vercel.app` để xác nhận khoá khớp và GPU xử lý thành công.
- **Lưu ý chi phí**: mỗi lượt sinh thật sẽ đánh thức GPU T4 trên Modal và tốn credit GPU (cộng thời gian giữ container chờ theo cấu hình `scaledown_window=420` giây, chưa đo phí thực tế). Chỉ chạy lượt kiểm tra thật sau khi đã hoàn tất đủ 3 bước khắc phục ở trên.

## Chưa kiểm chứng

Các hạng mục sau **chưa đo / chưa xác minh** tính đến ngày 21/11/2026:

- **Cold start Modal** (thời gian từ 0 container tới khi sẵn sàng): *chưa đo*.
- **Thời gian sinh 4 ảnh** trên Modal T4: *chưa đo*.
- **Phí thực tế** trên Modal (chi phí mỗi lượt sinh và chi phí giữ container chờ): *chưa đo*.
- **Độ bền lưu ảnh trên Modal Volume sau khi container tự tắt** (sau chu kỳ `scaledown_window` tự động): *chưa xác minh* (trước đó mới thử dừng app thủ công rồi deploy lại trên Preview, chưa chờ container tự tắt).
- **Lần push `main` kế tiếp có tự build thành công trên Vercel với cấu hình mới hay không** (Root Directory = `web_ui`, Framework = Other): *chưa xác minh*.

## Kiểm tra chưa tốn GPU

- `node scripts/test_live_gateway.js`
- Đặt `PYTHON_EXECUTABLE` trỏ tới `.venv` rồi chạy `node scripts/test_live_gateway_mock.js`
- Python từ `.venv` chạy `scripts/test_api_key_guard.py`, `scripts/test_acceptance_1_8.py`, `scripts/test_alert_webhook.py`, `scripts/test_worker_resilience.py` và `pytest`.
- `python scripts/ui_index.py` rồi kiểm tra diff của `web_ui/index.html`.

## Nhật ký kiểm thử kỹ thuật (21/11/2026)

Các ghi nhận dưới đây là kết quả kiểm thử trên Modal workspace `doandt0612` và các bản Vercel Preview trước/trong quá trình hoàn thiện cổng `/api/live/*` (các URL Preview nội bộ có bảo vệ Vercel Authentication, không dùng để nộp):

- Kiểm tra kết nối ban đầu: `/health` của Modal trả `cuda=true`, `device=Tesla T4`; `/heritage` trả 6 hiện vật; `POST /generate` không có `X-API-Key` trả `401`. Preview Vercel xác nhận `/health` và rewrite `/api/live/health`, `/api/live/heritage`. Job qua gateway cho `LR3D_61`, seed `20261121`, run `R20261120T171657-HV08` hoàn tất 4/4; cả bốn PNG tải được qua `/api/live/media/artifact`, mỗi ảnh có SHA-256 khác nhau. Bốn Passport mới được trả về. V1 vẫn có SHA-256 tiền tố `46F2E2E8784D2B1F` sau khi dừng rồi deploy lại Modal thủ công (chưa chờ scaledown tự động).
- Khôi phục phiên khi reload: sau lượt thử trên trình duyệt, phát hiện reload lúc job còn chạy làm mất job ID trong bộ nhớ trang; `POST` tiếp theo nhận `409` nhưng gateway cũ gắn nhầm nhãn demo. Đã sửa gateway trả `409` rõ ràng và lưu job đang chạy + `run_id` phía trình duyệt để tiếp tục polling và chọn đúng run khi reload trang Kết quả (ban đầu dùng `sessionStorage`, hiện trong code `web_ui/assets/js/core/generation.js` và `web_ui/assets/js/core/data.js` dùng `localStorage`). Bài kiểm thử `node --experimental-default-type=module scripts/test_live_session.mjs` đạt, xác nhận khôi phục run kể cả khi health lỗi và không `POST` thêm.
- Hàng chờ trên cùng container Modal: 1 job chạy, tối đa 2 job chờ (`MAX_ACTIVE_JOBS = 3`). Lượt đến sau nhận `queue_position`, không nhận `409`; hàng đầy trả `429` và không chuyển sang demo. Job lỗi không chặn các job sau. Trạng thái cuối được lưu vào Volume; job mất khi đang chạy hoặc chờ được báo gián đoạn (`404`). Qua Preview trên Modal `doandt0612`, hai lượt `8b83857ddd5d4532883fa6a02c13264f` và `aa68e7a41fa94cc19fcced3a2030ca06` được nhận liên tiếp; lúc lượt đầu `running` 10%, lượt sau `queued` vị trí 1; sau 45 giây không polling, lượt đầu hoàn tất 4/4, lượt sau chuyển sang `running`; sau đó cả hai hoàn tất 4/4 với run lần lượt `R20261121T110841-HV08` và `R20261121T111024-HV08`, PNG V1 có SHA-256 tiền tố khác nhau (`E15750E8B8ECE13B`, `C9B3B978FD795890`) và có hai tệp JSON job tương ứng trên Volume. Chưa thử ba người dùng thật đồng thời.
- Tối ưu hiển thị ảnh sau khi job hoàn tất: job trả sẵn bốn `variant` và đường ảnh `/media/run/...`, nên trang Kết quả dùng trực tiếp thay vì quét lại toàn bộ Passport; giữ cache hiện vật đã tải ở Studio, bắt đầu tải bốn PNG song song và đặt ảnh card live ở chế độ `eager`. Log trước khi sửa có một lượt `GET /passports` mất 7,35 giây và bốn `GET /media/artifact` mất đến 3,20 giây để về đủ. Bài kiểm thử `scripts/test_live_session.mjs` xác nhận bốn ảnh bắt đầu tải trước khi điều hướng và đúng URL của run. Chưa đo thời gian hiển thị trực quan sau sửa.
