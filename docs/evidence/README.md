# Chỉ mục minh chứng theo ba yêu cầu cải tiến của ban tổ chức

Tài liệu này không chép lại dữ liệu. Nó chỉ nói: mỗi minh chứng ở đâu, đã có hay chưa. Cột "Trạng thái" ghi thẳng sự thật tại ngày 22/11/2026 (nhánh `test`). **Chưa có** nghĩa là nhóm cần làm, không phải đã làm.

Quy ước cột "Vị trí": đường dẫn không ghi chú là đã nằm trong git. Mục ghi "chỉ trên máy" là ảnh hoặc gói thô theo quy tắc dự án không commit, nhóm cần tải lên Google Drive hoặc R2 và dán link vào cột "Link nộp".

## Yêu cầu 1: đánh giá chất lượng thiết kế cuối

| Minh chứng | Vị trí | Trạng thái | Link nộp |
|---|---|---|---|
| Bộ ảnh đầu vào, hoa văn, áo cuối của 24 thiết kế | `outputs/runs/` (ảnh và manifest mã băm), `outputs/passports/` | Có | |
| Kiểm tra giữ họa tiết và dáng áo sau xuất | Cổng G2, G3: `tsds/quality/`, ngưỡng `config/quality_gate.json` (QG-1.0), giải thích `docs/finals/05_QUALITY_ASSURANCE.md` | Có | |
| Quy tắc loại và thử lại | `tsds/quality/pattern_retry.py`, `tsds/quality/retry.py`; mô tả ở `docs/finals/05_QUALITY_ASSURANCE.md` | Có | |
| Ví dụ bị loại (khoảng 123 lượt) | `outputs/qc/pattern_rejects.csv` và ảnh trong `outputs/qc/pattern_rejects/` | Chỉ trên máy | `[CẦN NHÓM ĐIỀN]` |
| Người am hiểu di sản và thiết kế xem mẫu, phiếu nhận xét | Tiêu chí phiếu: `config/expert_rubric.json`. Ghi phiếu qua API `POST /passports/{id}/reviews` | **Chưa có phiếu thật** | |

## Yêu cầu 2: đối chứng có kiểm soát, nhiều seed

| Minh chứng | Vị trí | Trạng thái | Link nộp |
|---|---|---|---|
| Đặc tả sáu thí nghiệm (mỗi lần đổi một yếu tố) | `tsds/evaluation/experiments/EXP-A_*.json` đến `EXP-G_*.json` | Có | |
| Cấu hình từng lượt chạy (CSV) | `outputs/experiments/EXP-*/plan.csv`, `spec.json` | Có | |
| Kết quả từng lượt (mỗi ảnh có SHA-256) | `outputs/experiments/EXP-*/results.csv`, `summary.json` | Có | |
| EXP-A: trọng số ControlNet, 120 lượt, 5 seed (42, 7, 123, 2024, 31415) | `outputs/experiments/EXP-A/`, phân tích ở `docs/finals/06_EXPERIMENTS.md` | Có | |
| Thống kê mức dao động theo seed | `docs/finals/06_EXPERIMENTS.md` (hệ số biến thiên theo từng ô hiện vật và mức; kiểm định Wilcoxon, Friedman) | Có | |
| Gói chấm mù đã dựng sẵn (ảnh đổi mã, phiếu HTML) | `outputs/review/blind_review/` (72 thiết kế, nhiều seed), `outputs/review/blind_review_EXP-A/` (48 ảnh); khoá giải mã `GIU_RIENG/key.csv` giữ riêng | Chỉ trên máy | `[CẦN NHÓM ĐIỀN]` |
| **Bảng điểm của người đánh giá mù** | cần có file điểm từ ít nhất 3 người chấm | **Chưa có** | |
| Độ đồng thuận giữa người chấm (Krippendorff alpha, mục tiêu từ 0,667) | tính sau khi có điểm | **Chưa có** | |

Giới hạn đã nêu trong hồ sơ: mỗi mức EXP-A có 30 cặp (6 hiện vật nhân 5 seed); kiểm định chạy ba lần cho mỗi chỉ số, không hiệu chỉnh; chưa chấm mù nên chưa kết luận được "đẹp hơn" hay "giống vải in hơn".

## Yêu cầu 3: bản quyền, nguồn gốc, truy vết

| Minh chứng | Vị trí | Trạng thái | Link nộp |
|---|---|---|---|
| Danh mục nguồn và giấy phép sáu hiện vật | `docs/DANH_MUC_NGUON_HIEN_VAT.md`, dữ liệu `data/heritage/metadata.json` (DOI, giấy phép CC BY 4.0, ghi công) | Có. Chưa xác minh riêng nguồn từng vật | |
| Phân tích nguồn gốc, bản quyền, quyền dùng theo mục đích | `docs/finals/07_PROVENANCE_COPYRIGHT.md` | Có | |
| Design Passport có phiên bản, chuỗi mã băm từ nguồn đến thành phẩm | `outputs/passports/` (24 file) | Có | |
| Lịch sử bước sửa tay | Bước `manual_edit` trong `tsds/provenance/passport.py`; API sửa tay phải qua lại cổng G3; có test | Có chức năng. Chưa có Passport ví dụ có bước sửa tay trong bộ nộp | `[CẦN NHÓM ĐIỀN: tạo một ví dụ]` |
| Kiểm tra toàn vẹn chuỗi mã băm | lệnh ở mục "Cách tự kiểm tra" bên dưới | Đạt 24/24 ngày 22/11 | |
| Nhãn nội dung có hỗ trợ AI | `tsds/provenance/labeling.py`; khai báo đầy đủ ở `docs/ai_disclosure.md` | Có nhãn khi xuất ảnh qua API. Ảnh trên giao diện web chưa gắn nhãn | |
| Khai báo công cụ AI | `docs/ai_disclosure.md` | Có. Còn chỗ `[CẦN NHÓM ĐIỀN]` (giấy phép từng mô hình, thư của tác giả VietFashion) | |
| Thư xin phép hoặc xác nhận của đơn vị giữ ảnh | không cần cho CC BY 4.0, nhưng cần xác minh nguồn từng vật nếu muốn khẳng định quyền dùng công khai | **Chưa có** | |

## Link thử nghiệm

| Minh chứng | Vị trí | Trạng thái |
|---|---|---|
| Hướng dẫn thử nghiệm một trang | `docs/HUONG_DAN_THU_NGHIEM.md` | Có. Còn chỗ `[CẦN NHÓM ĐIỀN]` (link production, liên hệ, thời gian đo trên Modal) |
| Mô tả triển khai và bảy kiểm thử | `docs/DEPLOY_LIVE.md` | Có. Bản Preview kiểm ngày 21/11/2026; production chưa chuyển; code mới (gói `tsds/`) chưa deploy thử |

## Cách tự kiểm tra

Chạy tại thư mục gốc repo, bằng PowerShell.

Toàn vẹn chuỗi mã băm của Passport:

```powershell
uv run python -c "import glob, json; from pathlib import Path; from tsds.provenance import passport as P; fs = sorted(glob.glob('outputs/passports/*.json')); ok = sum(bool(P.verify(json.load(open(f, encoding='utf-8')), Path('.'))['ok']) for f in fs); print(ok, '/', len(fs), 'Passport toàn vẹn')"
```

Bộ kiểm thử tự động (không cần GPU):

```powershell
uv run pytest
```

Ngày 22/11/2026: 358 ca, trong đó 1 ca bị bỏ qua vì dành cho máy không có GPU.

Sinh lại một bộ thiết kế (cần GPU): `uv run python scripts/demo/generate_demo_set.py LR3D_33`. Cùng seed 42 cho ảnh trùng từng bit (SHA-256) với bộ trong `outputs/runs/`, nhóm đã kiểm ngày 22/11/2026.

## Việc nhóm cần làm để đủ bộ minh chứng

1. Gửi gói chấm mù cho ít nhất 3 người chấm, thu điểm, tính Krippendorff alpha.
2. Mời ít nhất một người am hiểu di sản và một người am hiểu thiết kế xem mẫu, thu phiếu. Nếu hết hạn vẫn chưa có thì ghi đúng sự thật: đã liên hệ bao nhiêu nơi, chưa có phản hồi, thẩm định là hạng mục tiếp theo. Không ghi "đã thẩm định".
3. Tải ví dụ bị loại và gói chấm mù lên Drive, dán link vào cột "Link nộp".
4. Điền các chỗ `[CẦN NHÓM ĐIỀN]` trong `docs/ai_disclosure.md` và `docs/HUONG_DAN_THU_NGHIEM.md`.
5. Tạo một Passport ví dụ có bước sửa tay để minh chứng yêu cầu 3.
6. Deploy thử code mới lên Modal và Vercel, chạy bảy kiểm thử trong `docs/DEPLOY_LIVE.md`.
