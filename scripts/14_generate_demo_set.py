"""Sinh bộ demo bằng luồng sản phẩm: mỗi hiện vật đang hoạt động ra 4 thiết kế (4 mức sáng tạo), áo nền do LoRA sinh.

Kết quả: outputs/runs/R<thời gian>-<mã>/ (ảnh, manifest) và outputs/passports/DP-*.json (Design Passport).
Sau đó chạy scripts/11_export_demo_data.py để xuất dữ liệu cho giao diện web.

    uv run python scripts/14_generate_demo_set.py            # mọi hiện vật đang hoạt động
    uv run python scripts/14_generate_demo_set.py LR3D_61    # chọn hiện vật
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generation.streamlit_runner import generate_design_set        # noqa: E402
from provenance.registry import all_items                          # noqa: E402


def main(argv: list[str]) -> int:
    ids = argv or [it["heritage_id"] for it in all_items(ROOT) if it.get("status", "active") == "active"]
    for n, hid in enumerate(ids, start=1):
        print(f"[{n}/{len(ids)}] {hid}", flush=True)
        results = generate_design_set(hid, lambda p, label: print(f"  {p}% {label}", flush=True))
        print(f"  xong {len(results)} thiết kế", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
