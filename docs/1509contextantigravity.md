# BÁO CÁO TOÀN DIỆN NGỮ CẢNH HỆ THỐNG — 15/09/2026
**Mã tài liệu:** `1509contextantigravity`  
**Dự án:** Tái sinh Di sản Số AI — Áo Dài & Gốm Sứ Bát Tràng  
**Phiên bản chuẩn:** MVP v6.1 (Generate-and-Curate)  
**Tác giả ghi nhận:** Antigravity (Pair Programming Assistant)  

---

## 1. TỔNG QUAN DỰ ÁN & ĐỊNH VỊ CỐT LÕI (MVP v6.1)

### 1.1. Bản chất Dự án
- **Định vị:** Ứng dụng AI chuyển hóa hoa văn từ hiện vật gốm sứ Bát Tràng thành bộ sưu tập thiết kế trang phục **Áo dài Việt Nam** đương đại.
- **Triết lý sản phẩm:** **Generate-and-Curate** ("Một nút bấm ra trọn bộ 4 thiết kế — người dùng đóng vai trò Curator chọn tác phẩm ưng ý nhất và nhận Hộ chiếu thiết kế - Design Passport").
- **Phạm vi dữ liệu:** **6 hiện vật gốm Bát Tràng kinh điển** được tuyển chọn tại [data/heritage/items.json](file:///d:/sangtaotre/tai-sinh-di-san-so-ai/data/heritage/items.json):
  1. `BT_Hac_XP`: Bình gốm hoa lam công và sen (Chính Hòa).
  2. `HSBT_XP-300x300`: Hoa sen trên gốm thờ Bát Tràng (Vĩnh Thịnh).
  3. `BHV_UU_XP1-600x600`: Bình hoa văn chim công hoa mẫu đơn (Thế kỷ XVIII).
  4. `MB_2C_XP_31`: Thuyền buồm và sóng nước (Thế kỷ XIX).
  5. `BT010_2`: Hoa cúc dây hoa lam (Cảnh Hưng).
  6. `binh-hoa-su-trang-ap-noi-hoa-sen-dat-vang-24k-bat-trang-cao-cap-anh-dai-dien`: Bình hoa sen dát vàng 24k (Đương đại).

### 1.2. Kiến trúc Kỹ thuật Pipeline (2 Giai đoạn sinh + 1 Lớp đánh giá)
Được cố định theo Hiến pháp kỹ thuật [docs/agent.md](file:///d:/sangtaotre/tai-sinh-di-san-so-ai/docs/agent.md) và đặc tả [docs/mvp_spec.md](file:///d:/sangtaotre/tai-sinh-di-san-so-ai/docs/mvp_spec.md):
1. **Giai đoạn 1 — Sinh hoa văn phẳng (Seamless Pattern):**
   - Tách nền, Canny CHỈ trích xuất nét hoa văn (loại bỏ đường viền dáng bình).
   - Chạy SD1.5 + ControlNet Canny cục bộ với 4 mức weight nội bộ cố định: `0.85` (Nguyên bản - giữ bảng màu gốc), `0.65`, `0.45`, `0.25` (sáng tạo tự do).
   - Xuất ra file hoa văn phẳng lặp liền mạch (`_pattern.png`).
2. **Giai đoạn 2 — Chiếu ghép lên Áo dài (Deterministic Garment Compositing):**
   - Thuật toán chấm điểm tự động tuyển chọn 1 trong 7 kiểu bố cục trang phục phù hợp nhất ([generation/layout_select.py](file:///d:/sangtaotre/tai-sinh-di-san-so-ai/generation/layout_select.py)).
   - Chiếu ghép tất định bằng mask nếp vải + displacement map + shading lên ảnh áo dài mẫu thật ([generation/garment.py](file:///d:/sangtaotre/tai-sinh-di-san-so-ai/generation/garment.py)).
   - Lượt hoàn thiện nhẹ img2img (`denoise = 0.40`) để tạo độ hòa quyện tự nhiên của lụa.
3. **Lớp Đánh giá & Minh bạch:**
   - Đo điểm tương đồng thị giác **Visual Similarity (%)** bằng mô hình CLIP giữa hoa văn sinh ra và hoa văn hiện vật gốc.
   - Trích xuất bảng màu chủ đạo (K-Means) và sinh **Design Passport**.
   - Lưu vết toàn bộ dữ liệu vào [evaluation/variants.csv](file:///d:/sangtaotre/tai-sinh-di-san-so-ai/evaluation/variants.csv).
4. **Phạm vi Legacy đã đóng băng:**
   - Supabase DB/RAG, Governance gate tiền kiểm, nút chọn Creative Intensity trên UI người dùng đã khóa lại, không phân bổ task mới.

---

## 2. HỆ THỐNG GIAO DIỆN CHUẨN (`web_ui`)

Thư mục giao diện tĩnh (trước đây có tên là `webtestdesign`, nay đã chuẩn hóa thành [web_ui](file:///d:/sangtaotre/tai-sinh-di-san-so-ai/web_ui)) là **Nguồn sự thật duy nhất (Single Source of Truth)** về mặt thiết kế giao diện:

### 2.1. Cấu trúc thư mục `web_ui`
```text
web_ui/
├── index.html                      # Khung trang chính gọn nhẹ
├── assets/
│   ├── css/                        # 15 stylesheet đã module hóa
│   │   ├── base.css, layout.css, footer.css, responsive.css
│   │   ├── sections/ (hero.css, catalog.css, curate-layout.css, curate-motion.css, variants.css)
│   │   ├── overlays/ (detail-modal.css, pipeline.css, passport.css, stage-lightbox.css)
│   │   └── effects/ (heritage-motion.css, loading-states.css)
│   ├── js/                         # component-loader.js, main.js
│   └── images/                     # Ảnh hiện vật, ảnh mẫu áo dài curate, icon pipeline
└── components/
    ├── layout/                     # header.html, footer.html
    ├── overlays/                   # modals.html (#detail-modal, #pipeline-modal, #passport-modal)
    └── sections/                   # experience.html (Hero & Catalog), curate.html (4 áo dài)
```

### 2.2. Luồng trải nghiệm người dùng 4 bước chuẩn mực
1. **Bước 1 — Khám phá & Lọc hiện vật:** Hero banner đồ họa sóng phượng SVG, thanh Filter Chips (`all`, `men-ran`, `men-lam`, `phat-giao`, `trang-tri`), lưới 6 thẻ hiện vật với 4 chấm màu men trích xuất.
2. **Bước 2 — Chiêm ngưỡng chi tiết (`#detail-modal`):** Cửa sổ nền mờ hiển thị ảnh phóng to, niên đại, phân loại, mô tả khảo cứu văn hóa, màu men to rõ và nút CTA lớn.
3. **Bước 3 — Tiến trình tạo tác AI (`#pipeline-modal`):** 4 Stage Cards trực quan (*Pha 01: Canny nét ➔ Pha 02: Hoa văn phẳng ➔ Pha 03: Ghép tà áo ➔ Pha 04: Áo dài hoàn chỉnh*), thanh tiến độ 0% → 100%.
4. **Bước 4 — Tuyển chọn thiết kế & Hộ chiếu (`curate.html` & `#passport-modal`):** Trình diễn 4 biến thể áo dài kèm huy hiệu tương đồng CLIP `★ {similarity}%`. Khi click xem mở Design Passport đối sánh hai chiều giữa áo dài và hiện vật gốc.

---

## 3. QUÁ TRÌNH TÁI CẤU TRÚC & TÁI SỬ DỤNG GIAO DIỆN CHO STREAMLIT

Thực hiện theo chỉ đạo của Người dùng: **Loại bỏ phân mảnh thiết kế, không duy trì CSS/HTML riêng trong Streamlit mà tái sử dụng 100% từ `web_ui` mà không làm thay đổi bất kỳ logic giao diện nào của bản gốc.**

### 3.1. Dọn sạch mã và file dư thừa trong `streamlit_ui`
- **Đã xóa:** `streamlit_ui/styles.css` (11.2 KB) — loại bỏ CSS cũ gây đè class.
- **Đã xóa:** `streamlit_ui/static_design.css` (68.4 KB) — loại bỏ bản sao CSS nguyên khối trùng lặp lỗi thời.
- **Đã xóa:** Toàn bộ các chuỗi HTML hardcode thô trong `streamlit_ui/views.py`.
- **Tạo mới:** `streamlit_ui/streamlit_overrides.css` (~25 dòng) — chỉ chứa CSS reset để ẩn header/footer mặc định của Streamlit và căn lề full-bleed.

### 3.2. Chuẩn hóa tên thư mục: `webtestdesign` ➔ `web_ui`
- Chuyển đổi an toàn qua lệnh `git mv` giữ 100% lịch sử Git.
- Cân xứng kiến trúc dự án: `web_ui/` (web tĩnh độc lập) và `streamlit_ui/` (Streamlit controller).
- Giữ nguyên vẹn 100% file, class CSS, JS, hình ảnh và animation.

### 3.3. Hoàn tất 5 Phase Tích hợp vào `streamlit_ui/views.py` & `helpers.py`
1. **Phase 1 (Header & Footer):** Nạp trực tiếp `header.html` (navbar kính mờ, stepper tự đổi `active`/`completed` theo URL query `?go=1..4`) và `footer.html`.
2. **Phase 2 (Bước 1 — Catalog & Hero):** Nạp trực tiếp `experience.html` với đồ họa sóng phượng SVG; Filter Chips lọc men theo URL param `?filter=...`; lưới 6 thẻ hiện vật nạp ảnh Base64 nét cao và màu men thật.
3. **Phase 3 (Bước 2 — Detail Modal):** Trích xuất `#detail-modal` từ `modals.html` với nền mờ có chiều sâu, ảnh hiện vật lớn, mô tả khảo cứu và nút CTA chuyển sang Bước 3 (`?go=3`).
4. **Phase 4 (Bước 3 — Visual Pipeline):** Trích xuất `#pipeline-modal` từ `modals.html`, nạp ảnh thật từ pipeline cho 4 Stage Cards, thanh tiến độ 100% và nút chuyển sang Bước 4 (`?go=4`).
5. **Phase 5 (Bước 4 — Curate & Passport):** Nạp `curate.html` hiển thị 4 thiết kế áo dài kèm điểm Similarity %, và `#passport-modal` đối sánh thiết kế và hiện vật gốc khi click chọn mẫu (`?choose=1..4`).

### 3.4. Khắc phục lỗi CommonMark Indented Code Block
- **Hiện tượng:** Trình duyệt in mã HTML/SVG thô ra màn hình dưới dạng code text.
- **Nguyên nhân:** Chuẩn CommonMark của Streamlit tự động coi các dòng thụt lề từ 4 dấu cách đi sau một dòng trống là một khối code (`<pre><code>`).
- **Giải pháp:** Bổ sung hàm `render_html()` tại [streamlit_ui/helpers.py](file:///d:/sangtaotre/tai-sinh-di-san-so-ai/streamlit_ui/helpers.py) tự động khử khoảng trắng thụt lề đầu dòng (`line.lstrip()`) trước khi truyền vào `st.markdown()`. Kiểm tra lại: 0 dòng còn thụt lề 4 dấu cách, đồ họa SVG và HTML hiển thị 100% sắc nét.

---

## 4. KẾT QUẢ KIỂM THỬ & TÌNH TRẠNG HIỆN TẠI

1. **Kiểm tra tự động E2E:** Script `scratch/test_e2e_all_phases.py` đã xác nhận:
   - 5/5 components HTML tồn tại và nạp chính xác.
   - 15/15 file CSS được nạp đúng thứ tự.
   - Toàn bộ dữ liệu ảnh của 6 hiện vật và biến thể áo dài trong [outputs/variants/](file:///d:/sangtaotre/tai-sinh-di-san-so-ai/outputs/variants) và [evaluation/variants.csv](file:///d:/sangtaotre/tai-sinh-di-san-so-ai/evaluation/variants.csv) đều khớp 100%.
2. **Khởi chạy cục bộ:** Ứng dụng Streamlit chạy trơn tru thông qua môi trường ảo:
   ```powershell
   .venv\Scripts\streamlit.exe run app.py
   ```
3. **Mã nguồn:** Gọn gàng, sạch sẽ, không còn file thừa, hoàn toàn sẵn sàng cho các giai đoạn tiếp theo.
