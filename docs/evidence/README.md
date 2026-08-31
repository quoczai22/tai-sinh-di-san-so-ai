# Bằng chứng — Smoke test SD1.5 + ControlNet (Ngày 2)

Kết quả chạy [`scripts/04_test_controlnet.py`](../../scripts/04_test_controlnet.py),
lưu lại làm bằng chứng deliverable Ngày 2. Thư mục `outputs/` bị gitignore nên
bốn ảnh này được sao chép sang đây để commit.

## Cấu hình sinh ra kết quả

| Tham số | Giá trị |
|---|---|
| Base model | `stable-diffusion-v1-5/stable-diffusion-v1-5` (fp16) |
| ControlNet | `lllyasviel/control_v11p_sd15_canny` (fp16) |
| Scheduler | UniPCMultistepScheduler |
| Resolution | 512 × 512 |
| Inference steps | 25 |
| Guidance scale | 7.5 |
| Seed | 42 |
| GPU | RTX 4060 Laptop 8 GB |

Prompt và negative prompt xem trực tiếp trong script (dòng 103–107).

## Bốn ảnh

| File | Nội dung |
|---|---|
| `smoketest_00_reference.png` | Ảnh tham chiếu đầu vào. Đây là họa tiết hình học do script tự sinh bằng OpenCV, **không phải mẫu di sản thật** — lúc chạy test thì `data/heritage/` còn rỗng |
| `smoketest_01_canny.png` | Bản đồ biên Canny — điều kiện cấu trúc mà ControlNet thực sự nhận vào |
| `smoketest_scale0.9_seed42.png` | `controlnet_conditioning_scale = 0.9` → **Preserve mode** |
| `smoketest_scale0.5_seed42.png` | `controlnet_conditioning_scale = 0.5` → **Reimagine mode** |

## Điều hai ảnh cuối chứng minh

Cả hai dùng **cùng prompt, cùng seed, cùng ảnh điều kiện**. Biến số duy nhất
thay đổi là `controlnet_conditioning_scale`.

- Ở **0.9**, kết quả bám gần như nguyên bản đồ Canny: vòng tròn đồng tâm và 8 nan
  hoa được giữ nguyên, model hầu như không thêm chi tiết nào.
- Ở **0.5**, bộ khung vẫn nhận ra được nhưng model đã tự thêm vành bện, họa tiết
  góc và tâm hoa — sáng tạo nhiều hơn hẳn.

Khác biệt này xác nhận `controlnet_conditioning_scale` là **biến số có tác động
nhìn thấy được**, tức là confound mà mục 16.3 của MVP Spec cảnh báo là có thật.
Do đó việc định nghĩa tường minh weight cho từng nhánh — Baseline dùng một giá trị
cố định, Proposed dùng giá trị thích ứng theo category — là bắt buộc, không phải
đề phòng thừa.

## Số đo hiệu năng

| Chỉ số | Giá trị |
|---|---|
| Peak VRAM | 3,33 GB / 8 GB |
| Thời gian mỗi ảnh | 5,6 – 7,0 giây (~4,7 it/s) |

## Tính tái lập

Chạy script hai lần liên tiếp cho ra bốn file **trùng khít SHA256**:

```
571bac619db61f66f579669e13ee956f9ea88c4a9b56fa0e27e5d373293dd7e9  smoketest_00_reference.png
6a79486e4ec06e8fc404005cd99b7c05f6c68329d2dda62b648a7cd92756eba5  smoketest_01_canny.png
fc9d95de8f59427adcbcd3f0f0e814fa268bd3e3044b73ee588254ccd2223e34  smoketest_scale0.9_seed42.png
bd3fe528a6a7eb44b45aace5a28b209171066362ad237a22ff7b6743842a6dd3  smoketest_scale0.5_seed42.png
```

Kiểm chứng lại bằng:

```powershell
python scripts/04_test_controlnet.py
Get-FileHash outputs\*.png -Algorithm SHA256
```

Tái lập được là điều kiện bắt buộc để so sánh Baseline với Proposed cho ra kết luận
có nghĩa — nếu cùng seed mà ra ảnh khác nhau thì mọi khác biệt đo được đều có thể
chỉ là nhiễu.
