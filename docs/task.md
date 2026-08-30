# TASK.MD — Trạng thái công việc (cập nhật mỗi ngày)

> Codex cập nhật mục "Hôm nay" sau khi đối chiếu PCCV mới nhất. Antigravity chỉ làm đúng mục "Hôm nay", ghi log vào mục "Log" khi xong. Nếu có mâu thuẫn với agent.md/mvp_spec.md → ghi vào mục "Cần xác nhận với người dùng", không tự quyết định.

> Quy tắc dọn sớm: task đã được Codex review và xác nhận Done chỉ giữ một dòng tóm tắt trong lũy kế; log/mô tả chi tiết được rút gọn cuối phiên. Codex giữ file này dưới 300 dòng, không xóa tài liệu nguồn hay lịch sử Git.

---

## Hôm nay — Ngày 2 / 30-08-2026

> Chưa phân công triển khai: cần người dùng xác nhận mâu thuẫn PCCV với kiến trúc đã khóa trước khi lập task DevOps/Software.

- [ ] Blocked — Chờ xác nhận môi trường Generation Layer: local GPU 8GB (theo `docs/agent.md`/MVP Spec) hay Colab/Kaggle (theo PCCV đính kèm). Không triển khai khi chưa có xác nhận.
- [x] Antigravity — Tạo `backend/app/` với đúng 3 file Python và `backend/requirements.txt`; không thêm module ngoài phạm vi.
- [x] Antigravity — Tạo `backend/.env.example` chỉ với placeholder `SUPABASE_URL` và `SUPABASE_SERVICE_ROLE_KEY`; không ghi secret thật.
- [x] Antigravity — Tạo/activate `backend/venv`, cài `requirements.txt`, chạy `uvicorn app.main:app --reload` và kiểm tra `GET /health` trả HTTP 200; ghi log kết quả, không commit `venv/` hoặc `.env`.

---

## Đã hoàn thành (lũy kế)

| Ngày | Task | Agent thực hiện | Ghi chú |
| --- | --- | --- | --- |
| 1 (29/8) | Khởi tạo GitHub repo | Antigravity | — |
| 1 (29/8) | Setup môi trường AI local (SD1.5+ControlNet) | AI/Data | Tham khảo, không thuộc quản lý file này |
| 2 (30/8) | Lưu tài liệu nền tảng và thiết lập `.gitignore` | Codex | Không commit/push trong phiên này |

---

## Log (Antigravity ghi sau khi xong việc)

> Format: `[Ngày] [Task] — [Done/Blocked] — [Ghi chú ngắn]`

- [30-08-2026] [Thiết lập quản lý repo] — Done — Lưu MVP Spec/PCCV, thêm `.gitignore`; chưa có code sản phẩm hay commit/push.
- [30-08-2026] [Khởi tạo backend FastAPI & Supabase config] — Done — Tạo backend/app/ (main.py, config.py, supabase_client.py), requirements.txt, .env.example, tạo venv, cài thư viện và test GET /health trả về HTTP 200 {"status": "ok"}.

---

## Cần xác nhận với người dùng

- PCCV đính kèm, phần AI/Data Ngày 2, yêu cầu setup Stable Diffusion + ControlNet trên Colab/Kaggle; `docs/agent.md` và MVP Spec khóa Generation Layer là SD1.5 + ControlNet trên local GPU 8GB, không Colab/Kaggle. Theo quy tắc, chưa tự chọn phương án.
- Đã lưu schema SQL mới nhất vào `db/schema.sql`; vẫn chưa có `docs/erd.html` để đối chiếu trực quan.
- Supabase credentials đã được gửi trong chat; không lưu lại các giá trị này. Cần rotate `service_role` (và nên rotate anon key nếu muốn) trên Supabase trước khi tạo `.env` local.
- [30-08-2026] Kiểm tra `.env`: URL/JWT đúng định dạng và mạng tới Supabase thông, nhưng REST trả `401 Unauthorized`; cần kiểm tra key có thuộc đúng project/đã rotate hay chưa.

---

## Backlog (task PCCV chưa tới lượt, để tham khảo không cần làm ngay)

- PCCV gốc được lưu tại `docs/Phan_Cong_Cong_Viec_Chi_Tiet.md` và `docs/PCCV.xlsx`; chỉ kéo task DevOps/Software lên "Hôm nay" sau khi mâu thuẫn trên được xác nhận.
