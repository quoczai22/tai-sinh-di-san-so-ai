# Đo thời gian sinh thiết kế

Tài liệu này định nghĩa từng con số thời gian ghi trong Design Passport (hồ sơ JSON mỗi thiết kế, ở `outputs/passports/`) và trong `manifest.json` (tệp tóm tắt mỗi lượt chạy, ở `outputs/runs/<run_id>/`).

## Vì sao cần

Trường `generation.duration_s` có từ trước chỉ là thời gian gọi Stable Diffusion một lần, của lần sinh hoa văn được chọn. Nó không gồm áo nền, các lần sinh lại, xếp bố cục, polish và kiểm tra chất lượng. Đọc nó như thời gian sinh cả thiết kế là sai. Trường này vẫn giữ nguyên nghĩa cũ để không vỡ dữ liệu cũ. Số đầy đủ nằm ở `generation.timing`.

## Cách đo

Mã đo nằm ở `tsds/core/timing.py`. Hàm `timed(store, key)` đo khối lệnh bên trong bằng `time.perf_counter()` (đồng hồ đơn điệu, không nhảy khi chỉnh giờ hệ thống). Chạy nhiều lần thì cộng dồn. Đơn vị là giây, làm tròn 2 chữ số.

## Các số của một thiết kế (`timing.design`)

| Khóa | Nghĩa |
|---|---|
| `pattern_selected_s` | Thời gian gọi Stable Diffusion của lần sinh hoa văn được chọn. Bằng `duration_s` cũ. |
| `pattern_total_s` | Cả bước hoa văn: mọi lần sinh lại, đo cổng G2 (cổng chất lượng hoa văn) và khớp bảng màu. |
| `layout_s` | Ghép hoa văn lên áo theo từng bố cục rồi CLIP xếp hạng. CLIP của bước này nạp lười, nên `layout_s` của thiết kế 1 còn gồm thời gian nạp CLIP đó (đo thật: thiết kế 1 chậm hơn các thiết kế sau khoảng 3 giây). |
| `polish_s` | Hoàn thiện img2img, gồm mọi lần polish lại và phép đo G3 trong vòng loại và thử lại. Lần polish đầu của lượt chạy còn gồm thời gian nạp model polish. |
| `quality_s` | Cổng chất lượng G2 và G3 cuối lượt (chạy trên CPU). |
| `design_s` | Từ lúc bắt đầu thiết kế đến hết kiểm tra chất lượng. Không gồm áo nền và nạp model. |

## Các số dùng chung cả lượt chạy (`timing.run`)

Các số này giống nhau trong cả 4 Passport của một lượt. Đừng cộng chúng cho từng thiết kế.

| Khóa | Nghĩa |
|---|---|
| `prepare_s` | Tách nền hiện vật, tạo ảnh tham chiếu và ảnh Canny. |
| `garment_s` | Sinh áo nền bằng LoRA và tách vùng áo bằng SAM. Thường là bước đơn lẻ lớn nhất. |
| `load_models_s` | Nạp Stable Diffusion + ControlNet và nạp CLIP chấm điểm tương đồng (`Scorer`). Không gồm model polish và CLIP của bước bố cục, hai model này nạp lười và nằm trong `polish_s`, `layout_s` của thiết kế đầu. |
| `set_s` | Tổng thời gian cả bộ, từ đầu thân hàm `generate_design_set` (sau các lệnh import) đến hết kiểm tra chất lượng. Không gồm bước ghi Passport và manifest (chưa đo, chỉ là ghi tệp). |
| `gpu`, `low_vram` | Máy đo. `low_vram` là `true` khi model chạy chế độ offload CPU, chậm hơn rõ rệt. |

`set_s` không bằng tổng `design_s` của 4 thiết kế, vì còn `prepare_s`, `garment_s`, `load_models_s`, thời gian của biến thể lỗi (nếu có, biến thể lỗi không có `design_s`), việc giải phóng model và vài bước nhỏ ở đầu hàm (đọc hiện vật, lưu ảnh tham chiếu). Mẫu đo thật ngày 28/11/2026 (hiện vật LR3D_61, RTX 4060 Laptop, một lượt): tổng `design_s` 97,52 giây cộng `prepare_s`, `garment_s`, `load_models_s` được 126,33 giây, `set_s` là 126,39 giây.

## Chưa đo

- Thời gian chờ trong hàng đợi của API (`/generate`). Số đo ở `docs/DEPLOY_LIVE.md` tính từ lúc gửi yêu cầu qua cổng, nên gồm cả phần này.
- Khởi động nguội của Modal.

## Chống sửa số

Khối `generation.timing` được ghi thêm vào sổ cái của Passport (sự kiện `timing`). Hàm `verify()` báo lỗi nếu thêm, sửa hoặc xóa khối làm hai bản không khớp, và báo lỗi băm nếu sổ cái bị sửa.

## Passport cũ

Passport tạo trước khi có tính năng này không có khối `timing`. Chúng vẫn hợp lệ. Muốn có số đo thì phải sinh lại.
