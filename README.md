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
| 1 | Đánh giá **thiết kế cuối**, không chỉ hoa văn trung gian | Cổng **G2** (hoa văn: rò dáng bình, đường nối) và **G3** (thiết kế cuối: giữ họa tiết PPS, IoU dáng áo, độ nét, giữ chi tiết mịn, lệch màu ΔE); vòng thử lại polish (đổi seed, hạ độ nhiễu, trả bản ghép thô); khoá họa tiết `pattern_lock_v1`; bộ tiêu chí chuyên gia 5 mục chấm mù. Không chỉ số nào tự phê duyệt thiết kế. | `quality/`, `config/quality_gate.json`, `config/expert_rubric.json`, [05](docs/finals/05_QUALITY_ASSURANCE.md) |
| 2 | **Đối chứng có kiểm soát**, nhiều seed, chấm mù | Module thí nghiệm từ chối kế hoạch đổi hơn một yếu tố; EXP-A (trọng số ControlNet, chưa chạy), EXP-B (bước hoàn thiện, 126 lượt), EXP-C (từng bước ghép), EXP-D (nguồn áo nền, 60 lượt), EXP-E (nguồn ảnh nạp, 36 lượt); gói chấm mù; thống kê KTC 95%, hệ số biến thiên, Krippendorff α, Wilcoxon, Friedman | `evaluation/experiment.py`, `evaluation/experiments/`, [06](docs/finals/06_EXPERIMENTS.md) |
| 3 | **Bản quyền, nguồn gốc, truy vết** | Danh mục nguồn schema 2.0; cổng quyền theo 4 mục đích sử dụng; Design Passport có sổ cái băm nối chuỗi, phiên bản có băm cha, chỉnh sửa tay chạy lại G3; nhãn "Thiết kế hỗ trợ bởi AI" trên ảnh xuất | `provenance/`, `data/heritage/metadata.json`, `outputs/passports/`, [07](docs/finals/07_PROVENANCE_COPYRIGHT.md) |

Kết quả bộ demo hiện tại (24 thiết kế, 6 hiện vật × 4 mức sáng tạo, ngày 19/11/2026, đọc từ Passport): G2 đạt 16, cảnh báo 5, loại 3 (cả 3 do đường nối, hiện vật LR3D_124); G3 đạt 14, cảnh báo 10, loại 0; PPS trung bình 0,943; giữ chi tiết mịn trung vị 0,87. Cả 10 cảnh báo G3 do chi tiết mịn dưới 0,85: bản cuối vẫn mất khoảng 13 đến 14% nét mảnh so với bản ghép thô. PPS cao một phần do chính cách làm (khoá họa tiết chép lại nét bản ghép), nên phải chờ chuyên gia chấm mù mới kết luận được bản nào đẹp hơn. Mốc so sánh bản 06/09/2026: G3 đạt 0/24, PPS trung vị 0,36 (số liệu lịch sử, xem [05](docs/finals/05_QUALITY_ASSURANCE.md)).

## 2. Xem nhanh (không cần GPU)

```powershell
uv run python -m http.server 5500 --directory web_ui
```

Mở `http://127.0.0.1:5500`. Giao diện cho người xem có 3 trang: Trang chủ, Studio, Bộ sưu tập. Không có API thì giao diện tự chạy **chế độ ngoại tuyến**, đọc dữ liệu thật đã xuất sẵn trong `web_ui/data/` (bộ demo 24 thiết kế).

## 3. Kiến trúc

```text
 Hiện vật (data/heritage, có nguồn & quyền)
        │  tiêu chí tuyển ảnh C1–C4 · cổng quyền
        ▼
 Mảng hoa văn phẳng đã trải từ mô hình 3D (data/heritage/panels)
        ▼
 GIAI ĐOẠN 1  SD 1.5 + ControlNet Canny (chỉ nét hoa văn) ──► hoa văn phẳng lát liền ──► Cổng G2
        ▼
 Áo dài nền   SD 1.5 + LoRA dáng áo dài sinh mỗi lần chạy, SAM tách vùng áo, kiểm tra áo hợp lệ
        ▼
 GIAI ĐOẠN 2  CLIP chọn bố cục ─► ghép tất định lên áo (chỉ in phần mực, trong vùng áo) ─►
              polish chỉ vùng áo 0,20 + khoá họa tiết ─► vòng thử lại ──► Cổng G3
        ▼
 QC Officer (cảnh báo) ─► Chuyên gia chấm mù ─► Phê duyệt / yêu cầu sửa / loại
        ▼
 Design Passport: tệp + SHA-256, tham số, bước AI/hệ thống/người, phiên bản, phiếu, quyền, nhãn AI
```

| Thành phần | Công nghệ |
|---|---|
| Sinh ảnh | Stable Diffusion 1.5 + ControlNet v1.1 Canny + LoRA dáng áo dài (`diffusers`, `peft`, PyTorch CUDA), SAM (tách vùng áo), CLIP (`transformers`) |
| Xử lý ảnh, phép đo | OpenCV, Pillow, NumPy, scikit-image, SciPy |
| API | FastAPI + Uvicorn (`api/main.py`); PyTorch chỉ nạp khi cần, máy không GPU thì `/generate` trả 503 |
| Giao diện | HTML/CSS/JS thuần (ES modules), không framework; 3 trang cho người xem (Trang chủ, Studio, Bộ sưu tập) |
| Dữ liệu | Tệp JSON/CSV trong repo, không dùng cơ sở dữ liệu |
| Kiểm thử | pytest (249 ca, không cần GPU) |

## 4. Cấu trúc thư mục

```text
.
├── api/                  FastAPI: hiện vật, sinh thiết kế, Passport, QC, thẩm định, chỉnh sửa, xuất bản, thí nghiệm
├── generation/           Pipeline hai giai đoạn (controlnet, pattern, palette, layout_select, garment, garment_lora, garment_sam, streamlit_runner)
├── quality/              Cổng G2/G3, phép đo, khoá họa tiết
├── provenance/           Danh mục nguồn, cổng quyền, Design Passport, băm, nhãn AI
├── evaluation/           Thí nghiệm có kiểm soát (experiment.py, experiments/), thử cách hoàn thiện ảnh (polish_finish_trial)
├── config/               Ngưỡng cổng QG-1.0, tiêu chí tuyển ảnh, bộ tiêu chí chuyên gia (có phiên bản)
├── data/
│   ├── heritage/         Ảnh hiện vật, metadata.json (schema 2.0), sources/ (ứng viên ảnh CC0 thay thế)
│   ├── garment/          Bố cục hoa văn (layouts.json); ảnh áo mẫu cũ chỉ dùng để chạy lại thí nghiệm cũ
│   ├── lora/             Trọng số LoRA dáng áo dài (CC BY-NC 4.0, chỉ dùng phi thương mại)
│   ├── archive/          Siêu dữ liệu schema 1 (đầu vào của bước chuyển đổi)
│   └── prompt_terms.json
├── outputs/
│   ├── runs/             Mỗi lần chạy một thư mục + manifest SHA-256 (bộ demo 24 thiết kế)
│   ├── passports/        24 Design Passport
│   └── experiments/      Kế hoạch và kết quả EXP-A đến EXP-E, gói chấm mù (ảnh thô không đưa vào repo)
├── web_ui/               Giao diện 3 trang: index.html, assets/ (css, js/lib, js/views), data/ (dữ liệu chế độ ngoại tuyến)
├── scripts/              01–04 cài đặt & kiểm GPU · 07 mô tả hoa văn · 08 chuyển schema, trích LR3D · 09 nạp ảnh hiện vật, tạo phần tử
│                         · 10 tạo hiện vật từ LR3D · 11 xuất dữ liệu giao diện, lọc VietFashion · 12 sơ đồ BPMN/Use Case, xuất tập LoRA
│                         · 13 huấn luyện LoRA · 14 sinh bộ demo
├── streamlit_ui/, app.py Công cụ kiểm chứng pipeline nội bộ (Streamlit)
├── tests/                249 ca pytest
├── docs/
│   ├── finals/           Hồ sơ vòng chung kết 01–11 + diagrams/ (BPMN 2.0, Use Case)
│   └── SETUP_AI_LOCAL.md Cài môi trường GPU
├── archive/              Lưu trữ bản 09/2026 (giao diện, đặc tả MVP, smoke test), không thuộc bản chung kết
├── requirements.txt · requirements-dev.txt · pytest.ini · vercel.json
└── README.md
```

## 5. Cài đặt và chạy

Lệnh chạy bằng PowerShell tại thư mục gốc.

**A. Giao diện + API**

```powershell
uv run python -m uvicorn api.main:app --host 127.0.0.1 --port 8000     # cửa sổ 1 (sinh ảnh thật cần GPU)
uv run python -m http.server 5500 --directory web_ui                    # cửa sổ 2
```

Có API ở `127.0.0.1:8000` thì giao diện chạy chế độ trực tiếp; không có thì chạy ngoại tuyến. Môi trường Python do `uv` quản lý ở thư mục `.venv`; mọi lệnh Python chạy qua `uv run`.

**B. Kiểm thử**

```powershell
uv run pytest     # 249 ca; không cần GPU (1 ca dành cho máy không có PyTorch nên bị bỏ qua trên máy có GPU)
```

**C. Sinh ảnh và thí nghiệm (cần GPU NVIDIA ≥ 6 GB, xem [`docs/SETUP_AI_LOCAL.md`](docs/SETUP_AI_LOCAL.md))**

```powershell
uv run python scripts/03_download_models.py                                  # tải SD 1.5 và ControlNet; CLIP và SAM tự tải lần đầu khi chạy
uv run python scripts/14_generate_demo_set.py                                # sinh bộ demo (khoảng 15 phút); thêm mã hiện vật để chạy riêng một vật
uv run python scripts/11_export_demo_data.py                                 # cập nhật web_ui/data cho chế độ ngoại tuyến
uv run python -m evaluation.experiment run evaluation/experiments/EXP-A_controlnet_weight.json   # chưa chạy, 120 lượt
```

Trọng số LoRA có sẵn ở `data/lora/aodai_r16_512/`; huấn luyện lại bằng `scripts/13_train_lora.py`.

**D. Nạp ảnh hiện vật mới** (kiểm SHA-1, tách nền, chấm C1–C4, ghi ở trạng thái chờ rà soát)

```powershell
uv run python scripts/09_ingest_heritage_image.py --file <ảnh> --candidate <mã Commons> --heritage-id <mã> --name "<tên>" --dry-run
```

**E. Công cụ kiểm chứng nội bộ:** `uv run streamlit run app.py`

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

- Đã chạy: EXP-B (126 lượt), EXP-C (24), EXP-D (60), EXP-E (36). **EXP-A (120 lượt) chưa chạy.**
- **Chưa có phiếu chấm của người thật:** cần ít nhất một người am hiểu di sản và một người am hiểu thiết kế xem mẫu và điền phiếu; gói chấm mù EXP-D cần ít nhất 3 người chấm; đủ ≥ 30 phiếu thì hiệu chỉnh ngưỡng thành QG-1.1 (không sửa đè QG-1.0).
- **Chưa hiện vật nào có giấy phép từng vật (0/6):** 6 hiện vật LR3D-CULT2 thuộc bộ dữ liệu công bố CC BY 4.0 nhưng từng vật có thể lấy từ nguồn giấy phép học thuật; hệ thống đang chặn xuất bản công khai; đã có mẫu thư xin phép, chưa gửi.
- **LoRA học từ VietFashion (CC BY-NC 4.0):** chỉ dùng phi thương mại, phải ghi công bài ICMR 2026 (xem `data/lora/README.md`).
- 3 thiết kế của hiện vật LR3D_124 bị G2 loại (đường nối), hệ thống chưa tự sinh lại hoa văn.
- Giao diện web chỉ còn 3 trang; Passport và chỉ số chất lượng đọc qua API và tệp dữ liệu, không hiện trên web.
- Bản cuối vẫn mất khoảng 13 đến 14% chi tiết mịn so với bản ghép thô; nếu cần giữ tuyệt đối có thể bỏ polish và dùng bản ghép.
