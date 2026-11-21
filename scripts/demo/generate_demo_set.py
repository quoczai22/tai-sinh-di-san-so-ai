"""Sinh bộ demo bằng luồng sản phẩm: mỗi hiện vật đang hoạt động ra 4 thiết kế (4 mức sáng tạo), áo nền do LoRA sinh.

Kết quả: outputs/runs/R<thời gian>-<mã>/ (ảnh, manifest) và outputs/passports/DP-*.json (Design Passport).
Sau đó chạy scripts/demo/export_demo_data.py để xuất dữ liệu cho giao diện web.

    uv run python scripts/demo/generate_demo_set.py            # mọi hiện vật đang hoạt động, seed 42
    uv run python scripts/demo/generate_demo_set.py LR3D_61    # chọn hiện vật
    uv run python scripts/demo/generate_demo_set.py --seed 43 --out outputs/multiseed   # bộ seed khác, lưu riêng

Bộ demo trên giao diện dùng MỘT seed duy nhất (mặc định 42) cho cả hoa văn lẫn áo LoRA, để chạy lại ra đúng bộ cũ.
generate_design_set tự chọn seed áo ngẫu nhiên khi không truyền; ở đây seed áo luôn bằng seed hoa văn.

--out DIR lưu run vào DIR/runs và Passport vào DIR/passports (mặc định outputs/runs và outputs/passports). Bộ nhiều seed cho
đánh giá mù (scripts/eval/build_blind_review.py) dùng --out outputs/multiseed để không lẫn vào bộ demo seed 42.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from generation.streamlit_runner import SEED, generate_design_set  # noqa: E402
from provenance.registry import all_items                          # noqa: E402


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Sinh bộ demo 4 mức sáng tạo cho các hiện vật")
    ap.add_argument("ids", nargs="*", help="mã hiện vật; bỏ trống là mọi hiện vật đang hoạt động")
    ap.add_argument("--seed", type=int, default=SEED, help="seed hoa văn, polish và áo LoRA (mặc định 42)")
    ap.add_argument("--out", default=None, help="thư mục gốc lưu run và Passport (mặc định outputs/)")
    args = ap.parse_args(argv)
    out = (ROOT / args.out) if args.out else None
    extra = {"output_dir": out / "runs", "passport_dir": out / "passports"} if out else {}
    ids = args.ids or [it["heritage_id"] for it in all_items(ROOT) if it.get("status", "active") == "active"]
    for n, hid in enumerate(ids, start=1):
        print(f"[{n}/{len(ids)}] {hid}", flush=True)
        results = generate_design_set(hid, lambda p, label: print(f"  {p}% {label}", flush=True),
                                      seed=args.seed, garment_seed=args.seed, **extra)
        print(f"  xong {len(results)} thiết kế", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
