# Setup môi trường AI local — SD1.5 + ControlNet

> Timeline Ngày 2 · Member 1 (AI/Computer Vision)

## Yêu cầu tối thiểu

| Hạng mục | Yêu cầu |
|---|---|
| GPU | NVIDIA, **≥ 6 GB VRAM** (đã kiểm chứng trên RTX 4060 Laptop 8 GB) |
| Driver | Hỗ trợ CUDA ≥ 12.1 — kiểm tra bằng `nvidia-smi` |
| Python | 3.10 hoặc 3.11 |
| Dung lượng trống | **~12 GB** (torch ~3 GB + wheel giải nén tạm ~5 GB + model ~3.5 GB) |
| OS | Windows 10/11 (script `.ps1`); trên Linux dùng lệnh pip tương đương |

## Chạy 4 bước

Mở **PowerShell** tại thư mục gốc project:

```powershell
# 1. Cài môi trường (~10 phút, tải ~3GB)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m venv venv                    # bỏ qua nếu venv đã có
.\scripts\01_setup_env.ps1

# 2. Xác nhận PyTorch thấy GPU
.\venv\Scripts\Activate.ps1
python scripts/02_check_gpu.py

# 3. Tải model (~3.5GB, chỉ bản fp16)
python scripts/03_download_models.py

# 4. Smoke test pipeline
python scripts/04_test_controlnet.py
```

Kết quả mong đợi ở bước 4: 4 ảnh trong `outputs/`.

Số đo tham chiếu trên RTX 4060 Laptop 8 GB (512×512, 25 steps, UniPC):

| Chỉ số | Giá trị |
|---|---|
| Peak VRAM | **3,33 GB** |
| Thời gian / ảnh | **5,6 – 7,0 giây** (~4,7 it/s) |
| Tái lập | 4 ảnh trùng khít SHA256 giữa 2 lần chạy cùng seed |

Nếu máy bạn lệch nhiều so với bảng này thì nên xem lại cấu hình trước khi đi tiếp.

## Nếu ổ hệ thống của bạn sắp đầy

Ba thứ này **luôn** ghi vào ổ hệ thống, bất kể project nằm ở đâu:

| Thứ | Vị trí mặc định | Kích thước |
|---|---|---|
| pip cache (wheel đã tải) | `%LOCALAPPDATA%\pip\Cache` | wheel torch CUDA ~2.5 GB |
| Thư mục tạm khi pip giải nén wheel | `%LOCALAPPDATA%\Temp` | ~5 GB, giải phóng sau khi cài |
| HuggingFace cache (model) | `%USERPROFILE%\.cache\huggingface` | ~3.5 GB |

**Mặc định `01_setup_env.ps1` không đổi gì cả** — nó chỉ báo dung lượng còn trống
và cảnh báo nếu thiếu chỗ. Muốn chuyển sang ổ khác thì truyền tham số:

```powershell
.\scripts\01_setup_env.ps1 -ModelRoot "E:\AI_Models"            # chỉ phiên này
.\scripts\01_setup_env.ps1 -ModelRoot "E:\AI_Models" -Persist   # nhớ vĩnh viễn
```

`-Persist` ghi `HF_HOME` và `PIP_CACHE_DIR` vào biến môi trường mức User, nghĩa là
**mọi dự án Python sau này trên máy đó** cũng dùng thư mục này. Đây là tác dụng phụ
ngoài phạm vi dự án nên phải bật thủ công. Gỡ bỏ:

```powershell
[Environment]::SetEnvironmentVariable('HF_HOME', $null, 'User')
[Environment]::SetEnvironmentVariable('PIP_CACHE_DIR', $null, 'User')
```

Biến `TMP`/`TEMP` chỉ đổi trong phiên chạy script, không bao giờ ghi vĩnh viễn — rất
nhiều phần mềm khác cũng đọc biến này.

## Nếu máy bạn khác cấu hình

Script tự đọc `nvidia-smi` và chọn kênh CUDA phù hợp. Ghi đè khi cần:

```powershell
.\scripts\01_setup_env.ps1 -CudaChannel cu128    # RTX 50xx (Blackwell)
.\scripts\01_setup_env.ps1 -CudaChannel cu118    # driver cu
.\scripts\01_setup_env.ps1 -CudaChannel cpu      # khong co GPU NVIDIA
```

Quy tắc tự chọn:

| Điều kiện | Kênh |
|---|---|
| Tên GPU khớp `RTX 5xxx` | `cu128` — Blackwell (sm_120) **không chạy được** wheel cu126 |
| Driver hỗ trợ CUDA ≥ 12.6 | `cu126` |
| Driver hỗ trợ CUDA ≥ 11.8 | `cu118` |
| Không có `nvidia-smi` | `cpu` — chậm hơn 20–50 lần, chỉ đủ để kiểm tra code chạy |

## Khóa phiên bản

Script pin sẵn `torch==2.13.0`. Muốn đổi:

```powershell
.\scripts\01_setup_env.ps1 -TorchVersion "2.12.0"
.\scripts\01_setup_env.ps1 -TorchVersion ""       # lay ban moi nhat, KHONG pin
```

Hai file requirements phục vụ hai mục đích khác nhau:

| File | Dùng khi | Cách dùng |
|---|---|---|
| `requirements.txt` | Chỉ cần môi trường **chạy được** | mặc định |
| `requirements-lock.txt` | Cần tái lập **chính xác** môi trường đã kiểm chứng | thêm cờ `-Lock` |

```powershell
.\scripts\01_setup_env.ps1 -Lock
```

### Giới hạn của tính tái lập

Cùng seed cho ra ảnh **trùng khít từng bit** khi và chỉ khi chạy trên **cùng một máy,
cùng phiên bản thư viện**. Đổi GPU, đổi phiên bản torch/cuDNN, hoặc đổi driver đều có
thể làm kết quả lệch đi vài pixel — kể cả khi mọi tham số sinh ảnh giống hệt nhau.

Hệ quả cho thiết kế thí nghiệm: **toàn bộ so sánh Baseline vs Proposed phải chạy trên
một máy duy nhất**. Gom kết quả từ nhiều máy của nhiều thành viên sẽ đưa thêm biến số
ngoài ý muốn vào phép so sánh, đúng loại confound mà mục 16 của spec đang tìm cách loại bỏ.
Các máy còn lại dùng để phát triển và kiểm thử, không dùng để sinh số liệu cuối.

## Vì sao chọn từng thứ

| Quyết định | Lý do |
|---|---|
| PyTorch wheel `cu126` từ index riêng | `pip install torch` thông thường sẽ kéo về bản **CPU-only**. Bắt buộc dùng `--index-url https://download.pytorch.org/whl/cu126` |
| `variant="fp16"` | Repo SD1.5 chứa cả `.bin`, `.ckpt`, fp32, non_ema → tải hết là **~24 GB**. Chỉ fp16: **~2.8 GB** |
| `stable-diffusion-v1-5/stable-diffusion-v1-5` | Repo `runwayml/stable-diffusion-v1-5` đã bị gỡ khỏi Hub năm 2024 |
| ControlNet **v1.1** (`control_v11p_sd15_canny`) | Bản mới hơn `sd-controlnet-canny`, giữ cấu trúc tốt hơn |
| `UniPCMultistepScheduler` | Chất lượng tốt ở 20–25 steps thay vì 50 → nhanh gấp đôi trên GPU laptop |
| `safety_checker=None` | Họa tiết di sản hay bị false-positive → trả về ảnh đen. Bật lại nếu cần cho phần công bố |
| `enable_attention_slicing` + VAE slicing | Đủ để 512×512 chạy thoải mái trong 8 GB, gần như không chậm hơn |

## Hai mức `controlnet_conditioning_scale`

Khớp với Constraint Engine trong spec (mục 15–16):

- **0.9 → Preserve mode**: bám sát cấu trúc họa tiết gốc
- **0.5 → Reimagine mode**: cho phép biến đổi mạnh hơn

Smoke test chạy cả hai với **cùng seed = 42** để xác nhận tính tái lập —
đây là điều kiện bắt buộc khi so sánh Baseline vs Proposed.

## Xử lý sự cố

| Triệu chứng | Nguyên nhân & cách sửa |
|---|---|
| `torch.cuda.is_available()` = False | Cài nhầm bản CPU. `pip uninstall -y torch torchvision` rồi cài lại với `--index-url https://download.pytorch.org/whl/cu126` |
| `CUDA out of memory` | Bỏ comment `pipe.enable_model_cpu_offload()` trong `04_test_controlnet.py` (chậm hơn ~30%, chỉ tốn ~3 GB) |
| Ảnh trả về toàn đen | Safety checker hoặc NaN của fp16. Đã tắt safety checker; nếu vẫn đen, thử `torch_dtype=torch.float32` để khoanh vùng |
| `No such file: ...fp16.safetensors` | Repo đó không có bản fp16 → bỏ `variant="fp16"` cho riêng repo đó |
| `TypeError` / `unexpected keyword` lúc `from_pretrained` | Lệch phiên bản `diffusers` ↔ `transformers`. Hạ transformers về nhánh 4.x |
| Hết chỗ giữa chừng khi cài | Xem mục "Nếu ổ hệ thống của bạn sắp đầy" ở trên |
| OOM sau nhiều lần generate liên tiếp | Thiếu `torch.cuda.empty_cache()` giữa các lần — spec mục 19 yêu cầu rõ điều này khi làm UI Streamlit |
| Tải model đứt giữa chừng | Chạy lại `03_download_models.py`, nó tải tiếp chứ không tải lại từ đầu |

## Định nghĩa hoàn thành (Ngày 2)

- [ ] `02_check_gpu.py` in ra đúng tên GPU + `cuda.is_available: True`
- [ ] `04_test_controlnet.py` chạy hết không OOM, sinh đủ 2 ảnh
- [ ] Peak VRAM ghi nhận < 6 GB (còn dư biên cho Streamlit + BGE-M3 sau này)
- [ ] Chạy lại lần 2 cùng seed cho ra ảnh giống hệt → pipeline tái lập được
