# Triển khai giao diện mới qua Vercel và Modal

Ngày cập nhật: 24/11/2026. Backend dùng Modal workspace doandt0612; các mốc kiểm thử ngày 21/11 ở dưới là lịch sử, không thay thế việc xác nhận trạng thái production hiện tại trên dashboard.

## Project Vercel chính thức

- **Project chính thức để nộp**: `tai-sinh-di-san-so-ai`, nối GitHub `quoczai22/tai-sinh-di-san-so-ai`, **Production Branch = `main`** ⇒ push lên `main` là tự deploy production.
- **Cấu hình build bắt buộc**: **Root Directory = `web_ui`**, **Framework = Other**. Trước ngày 20/11/2026, mọi build của project này đều lỗi vì Vercel nhận nhầm gốc repo là ứng dụng FastAPI (gốc có `requirements.txt` và `api/main.py`) và cố cài thư viện GPU (`pymeshlab` thất bại). Đã khắc phục bằng **Root Directory = `web_ui`**; nếu ai đổi lại cấu hình này, build sẽ hỏng lại.
- **Link công khai duy nhất để đưa giám khảo**: `https://tai-sinh-di-san-so-ai.vercel.app`.
- **Các đường dẫn không đưa cho giám khảo**: mọi địa chỉ khác của project (có `-quoczai22s-projects`, có `-git-main-`, hoặc link từng bản deploy) đều bị Vercel Authentication chặn (yêu cầu đăng nhập Vercel).
- **Project cũ không còn dùng**: `tai-sinh-di-san-so-design` (trước đây deploy tay bằng CLI) không còn dùng để nộp.

## Quyết định

- Kiến trúc chính thức: giám khảo → **Vercel** (`tai-sinh-di-san-so-ai`) → **Modal GPU T4** (`tai-sinh-di-san-so-api`). Khi bấm Tạo mà Modal lỗi, giao diện báo lỗi và giữ người dùng ở Studio; không đổi lượt sinh thất bại thành ảnh đã sinh sẵn. Dữ liệu mẫu trong `web_ui/data` chỉ dùng để trưng bày và chạy ngoại tuyến.
- Hai endpoint cũ `/api/generate` và `/api/status` đã ngừng dùng, trả HTTP `410`; chỉ `/api/live/generate` nhận lượt sinh mới. Hai bài test cũ về failover demo (`test_acceptance_1_8.py`, `test_alert_webhook.py`) kiểm thử gateway đã ngừng nên được xoá khỏi nhánh chính ngày 24/11/2026; vẫn xem được trong lịch sử Git.
- Chỉ bật live sau khi chủ tài khoản xác nhận Spend limit trên Modal. Người vận hành đã xác nhận ngày 24/11/2026 là đã đặt (mức cụ thể không ghi ở đây; chưa kiểm trên dashboard). Nếu đến 24/11 chưa ổn định live thì nộp bản demo.
- UptimeRobot chỉ ping `/health` của Vercel (`https://tai-sinh-di-san-so-ai.vercel.app/health`). Route `/health` và `/api/live/health` đều chạy trên CPU (`runtime: "vercel-cpu"`), không đánh thức Modal.

## Luồng giao diện

1. Trang đọc `web_ui/data` và gọi `GET /api/live/health`. Endpoint này chạy trên CPU và chỉ báo biến `MODAL_URL` và `MODAL_KEY` có được cấu hình hay không (`generation_available: true/false`); **không chứng minh** khoá đúng hay GPU sẵn sàng.
2. Khi bấm "Tạo thiết kế", UI gửi `POST /api/live/generate` với `heritage_id` và `seed`. Gateway kiểm tra giới hạn `RATE_LIMIT_PER_HOUR` (mặc định 10 lượt/IP/giờ), gắn header `X-API-Key` phía server rồi gọi Modal.
3. Modal nhận tối đa 3 lượt cùng lúc (`MAX_ACTIVE_JOBS = 3` trong `api/main.py`, `max_containers=1` trong `modal_app.py`): 1 lượt đang sinh trên T4, tối đa 2 lượt chờ theo thứ tự. UI hỏi `GET /api/live/generate/{job_id}?heritage_id=...` mỗi 1,2 giây, hiện vị trí chờ và tiến độ, tối đa 20 phút. Mã job được lưu trong `localStorage` (`dh:pending-generation`, thời hạn khôi phục 24 giờ) để quay lại cùng trình duyệt và cùng domain có thể tiếp tục theo dõi; kết quả job hoàn tất được lưu vào Modal Volume. Hàng chờ đầy trả `429` và xung đột trả `409` để người dùng thử lại, không chuyển sang demo. Nếu container bị dừng giữa lúc sinh và mất job (`404`), UI báo lỗi và cho người dùng tạo lại.
4. Xử lý lỗi trong `web_ui/api/live.js`:
   - Nếu Modal trả HTTP `401` hoặc `403` (commit `a7c1b39`): gateway trả HTTP **503** kèm thông báo `"Máy sinh ảnh chưa xác thực được. Vui lòng báo nhóm vận hành."`, **không** âm thầm chuyển sang demo.
   - Nếu Modal lỗi kết nối, timeout, lỗi HTTP khác (5xx...), chưa cấu hình `MODAL_URL`/`MODAL_KEY`: gateway trả HTTP `503`. Quá giới hạn lượt gọi trả `429`. Không trường hợp nào của luồng Tạo tự chuyển sang ảnh mẫu.
   - Nếu đã nhận mã job mà việc đọc tiến độ tạm lỗi, trình duyệt giữ mã để thử lại; không thay kết quả của job bằng ảnh mẫu.
5. Sau khi sinh xong, job trả sẵn 4 biến thể kèm đường ảnh `/media/run/{run_id}/{filename}` để UI hiển thị trực tiếp qua `/api/live/media/run/...`; khi tải lại trang Kết quả (`localStorage` khóa `dh:last-live-run`), UI lấy Passport qua `/api/live/passports` và ảnh PNG qua `/api/live/media/artifact`. Gateway chỉ chuyển tiếp các route đọc cần thiết và `POST /api/live/audit`; các route ghi Passport/QC/thẩm định/chỉnh sửa/xuất bản không được chuyển tiếp (trả 404).

## Lưu ảnh và cấu hình Modal

Modal gắn Volume tại /data/outputs. Docker image phải để trống đường dẫn này trước khi mount. Khi khởi động, modal_app.py nối /app/outputs tới Volume vì tsds/pipeline/run.py và tsds/api/store.py đều dùng /app/outputs. Mount và khởi động T4 đã kiểm chứng. Bốn Passport và ảnh V1 vẫn đọc được với cùng SHA-256 sau khi dừng app rồi deploy lại; chưa chờ scaledown tự động. Cấu hình giữ T4 sau lượt dùng cuối là 420 giây (7 phút); `timeout=900` là giới hạn thời gian xử lý, không phải thời gian chờ.

Backend đặt TSDS_GENERATE_PER_HOUR=1000 mặc định để gateway kiểm soát theo IP người dùng. Giới hạn gateway là giới hạn mềm, lưu trong RAM từng Vercel Function instance.

Giá trị cấu hình đọc từ `modal_app.py` (24/11/2026):

- Thời gian giữ GPU chờ sau lượt dùng cuối: `SCALEDOWN_SECONDS = 420` (`scaledown_window=420`, tức 420 giây / 7 phút — **giá trị cấu hình, chưa đo**).
- Giới hạn thời gian xử lý mỗi phiên gọi: `timeout=900` (900 giây — giá trị cấu hình, là giới hạn thời gian xử lý, không phải thời gian giữ GPU chờ).

## Tải bản chỉnh sửa và Thiết kế đã tạo (thêm 24/11/2026, chưa deploy thử)

Hai tính năng mới của giao diện. Phần deploy do người phụ trách deploy làm; mục này ghi những gì cần biết.

- **Mã mới:** `web_ui/api/edit.js` (hàm gateway ghi bản sửa, tách khỏi `live.js`), `web_ui/vercel.json` (thêm hàm `api/edit.js` và rewrite `/api/live/passports/:id/edits` đặt trước rewrite chung `/api/live/:route*`), trang `#/mine` và `#/edit/<mã Passport>` trong `web_ui/assets/`. Route `POST /passports/{id}/edits` đã có sẵn trong `tsds/api/main.py`, không đổi.
- **Phải tăng số phiên bản giao diện** khi phát hành, nếu không trình duyệt giữ mã cũ và báo lỗi module: `uv run python scripts/web/ui_index.py finals-N` (hiện là `finals-97`).
- **Khóa ghi:** các route ghi của Modal (`qc`, `reviews`, `edits`, `publish`) dùng chung khóa `DH_API_KEY` với route sinh ảnh; không còn biến `TSDS_WRITE_KEY` hay `MODAL_WRITE_KEY`. Hàm `edit.js` gửi `MODAL_KEY` (bằng `DH_API_KEY`) nên không cần cấu hình thêm. Sau khi deploy Modal, `GET /health` của Modal phải báo `write_protection: true` (ngày 24/11 từng báo `false` vì chưa đặt khóa ghi, nên các route ghi mở công khai). Biến tùy chọn `EDIT_RATE_LIMIT_PER_HOUR` (mặc định 5 lượt mỗi IP mỗi giờ).
- **Giới hạn ảnh:** PNG, tối đa 3 MB, cạnh dài tối đa 4096 px. Thân yêu cầu của hàm Vercel mặc định tối đa 4,5 MB, ảnh gửi dạng base64 lớn thêm khoảng 33%.
- **Thử trước khi lên production:** deploy bản Preview, tạo một thiết kế trực tiếp, bấm vào thiết kế, Tải lên chỉnh sửa, rồi kiểm Passport của thiết kế đó trong Modal Volume. Mỗi bản sửa ghi vĩnh viễn (sổ cái chỉ thêm vào, không có chức năng xóa), nên đừng thử trên Passport của bộ minh chứng.
- **ID tài khoản:** biểu mẫu và gateway `edit.js` bắt buộc ID bắt đầu bằng `TSDS` (tối đa 24 ký tự). API Python ở Modal không bắt buộc tiền tố (chỉ `[A-Za-z0-9_-]{2,24}`), nên ai gọi thẳng vào Modal vẫn ghi được ID khác.
- **Dữ liệu người dùng:** ID tài khoản và mô tả hiện công khai trong Passport, không xóa được. Gateway không phục vụ ảnh người dùng tải lên (chỉ thư mục `outputs/runs/`), nhưng route `/media/artifact` trực tiếp trên Modal cho đọc mọi ảnh dưới `outputs/`, kể cả `outputs/edits/`; chưa siết.
- **Thiết kế đã tạo** lưu danh sách trong trình duyệt (`localStorage`, khóa `dh:my-runs`); ảnh và Passport vẫn nằm trong Volume của Modal.

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
  - Đã thực hiện ngày 24/11/2026: một lượt sinh thật qua production thành công và khóa Vercel–Modal khớp (xem mục **Lượt sinh thật qua production (24/11/2026)**).
- **Lưu ý chi phí**: mỗi lượt sinh thật sẽ đánh thức GPU T4 trên Modal và tốn credit GPU (cộng thời gian giữ container chờ theo cấu hình `scaledown_window=420` giây, chưa đo phí thực tế). Chỉ chạy lượt kiểm tra thật sau khi đã hoàn tất đủ 3 bước khắc phục ở trên.

## Chưa kiểm chứng

Các hạng mục sau **chưa đo / chưa xác minh** tính đến ngày 24/11/2026:

- **Cold start Modal** (thời gian từ 0 container tới khi sẵn sàng): *chưa đo* (chỉ có một mẫu không kiểm soát: lượt `GET /health` đầu tiên sau khi deploy bản mới ngày 24/11 mất 15,2 giây).
- **Thời gian sinh 4 ảnh** trên Modal T4: mới có **một mẫu** (126,8 giây, container nhiều khả năng đang ấm, ngày 24/11/2026; xem mục **Lượt sinh thật qua production (24/11/2026)**); chưa đủ để kết luận phân bố, và chưa đo lúc container nguội.
- **Phí thực tế** trên Modal (chi phí mỗi lượt sinh và chi phí giữ container chờ): *chưa đo*.
- **Độ bền lưu ảnh trên Modal Volume sau khi container tự tắt** (sau chu kỳ `scaledown_window` tự động): *chưa xác minh* (trước đó mới thử dừng app thủ công rồi deploy lại trên Preview, chưa chờ container tự tắt).
- **Gửi chỉnh sửa thật qua trang `edit` trên production**: *chưa xác minh* (khóa ghi đã đúng trên Modal, nhưng chưa có lượt gửi chỉnh sửa nào đi qua gateway).
- Đã xác minh ngày 24/11/2026 (không còn là mục chưa kiểm chứng): với cấu hình Root Directory = `web_ui`, Framework = Other, bản production build từ `main` (commit `6c6c25f`) trên Vercel thành công (trạng thái Ready).
- Đã xác minh ngày 24/11/2026 sau khi deploy lại Modal từ `main` (`66dd279`): `GET /health` của Modal báo `write_protection: true`, `cuda: true`, GPU `Tesla T4`; `POST` vào `qc`, `reviews`, `edits`, `publish` và `/generate` khi không có khóa hoặc sai khóa đều trả HTTP 401; route đọc (`/heritage`, `/passports`) vẫn mở. Trước khi sửa, `/health` từng báo `write_protection: false`.
- Đã xác minh ngày 24/11/2026: một lượt sinh thật qua gateway production thành công, khóa `MODAL_KEY` (Vercel) và `DH_API_KEY` (Modal) khớp.

## Lượt sinh thật qua production (24/11/2026)

Đúng một lượt, sau khi deploy lại Modal từ `main` (`66dd279`) và được người vận hành duyệt (tốn credit GPU của workspace `doandt0612`). Kết quả là **một mẫu đo**, không phải số chính thức.

- **Cách chạy**: hiện vật `LR3D_61`, seed `20261124`; gửi `POST /api/live/generate` tới `https://tai-sinh-di-san-so-ai.vercel.app`, rồi hỏi `GET /api/live/generate/{job_id}` mỗi 3 giây.
- **Mốc thời gian** (tính từ lúc gửi yêu cầu, sai số ±3 giây do chu kỳ hỏi): +2,7 giây nhận job (HTTP 202, `backend: modal`, vị trí hàng chờ 1); +6,2 giây bắt đầu sinh áo dài nền bằng LoRA; +53,5 giây thiết kế 1/4; +74,4 giây thiết kế 2/4; +88,3 giây thiết kế 3/4; +102,3 giây thiết kế 4/4; +116,4 giây kiểm tra chất lượng và lập Design Passport; **+126,8 giây hoàn tất 4/4**.
- **Kết quả**: 4 Passport mới (run `R20261124T043719-HV08`, tạo lúc 04:37 UTC, tức 11:37 giờ Việt Nam; cách nhau khoảng 15 giây). G2: 3 PASS, 1 WARN. G3: 2 PASS, 2 WARN. Không thiết kế nào bị loại. V1 và V4 chờ chuyên gia; V2 và V3 có cảnh báo.
- **Ảnh**: V1 tải qua gateway trả HTTP 200, `image/png`, 712.314 byte, đúng chữ ký PNG, mất 1,6 giây.
- **Hạn chế**: đây không phải cold start (bước sinh bắt đầu sau 6 giây nên container nhiều khả năng đang ấm; Modal không cho thông tin chính thức); chỉ một mẫu; phí thực tế chưa đo (ước chừng khoảng 9 phút máy T4: 127 giây sinh cộng tối đa 7 phút giữ chờ, xem phí thật trên dashboard Modal); phản hồi hỏi trạng thái không có trường `backend`, `gpu`, `duration_s`, nên việc Modal xử lý được xác nhận qua HTTP 202 `backend: modal` lúc tạo job và qua 4 Passport mới.

## Kiểm tra chưa tốn GPU

- node tests/manual/test_live_gateway.js
- Đặt PYTHON_EXECUTABLE trỏ tới .venv rồi chạy node tests/manual/test_live_gateway_mock.js
- Python từ .venv chạy tests/manual/test_api_key_guard.py, tests/manual/test_worker_resilience.py và pytest.
- python scripts/web/ui_index.py rồi kiểm tra diff của web_ui/index.html.

## Nhật ký kiểm thử kỹ thuật (21/11/2026)

Sau lượt thử trên trình duyệt, phát hiện reload lúc job còn chạy làm mất job ID trong bộ nhớ trang; POST tiếp theo nhận 409 nhưng gateway gắn nhầm nhãn demo. Đã sửa gateway trả 409 rõ ràng và sessionStorage tiếp tục polling job cũ. Trình duyệt đã kiểm tra reload giữa lúc sinh rồi hoàn tất 4 ảnh không có nhãn demo trên Preview. Tiếp đó sửa việc reload trang Kết quả luôn quay lại demo: sessionStorage giữ run_id và trang Kết quả chọn đúng run của phiên. Khi health tạm chậm, trang vẫn thử đọc run đã lưu trước khi dùng demo. Bài kiểm thử `node --experimental-default-type=module tests/manual/test_live_session.mjs` đạt, xác nhận khôi phục run kể cả khi health lỗi và không POST thêm. Bản sửa cuối đã deploy Preview tại https://tai-sinh-di-san-so-15v9tig4g-quoczai22s-projects.vercel.app; health và tệp JS mới đã xác nhận qua CLI. Chưa kiểm tra trực quan bản Preview cuối vì in-app browser yêu cầu đăng nhập Vercel.

Sau đó bổ sung hàng chờ trong cùng container Modal: một job chạy, tối đa hai job chờ. Lượt đến sau nhận `queue_position`, không nhận 409; hàng đầy trả 429 và không chuyển sang demo. Job lỗi không chặn các job sau. Trạng thái cuối được lưu vào Volume để đọc lại sau khi container đổi; job mất khi đang chạy hoặc chờ được báo gián đoạn thay vì hiện nhầm kết quả cũ. Kiểm thử cục bộ xác nhận giới hạn ba lượt và khôi phục trạng thái; GPU thật đã kiểm tra hai lượt như ghi bên dưới.

Ngày 21/11: triển khai Preview `https://tai-sinh-di-san-so-25905pxi8-quoczai22s-projects.vercel.app` và Modal `doandt0612`. Qua Preview, hai lượt `8b83857ddd5d4532883fa6a02c13264f` và `aa68e7a41fa94cc19fcced3a2030ca06` được nhận liên tiếp; lúc lượt đầu `running` 10%, lượt sau `queued` vị trí 1. Sau 45 giây không polling, lượt đầu hoàn tất 4/4, lượt sau chuyển sang `running`. Sau đó cả hai hoàn tất 4/4 với run lần lượt `R20261121T110841-HV08` và `R20261121T111024-HV08`. PNG V1 của hai lượt tải qua Preview, chữ ký PNG đúng, SHA-256 tiền tố khác nhau (`E15750E8B8ECE13B`, `C9B3B978FD795890`). Modal Volume có hai tệp JSON job tương ứng. Chưa kiểm tra trực quan UI Preview vì bảo vệ Vercel Authentication; chưa thử ba người dùng thật hoặc khởi động lại container sau khi job xong. Bản production chưa thay đổi.

Tối ưu thời gian hiện ảnh sau khi job hoàn tất: job trả sẵn bốn `variant` và đường ảnh, nên trang Kết quả dùng trực tiếp thay vì quét lại toàn bộ Passport; giữ cache hiện vật đã tải ở Studio, bắt đầu tải bốn PNG song song và đặt ảnh card live ở chế độ eager. Log trước khi sửa có một lượt `GET /passports` mất 7,35 giây và bốn `GET /media/artifact` mất đến 3,20 giây để về đủ. Bài kiểm thử `tests/manual/test_live_session.mjs` xác nhận bốn ảnh bắt đầu tải trước khi điều hướng và đúng URL của run. Chưa đo thời gian hiển thị trực quan sau sửa.

## Cảnh báo vận hành

Hai lớp cảnh báo độc lập: Discord webhook báo lỗi từ gateway; UptimeRobot kiểm tra Vercel khi gateway không thể tự báo. `GET /health` và `GET /api/live/health` chỉ chạy trên CPU, không gọi Modal. Bài thử `node tests/manual/test_health_cpu.js` xác nhận điều này. Webhook có cooldown mặc định 30 phút trong RAM của từng Vercel instance; nhiều instance có thể gửi hơn một tin cho cùng một sự cố.

Zalo Bot hai chiều chỉ bật khi Vercel có `ALERT_ZALO_WEBHOOK_SECRET`. Khi gọi API `setWebhook` của Zalo, đặt `url` là `https://tai-sinh-di-san-so-ai.vercel.app/api/live/zalo-webhook` và `secret_token` bằng đúng giá trị đó. Zalo gửi secret qua header `X-Bot-Api-Secret-Token`; không đưa secret vào URL. Đặt `ALERT_ZALO_USER_CHAT_ID` cho người vận hành duy nhất được nhắn lệnh kiểm tra/đánh thức GPU; `ALERT_ZALO_CHAT_ID` cho nhóm chỉ được hỏi tình trạng. Thiếu các biến này thì webhook từ chối hoặc bỏ qua tin nhắn. Lệnh “đánh thức GPU” chỉ gọi `/health`, có thể khởi động container và tiêu credit; không tự sửa lỗi hay xác nhận sinh ảnh thành công. Chạy `node tests/manual/test_zalo_bot_guard.js` trước khi phát hành.

Nếu webhook đã được đăng ký và chưa biết ID chat riêng, sau khi phát hành bản có xác thực hãy nhắn riêng bot `/id`. Bot chỉ trả ID của chính cuộc chat đó, không gọi AI hoặc Modal. Dùng ID nhận được để đặt `ALERT_ZALO_USER_CHAT_ID`; không cần xóa webhook hay gọi `getUpdates`.

`/api/warmup` chỉ nhận POST với `X-Warmup-Key` khớp biến `WARMUP_KEY` trên Vercel; nếu chưa đặt khóa thì endpoint từ chối mọi yêu cầu. Không dùng nó làm URL giám sát định kỳ. Chạy `node tests/manual/test_warmup_guard.js` để kiểm tra.

Tin Discord có gợi ý xử lý theo mã lỗi để nhóm tra cứu nhanh trên điện thoại. Gateway thử lại đúng một lần các yêu cầu đọc GET khi gặp lỗi mạng hoặc HTTP 502/503/504. Không thử lại timeout dài, 401/403, hoặc POST `/generate`; tránh gửi hai lượt sinh ảnh và dùng GPU ngoài ý muốn. Khi vẫn lỗi, Studio báo lỗi và gateway gửi cảnh báo.

Nhóm tự cấu hình theo thứ tự:

1. Trong Discord, mở **Edit Channel → Integrations → Webhooks → New Webhook** và sao chép URL trong kênh riêng của nhóm. Không gửi URL vào chat hay commit.
2. Trong Vercel project `tai-sinh-di-san-so-ai`, đặt biến production `ALERT_DISCORD_WEBHOOK_URL` và `ALERT_COOLDOWN_MIN` bằng `30`, sau đó **Redeploy** để biến mới có hiệu lực.
3. Trên máy của người vận hành, điền URL vào `ALERT_DISCORD_WEBHOOK_URL` trong `.env.local` ở gốc repo (tệp này đã được Git bỏ qua), rồi chạy `node scripts/deploy/test_alert.js` đúng một lần. Script tự đọc tệp và chỉ in trạng thái gửi hoặc mã HTTP, không in URL.
4. Trong UptimeRobot, chọn **Add New Monitor → HTTP(s)**, URL `https://tai-sinh-di-san-so-ai.vercel.app/health`, chu kỳ 5 phút và email cho 2–3 thành viên. Không tạo monitor trỏ vào Modal, `/api/warmup` hoặc endpoint sinh ảnh.
5. Trên bản Vercel **Preview**, tạm bỏ `MODAL_URL`, redeploy Preview và bấm Tạo. Xác nhận Discord nhận tin và Studio báo máy sinh ảnh chưa sẵn sàng, không mở ảnh mẫu như kết quả mới. Khôi phục `MODAL_URL` rồi redeploy Preview. Không thử bằng cách xóa biến production.

| Tín hiệu | Nguyên nhân có thể | Xử lý |
| --- | --- | --- |
| Email UptimeRobot | Vercel hoặc route `/health` không phản hồi | Mở Vercel Deployments/Runtime Logs, kiểm tra domain và deployment mới nhất; rollback deployment lỗi nếu cần. |
| Discord “Modal lỗi” | Timeout, 5xx, lỗi mạng, thiếu cấu hình hoặc job thất bại | Xem endpoint và thời gian trong tin, đối chiếu Vercel Runtime Logs và Modal Logs; kiểm tra container, Volume, secret và trạng thái job trước khi deploy lại. |
| Discord “sai khóa 401” | `MODAL_KEY` ở Vercel không khớp `DH_API_KEY` trong Modal secret | Người có quyền kiểm tra hai giá trị trong dashboard riêng, cập nhật đúng secret/biến rồi redeploy phần bị đổi; không gửi khóa qua chat. |
| Modal hết credit | GPU không khởi động hoặc Modal trả lỗi trong lúc sinh | Kiểm tra Billing, Usage, Spend limit và workspace; Studio báo không tạo được thiết kế. Ảnh mẫu chỉ còn ở phần trưng bày. |

CI `Modal backend checks` kiểm tra bằng mock CPU; nó không xác nhận GPU thật hoặc tự deploy Modal. Trước production, chạy thử 1 job sinh bốn ảnh và kiểm tra đường ảnh trên Vercel sau khi deploy Modal thủ công.
