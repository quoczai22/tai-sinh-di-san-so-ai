"""Sinh ảnh áo dài trắng mỗi lần chạy bằng SD 1.5 cộng LoRA dáng áo dài, không phụ thuộc áo mẫu cố định.

Quy trình: sinh tối đa `tries` ứng viên (seed liên tiếp) → tách vùng áo bằng SAM → nhận ứng viên đầu tiên có
mặt nạ hợp lệ (`mask_ok`) và áo trắng trơn (`color_ok`). Không ứng viên nào đạt thì ném `GarmentError`; nơi gọi quay về áo mẫu cố định.

LoRA do scripts/13_train_lora.py huấn luyện từ VietFashion (CC BY-NC 4.0, chỉ dùng phi thương mại).
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LORA = ROOT / "data" / "lora" / "aodai_r16_512"
SIZE = (512, 688)                     # rộng x cao, khớp độ phân giải lúc huấn luyện LoRA
NEG_EXTRA = ", orange, red, colored trim, patterned"   # LoRA hay thêm viền màu; ép áo trắng trơn
# Một áo hợp lệ: không chạm mép khung, đủ lớn, đủ cao (thấy từ ngực xuống gấu)
MIN_FRAC, MAX_FRAC, MIN_HEIGHT_FRAC = 0.08, 0.55, 0.60


# Áo phải trắng trơn: tỉ lệ điểm "có màu rực" (độ bão hòa HSV > COLOR_SAT và đủ sáng) trong vùng áo không quá COLOR_MAX_FRAC.
# Đo trên 6 áo đã sinh: áo trắng đạt 0 đến 3% (viền hay thắt lưng nhỏ), áo có mảng đỏ hoặc cam đạt 16 đến 28%.
COLOR_SAT, COLOR_MIN_VAL, COLOR_MAX_FRAC = 0.35, 0.25, 0.05


class GarmentError(RuntimeError):
    """Không sinh được áo hợp lệ (thiếu LoRA, hoặc mọi ứng viên bị loại)."""


def color_ok(img: Image.Image, mask: np.ndarray) -> tuple[bool, str]:
    """Kiểm tra áo có trắng trơn không: vùng áo (theo mặt nạ) không được có mảng màu rực lớn (đỏ, cam...).

    LoRA đôi khi sinh áo có thân đỏ hoặc váy cam dù prompt đã yêu cầu trắng. Áo như vậy làm hoa văn xanh lam mất nổi bật
    và trông sai, nên bị loại như ứng viên có mặt nạ hỏng. Trả về (hợp lệ, lý do nếu không).
    """
    import cv2                                                      # noqa: PLC0415

    m = np.asarray(mask) > 0
    if not m.any():
        return False, "mặt nạ rỗng"
    hsv = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2HSV).astype(np.float32) / 255.0
    vivid = (hsv[..., 1] > COLOR_SAT) & (hsv[..., 2] > COLOR_MIN_VAL)
    frac = float(vivid[m].mean())
    if frac > COLOR_MAX_FRAC:
        return False, f"áo có màu rực {frac:.0%} vùng áo (tối đa {COLOR_MAX_FRAC:.0%}), không phải áo trắng trơn"
    return True, ""


def mask_ok(mask: np.ndarray) -> tuple[bool, str]:
    """Kiểm tra mặt nạ áo. Trả về (hợp lệ, lý do nếu không)."""
    m = np.asarray(mask) > 0
    h, w = m.shape
    if not m.any():
        return False, "mặt nạ rỗng"
    ys, xs = np.where(m)
    if xs.min() == 0 or xs.max() == w - 1:
        return False, "áo chạm mép trái hoặc phải"
    frac = float(m.mean())
    if not MIN_FRAC <= frac <= MAX_FRAC:
        return False, f"diện tích áo {frac:.0%} ngoài khoảng {MIN_FRAC:.0%} đến {MAX_FRAC:.0%}"
    if (ys.max() - ys.min() + 1) / h < MIN_HEIGHT_FRAC:
        return False, "áo thấp hơn 60% chiều cao khung"
    return True, ""


def pick_seed(seed: int | None = None) -> int:
    """Seed sinh áo: dùng seed được chỉ định, không có thì chọn ngẫu nhiên để mỗi lần chạy ra một áo khác.

    Seed thực dùng được ghi vào Design Passport (generation.garment.seed) nên vẫn tái lập được."""
    return secrets.randbelow(2**31) if seed is None else int(seed)


def generate_garment(out_dir: Path, seed: int = 42, lora_dir: Path | None = None, tries: int = 6) -> dict:
    """Sinh áo và lưu `garment.png` cùng `garment_mask.png` vào `out_dir`.

    Trả về dict: path, mask_path, mask (mảng 0/1), seed, lora, tried (danh sách {seed, status, reason}).
    """
    import torch                                                    # noqa: PLC0415
    from diffusers import StableDiffusionPipeline, UniPCMultistepScheduler  # noqa: PLC0415

    from . import garment_sam                                       # noqa: PLC0415
    from .prompt_template import GARMENT_NEG, GARMENT_PROMPT        # noqa: PLC0415
    from .stable_diffusion import load_env                          # noqa: PLC0415

    lora_dir = Path(lora_dir or DEFAULT_LORA)
    if not (lora_dir / "pytorch_lora_weights.safetensors").exists():
        raise GarmentError(f"Chưa có LoRA tại {lora_dir}. Chạy scripts/13_train_lora.py trước.")
    load_env()
    out_dir.mkdir(parents=True, exist_ok=True)
    pipe = StableDiffusionPipeline.from_pretrained(
        os.environ["SD15_MODEL_ID"], dtype=torch.float16, variant="fp16",
        safety_checker=None, requires_safety_checker=False)
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
    pipe.to("cuda")
    pipe.enable_attention_slicing()
    pipe.load_lora_weights(str(lora_dir))
    tried: list[dict] = []
    try:
        for k in range(tries):
            s = seed + k
            img = pipe(prompt=GARMENT_PROMPT, negative_prompt=GARMENT_NEG + NEG_EXTRA, num_inference_steps=30,
                       guidance_scale=7.5, width=SIZE[0], height=SIZE[1],
                       generator=torch.Generator("cuda").manual_seed(s)).images[0]
            try:
                mask = garment_sam.garment_mask_sam(img)
            except RuntimeError as exc:
                tried.append({"seed": s, "status": "rejected", "reason": str(exc)})
                continue
            ok, why = mask_ok(mask)
            if ok:
                ok, why = color_ok(img, mask)
            if not ok:
                tried.append({"seed": s, "status": "rejected", "reason": why})
                continue
            tried.append({"seed": s, "status": "accepted", "reason": ""})
            path, mask_path = out_dir / "garment.png", out_dir / "garment_mask.png"
            img.save(path)
            Image.fromarray((mask * 255).astype(np.uint8)).save(mask_path)
            return {"path": path, "mask_path": mask_path, "mask": mask, "seed": s,
                    "lora": str(lora_dir), "tried": tried}
    finally:
        del pipe
        garment_sam.free_model()
        torch.cuda.empty_cache()
    raise GarmentError(f"Cả {tries} ứng viên đều bị loại: " + "; ".join(f"seed {t['seed']}: {t['reason']}" for t in tried))
