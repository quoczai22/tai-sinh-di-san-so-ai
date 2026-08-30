# AGENT.MD — Ngữ cảnh nền tảng (KHÔNG được tự ý sửa)

> File này là "hiến pháp" chung cho mọi AI agent làm việc trên repo này (Codex, Claude Code, Antigravity). Mọi agent PHẢI đọc file này trước khi làm bất kỳ việc gì. Chỉ người dùng (chủ dự án) được sửa file này.

## 1. Dự án là gì

**Tái sinh Di sản Số** là nền tảng AI biến họa tiết gốm Bát Tràng thành thiết kế áo thun hiện đại, có lớp Cultural Governance Layer đảm bảo AI chỉ sáng tạo trong giới hạn có nguồn gốc và minh bạch.

Tài liệu tham chiếu bắt buộc đọc trước khi code, theo thứ tự:

1. `docs/mvp_spec.md` — đặc tả kỹ thuật đầy đủ 27 mục; là nguồn sự thật duy nhất. Nếu mâu thuẫn với PCCV/task.md, MVP Spec thắng và phải hỏi người dùng trước khi tự quyết.
2. `db/schema.sql` — schema database hiện tại (7 bảng).
3. `docs/erd.html` — sơ đồ ERD trực quan.
4. `docs/task.md` — trạng thái công việc hiện tại.

## 2. Kiến trúc tóm tắt (không được thay đổi nếu chưa hỏi người dùng)

`Knowledge Layer (RAG + Source-Grounded Rule Base) → Governance Layer (LLM Planner → Constraint Validator → Constraint Engine) → Generation Layer (Stable Diffusion 1.5 + ControlNet, LOCAL GPU 8GB — KHÔNG Colab/Kaggle) → Transparency & Assessment Layer (Visual Similarity/CLIP + Cultural Passport + Audit Log)`

Các quyết định đã chốt:

- Tech stack: SD1.5 (không SDXL), local GPU, BGE-M3 cho embedding, Supabase (Postgres + pgvector), FastAPI, Streamlit.
- Taxonomy cố định: `background`, `color_palette`, `composition_layout`, `core_motif`, `symbolic_element`, `product_context`, `material_texture`, `other_unclassified`.
- `rule_type`: `preserve` (BLOCK), `modifiable` (ALLOW), `restricted` (RESTRICT).
- LoRA fine-tune optional, không thuộc Definition of Done; không đặt threshold đạt/không đạt cho similarity score.
- Không làm trong 3 tuần: React, Mobile, Auth, Payment, Multi-heritage, LLM Critic layer riêng, cùng các mục tại mục 24 MVP Spec.

## 3. Vai trò từng agent

| Agent | Vai trò | Được làm | Không được làm |
| --- | --- | --- | --- |
| Codex | Manager | Đọc PCCV, tách task kỹ thuật hôm nay vào `task.md`, review kết quả Antigravity, cập nhật trạng thái | Tự viết phần lớn code triển khai; đổi quyết định kiến trúc khóa |
| Antigravity | Dev | Đọc `task.md` mục Hôm nay, code đúng task giao, ghi log sau khi xong | Mở rộng scope; tự sửa schema khi chưa được giao |
| Claude Code | Dev theo yêu cầu | Chỉ làm 1 task cụ thể được người dùng chỉ định sau khi đọc agent/task | Tự nhận thêm việc; bỏ qua agent/task |

## 4. Quy trình làm việc hàng ngày

1. Người dùng dán PCCV mới nhất đầu phiên.
2. Codex đối chiếu PCCV với `task.md`.
3. Codex cập nhật `task.md`: đánh dấu Done và ghi task Hôm nay đủ cụ thể để dev code ngay.
4. Antigravity chỉ làm đúng Hôm nay, ghi log Done/Blocked kèm lý do.
5. Claude Code, nếu được gọi, chỉ làm đúng task được chỉ định.

## 5. Quy tắc cứng

- Không thay đổi quyết định khóa ở mục 2 nếu chưa có xác nhận rõ ràng từ người dùng.
- Mọi phiên kết thúc bằng cập nhật `task.md`.
- Nếu tài liệu mâu thuẫn, ghi vào `task.md` mục `Cần xác nhận với người dùng`, không tự chọn.
- Không tạo file trạng thái/config khác ngoài `task.md` và `agent.md`.
