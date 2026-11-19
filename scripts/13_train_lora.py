"""Huấn luyện LoRA dáng áo dài trên SD 1.5 từ tập VietFashion đã lọc (kế hoạch mục 6.3, bước 4).

LoRA là một lớp nhỏ gắn thêm vào các lớp attention của UNet; chỉ lớp này được học, mô hình gốc
giữ nguyên. Nhờ vậy vừa 8 GB VRAM của RTX 4060.

Để tiết kiệm bộ nhớ, script mã hóa trước toàn bộ ảnh (VAE) và caption (text encoder) một lần, giải
phóng hai mô hình đó, rồi chỉ huấn luyện UNet.

Dữ liệu: data/vietfashion/lora_train/ (do scripts/12_export_lora_set.py tạo). VietFashion theo
CC BY-NC 4.0: chỉ dùng phi thương mại, ghi công bài ICMR 2026 (Cao và cộng sự, doi 10.1145/3805622.3810590).

Ảnh nguồn nhỏ (256x344): phóng lên 768x1032 không thêm chi tiết. SD 1.5 được huấn luyện ở 512, nên
độ phân giải cao hơn có thể không có lợi; so sánh với --width 512 --height 688 --rank 16 bằng thí nghiệm E6.

Chạy:  uv run python scripts/13_train_lora.py --steps 800
Ra:    data/lora/aodai_vietfashion/ (pytorch_lora_weights.safetensors, train_log.csv, config.json)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "vietfashion" / "lora_train"
OUT = ROOT / "data" / "lora" / "aodai_vietfashion"
WIDTH, HEIGHT = 768, 1032         # ảnh nguồn 256x344 (tỉ lệ 0,74) phóng 3 lần; SD 1.5 gốc quen 512 nên cần so với bản 512x688
TARGET_MODULES = ["to_q", "to_k", "to_v", "to_out.0"]   # các lớp attention của UNet


def read_metadata(folder: Path) -> list[dict]:
    """Đọc metadata.jsonl: mỗi dòng có file_name và text. Báo lỗi rõ nếu thiếu ảnh hoặc caption rỗng."""
    path = folder / "metadata.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Chưa có {path}. Chạy scripts/12_export_lora_set.py trước.")
    items = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not row.get("text", "").strip():
            raise ValueError(f"Dòng {n} của {path.name}: caption rỗng")
        if not (folder / row["file_name"]).exists():
            raise FileNotFoundError(f"Dòng {n}: thiếu ảnh {row['file_name']}")
        items.append(row)
    if not items:
        raise ValueError(f"{path} không có dòng nào")
    return items


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--steps", type=int, default=800, help="số bước cập nhật (mỗi bước gồm grad-accum ảnh)")
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--width", type=int, default=WIDTH)
    ap.add_argument("--height", type=int, default=HEIGHT)
    ap.add_argument("--rank", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--save-every", type=int, default=0, help="lưu mốc trung gian mỗi N bước (0 là không lưu)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    import numpy as np                                              # noqa: PLC0415
    import torch                                                    # noqa: PLC0415
    import torch.nn.functional as F                                 # noqa: PLC0415
    from diffusers import AutoencoderKL, DDPMScheduler, StableDiffusionPipeline, UNet2DConditionModel  # noqa: PLC0415
    from diffusers.utils import convert_state_dict_to_diffusers     # noqa: PLC0415
    from peft import LoraConfig                                     # noqa: PLC0415
    from peft.utils import get_peft_model_state_dict                # noqa: PLC0415
    from PIL import Image                                           # noqa: PLC0415
    from transformers import CLIPTextModel, CLIPTokenizer           # noqa: PLC0415

    sys.path.insert(0, str(ROOT))
    from generation.stable_diffusion import load_env                # noqa: PLC0415

    args = parse_args(argv)
    if args.width % 8 or args.height % 8:
        raise ValueError("Chiều rộng và cao phải chia hết cho 8 (yêu cầu của VAE)")
    items = read_metadata(args.data)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    load_env()
    model_id = os.environ["SD15_MODEL_ID"]
    dev, dtype = "cuda", torch.bfloat16
    kw = {"torch_dtype": dtype, "variant": "fp16"}

    # 1. Mã hóa trước ảnh và caption, rồi bỏ VAE và text encoder khỏi GPU
    tok = CLIPTokenizer.from_pretrained(model_id, subfolder="tokenizer")
    text_encoder = CLIPTextModel.from_pretrained(model_id, subfolder="text_encoder", **kw).to(dev)
    vae = AutoencoderKL.from_pretrained(model_id, subfolder="vae", **kw).to(dev)
    latents, embeds = [], []
    with torch.no_grad():
        for it in items:
            im = Image.open(args.data / it["file_name"]).convert("RGB").resize((args.width, args.height), Image.LANCZOS)
            x = torch.from_numpy(np.asarray(im)).permute(2, 0, 1)[None].to(dev, dtype) / 127.5 - 1.0
            latents.append((vae.encode(x).latent_dist.mean * vae.config.scaling_factor).cpu())
            ids = tok(it["text"], padding="max_length", max_length=tok.model_max_length, truncation=True,
                      return_tensors="pt").input_ids.to(dev)
            embeds.append(text_encoder(ids)[0].cpu())
    del vae, text_encoder
    torch.cuda.empty_cache()

    # 2. UNet đóng băng, gắn LoRA (tham số học được để float32 cho ổn định)
    unet = UNet2DConditionModel.from_pretrained(model_id, subfolder="unet", **kw)
    unet.requires_grad_(False)
    unet.add_adapter(LoraConfig(r=args.rank, lora_alpha=args.rank, init_lora_weights="gaussian",
                                target_modules=TARGET_MODULES))
    for p in unet.parameters():
        if p.requires_grad:
            p.data = p.data.float()
    unet.enable_gradient_checkpointing()
    unet.to(dev).train()
    params = [p for p in unet.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=1e-2)
    sched = DDPMScheduler.from_pretrained(model_id, subfolder="scheduler")
    n_params = sum(p.numel() for p in params)
    print(f"{len(items)} ảnh, LoRA rank {args.rank}: {n_params / 1e6:.2f} triệu tham số học được")

    # 3. Vòng huấn luyện
    args.out.mkdir(parents=True, exist_ok=True)
    torch.cuda.reset_peak_memory_stats()
    t0, log = time.time(), []

    def save(path: Path) -> None:
        state = convert_state_dict_to_diffusers(get_peft_model_state_dict(unet))
        StableDiffusionPipeline.save_lora_weights(save_directory=str(path), unet_lora_layers=state,
                                                  safe_serialization=True)

    for step in range(1, args.steps + 1):
        loss_sum = 0.0
        for _ in range(args.grad_accum):
            i = random.randrange(len(items))
            lat, emb = latents[i].to(dev, dtype), embeds[i].to(dev, dtype)
            noise = torch.randn_like(lat)
            t = torch.randint(0, sched.config.num_train_timesteps, (1,), device=dev)
            noisy = sched.add_noise(lat, noise, t)
            with torch.autocast("cuda", dtype=dtype):
                pred = unet(noisy, t, emb).sample
            loss = F.mse_loss(pred.float(), noise.float()) / args.grad_accum
            loss.backward()
            loss_sum += loss.item()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        log.append({"step": step, "loss": round(loss_sum, 5), "elapsed_s": round(time.time() - t0, 1)})
        if step % 20 == 0 or step == 1:
            print(f"bước {step}/{args.steps}  loss {loss_sum:.4f}  {log[-1]['elapsed_s']}s", flush=True)
        if args.save_every and step % args.save_every == 0 and step != args.steps:
            save(args.out / f"step_{step}")

    save(args.out)
    with open(args.out / "train_log.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(log[0]))
        w.writeheader()
        w.writerows(log)
    peak = torch.cuda.max_memory_allocated() / 1024 ** 3
    cfg = {**{k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
           "base_model": model_id, "n_images": len(items), "resolution": [args.width, args.height],
           "target_modules": TARGET_MODULES, "trainable_params": n_params, "peak_vram_gb": round(peak, 2),
           "seconds": round(time.time() - t0, 1), "torch": torch.__version__,
           "data_license": "VietFashion CC BY-NC 4.0, chỉ dùng phi thương mại"}
    (args.out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Xong. VRAM đỉnh {peak:.2f} GB, {cfg['seconds']} giây → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
