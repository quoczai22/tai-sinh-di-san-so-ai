# -*- coding: utf-8 -*-
"""Bọc pipeline SD1.5 + ControlNet (spec mục 12.1, 18).

Chạy local trên GPU 8GB. Giải phóng VRAM đúng cách giữa các lần chạy là yêu
cầu tường minh của spec mục 18 — không làm sẽ OOM khi demo nhiều lần liên tiếp.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from PIL import Image

for _s in (sys.stdout, sys.stderr):
    if getattr(_s, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parent.parent

STEPS = 25
GUIDANCE = 7.5
SCHEDULER = "UniPCMultistep"      # chất lượng tốt với ít step → nhanh trên GPU laptop


def load_env() -> None:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class Generator:
    """Nạp model một lần, sinh nhiều ảnh, rồi giải phóng tường minh."""

    def __init__(self) -> None:
        load_env()
        import torch                                        # noqa: PLC0415
        from diffusers import (ControlNetModel,             # noqa: PLC0415
                               StableDiffusionControlNetPipeline,
                               UniPCMultistepScheduler)
        assert torch.cuda.is_available(), "Khong thay GPU — chay scripts/02_check_gpu.py"
        self.torch = torch
        t0 = time.time()
        cn = ControlNetModel.from_pretrained(
            os.environ["CONTROLNET_CANNY_ID"], torch_dtype=torch.float16, variant="fp16")
        pipe = StableDiffusionControlNetPipeline.from_pretrained(
            os.environ["SD15_MODEL_ID"], controlnet=cn, torch_dtype=torch.float16,
            variant="fp16",
            # Safety checker cho false-positive trên hoạ tiết tôn giáo → ảnh đen.
            # Tắt là quyết định có chủ đích, phải ghi vào docs/ai_disclosure.md.
            safety_checker=None, requires_safety_checker=False)
        pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
        pipe.to("cuda")
        pipe.enable_attention_slicing()
        try:
            pipe.vae.enable_slicing()
        except AttributeError:
            pipe.enable_vae_slicing()
        self.pipe, self.controlnet = pipe, cn
        self.load_seconds = time.time() - t0
        p = torch.cuda.get_device_properties(0)
        self.gpu = f"{p.name} {p.total_memory / 1024**3:.0f}GB"

    def generate(self, positive: str, negative: str, control: Image.Image,
                 weight: float, seed: int) -> tuple[Image.Image, float, float]:
        self.torch.cuda.reset_peak_memory_stats()
        t0 = time.time()
        img = self.pipe(
            prompt=positive, negative_prompt=negative, image=control,
            num_inference_steps=STEPS, guidance_scale=GUIDANCE,
            controlnet_conditioning_scale=weight,
            generator=self.torch.Generator("cuda").manual_seed(seed),
        ).images[0]
        peak = self.torch.cuda.max_memory_allocated() / 1024**3
        return img, time.time() - t0, peak

    def set_seamless(self, on: bool = True) -> None:
        """Bật/tắt chế độ sinh ảnh LẶP LIỀN MẠCH.

        Mặc định các lớp conv dùng zero-padding, nên mép trái/phải và trên/dưới
        của ảnh không liên quan gì nhau — ghép hai bản cạnh nhau là lộ đường nối.
        Đổi sang `circular` thì padding lấy từ mép đối diện, buộc model sinh ra
        ảnh mà mép trái nối liền mép phải.

        Đây là cách sửa ĐÚNG GỐC. Trước đó tôi lát gương để né đường nối, nhưng
        cách đó tạo ra đối xứng gương kiểu kaleidoscope — vừa không giống hoa văn
        gốm vẽ tay, vừa không giấu được việc hoạ tiết bị cắt ở ranh giới ô.
        """
        import torch                                          # noqa: PLC0415
        mode = "circular" if on else "zeros"
        for net in (self.pipe.unet, self.pipe.vae, self.controlnet):
            for m in net.modules():
                if isinstance(m, torch.nn.Conv2d):
                    m.padding_mode = mode
        self.seamless = on

    def close(self) -> None:
        del self.pipe, self.controlnet
        self.torch.cuda.empty_cache()

    def versions(self) -> dict:
        import diffusers                                    # noqa: PLC0415
        return {"torch": self.torch.__version__, "diffusers": diffusers.__version__,
                "sd_model_id": os.environ["SD15_MODEL_ID"],
                "controlnet_id": os.environ["CONTROLNET_CANNY_ID"],
                "scheduler": SCHEDULER, "steps": STEPS, "guidance": GUIDANCE,
                "gpu": self.gpu}
