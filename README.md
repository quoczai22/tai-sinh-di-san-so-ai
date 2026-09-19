# Tái Sinh Di Sản Số

> Từ hoa văn gốm Bát Tràng đến áo dài đương đại — hệ thống tự sinh một bộ 4 thiết kế mỗi lần bấm nút, kèm chỉ số đo lường và nhật ký truy vết, để con người chọn.

Bài dự thi **Cuộc thi Sáng tạo trẻ Quốc gia về AI năm 2026** (Trung ương Đoàn TNCS Hồ Chí Minh, Bảng C, `ai.tainangviet.vn`), đội thi 3 người (AI/Data Engineer · DevOps/Software Engineer · BA).

## Mục lục

1. [Vấn đề và mục tiêu](#1-vấn-đề-và-mục-tiêu)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Đóng góp kỹ thuật](#3-đóng-góp-kỹ-thuật)
4. [Cấu trúc thư mục](#4-cấu-trúc-thư-mục)
5. [Cài đặt môi trường](#5-cài-đặt-môi-trường)
6. [Chạy dự án](#6-chạy-dự-án)

---

## 1. Vấn đề và mục tiêu

Người trẻ muốn đưa hoa văn di sản (mở đầu bằng gốm Bát Tràng) vào thiết kế hiện đại, nhưng hai cách làm phổ biến đều có vấn đề:

- Chép nguyên hoa văn lên sản phẩm → không có tính sáng tạo.
- Để mô hình sinh ảnh tự do "diễn giải" di sản → mất kiểm soát về hình dáng sản phẩm, không đo lường và không tái lập được kết quả.

**Mục tiêu:** xây dựng một pipeline đưa hoa văn gốm Bát Tràng lên áo dài Việt Nam sao cho:

- **Dáng trang phục luôn đúng** — không phụ thuộc việc mô hình sinh ảnh "có vẽ đúng áo dài hay không".
- **Độ trung thành với hoa văn gốc đo được** bằng chỉ số so sánh, không chỉ đánh giá bằng mắt.
- **Toàn bộ tham số sinh ảnh tái lập và truy vết được** — mỗi lần sinh ảnh đều ghi lại đầy đủ để xem lại, đối chiếu.

## 2. Kiến trúc hệ thống

Hệ thống gồm hai lớp: **Generation Layer** (sinh thiết kế) và **Assessment Layer** (đo lường & minh bạch).

```text
┌───────────────────────────────────────────────────────────┐
│                     GENERATION LAYER                        │
│                                                              │
│  GIAI ĐOẠN 1 — SINH HOA VĂN PHẲNG                            │
│  ảnh gốm ─► tách nền, Canny CHỈ GIỮ HOA VĂN (bỏ đường bao     │
│  món đồ) ─► SD1.5 + ControlNet (4 mức Creative Intensity     │
│  điều tiết mức biến tấu) ─► hoa văn lặp liền mạch             │
│                          ↓                                   │
│  GIAI ĐOẠN 2 — ĐƯA LÊN ÁO DÀI                                │
│  chấm điểm 7 bố cục bằng CLIP, tự chọn bố cục hợp nhất ─►     │
│  ghép ảnh TẤT ĐỊNH lên ảnh áo dài mẫu (mask mềm +             │
│  displacement + shading) ─► lượt hoàn thiện img2img ─►        │
│  4 THIẾT KẾ ÁO DÀI                                            │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌───────────────────────────────────────────────────────────┐
│                     ASSESSMENT LAYER                         │
│  Visual Similarity (CLIP) · Design Passport (×4) · Audit Log │
└───────────────────────────────────────────────────────────┘
```

**Luồng dùng:** người dùng chọn một hiện vật gốm, bấm **một nút duy nhất** — hệ thống tự sinh cả 4 thiết kế (khác mức biến tấu hoa văn, bảng màu, bố cục do hệ thống tự chấm điểm chọn). Mỗi thiết kế hiển thị kèm một **Design Passport** riêng (hoa văn nguồn, bố cục, chỉ số Similarity tham khảo). Người dùng xem cả 4 và chọn thiết kế ưng ý; lựa chọn đó được ghi vào **Audit Log**.

**Vì sao tách hai giai đoạn sinh:** đưa thẳng ảnh gốm vào ControlNet trong khi prompt yêu cầu vẽ áo dài tạo ra xung đột hình học — bản đồ Canny mô tả dáng vật chứa (bình, cổ hẹp, đế tròn) còn prompt mô tả trang phục (tà dài, mặc ngoài quần). Giải pháp: giai đoạn 1 chỉ sinh hoa văn phẳng, không nhắc gì tới sản phẩm đầu ra; giai đoạn 2 ghép hoa văn lên áo dài bằng phép ghép ảnh **tất định** (không dùng model sinh ảnh để vẽ lại dáng áo), nên hình dáng trang phục luôn đúng bất kể Stable Diffusion sinh ra hoa văn thế nào.

### Tech stack

| Thành phần | Công nghệ | Vai trò trong hệ thống |
|---|---|---|
| Model sinh ảnh | Stable Diffusion 1.5 (`diffusers`) + ControlNet v1.1 Canny | Sinh hoa văn phẳng có điều kiện cấu trúc lấy từ ảnh gốm |
| Scheduler | `UniPCMultistepScheduler` | Giữ chất lượng ảnh ở số bước suy luận thấp, chạy nhanh trên GPU laptop |
| Runtime AI | PyTorch + CUDA (`torch`, `torchvision`) | Chạy inference trên GPU local, quản lý VRAM (attention/VAE slicing, giải phóng cache giữa các lần sinh) |
| Đánh giá thị giác | CLIP (`transformers`) | Đo Visual Similarity giữa hoa văn sinh ra và hoa văn gốc; chấm điểm 7 bố cục để tự chọn bố cục hợp nhất |
| Xử lý ảnh | OpenCV, Pillow, NumPy | Trích Canny edge chỉ giữ hoa văn, tách nền/alpha mask, ghép ảnh tất định (mask mềm, displacement, shading), khớp bảng màu bằng thống kê không gian LAB |
| Backend API | FastAPI + Uvicorn | Bridge giữa Web UI tĩnh và pipeline PyTorch: liệt kê hiện vật, chạy job sinh ảnh nền, phục vụ media, ghi audit event |
| UI kiểm chứng nội bộ | Streamlit | Giao diện chạy pipeline trực tiếp bằng dữ liệu hiện vật thật |
| UI trình diễn công khai | HTML/CSS/JS thuần, component loader tự viết | Frontend trình diễn sản phẩm |
| Trích xuất tư liệu | `pdfplumber` | Đọc PDF tư liệu nghiên cứu Bát Tràng |
| Mô tả hoa văn (offline) | Google Gemini API | Sinh mô tả tiếng Anh ngắn cho hoa văn — chạy một lần offline, không nằm trong luồng runtime của pipeline sinh ảnh |
| Lưu trữ dữ liệu | File JSON/CSV tĩnh | Không dùng database — metadata hiện vật, mô tả hoa văn, log thực nghiệm và audit log đều là file trong repo |
| Cấu hình môi trường | `python-dotenv` + file `.env` | Quản lý model id, API key, biến môi trường theo máy |
| Deploy frontend | Vercel | Host Web UI tĩnh |
| Dev tooling | VS Code `launch.json`/`tasks.json`, script PowerShell | Khởi động nhanh hai chế độ chạy, tự chọn kênh CUDA phù hợp máy khi cài đặt |

## 3. Đóng góp kỹ thuật

1. **Tách hai giai đoạn sinh** — gỡ xung đột hình học giữa điều kiện cấu trúc (Canny của vật thể gốc) và sản phẩm đầu ra (trang phục), thay vì cố "hoà giải" bằng cách chỉnh một tham số duy nhất.
2. **Conditioning chỉ trên hoa văn** — bóc đường bao hình dáng hiện vật (bình, lư hương...) khỏi bản đồ Canny trước khi đưa vào ControlNet, để ControlNet chỉ giữ cấu trúc hoa văn chứ không giữ luôn hình dáng vật chứa.
3. **Sinh tile lặp liền mạch bằng circular padding** ở bước hậu xử lý ảnh sinh ra, cho phép hoa văn lặp lại tự nhiên khi phủ lên bề mặt vải.
4. **Tự động chọn bố cục bằng CLIP** — chấm điểm 7 phương án bố trí hoa văn trên áo dài, thay vì chạy lại Stable Diffusion cho từng phương án.
5. **Ghép ảnh tất định ở giai đoạn 2** — mask mềm, displacement, shading và color grade thay vì mô hình sinh ảnh để đặt hoa văn lên áo dài, đảm bảo dáng trang phục luôn đúng và kết quả tái lập được.
6. **Khớp bảng màu tất định bằng thống kê LAB** — cho phép có một biến thể trung thành màu sắc với hiện vật gốc mà không cần ép màu qua prompt.
7. **Ràng buộc ngân sách token cho prompt** — mô tả hoa văn được giới hạn theo đúng tokenizer của SD1.5, tránh bị cắt bớt nội dung ở giới hạn token của CLIP.
8. **Audit Log + Design Passport** — mỗi lần sinh ảnh ghi lại đầy đủ tham số (mức biến tấu, bảng màu, bố cục, seed, prompt, thời gian chạy, hash ảnh đầu ra) và lựa chọn cuối cùng của người dùng, phục vụ khả năng truy vết và tái lập.

Mọi mô tả hiện vật hiển thị cho người dùng là nội dung do nhóm biên soạn, không phải trích dẫn học thuật; mọi ảnh hiện vật ghi trung thực trạng thái giấy phép cho tới khi xác minh được nguồn.

## 4. Cấu trúc thư mục

```text
.
├── app.py                    # Điểm vào Streamlit — UI kiểm chứng pipeline nội bộ
├── api/
│   ├── main.py                 # FastAPI: /heritage, /generate (job GPU nền), /audit, /media/*
│   ├── audit.py                 # Ghi audit event ra outputs/audit/audit.jsonl (append-only)
│   └── README.md                # Hướng dẫn chạy API bridge cho web_ui
├── generation/                 # Generation Layer — lõi kỹ thuật của dự án
│   ├── controlnet.py             # Tách nền, alpha mask, Canny CHỈ giữ hoa văn
│   ├── prompt_template.py        # Prompt giai đoạn 1, kiểm ngân sách token
│   ├── pattern.py                  # GIAI ĐOẠN 1 — sinh hoa văn phẳng, 4 mức Creative Intensity
│   ├── palette.py                   # Khớp bảng màu hiện vật gốc bằng thống kê LAB (tất định)
│   ├── layout_select.py              # Chấm điểm 7 bố cục bằng CLIP, tự chọn bố cục hợp nhất
│   ├── garment.py                     # GIAI ĐOẠN 2 — ghép hoa văn lên áo dài (tất định, không SD)
│   ├── stable_diffusion.py             # Wrapper SD1.5 + ControlNet, quản lý VRAM
│   └── streamlit_runner.py              # Điều phối end-to-end: generate_design_set(heritage_id)
├── evaluation/                  # Script đo lường/thực nghiệm dựa trên pipeline ở generation/
│   ├── variants.py
│   └── intensity_sweep.py
├── scripts/
│   ├── 01_setup_env.ps1          # Cài PyTorch đúng kênh CUDA + dependencies
│   ├── 02_check_gpu.py            # Xác nhận torch.cuda.is_available()
│   ├── 03_download_models.py       # Tải SD1.5 + ControlNet (fp16)
│   ├── 04_test_controlnet.py        # Smoke test pipeline, sinh ảnh tham chiếu ở outputs/
│   └── 07_describe_heritage.py       # LLM thị giác viết mô tả hoa văn — CHẠY OFFLINE 1 LẦN
├── streamlit_ui/                # Views/session cho app.py
│   ├── heritage_data.py           # Đọc + kiểm tra data/heritage/metadata.json
│   ├── session.py
│   └── views.py
├── web_ui/                      # Frontend tĩnh (HTML/CSS/JS thuần) cho bản trình diễn công khai
│   ├── index.html
│   ├── components/                # layout/, sections/, overlays/ — nạp bằng component-loader.js
│   ├── assets/                     # css/js/images/fonts
│   └── DEPLOY.md                   # Hướng dẫn deploy Vercel
├── data/
│   ├── heritage/                  # Ảnh hiện vật + metadata.json (Heritage Dataset)
│   ├── garment/                     # Ảnh áo dài mẫu + layouts.json (toạ độ vùng bố cục)
│   ├── documents/                    # PDF tư liệu nghiên cứu (không commit nội dung, chỉ .gitkeep)
│   └── prompt_terms.json             # Mô tả tiếng Anh ngắn cho từng hiện vật, dùng ở giai đoạn 1
├── docs/
│   ├── mvp_spec.md               # Đặc tả kỹ thuật của pipeline
│   ├── SETUP_AI_LOCAL.md           # Hướng dẫn cài môi trường AI local chi tiết
│   └── evidence/                    # Ảnh minh hoạ kết quả pipeline
├── outputs/                     # Ảnh sinh ra + audit.jsonl (gitignored)
├── requirements.txt
└── vercel.json                  # Cấu hình deploy web_ui tĩnh lên Vercel
```

## 5. Cài đặt môi trường

Yêu cầu tối thiểu: GPU NVIDIA ≥6GB VRAM, driver hỗ trợ CUDA ≥12.1, Python 3.10/3.11, ~12GB dung lượng trống. Hướng dẫn đầy đủ (chuyển cache sang ổ khác, chọn kênh CUDA theo GPU, xử lý sự cố) nằm ở [`docs/SETUP_AI_LOCAL.md`](docs/SETUP_AI_LOCAL.md). Tóm tắt 4 bước, chạy PowerShell tại thư mục gốc:

```powershell
# 1. Cài môi trường (PyTorch đúng kênh CUDA + dependencies)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m venv venv
.\scripts\01_setup_env.ps1

# 2. Xác nhận PyTorch thấy GPU
.\venv\Scripts\Activate.ps1
python scripts/02_check_gpu.py

# 3. Tải model (chỉ bản fp16: SD1.5 + ControlNet Canny v1.1)
python scripts/03_download_models.py

# 4. Smoke test pipeline
python scripts/04_test_controlnet.py
```

Tạo file `.env` ở thư mục gốc (không commit) với các biến sau:

| Biến | Bắt buộc cho | Ghi chú |
|---|---|---|
| `HF_HOME` | Tải model | Tuỳ chọn — không set thì dùng cache mặc định của `huggingface_hub` |
| `SD15_MODEL_ID` | Pipeline sinh ảnh | Id repo Stable Diffusion 1.5 dùng chung cho mọi lần chạy |
| `CONTROLNET_CANNY_ID` | Pipeline sinh ảnh | Id repo ControlNet Canny v1.1 |
| `GEMINI_API_KEY` | Chỉ `scripts/07_describe_heritage.py` | Chạy offline một lần, không dùng ở runtime |
| `WEB_UI_ORIGINS` | `api/main.py` khi deploy | Danh sách domain frontend được phép gọi API, phân tách bằng dấu phẩy |

## 6. Chạy dự án

Hai cách chạy, tương ứng hai cấu hình trong `.vscode/launch.json`:

**A. Streamlit — UI kiểm chứng pipeline (dành cho dev/nội bộ)**

```powershell
streamlit run app.py --server.headless=true --server.port=8501
```

**B. Web UI tĩnh + FastAPI — bản trình diễn công khai**

```powershell
# Terminal 1: API (job GPU chạy nền, audit log, media hiện vật/thiết kế)
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000

# Terminal 2: frontend tĩnh
python -m http.server 5500 --directory web_ui
```

Sau đó mở `http://127.0.0.1:5500`. Trong VS Code, hai cấu hình debug **"Tái sinh: Web UI + API"** và **"Streamlit: Tái sinh Di sản Số"** trong `launch.json` tự khởi động đủ tiến trình cần thiết (kể cả task reset port trước khi chạy).

Deploy `web_ui` lên Vercel: xem [`web_ui/DEPLOY.md`](web_ui/DEPLOY.md) — `vercel.json` đã cấu hình rewrite `/` → `web_ui/index.html`; khi có domain API GPU production, trỏ `window.DH_API_BASE` trong `web_ui/assets/js/config.js` sang domain đó.
