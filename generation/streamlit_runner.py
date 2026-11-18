from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from generation import controlnet as cn, element_library, garment, layout_select, palette, pattern
from generation.stable_diffusion import Generator

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "outputs" / "variants"
SEED = 42


def generate_design_set(
    heritage_id: str,
    on_progress: Callable[[int, str], None] | None = None,
    output_dir: Path | None = None,
    source: str = "render",
) -> list[dict]:
    """Sinh bốn thiết kế cho một hiện vật.

    source chọn ảnh nạp cho ControlNet (thiếu thì tự quay về bậc thấp hơn: elements, panel, rồi ảnh hiện vật):
    - "render" (mặc định): ảnh hiện vật trong data/heritage/ (với LR3D là ảnh render cả bình), đúng luồng hồ sơ gốc.
    - "panel": mảng texture phẳng trong data/heritage/panels/.
    - "elements": mỗi biến thể một phần tử trong kho data/elements/.
    """
    def report(progress: int, label: str) -> None:
        if on_progress:
            on_progress(progress, label)

    report(5, "Đang chuẩn bị hoa văn từ hiện vật...")
    cache: dict[str, dict] = {}

    def prep(path: Path | None) -> dict:
        key = str(path)
        if key not in cache:
            cache[key] = cn.prepare(heritage_id, ornament_only=True, trim=True, image_path=path)
        return cache[key]

    inputs = element_library.variant_inputs(heritage_id, source, root=ROOT)
    try:
        prepared_list = [prep(p) for _, p in inputs]
    except (OSError, ValueError):
        inputs = [("hien_vat", None)] * 4  # file hỏng: quay về ảnh hiện vật mặc định thay vì làm sập lượt sinh
        prepared_list = [prep(None)] * 4
    source_ids = [label for label, _ in inputs]
    output_dir = output_dir or OUT_DIR
    output_dir = output_dir if output_dir.is_absolute() else ROOT / output_dir
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        output_dir = ROOT / "digital-heritage-ai" / ".model-cache" / "generated"
        output_dir.mkdir(parents=True, exist_ok=True)

    generator = Generator()
    try:
        from evaluation.intensity_sweep import Scorer

        scorer = Scorer()
        used_layouts: set[str] = set()
        results: list[dict] = []
        for index, variant in enumerate((
            {"level": 1, "palette": "original"},
            {"level": 2, "palette": "free"},
            {"level": 3, "palette": "free"},
            {"level": 4, "palette": "free"},
        ), start=1):
            report(10 + (index - 1) * 20, f"Đang tạo thiết kế {index}/4...")
            prepared = prepared_list[index - 1]
            source_colors = palette.dominant_colors(prepared["reference"], prepared["reference_mask"])
            result = pattern.generate(generator, heritage_id, variant["level"], SEED, prepared=prepared)
            design_pattern = result["image"]
            if variant["palette"] == "original":
                design_pattern = palette.match_palette(
                    design_pattern, prepared["reference"], prepared["reference_mask"]
                )

            ranked = layout_select.rank(design_pattern)
            chosen = next((item for item in ranked if item["layout"] not in used_layouts), ranked[0])
            used_layouts.add(chosen["layout"])
            design = garment.polish(chosen["image"], strength=0.40, seed=SEED)
            design_path = output_dir / f"{heritage_id}_V{index}_aodai.png"
            design.save(design_path)
            similarity = scorer.similarity(prepared["reference"], design_pattern)
            results.append({
                "variant_index": index,
                "source_element": source_ids[index - 1],  # nguồn ảnh nét: mã phần tử, "panel" hoặc "hien_vat"
                "layout_label": chosen["label"],
                "similarity_pattern_vs_ceramic": round(similarity, 4),
                "source_palette": ";".join(
                    f"#{red:02x}{green:02x}{blue:02x}" for red, green, blue in source_colors
                ),
                "design_path": str(design_path.relative_to(ROOT)).replace("\\", "/"),
            })
        report(100, "Đã tạo xong bốn thiết kế.")
        return results
    finally:
        generator.close()
        garment.free_polish_pipe()
