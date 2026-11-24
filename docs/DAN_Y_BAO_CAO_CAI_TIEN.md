# Dàn ý báo cáo cải tiến: Tái sinh Di sản Số

Tài liệu này là dàn ý để soạn báo cáo cải tiến (LaTeX). Nó không chép lại số liệu. Mỗi mục ghi: viết gì, lấy dữ liệu hoặc hình ở đâu, còn thiếu gì. Ngày soạn 24/11/2026.

Nguyên tắc xuyên suốt:
1. Ba yêu cầu của ban tổ chức (BTC) là xương sống. Mỗi yêu cầu theo một khung: BTC yêu cầu gì, nhóm làm gì, bằng chứng ở đâu, còn thiếu gì.
2. Tách "cải tiến mới" khỏi "chức năng sẵn có".
3. Mọi con số phải khớp tệp nguồn. Chỗ nào chưa làm thì ghi đúng, không viết "đã xong".
4. Cuối mỗi chương yêu cầu có một hộp "Bằng chứng" gồm đường dẫn tệp và lệnh để người chấm tự kiểm.

## Chương 0. Tóm tắt (1 trang)

- Bảng 3 dòng: yêu cầu, đã làm, bằng chứng, còn thiếu. Nguồn: `docs/cac_yeu_cau_cai_tien.md`, mục 1.
- Bốn điểm cải tiến mới đáng nêu: cổng G3 áp cho cả bản người sửa tay; trang Thiết kế đã tạo; trang tải bản chỉnh sửa ghi vào Passport; nhãn "Đã chỉnh sửa" trên ảnh (giao diện và file tải về).
- Link thử nghiệm và tình trạng deploy (preview hay production).

## Chương 1. Bối cảnh và mục tiêu

1.1 Bài toán: đưa hoa văn gốm Bát Tràng lên áo dài, giữ họa tiết và dáng áo.
1.2 Hệ thống bản trước (09/2026) và hạn chế BTC chỉ ra.
1.3 Ba yêu cầu cải tiến của BTC (chép nguyên văn).
1.4 Bảng "trước và sau": mỗi dòng một cải tiến, nằm ở chương nào.
1.5 Phạm vi và cách đọc báo cáo.

Nguồn: `docs/finals/01_AUDIT.md`, `docs/finals/11_CHANGELOG.md`.

## Chương 2. Phân tích và thiết kế hệ thống (UML)

2.1 Tác nhân và chức năng: sơ đồ use case (19 ca, đã có `docs/finals/diagrams/use_case.puml`). Cần thêm ca "xem lại thiết kế đã tạo" và "tải bản chỉnh sửa".
2.2 Quy trình nghiệp vụ: BPMN AS-IS và TO-BE (đã có), đối chiếu APQC (`docs/finals/02_APQC.md`, `03_BPMN.md`).
2.3 Kiến trúc thành phần: sơ đồ component các gói `tsds/` (`generation`, `quality`, `provenance`, `evaluation`, `api`), `web_ui`, cổng Vercel. **Cần vẽ.**
2.4 Mô hình dữ liệu: sơ đồ lớp của Design Passport (heritage, artifacts, generation, process_steps, quality, versions, edits, reviews, approval, ai_disclosure, ledger, rights). Dữ liệu dạng tệp JSON, không có cơ sở dữ liệu. **Cần vẽ.**
2.5 Trạng thái phê duyệt: sơ đồ trạng thái 7 trạng thái (`APPROVAL_STATES` trong `tsds/provenance/passport.py`), và việc sửa tay đưa Passport về chờ thẩm định lại. **Cần vẽ.**
2.6 Tương tác: sơ đồ tuần tự "Tạo thiết kế" (trình duyệt, cổng, Modal, hàng chờ, pipeline, G2, G3, Passport, hỏi lại trạng thái) và "Tải bản chỉnh sửa" (kiểm form, giới hạn lượt, Modal, G3, sổ cái). **Cần vẽ.**
2.7 Quyết định thiết kế và đánh đổi: dùng tệp thay cơ sở dữ liệu; hai chế độ trực tiếp và trình diễn; cổng Vercel che khóa; ID tài khoản thay email.

Tùy chọn: sơ đồ hoạt động của vòng thử lại G2, G3 (đổi seed, hạ trọng số ControlNet, khóa họa tiết, tối đa 3 lần).

## Chương 3. Chức năng hệ thống và pipeline

3.1 Luồng người dùng trên web, mỗi bước một ảnh chụp: Trang chủ, Studio (có thanh tiến độ), Kết quả (4 thiết kế), cửa sổ phóng to, Thiết kế đã tạo, trang chỉnh sửa, các hộp xác nhận, hộp "Đã cập nhật bản chỉnh sửa". **Cần chụp.**
3.2 Pipeline AI 11 bước: dùng `outputs/report_figures/pipeline_viz/` (bộ `R20261124T043655-HV09`).
3.3 Chọn bố cục bằng CLIP, mặt nạ vùng in không lem ra ngoài áo, polish chỉ trong vùng áo, khóa họa tiết.
3.4 Nhãn AI: trên giao diện, in lên file tải về (`design_image/truoc_sau_ghep.png`), trên ảnh xuất qua API.

## Chương 4. Yêu cầu 1: đánh giá thiết kế cuối

4.1 Yêu cầu và cách hiểu: đánh giá thiết kế cuối, không chỉ hoa văn trung gian.
4.2 Cổng G2: `vessel_leakage`, `seam_ratio`. Cổng G3: PPS, `garment_shape_iou`, `sharpness_ratio`, `detail_ratio`, `palette_shift_de`. Công thức, ngưỡng (`config/quality_gate.json`, QG-1.0).
4.3 Quyết định PASS, WARN, FAIL; vòng loại và thử lại; không tự phê duyệt.
4.4 Kết quả 24 thiết kế: G2 đạt 16, cảnh báo 6, loại 2; G3 đạt 20, cảnh báo 4, loại 0; PPS trung bình 0,952. Nguồn: `docs/cac_yeu_cau_cai_tien.md` mục 2.
4.5 Thẩm định chuyên gia: tiêu chí `config/expert_rubric.json`, phiếu đã dựng, **chưa có phiếu thật**.
4.6 Giới hạn: ngưỡng tạm thời, chưa hiệu chỉnh bằng phiếu chuyên gia; chỉ đo kỹ thuật, không đo thẩm mỹ.

Hình: `passport/lan1/passport_6_chat_luong.png`, bước 8 và 9 của `pipeline_viz`.

## Chương 5. Yêu cầu 2: đối chứng có kiểm soát, nhiều seed

5.1 Nguyên tắc: mỗi thí nghiệm chỉ đổi một yếu tố, module từ chối kế hoạch đổi nhiều hơn một yếu tố.
5.2 Sáu thí nghiệm EXP-A đến EXP-G: bảng yếu tố, số lượt, số seed.
5.3 EXP-A chi tiết: 120 lượt, 5 seed (42, 7, 123, 2024, 31415). Hệ số biến thiên theo seed, kiểm định Wilcoxon, Friedman.
5.4 Chấm mù: 28 phiếu của người quan tâm; điểm giảm từ 3,72 xuống 3,38 khi hạ trọng số ControlNet.
5.5 Độ đồng thuận: Krippendorff alpha 0,028, **không đạt** mục tiêu 0,667. Nêu thẳng, và nói 28 người không phải chuyên gia.
5.6 Giới hạn: mỗi mức 30 cặp; chưa có chấm mù của chuyên gia.

Hình: **cần vẽ** biểu đồ điểm trung bình theo mức trọng số kèm độ dao động theo seed. Nguồn: `outputs/experiments/EXP-A/`, `docs/finals/06_EXPERIMENTS.md`.

## Chương 6. Yêu cầu 3: nguồn gốc, bản quyền, truy vết

6.1 Nguồn và giấy phép sáu hiện vật (DOI, CC BY 4.0, ghi công). Nguồn: `docs/DANH_MUC_NGUON_HIEN_VAT.md`.
6.2 Cổng quyền theo bốn mục đích: hiển thị, xuất bản, thương mại.
6.3 Design Passport: cấu trúc, chuỗi mã băm, kiểm toàn vẹn 28/28.
6.4 Nhãn nội dung có hỗ trợ AI và khai báo công cụ AI (`docs/ai_disclosure.md`).
6.5 **Lịch sử sửa thủ công** (điểm mới chính):
  - Luồng: tải bản sửa lên, ghi `edits`, tạo phiên bản `human_edit`, thêm bước `manual_edit`, chạy lại G3, về chờ thẩm định.
  - Ví dụ thật: Passport `DP-HV09-20261124T043655-V3`, bản sửa E1 (người sửa `TSDS01`, vai trò designer, công cụ Canva).
  - So lần 1 với lần 2: `edits` 0 thành 1; `versions` 1 thành 2; `process_steps` 9 thành 11; sổ cái 12 thành 18 mục, 12 mục đầu giữ nguyên.
  - Ảnh trước và sau, mã băm khớp Passport.
  - Quan sát thật: bản sửa chỉ đổi độ sáng mà PPS tụt từ 0,97 xuống 0,72 (vẫn PASS).
6.6 Giới hạn: chưa xác minh riêng nguồn từng hiện vật; ví dụ sửa tay do thành viên nhóm làm, chưa qua chuyên gia; chưa có thư xác nhận từ đơn vị giữ ảnh.

Hình: toàn bộ `passport/lan1/` và `passport/lan2/`, `design_image/truoc_sau_ghep.png`.

## Chương 7. Luồng triển khai (deploy)

7.1 Kiến trúc triển khai: sơ đồ deployment. Vercel (giao diện tĩnh và hàm cổng trong `web_ui/api/`), Modal (FastAPI trên GPU T4, Volume tại `/data/outputs`). **Cần vẽ.**
7.2 Các bước: đổi token phiên bản (`scripts/web/ui_index.py`), đặt biến môi trường, deploy Modal, deploy Vercel, kiểm thử không tốn GPU, thử một lượt thật.
7.3 Bí mật và biến: `MODAL_URL`, `MODAL_KEY`, `TSDS_WRITE_KEY`, `MODAL_WRITE_KEY`, `DH_API_KEY` (không ghi giá trị).
7.4 Bảo vệ: giới hạn lượt theo IP, kích thước ảnh tối đa 3 MB, kiểm chữ ký PNG, khóa ghi do máy chủ giữ.
7.5 Dự phòng: Modal lỗi thì cổng trả `backend=demo`, giao diện dùng dữ liệu sinh sẵn và hiện nhãn.
7.6 Tình trạng thật: preview đã kiểm 21/11/2026; production chưa chuyển; trang tải bản chỉnh sửa **chưa deploy thử**; Vercel Authentication đang bật nên người ngoài chưa mở được. **Cần xác nhận với thành viên phụ trách deploy.**

Nguồn: `docs/DEPLOY_LIVE.md`, `docs/HUONG_DAN_THU_NGHIEM.md`.

## Chương 8. Kiểm thử và bảo mật dữ liệu người dùng

8.1 Kiểm thử: pytest (chạy lại và ghi số ca khi chốt báo cáo), kiểm thử giao diện bằng Node, rà soát độc lập đối chiếu đặc tả với kết quả thật.
8.2 Bảo mật tải ảnh: người dùng nhập ID bắt đầu bằng TSDS, không nhập họ tên hay email; giới hạn lượt; không ghi nội dung biểu mẫu vào nhật ký.
8.3 Giới hạn đã biết: tuyến `/media/artifact` phục vụ mọi tệp dưới `outputs/`; chưa siết. Nêu thẳng.

## Chương 9. Giới hạn và hướng tiếp theo

Bảng: việc chưa làm, vì sao, hướng làm tiếp. Gồm: phiếu chuyên gia thật, chấm mù lại với người có chuyên môn, xác minh nguồn từng hiện vật, hiệu chỉnh ngưỡng chất lượng, deploy production và trang chỉnh sửa, hiển thị Passport trên giao diện.

## Phụ lục

- A. Chỉ mục minh chứng (`docs/evidence/README.md`).
- B. Cách tự kiểm tra: lệnh kiểm toàn vẹn chuỗi mã băm.
- C. Bảng danh mục hình: tệp, chương dùng.
- D. Thuật ngữ (Passport, G2, G3, PPS, seed, ControlNet, LoRA, SAM, CLIP).

## Danh mục hình hiện có

| Hình | Dùng ở |
|---|---|
| `report_figures/pipeline_viz/<run>/buoc01` đến `buoc11` | 3.2, bước 8 và 9 ở 4 |
| `report_figures/passport/lan1/passport_1` đến `passport_9` | 4.2, 6.3, 6.5 |
| `report_figures/passport/lan2/passport_1` đến `passport_9` | 6.5 |
| `report_figures/passport/lan2/anh_truoc_sau.png`, `ma_bam_truoc_sau.png` | 6.5 |
| `report_figures/design_image/truoc_sau_ghep.png` | 3.4, 6.4 |
| `docs/finals/diagrams/use_case.svg`, `bpmn_as_is.svg`, `bpmn_to_be.svg` | 2.1, 2.2 |

## Việc cần làm trước khi viết

1. Vẽ 6 sơ đồ mới (component, class Passport, state phê duyệt, 2 sơ đồ tuần tự, deployment) bằng PlantUML.
2. Vẽ biểu đồ EXP-A cho chương 5.
3. Chụp luồng giao diện web cho mục 3.1.
4. Xác nhận trạng thái deploy với thành viên phụ trách.
5. Quyết định nơi lưu Passport mới và ảnh sửa tay để BTC kiểm được (Drive hoặc commit).
6. Cập nhật dòng "Lịch sử bước sửa tay" trong `docs/evidence/README.md`.
