# Nhật ký thí nghiệm

Nhật ký này gom lại theo thứ tự thời gian mọi thí nghiệm đã chạy: câu hỏi, cấu hình, kết quả, kết luận, quyết định tiếp theo. Mục đích: làm gốc để viết báo cáo và paper. Số liệu lấy từ `outputs/experiments/EXP-*/results.csv` và `summary.json`, đã đối chiếu với [06_EXPERIMENTS.md](finals/06_EXPERIMENTS.md) và [KET_QUA_EXP_G.md](KET_QUA_EXP_G.md). Ô ghi **[CẦN BỔ SUNG]** là thông tin chưa có trong repo, nhóm cần tự điền.

## Quy ước

- **Lượt chạy**: một tổ hợp (hiện vật, mức của biến độc lập, seed). Mỗi lượt ra một ảnh có SHA-256.
- **PPS** (Pattern Preservation Score): mức giữ họa tiết của ảnh cuối so với bản ghép thô. **IoU**: mức giữ dáng áo. **ΔE**: độ lệch màu. **Chi tiết mịn** (`detail_ratio`): mức giữ nét mảnh. **VLS** (`vessel_leakage`): mức hình bình lọt vào hoa văn, thấp là tốt. **Đường nối** (`seam_ratio`): độ lộ đường nối khi lát ô, thấp là tốt.
- Kiểm định: Wilcoxon có dấu cho từng cặp so với mức đối chứng, Friedman khi có từ 3 mức. Mẫu nhỏ nên p chỉ để tham khảo.
- Mọi thí nghiệm dùng 6 hiện vật gốm LR3D-CULT2 đang dùng, trừ EXP-C (6 hiện vật cũ).
- **Chấm mù thật mới có ở EXP-A**, do 28 người quan tâm (không phải chuyên gia), độ đồng thuận thấp (alpha 0,03). Các thí nghiệm khác chưa chấm mù; các phiếu `ratings_CG01..03.csv` của chúng là mẫu trống. Mọi kết luận về "đẹp hơn" hay "giống vải in hơn" cho từng thiết kế đều chưa được kiểm.

## Tổng quan

| Mã | Ngày chạy | Biến độc lập | Số lượt | Trạng thái | Quyết định rút ra |
|---|---|---|---|---|---|
| EXP-C | 18/11/2026 | Chế độ ghép tất định (bỏ displacement, shading, color grade) | 24 | Đã chạy, trên 6 hiện vật cũ | Displacement đổi ảnh nhiều nhất; chưa biết có lợi không |
| EXP-B | 19/11/2026 | Cách hoàn thiện (polish) | 126 | Đã chạy | Polish chỉ vùng áo, độ nhiễu thấp, khoá họa tiết |
| EXP-D | 19/11/2026 | Nguồn áo nền (cố định hay LoRA) | 60 | Đã chạy | Không khác biệt; chọn LoRA vì lý do thiết kế |
| EXP-E | 19/11/2026 | Ảnh nạp ControlNet (bình render hay mảng phẳng) | 36 | Đã chạy | Chuyển mặc định sang mảng phẳng |
| EXP-F | 20/11/2026 | Như EXP-E, chạy lại trên pipeline hiện tại | 36 | Đã chạy | Mảng phẳng giữ họa tiết và màu tốt hơn; ControlNet vẫn bịa họa tiết |
| EXP-G | 20/11/2026 | Cách tạo ô hoa văn (5 mức) | 90 | Đã chạy | `paste_direct` giữ họa tiết nhất; cần sửa màu mờ (`paste_boost`) |
| EXP-A | 20/11/2026 | Trọng số ControlNet | 120 | Đã chạy; 28 người quan tâm chấm mù (22 đến 23/11) | Hạ trọng số giảm lọt hình bình và giảm điểm "nhận ra họa tiết gốc"; người chấm ít đồng thuận (alpha 0,03) |

Ghi chú: cả sáu tệp đặc tả trong `tsds/evaluation/experiments/` từng ghi `"status": "planned"` dù đã chạy xong. Ngày 24/11/2026 đã sửa thành `completed` (mỗi thí nghiệm đều có `results.csv`).

---

## EXP-C: từng bước ghép tất định

- **Ngày:** 18/11/2026 (`summary.json`: 05:14 UTC). Chạy trên CPU.
- **Câu hỏi:** mỗi bước ghép (displacement, shading, color grade) đổi ảnh bao nhiêu?
- **Thiết kế:** 4 chế độ (đầy đủ, bỏ displacement, bỏ shading, bỏ color grade), 6 hiện vật cũ, không lặp seed (tất định). 24 lượt.
- **Kết quả** (PPS so với bản đầy đủ): bỏ displacement 0,851; bỏ shading 0,965; bỏ color grade 0,958. Friedman χ² = 16,2, p = 0,001. Wilcoxon mỗi chế độ p = 0,031 (giá trị nhỏ nhất có thể với 6 cặp).
- **Kết luận:** displacement làm ảnh thay đổi nhiều nhất. "Thay đổi" không có nghĩa "có lợi".
- **Hạn chế:** chạy trên áo mẫu cố định đã bỏ khỏi luồng nên không chạy lại được. Ảnh đã xoá 19/11/2026; còn `plan.csv`, `results.csv`, `summary.json`. Khôi phục ảnh từ commit `b1192b0`.
- **Bài học cho paper:** đây là ablation bước ghép. Cần thêm chấm mù để biết bước nào thực sự làm ảnh "giống vải in".

## EXP-B: bước hoàn thiện (polish)

- **Ngày:** 19/11/2026. Commit `ab37b7d`.
- **Câu hỏi:** polish làm mất bao nhiêu họa tiết, khoá họa tiết giữ lại được bao nhiêu?
- **Thiết kế:** 7 cách hoàn thiện, 6 hiện vật, 3 seed polish (42, 7, 123). 126 lượt. Cấu hình lúc chạy: áo mẫu cố định, ảnh nạp là ảnh bình render, hoa văn seed 42.
- **Kết quả chính** (PPS, bản không polish bằng 1): polish toàn ảnh 0,40 (cách cũ) còn 0,303; polish toàn ảnh 0,25 còn 0,494; khoá họa tiết đưa lên 0,809 đến 0,862. IoU: polish chỉ vùng áo 0,993, toàn ảnh 0,956. Friedman χ² = 106,6, p < 0,001.
- **Kết luận:** polish toàn ảnh làm mất hai phần ba họa tiết. Độ nhiễu thấp giữ tốt hơn. PPS của bản khoá cao một phần do cách làm (chép nét từ bản ghép) nên không chứng minh đẹp hơn.
- **Quyết định:** luồng sản phẩm chuyển sang polish chỉ vùng áo, khoá họa tiết mặc định.
- **Hạn chế:** ảnh EXP-B chưa từng commit và đã xoá 19/11/2026, không khôi phục được. Còn số liệu trong `results.csv`.
- **Thử bổ sung cùng ngày** (`evaluation/polish_finish_trial.py`, kết quả `evaluation/polish_finish_trial.csv`): 12 thiết kế trên bộ demo mới. Khoá họa tiết cũ (`dog_sigma_low` 1,2) làm mất nét mảnh (chi tiết mịn 0,56 đến 0,61, 8/12 và 6/12 thiết kế bị loại). Với `dog_sigma_low` 0,3, chi tiết mịn 0,83, không thiết kế nào bị loại. Chọn độ nhiễu 0,20 và `dog_sigma_low` 0,3 làm mặc định. Đây là cơ sở của chỉ số `detail_ratio` trong cổng G3.

## EXP-D: nguồn áo nền

- **Ngày:** 19/11/2026. Commit `2d821d5`, chạy lại ở `5a5fee4` sau khi sửa lỗi.
- **Câu hỏi:** áo dài nền do LoRA sinh so với áo mẫu cố định.
- **Thiết kế:** 2 mức, 6 hiện vật, 5 seed (42 đến 46). 60 lượt. Cố định: ảnh nạp mảng phẳng, polish chỉ vùng áo 0,30, bố cục "Dải thân trước".
- **Kết quả:** không khác biệt có ý nghĩa ở chỉ số nào (PPS 0,452 và 0,475, p = 0,37; IoU p = 0,58; ΔE p = 1,00). 30/30 áo LoRA hợp lệ ngay lần thử đầu.
- **Kết luận:** chỉ số tự động không phân biệt được hai nguồn áo. Việc dùng LoRA là lựa chọn thiết kế (không phụ thuộc dáng áo có sẵn), không phải kết luận của thí nghiệm.
- **Lưu ý thống kê:** chỉ có 5 áo LoRA khác nhau (mỗi seed một áo dùng chung cho 6 hiện vật), nên các lượt cùng seed không độc lập.
- **Lần chạy đầu bị loại:** lần chạy đầu cho áo LoRA "tốt hơn". Sau khi sửa hai lỗi (hoa văn ghép tràn ra ngoài áo, nền hoa văn bị in thành khối kem), lợi thế biến mất. Lần chạy đầu không lưu số liệu. Đây là bài học về việc kiểm tra lỗi trước khi tin kết quả.
- **Gói chấm mù:** gói cũ không còn dùng được (ảnh áo cố định đã xoá).

## EXP-E: nguồn ảnh nạp cho ControlNet

- **Ngày:** 19/11/2026 (`summary.json`: 12:03 UTC). Commit `5a5fee4`.
- **Câu hỏi:** nạp ảnh bình render hay mảng hoa văn phẳng cho ControlNet?
- **Thiết kế:** 2 mức, 6 hiện vật, 3 seed (42, 43, 44). 36 lượt. Áo mẫu cố định, polish chỉ vùng áo 0,30.
- **Kết quả:** VLS 0,133 (render) và 0,076 (phẳng), p = 0,25, chưa có ý nghĩa. ΔE 6,41 và 5,67, p = 0,044. PPS và IoU không khác.
- **Quan sát bằng mắt:** nạp ảnh bình cho ra hình bình đặt trên kệ ở hiện vật 33, 50, 124; nạp mảng phẳng cho hoa văn phẳng ở cả 6. VLS có thể kém nhạy với kiểu lỗi này.
- **Quyết định:** mặc định chuyển sang mảng phẳng (thiếu mảng thì quay về ảnh bình).
- **Hạn chế:** ảnh EXP-E chưa từng commit và đã xoá, không khôi phục được.

## EXP-F: chạy lại EXP-E trên pipeline hiện tại

- **Ngày:** 20/11/2026 (`summary.json`: 04:29 UTC). Log: `outputs/logs/expf_run.log`. Chưa commit.
- **Lý do:** EXP-E chạy trước khi có áo LoRA và polish 0,20 kèm khoá họa tiết.
- **Thiết kế:** 2 mức (`panel`, `render`), 6 hiện vật, 3 seed. 36 lượt, cả 36 hoàn thành. Cố định: trọng số ControlNet 0,65, bố cục `front_panel`, polish có mặt nạ 0,20 kèm khoá, áo LoRA. Không có vòng thử lại G2/G3.
- **Kết quả** (trung bình 18 lượt mỗi mức; `panel` là đối chứng):

| Chỉ số | panel | render | Hiệu trung vị | p (Wilcoxon) |
|---|---|---|---|---|
| Giữ họa tiết (PPS) | 0,959 | 0,942 | −0,015 | 0,018 |
| Giữ chi tiết mịn | 0,890 | 0,843 | −0,010 | 0,018 |
| Lệch màu ΔE | 1,09 | 1,82 | +0,60 | 0,002 |
| Lọt hình bình (VLS) | 0,101 | 0,142 | +0,003 | 0,43 |
| Đường nối | 1,55 | **0,93** | −0,29 | 0,054 |
| IoU áo | 0,992 | 0,993 | +0,001 | 0,27 |
| Độ nét | 0,86 | 0,845 | −0,011 | 0,099 |

- **Kết luận:** mảng phẳng giữ họa tiết, chi tiết mịn và màu tốt hơn, có ý nghĩa thống kê. Đổi lại đường nối của mảng phẳng tệ hơn (1,55 so với 0,93, p = 0,054, sát ngưỡng). VLS không khác.
- **Phát hiện dẫn tới EXP-G:** ControlNet Canny vẽ lại hoa văn nên bịa họa tiết và lọt hình bình, kể cả khi nạp mảng phẳng.

## EXP-G: cách tạo ô hoa văn từ mảng phẳng

Chi tiết đầy đủ: [KET_QUA_EXP_G.md](KET_QUA_EXP_G.md). Mã: `evaluation/exp_g.py`. Test: `tests/test_exp_g.py`. Log: `outputs/logs/expg_run.log`, `outputs/logs/expg_boost_run.log`. Chưa commit.

- **Ngày:** 20/11/2026 (`summary.json`: 05:12 UTC).
- **Câu hỏi:** dán nguyên hoặc vẽ lại nhẹ có giữ họa tiết gốc tốt hơn cách ControlNet vẽ lại hoàn toàn không?
- **Thiết kế:** 5 mức, 6 hiện vật, 3 seed. Đợt đầu 72 lượt (4 mức), đợt bổ sung 18 lượt (`paste_boost`), tổng 90 lượt (`results.csv` 90 dòng). Bản sao kết quả 4 mức: `results_4levels_backup.csv`.
- **Các mức:** `sd_controlnet` (đối chứng, cách cũ), `paste_direct` (cắt chữ nhật lớn nhất, làm liền ở mép), `img2img_low` (vẽ lại nhẹ, độ nhiễu 0,30), `elements_sam` (một phần tử cắt bằng SAM, xếp so le), `paste_boost` (dán nguyên rồi kéo tương phản và sắc xanh của mực).
- **Kết quả chính** (trung bình 18 lượt mỗi mức, 4 mức đầu):

| Chỉ số | sd_controlnet | paste_direct | img2img_low | elements_sam |
|---|---|---|---|---|
| Khớp SIFT với mảng gốc | 0,003 | **0,395** | 0,004 | 0,079 |
| Lọt hình bình | 0,101 | 0,037 | **0,024** | 0,106 |
| Đường nối | 1,55 | 1,28 | 1,92 | 1,32 |
| Giữ họa tiết qua polish | 0,959 | 0,949 | 0,962 | 0,949 |
| Lệch màu ΔE | 1,09 | 1,30 | 1,35 | 0,96 |

- **Xem bằng mắt (seed 42):** `sd_controlnet` bịa họa tiết (rồng thành sóng, hoa đổi màu). `paste_direct` giữ đúng họa tiết nhưng màu mờ. `img2img_low` thêm nét vẽ lạ, đường nối kém nhất. `elements_sam` sạch nhưng 2/6 hiện vật chọn nhầm mảnh vụn.
- **Sự cố và cách xử lý:** `paste_direct` in mờ. Nguyên nhân đo được: `garment.apply` chỉ in điểm có sắc độ 16 đến 34, còn mảng phẳng có sắc độ p90 chỉ 11 đến 30. Sửa bằng `boost_ink` (kéo tương phản). Một bản kéo mọi hướng làm hiện đốm vàng ở LR3D_97 nên bị bỏ. Kết quả: mức in mực trung bình 11,6 lên 14,7 (SD là 12,4). SIFT giảm 0,395 xuống 0,293.
- **Kết luận tạm:** không cần vẽ lại hoa văn bằng SD nếu mục tiêu là giữ họa tiết gốc. Chưa có kết luận về độ đẹp.
- **Hạn chế đã biết:** SIFT chỉ đo kế thừa pixel. Chỉ số VLS bị thổi phồng ở `elements_sam`. Cỡ họa tiết lẫn với phương pháp ở `elements_sam`. `paste_direct` không dùng seed hoa văn nên thực chất 6 mẫu độc lập. Tham số kéo (60 và 45) chọn bằng mắt trên seed 42, chưa hiệu chỉnh trên tập khác. Chưa có DreamSim hay chấm mù.

## EXP-A: trọng số ControlNet

Chi tiết đầy đủ: [06_EXPERIMENTS.md](finals/06_EXPERIMENTS.md) (kết quả máy đo và điểm người chấm). Nhập điểm bằng `scripts/eval/import_google_form.py`, test `tests/test_import_google_form.py`.

- **Ngày:** chạy 20/11/2026 (`summary.json`: 16:13 UTC). Chấm mù nộp 22 đến 23/11/2026.
- **Câu hỏi:** ảnh hưởng **riêng** của trọng số ControlNet (0,85, 0,65, 0,45, 0,25), 5 seed (42, 7, 123, 2024, 31415). 120 lượt, cả 120 hoàn tất, cần GPU.
- **Cấu hình lúc chạy:** nguồn mảng phẳng, áo LoRA, bố cục `front_panel`, `stage2_finish` là `masked_0.20+pattern_lock` (polish chỉ vùng áo 0,20 kèm khoá họa tiết). Đặc tả đã khớp với những gì chạy. Ghi chú trong nhật ký trước đây rằng đặc tả còn cấu hình cũ (polish toàn ảnh 0,40) đã lỗi thời. Cột `cfg.polish_strength` = 0,4 trong `results.csv` là giá trị mặc định của mã (`experiment.py` dòng 37); mã chọn cách hoàn thiện theo `stage2_finish` (dòng 232). Chưa đọc hết đường chạy để khẳng định cột 0,4 không ảnh hưởng.
- **Kết quả máy đo:** hạ trọng số làm giảm lọt hình bình (VLS 0,097 xuống 0,012; Friedman p dưới 0,001); PPS, IoU, chi tiết mịn và màu không đổi.
- **Kết quả chấm mù (28 người quan tâm, 48 ảnh gồm 6 hiện vật, 4 trọng số, seed 42 và 7):** điểm trung bình 4 tiêu chí giảm từ 3,72 (0,85) xuống 3,38 (0,25), Friedman p = 2,5 phần triệu trên 12 khối; mạnh nhất ở "nhận ra họa tiết gốc" (3,73 xuống 3,00). Alpha gộp 0,028 (mục tiêu từ 0,667), nên chỉ là xu hướng nhóm.
- **Chất lượng phiếu:** 4 trong 28 người chấm gần như một mức. Bỏ họ thì xu hướng không đổi, alpha 0,06.
- **Hạn chế:** người chấm không có chuyên môn; chưa có phiếu chuyên gia; chỉ 2 seed trong form (thí nghiệm có 5); chênh lệch giữa 0,65 và 0,85 không có ý nghĩa.

---

## Việc chưa làm, theo thứ tự ưu tiên

1. Chấm mù có chuyên môn: gửi phiếu cho ít nhất một người am hiểu di sản và một người am hiểu thiết kế (`outputs/review/google_form_EXP-A_expert*/`, hiện chỉ có phiếu Word trống). Điểm của 28 người quan tâm có alpha 0,03 nên chưa đủ để kết luận "đẹp hơn".
2. Chấm mù các thí nghiệm khác (EXP-B, D, E, F, G): đều chưa có phiếu.
3. Chạy EXP-G với chỉ số giống hiện vật bằng DreamSim và hiệu chỉnh tham số kéo mực trên tập seed khác.
4. Commit dữ liệu thí nghiệm hoặc lưu bản sao ngoài git (R2, Google Drive). Hiện `EXP-F`, `EXP-G`, `outputs/experiments/EXP-D/images/` chưa commit; ảnh EXP-B và EXP-E đã mất.

## Môi trường chạy

- **[CẦN BỔ SUNG]** Mẫu GPU, phiên bản CUDA, driver.
- **[CẦN BỔ SUNG]** Phiên bản chính xác của Stable Diffusion 1.5, ControlNet Canny v1.1, SAM, và tệp LoRA áo dài (băm SHA-256, cấu hình huấn luyện ở `scripts/13_train_lora.py`).
- Thư viện: `uv.lock` ở gốc repo (cần ghi commit tương ứng với từng thí nghiệm).
- Mỗi ảnh trong `results.csv` có SHA-256 riêng, nên đối chiếu được ảnh với số liệu.
