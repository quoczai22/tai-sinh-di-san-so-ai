import os
import sys

def main():
    print("=" * 60)
    print("KIEM TRA MOI TRUONG AI LOCAL")
    print("=" * 60)

    print(f"Python      : {sys.version.split()[0]}")
    print(f"Executable  : {sys.executable}")
    hf_home = os.environ.get("HF_HOME")
    if hf_home:
        print(f"HF_HOME     : {hf_home}")
    else:
        default = os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
        print(f"HF_HOME     : (khong dat) -> dung mac dinh {default}")

    import torch
    print(f"\ntorch       : {torch.__version__}")
    print(f"CUDA build  : {torch.version.cuda}")
    print(f"cuda.is_available : {torch.cuda.is_available()}")

    if not torch.cuda.is_available():
        print("\n[LOI] PyTorch khong thay CUDA.")
        print("Nguyen nhan thuong gap: da cai nham ban CPU-only.")
        print("Sua: pip uninstall -y torch torchvision")
        print("     pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126")
        sys.exit(1)

    props = torch.cuda.get_device_properties(0)
    print(f"GPU         : {props.name}")
    print(f"VRAM        : {props.total_memory / 1024**3:.2f} GB")
    print(f"Compute cap : sm_{props.major}{props.minor}")

    # Phep tinh thuc te tren GPU de chac chan kernel chay duoc
    x = torch.randn(2000, 2000, device="cuda", dtype=torch.float16)
    y = (x @ x).sum().item()
    torch.cuda.synchronize()
    print(f"\n[OK] Matmul fp16 tren GPU chay duoc (checksum={y:.1f})")

    import diffusers, transformers
    print(f"diffusers   : {diffusers.__version__}")
    print(f"transformers: {transformers.__version__}")

    torch.cuda.empty_cache()
    print("\n=== MOI TRUONG SAN SANG ===")

if __name__ == "__main__":
    main()
