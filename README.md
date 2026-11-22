# Tái Sinh Di Sản Số

> Hoa văn gốm Bát Tràng, dệt lại thành áo dài — có kiểm định chất lượng, thí nghiệm có đối chứng và hồ sơ truy vết cho từng thiết kế.

Bài dự thi **vòng chung kết** Cuộc thi Sáng tạo trẻ Quốc gia về Trí tuệ nhân tạo 2026, Bảng C — nhóm *3 chàng hiệp sĩ mộng mơ*.
Hồ sơ vòng chung kết nằm ở [`docs/finals/`](docs/finals/README.md).

## Mục lục

1. [Xem nhanh (không cần GPU)](#1-xem-nhanh-không-cần-gpu)
2. [Kiến trúc](#2-kiến-trúc)
3. [Cấu trúc thư mục](#3-cấu-trúc-thư-mục)
4. [Cài đặt và chạy](#4-cài-đặt-và-chạy)
5. [Biến môi trường](#5-biến-môi-trường)
6. [Tài liệu](#6-tài-liệu)
7. [Trạng thái và việc còn lại](#7-trạng-thái-và-việc-còn-lại)

---

## 1. Xem nhanh (không cần GPU)

```powershell
uv run python -m http.server 5500 --directory web_ui
```

Mở `http://127.0.0.1:5500`. Giao diện cho người xem có 3 trang: Trang chủ, Studio (chọn hiện vật) và Kết quả (4 tà áo). Không có API thì giao diện tự chạy **chế độ ngoại tuyến**, đọc dữ liệu thật đã xuất sẵn trong `web_ui/data/` (bộ demo 24 thiết kế).

## 2. Kiến trúc

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
| API | FastAPI + Uvicorn (`tsds/api/main.py`); PyTorch chỉ nạp khi cần, máy không GPU thì `/generate` trả 503 |
| Giao diện | HTML/CSS/JS thuần (ES modules), không framework; 3 trang cho người xem (Trang chủ, Studio, Kết quả) |
| Dữ liệu | Tệp JSON/CSV trong repo, không dùng cơ sở dữ liệu |
| Kiểm thử | pytest (359 ca, không cần GPU) |

## 3. Cấu trúc thư mục

```text
.
├── tsds/                 Gói Python duy nhất của dự án (import: from tsds.generation.pattern import controlnet)
│   ├── core/             Tầng thấp nhất, không import gói nào khác: paths.py (mọi đường dẫn), align.py, pattern_lock.py (khoá họa tiết)
│   ├── generation/       Sinh ảnh. stable_diffusion (nạp Stable Diffusion) và prompt_template (prompt hoa văn và áo) dùng chung cho cả hai giai đoạn, nằm ngay ở đây
│   │   ├── pattern/      Giai đoạn 1, hoa văn: pattern, controlnet, palette, elements, element_library
│   │   └── garment/      Giai đoạn 2, áo: garment (ghép, hoàn thiện), garment_lora (áo nền), garment_sam (tách vùng áo), layout_select (chọn bố cục)
│   ├── quality/          Cổng G2/G3, phép đo, thử lại
│   ├── provenance/       Danh mục nguồn, cổng quyền, Design Passport, băm, nhãn AI
│   ├── evaluation/       Thí nghiệm có kiểm soát (experiment.py, experiments/), thử cách hoàn thiện ảnh (polish_finish_trial)
│   ├── pipeline/         run.py: điều phối end-to-end một lần sinh (generate_design_set)
│   ├── api/              FastAPI: hiện vật, sinh thiết kế, Passport, QC, thẩm định, chỉnh sửa, xuất bản, thí nghiệm
│   └── streamlit_ui/     Công cụ kiểm chứng pipeline nội bộ (Streamlit; app.py ở gốc chỉ gọi tsds/streamlit_ui/app.py)
├── config/               Ngưỡng cổng QG-1.0, tiêu chí tuyển ảnh, bộ tiêu chí chuyên gia (có phiên bản)
├── data/
│   ├── heritage/         Ảnh hiện vật, metadata.json (schema 2.0), sources/ (ứng viên ảnh CC0 thay thế)
│   ├── garment/          Bố cục hoa văn (layouts.json); ảnh áo mẫu cũ chỉ dùng để chạy lại thí nghiệm cũ
│   ├── lora/             Trọng số LoRA dáng áo dài (CC BY-NC 4.0, chỉ dùng phi thương mại)
│   ├── raw/              Dữ liệu gốc thô, không commit: lr3d_src/ (mô hình LR3D-CULT2), vietfashion/, file zip tải về
│   └── prompt_terms.json
├── outputs/
│   ├── runs/             Mỗi lần chạy một thư mục + manifest SHA-256 (bộ demo 24 thiết kế)
│   ├── passports/        24 Design Passport
│   ├── experiments/      Kế hoạch và kết quả EXP-A đến EXP-G (ảnh thô không đưa vào repo)
│   ├── review/           Gói chấm mù gửi người đánh giá (blind_review*), không commit
│   ├── logs/             Nhật ký các lần chạy thí nghiệm và sinh demo, không commit
│   └── archive/          Bản lưu cũ (ví dụ Passport của lượt sinh trước)
├── web_ui/               Giao diện 3 trang: index.html, assets/ (css, js/lib, js/views), data/ (dữ liệu chế độ ngoại tuyến)
├── scripts/              Chia theo mục đích (chạy từ gốc repo: uv run python scripts/<nhóm>/<tên>.py)
│   ├── setup/            Cài môi trường, kiểm GPU, tải mô hình, thử nhanh ControlNet
│   ├── data_prep/        Chuẩn bị dữ liệu: mô tả hoa văn, trích LR3D, nạp ảnh, tạo hiện vật, lọc VietFashion, xuất tập LoRA, tách nền
│   ├── train/            Huấn luyện LoRA dáng áo dài
│   ├── demo/             Sinh bộ demo (generate_demo_set) và xuất dữ liệu cho web_ui (export_demo_data)
│   ├── web/              Phát hành giao diện: ui_index (index.html), xuất và nén mô hình 3D
│   ├── docs/             Dựng sơ đồ BPMN và Use Case
│   ├── eval/             Gói chấm mù, đo tốc độ sinh, đo backend
│   └── deploy/           Gói Hugging Face Space, cổng thử nghiệm cục bộ
├── app.py                Điểm chạy Streamlit nội bộ (streamlit run app.py)
├── tests/                Ca pytest; manual/ là các script kiểm thử chạy tay (không thuộc pytest)
├── docs/
│   ├── finals/           Hồ sơ vòng chung kết 01–11 + diagrams/ (BPMN 2.0, Use Case)
│   └── SETUP_AI_LOCAL.md Cài môi trường GPU
├── archive/              Lưu trữ bản 09/2026 (giao diện, đặc tả MVP, smoke test), không thuộc bản chung kết
├── pyproject.toml · uv.lock · requirements-api.txt (chỉ cho ảnh Docker) · pytest.ini · vercel.json
└── README.md
```

**Phân tầng import** (tầng dưới không được import ngược lên tầng trên; `tests/test_layering.py` kiểm tra tự động, kể cả import đặt trong hàm):
`tsds.core` < `tsds.generation` < `tsds.quality` < `tsds.provenance` < `tsds.evaluation` < `tsds.pipeline` < `tsds.api`, `tsds.streamlit_ui`.
Mã Python nằm hết trong `tsds/` nên `Dockerfile` và `COPY_DIRS` của `scripts/deploy/build_hf_space.py` chỉ cần `tsds/`, `config/`, `data/` (`tests/test_deploy_files.py` kiểm tra). Thư viện khai báo trong `pyproject.toml` (cài bằng `uv sync`); `requirements-api.txt` chỉ dành cho ảnh Docker.

## 4. Cài đặt và chạy

Lệnh chạy bằng PowerShell tại thư mục gốc.

**A. Giao diện + API**

```powershell
uv run python -m uvicorn tsds.api.main:app --host 127.0.0.1 --port 8000     # cửa sổ 1 (sinh ảnh thật cần GPU)
uv run python -m http.server 5500 --directory web_ui                    # cửa sổ 2
```

Có API ở `127.0.0.1:8000` thì giao diện chạy chế độ trực tiếp; không có thì chạy ngoại tuyến. Môi trường Python do `uv` quản lý ở thư mục `.venv`; mọi lệnh Python chạy qua `uv run`.

**B. Kiểm thử**

```powershell
uv run pytest     # 359 ca; không cần GPU (1 ca dành cho máy không có PyTorch nên bị bỏ qua trên máy có GPU)
```

**C. Sinh ảnh và thí nghiệm (cần GPU NVIDIA ≥ 6 GB, xem [`docs/SETUP_AI_LOCAL.md`](docs/SETUP_AI_LOCAL.md))**

```powershell
uv run python scripts/setup/download_models.py                                  # tải SD 1.5 và ControlNet; CLIP và SAM tự tải lần đầu khi chạy
uv run python scripts/demo/generate_demo_set.py                                # sinh bộ demo (khoảng 15 phút); thêm mã hiện vật để chạy riêng một vật
uv run python scripts/eval/build_blind_review.py                              # dựng gói đánh giá mù 24 thiết kế (trang HTML phiếu chấm + khóa giải mã riêng) vào outputs/review/blind_review/
uv run python scripts/data_prep/cutout_heritage.py                                  # tách nền ảnh 6 hiện vật (SAM) thành PNG trong suốt, chỉ dùng để hiển thị
uv run python scripts/web/export_heritage_glb.py                              # nén mô hình 3D 6 hiện vật thành GLB nhẹ cho khung xoay 360 độ ở trang Studio
uv run python scripts/demo/export_demo_data.py                                 # cập nhật web_ui/data cho chế độ ngoại tuyến
uv run python -m tsds.evaluation.experiment run tsds/evaluation/experiments/EXP-A_controlnet_weight.json   # chưa chạy, 120 lượt
```

Trọng số LoRA có sẵn ở `data/lora/aodai_r16_512/`; huấn luyện lại bằng `scripts/train/train_lora.py`.

**D. Nạp ảnh hiện vật mới** (kiểm SHA-1, tách nền, chấm C1–C4, ghi ở trạng thái chờ rà soát)

```powershell
uv run python scripts/data_prep/ingest_heritage_image.py --file <ảnh> --candidate <mã Commons> --heritage-id <mã> --name "<tên>" --dry-run
```

**E. Công cụ kiểm chứng nội bộ:** `uv run streamlit run app.py`

**Triển khai giao diện:** Project Vercel `tai-sinh-di-san-so-ai` đã nối với GitHub, theo dõi `main` và dùng Root Directory `web_ui`. Push lên `main` tự tạo production deployment tại `https://tai-sinh-di-san-so-ai.vercel.app/`; không cần chạy `vercel deploy --prod` thêm. Pull request và push lên `main` có kiểm thử giao diện trong `.github/workflows/web-ui.yml`. Vercel triển khai độc lập với kết quả kiểm thử, vì vậy cần xem trạng thái CI trước khi merge. Khi có API GPU công khai, đặt `window.DH_API_BASE` trong `web_ui/assets/js/config.js`. Mỗi lần phát hành giao diện, chạy `python scripts/web/ui_index.py finals-N` để đổi phiên bản ở mọi thẻ CSS, script và import map (trình duyệt không dùng lại tệp cũ). Cấu trúc thư mục giao diện: `docs/UI_ARCHITECTURE.md`.

## 5. Biến môi trường

Đặt trong tệp `.env` ở thư mục gốc (không commit).

| Biến | Dùng cho | Ghi chú |
|---|---|---|
| `HF_HOME` | Tải model | Tuỳ chọn |
| `SD15_MODEL_ID`, `CONTROLNET_CANNY_ID` | Pipeline sinh ảnh | Id repo model |
| `GEMINI_API_KEY` | Chỉ `scripts/data_prep/describe_heritage.py` | Chạy offline một lần |
| `WEB_UI_ORIGINS` | API khi triển khai | Danh sách domain giao diện, phân tách bằng dấu phẩy |
| `TSDS_WRITE_KEY` | API khi chạy công khai | Thao tác ghi phải gửi header `X-API-Key` |
| `TSDS_GENERATE_PER_HOUR` | API | Giới hạn số lần sinh mỗi giờ cho một IP (mặc định 6) |

## 6. Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [docs/finals/README.md](docs/finals/README.md) | Đối chiếu yêu cầu BTC → tính năng → bằng chứng, tự đánh giá |
| [01_AUDIT](docs/finals/01_AUDIT.md) · [02_APQC](docs/finals/02_APQC.md) · [03_BPMN](docs/finals/03_BPMN.md) · [04_USE_CASE](docs/finals/04_USE_CASE.md) | Rà soát, quy trình AS-IS/TO-BE, BPMN 2.0, Use Case |
| [05_QUALITY_ASSURANCE](docs/finals/05_QUALITY_ASSURANCE.md) · [06_EXPERIMENTS](docs/finals/06_EXPERIMENTS.md) · [07_PROVENANCE_COPYRIGHT](docs/finals/07_PROVENANCE_COPYRIGHT.md) | Ba yêu cầu cải tiến |
| [08_KPI](docs/finals/08_KPI.md) · [09_ARCHITECTURE_UI](docs/finals/09_ARCHITECTURE_UI.md) · [10_TEST_REPORT](docs/finals/10_TEST_REPORT.md) · [11_CHANGELOG](docs/finals/11_CHANGELOG.md) | KPI, kiến trúc & giao diện, kiểm thử, thay đổi |

## 7. Trạng thái và việc còn lại

Yêu cầu cải tiến của ban tổ chức, minh chứng và link thử nghiệm: [`docs/cac_yeu_cau_cai_tien.md`](docs/cac_yeu_cau_cai_tien.md).

Chỉ ghi số đã đo; phần chưa có dữ liệu ghi là "mục tiêu cần đo" (xem [08_KPI](docs/finals/08_KPI.md)).

- Đã chạy: EXP-A (120 lượt, 5 seed), EXP-B (126), EXP-D (60), EXP-E (36), EXP-F (36), EXP-G (90). Kết quả: `docs/finals/06_EXPERIMENTS.md`. Chưa thí nghiệm nào có chấm mù của người thật.
- **Chưa có phiếu chấm của người thật:** cần ít nhất một người am hiểu di sản và một người am hiểu thiết kế xem mẫu và điền phiếu; gói chấm mù EXP-D cần ít nhất 3 người chấm; đủ ≥ 30 phiếu thì hiệu chỉnh ngưỡng thành QG-1.1 (không sửa đè QG-1.0).
- **Giấy phép ảnh nguồn:** 6 hiện vật LR3D-CULT2 ghi CC BY 4.0 (giấy phép công bố của bộ dữ liệu, xác nhận 21/11/2026) kèm ghi công tác giả. Nhóm chưa xác minh riêng nguồn của từng vật (một phần mô hình trong bộ có thể lấy từ Sketchfab theo giấy phép học thuật). Xem `docs/DANH_MUC_NGUON_HIEN_VAT.md`.
- **LoRA học từ VietFashion (CC BY-NC 4.0):** chỉ dùng phi thương mại, phải ghi công bài ICMR 2026 (xem `data/lora/README.md`).
- Hiện vật LR3D_124 hay bị G2 loại vì đường nối (3 trong 4 thiết kế ở bộ demo). Vòng sinh lại bằng đổi seed chỉ cứu được một phần (thử thật: 1 trong 3), xem `docs/finals/05_QUALITY_ASSURANCE.md`.
- Giao diện web chỉ còn 3 trang; Passport và chỉ số chất lượng đọc qua API và tệp dữ liệu, không hiện trên web.
- Bản cuối vẫn mất khoảng 13 đến 14% chi tiết mịn so với bản ghép thô; nếu cần giữ tuyệt đối có thể bỏ polish và dùng bản ghép.
