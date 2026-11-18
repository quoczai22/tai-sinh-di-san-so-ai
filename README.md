# Tái Sinh Di Sản Số

> Hoa văn gốm Bát Tràng, dệt lại thành áo dài — có kiểm định chất lượng, thí nghiệm có đối chứng và hồ sơ truy vết cho từng thiết kế.

Bài dự thi **vòng chung kết** Cuộc thi Sáng tạo trẻ Quốc gia về Trí tuệ nhân tạo 2026, Bảng C — nhóm *3 chàng hiệp sĩ mộng mơ*.
Hồ sơ đầy đủ cho Ban tổ chức (BTC) nằm ở [`docs/finals/`](docs/finals/README.md).

## Mục lục

1. [Ba yêu cầu cải tiến của BTC](#1-ba-yêu-cầu-cải-tiến-của-btc)
2. [Xem nhanh (không cần GPU)](#2-xem-nhanh-không-cần-gpu)
3. [Kiến trúc](#3-kiến-trúc)
4. [Cấu trúc thư mục](#4-cấu-trúc-thư-mục)
5. [Cài đặt và chạy](#5-cài-đặt-và-chạy)
6. [Biến môi trường](#6-biến-môi-trường)
7. [Tài liệu](#7-tài-liệu)
8. [Trạng thái và việc còn lại](#8-trạng-thái-và-việc-còn-lại)

---

## 1. Ba yêu cầu cải tiến của BTC

| # | BTC yêu cầu | Đã làm | Xem ở |
|---|---|---|---|
| 1 | Đánh giá **thiết kế cuối**, không chỉ hoa văn trung gian | Cổng **G2** (hoa văn: rò dáng bình, đường nối) và **G3** (thiết kế cuối: giữ họa tiết PPS, IoU dáng áo, độ nét, lệch màu ΔE); định tuyến sinh lại / sửa / QC xem / chuyển chuyên gia; khoá họa tiết `pattern_lock_v1`; bộ tiêu chí chuyên gia 5 mục chấm mù. Không chỉ số nào tự phê duyệt thiết kế. | `quality/`, `config/quality_gate.json`, `config/expert_rubric.json`, [05](docs/finals/05_QUALITY_ASSURANCE.md) |
| 2 | **Đối chứng có kiểm soát**, nhiều seed, chấm mù | Module thí nghiệm từ chối kế hoạch đổi hơn một yếu tố; EXP-A (trọng số ControlNet), EXP-B (bước hoàn thiện), EXP-C (từng bước ghép, đã chạy); gói chấm mù; thống kê KTC 95%, hệ số biến thiên, Krippendorff α, Wilcoxon, Friedman | `evaluation/experiment.py`, `evaluation/experiments/`, [06](docs/finals/06_EXPERIMENTS.md) |
| 3 | **Bản quyền, nguồn gốc, truy vết** | Danh mục nguồn schema 2.0; cổng quyền theo 4 mục đích sử dụng; Design Passport có sổ cái băm nối chuỗi, phiên bản có băm cha, chỉnh sửa tay chạy lại G3; nhãn "Thiết kế hỗ trợ bởi AI" trên ảnh xuất | `provenance/`, `data/heritage/metadata.json`, `outputs/passports/`, [07](docs/finals/07_PROVENANCE_COPYRIGHT.md) |

Kết quả trên 24 thiết kế ngày 06/09/2026 (`evaluation/quality_gate_legacy.csv`): G2 đạt 21 · cảnh báo 1 · loại 2; G3 đạt 0 · cảnh báo 4 · loại 20; sau khi khoá họa tiết 19 thiết kế: đạt 10 · cảnh báo 9. Điểm PPS sau sửa cao một phần do chính cách sửa (chép lại nét gốc), nên phải chờ chuyên gia chấm mù mới kết luận được bản sửa có đẹp hơn.

## 2. Xem nhanh (không cần GPU)

```powershell
python -m http.server 5500 --directory web_ui
```

Mở `http://127.0.0.1:5500`. Không có API thì giao diện tự chạy **chế độ ngoại tuyến**, đọc dữ liệu thật đã xuất sẵn trong `web_ui/data/`.

## 3. Kiến trúc

```text
 Hiện vật (data/heritage, có nguồn & quyền)
        │  tiêu chí tuyển ảnh C1–C4 · cổng quyền
        ▼
 GIAI ĐOẠN 1  SD 1.5 + ControlNet Canny (chỉ nét hoa văn) ──► hoa văn phẳng lát liền ──► Cổng G2
        ▼
 GIAI ĐOẠN 2  CLIP chọn bố cục ─► ghép tất định lên áo mẫu ─► img2img ──► Cổng G3 ─► (sửa: khoá họa tiết)
        ▼
 QC Officer (cảnh báo) ─► Chuyên gia chấm mù ─► Phê duyệt / yêu cầu sửa / loại
        ▼
 Design Passport: tệp + SHA-256, tham số, bước AI/hệ thống/người, phiên bản, phiếu, quyền, nhãn AI
```

| Thành phần | Công nghệ |
|---|---|
| Sinh ảnh | Stable Diffusion 1.5 + ControlNet v1.1 Canny (`diffusers`, PyTorch CUDA), CLIP (`transformers`) |
| Xử lý ảnh, phép đo | OpenCV, Pillow, NumPy, scikit-image, SciPy |
| API | FastAPI + Uvicorn (`api/main.py`); PyTorch chỉ nạp khi cần, máy không GPU thì `/generate` trả 503 |
| Giao diện | HTML/CSS/JS thuần (ES modules), không framework; một họ chữ Noto Serif |
| Dữ liệu | Tệp JSON/CSV trong repo, không dùng cơ sở dữ liệu |
| Kiểm thử | pytest (130 ca, không cần GPU) |

## 4. Cấu trúc thư mục

```text
.
├── api/                  FastAPI: hiện vật, sinh thiết kế, Passport, QC, thẩm định, chỉnh sửa, xuất bản, thí nghiệm
├── generation/           Pipeline hai giai đoạn (controlnet, pattern, palette, layout_select, garment, streamlit_runner)
├── quality/              Cổng G2/G3, phép đo, khoá họa tiết
├── provenance/           Danh mục nguồn, cổng quyền, Design Passport, băm, nhãn AI
├── evaluation/           Thí nghiệm có kiểm soát (experiment.py, experiments/), kết quả cổng trên 24 thiết kế
├── config/               Ngưỡng cổng QG-1.0, tiêu chí tuyển ảnh, bộ tiêu chí chuyên gia (có phiên bản)
├── data/
│   ├── heritage/         Ảnh hiện vật, metadata.json (schema 2.0), sources/ (ứng viên ảnh CC0 thay thế)
│   ├── garment/          Áo dài mẫu và các bố cục
│   ├── archive/          Siêu dữ liệu schema 1 (đầu vào của bước chuyển đổi)
│   └── prompt_terms.json
├── outputs/
│   ├── runs/             Mỗi lần chạy một thư mục + manifest SHA-256
│   ├── passports/        24 Design Passport
│   ├── experiments/      Kế hoạch, kết quả, gói chấm mù
│   └── variants/         Ảnh 24 thiết kế gốc (Passport tham chiếu, không di chuyển)
├── web_ui/               Giao diện: index.html, assets/ (css, js/lib, js/views), data/ (dữ liệu chế độ ngoại tuyến)
├── scripts/              01–04 cài đặt & kiểm GPU · 07 mô tả hoa văn · 08 chuyển schema · 09 nạp ảnh hiện vật
│                         · 10 dựng lại lần chạy cũ · 11 xuất dữ liệu giao diện · 12 sinh sơ đồ BPMN/Use Case
├── streamlit_ui/, app.py Công cụ kiểm chứng pipeline nội bộ (Streamlit)
├── tests/                130 ca pytest
├── docs/
│   ├── finals/           Hồ sơ vòng chung kết 01–11 + diagrams/ (BPMN 2.0, Use Case)
│   ├── evidence/         Ảnh đối chiếu hiện vật – hoa văn – bản ghép – bản cuối – bản sửa (quality_gate/)
│   └── SETUP_AI_LOCAL.md Cài môi trường GPU
├── archive/              Lưu trữ bản 09/2026 (giao diện, đặc tả MVP, smoke test) — không thuộc bản chung kết
├── requirements.txt · requirements-dev.txt · pytest.ini · vercel.json
└── README.md
```

## 5. Cài đặt và chạy

Lệnh chạy bằng PowerShell tại thư mục gốc.

**A. Giao diện + API (không cần GPU)**

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = "1"                       # các tệp requirements có chú thích tiếng Việt
pip install -r requirements-dev.txt; pip install uvicorn
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000     # cửa sổ 1
python -m http.server 5500 --directory web_ui                    # cửa sổ 2
```

Có API ở `127.0.0.1:8000` thì giao diện chạy chế độ trực tiếp (ghi phiếu thẩm định, QC, chỉnh sửa qua API).

**B. Kiểm thử**

```powershell
pytest            # 130 ca; 19 ca kiểm tra cú pháp JS cần Node.js, máy không có Node thì được bỏ qua
```

**C. Sinh ảnh và thí nghiệm (cần GPU NVIDIA ≥ 6 GB, xem [`docs/SETUP_AI_LOCAL.md`](docs/SETUP_AI_LOCAL.md))**

```powershell
pip install -r requirements.txt             # cài PyTorch CUDA theo hướng dẫn SETUP_AI_LOCAL
python scripts/03_download_models.py
python -m evaluation.experiment run evaluation/experiments/EXP-A_controlnet_weight.json
python -m evaluation.experiment run evaluation/experiments/EXP-B_stage2_finish.json
python scripts/11_export_demo_data.py       # cập nhật web_ui/data cho chế độ ngoại tuyến
```

**D. Nạp ảnh hiện vật mới** (kiểm SHA-1, tách nền, chấm C1–C4, ghi ở trạng thái chờ rà soát)

```powershell
python scripts/09_ingest_heritage_image.py --file <ảnh> --candidate <mã Commons> --heritage-id <mã> --name "<tên>" --dry-run
```

**E. Công cụ kiểm chứng nội bộ:** `streamlit run app.py`

**Triển khai giao diện:** `vercel.json` chuyển `/` tới `web_ui/index.html`. Khi có API GPU công khai, đặt `window.DH_API_BASE` trong `web_ui/assets/js/config.js`. Mỗi lần phát hành giao diện, đổi chuỗi phiên bản `finals-N` trong `web_ui/index.html` (thẻ link, script và import map) để trình duyệt không dùng lại tệp cũ.

## 6. Biến môi trường

Đặt trong tệp `.env` ở thư mục gốc (không commit).

| Biến | Dùng cho | Ghi chú |
|---|---|---|
| `HF_HOME` | Tải model | Tuỳ chọn |
| `SD15_MODEL_ID`, `CONTROLNET_CANNY_ID` | Pipeline sinh ảnh | Id repo model |
| `GEMINI_API_KEY` | Chỉ `scripts/07_describe_heritage.py` | Chạy offline một lần |
| `WEB_UI_ORIGINS` | API khi triển khai | Danh sách domain giao diện, phân tách bằng dấu phẩy |
| `TSDS_WRITE_KEY` | API khi chạy công khai | Thao tác ghi phải gửi header `X-API-Key` |
| `TSDS_GENERATE_PER_HOUR` | API | Giới hạn số lần sinh mỗi giờ cho một IP (mặc định 6) |

## 7. Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [docs/finals/README.md](docs/finals/README.md) | Đối chiếu yêu cầu BTC → tính năng → bằng chứng, tự đánh giá |
| [01_AUDIT](docs/finals/01_AUDIT.md) · [02_APQC](docs/finals/02_APQC.md) · [03_BPMN](docs/finals/03_BPMN.md) · [04_USE_CASE](docs/finals/04_USE_CASE.md) | Rà soát, quy trình AS-IS/TO-BE, BPMN 2.0, Use Case |
| [05_QUALITY_ASSURANCE](docs/finals/05_QUALITY_ASSURANCE.md) · [06_EXPERIMENTS](docs/finals/06_EXPERIMENTS.md) · [07_PROVENANCE_COPYRIGHT](docs/finals/07_PROVENANCE_COPYRIGHT.md) | Ba yêu cầu cải tiến |
| [08_KPI](docs/finals/08_KPI.md) · [09_ARCHITECTURE_UI](docs/finals/09_ARCHITECTURE_UI.md) · [10_TEST_REPORT](docs/finals/10_TEST_REPORT.md) · [11_CHANGELOG](docs/finals/11_CHANGELOG.md) | KPI, kiến trúc & giao diện, kiểm thử, thay đổi |

## 8. Trạng thái và việc còn lại

Chỉ ghi số đã đo; phần chưa có dữ liệu ghi là "mục tiêu cần đo" (xem [08_KPI](docs/finals/08_KPI.md)).

- EXP-C đã chạy; **EXP-A, EXP-B chờ máy GPU**.
- **Chưa có phiếu chấm của chuyên gia**: cần ít nhất 3 chuyên gia chấm gói mù EXP-C và hàng đợi thẩm định; đủ ≥ 30 phiếu thì hiệu chỉnh ngưỡng thành QG-1.1 (không sửa đè QG-1.0).
- **Chưa hiện vật nào có giấy phép**: hệ thống đang chặn xuất bản công khai; đã có mẫu thư xin phép.
- 3 ảnh hiện vật bị ngừng dùng; 4 ảnh CC0 thay thế (Wikimedia Commons) đã tải và khớp SHA-1 nhưng **chưa nạp vào danh mục**.
- Cần xác nhận loài chim trên HV01 (chim công hay bạch hạc).
