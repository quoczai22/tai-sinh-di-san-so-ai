"""Đường dẫn chung của dự án: MỘT nơi định nghĩa, mọi gói import từ đây (không tự ghép ROOT / "data"... nữa).

Giữ nguyên tên thư mục `data/heritage`, `data/lora`, `outputs/runs`... vì Design Passport (có mã băm) lưu đường dẫn tương đối tới chúng.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
HERITAGE_DIR = DATA_DIR / "heritage"          # ảnh hiện vật và metadata.json
PANELS_DIR = HERITAGE_DIR / "panels"          # mảng hoa văn phẳng trải từ mô hình 3D
GARMENT_DIR = DATA_DIR / "garment"            # bố cục hoa văn, áo mẫu cũ
LORA_DIR = DATA_DIR / "lora"                  # trọng số LoRA dáng áo dài

CONFIG_DIR = ROOT / "config"

OUTPUTS_DIR = ROOT / "outputs"
RUNS_DIR = OUTPUTS_DIR / "runs"               # mỗi lần chạy một thư mục
PASSPORTS_DIR = OUTPUTS_DIR / "passports"     # Design Passport
EDITS_DIR = OUTPUTS_DIR / "edits"             # bản sửa tay
EXPERIMENTS_DIR = OUTPUTS_DIR / "experiments"
QC_DIR = OUTPUTS_DIR / "qc"                   # ảnh bị loại và nhật ký thử lại của cổng chất lượng
