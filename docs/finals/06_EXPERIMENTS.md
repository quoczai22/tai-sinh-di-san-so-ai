# 06. Thử nghiệm có kiểm soát

Trả lời yêu cầu cải tiến 2 của BTC: **đối chứng có kiểm soát và thử nhiều seed**.

## Vấn đề của bộ 4 biến thể cũ

Bốn biến thể V1–V4 ngày 06/09/2026 khác nhau ở **bốn** yếu tố cùng lúc (`evaluation/variants.csv`):

| Yếu tố | V1 | V2 | V3 | V4 |
|---|---|---|---|---|
| Trọng số ControlNet | 0,85 | 0,65 | 0,45 | 0,25 |
| Cụm từ thêm vào prompt | – | – | "modern simplified interpretation" | "bold contemporary reinterpretation" |
| Bảng màu | giữ màu gốc | tự do | tự do | tự do |
| Bố cục trên áo | do CLIP chọn, khác nhau giữa các biến thể | | | |
| Seed | 42 | 42 | 42 | 42 |

Vì vậy không thể nói khác biệt giữa V1 và V4 là do trọng số ControlNet, và không biết với seed khác kết quả dao động bao nhiêu. Bộ biến thể này vẫn được giữ làm **tính năng sản phẩm** (đưa ra 4 phương án đa dạng cho nhà thiết kế), nhưng không dùng làm bằng chứng so sánh.

## Module Experiment Management

Tệp `evaluation/experiment.py`. Mỗi thí nghiệm là một tệp JSON trong `evaluation/experiments/`:

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
python -m evaluation.experiment plan    evaluation/experiments/EXP-A_controlnet_weight.json   # sinh kế hoạch, KIỂM TRA đơn biến
python -m evaluation.experiment run     evaluation/experiments/EXP-A_controlnet_weight.json   # chạy (EXP-A, EXP-B cần GPU)
python -m evaluation.experiment blind   outputs/experiments/EXP-A --raters CG01,CG02,CG03     # gói chấm mù
python -m evaluation.experiment analyze outputs/experiments/EXP-A                            # thống kê
```

### Kiểm soát được thực thi bằng mã

1. **Kiểm tra đơn biến**: trước khi ghi kế hoạch, `validate_plan` so mọi cặp lượt chạy; nếu có tham số nào ngoài biến độc lập và biến lặp mà khác nhau, kế hoạch bị từ chối (`PlanError`). Bộ kiểm thử có ca dựng lại đúng bộ V1–V4 cũ và xác nhận nó bị từ chối.
2. **Kế hoạch ghi trước khi chạy**: `plan.csv` liệt kê toàn bộ cấu hình từng lượt; kết quả ghi vào `results.csv` cùng khoá lượt chạy.
3. **Truy vết từng lượt**: mỗi ảnh kèm SHA-256 của chính nó và của hoa văn đầu vào.
4. **Chấm mù**: gói chấm chỉ có mã ngẫu nhiên `B####`; bảng giải mã `key.csv` để riêng; thứ tự ảnh xáo riêng cho từng người chấm (có hạt giống cố định nên dựng lại được).
5. **Đồng thuận trước khi kết luận**: tính Krippendorff's alpha (dữ liệu khoảng) giữa người chấm. Mục tiêu α ≥ 0,667 mới dùng điểm trung bình để kết luận.
6. **Thống kê**: trung bình, độ lệch chuẩn, khoảng tin cậy 95% (phân phối t), hệ số biến thiên theo mức; so sánh cặp với mức đối chứng trên cùng hiện vật và seed (Wilcoxon có dấu, chỉ báo p khi có ≥ 6 cặp); so sánh tất cả các mức (Friedman, khi có ≥ 3 khối đủ mức).

## Ba thí nghiệm

| | EXP-A | EXP-B | EXP-C |
|---|---|---|---|
| Câu hỏi | Trọng số ControlNet ảnh hưởng **riêng** thế nào đến hoa văn và thiết kế cuối, và dao động giữa các seed lớn đến đâu? | img2img làm thiết kế giống vải in hơn đến mức nào, đổi lại mất bao nhiêu họa tiết? Khoá họa tiết có giữ được cả hai không? | Mỗi bước ghép tất định (displacement, shading, color grade) đóng góp gì? |
| Biến độc lập | Trọng số: 0,85 / 0,65 / 0,45 / 0,25 | Bước hoàn thiện: không img2img / img2img 0,25 / img2img 0,40 / img2img 0,40 + khoá họa tiết | Chế độ ghép: đầy đủ / bỏ displacement / bỏ shading / bỏ color grade |
| Lặp | 5 seed: 42, 7, 123, 2024, 31415 | 3 seed img2img: 42, 7, 123 | Không (tất định) |
| Cố định | Prompt không thêm cụm từ, bảng màu tự do, bố cục "Dải thân trước", img2img 0,40 | Trọng số 0,65, seed hoa văn 42, bảng màu tự do, bố cục "Dải thân trước" | Hoa văn V2 ngày 06/09/2026, bố cục "Dải thân trước", không img2img |
| Hiện vật | 3 hiện vật đang dùng | 3 hiện vật đang dùng | Cả 6 (chỉ ghép trên CPU) |
| Số lượt | 60 | 36 | 24 |
| Chấm mù | ≥ 3 người, 4 tiêu chí | ≥ 3 người, 4 tiêu chí | ≥ 3 người, 2 tiêu chí |
| Trạng thái | Đã lập và kiểm tra kế hoạch; chờ máy GPU | Đã lập và kiểm tra kế hoạch; chờ máy GPU | **Đã chạy**; gói chấm mù sẵn sàng, chờ phiếu |

Ba thí nghiệm chia đúng chỗ BTC hỏi: EXP-C chỉ đổi bước ghép, EXP-B chỉ đổi bước hoàn thiện, EXP-A chỉ đổi ControlNet; prompt và bảng màu cố định trong cả ba.

## Kết quả EXP-C (tự động)

Chỉ số: PPS của mỗi chế độ so với bản ghép đầy đủ (bản đầy đủ = 1). Chỉ số này cho biết **mỗi bước làm ảnh thay đổi bao nhiêu**, không cho biết bước đó làm ảnh đẹp hơn hay giống vải hơn; câu hỏi đó chờ phiếu chuyên gia.

| Chế độ | n | Trung bình | Độ lệch chuẩn | KTC 95% | Hiệu trung vị so với đầy đủ |
|---|---|---|---|---|---|
| Đầy đủ | 6 | 1,000 | 0 | – | – |
| Bỏ displacement | 6 | 0,851 | 0,041 | 0,808 – 0,893 | −0,140 |
| Bỏ shading | 6 | 0,965 | 0,016 | 0,948 – 0,981 | −0,035 |
| Bỏ color grade | 6 | 0,958 | 0,039 | 0,918 – 0,999 | −0,026 |

Friedman trên 6 hiện vật: χ² = 16,2; p = 0,001. Wilcoxon từng chế độ so với đầy đủ: p = 0,031 cho cả ba — với 6 cặp, đây là giá trị p nhỏ nhất có thể đạt, nghĩa là cả 6 hiện vật đều thay đổi cùng chiều.

Đọc kết quả: displacement (uốn họa tiết theo nếp vải) là bước làm thay đổi hình ảnh nhiều nhất trong ba bước; shading và color grade thay đổi ít. Có thay đổi không có nghĩa là có lợi; giả thuyết "displacement giúp họa tiết trông như in trên vải" chỉ được kết luận khi phiếu tiêu chí "Giống vải in thật" có đồng thuận đủ.

Tệp: `outputs/experiments/EXP-C/` (`plan.csv`, `results.csv`, `images/`, `summary.json`, `blind/`).

## Những gì chưa làm được và vì sao

- EXP-A, EXP-B cần máy có GPU NVIDIA và mô hình SD 1.5 đã tải. Môi trường dựng bản này không có GPU nên không chạy; kế hoạch, bộ chạy GPU và bộ phân tích đã có, chạy bằng một lệnh trên máy của nhóm.
- Chưa có phiếu chuyên gia thật. Ba tệp `ratings_CG01.csv`… trong gói chấm là mẫu trống; nhóm **không** điền điểm giả.
