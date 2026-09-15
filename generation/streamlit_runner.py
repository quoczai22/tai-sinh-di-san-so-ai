from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from generation import controlnet as cn, garment, layout_select, palette, pattern
from generation.stable_diffusion import Generator

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "outputs" / "variants"
SEED = 42


def generate_design_set(
    heritage_id: str,
    on_progress: Callable[[int, str], None] | None = None,
) -> list[dict]:
    def report(progress: int, label: str) -> None:
        if on_progress:
            on_progress(progress, label)

    report(5, "Đang chuẩn bị hoa văn từ hiện vật...")
    prepared = cn.prepare(heritage_id, ornament_only=True, trim=True)
    source_colors = palette.dominant_colors(prepared["reference"], prepared["reference_mask"])
    output_dir = OUT_DIR if OUT_DIR.is_absolute() else ROOT / OUT_DIR
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
