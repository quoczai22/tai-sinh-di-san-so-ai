import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# HF_HOME la tuy chon. Khong set thi huggingface_hub tu dung thu muc mac dinh.
HF_HOME = os.environ.get("HF_HOME")
CACHE_DIR = Path(HF_HOME) if HF_HOME else Path.home() / ".cache" / "huggingface"

print(f"Cache dich : {CACHE_DIR}" + ("" if HF_HOME else "  (mac dinh he thong)"))
print()

from huggingface_hub import snapshot_download

# Cac file text/config luon can + chi ban fp16 cua trong so
FP16_ONLY = ["*.json", "*.txt", "*.fp16.safetensors"]

MODELS = [
    # (repo_id, allow_patterns, mo ta)
    (os.environ["SD15_MODEL_ID"], FP16_ONLY, "Stable Diffusion 1.5 (base) ~2.8GB"),
    (os.environ["CONTROLNET_CANNY_ID"], ["*.json", "*.fp16.safetensors"], "ControlNet v1.1 Canny ~723MB"),
    # Bo comment 2 dong duoi neu muon thu nghiem them preprocessor khac (ngay 7 theo timeline):
    # ("lllyasviel/control_v11p_sd15_softedge", ["*.json", "*.fp16.safetensors"], "ControlNet SoftEdge ~723MB"),
    # ("lllyasviel/control_v11p_sd15_lineart", ["*.json", "*.fp16.safetensors"], "ControlNet Lineart ~723MB"),
]


def main():
    for repo_id, patterns, desc in MODELS:
        print(f"[..] {repo_id}  -  {desc}")
        path = snapshot_download(
            repo_id=repo_id,
            allow_patterns=patterns,
            # dut mang: chay lai lenh nay se tai tiep, khong tai lai tu dau
        )
        size = sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file())
        print(f"[OK] {size / 1024**3:.2f} GB -> {path}\n")

    print("=== TAI MODEL XONG. Tiep theo: python scripts/04_test_controlnet.py ===")


if __name__ == "__main__":
    main()
