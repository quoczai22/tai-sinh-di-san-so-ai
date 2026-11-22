"""Đo thời gian từng bước của một lần sinh bộ 4 thiết kế (đúng luồng khi bấm "Tạo thiết kế").

Không sửa code của pipeline: script bọc các hàm chính bằng bộ đếm giờ (đồng bộ GPU trước và sau mỗi hàm
để số đo là thời gian thật). Ảnh, Passport và nhật ký loại ảnh ghi vào outputs/_profile_tmp/ (runner chỉ nhận đường dẫn nằm trong repo) và bị xóa hết khi xong.
Chạy nhiều lượt trong cùng một tiến trình để thấy khác biệt giữa lượt đầu (nạp mô hình lần đầu) và các lượt sau,
giống một máy chủ API đã chạy sẵn.

    uv run python scripts/eval/profile_generation.py                    # LR3D_61, 2 lượt
    uv run python scripts/eval/profile_generation.py LR3D_33 --runs 1

Cần GPU NVIDIA và mô hình đã tải (xem docs/SETUP_AI_LOCAL.md). Mỗi lượt khoảng 2 đến 3 phút.
Các dòng trong bảng là thời gian bao gồm cả bước con. Dòng "trong đó" là một phần của dòng ngay trên nó.
"""
import argparse
import functools
import shutil
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import torch                                                       # noqa: E402

from evaluation import intensity_sweep                              # noqa: E402
from generation import controlnet, garment, garment_lora, layout_select, pattern  # noqa: E402
from pipeline import run as pipeline_run                       # noqa: E402
from generation.stable_diffusion import Generator                   # noqa: E402
from provenance import builder, passport                            # noqa: E402
from quality import assess, pattern_retry, retry                                   # noqa: E402

# (nhãn, đối tượng, tên hàm, có phải bước con của dòng trước không)
STEPS = [
    ("Sinh áo dài nền (LoRA + SAM, tối đa 6 lần thử)", garment_lora, "generate_garment", False),
    ("Nạp bộ sinh hoa văn (SD 1.5 + ControlNet)", Generator, "__init__", False),
    ("Nạp CLIP chấm điểm", intensity_sweep.Scorer, "__init__", False),
    ("Chuẩn bị đường nét Canny", controlnet, "prepare", False),
    ("Sinh hoa văn (4 thiết kế)", pattern, "generate", False),
    ("Chọn bố cục bằng CLIP (4 thiết kế)", layout_select, "rank", False),
    ("Polish + khóa họa tiết + vòng thử lại", retry, "polish_with_retry", False),
    ("  trong đó nạp bộ img2img", garment, "_img2img_pipe", True),
    ("  trong đó chạy img2img", garment, "polish", True),
    ("Cổng chất lượng G2/G3", assess, "assess_design", False),
    ("Lập Design Passport", builder, "build_design_passport", False),
    ("Ghi Passport ra đĩa", passport, "save", False),
]
TIMES: dict[str, list[float]] = defaultdict(list)


def sync() -> None:
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def instrument(obj, name: str, label: str) -> None:
    fn = getattr(obj, name)

    @functools.wraps(fn)
    def inner(*args, **kwargs):
        sync()
        t = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            sync()
            TIMES[label].append(time.perf_counter() - t)

    if hasattr(fn, "cache_clear"):                                  # hàm có lru_cache (bộ img2img): giữ lại cache_clear cho code gốc
        inner.cache_clear = fn.cache_clear
    setattr(obj, name, inner)


def report(run: int, total: float, sub_run: dict[str, list[float]]) -> None:
    print(f"\n=== Lượt {run}: tổng {total:.1f} giây ({total / 60:.1f} phút) ===")
    print(f"{'Bước':<52}{'Số lần':>7}{'Tổng (giây)':>13}{'Mỗi lần':>10}{'% tổng':>8}")
    accounted = 0.0
    for label, _, _, child in STEPS:
        xs = sub_run.get(label, [])
        if not xs:
            continue
        s = sum(xs)
        if not child:
            accounted += s
        print(f"{label:<52}{len(xs):>7}{s:>13.1f}{s / len(xs):>10.1f}{100 * s / total:>7.0f}%")
    print(f"{'Phần còn lại (chuẩn bị, lưu ảnh, scorer, ghi manifest...)':<52}{'':>7}{total - accounted:>13.1f}{'':>10}{100 * (total - accounted) / total:>7.0f}%")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("heritage_id", nargs="?", default="LR3D_61")
    ap.add_argument("--runs", type=int, default=2)
    args = ap.parse_args()
    if not torch.cuda.is_available():
        print("Không có GPU CUDA, không đo được.")
        return 1

    base = ROOT / "outputs" / "_profile_tmp"
    base.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="profile_gen_", dir=base))
    pipeline_run.PASSPORT_DIR = tmp / "passports"             # Passport và nhật ký ghi vào thư mục tạm
    retry.QC_DIR = tmp / "qc"
    pattern_retry.QC_DIR = tmp / "qc"
    for label, obj, name, _ in STEPS:
        instrument(obj, name, label)

    try:
        print(f"GPU: {torch.cuda.get_device_name(0)}; hiện vật {args.heritage_id}; ghi tạm vào {tmp}")
        for run in range(1, args.runs + 1):
            TIMES.clear()
            t0 = time.perf_counter()
            results = pipeline_run.generate_design_set(
                args.heritage_id, lambda p, label: print(f"  [{time.perf_counter() - t0:6.1f}s] {p}% {label}", flush=True),
                output_dir=tmp / "runs")
            total = time.perf_counter() - t0
            done = sum(r["status"] == "completed" for r in results)
            print(f"  xong {done}/{len(results)} thiết kế")
            report(run, total, dict(TIMES))
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
