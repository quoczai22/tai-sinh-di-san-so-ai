# 05. Quy trình đảm bảo chất lượng (Quality Assurance)

Trả lời yêu cầu cải tiến 1 của BTC: **đánh giá thiết kế cuối, không chỉ hoa văn trung gian**.

Nguyên tắc: máy đo những gì đo được bằng kỹ thuật (họa tiết còn không, dáng áo còn không, ảnh nét không, màu lệch không) và chỉ quyết định *đường đi tiếp*. Văn hoá và thẩm mỹ do chuyên gia quyết định. Không chỉ số nào tự phê duyệt thiết kế; hàm `approval_from_assessment` trong `quality/assess.py` không bao giờ trả trạng thái "đã phê duyệt".

## Chuỗi cổng

| Cổng | Đo gì | Ai | Không đạt thì |
|---|---|---|---|
| G0. Tuyển ảnh (C1–C4) và cổng quyền | Độ phân giải, mật độ nét, quyền, tính xác thực di sản | Hệ thống (C1–C3), người xác nhận (C4) | Không đưa hiện vật vào thư viện / không chạy ([07](07_PROVENANCE_COPYRIGHT.md)) |
| Kiểm tra áo nền | Áo do LoRA sinh: mặt nạ áo hợp lệ (không chạm mép khung, diện tích 8% đến 55%, cao ít nhất 60% khung) | Hệ thống | Sinh ứng viên khác (tối đa 6); cả 6 bị loại thì báo lỗi, không sinh thiết kế |
| G2. Hoa văn | Rò dáng vật chứa (VLS), đường nối khi lát | Hệ thống | Vòng sinh lại hoa văn (mục dưới): đổi seed tối đa 3 lần; vẫn lỗi thì giữ bản ít lỗi nhất và đánh dấu "không đạt". Chưa thử giảm trọng số ControlNet |
| Hoàn thiện ảnh (polish) | PPS và IoU của ảnh vừa polish | Hệ thống | Vòng thử lại tự động (mục dưới): đổi seed, hạ độ nhiễu, cuối cùng trả bản ghép thô kèm nhãn |
| G3. Thiết kế cuối | Giữ họa tiết (PPS), giữ dáng áo (IoU), độ nét, giữ chi tiết mịn, lệch màu | Hệ thống | Đánh dấu "không đạt" kèm bước gợi ý; có ứng viên sửa bằng khoá họa tiết nếu G2 không lỗi |
| QC | Thiết kế có cảnh báo (WARN) | QC Officer | Chuyển chuyên gia kèm ghi chú, hoặc trả về sửa |
| Thẩm định | 5 tiêu chí văn hoá, thẩm mỹ, toàn vẹn | Chuyên gia (chấm mù) | Yêu cầu sửa (ghi lý do) hoặc loại |
| Xuất bản | Đã phê duyệt và quyền cho phép | Hệ thống | Chỉ cho tải xuống kèm nhãn phi thương mại |

## Định nghĩa phép đo

Tất cả nằm trong `quality/metrics.py`. Ảnh được chuyển sang không gian màu CIELAB. "Bản ghép" là ảnh ghép tất định hoa văn lên áo, trước polish.

| Phép đo | Cách tính | Ý nghĩa |
|---|---|---|
| VLS (rò dáng vật chứa) | Tỉ lệ viền ảnh hoa văn là nền trơn × IoU giữa hình bóng vật thể trong hoa văn và hình bóng hiện vật | Cao nghĩa là "hoa văn" thực chất là ảnh cái bình đặt trên nền |
| Tỉ lệ đường nối | Chênh lệch giữa mép trái và mép phải (và giữa mép trên và mép dưới) khi lát, chia cho chênh lệch trung bình giữa hai cột (hàng) kề nhau bên trong ảnh; lấy chiều lớn hơn | > 2 nghĩa là mắt thấy đường kẻ khi lát hoa văn lên vải |
| PPS (giữ họa tiết) | Căn chỉnh bản cuối với bản ghép (ECC, affine). Trong vùng có họa tiết, tính tương quan chuẩn hoá (NCC) của dải tần trung (hiệu hai Gaussian σ=1,2 và σ=4) trên kênh L*, và NCC của kênh a*, b*. PPS = trung bình của tương quan nét và tương quan sắc độ | 1 là giữ nguyên; dưới 0,4 nghĩa là dưới 16% phương sai nét vẽ còn lại, họa tiết đã bị vẽ lại |
| IoU dáng áo | Tách hình áo bằng GrabCut (khởi tạo từ mặt nạ áo SAM của chính thiết kế) trên bản ghép và bản cuối, tính IoU | Dưới 0,92 tương đương lệch ≥ 8% diện tích áo. Với polish chỉ vùng áo, giá trị luôn gần 1 |
| Tỉ lệ độ nét | Phương sai Laplacian của bản cuối chia cho của bản ghép, trong vùng áo | Dưới 0,25 thì họa tiết nhoè |
| Giữ chi tiết mịn (`detail_ratio`) | Phương sai Laplacian của bản cuối chia cho của bản ghép, **chỉ trong vùng họa tiết** | Bắt được nét mảnh bị nhoè mà PPS (chỉ đo dải tần trung) và độ nét (đo cả vùng áo, phần lớn là vải trơn) bỏ sót. Dưới 0,6 là lỗi |
| Lệch màu | ΔE76 giữa màu Lab trung bình vùng họa tiết của bản ghép và bản cuối | ΔE ≈ 10 là khác màu thấy rõ khi đặt cạnh nhau |
| Trôi ngoài áo (M2) | Sai khác tuyệt đối trung bình giữa bản ghép và bản cuối ở ngoài mặt nạ áo, thang 0 đến 255 | Polish chỉ vùng áo cho đúng 0. Chỉ đo và ghi, chưa dùng làm ngưỡng |

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
| G3 | Giữ chi tiết mịn (cao tốt) | < 0,85 | < 0,60 |
| G3 | Lệch màu ΔE (thấp tốt) | > 10 | > 20 |

Quyết định của một cổng là mức tệ nhất trong các phép đo của cổng đó. Quyết định chung là mức tệ hơn giữa G2 và G3.

**Vì sao gọi là tạm thời**: ngưỡng được đặt theo ý nghĩa của từng phép đo và quan sát trên các thiết kế đã sinh, chưa đối chiếu với phiếu chuyên gia. Chỉ số `detail_ratio` được thêm vào QG-1.0 ngày 19/11/2026 sau khi phát hiện khoá họa tiết cũ làm mất nét mảnh; Passport sinh trước ngày đó không có chỉ số này. Nhóm không trình bày ngưỡng như đã được kiểm chứng.

## Hoàn thiện ảnh: polish chỉ vùng áo, khoá họa tiết, vòng thử lại

Bước hoàn thiện (`generation/garment.py::polish_locked`) gồm ba việc nối tiếp:

1. **Polish chỉ vùng áo** (Stable Diffusion 1.5 img2img, độ nhiễu 0,20): ảnh polish chỉ được dùng trong mặt nạ áo; ngoài áo giữ nguyên từng pixel của bản ghép (trôi ngoài áo bằng 0). Mặc định cũ là polish toàn ảnh độ nhiễu 0,40; EXP-B cho thấy cách này làm PPS tụt còn 0,30 và làm lệch dáng áo (IoU 0,956 so với 0,993 ở polish chỉ vùng áo), vì nền và tay cũng bị vẽ lại.
2. **Khoá họa tiết** (`quality/repair.py`, `pattern_lock_v1`): giữ phần tần thấp của ảnh polish (bóng nếp vải, ánh sáng) và trả lại nét vẽ và màu của họa tiết từ bản ghép, chỉ trong vùng họa tiết (mặt nạ làm mềm 3 px). Kênh sáng trả lại mọi tần số mịn hơn σ = 4 px của bản ghép (`dog_sigma_low` = 0,3, `dog_sigma_high` = 4,0); kênh màu kéo về bản ghép với trọng số 0,85. Sau cùng ép phần ngoài áo về đúng bản ghép.
3. **Vòng thử lại** (`quality/retry.py`): đo cổng G3 trên ảnh vừa hoàn thiện. Nếu **PPS dưới 0,40 hoặc IoU dưới 0,92** (hai chỉ số ở mức lỗi) thì thử lại theo thứ tự: seed gốc, rồi 3 seed kế tiếp cùng độ nhiễu 0,20, rồi hạ độ nhiễu xuống 0,12 một lần; vẫn lỗi thì **trả bản ghép thô** kèm nhãn "chưa qua bước hoàn thiện". Tối đa 5 lần polish. Mọi lần bị loại ghi vào `outputs/qc/rejects.csv` kèm ảnh. Các chỉ số khác (độ nét, chi tiết mịn, lệch màu) chỉ cảnh báo, không kích hoạt thử lại.

Căn cứ chọn cấu hình là `evaluation/polish_finish_trial.csv` (xem [06](06_EXPERIMENTS.md)): trên 12 thiết kế, khoá họa tiết cũ (`dog_sigma_low` 1,2) cho PPS cao (0,91) nhưng chi tiết mịn thấp (0,61); `dog_sigma_low` 0,3 giữ chi tiết mịn 0,83 và không thiết kế nào bị loại.

**Lưu ý quan trọng**: PPS của bản có khoá họa tiết cao *do cách làm* (nét vẽ được chép lại từ bản ghép). PPS cao vì vậy **không chứng minh** bản khoá đẹp hơn hay giống vải in hơn. Với khoá họa tiết, bản cuối rất gần bản ghép thô; phần polish còn lại chủ yếu chỉnh ánh sáng. Câu hỏi "bản nào đẹp hơn" được giao cho chuyên gia chấm mù.

## Sinh lại hoa văn khi G2 lỗi

Vòng này (`quality/pattern_retry.py`, gọi từ `generation/streamlit_runner.py`) đo G2 ngay sau khi sinh hoa văn, trước khi ghép lên áo, để không phí công polish và cổng G3 cho một hoa văn chắc chắn bị loại.

1. Sinh hoa văn với seed gốc rồi đo G2 (trên đúng ảnh sẽ dùng, sau khi khớp bảng màu).
2. Chỉ **LỖI** mới kích hoạt: VLS từ 0,40 hoặc đường nối từ 2,0. Cảnh báo (WARN) dùng luôn, giống vòng polish.
3. Sinh lại với seed gốc cộng 1, cộng 2, cộng 3 (tối đa `max_retries` = 3 lần sinh lại, giữ nguyên prompt, trọng số ControlNet và bảng màu). Seed polish vẫn là seed gốc.
4. Vẫn lỗi sau mọi lần: giữ bản ít lỗi nhất (chỉ số tệ nhất so với ngưỡng lỗi thấp nhất), trạng thái `best_of_failed`. G2 vẫn báo LỖI nên Passport ghi `qa_failed` và thiết kế bị ẩn khỏi giao diện, không có gì bị che giấu.
5. Lỗi ở bước đo (không phải bước sinh) không làm mất ảnh và không sinh lại; ảnh được dùng với trạng thái `unmeasured`.

Mọi lần bị loại ghi vào `outputs/qc/pattern_rejects.csv` và `outputs/qc/pattern_rejects/`. Passport ghi `generation.pattern_seed` (seed hoa văn thực dùng) và `generation.pattern_retry` (trạng thái và từng lần thử, kèm giá trị VLS và đường nối). Tắt cho một biến thể bằng `pattern_retry: false`.

**Thử thật trên LR3D_124** (hiện vật có 3 thiết kế bị loại ở bộ demo, seed 42, 20/11/2026, RTX 4060 Laptop): thiết kế 1 được cứu ở lần thử thứ 4 (seed 45, đường nối từ 2,71 xuống 1,54, còn cảnh báo). Thiết kế 2 và 3 cả 4 lần đều lỗi (đường nối 2,17 đến 5,94), giữ bản ít lỗi nhất và vẫn `qa_failed`. Thiết kế 4 đạt ngay. Mỗi lần sinh lại thêm khoảng 10 đến 12 giây, nên lượt chạy này mất 263 giây thay vì khoảng 100 đến 150 giây.

**Kết luận và giới hạn**: đổi seed chỉ cứu được một phần. Trong 4 thiết kế của LR3D_124, chỉ thiết kế mức 4 (trọng số ControlNet 0,25, thấp nhất) đạt ngay, ba mức có trọng số cao hơn (0,85, 0,65, 0,45) đều lỗi đường nối. Nghi ngờ nguyên nhân do mảng phẳng của LR3D_124 có rìa lệch nên đường nét điều khiển dính vào mép, trọng số càng cao càng lộ. Chưa làm bước giảm trọng số ControlNet ở lần thử cuối (cấu hình G2 có nêu hướng này) vì nó đổi ý nghĩa của mức sáng tạo, cần nhóm quyết định.

## Kết quả bộ demo hiện tại (19/11/2026)

Bộ 24 thiết kế (6 hiện vật LR3D-CULT2 × 4 mức sáng tạo) sinh bằng `scripts/14_generate_demo_set.py`: mỗi hiện vật một áo LoRA riêng, ảnh nạp là mảng hoa văn phẳng, polish chỉ vùng áo 0,20 kèm khoá họa tiết. Kết quả đọc từ Passport (`GET /quality/designs`).

| | PASS | WARN | FAIL |
|---|---|---|---|
| G2 hoa văn | 16 | 5 | 3 |
| G3 thiết kế cuối | 14 | 10 | 0 |
| Tổng thể (mức tệ hơn của G2 và G3) | 9 | 12 | 3 |

| Phép đo (n = 24) | Trung bình | Thấp nhất | Cao nhất |
|---|---|---|---|
| PPS | 0,943 | 0,891 | 0,980 |
| IoU dáng áo | 0,995 | 0,977 | 0,999 |
| Độ nét | 0,846 | 0,684 | 0,941 |
| Giữ chi tiết mịn | 0,855 (trung vị 0,869) | 0,716 | 0,947 |
| Lệch màu ΔE | 1,21 | 0,22 | 1,96 |
| VLS | 0,038 | 0,000 | 0,221 |

- Cả 24 thiết kế qua polish ngay lần đầu; vòng thử lại không chạy lần nào.
- Cả 10 cảnh báo G3 đến từ chỉ số giữ chi tiết mịn (dưới 0,85). Các chỉ số khác của G3 đều đạt ở cả 24 thiết kế. Nghĩa là bản cuối vẫn mất trung bình khoảng 14% chi tiết mịn so với bản ghép thô.
- G2: 3 thiết kế bị loại đều của hiện vật HV12 (LR3D_124) do đường nối (2,41 đến 3,04); 3 thiết kế cảnh báo VLS (0,201 đến 0,221) và 2 cảnh báo đường nối (1,59 và 1,92).
- Trạng thái Passport sau cổng: 9 chờ chuyên gia, 12 chờ QC, 3 không đạt (3 thiết kế này bị ẩn khỏi trang chủ và trang Kết quả).

### Mốc so sánh: bản 06/09/2026 (số liệu lịch sử)

Trên 24 thiết kế cũ (6 hiện vật × 4, áo mẫu cố định, polish toàn ảnh 0,40): G2 đạt 21, cảnh báo 1, lỗi 2; G3 đạt 0, cảnh báo 4, lỗi 20; PPS trung vị 0,36 (thấp nhất 0,16); IoU thấp nhất 0,93; lệch màu lớn nhất ΔE 8,1; sau khoá họa tiết (σ 1,2) 19 thiết kế được sửa: đạt 10, cảnh báo 9. Đó là bằng chứng chính cho nhận xét của BTC rằng polish toàn ảnh làm biến dạng hoa văn. Ảnh, Passport và bảng đo của bộ này đã xoá khỏi cây làm việc ngày 19/11/2026 (nhóm chỉ dùng ảnh do LoRA sinh); khôi phục từ commit `b1192b0` (`evaluation/quality_gate_legacy.csv`, `docs/evidence/quality_gate/`).

### Ví dụ bị loại và được sửa

| Trường hợp | Chuyện gì xảy ra | Xử lý | Bằng chứng |
|---|---|---|---|
| `DP-HV12-20261119T162748-V1`, `V2`, `V3` | Hoa văn có đường nối lớn khi lát (2,71, 3,04 và 2,41); mảng phẳng của LR3D_124 có rìa lệch | G2 loại, trạng thái `qa_failed`, ẩn khỏi Bộ sưu tập; cần sinh lại hoa văn (chưa tự động) | Passport hiện tại |
| `DP-HV10-20261119T162255-V1`, `V2` và `DP-HV07-20261119T161630-V1` | VLS 0,221, 0,203 và 0,201, lọt nhẹ hình vật chứa | G2 cảnh báo, chờ QC xem | Passport hiện tại |
| Bộ demo trước (polish 0,30, chưa khoá họa tiết): HV07 V3 | PPS 0,36, 0,3995, 0,3983, 0,3756 ở 4 seed (seed 42 đến 45) đều dưới 0,40 | Hạ độ nhiễu xuống 0,22 và thử lần 5: đạt | `outputs/qc/rejects.csv` và ảnh bị loại trong commit `900ee09` |
| Bộ demo trước: HV11 V3 và V4 | PPS 0,23 đến 0,37 ở cả 5 lần thử | Trả bản ghép thô kèm nhãn "chưa qua bước hoàn thiện" | như trên |
| Bộ demo trước: HV12 V1 | PPS 0,3997 và 0,3976 ở seed 42 và 43 | Đạt ở seed 44 | như trên |
| Khoá họa tiết cũ (σ 1,2) | PPS cao (0,91) nhưng mất nét mảnh, giữ chi tiết mịn 0,61; 6/12 thiết kế loại theo chỉ số mới | Đổi `dog_sigma_low` 0,3, thêm chỉ số `detail_ratio` | `evaluation/polish_finish_trial.csv` |
| Bản 06/09/2026: HV01 V1, V2 | Hoa văn là ảnh nguyên chiếc bình (VLS 0,56 và 0,67) | G2 loại (lịch sử); nay mặc định nạp mảng phẳng nên VLS lớn nhất chỉ 0,22 | commit `b1192b0` |

### Giới hạn đã biết

- VLS bắt được trường hợp cả chiếc bình nằm trong hoa văn, nhưng **bỏ sót** trường hợp hoa văn là *mảnh* thân bình hoặc mảng nền (đã thấy ở bản 06/09/2026).
- PPS đo mức giữ họa tiết **so với bản ghép**, không so với hiện vật gốc. Hoa văn giai đoạn 1 có giống hiện vật hay không vẫn là việc của chuyên gia (tiêu chí "Nhận ra họa tiết gốc").
- Với khoá họa tiết, PPS gần 0,94 do cách làm; không dùng để so độ đẹp.
- IoU dáng áo gần 1 vì polish chỉ vùng áo; nó không đo áo LoRA có giống áo dài truyền thống hay không. Áo LoRA vẫn thường tay loe và thắt eo; nhóm chấp nhận tay loe. Việc này chỉ chấm mù mới trả lời.
- Ngưỡng `detail_ratio` (0,85 và 0,6) đặt theo quan sát trên bộ demo, chưa đối chiếu với người xem.
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

Việc xem xét của chuyên gia là một bước **ngoài hệ thống**: nhóm mời người am hiểu xem mẫu, thu phiếu, rồi đưa kết quả vào báo cáo. Giao diện web cho người xem không còn trang thẩm định; API ghi phiếu (`POST /passports/{id}/reviews`) vẫn có và phiếu được ghi vào Passport.

## Gói đánh giá mù cho chuyên gia

`scripts/18_build_blind_review.py` dựng gói chấm mù cho cả 24 thiết kế của bộ demo, kể cả 3 thiết kế mà cổng chất lượng đã loại (để đo mức đồng thuận giữa cổng tự động và chuyên gia). Kết quả nằm trong `outputs/blind_review/` (ảnh, không đưa lên git).

- `GOI_GUI/` (và `GOI_GUI.zip`) gửi người chấm. Gồm một trang `index.html` mở offline bằng trình duyệt, ảnh thiết kế đã đổi tên mã ngẫu nhiên và ảnh hiện vật đối chiếu. Không có mã Passport, mức sáng tạo, điểm hay quyết định của cổng.
- `GIU_RIENG/` nhóm giữ: `key.csv` (mã trỏ về Passport, hiện vật, mức sáng tạo, kết quả G2 và G3, trạng thái duyệt) và `HUONG_DAN_NOI_BO.md` (cách gửi, thu, giải mã).
- Người chấm nhập mã riêng (ví dụ CG01) và chọn vai: chuyên gia di sản chấm 2 tiêu chí, chuyên gia thiết kế chấm 3 tiêu chí, người am hiểu cả hai chấm đủ 5, theo trường `owner` của bộ tiêu chí ER-1.0. Mỗi thiết kế còn có quyết định Đạt, Cần chỉnh sửa hoặc Loại và ô nhận xét.
- Thứ tự thiết kế được xáo riêng theo mã người chấm. Trang tự lưu nháp trong trình duyệt và xuất `ratings_<mã>.csv`.
- Cần ít nhất 1 chuyên gia di sản và 1 chuyên gia thiết kế; 24 thiết kế do 2 người chấm là 48 phiếu, đủ mốc 30 phiếu để hiệu chỉnh ngưỡng. Chưa có công cụ tự động tổng hợp phiếu và so với cổng.

## Hiệu chỉnh ngưỡng khi có phiếu chuyên gia

1. Thu tối thiểu 30 phiếu thẩm định trên các thiết kế có đủ kết quả G2/G3.
2. Với mỗi phép đo, coi quyết định chuyên gia ("Đạt" so với "Sửa/Loại") là nhãn. Quét các ngưỡng, chọn ngưỡng có độ đồng thuận cao nhất (Cohen's kappa hoặc balanced accuracy), báo cáo kèm ma trận nhầm lẫn.
3. Ghi ngưỡng mới thành phiên bản cấu hình mới (QG-1.1), **không sửa đè** QG-1.0. Passport cũ vẫn ghi phiên bản cấu hình đã dùng nên đọc lại được.
4. Nếu một phép đo không có ngưỡng nào đồng thuận tốt hơn ngẫu nhiên, hạ phép đo đó xuống chỉ cảnh báo, không chặn.

## Bằng chứng

| Bằng chứng BTC yêu cầu | Ở đâu |
|---|---|
| Bộ hiện vật, hoa văn, thiết kế cuối | `outputs/runs/R<thời điểm>-<mã>/`: `00_reference.png` (ảnh nạp), `V<n>_pattern.png`, `V<n>_aodai_raw.png`, `V<n>_aodai.png`, `garment.png`; Passport `outputs/passports/DP-*.json` (mục `quality`) |
| Phiếu nhận xét của người am hiểu | **Chưa có phiếu thật.** Phiếu mẫu và gói chấm mù: `outputs/experiments/EXP-D/blind/` (ảnh không đưa vào repo) |
| Ví dụ bị loại và được sửa | Bảng "Ví dụ bị loại và được sửa" ở trên; `outputs/qc/rejects.csv` và ảnh bị loại trong commit `900ee09`; `evaluation/polish_finish_trial.csv` |
