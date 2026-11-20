# Kết quả EXP-G: bốn cách tạo ô hoa văn từ mảng phẳng

- **Ngày chạy:** 20/11/2026. 72 lượt (6 hiện vật x 4 cách x 3 seed), cả 72 lượt ra ảnh.
- **Đặc tả:** `evaluation/experiments/EXP-G_pattern_method.json`. **Mã:** `evaluation/exp_g.py`. **Ảnh và số liệu:** `outputs/experiments/EXP-G/`.
- **Ô hoa văn** là ảnh nhỏ mà `garment.apply` lát liền lên áo. Cả bốn cách dùng chung áo LoRA, bố cục `front_panel`, polish có mặt nạ 0,20 kèm khóa họa tiết. Chỉ khác cách tạo ô.

> **Cập nhật 20/11/2026 (đọc trước):** các số và ảnh của `elements_sam` (LR3D_38, LR3D_61, LR3D_97) và `elements_clip` (LR3D_38, LR3D_97) ở các mục "Sửa màu mờ" và "Chọn phần tử tốt" bị lỗi nền in cả mảng. Lỗi đã sửa trong `generation/garment.py` (mục "Sửa lỗi nền in cả mảng" ở cuối) và hai mức đã chạy lại; kết quả chạy lại nằm ở mục đó, thay cho số cũ.

## Bốn cách

| Cách | Làm gì |
|---|---|
| `sd_controlnet` | Cách hiện tại. Canny của mảng đưa vào ControlNet, Stable Diffusion vẽ lại hoàn toàn. Đối chứng. |
| `paste_direct` | Cắt hình chữ nhật lớn nhất nằm trọn trong mảng, làm liền mạch ở dải mép 15%. Không vẽ lại. |
| `img2img_low` | Lấy ô của `paste_direct` rồi vẽ lại nhẹ bằng img2img, độ nhiễu 0,30. |
| `elements_sam` | Dán một phần tử đã cắt bằng SAM (điểm cao nhất của hiện vật), xếp so le. |

## Số đo (trung bình 18 lượt mỗi cách)

| Chỉ số | sd_controlnet | paste_direct | img2img_low | elements_sam |
|---|---|---|---|---|
| Khớp SIFT với mảng gốc (cao là kế thừa pixel) | 0,003 | **0,395** | 0,004 | 0,079 |
| Lọt hình bình (thấp là tốt) | 0,101 | **0,037** | **0,024** | 0,106 |
| Đường nối khi lát (thấp là tốt) | 1,55 | 1,28 | 1,92 | 1,32 |
| Giữ họa tiết qua polish | 0,959 | 0,949 | 0,962 | 0,949 |
| Giữ chi tiết mịn | 0,890 | 0,875 | 0,889 | 0,908 |
| Lệch màu ΔE | 1,09 | 1,30 | 1,35 | 0,96 |

Kiểm định cặp Wilcoxon so với `sd_controlnet` (mẫu nhỏ, chỉ tham khảo): SIFT của `paste_direct` và `elements_sam` khác rõ (p dưới 0,001); lọt hình bình của `paste_direct` p=0,03, `img2img_low` p=0,004; các chỉ số còn lại phần lớn không khác có ý nghĩa.

## Xem bằng mắt (seed 42, 6 hiện vật)

- **`sd_controlnet`:** sáng, nét, nhưng bịa họa tiết: rồng thành sóng (LR3D_61), hoa đổi màu xanh lá (LR3D_38).
- **`paste_direct`:** giữ đúng họa tiết, rồng nguyên vẹn, ít lọt hình bình. Màu xám nhạt hơn, có bóng mờ ở dải hòa mép. Hiện vật ít tương phản (LR3D_97) gần như biến mất trên áo.
- **`img2img_low`:** gần `paste_direct` nhưng thêm nét vẽ lạ. LR3D_124 ra màu sặc sỡ (xanh lá, vàng), LR3D_97 méo. Đường nối kém nhất (1,92, sát ngưỡng loại 2,0).
- **`elements_sam`:** áo sạch, nhìn như thêu họa tiết riêng, nhận ra hình chính ở LR3D_33, LR3D_50, LR3D_124. Hai trong sáu hiện vật quy tắc chọn tự động lấy phải mảnh vụn: lá (LR3D_38), đuôi rồng (LR3D_61).

## Giới hạn cần nhớ

- SIFT chỉ đo kế thừa pixel. `img2img_low` giữ bố cục nhưng SIFT gần 0, nên SIFT thấp không có nghĩa là hỏng.
- Chỉ số lọt hình bình coi viền phẳng là "nền". Ô `elements_sam` có nền phẳng, nên số 0,106 bị thổi phồng, không so được.
- `garment.apply` kéo mọi ô về cùng độ rộng. Ô `elements_sam` chỉ có 2 họa tiết nên mỗi họa tiết in to hơn nhiều. Khác biệt ở mức này lẫn với cỡ họa tiết.
- `paste_direct` không dùng seed hoa văn: ba seed chỉ khác áo và polish, nên thực chất 6 ô độc lập.
- Chưa chấm mù, chưa có chỉ số giống hiện vật bằng DreamSim. Nguyên nhân mờ màu của `paste_direct` trên áo mới là giả thuyết (độ tương phản thấp của mảng sau khi bỏ nền), chưa kiểm.

## Sửa màu mờ: mức `paste_boost` (thêm ngày 20/11/2026)

**Nguyên nhân (đã đo).** `garment.apply` chỉ in điểm có sắc độ từ 16 đến 34 hoặc đủ tối. Mảng phẳng cắt từ ảnh bình có sắc độ thấp: p90 chỉ 11 đến 30, trong khi ô do SD sinh là 28 đến 62. Độ đục trung bình của ô dán nguyên thấp hơn ô SD ở 4 trong 6 hiện vật (LR3D_97 chỉ 0,05).

**Cách sửa.** Hàm `boost_ink` trong `evaluation/exp_g.py` kéo mực ra xa màu nền trong không gian LAB, neo tại màu nền để nền không đổi. Hai hệ số, đều tự về 1 khi ảnh đã đủ tương phản:
- Kéo khoảng cách tới màu nền (phân vị 98 lên 60, tối đa 3 lần).
- Kéo sắc độ (phân vị 95 lên 45, tối đa 2 lần), chỉ cho điểm nghiêng về xanh. Bản kéo mọi hướng làm hiện đốm vàng (vết ố men) ở LR3D_97 nên đã bỏ.

**Kết quả** (cùng áo LoRA, mã băm áo giống hệt lần chạy trước; 18 lượt mới, 72 lượt cũ giữ nguyên). Mức in mực là độ lệch màu ΔE giữa áo cuối và áo trơn trong vùng in:

| Hiện vật | dán nguyên | dán nguyên + kéo | SD ControlNet |
|---|---|---|---|
| LR3D_33 | 11,8 | 13,3 | 17,4 |
| LR3D_38 | 5,0 | **12,2** | 6,5 |
| LR3D_50 | 19,4 | 19,4 (không đổi) | 14,6 |
| LR3D_61 | 11,9 | 13,6 | 18,6 |
| LR3D_97 | 2,9 | **7,1** | 10,6 |
| LR3D_124 | 18,6 | 22,8 | 6,9 |
| **Trung bình** | 11,6 | **14,7** | 12,4 |

Sắc độ p95 trong vùng in: 11,1 lên 21,1 (SD là 25,1). Các chỉ số cũ gần như không đổi: lọt hình bình 0,037 xuống 0,028, đường nối 1,28 xuống 1,27, giữ họa tiết qua polish 0,949 lên 0,953. SIFT giảm từ 0,395 xuống 0,293 vì đổi màu làm đổi gradient; họa tiết vẫn là bản cắt từ mảng.

**Còn lại.**
- LR3D_33 và LR3D_61 vẫn xám xanh hơn ô SD (sáng, vivid).
- LR3D_97 vẫn yếu vì nguồn vốn nhạt, kéo thêm sẽ khuếch đại nhiễu men.
- LR3D_124 hơi ngả xanh ngọc ở lông vũ; chưa đối chiếu với màu thật của hiện vật.
- Chưa chấm mù. Tham số 60 và 45 chọn bằng mắt trên seed 42, chưa hiệu chỉnh trên tập khác.
- Ảnh thử: `outputs/experiments/EXP-G/boost_trial3_seed42.jpg`; so sánh trước và sau: `contact_boost_vs_direct_seed42.jpg`.

## Chọn phần tử tốt: mức `elements_clip` (thêm ngày 20/11/2026)

**Vấn đề.** Quy tắc chọn cũ (`element_library.score`: cạnh ngắn x tỉ lệ mực) không biết phần tử có nguyên vẹn hay có phải hình chính, nên lấy mảnh vụn ở LR3D_38 (cặp nửa lá) và LR3D_61 (mảnh cong).

**Quy tắc mới** (`pick_main_element` trong `evaluation/exp_g.py`, tất định):
1. Lọc hình dạng: cạnh ngắn từ 200 px, tỉ lệ cạnh dài trên cạnh ngắn tối đa 2,6, độ lấp đầy hộp bao từ 0,30. Không ai qua lọc thì xét tất cả.
2. CLIP chấm độ khớp giữa ảnh phần tử (đặt trên màu nền men) và mô tả hiện vật (`name_en` cộng `base_description` trong `data/prompt_terms.json`).
3. Nhân hệ số phạt nhẹ cho phần tử nhỏ: (cạnh ngắn / 400) mũ 0,25, tối đa 1. Hòa điểm thì theo mã phần tử.

**Phần tử chọn:**

| Hiện vật | Cũ | Mới | Nhận xét (xem ảnh) |
|---|---|---|---|
| LR3D_33 | cành mẫu đơn | cartouche chim phượng nguyên vẹn | Đúng hơn với "medallion", nhưng nét mảnh và nhạt hơn khi in |
| LR3D_38 | cặp nửa lá | cụm cành lá | Nguyên vẹn hơn, nhưng nguồn vốn nhạt nên in vẫn mờ |
| LR3D_50 | hoa sen có đuôi rách | hoa sen sạch | Tốt hơn rõ |
| LR3D_61 | mảnh cong | mảnh mây | Vẫn chưa phải rồng. Mô tả là "rồng và mây" nên CLIP chọn mây; mặt rồng đứng hạng 3 |
| LR3D_97, LR3D_124 | giữ nguyên | giữ nguyên | Đã đúng từ trước |

**Số đo** (18 lượt mỗi mức): giữ chi tiết mịn 0,908 lên 0,914 (p=0,02). SIFT 0,079 xuống 0,067. Mức in mực ΔE giảm ở LR3D_33 (7,4 xuống 4,8) và LR3D_61 (10,3 xuống 4,4), vì phần tử mới nhạt và thanh hơn. Các chỉ số còn lại không khác có ý nghĩa.

**Lưu ý chỉ số đường nối.** `seam_ratio` tăng từ 1,32 lên 1,95, riêng LR3D_38 (2,96) và LR3D_61 (2,57) vượt ngưỡng loại 2,0. Đây là sai số của chỉ số, không phải đường nối thật: ô xếp theo cấu trúc nên liền mạch, độ lệch qua đường nối nằm trong khoảng độ lệch giữa các cột kề bên trong (LR3D_38: 0,89 so với p99 là 1,59). Chỉ số chia cho sai khác trung bình toàn ô, mà ô thưa phần lớn là nền phẳng nên mẫu số rất nhỏ. Giống `vessel_leakage` ở `elements_sam`: hai chỉ số cổng G2 thiên lệch với ô thưa.

**Giới hạn.**
- Quy tắc chọn phần tử đúng hơn, nhưng không biết đâu là hình chính khi mô tả có nhiều thành phần (LR3D_61).
- Chỉ 6 hiện vật, chọn quy tắc và tham số (2,6; 0,30; 400; 0,25) sau khi xem ảnh của chính 6 hiện vật này, nên chưa kiểm trên tập khác.
- Chưa chấm mù. Phần CLIP của hàm chọn chưa có subagent kiểm độc lập; hàm xếp hạng thuần túy có test.
- Ảnh so sánh: `outputs/experiments/EXP-G/contact_elements_sam_vs_clip_seed42.jpg` (hai cột ô hoa văn, hai cột áo cuối, cũ rồi mới).

## Kéo màu cho phần tử: mức `elements_boost` (thêm ngày 20/11/2026)

Cùng phần tử và cách xếp ô của `elements_clip`, thêm bước `boost_ink` (cùng hàm, cùng tham số 60 và 45 như `paste_boost`). 18 lượt mới.

**Độ đậm mực** là ΔE trung bình của điểm mực rõ (ΔE so với áo trơn trên 15, bản ghép thô trước polish) và phần trăm vùng in có mực rõ:

| Hiện vật | clip | boost |
|---|---|---|
| LR3D_33 | 26,8 (9,5%) | 30,5 (13,1%) |
| LR3D_38 | 20,3 (34,4%, mảng nền) | **38,6 (9,3%)** |
| LR3D_50 | 37,7 (11,4%) | 37,7 (không đổi) |
| LR3D_61 | 35,9 (6,9%) | 39,7 (7,5%) |
| LR3D_97 | 19,4 (16,9%, mảng nền) | **31,7 (11,1%)** |
| LR3D_124 | 33,0 (18,5%) | 37,8 (19,7%) |

Xem ảnh: nét xanh rõ hơn ở LR3D_38 và LR3D_97, tăng nhẹ ở LR3D_33, LR3D_61 và LR3D_124, không đổi ở LR3D_50. Các chỉ số khác: SIFT 0,067 xuống 0,058, lệch màu ΔE 1,25 lên 1,59 (p=0,003, màu bị kéo xa bảng màu gốc), giữ chi tiết mịn 0,914 xuống 0,913. Đường nối 1,95 lên 2,03 (chỉ số thiên lệch với ô thưa, xem mục trước).

### Phát hiện: nền ô bị in cả mảng khi mực quá nhạt

`garment.ground_alpha` (trong pipeline, `generation/garment.py`) có quy tắc dự phòng: độ đục trung bình dưới 0,05 thì giữ đục hoàn toàn, để hoa văn trắng trên nền kem không biến mất. Hệ quả: ô có mực rất nhạt bị in **cả màu nền** thành một mảng phẳng đè lên áo.

Độ đục trung bình của ô trước khi áp quy tắc dự phòng (dưới 0,05 là bị in cả nền):

| Hiện vật | elements_sam | elements_clip | elements_boost |
|---|---|---|---|
| LR3D_38 | 0,050 | **0,041** | 0,115 |
| LR3D_61 | **0,046** | 0,085 | 0,093 |
| LR3D_97 | **0,015** | **0,015** | 0,144 |

Đó là các mảng xám trên thân áo ở ảnh `elements_sam` và `elements_clip`, và nó làm sai các chỉ số ΔE của hai mức đó ở những hiện vật trên. `boost_ink` đẩy độ đục lên trên 0,1 nên tránh được lỗi này. Phần cải thiện của mức kéo màu ở LR3D_38 và LR3D_97 vì vậy gồm cả việc bỏ mảng nền, không chỉ làm mực đậm hơn.

**Chưa sửa** trong pipeline chính. Hướng sửa gợi ý: chỉ dùng quy tắc dự phòng khi ô là hoa văn trắng trên nền kem (nền sáng và mực còn sáng hơn nền), không dùng cho ô mực xanh nhạt trên nền xám. Cần bàn trước khi sửa vì nó đổi hành vi của mọi lượt sinh.

**Giới hạn.** Tham số kéo màu vẫn chọn bằng mắt trên seed 42. Chưa chấm mù. Chưa có số đo độ giống hiện vật bằng DreamSim, nên "màu gần hiện vật hơn" chưa được kiểm; ΔE tăng cho thấy màu có xa bảng màu gốc hơn.

## Sửa lỗi nền in cả mảng (`ground_alpha`) (20/11/2026)

**Sửa trong pipeline chính:** `generation/garment.py`, hàm `ground_alpha` và hàm mới `_faint_ink_alpha`. Chỉ đổi nhánh dự phòng (độ đục trung bình dưới 0,05). Mọi ô có độ đục từ 0,05 trở lên đi đường cũ, không đổi kết quả (có test dùng `monkeypatch` chứng minh nhánh mới không được gọi).

**Cách làm.** Nhánh dự phòng cũ trả toàn 1 (giữ đục hoàn toàn) để hoa văn trắng trên nền kem không biến mất. Nhánh mới thử trước: so từng điểm với màu nền của ô (trung vị từng kênh LAB), nếu ô là "nền phẳng có mực thưa" thì trả độ đục theo độ lệch nền (nền trong suốt, mực đục); không thì vẫn trả toàn 1 như cũ. Ô được coi là "nền phẳng có mực thưa" khi cả ba điều kiện đúng, với khoảng cách ΔE76 tới màu nền:

| Điều kiện | Ngưỡng |
|---|---|
| Điểm gần nền (ΔE dưới 8) chiếm ít nhất | 82% |
| Điểm lệch nhẹ (ΔE từ 8 đến 20) chiếm nhiều nhất | 12% |
| Điểm mực rõ (ΔE từ 20 trở lên) chiếm ít nhất | 0,5% |

**Kiểm tra độc lập.** Một subagent đọc logic tìm ra lỗ hổng ở bản sửa đầu (ngưỡng đơn 0,5% mong manh). Ca đối kháng đã thêm test: hoa văn trắng kèm đốm bẩn 5x5 (gần nền 0,80, lệch nhẹ 0,20), vùng sáng chiếm hơn nửa ô, nền nhiễu σ=10 (gần nền 0,56). Cả ba vẫn giữ đục hoàn toàn như cũ. Một subagent khác tính trước từ đặc tả: khớp với mã. Toàn bộ pytest đạt, không hồi quy.

**Giới hạn.** Ba ngưỡng hiệu chỉnh trên 6 ô phần tử thật (gần nền từ 0,858, lệch nhẹ tới 0,087) và vài ca tổng hợp; biên còn hẹp (0,858 so với 0,82; 0,087 so với 0,12). Ô thật khác có thể rơi sát ngưỡng. Chưa thử trên ô do SD sinh có nền thưa mực.

**Kết quả chạy lại** (36 lượt `elements_sam` và `elements_clip`; các mức khác không đi qua nhánh này nên giữ nguyên). Mảng nền xám trên thân áo ở LR3D_38 và LR3D_97 biến mất, chỉ còn mực; các hiện vật khác giống hệt trước. Độ đậm mực chỉ còn là mực (ΔE trung bình vùng in, bản ghép thô; phần trăm vùng ΔE trên 15):

| Hiện vật | elements_sam | elements_clip | elements_boost |
|---|---|---|---|
| LR3D_33 | 5,7 (14,0%) | 3,2 (9,5%) | 4,5 (13,1%) |
| LR3D_38 | 2,3 (8,0%) | 1,7 (4,9%) | 3,9 (9,3%) |
| LR3D_50 | 5,4 (12,6%) | 4,6 (11,4%) | 4,6 (11,4%) |
| LR3D_61 | 1,6 (4,2%) | 2,7 (6,9%) | 3,2 (7,5%) |
| LR3D_97 | 1,4 (2,6%) | 1,4 (2,6%) | 4,0 (11,1%) |
| LR3D_124 | 6,7 (18,5%) | 6,7 (18,5%) | 8,0 (19,7%) |

Hệ quả: kéo màu (`elements_boost`) vẫn cho mực rõ hơn rõ ở LR3D_38 (1,7 lên 3,9) và LR3D_97 (1,4 lên 4,0), nhưng phần cải thiện là **thật sự do kéo màu**, không còn lẫn với việc bỏ mảng nền như tôi đã viết ở mục trước. Ảnh so sánh trước và sau sửa: `outputs/experiments/EXP-G/contact_alpha_fix_before_after_seed42.jpg` (cột 1 và 2: elements_clip trước, sau; cột 3 và 4: elements_sam trước, sau).
