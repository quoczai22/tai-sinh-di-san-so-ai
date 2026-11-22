# Kiến trúc giao diện: web_ui và Streamlit

Tài liệu này ghi **mỗi file làm gì** và **nằm ở bước nào của pipeline GUI**. Cập nhật lần cuối: 20/11/2026, sau đợt tách thư mục theo component.

## 1. Nguyên tắc

- **Không bundler, không framework.** web_ui chạy ES modules thuần (mở `index.html` là chạy) và dựng DOM bằng `h()` trong `tsds/core/dom.js`, đóng vai JSX.
- **Component** là một hàm `Ten(props) → HTMLElement`:
  - không đọc hay ghi biến toàn cục;
  - nhận dữ liệu qua tham số, báo sự kiện qua callback.
- **View** (`views/*.js`) chỉ lấy dữ liệu từ `tsds/core/data.js` rồi ghép component. View không tự định nghĩa component (có kiểm thử chặn: `tests/test_frontend.py::test_views_do_not_define_components`).
- **Mỗi component có file CSS cùng tên** trong `assets/css/components/`. Tên class bắt đầu bằng tên component (`.journey-card`, `.jc-img`…).
- **Mỗi file ≤ 500 dòng** và mở đầu bằng chú thích vai trò. Có kiểm thử chặn: `test_ui_files_stay_small_and_documented`.
- **`index.html` không sửa tay ở hai chỗ:** thẻ `<link>` CSS và import map. Thêm, đổi tên hay xoá file JS/CSS thì chạy `python scripts/web/ui_index.py`. Phát hành bản mới thì chạy `python scripts/web/ui_index.py finals-N`.
- **Không `innerHTML` với dữ liệu, không số viết cứng.** Có sẵn kiểm thử từ trước.

## 2. Luồng một lần mở trang

```
index.html ─► config.js (DH_API_BASE)
          └─► app.js
                ├─ tsds/core/motion.js       áp mức chuyển động đã lưu, đo máy yếu → <html class="motion-off|calm">
                ├─ tsds/core/data.js#init    GET /health (≤2,5 s) → chế độ live (có GPU) | demo (dữ liệu thật đã sinh sẵn)
                └─ tsds/core/router.js#startRouter
                      mỗi lần đổi hash:
                      ├─ tsds/core/routes.js           tìm trang, tải lười views/<mã>.js
                      ├─ components/nav.js        vẽ thanh trên, menu, chân trang; đóng menu
                      ├─ views/<mã>.js#render     lấy dữ liệu (tsds/core/data.js) → ghép components
                      ├─ components/hero/index.js ảnh bìa của trang
                      ├─ tsds/core/reveal.js#enhance   gắn hiệu ứng hiện dần
                      └─ tsds/core/scenes.js#scenes    cảnh cuộn (--e/--p/--x, khối dính --pp)
```

## 3. Pipeline GUI cho người xem

| Bước | Trang (hash) | View | Component chính | Dữ liệu / API |
|---|---|---|---|---|
| 0. Khám phá | `#/library` | `views/library.js` | `hero/fan`, `journey-card`, `artifact-card`, `gallery-item`, `chapter-head`; trang trí `decor/phoenix`, `decor/drum` | `data.heritage()`, `data.passports()` |
| 1. Chọn đầu vào | `#/studio` | `views/studio.js` | `picker-card` (rê chuột thì xoay 3D qua `viewer3d.hoverSpin`) | `data.heritage()` |
| 2. Tạo thiết kế | `#/studio/<mã>` | `views/studio.js` | `viewer3d`, `viewer-controls`, `artifact-book` (nút "Xem ý nghĩa hoa văn" mở sổ hai trang nổi trên trang), `layout.stateBox` | Có GPU: `tsds/core/generation.js` gọi `POST /generate` rồi hỏi `GET /generate/{id}`. Không có GPU: mở bộ đã sinh sẵn, không giả lập |
| 3. Xem và tải đầu ra | `#/result/<mã>` | `views/result.js` | `design-card`, `lightbox`, `badges.demoNotice` | `data.passports()`, `tsds/core/download.js` |

Nhãn AI (`components/badges.js#aiMark`) có trên **mọi** ảnh do AI hỗ trợ tạo, phục vụ YC3. Ở chế độ trình diễn, trang Kết quả luôn có dòng "Kết quả đã sinh sẵn".

## 4. Cây thư mục web_ui

```
web_ui/
├── index.html                 khung trang tĩnh (thanh trên, ảnh bìa, #main, chân trang) + CSS/import map do script sinh
├── data/                      dữ liệu THẬT cho chế độ trình diễn (scripts/demo/export_demo_data.py xuất)
└── assets/
    ├── js/
    │   ├── app.js             điểm khởi động (3 bước ở mục 2)
    │   ├── config.js          DH_API_BASE (địa chỉ API GPU)
    │   ├── core/              KHÔNG vẽ giao diện
    │   │   ├── dom.js         h(), clear(), toast()
    │   │   ├── icons.js       icon(tên) → <svg>
    │   │   ├── data.js        lớp dữ liệu duy nhất: live/demo, heritage, passports, media, generate, audit
    │   │   ├── designs.js     quy tắc chọn ảnh thiết kế (latestOf, patternOf, byPref, pickPassport, fullImage)
    │   │   ├── generation.js  vòng sinh: POST /generate → hỏi trạng thái → báo tiến độ
    │   │   ├── download.js    tải ảnh về máy (luôn PNG/JPEG)
    │   │   ├── routes.js      bảng trang
    │   │   ├── router.js      đổi trang theo hash, chuyển cảnh mờ chéo
    │   │   ├── motion.js      reduced()/calm(), bật/tắt chuyển động, máy yếu, trình chiếu cycle()
    │   │   ├── reveal.js      hiện dần khi cuộn, số đếm, chữ tách từ / sáng dần
    │   │   └── scenes.js      cảnh cuộn (--e/--p/--x/--pp), thị sai
    │   ├── components/        thành phần tái sử dụng, mỗi file một thành phần
    │   │   ├── nav.js         thanh trên + menu + chân trang + sợi chỉ cuộn
    │   │   ├── hero/          index.js (ảnh bìa), fan.js (quạt thẻ), marquee.js (băng ảnh trôi)
    │   │   ├── badges.js      nhãn AI, nhãn "đã sinh sẵn"
    │   │   ├── layout.js      section, stateBox
    │   │   ├── chapter-head.js, journey-card.js, artifact-card.js, gallery-item.js   (trang chủ)
    │   │   ├── picker-card.js, viewer3d.js, viewer-controls.js, artifact-book.js     (Studio)
    │   │   └── design-card.js, lightbox.js                                           (Kết quả)
    │   ├── decor/             hình trang trí SVG: phoenix.js, drum.js (trống, mây, sợi chỉ)
    │   ├── views/             library.js, studio.js, result.js — chỉ ghép component
    │   └── vendor/three/      Three.js (MIT), nạp qua import map, chỉ tải khi cần 3D
    ├── css/                   thứ tự nạp = assets/css/order.json
    │   ├── base/              tokens → reset → typography → layout → reveal  …  motion (nạp cuối)
    │   ├── components/        1 file cho 1 component JS (nav, menu, hero, hero-fan, journey-pin, journey-card,
    │   │                      artifact-card, picker-card, gallery-item, design-card, lightbox, viewer3d, artifact-book, footer,
    │   │                      buttons, badges, feedback)
    │   ├── decor/             phoenix.css, drum.css
    │   └── views/             home.css, studio.css, result.css
    ├── models/                mô hình GLB của hiện vật (viewer3d)
    └── images/                ảnh PNG gốc để tải xuống ở chế độ trình diễn
```

### Thứ tự CSS và lý do

`base/tokens` → `base/reset` → `base/typography` → `base/layout` → `base/reveal` → `components/*` → `decor/*` → `views/*` → `base/motion`

- `base/reveal` nạp **trước** component: transition và opacity riêng của `.journey-card`, `.design`, `.out-card`… phải đè được luật `.reveal` chung, đúng như bản gốc.
- `base/motion` nạp **cuối**: các luật tắt chuyển động (`html.motion-off *`) phải thắng.
- Trong mỗi file, các luật giữ nguyên thứ tự như trong `app.css` và `exhibit.css` cũ.

## 5. Streamlit (công cụ nội bộ kiểm chứng pipeline)

```
app.py                          điểm chạy: streamlit run app.py → streamlit_ui.app.main()
streamlit_ui/
├── app.py                      luồng: theme → đọc hiện vật → trạng thái phiên → thanh bên → màn hình Tạo
├── state.py                    st.session_state: hiện vật đang chọn, bộ thiết kế vừa sinh
├── theme.py                    cấu hình trang, CSS, tiêu đề
├── variants.py                 đọc bộ 4 ảnh đã sinh trên ổ đĩa
├── components/
│   ├── sidebar.py              GPU/CPU, PyTorch, Python, thống kê dữ liệu
│   ├── heritage_picker.py      bước 1–2: chọn hiện vật, thông tin, trạng thái PyTorch, nút Tạo
│   └── variant_results.py      bước cuối: 3 thẻ (bộ 4 thiết kế + tải PNG, đối chiếu, bảng số liệu)
├── screens/generate.py         ghép các component; gọi tsds/pipeline/run.py khi bấm Tạo
└── heritage_data.py            lớp chuyển tiếp → tsds/provenance/heritage.py (giữ cho mã cũ)
```

- Thư mục màn hình tên `screens/` chứ không phải `pages/`, vì Streamlit tự coi `pages/` là trang con.
- `load_heritage_metadata` đã chuyển sang `tsds/provenance/heritage.py`. Lý do: API (`tsds/api/main.py`), `evaluation/`, `mock_backend.py` và kiểm thử đều dùng hàm này, mà backend thì không được phụ thuộc thư mục giao diện. `Dockerfile` không còn phải chép `streamlit_ui/`.

## 6. Thêm một thành phần mới

1. Tạo `assets/js/components/ten-moi.js`:
   - mở đầu bằng 2–3 dòng chú thích (vai trò, props, dùng ở đâu);
   - `export function tenMoi(props)` trả về phần tử.
2. Nếu cần CSS:
   - tạo `assets/css/components/ten-moi.css`, class bắt đầu bằng `.ten-moi`;
   - thêm vào `assets/css/order.json`, đặt trước `views/` và `base/motion.css`.
3. `import` trong view cần dùng.
4. Chạy `python scripts/web/ui_index.py`, rồi `pytest tests/test_frontend.py`.

## 7. Đợt tách ngày 20/11/2026: đã làm gì, kiểm chứng ra sao

- **JS:**
  - `lib/` được chia thành `core/`, `components/` và `decor/`.
  - `ui.js` (19 hàm) chỉ giữ 4 hàm còn dùng, chuyển vào `badges.js` và `layout.js`.
  - Các component nằm trong view được tách ra file riêng: `designCard`, `zoomablePic`/`openLightbox`, `pickerCard`, thẻ hành trình, thẻ hiện vật, ảnh tà áo, thanh điều khiển 3D.
  - Code của các trang đã gỡ khỏi web hôm 19/11 được bỏ (vẫn còn trong lịch sử git): `rail`, `tilt`, các chip thẩm định, `chain`, `kv`, `stat`, `fmt`, `downloadJson`, gọi API phiếu thẩm định/QC/chỉnh sửa, ảnh bìa nổi của Studio (`studioVisual`, chưa từng được gọi).
- **CSS:**
  - `app.css` (325 dòng) và `exhibit.css` (5.187 dòng) được chia thành 27 file, file dài nhất 445 dòng.
  - Bỏ 358 bộ chọn và 2 keyframes không còn khớp phần tử nào: class của chúng không còn xuất hiện trong JS/HTML.
- **Kiểm chứng:**
  - Chụp `getComputedStyle` của mọi phần tử, kể cả `::before`/`::after`, ở 4 trang × 9 cấu hình. Các cấu hình gồm 6 khổ từ 390 đến 1440px, chế độ tắt chuyển động và chế độ máy yếu. Kết quả trùng bản gốc, kể cả transition.
  - Phần lệch còn lại chỉ là nhiễu thời điểm: băng ảnh trôi lệch vài px, còn lề `auto` khi đo hai lần trên chính bản gốc cũng cho kết quả khác nhau.
  - Kịch bản tương tác (menu, tắt chuyển động, Studio, Tạo, lightbox) cho kết quả giống bản gốc.
  - Streamlit: cây phần tử giống hệt ở 3 trạng thái.
  - Có đúng một chỗ phải bù vì thứ tự nạp đổi: logo chân trang trên điện thoại (`footer.css`, khối `@media (max-width: 640px)`).
