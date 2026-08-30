# TASK.MD — Trạng thái công việc (cập nhật mỗi ngày)

> Codex cập nhật mục "Hôm nay" sau khi đối chiếu PCCV mới nhất. Antigravity chỉ làm đúng mục "Hôm nay", ghi log vào mục "Log" khi xong. Nếu có mâu thuẫn với agent.md/mvp_spec.md → ghi vào mục "Cần xác nhận với người dùng", không tự quyết định.

---

## Hôm nay — Ngày 2 / 30-08-2026

> Chưa phân công triển khai: cần người dùng xác nhận mâu thuẫn PCCV với kiến trúc đã khóa trước khi lập task DevOps/Software.

- [ ] Blocked — Chờ xác nhận môi trường Generation Layer: local GPU 8GB (theo `docs/agent.md`/MVP Spec) hay Colab/Kaggle (theo PCCV đính kèm). Không triển khai khi chưa có xác nhận.

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

---

## Cần xác nhận với người dùng

- PCCV đính kèm, phần AI/Data Ngày 2, yêu cầu setup Stable Diffusion + ControlNet trên Colab/Kaggle; `docs/agent.md` và MVP Spec khóa Generation Layer là SD1.5 + ControlNet trên local GPU 8GB, không Colab/Kaggle. Theo quy tắc, chưa tự chọn phương án.
- Chưa có bản nguồn `db/schema.sql` và `docs/erd.html` trong repo hoặc tệp đính kèm. Cần cung cấp hai tệp này trước khi phân rã hay review các task database/API phụ thuộc schema.

---

## Backlog (task PCCV chưa tới lượt, để tham khảo không cần làm ngay)

- PCCV gốc được lưu tại `docs/Phan_Cong_Cong_Viec_Chi_Tiet.md` và `docs/PCCV.xlsx`; chỉ kéo task DevOps/Software lên "Hôm nay" sau khi mâu thuẫn trên được xác nhận.
