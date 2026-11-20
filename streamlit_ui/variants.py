"""Đọc bộ 4 thiết kế đã được pipeline ghi ra ổ đĩa (outputs/variants/<mã>_V<n>_aodai.png)."""
from __future__ import annotations

from pathlib import Path


def saved_variants(project_root: Path, heritage_id: str) -> list[dict]:
    """Trả về bốn ảnh thiết kế thật đã được pipeline ghi ra ổ đĩa."""
    variants = []
    for index in range(1, 5):
        image_path = project_root / "outputs" / "variants" / f"{heritage_id}_V{index}_aodai.png"
        if not image_path.is_file():
            return []
        variants.append({
            "variant_index": index,
            "layout_label": f"Thiết kế {index}",
            "design_path": image_path.relative_to(project_root).as_posix(),
        })
    return variants
