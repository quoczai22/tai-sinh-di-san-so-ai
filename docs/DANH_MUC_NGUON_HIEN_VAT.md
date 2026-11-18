# Danh mục nguồn và quyền sử dụng sáu hiện vật (bản 19/11/2026)

Tài liệu này trả lời yêu cầu 3 của ban tổ chức: nguồn và quyền sử dụng sáu hiện vật, cách ghi công, lịch sử các bước chỉnh sửa do người làm, và nhãn nội dung có hỗ trợ AI.

## 1. Thay đổi so với hồ sơ gốc

Hồ sơ gốc dùng sáu ảnh chụp bình gốm lấy từ trang bán hàng, giấy phép chưa xác minh, một số ảnh chưa điền URL trong dữ liệu chạy. Ngày 19/11/2026 nhóm quyết định thay bằng sáu mảng texture phẳng cắt từ bộ dữ liệu LR3D-CULT2, vì bộ dữ liệu này có DOI và giấy phép công bố, nguồn kiểm chứng được hơn.

Pipeline sinh ảnh (hai giai đoạn) giữ nguyên. Chỉ thay dữ liệu đầu vào và nhãn nguồn. Các điểm khác biệt khi đọc hồ sơ:

- Ảnh hiện vật mặc định là ảnh render cả bình từ mô hình 3D (camera 1, khung 1), gần với ảnh chụp bình của hồ sơ gốc. Mảng texture phẳng của cùng vật là đầu vào thay thế, dùng để so sánh.
- Sáu ảnh cũ vẫn còn trong thư mục `data/heritage/` và trong lịch sử git để đối chiếu. Bản dữ liệu cũ nằm ở commit trước `3a849df`.

Sáu hiện vật cũ, giữ lại để minh bạch:

| Mã cũ | Tên | Nguồn (trang bán hàng) | Trạng thái |
|---|---|---|---|
| `BT_Hac_XP` | Bình gốm dáng Tỏi hút lộc | fullhome-decor.com | Giấy phép chưa xác minh |
| `HSBT_XP-300x300` | Bình gốm hoa sen mực đen | fullhome-decor.com | Giấy phép chưa xác minh |
| `BHV_UU_XP1-600x600` | Bình gốm chim công phong thủy | fullhome-decor.com | Giấy phép chưa xác minh |
| `MB_2C_XP_31` | Bình gốm thuyền buồm | fullhome-decor.com | Giấy phép chưa xác minh |
| `BT010_2` | Bình gốm cúc vạn thọ | battrangceramica.com.vn | Giấy phép chưa xác minh |
| `binh-hoa-su-trang-ap-noi-hoa-sen-dat-vang-24k-...` | Bình hoa sứ trắng sen dát vàng 24k | xuonggomsuviet.vn | Giấy phép chưa xác minh |

URL đầy đủ của sáu ảnh cũ nằm trong lịch sử của file `data/metadata.json`.

## 2. Bộ dữ liệu nguồn

- **Tên:** LR3D-CULT2, Vietnamese Ceramic Cultural Artifacts (mô hình 3D, ảnh render đa góc và texture).
- **Tác giả:** Nguyen Le Huu Bao, Nguyen Van Nhat Nam, Nguyen The Trong Nha, Bui Cao Vu (theo trang dataset; đơn vị ghi trên trang: FPT University, Hà Nội).
- **Trang dataset:** <https://data.mendeley.com/datasets/jr23fnrvx2/1>, DOI `10.17632/jr23fnrvx2.1`, công bố ngày 2/3/2026.
- **Giấy phép công bố của bộ dữ liệu:** CC BY 4.0, theo trang dataset.
- **Xuất xứ theo mô tả của bộ dữ liệu:** một phần mô hình được quét quang trắc tại các làng gốm Bát Tràng và Thanh Hà, một phần lấy từ Sketchfab theo giấy phép dùng cho học thuật. Trang không chỉ ra vật nào thuộc nguồn nào, và metadata từng vật chỉ có tên, tâm vật thể, vị trí camera.

## 3. Sáu hiện vật đang dùng

| Mã trong hệ thống | Vật trong dataset | File texture gốc | Cách cắt mảng phẳng | Kích thước mảng phẳng | Trạng thái |
|---|---|---|---|---|---|
| `LR3D_33` | `ceramic_vases_33` | `ceramic_vases_33.png` | Đảo UV nhiều nét mực lam nhất, khung [4000, 3556, 8185, 8151], thu 0,446 lần | 1865×2048 | Giấy phép và xuất xứ từng vật chưa xác minh |
| `LR3D_61` | `ceramic_vases_61` | `ceramic_vases_61.png` | Khung [38, 2274, 3862, 4057], thu 0,536 lần | 2048×955 | Như trên |
| `LR3D_50` | `ceramic_vases_50` | `ceramic_vases_50.png` | Khung [96, 2492, 4761, 8123], thu 0,364 lần | 1697×2048 | Như trên |
| `LR3D_38` | `ceramic_vases_38` | `ceramic_vases_38.png` | Khung [6, 6, 2107, 3253], thu 0,631 lần. Còn dính một đĩa nhỏ có nhãn kiểm kê ở đáy | 1325×2048 | Như trên |
| `LR3D_97` | `ceramic_vases_97` | `ceramic_vases_97.png` | Khung [3108, 48, 4074, 2252], thu 0,929 lần. Nét lam thưa | 898×2048 | Như trên |
| `LR3D_124` | `ceramic_vases_124` | `ceramic_vases_124.jpeg` | Khung [1182, 314, 2276, 2806], thu 0,822 lần | 899×2048 | Như trên |

**Ảnh hiện vật mặc định** của mỗi mã là ảnh render cả bình (512×512, nền xám) lấy từ ảnh render đa góc của dataset: camera 1, khung 1, góc cố định cho cả sáu vật, không chọn tay. File ở `data/heritage/LR3D_<số>.png`, tên file gốc trong dataset ghi ở trường `render_source` của `lr3d_crops.json`. Mảng phẳng ở `data/heritage/panels/LR3D_<số>.png`.

Thông số đầy đủ (phương pháp mặt nạ, độ phủ UV, số đảo tìm được) ở `data/heritage/lr3d_crops.json`. Kho phần tử cắt từ các mảng này ở `data/elements/` (không commit), mỗi phần tử có bản ghi trong `index.json` kèm mã vật nguồn, DOI và trạng thái giấy phép.

## 4. Cách ghi công

Khi hiển thị hoặc công bố, ghi:

> Hoa văn lấy từ bộ dữ liệu LR3D-CULT2 (Nguyen Le Huu Bao, Nguyen Van Nhat Nam, Nguyen The Trong Nha, Bui Cao Vu), Mendeley Data, phiên bản 1, DOI 10.17632/jr23fnrvx2.1, giấy phép CC BY 4.0. Một phần dữ liệu quét tại Bát Tràng và Thanh Hà, một phần lấy từ Sketchfab; xuất xứ từng vật chưa xác định. Ảnh thiết kế do hệ thống có hỗ trợ AI tạo ra.

Nhãn hiển thị trong ứng dụng: "Gốm men lam · LR3D-CULT2 (Bát Tràng, Thanh Hà)", kèm ghi chú giấy phép ở trường `licenseNote`. Nhãn này lặp lại mô tả của bộ dữ liệu, không khẳng định từng vật là Bát Tràng.

## 5. Lịch sử các bước do người làm

| Ngày | Bước | Người làm |
|---|---|---|
| 18/11/2026 | Quét 120 vật thể, chọn bằng mắt 14 vật có mảng lam trắng sạch | Trợ lý AI đề xuất theo bảng ảnh thu nhỏ |
| 19/11/2026 | Chọn 6 vật trong 14, chọn nhãn nguồn, quyết định thay hiện vật, chọn dùng ảnh render cả bình làm đầu vào mặc định | Nhóm |
| 18 đến 19/11/2026 | Viết mô tả hiện vật (`team_description`) và mô tả cho prompt (`prompt_terms.json`) từ quan sát ảnh | Trợ lý AI, **chưa có người rà soát** (`reviewed_by_human: false`) |

Các bước sau do hệ thống làm tự động, không có chỉnh sửa tay lên ảnh: cắt mảng texture, cắt phần tử, lọc phần tử, sinh họa tiết, ghép lên áo.

## 6. Việc chưa làm

- Chưa liên hệ nhóm tác giả LR3D-CULT2 để xác nhận xuất xứ và giấy phép từng vật. Cho đến lúc đó, sáu hiện vật chỉ dùng cho thử nghiệm và trình bày, kèm nhãn chưa xác minh.
- Chưa có chuyên gia di sản hoặc thiết kế xem xét mẫu.
- Chưa tích hợp các trường nguồn này vào Design Passport của ứng dụng (xem mục 9 của `docs/HUONG_CAI_TIEN_V2.md`).
- Phần lớn nhãn nguồn trong giao diện web (tiêu đề trang, chân trang, các đoạn giới thiệu) vẫn ghi chung "Bát Tràng" ở chín chỗ, chưa đối chiếu với tuyên bố ở mục 4.
