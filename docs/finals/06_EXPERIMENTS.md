# 06. Thử nghiệm có kiểm soát

Trả lời yêu cầu cải tiến 2 của BTC: **đối chứng có kiểm soát và thử nhiều seed**.

## Vấn đề của bộ 4 biến thể cũ

Bốn biến thể V1 đến V4 của bản 06/09/2026 khác nhau ở **bốn** yếu tố cùng lúc (`tsds/evaluation/variants.csv`). Luồng sản phẩm hiện nay vẫn giữ cách đặt này (bốn mức sáng tạo đổi nhiều yếu tố cùng lúc):

| Yếu tố | V1 | V2 | V3 | V4 |
|---|---|---|---|---|
| Trọng số ControlNet | 0,85 | 0,65 | 0,45 | 0,25 |
| Cụm từ thêm vào prompt | – | – | "modern simplified interpretation" | "bold contemporary reinterpretation" |
| Bảng màu | giữ màu gốc | tự do | tự do | tự do |
| Bố cục trên áo | do CLIP chọn, khác nhau giữa các biến thể (bộ demo vẫn giữ cách này; EXP-F và EXP-G cố định `front_panel` để so riêng ô hoa văn) | | | |
| Seed | 42 | 42 | 42 | 42 |

Vì vậy không thể nói khác biệt giữa V1 và V4 là do trọng số ControlNet, và không biết với seed khác kết quả dao động bao nhiêu. Bộ biến thể này vẫn được giữ làm **tính năng sản phẩm** (đưa ra 4 phương án đa dạng cho nhà thiết kế), nhưng không dùng làm bằng chứng so sánh.

Từ 20/11/2026 bộ demo dùng **một seed duy nhất (42)** nhưng vẫn để CLIP chọn bố cục khác nhau cho bốn biến thể, nên bốn mức khác nhau cả ở trọng số ControlNet, cụm prompt, bảng màu và vị trí họa tiết. Độ dao động theo seed được đo ở gói chấm mù nhiều seed (42, 43, 44; xem [05](05_QUALITY_ASSURANCE.md)) và ở các thí nghiệm có kiểm soát bên dưới.

## Module Experiment Management

Tệp `tsds/evaluation/experiment.py`. Mỗi thí nghiệm là một tệp JSON trong `tsds/evaluation/experiments/`:

| Trường | Ý nghĩa |
|---|---|
| `question`, `why` | Câu hỏi cần trả lời và vì sao cần hỏi |
| `independent_variable` | **Một** biến được thay đổi và các mức của nó |
| `replicates` | Biến lặp (seed) để đo dao động; không phải biến cần so sánh |
| `fixed` | Mọi tham số còn lại, ghi rõ giá trị |
| `units` | Hiện vật dùng: `active` (đang dùng), `legacy_all` (cả 6, chỉ cho phép khi không cần GPU) hoặc danh sách |
| `metrics` | Chỉ số tự động và tiêu chí người chấm |
| `blind_review` | Có chấm mù không, tối thiểu bao nhiêu người chấm |

Quy trình chạy:

```bash
python -m tsds.evaluation.experiment plan    tsds/evaluation/experiments/EXP-A_controlnet_weight.json   # sinh kế hoạch, KIỂM TRA đơn biến
python -m tsds.evaluation.experiment run     tsds/evaluation/experiments/EXP-A_controlnet_weight.json   # chạy (EXP-A, B, D, E, F cần GPU; EXP-C chạy trên CPU; EXP-G chạy bằng python -m tsds.evaluation.exp_g plan|run|analyze)
python -m tsds.evaluation.experiment blind   outputs/experiments/EXP-A --raters CG01,CG02,CG03     # gói chấm mù
python -m tsds.evaluation.experiment analyze outputs/experiments/EXP-A                            # thống kê
```

### Kiểm soát được thực thi bằng mã

1. **Kiểm tra đơn biến**: trước khi ghi kế hoạch, `validate_plan` so mọi cặp lượt chạy; nếu có tham số nào ngoài biến độc lập và biến lặp mà khác nhau, kế hoạch bị từ chối (`PlanError`). Bộ kiểm thử có ca dựng lại đúng bộ V1–V4 cũ và xác nhận nó bị từ chối.
2. **Kế hoạch ghi trước khi chạy**: `plan.csv` liệt kê toàn bộ cấu hình từng lượt; kết quả ghi vào `results.csv` cùng khoá lượt chạy.
3. **Truy vết từng lượt**: mỗi ảnh kèm SHA-256 của chính nó và của hoa văn đầu vào.
4. **Chấm mù**: gói chấm chỉ có mã ngẫu nhiên `B####`; bảng giải mã `key.csv` để riêng; thứ tự ảnh xáo riêng cho từng người chấm (có hạt giống cố định nên dựng lại được).
5. **Đồng thuận trước khi kết luận**: tính Krippendorff's alpha (dữ liệu khoảng) giữa người chấm. Mục tiêu α ≥ 0,667 mới dùng điểm trung bình để kết luận.
6. **Thống kê**: trung bình, độ lệch chuẩn, khoảng tin cậy 95% (phân phối t), hệ số biến thiên theo mức; so sánh cặp với mức đối chứng trên cùng hiện vật và seed (Wilcoxon có dấu, chỉ báo p khi có ≥ 6 cặp); so sánh tất cả các mức (Friedman, khi có ≥ 3 khối đủ mức).

## Bảy thí nghiệm (EXP-A đến EXP-G)

| | EXP-A | EXP-B | EXP-C | EXP-D | EXP-E |
|---|---|---|---|---|---|
| Câu hỏi | Trọng số ControlNet ảnh hưởng **riêng** thế nào đến hoa văn và thiết kế cuối? | Bước hoàn thiện (polish) làm mất bao nhiêu họa tiết, và khoá họa tiết giữ lại được bao nhiêu? | Mỗi bước ghép tất định (displacement, shading, color grade) đóng góp gì? | Áo dài nền do LoRA sinh so với áo mẫu cố định | Ảnh nạp cho ControlNet: ảnh render cả bình so với mảng hoa văn phẳng |
| Biến độc lập | Trọng số: 0,85 / 0,65 / 0,45 / 0,25 | Cách hoàn thiện: không polish; polish toàn ảnh 0,25 và 0,40; polish toàn ảnh 0,40 + khoá; polish chỉ vùng áo 0,25 và 0,30; polish chỉ vùng áo 0,30 + khoá | Chế độ ghép: đầy đủ / bỏ displacement / bỏ shading / bỏ color grade | Nguồn áo nền: cố định / LoRA | Nguồn ảnh nạp: render / mảng phẳng |
| Lặp | 5 seed: 42, 7, 123, 2024, 31415 | 3 seed polish: 42, 7, 123 | Không (tất định) | 5 seed: 42 đến 46 (cũng là seed hoa văn và seed áo LoRA) | 3 seed: 42, 43, 44 |
| Hiện vật | 6 hiện vật đang dùng | 6 hiện vật đang dùng | 6 hiện vật cũ (chỉ ghép trên CPU) | 6 hiện vật đang dùng | 6 hiện vật đang dùng |
| Số lượt | 120 | 126 | 24 | 60 | 36 |
| Trạng thái | **Đã chạy 120/120** (20/11/2026) | **Đã chạy 126/126** | **Đã chạy 24/24** (trên 6 hiện vật cũ) | **Đã chạy 60/60** | **Đã chạy 36/36** |
| Chấm mù | Chưa | Chưa | Gói đã dựng, **chưa có phiếu** | Gói đã dựng (60 ảnh, 3 phiếu trống), **chưa có phiếu** | Chưa |

Hai thí nghiệm thêm ngày 20/11/2026, cùng cố định: áo LoRA, bố cục `front_panel`, ControlNet 0,65, bảng màu tự do, polish chỉ vùng áo 0,20 kèm khoá họa tiết; lặp theo 3 seed 42, 43, 44.

| | EXP-F | EXP-G |
|---|---|---|
| Câu hỏi | Nếu pipeline nhận thẳng ảnh bình render thay vì mảng hoa văn phẳng, thiết kế cuối giữ họa tiết, dáng áo và màu tốt hơn hay kém hơn? | Trích hoa văn từ mảng phẳng bằng cách dán nguyên, vẽ lại nhẹ hoặc cắt phần tử SAM có giữ họa tiết gốc hơn cách SD vẽ lại hoàn toàn không? |
| Biến độc lập | Nguồn ảnh nạp: mảng phẳng / ảnh render (`tsds/evaluation/experiments/EXP-F_vessel_vs_panel.json`) | Cách tạo ô hoa văn, 7 mức: `sd_controlnet` (đối chứng), `paste_direct`, `img2img_low`, `elements_sam`, `paste_boost`, `elements_clip`, `elements_boost` (`EXP-G_pattern_method.json`, mã `tsds/evaluation/exp_g.py`) |
| Số lượt | 36 (6 hiện vật × 2 × 3 seed) | 126 (6 hiện vật × 7 × 3 seed) |
| Trạng thái | **Đã chạy 36/36** | **Đã chạy 126/126**; hai mức phần tử chạy lại sau khi sửa lỗi nền in cả mảng (`ground_alpha`) |
| Chấm mù | Chưa | Chưa |

Mỗi thí nghiệm chỉ đổi một yếu tố. Kế hoạch đổi hơn một yếu tố bị mã từ chối (kiểm thử `test_experiment.py`, `test_exp_g.py`).

Ghi chú về việc áo mẫu cố định đã bỏ: luồng sản phẩm hiện chỉ dùng áo do LoRA sinh. Quyết định này là lựa chọn thiết kế của nhóm (không phụ thuộc dáng áo có sẵn), **không** phải kết luận của EXP-D, vì EXP-D không thấy khác biệt có ý nghĩa (xem dưới) và chưa có chấm mù. Mức `fixed` còn trong mã chỉ để chạy lại các thí nghiệm cũ.

## Kết quả EXP-A: trọng số ControlNet (120 lượt)

Chạy ngày 20/11/2026, cả 120 lượt hoàn tất. Mỗi mức 30 cặp (6 hiện vật × 5 seed: 42, 7, 123, 2024, 31415). Cấu hình: nguồn mảng phẳng, áo LoRA (mỗi seed một áo), bố cục `front_panel`, bảng màu tự do, polish chỉ vùng áo 0,20 kèm khoá họa tiết; chỉ đổi trọng số ControlNet. Trung bình theo mức (số liệu trong `outputs/experiments/EXP-A/summary.json`); cột cuối là kiểm định Friedman trên 30 khối (hiện vật × seed):

| Chỉ số | 0,85 | 0,65 | 0,45 | 0,25 | Friedman p |
|---|---|---|---|---|---|
| Lọt hình bình (VLS, thấp là tốt) | 0,097 | 0,086 | 0,036 | **0,012** | dưới 0,001 |
| Đường nối khi lát (thấp là tốt) | 1,68 | 1,64 | 1,38 | **1,24** | 0,39 |
| Giữ họa tiết qua polish (PPS) | 0,941 | 0,938 | 0,937 | 0,940 | 0,46 |
| Giữ dáng áo (IoU) | 0,991 | 0,989 | 0,990 | 0,992 | 0,68 |
| Giữ chi tiết mịn | 0,865 | 0,866 | 0,866 | 0,863 | 0,74 |
| Lệch màu ΔE | 1,25 | 1,23 | 1,12 | 1,21 | 0,47 |

- **Hạ trọng số làm giảm lọt hình bình rõ.** So với 0,85, mức 0,45 và 0,25 khác có ý nghĩa (Wilcoxon theo cặp p = 0,0001 và 0,0003); mức 0,65 chưa khác (p = 0,47). Đường nối cũng thấp dần theo trọng số nhưng không đạt ý nghĩa tổng thể (Friedman p = 0,39; riêng 0,25 so với 0,85 p = 0,032, chưa hiệu chỉnh đa so sánh).
- **PPS, IoU, chi tiết mịn và màu không đổi theo trọng số.** PPS đo giữ họa tiết qua polish so với bản ghép thô, **không đo giống hiện vật gốc**, nên không thấy được việc trọng số thấp thay hoa văn.
- **Xem ảnh (seed 42) cho thấy điều chỉ số máy không thấy:** ở 0,25 hoa văn thành mảng hoa văn dày chung chung, LR3D_124 mất dải lông vũ và huy hiệu rồng, LR3D_61 mất hình rồng thành dải sóng. Trọng số thấp tránh dáng bình nhưng bỏ họa tiết gốc. Kết luận về "nhận ra họa tiết gốc" phải chờ phiếu chuyên gia.
- **Theo hiện vật:** LR3D_38 lọt hình bình nhiều nhất ở 0,85 (VLS 0,213) và PPS giảm từ 0,934 xuống 0,892 ở 0,25; LR3D_50 và LR3D_97 gần như không lọt (VLS 0,0 đến 0,04).
- **Dao động theo seed:** hệ số biến thiên của PPS trong từng ô (hiện vật × mức), trung bình 6 hiện vật, là 2,1% ở 0,85, 2,4% ở 0,65, 2,8% ở 0,45, 2,9% ở 0,25: tăng nhẹ khi trọng số giảm. VLS dao động rất lớn (hệ số biến thiên 81% đến 177%) vì hầu hết giá trị gần 0, vài seed cao.
- **Giới hạn:** 30 cặp mỗi mức; Wilcoxon chạy ba lần cho mỗi chỉ số, không hiệu chỉnh; chưa chấm mù; chỉ số CLIP nêu trong đặc tả không có trong kết quả (cột `clip_similarity_pattern_vs_ceramic` không được ghi). EXP-A giữ cố định prompt, bảng màu và bố cục, còn bốn mức sáng tạo của bộ demo đổi cả prompt và bảng màu cùng trọng số, nên kết quả EXP-A không thay được so sánh bốn mức của bộ demo.

## Kết quả EXP-B: bước hoàn thiện (126 lượt)

Chỉ số so với bản ghép thô (bản không polish bằng 1). Mỗi mức 18 cặp (6 hiện vật × 3 seed). Cấu hình lúc chạy: áo mẫu cố định, ảnh nạp là ảnh bình render, hoa văn seed 42.

| Cách hoàn thiện | Giữ họa tiết (PPS) | Giữ dáng áo (IoU) | Độ nét | Lệch màu (ΔE) |
|---|---|---|---|---|
| Không polish | 1,000 | 1,000 | 1,00 | 0,0 |
| Polish toàn ảnh 0,25 | 0,494 | 0,963 | 0,84 | 2,8 |
| Polish toàn ảnh 0,40 (cách cũ) | **0,303** | 0,956 | 0,88 | 5,5 |
| Polish toàn ảnh 0,40 + khoá họa tiết | 0,809 | 0,954 | 0,68 | 3,0 |
| Polish chỉ vùng áo 0,25 | 0,494 | 0,993 | 0,85 | 2,8 |
| Polish chỉ vùng áo 0,30 | 0,429 | 0,993 | 0,87 | 3,7 |
| Polish chỉ vùng áo 0,30 + khoá họa tiết | 0,862 | 0,993 | 0,79 | 2,1 |

- Polish toàn ảnh 0,40 (cách của bản 09/2026) làm PPS tụt còn 0,30, thấp nhất trong các cách có polish. Friedman trên 18 khối: χ² = 106,6; p < 0,001. Mọi mức so với không polish đều có p ≤ 0,0002 (Wilcoxon).
- Polish chỉ vùng áo giữ dáng áo tốt hơn rõ (IoU 0,993 so với 0,956) và giữ nguyên từng pixel ngoài áo. Đây là lý do luồng sản phẩm chuyển sang polish chỉ vùng áo.
- Độ nhiễu thấp hơn giữ họa tiết tốt hơn (0,25 cao hơn 0,30). Khoá họa tiết đưa PPS lên 0,81 đến 0,86, nhưng PPS này cao **do cách làm** (chép nét từ bản ghép), nên không chứng minh bản khoá đẹp hơn. Câu hỏi đó cần chấm mù.
- Chưa có chấm mù, nên chưa biết lợi ích "giống vải in hơn" của polish có bù được phần họa tiết bị đổi hay không.

Tệp: `outputs/experiments/EXP-B/` (`plan.csv`, `results.csv`, `summary.json`). Ảnh của EXP-B (chưa từng commit) đã xoá ngày 19/11/2026 cùng toàn bộ ảnh dựng trên áo mẫu cố định và không khôi phục được; số liệu giữ nguyên trong `results.csv`.

## Kết quả EXP-D: nguồn áo nền (60 lượt)

Mỗi mức 30 cặp (6 hiện vật × 5 seed). Cấu hình cố định: ảnh nạp là mảng hoa văn phẳng, polish chỉ vùng áo 0,30, bố cục "Dải thân trước". Giữ dáng áo đo so với chính áo nền của lượt đó.

| Chỉ số | Áo cố định | Áo LoRA | Hiệu trung vị | p (Wilcoxon) |
|---|---|---|---|---|
| Giữ họa tiết (PPS) | 0,452 | 0,475 | +0,007 | 0,37 |
| Giữ dáng áo (IoU) | 0,990 | 0,988 | +0,002 | 0,58 |
| Độ nét | 0,92 | 0,96 | +0,07 | 0,44 |
| Lệch màu (ΔE) | 5,22 | 5,12 | +0,07 | 1,00 |

**Không có khác biệt có ý nghĩa ở chỉ số nào.** Cả 30 lượt LoRA đều có áo hợp lệ ngay lần thử đầu. Lưu ý: chỉ có 5 áo LoRA khác nhau (mỗi seed một áo dùng chung cho 6 hiện vật), nên các lượt cùng seed không độc lập. Độ đẹp và độ đúng dáng áo dài chỉ chấm mù mới trả lời được; gói chấm mù (`outputs/experiments/EXP-D/blind/`: `key.csv`, 3 phiếu trống, hướng dẫn chấm) đã dựng nhưng chưa gửi người chấm.

Ghi chú về lịch sử: lần chạy đầu của EXP-D cho áo LoRA "tốt hơn" ở PPS và lệch màu. Sau khi sửa hai lỗi (hoa văn bị ghép tràn ra ngoài áo, và mảng nền hoa văn bị in thành khối kem) rồi đổi nguồn ảnh nạp sang mảng phẳng, lợi thế đó biến mất. Nghĩa là nó là hệ quả của các lỗi, không phải của áo LoRA (số liệu lần chạy đầu không được lưu).

## Kết quả EXP-E: nguồn ảnh nạp cho ControlNet (36 lượt)

Mỗi mức 18 cặp (6 hiện vật × 3 seed). Áo mẫu cố định, polish chỉ vùng áo 0,30.

| Chỉ số | Ảnh bình render | Mảng phẳng | Hiệu trung vị | p (Wilcoxon) |
|---|---|---|---|---|
| Lọt hình bình (VLS, thấp là tốt) | 0,133 | **0,076** | −0,012 | 0,25 |
| Giữ họa tiết (PPS) | 0,447 | 0,442 | −0,009 | 0,87 |
| Giữ dáng áo (IoU) | 0,992 | 0,992 | +0,001 | 0,40 |
| Lệch màu (ΔE) | 6,41 | **5,67** | −0,81 | 0,044 |

Chỉ số VLS nghiêng về mảng phẳng nhưng **chưa đạt ý nghĩa thống kê** (p = 0,25). Trên ảnh, khác biệt rõ hơn chỉ số: nạp ảnh bình render cho ra hình bình đặt trên kệ, hình bình có nền hoặc cổ bình (hiện vật 33, 50, 124), còn nạp mảng phẳng cho hoa văn phẳng ở cả 6 hiện vật. VLS có thể kém nhạy với kiểu lỗi này. Dựa vào đó, mặc định của luồng sản phẩm chuyển sang mảng phẳng; chấm mù sẽ xác nhận.

## Kết quả EXP-F: ảnh bình gốc so với mảng phẳng (36 lượt)

Mỗi mức 18 cặp (6 hiện vật × 3 seed), cấu hình hiện nay (polish 0,20 kèm khoá họa tiết). Trung bình (KTC 95%), số liệu trong `outputs/experiments/EXP-F/summary.json`:

| Chỉ số | Mảng phẳng | Ảnh bình render |
|---|---|---|
| Giữ họa tiết (PPS, cao là tốt) | **0,959** (0,953 đến 0,965) | 0,942 (0,929 đến 0,954) |
| Giữ chi tiết mịn (cao là tốt) | **0,890** (0,880 đến 0,900) | 0,843 (0,799 đến 0,886), thấp nhất 0,544 |
| Lệch màu ΔE (thấp là tốt) | **1,09** (0,96 đến 1,22) | 1,82 (1,30 đến 2,34), cao nhất 4,93 |
| Lọt hình bình (VLS, thấp là tốt) | **0,101** | 0,142 (cao nhất 0,509) |
| Đường nối khi lát (thấp là tốt) | 1,55 | **0,93** |
| Giữ dáng áo (IoU) | 0,992 | 0,993 |
| Độ nét | 0,860 | 0,845 |

Mảng phẳng tốt hơn ở họa tiết, chi tiết mịn, màu và lọt hình bình; hai nguồn ngang nhau ở dáng áo. Đường nối ở ảnh bình thấp hơn, nhưng chỉ số này **có thể thiên lệch**: nạp ảnh bình hay cho ra vật rời trên nền trơn, nơi đường nối ít thấy. Chưa có phiếu chấm mù.

Nạp ảnh bình còn có một lỗi chỉ số không thấy: bộ demo sinh thử từ ảnh bình (20/11/2026, đã bỏ) cho hoa văn mang dáng cả chiếc bình ở mức 1 và 2 của LR3D_33, 50, 97 và 124, và hoa văn của LR3D_124 thành ba vật rời. LR3D_33 vẫn đo VLS 0,0001 vì bình choán đầy khung ô. Vì vậy luồng sản phẩm dùng lại **mảng phẳng làm nguồn mặc định** (`source="panel"`).

## Kết quả EXP-G: cách tạo ô hoa văn (126 lượt)

Chi tiết đầy đủ, ảnh và các mức thêm sau ở `docs/KET_QUA_EXP_G.md`. Ba mức đầu so với đối chứng (trung bình 18 lượt mỗi mức):

| Chỉ số | `sd_controlnet` | `paste_direct` | `img2img_low` |
|---|---|---|---|
| Khớp SIFT với mảng gốc (cao là kế thừa pixel) | 0,003 | **0,395** | 0,004 |
| Lọt hình bình (thấp là tốt) | 0,101 | 0,037 | **0,024** |
| Đường nối khi lát (thấp là tốt) | 1,55 | **1,28** | 1,92 |
| Giữ họa tiết qua polish | 0,959 | 0,949 | **0,962** |
| Giữ chi tiết mịn | **0,890** | 0,875 | 0,889 |
| Lệch màu ΔE | **1,09** | 1,30 | 1,35 |

- **Dán nguyên giữ họa tiết hơn hẳn** (SIFT 0,395 so với 0,003), nhưng ô thường nhạt hơn nên phải kéo đậm mực (`paste_boost`). **Vẽ lại nhẹ** (`img2img_low`) thêm nét vẽ lạ và có đường nối kém nhất.
- **Phần tử SAM** (`elements_*`) cho áo sạch, nhìn như thêu họa tiết riêng, nhưng quy tắc chọn tự động còn lấy nhầm phần tử ở vài hiện vật (lá ở LR3D_38, mây hoặc đuôi rồng ở LR3D_61).
- **Lỗi tìm được và đã sửa trong luồng sản phẩm:** ô thưa hoặc mực nhạt bị in cả nền thành mảng phẳng (`ground_alpha`); có 7 ca kiểm thử.
- **Chưa đưa vào luồng sản phẩm:** luồng vẫn dùng `sd_controlnet` từ mảng phẳng. Các mức dán và phần tử là hướng đang cân nhắc (SAM tách motif, ghép tất định rồi polish), chưa có chấm mù.
- Cả hai chỉ số lọt hình bình và đường nối thiên lệch với ô thưa; SIFT chỉ đo kế thừa pixel.

## Kết quả EXP-C: từng bước ghép (chạy trên 6 hiện vật cũ)

Chỉ số: PPS của mỗi chế độ so với bản ghép đầy đủ (bản đầy đủ bằng 1). Chỉ số này cho biết **mỗi bước làm ảnh thay đổi bao nhiêu**, không cho biết bước đó làm ảnh đẹp hơn hay giống vải hơn.

| Chế độ | n | Trung bình | Độ lệch chuẩn | KTC 95% | Hiệu trung vị so với đầy đủ |
|---|---|---|---|---|---|
| Đầy đủ | 6 | 1,000 | 0 | – | – |
| Bỏ displacement | 6 | 0,851 | 0,041 | 0,808 – 0,893 | −0,140 |
| Bỏ shading | 6 | 0,965 | 0,016 | 0,948 – 0,981 | −0,035 |
| Bỏ color grade | 6 | 0,958 | 0,039 | 0,918 – 0,999 | −0,026 |

Friedman trên 6 hiện vật: χ² = 16,2; p = 0,001. Wilcoxon từng chế độ so với đầy đủ: p = 0,031 cho cả ba (với 6 cặp, đây là giá trị nhỏ nhất có thể đạt: cả 6 hiện vật đổi cùng chiều). Displacement (uốn họa tiết theo nếp vải) là bước làm thay đổi hình ảnh nhiều nhất. Có thay đổi không có nghĩa là có lợi.

EXP-C ghép trên áo mẫu cố định của 6 hiện vật cũ nên **không chạy lại được** sau khi áo mẫu bị bỏ khỏi luồng. Ảnh và gói chấm mù của EXP-C đã xoá ngày 19/11/2026; còn `plan.csv`, `results.csv`, `summary.json`. Muốn xem ảnh, quay lại commit `b1192b0`.

## Thử hoàn thiện ảnh trên bộ demo hiện tại

Ngoài EXP-B, nhóm thử riêng cách hoàn thiện trên bản ghép thô của bộ demo ngày 19/11/2026: `tsds/evaluation/polish_finish_trial.py` (cần GPU), kết quả ở `tsds/evaluation/polish_finish_trial.csv`. Với mỗi bản ghép thô, polish chỉ vùng áo ở 2 độ nhiễu rồi (a) giữ nguyên, (b) khoá họa tiết với `dog_sigma_low` = 1,2 (cũ), (c) khoá họa tiết với `dog_sigma_low` = 0,3 (hiện tại).

12 thiết kế (6 hiện vật × 2 mức sáng tạo), cùng seed polish 42, không có vòng thử lại. Cột "Giữ chi tiết mịn" là chỉ số `detail_ratio` (bản cuối so với bản ghép thô, cao là tốt, ngưỡng lỗi 0,6).

| Độ nhiễu | Cách hoàn thiện | PPS | IoU | Độ nét | Giữ chi tiết mịn (trung bình, thấp nhất) | ΔE | G3: đạt / cảnh báo / lỗi |
|---|---|---|---|---|---|---|---|
| 0,30 | Polish thuần | 0,466 | 0,993 | 0,71 | 0,69 (0,42) | 5,9 | 0 / 3 / 9 |
| 0,30 | Khoá họa tiết, `dog_sigma_low` 1,2 (cũ) | 0,888 | 0,994 | 0,64 | 0,56 (0,33) | 3,9 | 0 / 4 / 8 |
| 0,30 | Khoá họa tiết, `dog_sigma_low` 0,3 | 0,932 | 0,995 | 0,84 | 0,83 (0,71) | 2,1 | 5 / 7 / 0 |
| 0,20 | Polish thuần | 0,541 | 0,996 | 0,72 | 0,75 (0,51) | 4,8 | 1 / 8 / 3 |
| 0,20 | Khoá họa tiết, `dog_sigma_low` 1,2 (cũ) | 0,908 | 0,996 | 0,66 | 0,61 (0,41) | 3,1 | 0 / 6 / 6 |
| **0,20** | **Khoá họa tiết, `dog_sigma_low` 0,3 (mặc định hiện nay)** | **0,944** | 0,996 | 0,83 | **0,83 (0,72)** | **1,5** | **5 / 7 / 0** |

- **Khoá họa tiết cũ (σ = 1,2) làm PPS tăng mạnh nhưng làm mất nét mảnh:** chi tiết mịn còn 0,56 đến 0,61, thấp hơn cả polish thuần (0,69 đến 0,75). PPS không phát hiện được vì chỉ đo dải tần trung. Đây là lý do nhóm thêm chỉ số `detail_ratio` vào G3: với chỉ số này, 8/12 và 6/12 thiết kế của cấu hình cũ bị loại.
- **Khoá họa tiết `dog_sigma_low` 0,3** giữ chi tiết mịn ở mức 0,83 ở cả hai độ nhiễu, không thiết kế nào bị loại, lệch màu thấp nhất.
- **Độ nhiễu 0,20 tốt hơn 0,30** ở mọi chỉ số, nên được chọn làm mặc định.
- Vẫn còn mất khoảng 17% chi tiết mịn so với bản ghép thô; bộ demo hiện tại (24 thiết kế, 20/11/2026) cho trung vị 0,881 (mất 12%), bộ 72 thiết kế nhiều seed cho 0,883. Bản cuối chưa bằng bản ghép thô về nét mảnh.
- Các số này đo bằng máy; chưa có chấm mù về việc bản nào đẹp hơn.


## Những gì chưa làm được

- **Gói chấm mù nhiều seed (72 thiết kế, mỗi người chấm 24) đã dựng, chưa có phiếu.** Xem [05](05_QUALITY_ASSURANCE.md).
- **Gói chấm mù riêng cho EXP-A đã dựng, chưa có phiếu:** `scripts/eval/build_blind_review.py --experiment outputs/experiments/EXP-A --seeds 42,7` ra `outputs/review/blind_review_EXP-A/` (48 ảnh = 6 hiện vật × 4 trọng số × 2 seed, 24 ô; mỗi người chấm thấy 24 ảnh, một seed mỗi ô, theo mã người chấm). Chỉ 4 tiêu chí trong đặc tả EXP-A (nhận ra họa tiết gốc, phù hợp văn hoá, thẩm mỹ, toàn vẹn dáng áo); trang gửi người chấm không lộ trọng số, seed hay tên thí nghiệm; `key.csv` ghi trọng số ở cột `intensity_level`. Cần ít nhất 3 người chấm (đặc tả), có mã số cuối liên tiếp (CG01, CG02, ...).
- **Chưa có phiếu chuyên gia thật.** Các tệp `ratings_CG01.csv` đến `CG03.csv` trong gói chấm là mẫu trống; nhóm **không** điền điểm giả. Vì vậy mọi kết luận về "đẹp hơn" hay "giống vải in hơn" ở trên đều chưa có.
- Các kết quả trên dùng cấu hình lúc chạy (xem từng mục). Cấu hình mặc định hiện nay của luồng sản phẩm (polish 0,20 và khoá họa tiết 0,3) khác EXP-B, D, E; phần "Thử hoàn thiện ảnh" đo trực tiếp cấu hình hiện nay.
