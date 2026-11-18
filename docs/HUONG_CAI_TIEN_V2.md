# Hướng cải tiến hệ thống Tái Sinh Di Sản Số, Phiên bản 2 (bản chỉnh ngày 19/11/2026)

- **Ngày:** 19/11/2026. Hạn nộp minh chứng cải tiến: hết ngày 25/11/2026.
- **Mục tiêu:** (1) họa tiết gốm còn nhận ra được sau khi vẽ lại, không chỉnh tay; (2) ảnh áo dài chân thực; (3) đủ minh chứng cho ba yêu cầu của ban tổ chức; (4) có đường dẫn để ban tổ chức thử.
- **Phạm vi:** giữ kiến trúc hai giai đoạn hiện tại và cách **vẽ lại họa tiết bằng diffusion ở mọi mức** (vẽ lại mới đẹp và có sáng tạo). Cải thiện đầu vào (ảnh nét lấy từ phần tử họa tiết), nền áo độ phân giải cao, polish nhẹ có mặt nạ, bộ đánh giá đo độ trung thành nhận ra được kèm tiêu chí loại, và hồ sơ nguồn. Dán nguyên phần tử lên áo chỉ còn là mốc đối chiếu tùy chọn.
- **Đổi hướng ngày 19/11:** bản trước đặt mức 1 là "giữ nguyên từng pixel bằng phương pháp tất định". Nhóm quyết định bỏ yêu cầu đó vì các paper tham khảo đều biến đổi họa tiết thay vì dán nguyên, và dán nguyên không đẹp, không sáng tạo. Yêu cầu của ban tổ chức là kiểm tra độ giữ họa tiết, được hiểu là độ trung thành nhận ra được (đo bằng DreamSim và SIFT), không phải trùng pixel.

## 0. Cần bạn quyết (ảnh hưởng đến kế hoạch)

| # | Câu hỏi | Nếu có | Nếu không |
|---|---|---|---|
| 1 | Nhóm có ảnh áo dài trơn thật (tự chụp, có đồng ý người mẫu) trong 1 đến 2 ngày không? | Dùng làm nền chính (mục 6) | Dùng nền AI 1024px, ghi rõ giới hạn chân thực |
| 2 | Ngày chung kết thật là ngày nào? File cũ từng ghi 20 đến 22/11, chưa xác nhận | Nếu sớm hơn 25/11, nén lịch ở mục 10 | Giữ lịch 18 đến 25/11 |
| 3 | Có người am hiểu di sản hoặc thiết kế ngoài nhóm không? | Gửi phiếu thẩm định (mục 8.4) | Ghi rõ "chưa có chuyên gia", không tuyên bố đã thẩm định |
| 4 | Môi trường Python: CLAUDE.md quy định `uv` và `pyproject.toml`, repo hiện dùng `requirements.txt` và `scripts/01_setup_env.ps1` | Làm theo CLAUDE.md, chuyển sang uv | Giữ hiện trạng và ghi lệch quy ước |
| 5 | Ngưỡng loại (mục 8.2) | Chốt sau khi đo thực tế trên 6 hiện vật | Dùng ngưỡng đề xuất |
| 6 | Ai liên hệ nhóm tác giả LR3D-CULT2 (FPT University, Hà Nội) và nhóm VietFashion để hỏi xuất xứ, giấy phép, phạm vi dùng? | Có phản hồi bằng văn bản: cập nhật mục 2 và dùng được rộng hơn | Không có: giữ trạng thái "chưa xác minh", chỉ dùng nội bộ |
| 7 | Thay 6 hiện vật gốc bằng 6 mảng LR3D (phương án B) | **Đã chọn ngày 19/11/2026.** Ghi rõ thay đổi trong hồ sơ nộp (danh mục nguồn); nên hỏi ban tổ chức xem họ chấp nhận không nếu liên hệ được | Nếu ban tổ chức không chấp nhận: quay về bộ gốc làm bộ chính (phương án A), giữ 6 mảng LR3D làm bộ mở rộng. Bản thay nằm ở commit `3a849df`, dễ hoàn lại |

## 1. Kết luận thiết kế

Không thay toàn bộ hệ thống bằng một model lớn hơn. Ba ưu tiên, theo thứ tự:

1. **Vẽ lại có kiểm soát, họa tiết còn nhận ra được.** Mọi mức vẫn dùng ControlNet vẽ lại họa tiết. Mức 1 là mức trung thành: họa tiết chính phải còn nhận ra là hoa văn gốc, đo bằng DreamSim và SIFT (M4). Sửa các nguyên nhân gây hỏng hiện tại: ảnh nét lấy từ phần tử thay vì cả hiện vật thu về 512 px, nền áo cao phân giải, polish nhẹ hơn. Thiết kế mức 1 của vật #61 hiện làm mất hẳn con rồng, đó là lỗi phải sửa dù theo tiêu chuẩn lỏng. Dán nguyên phần tử chỉ làm mốc đối chiếu tùy chọn (mục 3.3).
2. **Nền áo độ phân giải cao.** Ảnh áo hiện tại do Stable Diffusion sinh ở 512×512, thân áo rộng khoảng 90 px, nên mọi họa tiết đều bị thu nhỏ 4 đến 5 lần. Đây là điểm nghẽn của độ chân thực.
3. **Minh chứng đủ cho ba yêu cầu:** tiêu chí loại và thử lại có ngưỡng, so sánh có kiểm soát nhiều seed, hồ sơ nguồn và quyền sử dụng của 6 hiện vật.

Fine-tune LoRA chuyển xuống thử nghiệm tùy chọn (mục 4.4). Lý do nằm ở số liệu quét dữ liệu ở mục 2.

```text
Ảnh hiện vật gốm (6 hiện vật, có nguồn và giấy phép ghi trong hồ sơ)
    ↓
Cắt mảng texture phẳng từ mô hình 3D (đảo UV có nhiều nét mực lam nhất)
    ↓
Cắt phần tử họa tiết bằng SAM thành ảnh RGBA, kiểm tra tự động (đã có module)
    ↓
Kho phần tử (kèm nguồn, giấy phép, tham số)
    ↓
 ┌──────────────────────────────────────────────────────────────┐
 │ Mọi mức 1 đến 4: ControlNet Canny vẽ lại họa tiết từ phần tử   │
 │ (mức 1 bám sát nhất, mức 4 tự do nhất)                         │
 │ Mốc đối chiếu tùy chọn: dán nguyên phần tử, không qua diffusion │
 └──────────────────────────────────────────────────────────────┘
    ↓
Ghép lên nền áo độ phân giải cao theo ánh sáng và nếp vải
    ↓
Polish nhẹ có mặt nạ, dán lại pixel gốc ngoài vùng áo
    ↓
Đo tự động, thử lại hoặc loại theo tiêu chí
    ↓
Chấm mù nội bộ + phiếu thẩm định chuyên gia
    ↓
Design Passport, nhãn "có hỗ trợ AI", nhật ký chỉnh sửa
```

## 2. Dữ liệu và nguồn

### 2.1. Sáu hiện vật đang dùng, nguồn thật và hiện trạng giấy phép

**Cập nhật 18/11/2026: 6 hiện vật dưới đây đã được thay trong dữ liệu chạy bằng 6 vật thể từ LR3D-CULT2** (ảnh hiện vật mặc định là ảnh render cả bình, mảng texture phẳng là nhánh so sánh, xem mục 4.1) (vật #33, #61, #50, #38, #97, #124, mã `LR3D_<số>` trong `data/heritage/`). Ảnh được cắt tự động bằng `scripts/10_make_heritage_from_lr3d.py`, khung cắt ghi ở `data/heritage/lr3d_crops.json`. Nhãn hiển thị là "Gốm men lam · LR3D-CULT2 (Bát Tràng, Thanh Hà)", lặp lại mô tả của bộ dữ liệu và không khẳng định từng vật là Bát Tràng. Nhóm đã chọn phương án B (giữ bản thay) ngày 19/11/2026. Danh mục nguồn, giấy phép, cách ghi công và lịch sử các bước do người làm nằm ở `docs/DANH_MUC_NGUON_HIEN_VAT.md`. Sáu ảnh cũ vẫn còn trong thư mục (chưa xóa), bản dữ liệu cũ nằm trong lịch sử git. Phần bảng và hai vấn đề dưới đây mô tả sáu hiện vật cũ, giữ lại để đối chiếu. Chất lượng ảnh biến thể sinh từ hiện vật mới giống hệ thống cũ: họa tiết được diễn giải lại, chưa giữ được rõ (ví dụ con rồng của vật #61 mất ở mức 1). Việc cần làm là cải thiện đầu vào cho vẽ lại (mục 4.1), không phải dán nguyên.

Thông tin lấy từ `data/metadata.json` (file có đường dẫn nguồn). Cả 6 ảnh có `license: unverified` và ghi chú "chỉ dùng nội bộ MVP".

| Mã hiện vật | Tên trong metadata | Nguồn (trang bán hàng) | Kích thước ảnh |
|---|---|---|---|
| `BT_Hac_XP` | Bình gốm dáng Tỏi hút lộc | fullhome-decor.com | 1746 px |
| `HSBT_XP-300x300` | Bình gốm hoa sen mực đen | fullhome-decor.com | 300 px |
| `BHV_UU_XP1-600x600` | Bình gốm chim công phong thủy | fullhome-decor.com | 600 px |
| `MB_2C_XP_31` | Bình gốm thuyền buồm | fullhome-decor.com | 1191 px |
| `BT010_2` | Bình gốm cúc vạn thọ | battrangceramica.com.vn | 324×617 px |
| `binh-hoa-su-trang-ap-noi-hoa-sen-dat-vang-24k-...` | Bình hoa sứ trắng sen dát vàng 24k | xuonggomsuviet.vn | 1024 px |

URL đầy đủ nằm trong `data/metadata.json`.

**Hai vấn đề cần sửa trước khi nộp, vì ảnh hưởng trực tiếp đến yêu cầu 3:**

1. **Nhãn trong `data/heritage/items.json` mâu thuẫn với nguồn thật.** File này ghi nguồn như "Bảo tàng Lịch sử Quốc gia", niên hiệu Chính Hòa, Vĩnh Thịnh, Cảnh Hưng, thế kỷ XVIII. Trong khi `data/metadata.json` cho thấy ảnh lấy từ trang bán hàng gốm trang trí. Tên cũng lệch (ví dụ `BT_Hac_XP` là "hoa lam công và sen" ở một file, "Tỏi hút lộc" ở file kia). Việc cần làm: lấy `data/metadata.json` làm căn cứ, bỏ hoặc sửa niên hiệu và nguồn bảo tàng nếu không có trích dẫn kiểm chứng được, tạm gắn nhãn "ảnh sản phẩm gốm Bát Tràng từ trang bán hàng".
2. **Giấy phép chưa xác minh.** Việc cần làm: liên hệ cửa hàng xin phép bằng văn bản, hoặc thay bằng ảnh nhóm tự chụp, hoặc ảnh có giấy phép mở (mục 2.3). Trong lúc chưa xong, ghi rõ trạng thái trong Passport và không dùng ảnh trong tài liệu công khai.
3. Mô tả `team_description` có nhiều đoạn giống văn bán hàng (ví dụ "thu hút tài lộc, mang lại vượng khí"). Cần kiểm tra có chép từ trang gốc không, và viết lại hoặc trích dẫn đúng.
4. Hai file `data/metadata.json` và `data/heritage/metadata.json` trùng cấu trúc, file thứ hai có `image_source_url: null`. Cần chọn một file làm nguồn duy nhất.

### 2.2. LR3D-CULT2: hạ xuống nguồn tham khảo bổ sung

- **Tên:** LR3D-CULT2, Vietnamese Ceramic Cultural Artifacts (mesh 3D và ảnh render đa góc).
- **Trang:** <https://data.mendeley.com/datasets/jr23fnrvx2/1>, DOI `10.17632/jr23fnrvx2.1`, giấy phép công bố theo trang dataset: CC BY 4.0.
- **Dung lượng:** file `data/LR3D-CULT2 ... .zip` khoảng 7,7 GB, bên trong là 8 zip lồng nhau (6 zip bình gốm, 2 zip `metal_cups_` cùng dung lượng 72042717 byte, nhiều khả năng trùng và không phải gốm).

**Kết quả quét ngày 18/11/2026 trên cả 6 zip bình gốm (120 vật thể). Phân loại bằng mắt trên bảng ảnh thu nhỏ 256 px. Không dùng chỉ số màu vì chỉ số đó không đáng tin:**

| Điều kiện | Kết quả |
|---|---|
| Ảnh render | 512×512, hơi mờ, bình chỉ chiếm khoảng 180×320 px, 180 ảnh mỗi vật. Không đủ nét để huấn luyện |
| Texture gốc của mô hình 3D | 1024 đến 8192 px, đã trải phẳng sẵn. Dùng tốt để cắt phần tử ở vùng có hoa văn thật |
| Lam trắng, mảng sạch và lớn | Khoảng 12 đến 15 vật: #15 (dải chim và cây, 7319×3258), #50, #59, #61 (rồng), #124, #37, #38, #47, #78, #119, #118, #33, #83 (bình dẹt rồng lam), #97 (4 mặt trải phẳng) |
| Lam trắng nhưng bị cắt vụn hoặc lỗi quét | Khoảng 20 vật: #19, #32, #34, #44, #45, #46, #53, #55, #79, #110, #111, #114, #115, #116, #74, #89, #92, #94, #100 |
| Không phải lam trắng | Khoảng 85 vật: men nâu, men ngọc, đất nung, mảnh xám, hoa phấn nhiều màu |
| Lỗi thường gặp | Vùng nội suy sinh vệt tỏa tròn (#31 đến #36) hoặc ô vuông (#51, #52, #58). Mảnh gốm khảo cổ có vết bẩn và lỗ trống. #40 không tìm thấy texture, #48 trông như bản đồ pháp tuyến, không phải ảnh màu |
| Không hợp chủ đề | Có chữ Latin (#1), nhãn thương mại (#54), kiểu cung đình vàng (#66), họa tiết trông như in hiện đại (#57), rồng lam kiểu gần gốm Trung Hoa (#61, #83, #118). Cần chuyên gia xác nhận |
| Nguồn gốc | Metadata chỉ có tên (`binh_gom_NN`), tâm vật thể, vị trí camera. Không có giấy phép hay xuất xứ từng vật. Trang dataset ghi chung cho cả bộ: một phần "digitized from photogrammetric scans collected in the Bát Tràng and Thanh Hà pottery villages", một phần "3D models sourced from Sketchfab under academic-use licenses", không chỉ ra vật nào thuộc nguồn nào |

**Đính chính:** tiền tố `sketchfab_collection_1` (khoảng #1 đến #53), `_2` (#54 đến #78), `_3` (#79 đến #124) trong tên ảnh render chưa rõ nghĩa. Có thể chỉ là tên cảnh render của tác giả. Không dùng tiền tố này làm bằng chứng nguồn gốc. Bản trước của tài liệu này đã suy diễn sai điều đó.

**Hệ quả:**

- Có khoảng 12 đến 15 vật lam trắng sạch với texture 4096 đến 8192 px. Mỗi vật cho được nhiều crop, nên kho phần tử và nhánh LoRA thử nghiệm (mục 4.4) đáng thử, nhưng chưa chắc có lợi.
- Không xác định được vật nào là Bát Tràng. Không khẳng định từng vật là Bát Tràng; chỉ dùng câu chuẩn ở `docs/DANH_MUC_NGUON_HIEN_VAT.md` mục 4 (nhắc Bát Tràng và Thanh Hà theo mô tả của bộ dữ liệu).
- Giấy phép từng vật chưa rõ và có thể mâu thuẫn với CC BY 4.0 ghi chung trên trang. Chỉ dùng cho thử nghiệm nội bộ, chưa đưa vào sản phẩm công khai. Cập nhật 19/11/2026: nhóm cho biết đã được phép dùng phi thương mại (chưa có bằng chứng lưu trong hồ sơ, xem mục 3.5). Khi có bằng chứng, dùng cho bản thử nghiệm của ban tổ chức là hợp lý, kèm nhãn phi thương mại.
- Việc cần làm: hỏi nhóm tác giả bằng văn bản về ánh xạ vật và nguồn gốc, giấy phép từng vật. Chưa có ai liên hệ (câu hỏi 6 ở mục 0).
- Giới hạn của đánh giá này: nhìn bằng mắt trên ảnh thu nhỏ, chưa kiểm tra từng vật ở độ phân giải đầy đủ. Kết quả đo nằm ngoài repo (file CSV và bảng ảnh trong thư mục tạm của phiên làm việc).

### 2.3. Nguồn mở bổ sung (tùy chọn)

Có thể dùng các ảnh Wikimedia Commons có giấy phép ghi riêng trên từng trang, kiểm tra lại trước khi dùng:

- [Vietnam 17th C, Bat Trang jar, ghi CC0](https://commons.wikimedia.org/wiki/File:Vietnam_17th_C_-_Bat_Trang_jar_NUS_Museum.jpg)
- [Bát Tràng DSC 0096, ghi CC BY-SA 4.0](https://commons.wikimedia.org/wiki/File:B%C3%A1t_Tr%C3%A0ng_DSC_0096.JPG)

Mỗi nguồn ghi riêng giấy phép trong metadata. Không trộn giấy phép khi chưa xác định điều kiện chia sẻ ảnh dẫn xuất.

### 2.4. VietFashion (chưa xác minh, chưa dùng)

VietFashion là dataset áo dài và thời trang Việt Nam, trang dự án <https://hng0303.github.io/VietFashion>.

- Trang chính thức không nêu giấy phép cho dataset, paper hay mã. Chỉ ghi dataset "publicly available". Giấy phép CC BY-NC-ND 4.0 gặp ở bài báo chưa chắc áp dụng cho dataset.
- Nội dung: tập trung vào áo dài. Có 650 bản phác thảo do người vẽ, hơn 21.000 ảnh do SANA-ControlNet sinh theo phác thảo, câu mô tả trung bình 42 từ trích từ tạp chí thời trang, 11 nhóm thuộc tính. Các thuộc tính chia ba nhóm: cấu trúc (dáng thân áo, cổ, tay), chi tiết (vải, họa tiết hoa, eo) và bối cảnh (nền, ánh sáng). Đây không phải ảnh áo dài thật.
- Chưa biết (trang và bài báo không nêu): tỉ lệ ảnh đúng dáng áo dài, độ phân giải ảnh, ảnh có người mặc hay chỉ có áo, và có kiểm tra chất lượng ảnh sinh hay không. Kiểm chứng ở mục 6.3.
- Nếu đúng là CC BY-NC-ND: dùng phi thương mại cho nghiên cứu hoặc thi đấu có thể được. Điều khoản ND (không phái sinh) khiến việc phát hành hoặc deploy mô hình, ảnh sinh từ dữ liệu này là vùng xám.
- Rủi ro khác: bản quyền của ảnh do AI sinh, câu chữ trích từ tạp chí, và nguy cơ mô hình học thêm nét "ảnh AI".
- Việc cần làm: hỏi nhóm tác giả bằng văn bản về phạm vi dùng (câu hỏi 6 ở mục 0). Trong lúc chờ, không dùng để huấn luyện bản công khai.

## 3. Giai đoạn 1: kho phần tử họa tiết (đầu vào cho vẽ lại và mốc đối chiếu)

Mục tiêu: lấy các phần tử họa tiết nét từ ảnh gốm, giữ nguyên pixel khi cắt, không chỉnh tay. Phần tử dùng để (a) lấy ảnh nét đầu vào cho ControlNet ở mọi mức, (b) làm mốc đối chiếu tùy chọn (mục 3.3).

### 3.1. Các bước

Với mảng texture phẳng của LR3D-CULT2, bước 2 và 3 (silhouette, trải trụ) không cần, vì texture đã phẳng và mô hình 3D cho sẵn vùng hợp lệ (UV). Hai bước đó chỉ cần nếu quay lại dùng ảnh chụp bình cong. Phần đã có: `generation/elements.py`, `scripts/08_extract_lr3d.py`, `09_build_elements.py`, `10_make_heritage_from_lr3d.py`.

1. **Kiểm tra ảnh nguồn:** độ phân giải, có kênh trong suốt (alpha) không, bình có bị che khuất không. Ghi kết quả vào hồ sơ.
2. **Tách silhouette** (viền ngoài của bình): dùng alpha nếu có. Nếu không, dùng Grounded SAM. Grounding DINO là mô hình phát hiện vật theo mô tả chữ (ví dụ "ceramic vase"), cho ra khung chữ nhật. SAM (Segment Anything) nhận khung đó và cho ra mask chính xác theo viền.
3. **Trải trụ:** bình gần giống hình trụ, nên ảnh chụp bị co ở hai mép. Từ silhouette tính bán kính từng hàng ảnh, góc theta = arcsin((x trừ tâm) chia bán kính), rồi lấy mẫu lại thành ảnh phẳng. Dùng tỉ lệ ngang theo từng hàng, chỉ giữ dải có bán kính từ 60% bán kính lớn nhất trở lên và góc nhìn không quá 65 độ. Lần thử trước dùng ngưỡng 85% đã cắt mất thân thuyền, cần dùng 60%.
4. **Cắt phần tử:** SAM tự phân đoạn, hoặc Grounded SAM theo từ khóa (con thuyền, chim công, hoa sen, hoa cúc). Mỗi phần tử lưu thành ảnh RGBA (màu cộng kênh trong suốt).
5. **Kiểm tra tự động** (không cần người): diện tích tối thiểu, mask liền một khối, độ phân giải tối thiểu của phần tử, mức co giãn khi trải phẳng được ghi lại, không có pixel nằm ngoài silhouette. Phần tử không đạt thì loại và ghi lý do vào nhật ký.
6. **Lưu kho phần tử** (đề xuất đặt ở `data/elements/`, không commit vì là ảnh thô). Mỗi phần tử kèm: mã hiện vật nguồn, giấy phép, tham số trải trụ, mã phiên bản thuật toán.

### 3.2. Kết quả thử trên ảnh chụp bình cũ (không còn dùng)

Thử trước đây trên 6 ảnh chụp bình cũ, nay đã được thay bằng 6 mảng LR3D (mục 2.1). Mã không còn trong nhánh. Kết quả, giữ để tham khảo:

- Tốt: thuyền, hoa sen đen, hoa cúc.
- Con công: mask còn lẫn hoa xung quanh.
- Sen dát vàng: trắng trên trắng, khó tách.
- Bình hồ lô, bình cầu: trải phẳng sai ở vai và đáy.
- `BT_Hac_XP` chưa đủ kết quả để kết luận, cần chạy lại.
- Ba ảnh nguồn dưới 1024 px (300, 324, 600) sẽ mờ khi phóng to. Không được tuyên bố độ nét cao cho các ảnh này.

### 3.3. Mốc đối chiếu tùy chọn: dán nguyên phần tử

Dán nguyên phần tử lên áo (không qua Stable Diffusion) chỉ làm khi còn thời gian. Mục đích là làm mốc để đo: so họa tiết vẽ lại với bản dán nguyên bằng M4, để chứng minh bằng số rằng vẽ lại vẫn giữ họa tiết. Đây không phải sản phẩm chính. Nếu làm, vùng họa tiết của bản này phải trùng pixel với phần tử (sai khác bằng 0, chỉ số M3).

### 3.4. Cách tận dụng LR3D-CULT2 (thử nghiệm nội bộ)

Dataset có mô hình 3D (`.obj`), texture trải phẳng, 180 ảnh render và vị trí camera mỗi vật. Có bảy hướng dùng, xếp theo thứ tự nên làm:

| # | Hướng | Cách làm | Giúp được | Công sức | Rủi ro |
|---|---|---|---|---|---|
| 1 | Kho phần tử từ texture | Tách vùng có hoa văn khỏi nền đen, cắt phần tử bằng SAM, lọc tự động, chỉ lấy vùng không bị nội suy | Phần tử đa dạng, độ nét cao cho mức 2 đến 4 | Thấp | Giấy phép từng vật |
| 2 | Kiểm tra sao chép (độ độc đáo) | Nhúng vector đặc trưng (CLIP hoặc DreamSim) cho mọi crop. Với mỗi họa tiết sinh ra, tìm crop gần nhất và báo khoảng cách | Chứng minh mức 3 đến 4 không chép nguyên mẫu, hỗ trợ yêu cầu 3 | Thấp | Chỉ đo, không phát hành dữ liệu |
| 3 | Thước đo chuẩn cho việc giữ họa tiết | Texture thật làm đáp án. Render bình từ góc đã biết, chạy trích xuất, so với texture bằng SSIM hoặc DreamSim | Số liệu định lượng cho yêu cầu 1. Nếu làm, thêm vào mục 8.1 | Trung bình | Phải ánh xạ UV đúng, chưa kiểm tra khả thi |
| 4 | Tìm phần tử theo từ khóa | Dán nhãn crop bằng CLIP zero-shot (hoa sen, rồng, mây). Người dùng chọn từ khóa, hệ thống lấy phần tử, lấy Canny, rồi sinh biến thể | Đa dạng không cần huấn luyện | Trung bình | Nhãn tự động có thể sai |
| 5 | Lát liền mạch từ mảng thật | Dùng mảng lớn như #15, #124 làm nguồn lát thay vì sinh bằng SD. Ghép bằng quilting (ghép mảnh theo đường cắt tối ưu) | Họa tiết nét hơn, giảm seam | Trung bình | Số mảng đủ lớn không nhiều |
| 6 | Xem hiện vật 3D trên giao diện (chi tiết ở mục 3.5) | Hiển thị `.obj` và texture bằng three.js cạnh Passport | Minh bạch nguồn: người xem thấy hiện vật gốc và phần cắt | Trung bình | File nặng, giấy phép vật được hiển thị |
| 7 | LoRA | Mục 4.4 | Phong cách men lam nhất quán | Cao | Giấy phép, dữ liệu |

Hướng 1 là nền cho hướng 2, 4, 5. Hướng 2 và 3 chỉ đo và đối chiếu nội bộ nên rủi ro giấy phép thấp hơn. Hướng 1, 4, 5, 6 đưa dữ liệu vào sản phẩm nên cần lập bảng giấy phép từng vật trước.

Điều kiện chung: ghi rõ nguồn dataset (mục 12), không khẳng định từng vật là Bát Tràng (dùng câu chuẩn ở danh mục nguồn), không commit ảnh thô (để trong `data/`, theo CLAUDE.md), không dùng ở bản công khai nếu giấy phép chưa rõ.

### 3.5. Khung xem 3D xoay bằng chuột (tùy chọn)

Mục đích: ban tổ chức xem được hiện vật gốc ngay trên giao diện và đối chiếu với thiết kế, làm rõ chuỗi "đầu vào, hoa văn, áo cuối" (yêu cầu 1) và nguồn gốc (yêu cầu 3).

**Quyền sử dụng (cập nhật 19/11/2026).** Nhóm cho biết đã được phép dùng bộ dữ liệu cho mục đích phi thương mại. Hồ sơ chưa lưu bằng chứng: cần ghi người cấp phép, ngày và hình thức xác nhận vào `docs/DANH_MUC_NGUON_HIEN_VAT.md` mục 6. Phạm vi cho phép cũng cần làm rõ trước khi đưa lên trang công khai: có gồm hiển thị và cho tải mô hình 3D, hay chỉ dùng nội bộ. Khung xem phải kèm nhãn "chỉ dùng phi thương mại" và dòng ghi công ở mục 12.

Dữ liệu của sáu hiện vật (đã đo 19/11/2026):

| Vật | Mô hình `.obj` | Số mặt | Texture gốc |
|---|---|---|---|
| #61 | 3 MB | 16 nghìn | 8 MB |
| #124 | 4 MB | 21 nghìn | 2 MB |
| #50 | 5 MB | 25 nghìn | 28 MB |
| #33 | 13 MB | 67 nghìn | 40 MB |
| #97 | 30 MB | 169 nghìn | 15 MB |
| #38 | 190 MB | 1,04 triệu | 10 MB |

Hai cách làm:

| | A. Xem 3D thật (three.js, thư viện WebGL) | B. Chuỗi ảnh xoay 360 độ |
|---|---|---|
| Cách làm | Nạp mô hình và texture, xoay và phóng to bằng chuột | Dùng ảnh render đa góc có sẵn (2 vòng camera, mỗi vòng 90 khung), kéo chuột để đổi khung |
| Tải về | Phải giảm lưới và nén texture | Khoảng 36 khung mỗi vật, nén còn khoảng 1 MB |
| Trải nghiệm | Xoay tự do, nhìn rõ họa tiết | Chỉ xoay quanh trục, ảnh 512 px |
| Công sức | Trung bình | Thấp |

Các bước nếu làm cách A (chưa làm):

1. Giảm số mặt của #33, #97, #38 xuống khoảng 20 đến 50 nghìn. Công cụ giảm lưới và chuyển sang định dạng glTF (định dạng 3D gọn cho web) chưa cài trong môi trường, chất lượng sau giảm chưa kiểm chứng.
2. Nén texture về JPEG khoảng 2048 px (vài trăm KB đến 1 MB).
3. Viết khung xem trên trang tĩnh `web_ui/` bằng three.js, điều khiển xoay bằng chuột và cảm ứng, đặt cạnh ảnh thiết kế.
4. Kiểm thử tải trang trên điện thoại. Mục tiêu đề xuất: mỗi vật dưới 5 MB, tải trong vài giây trên mạng thường (chưa có cơ sở thực nghiệm).

Thứ tự đề xuất: làm cách B trước vì rủi ro giấy phép thấp hơn và ít công sức. Cách A chỉ cho các vật nhẹ (#61, #124, #50) sau khi làm rõ phạm vi giấy phép. Bỏ #38 hoặc giảm lưới rất mạnh.

## 4. Giai đoạn 1: vẽ lại họa tiết bằng ControlNet (mọi mức)

### 4.1. Giữ cơ chế hiện tại

**Nguồn ảnh nét (cập nhật 19/11/2026).** Tham số `source` của `generate_design_set` chọn ảnh nạp cho ControlNet, thiếu thì tự quay về bậc thấp hơn:

- `render` (mặc định): ảnh hiện vật trong `data/heritage/`. Với sáu vật LR3D đây là ảnh render cả bình, đúng luồng hồ sơ gốc (đầu vào là ảnh bình).
- `panel`: mảng texture phẳng trong `data/heritage/panels/`.
- `elements`: mỗi biến thể một phần tử trong kho `data/elements/`.

Ba nguồn này là ba nhánh của thí nghiệm E1 (mục 8.3). Kết quả xem bằng mắt trên sáu vật: chất lượng cùng nhóm, ảnh render đôi khi để lọt cấu trúc dải của bình vào họa tiết (rõ ở mức 1), mảng phẳng thì không. Chưa có số đo M4, chưa kết luận nguồn nào tốt hơn.

**Lỗi đã sửa khi dùng ảnh render (rà soát 19/11).** Ảnh nền xám đi qua `prepare` bị hai lỗi từ trước: (1) viền `letterbox` luôn trắng nên màu nền ước từ viền sai, cả nền xám bị tính là vật, đường bao bình không bị loại và bảng màu lệch về xám; (2) men trắng của bình lệch màu nền chỉ khoảng 20, mặt nạ bị thủng, mất họa tiết ở giữa thân. Đã sửa: viền chèn theo màu nền, lấp lỗ mặt nạ không nối với mép khung, ngưỡng tách nền thích ứng (26 cho nền trắng, 10 cho nền xám). Có 9 kiểm thử mới, đã kiểm bằng cách giả lập hành vi cũ thì các kiểm thử thất bại. Thí nghiệm "render so với mảng" làm trước bản sửa này không còn dùng được.

ControlNet là mạng phụ nhận điều kiện hình ảnh để điều khiển Stable Diffusion. Hệ thống hiện dùng điều kiện Canny (ảnh đường nét) với bốn mức trọng số cố định: 0,85, 0,65, 0,45, 0,25 cho các mức sáng tạo. Giữ nguyên bốn mức này để so sánh có kiểm soát.

Áp dụng cho cả bốn mức, kể cả mức 1 (trọng số 0,85, giữ bảng màu gốc, vẫn vẽ lại nhưng bám sát nhất). Thay đổi chính: ảnh Canny lấy từ **phần tử trong kho** (mục 3), không lấy từ cả hiện vật. Lý do: hệ thống hiện thu cả hiện vật về 512 px (`letterbox` trong `generation/controlnet.py`), nên họa tiết nhỏ có thể mất nét, ví dụ con rồng của vật #61 biến thành sọc (nguyên nhân này là nghi ngờ, kiểm chứng bằng thí nghiệm E1 ở mục 8.3). Phần tử cắt ra có thể đưa vào ở độ phân giải cao hơn nhiều so với một họa tiết nhỏ nằm trong cả hiện vật. Chỉnh `prepare` để nhận phần tử là việc cần làm, chưa có.

### 4.2. Tileable pattern (lát liền mạch)

Giữ circular padding (tính toán vòng ở biên để hai mép ảnh nối liền) cho UNet và VAE, không áp dụng cho ControlNet. Quy tắc này lấy từ kết quả hiện tại của dự án, cần giữ nguyên.

### 4.3. Lưu ý về độ chính xác

Mọi mức đều vẽ lại họa tiết, nên không đo "giữ nguyên pixel". Mức 1 đo độ trung thành: họa tiết chính phải còn nhận ra, bằng DreamSim và SIFT (M4) với ngưỡng chặt hơn mức 2 đến 4, cùng độ lệch màu (M6). Các mức sau cho phép lệch nhiều hơn, miễn là còn thuộc họ họa tiết gốc.

### 4.4. Thử nghiệm tùy chọn: LoRA, IP-Adapter, semantic map

LoRA (Low-Rank Adaptation) là cách huấn luyện thêm một lớp nhỏ lên mô hình có sẵn để học một phong cách, nhẹ hơn huấn luyện toàn mô hình. IP-Adapter là mô-đun cho mô hình nhận thêm ảnh tham chiếu. Semantic map là bản đồ phân vùng theo loại họa tiết.

Không đưa vào luồng chính vì:

- LoRA học phong cách chung, không đảm bảo giữ đúng một họa tiết cụ thể, trong khi ưu tiên của dự án là giữ đúng.
- Dữ liệu LR3D-CULT2 có khoảng 12 đến 15 vật lam trắng sạch nhưng chưa rõ xuất xứ và giấy phép từng vật (mục 2.2).
- IP-Adapter thường mất chi tiết nhỏ.
- Mỗi thành phần thêm vào cần ablation đầy đủ (so sánh từng thành phần một), tốn thời gian chạy.

**Điều kiện bật lại:** có kho phần tử sạch với giấy phép rõ, còn thời gian sau khi xong các việc bắt buộc, và kết quả thắng rõ trong chấm mù ở mức 2 đến 3. Cách kiểm chứng gọn: cắt tự động khoảng 100 đến 200 phần tử, huấn luyện LoRA rank 8 khoảng 1 đến 2 giờ trên RTX 4060, rồi chạy cùng 5 seed có và không LoRA.

## 5. Tileable nâng cao (chuyển sang hướng phát triển)

Noise rolling (dịch vòng nhiễu để các mép nối liền ngay khi sinh), boundary inpainting (vẽ lại vùng đường nối) và Tiled Diffusion (ghép ô khi sinh ảnh lớn): chưa có bằng chứng seam là điểm nghẽn chính so với độ chân thực. Chỉ làm khi đo seam (mục 8.2) cho thấy vượt ngưỡng.

## 6. Giai đoạn 2: đưa họa tiết lên áo dài

### 6.1. Nền áo

- **Hướng chính nếu có ảnh thật** (câu hỏi 1 ở mục 0): ảnh áo dài trơn nhóm tự chụp, độ phân giải cao (thân áo rộng hàng trăm pixel), có đồng ý người mẫu, giấy phép sạch. Ghi nguồn vào Passport.
- **Dự phòng:** ảnh áo AI 1024 px sinh bằng hàm `make_template` trong `generation/garment.py`. Đã sinh được trong khoảng 23 giây, VRAM đỉnh 7,1 GB, nhưng **chưa kiểm tra chất lượng bằng mắt**. Cần xem trước khi dựa vào.

### 6.2. Ghép theo vật lý, tất định

1. Tách vùng áo bằng SAM, lưu mask một lần.
2. Ước lượng độ sâu hoặc nếp vải để uốn họa tiết theo thân áo (mô hình ước lượng độ sâu sẽ chọn sau khi thử).
3. Nhân đổ bóng lấy từ độ sáng của vải, giữ lại phần phản chiếu của lụa.
4. Khớp cân bằng trắng và độ nét với ảnh nền.

Việc UV mapping đầy đủ và material map kiểu ControlMat chuyển sang hướng phát triển. ControlMat dùng để chụp vật liệu, không phù hợp để ghép họa tiết, và bản "nhẹ" chưa được định nghĩa rõ.

### 6.3. Thử nghiệm tùy chọn: LoRA dáng áo dài từ VietFashion

Mục tiêu: sinh áo dài trơn đúng dáng mà không cần áo mẫu có sẵn, thay cho ảnh nền sinh bằng `make_template` (mục 6.1). Chỉ làm khi xin được quyền dùng dataset (câu hỏi 6 ở mục 0) và còn thời gian sau các việc bắt buộc.

Vì sao có thể giúp: Stable Diffusion 1.5 gốc hay sinh sai áo dài (lẫn váy, đầm), vì ảnh áo dài ít trong dữ liệu học của nó. LoRA là cách huấn luyện thêm một lớp nhỏ để mô hình học một khái niệm mới. Dataset cho ảnh áo dài kèm câu mô tả có thuộc tính dáng áo, nên dạy được chữ "áo dài" gắn với hình đúng. Cặp phác thảo và ảnh cũng thể hiện dáng, vì ảnh được sinh bám theo phác thảo.

Các bước:

1. **Kiểm chứng mẫu (khoảng nửa ngày):** tải khoảng 100 ảnh, xem bằng mắt: tỉ lệ đúng dáng áo dài, độ phân giải, có người mặc không, có áo trơn không. Chỉ huấn luyện nếu từ 70% ảnh đúng dáng trở lên. Ngưỡng này là đề xuất, chưa có cơ sở thực nghiệm.
2. **Lọc tự động:** giữ ảnh áo dài toàn thân, loại ảnh lỗi bằng điểm CLIP với câu mô tả áo dài, kiểm tra một mẫu bằng mắt, ghi số ảnh bị loại và lý do vào nhật ký.
3. **Giữ nguyên câu mô tả, gồm cả họa tiết và nền:** mô hình sẽ gắn họa tiết và nền với chữ đó, không gắn với "áo dài". Lúc sinh, viết "áo dài trơn, không họa tiết" để ra thân áo sạch cho bước ghép họa tiết gốm.
4. **Huấn luyện LoRA:** SD 1.5, 512 px, rank 8, khoảng 1 đến 2 giờ trên RTX 4060. Thường vừa 8 GB khi bật gradient checkpointing và fp16, chưa thử trên máy của nhóm.
5. **Dùng lúc sinh:** thay ảnh nền AI. Muốn ép dáng theo ý, kết hợp ControlNet scribble (bản có sẵn, không cần huấn luyện) với nét phác của nhóm.
6. **So sánh có kiểm soát:** thêm thí nghiệm E6 ở mục 8.3. Nền áo có và không LoRA, 5 seed, đo M1 (giữ dáng áo) và chấm mù. Giữ LoRA nếu thắng rõ ở cả hai, nếu không thì bỏ.

Giới hạn:

- Ảnh gốc do AI sinh nên lỗi của SANA (tay, vải, tà áo) có thể lọt vào dữ liệu học. Bước lọc là bắt buộc.
- LoRA tăng xác suất đúng dáng, không bảo đảm mỗi lần sinh đều đúng. Vẫn dùng M1 và quy tắc thử lại ở mục 8.
- Không giúp phần họa tiết gốm. Dữ liệu chỉ dạy dáng áo.
- Không huấn luyện ControlNet phác thảo riêng, quá nặng với 8 GB VRAM trong thời hạn này.
- Ghi nguồn dataset và phiên bản LoRA vào Passport (trường `base_garment_source`). Không phát hành trọng số LoRA khi chưa có quyền.

## 7. Polish nhẹ có mặt nạ

Hiện tại `polish()` trong `generation/garment.py` chạy img2img (sinh ảnh từ ảnh có sẵn, thêm nhiễu rồi khử nhiễu) trên toàn ảnh với strength 0,40, không có mask.

Phiên bản mới:

1. Chạy img2img với strength thấp hơn 0,40 (thử khoảng 0,25 đến 0,35, chọn bằng M4) để hòa vải và ánh sáng mà ít vẽ lại họa tiết lần thứ hai.
2. **Dán lại pixel gốc ở vùng ngoài áo** (mặt nạ áo, M2): polish không được đổi nền, tóc, tay.

Họa tiết trên áo vẫn được phép biến đổi nhẹ vì mọi mức đều vẽ lại. Không dán lại pixel họa tiết, trừ bản mốc đối chiếu ở mục 3.3.

Vì sao giảm strength và dùng mặt nạ: polish toàn ảnh ở 0,40 vẽ lại họa tiết một lần nữa, là một nguyên nhân nghi ngờ làm mất chi tiết. Kiểm chứng bằng thí nghiệm E2 ở mục 8.3.

Differential Diffusion (cho mỗi pixel một cường độ riêng bằng bản đồ strength) là hướng nâng cấp. Paper gốc chạy trên Stable Diffusion 2.1. Bản cho SD 1.5 chưa xác minh, cần thử riêng. Cách đơn giản và đủ dùng trước mắt: img2img rồi dán lại.

Chuyển sang hướng phát triển: RePaint (inpainting có lấy mẫu lại) và virtual try-on kiểu Texture-Preserving Diffusion (TPD). TPD huấn luyện trên dữ liệu thử đồ người (VITON-HD), khác miền ảnh gốm và có hạn chế giấy phép phi thương mại.

## 8. Lớp đánh giá

Không dùng điểm CLIP làm kết luận duy nhất về đẹp hay đúng văn hóa.

### 8.1. Chỉ số tự động (xác định rõ cách đo)

| Mã | Tên | Cách đo | Ngưỡng đề xuất |
|---|---|---|---|
| M1 | Giữ dáng áo | IoU (tỉ lệ phần giao trên phần hợp) giữa mask áo trước và sau polish | 0,95 trở lên |
| M2 | Tràn ngoài áo | Tỉ lệ pixel ngoài mask áo bị đổi giá trị | 0,5% trở xuống |
| M3 | Giữ nguyên pixel (chỉ cho bản dán nguyên ở mục 3.3, nếu làm) | Sai khác trung bình trong vùng họa tiết giữa ảnh cuối và phần tử đã cắt | Bằng 0 |
| M4 | Độ trung thành họa tiết (mọi mức, chỉ số chính cho "độ giữ họa tiết") | DreamSim (khoảng cách cảm thụ giữa hai ảnh, thấp là giống) giữa vùng họa tiết của ảnh cuối và phần tử gốc; bổ sung số điểm khớp SIFT (điểm đặc trưng cục bộ) | Đặt sau khi đo phân bố trên 6 mảng LR3D; mức 1 đặt chặt hơn mức 2 đến 4 |
| M5 | Liền mạch (seam) | Tỉ lệ độ lệch màu và độ sáng ở đường nối so với trong ô, 1,0 là liền hoàn toàn | 1,3 trở xuống |
| M6 | Lệch màu | Khoảng cách màu LAB (ΔE) giữa bảng màu phần tử và ảnh cuối | Đặt sau khi đo |
| M7 | Giữ cấu trúc áo (DINO) | DINO-ViT là mô hình thị giác học không cần nhãn, cho vector đặc trưng theo từng mảnh ảnh. Lấy vector khóa (key) của một lớp attention (bài báo dùng lớp thứ l, lớp cụ thể chọn sau khi thử) ở từng mảnh, tính khoảng cách giữa ảnh áo nền và ảnh áo hoàn chỉnh trên vùng ngoài họa tiết. Thấp là cấu trúc giữ tốt. Phương án thay: chạy Mask R-CNN (mô hình phát hiện vật) lấy mặt nạ áo rồi tính recall và precision so với áo nền | Đặt sau khi đo |

Tất cả ngưỡng là đề xuất ban đầu, được hiệu chỉnh sau khi đo thực tế rồi ghi giá trị cuối vào file cấu hình. M3 chỉ áp dụng cho bản dán nguyên (nếu làm). M7 chỉ dùng để đo, không dùng để dẫn hướng khi sinh ảnh (dẫn hướng bằng DINO tốn thời gian và chưa kiểm chứng với Stable Diffusion 1.5). Ý tưởng M7 lấy từ bài DiffFashion (mục 15), bổ sung cho M1 vì M1 chỉ so đường viền ngoài, còn M7 so cả cấu trúc bên trong thân áo.

### 8.2. Tiêu chí loại và thử lại

- Vi phạm M1, M2 hoặc M4 (họa tiết không còn nhận ra, vượt ngưỡng của mức tương ứng): thử lại với seed kế tiếp, tối đa 3 lần.
- Sau 3 lần vẫn hỏng: loại, lưu ảnh kèm lý do vào thư mục riêng (đề xuất `outputs/rejected/`) để làm ví dụ "bị loại" cho minh chứng.
- Mẫu sửa được (ví dụ chỉnh tham số mask rồi đạt): lưu cả bản trước và sau, ghi vào nhật ký.
- Toàn bộ nhật ký lưu cùng Design Passport.

### 8.3. So sánh có kiểm soát nhiều seed

Giữ cố định prompt, bảng màu, bố cục, điều kiện đầu vào, và **chỉ đổi một thành phần mỗi thí nghiệm**. Chạy 5 seed (42 đến 46) trên 6 mảng LR3D (`LR3D_33`, `LR3D_61`, `LR3D_50`, `LR3D_38`, `LR3D_97`, `LR3D_124`). Cả 6 mảng có cạnh dài 2048 px (cắt từ texture 4096 đến 8192 px). `LR3D_97` có nét lam thưa nên ít chi tiết nhất, `LR3D_38` còn dính một đĩa nhãn kiểm kê ở đáy.

| Thí nghiệm | Thành phần thay đổi | Các cấu hình |
|---|---|---|
| E1 | Nguồn ảnh nét cho ControlNet | Ba nhánh: ảnh render cả bình (mặc định, `source="render"`), mảng phẳng (`panel`), phần tử cắt (`elements`). Cùng prompt, seed, mức, chỉ khác ảnh nạp. Lưu ý: nhánh phần tử dùng mỗi biến thể một phần tử khác nhau nên chưa đối chứng chặt, cần thêm chế độ cố định một phần tử. Thêm mốc dán nguyên nếu làm mục 3.3 |
| E2 | Bước polish | Không polish, polish toàn ảnh 0,40 (hiện tại), polish nhẹ 0,25 đến 0,35 có mặt nạ áo |
| E3 | Nền áo | Nền AI 512 hiện tại, so với nền độ phân giải cao |
| E4 | Trọng số ControlNet | Bốn mức 0,85, 0,65, 0,45, 0,25 |
| E5 (tùy chọn) | LoRA | Có và không (mục 4.4) |
| E6 (tùy chọn) | LoRA dáng áo dài | Nền áo có và không LoRA huấn luyện từ VietFashion (mục 6.3) |

Sản phẩm: file CSV cấu hình mỗi lần chạy (cấu hình, seed, mã băm ảnh), bảng điểm người chấm, và thống kê gồm trung bình, độ lệch chuẩn, nhỏ nhất và lớn nhất.

### 8.4. Chấm mù và thẩm định

**Chấm mù nội bộ:** ít nhất 3 người, xáo thứ tự ảnh, ẩn tên cấu hình. Thang 1 đến 5 cho sáu tiêu chí: giữ đúng motif, giữ màu, đúng dáng áo dài, hòa vào nếp vải, thẩm mỹ, phù hợp văn hóa. Tính độ đồng thuận giữa người chấm bằng hệ số Krippendorff alpha (số đo mức nhất quán giữa nhiều người chấm). Ghi lý do loại.

Đối chiếu với bài DiffFashion: họ khảo sát 30 người, thang 0 đến 100, ba mặt là độ chân thực, giữ cấu trúc và giống vẻ ngoài. Sáu tiêu chí ở trên đã phủ ba mặt này: chân thực gồm "hòa vào nếp vải" và "thẩm mỹ", cấu trúc là "đúng dáng áo dài", vẻ ngoài gồm "giữ đúng motif" và "giữ màu". Không đổi thang. Khi báo cáo, nêu rõ số người chấm và số mẫu, vì bài đó cũng chỉ dùng 30 cặp ảnh nên kết luận thống kê yếu.

**Phiếu thẩm định của người ngoài nhóm:** mỗi mẫu gồm ảnh đầu vào, ảnh phần tử, ảnh áo cuối, thang điểm cùng sáu tiêu chí, một ô "chấp nhận, cần sửa, loại" và ô lý do. Cần ít nhất một người am hiểu di sản và một người am hiểu thiết kế nếu có (câu hỏi 3 ở mục 0). Nếu không có, ghi rõ trong tài liệu nộp rằng chưa có thẩm định chuyên gia và phiếu do nhóm điền, không trình bày như đã được chuyên gia xác nhận.

## 9. Design Passport, nhãn AI và nhật ký

Bổ sung các trường:

```text
source_artifact_id         mã hiện vật nguồn (6 hiện vật hoặc nguồn bổ sung)
source_url                 địa chỉ ảnh gốc
source_license             giấy phép, hoặc "unverified"
source_license_evidence    bằng chứng (thư xin phép, trang giấy phép)
element_id, element_version  phần tử trong kho
preprocessing_version      phiên bản trải trụ và cắt phần tử
segmentation_method        alpha hoặc Grounded SAM
base_garment_source        ảnh thật nhóm tự chụp hoặc ảnh AI, kèm phiên bản
conditioning_level         mức 1 đến 4
controlnet_scale           trọng số ControlNet (mức 2 đến 4)
polish_method              img2img + dán lại
lock_region_version        phiên bản mask khóa
metric_version             phiên bản bộ chỉ số
ai_assisted_label          nhãn "nội dung có hỗ trợ AI"
```

Passport phải ghi rõ:

- Bước nào do AI sinh (ControlNet, polish), bước nào là ghép tất định (trích xuất, ghép, dán lại).
- Mọi bước chỉnh sửa do con người, kèm người làm, thời điểm, lý do (nhật ký chỉnh sửa). Nếu không có chỉnh tay thì ghi "không có".
- Ảnh đầu ra hiển thị cho người dùng phải có nhãn "có hỗ trợ AI".
- Với ảnh gốm: giấy phép của từng hiện vật và trạng thái xác minh.
- Với LR3D-CULT2 nếu dùng: ghi attribution (mục 12).

## 10. Lịch triển khai 18 đến 25/11

Vai trò gợi ý, nhóm tự gán người: **AI** (mô hình và pipeline), **DEV** (API, giao diện, deploy), **BA** (dữ liệu, tài liệu, đánh giá).

| Ngày | AI | DEV | BA |
|---|---|---|---|
| 18/11 (đã làm) | Module cắt phần tử từ texture phẳng, thay 6 hiện vật bằng 6 mảng LR3D, sinh 24 thiết kế | Dựng khung deploy (mục 11) | Chốt các câu hỏi mục 0, sửa mâu thuẫn `items.json` và `metadata.json` |
| 19/11 | Cho `controlnet.prepare` nhận phần tử cắt, chạy thử E1 trên `LR3D_61`, xem bằng mắt | Chuẩn bị hoặc chụp ảnh nền áo | Gửi xin phép nguồn ảnh, soạn bảng nguồn và giấy phép, gửi email hỏi nhóm tác giả LR3D-CULT2 và VietFashion |
| 20/11 | Nền áo cao phân giải, polish nhẹ có mặt nạ, thử E2 và E3 trên một mảng | Hiển thị Passport và nhãn AI | Soạn phiếu thẩm định và phiếu chấm mù |
| 21/11 | Viết chỉ số M1, M2, M4, M6, M7, quy tắc thử lại, kiểm thử bằng pytest | Nối quy tắc loại vào API | Tìm người thẩm định |
| 22/11 | Chạy 5 seed trên 6 hiện vật theo E1 đến E4 | Triển khai bản đầu của đường dẫn thử | Chuẩn bị bảng ghi kết quả |
| 23/11 | Lưu ví dụ bị loại và sửa | Kiểm thử tải | Gửi phiếu, tổ chức chấm mù |
| 24/11 | Sửa lỗi theo kết quả | Đóng băng bản nộp | Thống kê, tổng hợp bộ minh chứng |
| 25/11 | Dự phòng | Kiểm tra đường dẫn hoạt động | Nộp |

**Điểm quyết định cuối ngày 20/11:** nếu ảnh nét từ phần tử làm họa tiết mức 1 nhận ra rõ hơn bản hiện tại trên ít nhất 3 trong 6 mảng (xem bằng mắt và đo M4), giữ hướng này cho cả tuần. Nếu không, làm thêm bản dán nguyên (mục 3.3) để biết lỗi nằm ở bước vẽ lại hay ở nguồn ảnh, rồi chỉnh tiếp, và ghi rõ giới hạn trong báo cáo.

**Quy trình theo CLAUDE.md:** sau mỗi module lớn, chạy pytest, một subagent chỉ đọc kiểm tra logic, một subagent khác tính trước kết quả mong đợi chỉ từ đặc tả và dữ liệu đầu vào rồi so với kết quả chạy thật, và tự rà soát lại trước khi báo xong. Ngoài ra bắt buộc xem ảnh bằng mắt cho từng hiện vật, vì kiểm thử theo đặc tả không bắt được lỗi hình ảnh.

## 11. Triển khai đường dẫn cho ban tổ chức thử

Mục tiêu: ban tổ chức bấm vào đường dẫn và tạo được áo dài, không cần cài đặt.

- **Lớp giao diện:** `web_ui` là trang tĩnh, đặt trên dịch vụ lưu trang tĩnh (ví dụ Vercel).
- **Lớp sinh ảnh:** API trong `api/main.py` chạy trên máy có GPU của nhóm, mở ra ngoài bằng một tunnel (đường hầm HTTPS, ví dụ Cloudflare Tunnel).
- **Hạn chế:** khi máy tắt hoặc mất mạng thì không sinh ảnh được. Vì vậy cần thêm chế độ xem lại mẫu đã sinh sẵn (thư viện ảnh tĩnh cùng Passport) để ban tổ chức vẫn xem được kết quả.
- Việc cần xác nhận bằng cách chạy thử: giới hạn thời gian của tunnel, một người dùng một lúc do GPU 8 GB, và ghi chú rõ thời gian chờ mỗi ảnh.

## 12. Attribution

LR3D-CULT2, nếu có dùng cho thử nghiệm:

```text
Nguyen, Le Huu Bao; Nguyen, Van Nhat Nam; Nguyen, The Trong Nha; BUI, Cao Vu.
"LR3D-CULT2: Vietnamese Ceramic Cultural Artifacts." Mendeley Data, Version 1.
DOI: 10.17632/jr23fnrvx2.1. Giấy phép công bố trên trang dataset: CC BY 4.0.
Một phần dữ liệu có nguồn Sketchfab theo giấy phép học thuật. Chưa kiểm tra giấy phép từng vật.
```

Chỉ ghi "đã lọc, cắt, dùng để huấn luyện" khi thực sự đã làm. Hiện tại dataset chỉ được quét để đánh giá, chưa dùng để huấn luyện.

## 13. Những điều không làm lúc này

- Không đưa LoRA huấn luyện từ LR3D-CULT2, hoặc phần tử cắt từ dataset này, vào bản công khai khi chưa có giấy phép và xuất xứ từng vật.
- Không dùng VietFashion để huấn luyện bản công khai khi chưa hỏi nhóm tác giả.
- Không khẳng định từng vật là Bát Tràng, không gắn nhãn bảo tàng và niên hiệu, khi chưa có nguồn kiểm chứng. Câu được phép dùng nằm ở `docs/DANH_MUC_NGUON_HIEN_VAT.md` mục 4.
- Không polish toàn ảnh với strength cao.
- Không dùng điểm CLIP làm kết luận duy nhất về đúng văn hóa.
- Không bật đồng thời nhiều điều kiện mà chưa có ablation.
- Không dùng người thật làm mẫu khi chưa có đồng ý.
- Không trình bày phiếu do nhóm điền như thẩm định chuyên gia.

## 14. Hướng phát triển (chưa làm trong đợt này)

LoRA và IP-Adapter (mục 4.4), semantic motif map, noise rolling và boundary inpainting, Tiled Diffusion, UV mapping đầy đủ, material map kiểu ControlMat, adapter kiểu DANet với bộ phân loại họa tiết, RePaint, virtual try-on đầy đủ (TPD).

Đã xem xét và không dùng làm hướng chính: DiffFashion (chuyển vẻ ngoài từ ảnh tham chiếu lên quần áo bằng mô hình khuếch tán). Lý do: nó cố ý diễn giải lại họa tiết theo ngữ nghĩa (điểm giống vẻ ngoài chỉ 52,9 trên 100 trong khảo sát của chính họ), trái với mục tiêu giữ nguyên họa tiết. Ngoài ra dùng mô hình ImageNet ảnh nhỏ, 2 phút mỗi ảnh trên RTX 3090, chỉ thử trên 30 cặp ảnh túi xách và sinh vật biển.

## 15. Nguồn paper tham khảo

Các paper nằm trong thư mục `docs/paper tham khảo/`. Kỹ thuật chính dùng trong bản này:

- `Grounded SAM Assembling Open-World Models for Diverse Visual Tasks.pdf`: phát hiện và phân đoạn theo từ khóa (mục 3).
- `Unwrapping Low-rank Textures on Generalized Cylindrical Surfaces.pdf`: trải phẳng bề mặt cong (mục 3).
- `Differential Diffusion Giving Each Pixel Its Strength.pdf`: cường độ theo từng pixel (mục 7, hướng nâng cấp).
- `An Intelligent Generation Method for Kizil Rhombic Mural Patterns ... .pdf`: làm sạch dữ liệu, chỉnh phối cảnh, bám cấu trúc.
- `WISE World Knowledge-Informed Semantic Evaluation for Text-to-Image.pdf` và `Toward Verifiable and Reproducible Human Evaluation for Text-to-Image Generationpdf.pdf`: đánh giá và chấm người có kiểm soát (mục 8).
- `Multimodal Conditioning of Fine-Tuned Stable Diffusion XL for.pdf`, `Paper_109-Generating_New_Ulos_Motif_with_Generative_AI_Method.pdf`, `The Inheritance and Innovation of Blue Calico Culture Driven by AIGC.pdf`: mô hình hóa họa tiết văn hóa, nhắc rằng chồng nhiều điều kiện có thể làm kém đi.
- `Cao_Image_Reference-Guided_Fashion_Design_With_Structure-Aware_Transfer_by_Diffusion_Models_CVPRW_2023_paper.pdf` (DiffFashion): ý tưởng đo giữ cấu trúc bằng DINO-ViT (chỉ số M7) và thiết kế khảo sát ba mặt (mục 8). Không dùng làm phương pháp sinh, xem mục 14.
- Hướng phát triển: `Structured Pattern Expansion with Diffusion Models.pdf`, `Content-aware Tile Generation using Exterior Boundary Inpainting.pdf`, `Tiled Diffusion.pdf`, `RePaint Inpainting using Denoising Diffusion Probabilistic Models.pdf`, `ControlMat A Controlled Generative Approach to Material Capture.pdf`, `Texture-Preserving Diffusion Models for High-Fidelity Virtual Try-On.pdf`, `Advancing Traditional Dunhuang Regional Pattern Design with Diffusion Adapter Networks and Cross-Entropy.pdf`.

## 16. Thay đổi so với bản v2 ngày 18/11 buổi đầu

| Mục | Thay đổi |
|---|---|
| Mục tiêu và kết luận | Từ "LoRA, polish, 5 seed" sang "trích xuất tất định, nền áo cao phân giải, minh chứng ba yêu cầu" |
| Khung xem 3D và quyền phi thương mại | Mới: mục 3.5, hai cách làm, số liệu dung lượng sáu vật. Nhóm cho biết được phép dùng phi thương mại, chưa có bằng chứng trong hồ sơ |
| Đầu vào mặc định (quyết định 19/11) | Ảnh hiện vật mặc định là ảnh render cả bình (đúng luồng hồ sơ gốc), mảng phẳng và phần tử là nhánh so sánh E1. Sửa lỗi nền xám trong `controlnet.prepare`. Mục 2.1, 4.1, 8.3 |
| Hướng mức 1 (quyết định 19/11) | Bỏ "mức 1 giữ nguyên pixel bằng phương pháp tất định" làm đường chính. Mọi mức vẽ lại bằng ControlNet, mức 1 là mức trung thành đo bằng M4. Dán nguyên phần tử thành mốc đối chiếu tùy chọn (mục 3.3). Sửa mục 1, 3, 4, 7, 8.1 đến 8.3 và lịch ở mục 10 |
| LR3D-CULT2 | Từ dataset chính huấn luyện LoRA xuống nguồn tham khảo, kèm kết quả quét 120 vật thể và đính chính về tiền tố `sketchfab_collection` |
| VietFashion | Mới: mục 2.4, ghi nhận giấy phép chưa xác minh trên trang chính thức |
| LoRA dáng áo dài từ VietFashion | Mới: mục 6.3, thử nghiệm tùy chọn, kèm bước kiểm chứng mẫu và thí nghiệm E6 |
| DiffFashion (CVPRW 2023) | Mới: chỉ số M7 ở mục 8.1, ghi chú đối chiếu khảo sát ở mục 8.4, ghi nhận "không dùng làm hướng chính" ở mục 14, thêm vào mục 15 |
| Cách dùng LR3D-CULT2 | Mới: mục 3.4, bảy hướng tận dụng dữ liệu |
| Bộ dữ liệu `bat_trang_patterns/` cho LoRA | Bỏ, thay bằng kho phần tử |
| Segmentation | Bỏ "kiểm tra thủ công", thay bằng kiểm tra tự động và nhật ký |
| Phối cảnh | Thay bằng trải trụ từ silhouette |
| Giai đoạn 1 | Bản 18/11 tách hai đường (mức 1 tất định, mức 2 đến 4 ControlNet). Bản 19/11 bỏ cách tách này: mọi mức dùng ControlNet |
| LoRA | Xuống thử nghiệm tùy chọn với điều kiện bật lại |
| Noise rolling, boundary inpainting, UV, ControlMat | Xuống hướng phát triển |
| Polish | Thêm dán lại pixel gốc ở vùng khóa |
| Đánh giá | Định nghĩa chỉ số và ngưỡng, thêm tiêu chí loại, phiếu thẩm định, ví dụ bị loại |
| Nguồn 6 hiện vật | Mới: bảng nguồn và các mâu thuẫn cần sửa |
| Passport | Thêm nhãn AI, nhật ký chỉnh sửa, giấy phép từng nguồn |
| Lịch và deploy | Mới: lịch 18 đến 25/11 và phương án đường dẫn thử |
| Định dạng | Bỏ gạch dài, thêm giải thích thuật ngữ ở lần nhắc đầu |
