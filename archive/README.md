# Lưu trữ — bản 09/2026 (trước vòng chung kết)

Thư mục này **không thuộc bản chung kết**. Giữ lại nguyên trạng để đối chiếu trước/sau, theo nguyên tắc không xoá dữ liệu.
Bản chung kết: xem [`README.md`](../README.md) ở thư mục gốc.

| Thư mục / tệp | Nội dung | Ghi chú |
|---|---|---|
| `web_ui_2026-09/` | Giao diện trình diễn bản 09/2026 (trước là `web_ui/legacy/`) | Các phát hiện về giao diện này nằm ở [`docs/finals/01_AUDIT.md`](../docs/finals/01_AUDIT.md) (A6, A10, A13). Ảnh thiết kế trong giao diện trỏ tới `../assets/images/variants/` nên khi mở từ vị trí lưu trữ sẽ không hiện ảnh. |
| `docs/mvp_spec_2026-09.md` | Đặc tả MVP bản 09/2026 (trước là `docs/mvp_spec.md`) | Tiêu chí tuyển ảnh C2 của bản chung kết vẫn kế thừa mục 4.2 của đặc tả này (`config/heritage_selection.json`). |
| `docs/smoketest_2026-09/` | Bằng chứng smoke test SD1.5 + ControlNet ban đầu (trước ở `docs/evidence/`) | Ảnh do `scripts/04_test_controlnet.py` sinh; mã SHA-256 ghi trong README của thư mục. |

Dữ liệu cũ không chuyển vào đây mà vẫn ở chỗ mã nguồn và Design Passport tham chiếu tới:

- `data/archive/2026-09_schema1/` — siêu dữ liệu hiện vật schema 1 (đầu vào của `scripts/08_migrate_heritage_metadata_v2.py`).
- `outputs/variants/`, `evaluation/variants.csv` — 24 thiết kế ngày 06/09/2026; Passport ghi đường dẫn và mã băm của các tệp này nên không di chuyển.
