# 05. Quy trình đảm bảo chất lượng (Quality Assurance)

Trả lời yêu cầu cải tiến 1 của BTC: **đánh giá thiết kế cuối, không chỉ hoa văn trung gian**.

Nguyên tắc: máy đo những gì đo được bằng kỹ thuật (họa tiết còn không, dáng áo còn không, ảnh nét không, màu lệch không) và chỉ quyết định *đường đi tiếp*. Văn hoá và thẩm mỹ do chuyên gia quyết định. Không chỉ số nào tự phê duyệt thiết kế; hàm `approval_from_assessment` trong `quality/assess.py` không bao giờ trả trạng thái "đã phê duyệt".

## Chuỗi cổng

| Cổng | Đo gì | Ai | Không đạt thì |
|---|---|---|---|
| G0. Tuyển ảnh (C1–C4) và cổng quyền | Độ phân giải, mật độ nét, quyền, tính xác thực di sản | Hệ thống (C1–C3), người xác nhận (C4) | Không đưa hiện vật vào thư viện / không chạy ([07](07_PROVENANCE_COPYRIGHT.md)) |
| G2. Hoa văn | Rò dáng vật chứa (VLS), đường nối khi lát | Hệ thống | Sinh lại: đổi seed hoặc giảm trọng số một mức, giữ prompt và bảng màu; tối đa 3 lần |
| G3. Thiết kế cuối | Giữ họa tiết (PPS), giữ dáng áo (IoU), độ nét, lệch màu | Hệ thống | Sửa: khoá họa tiết hoặc giảm strength img2img |
| QC | Thiết kế có cảnh báo (WARN) | QC Officer | Chuyển chuyên gia kèm ghi chú, hoặc trả về sửa |
| Thẩm định | 5 tiêu chí văn hoá, thẩm mỹ, toàn vẹn | Chuyên gia (chấm mù) | Yêu cầu sửa (ghi lý do) hoặc loại |
| Xuất bản | Đã phê duyệt và quyền cho phép | Hệ thống | Chỉ cho tải xuống kèm nhãn phi thương mại |

## Định nghĩa phép đo

Tất cả nằm trong `quality/metrics.py`. Ảnh được chuyển sang không gian màu CIELAB.

| Phép đo | Cách tính | Ý nghĩa |
|---|---|---|
| VLS (rò dáng vật chứa) | Tỉ lệ viền ảnh hoa văn là nền trơn × IoU giữa hình bóng vật thể trong hoa văn và hình bóng hiện vật | Cao nghĩa là "hoa văn" thực chất là ảnh cái bình đặt trên nền |
| Tỉ lệ đường nối | Chênh lệch giữa mép trái và mép phải (và giữa mép trên và mép dưới) khi lát, chia cho chênh lệch trung bình giữa hai cột (hàng) kề nhau bên trong ảnh; lấy chiều lớn hơn | > 2 nghĩa là mắt thấy đường kẻ khi lát hoa văn lên vải |
| PPS (giữ họa tiết) | Căn chỉnh bản cuối với bản ghép (ECC, affine). Trong vùng có họa tiết, tính tương quan chuẩn hoá (NCC) của dải tần trung (hiệu hai Gaussian σ=1,2 và σ=4) trên kênh L*, và NCC của kênh a*, b*. PPS = trung bình của tương quan nét và tương quan sắc độ | 1 là giữ nguyên; dưới 0,4 nghĩa là dưới 16% phương sai nét vẽ còn lại — họa tiết đã bị vẽ lại |
| IoU dáng áo | Tách hình áo bằng GrabCut (khởi tạo từ mặt nạ áo mẫu) trên bản ghép và bản cuối, tính IoU | Dưới 0,92 tương đương lệch ≥ 8% diện tích áo |
| Tỉ lệ độ nét | Phương sai Laplacian của bản cuối chia cho của bản ghép, trong vùng áo | img2img làm mềm vải là chủ ý; dưới 0,25 thì họa tiết nhoè |
| Lệch màu | ΔE76 giữa màu Lab trung bình vùng họa tiết của bản ghép và bản cuối | ΔE ≈ 10 là khác màu thấy rõ khi đặt cạnh nhau |

CLIP vẫn được tính và lưu trong Passport (`reference_metrics`) nhưng **không tham gia quyết định**, vì nó đo hoa văn giai đoạn 1 so với ảnh gốm, không đo áo.

## Ngưỡng (QG-1.0, tạm thời)

Tệp `config/quality_gate.json`. Mỗi ngưỡng có cột "vì sao" trong tệp cấu hình.

| Cổng | Phép đo | Cảnh báo | Không đạt |
|---|---|---|---|
| G2 | VLS (thấp tốt) | ≥ 0,20 | ≥ 0,40 |
| G2 | Tỉ lệ đường nối (thấp tốt) | ≥ 1,5 | ≥ 2,0 |
| G3 | PPS (cao tốt) | < 0,60 | < 0,40 |
| G3 | IoU dáng áo (cao tốt) | < 0,95 | < 0,92 |
| G3 | Tỉ lệ độ nét (cao tốt) | < 0,45 | < 0,25 |
| G3 | Lệch màu ΔE (thấp tốt) | > 10 | > 20 |

Quyết định của một cổng là mức tệ nhất trong các phép đo của cổng đó. Quyết định chung là mức tệ hơn giữa G2 và G3.

**Vì sao gọi là tạm thời**: ngưỡng được đặt theo ý nghĩa của từng phép đo và quan sát trên 24 thiết kế ngày 06/09/2026, chưa đối chiếu với phiếu chuyên gia. Nhóm không trình bày ngưỡng này như đã được kiểm chứng.

## Sửa tự động: khoá họa tiết

`quality/repair.py`, phương pháp `pattern_lock_v1`. Đo trên 24 thiết kế cho thấy img2img giữ dáng áo gần như tuyệt đối (lệch căn chỉnh < 1 px) nhưng vẽ lại họa tiết. Vì hình học không lệch, có thể tách tần số:

- Kênh sáng: giữ phần tần thấp của bản img2img (bóng nếp vải, ánh sáng) và trả lại dải tần trung (nét vẽ) của bản ghép, chỉ trong vùng họa tiết (mặt nạ làm mềm 3 px).
- Kênh màu: kéo sắc độ về bản ghép với trọng số 0,85.
- Không nội suy lại ảnh khi lệch ≤ 1 px và co giãn ≤ 0,5%, vì nội suy làm mờ vi chi tiết vải (đo được: độ nét bản sửa tụt còn 0,17–0,39 khi luôn nội suy).

**Lưu ý quan trọng**: PPS của bản khoá họa tiết cao *do cách làm* (nét vẽ được chép lại từ bản ghép). PPS cao vì vậy **không chứng minh** bản khoá đẹp hơn hay giống vải in hơn. Bản khoá chỉ là ứng viên; nó được lưu thành phiên bản riêng (`system_repair`) cạnh bản img2img, và câu hỏi "bản nào tốt hơn" được giao cho chuyên gia chấm mù trong thí nghiệm EXP-B.

## Kết quả trên 24 thiết kế ngày 06/09/2026

Tệp: `evaluation/quality_gate_legacy.csv`. Ảnh đối chiếu (hiện vật, hoa văn, bản ghép, bản cuối, bản sửa) cho từng thiết kế: `docs/evidence/quality_gate/DP-*.jpg`. Dựng lại bằng `python scripts/10_build_legacy_runs.py`.

| | PASS | WARN | FAIL |
|---|---|---|---|
| G2 hoa văn | 21 | 1 | 2 |
| G3 thiết kế cuối (bản img2img) | 0 | 4 | 20 |
| G3 sau khoá họa tiết (19 thiết kế được sửa) | 10 | 9 | 0 |

- PPS bản img2img: trung vị 0,36 (thấp nhất 0,16, cao nhất 0,51). Đây là bằng chứng chính cho nhận xét của BTC rằng img2img toàn ảnh làm biến dạng hoa văn.
- IoU dáng áo: thấp nhất 0,93, không thiết kế nào dưới 0,92; 11 thiết kế ở mức cảnh báo (< 0,95). Dáng áo không phải vấn đề chính.
- Lệch màu: lớn nhất ΔE 8,1; không thiết kế nào vượt ngưỡng cảnh báo.
- Trạng thái Passport sau cổng: 10 chờ chuyên gia, 12 chờ QC, 2 không đạt.

### Ví dụ bị loại và được sửa

| Thiết kế | Chuyện gì xảy ra | Cổng | Xử lý |
|---|---|---|---|
| DP-HV01-20260906-V1, V2 | Hoa văn là ảnh nguyên chiếc bình (VLS 0,56 và 0,67) | G2 FAIL | Không sửa được ở giai đoạn 2; phải sinh lại hoa văn |
| DP-HV03-20260906-V2 | img2img vẽ lại họa tiết (PPS 0,37) | G3 FAIL | Khoá họa tiết → PPS 0,80, G3 PASS; chờ chuyên gia so mù hai bản |
| DP-HV04-20260906-V2 | PPS 0,46, IoU 0,94 | G3 WARN | Chuyển QC Officer xem |
| DP-HV02-20260906-V3 | PPS 0,16 (hiện vật ảnh 300×300) | G3 FAIL | Sau sửa PPS 0,58, vẫn WARN; hiện vật đã ngừng dùng |

### Giới hạn đã biết

- VLS bắt được trường hợp cả chiếc bình nằm trong hoa văn, nhưng **bỏ sót** trường hợp hoa văn là *mảnh* thân bình (HV06 V1, V2: VLS 0,10 và 0,04 dù nhìn bằng mắt thấy mảnh thân bình).
- HV06 V3 bị cảnh báo VLS 0,24 dù hoa văn không có dáng bình (cảnh báo nhầm).
- PPS đo mức giữ họa tiết **so với bản ghép**, không so với hiện vật gốc. Hoa văn giai đoạn 1 có giống hiện vật hay không vẫn là việc của chuyên gia (tiêu chí "Nhận ra họa tiết gốc").
- Chưa có phiếu chuyên gia thật nên chưa đo được mức đồng thuận giữa cổng tự động và người.

## Bộ tiêu chí chuyên gia (ER-1.0)

Tệp `config/expert_rubric.json`. Thang 1–5.

| Tiêu chí | Câu hỏi | Người chấm chính |
|---|---|---|
| Nhận ra họa tiết gốc | Đặt cạnh ảnh hiện vật, có nhận ra họa tiết bắt nguồn từ hiện vật này không? | Chuyên gia di sản |
| Phù hợp văn hoá | Biểu tượng có được dùng đúng ngữ cảnh không? | Chuyên gia di sản |
| Thẩm mỹ thiết kế | Bố cục, màu, tỉ lệ có hài hoà, mặc được không? | Chuyên gia thiết kế |
| Toàn vẹn dáng áo dài | Cổ, tay, tà, eo có đúng dáng áo dài không? | Chuyên gia thiết kế |
| Giống vải in thật | Họa tiết trông như in trên vải theo nếp hay như hình dán phẳng? | Chuyên gia thiết kế |

Quy tắc đạt: không tiêu chí nào dưới 3 **và** "Phù hợp văn hoá" từ 4 trở lên. Quyết định cuối vẫn là của chuyên gia; hệ thống chỉ đánh dấu "mâu thuẫn với quy tắc" khi quyết định "Đạt" trái với điểm.

Chấm mù: người chấm không thấy mã biến thể, trọng số, điểm của máy, hay quyết định của người khác; thứ tự hiển thị được xáo riêng cho từng người chấm.

## Hiệu chỉnh ngưỡng khi có phiếu chuyên gia

1. Thu tối thiểu 30 phiếu thẩm định trên các thiết kế có đủ kết quả G2/G3.
2. Với mỗi phép đo, coi quyết định chuyên gia ("Đạt" so với "Sửa/Loại") là nhãn. Quét các ngưỡng, chọn ngưỡng có độ đồng thuận cao nhất (Cohen's kappa hoặc balanced accuracy), báo cáo kèm ma trận nhầm lẫn.
3. Ghi ngưỡng mới thành phiên bản cấu hình mới (QG-1.1), **không sửa đè** QG-1.0. Passport cũ vẫn ghi phiên bản cấu hình đã dùng nên đọc lại được.
4. Nếu một phép đo không có ngưỡng nào đồng thuận tốt hơn ngẫu nhiên, hạ phép đo đó xuống chỉ cảnh báo, không chặn.

## Bằng chứng

| Bằng chứng BTC yêu cầu | Ở đâu |
|---|---|
| Bộ hiện vật – hoa văn – thiết kế cuối kèm phiếu đánh giá | `docs/evidence/quality_gate/DP-*.jpg` + `outputs/passports/DP-*.json` (mục `quality`, `reviews`) |
| Ví dụ bị loại và được sửa | Bảng "Ví dụ bị loại và được sửa" ở trên; phiên bản `system_repair` trong Passport |
| Phiếu chấm chuyên gia | Khu vực "Thẩm định chuyên gia" trên giao diện; gói chấm mù `outputs/experiments/EXP-C/blind/` |
