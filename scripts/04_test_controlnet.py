import os
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from dotenv import load_dotenv
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

from diffusers import (
    ControlNetModel,
    StableDiffusionControlNetPipeline,
    UniPCMultistepScheduler,
)

OUT_DIR = ROOT / "outputs"
OUT_DIR.mkdir(exist_ok=True)
SEED = 42
RESOLUTION = 512  # SD1.5 native. Tren 8GB co the len 768 nhung cham hon nhieu.


def load_or_make_reference() -> Image.Image:
    """Lay anh heritage dau tien; neu chua co dataset thi tao hoa tiet hinh hoc de test."""
    heritage = ROOT / "data" / "heritage"
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        files = sorted(heritage.glob(ext))
        if files:
            print(f"[i] Dung anh tham chieu: {files[0].name}")
            return Image.open(files[0]).convert("RGB").resize((RESOLUTION, RESOLUTION))

    print("[i] Chua co anh trong data/heritage/ -> tao hoa tiet hinh hoc de smoke test.")
    canvas = np.full((RESOLUTION, RESOLUTION, 3), 255, np.uint8)
    c = RESOLUTION // 2
    for r in range(40, 240, 40):
        cv2.circle(canvas, (c, c), r, (0, 0, 0), 3)
    for k in range(8):
        a = k * np.pi / 4
        p1 = (int(c + 60 * np.cos(a)), int(c + 60 * np.sin(a)))
        p2 = (int(c + 230 * np.cos(a)), int(c + 230 * np.sin(a)))
        cv2.line(canvas, p1, p2, (0, 0, 0), 3)
    return Image.fromarray(canvas)


def to_canny(img: Image.Image, low: int = 100, high: int = 200) -> Image.Image:
    """Preprocessor Canny - dieu kien cau truc dau vao cho ControlNet."""
    arr = cv2.Canny(np.array(img), low, high)
    return Image.fromarray(np.stack([arr] * 3, axis=-1))


def main():
    assert torch.cuda.is_available(), "Khong thay GPU - chay 02_check_gpu.py truoc."
    dtype = torch.float16

    print("[..] Nap ControlNet + SD1.5 (fp16)...")
    controlnet = ControlNetModel.from_pretrained(
        os.environ["CONTROLNET_CANNY_ID"], torch_dtype=dtype, variant="fp16"
    )
    pipe = StableDiffusionControlNetPipeline.from_pretrained(
        os.environ["SD15_MODEL_ID"],
        controlnet=controlnet,
        torch_dtype=dtype,
        variant="fp16",
        safety_checker=None,          # tranh false-positive lam anh den; bat lai neu can
        requires_safety_checker=False,
    )
    # UniPC: chat luong tot voi it step -> nhanh hon tren GPU laptop
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
    pipe.to("cuda")

    # --- Toi uu VRAM ---
    pipe.enable_attention_slicing()   # giam peak VRAM, gan nhu khong cham hon
    # VAE slicing: API doi cho giua cac ban diffusers -> thu ca hai
    try:
        pipe.vae.enable_slicing()
    except AttributeError:
        pipe.enable_vae_slicing()
    # Neu VAN bi OOM, bo comment dong duoi (cham hon ~30% nhung chi ton ~3GB VRAM):
    # pipe.enable_model_cpu_offload()

    reference = load_or_make_reference()
    control = to_canny(reference)
    reference.save(OUT_DIR / "smoketest_00_reference.png")
    control.save(OUT_DIR / "smoketest_01_canny.png")

    prompt = (
        "traditional Vietnamese heritage motif, intricate ornamental pattern, "
        "flat vector illustration, clean lines, high detail"
    )
    negative = "blurry, low quality, watermark, text, distorted, photorealistic"

    # 0.9 = Preserve (giu cau truc chat) | 0.5 = Reimagine (bien doi manh hon)
    for scale in (0.9, 0.5):
        torch.cuda.reset_peak_memory_stats()
        t0 = time.time()

        image = pipe(
            prompt=prompt,
            negative_prompt=negative,
            image=control,
            num_inference_steps=25,
            guidance_scale=7.5,
            controlnet_conditioning_scale=scale,
            generator=torch.Generator("cuda").manual_seed(SEED),
        ).images[0]

        dt = time.time() - t0
        peak = torch.cuda.max_memory_allocated() / 1024**3
        out = OUT_DIR / f"smoketest_scale{scale}_seed{SEED}.png"
        image.save(out)
        print(f"[OK] scale={scale}  {dt:.1f}s  peak VRAM {peak:.2f} GB  -> {out.name}")

    # Giai phong VRAM giua cac lan chay (spec muc 19 yeu cau ro dieu nay)
    del pipe, controlnet
    torch.cuda.empty_cache()
    print(f"\n=== SMOKE TEST PASS. Xem ket qua trong {OUT_DIR} ===")


if __name__ == "__main__":
    main()
