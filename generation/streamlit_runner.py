from __future__ import annotations

from collections.abc import Callable
import hashlib
import os
from pathlib import Path
import time

from generation import controlnet as cn, garment, layout_select, palette, pattern
from generation.stable_diffusion import Generator

ROOT = Path(__file__).resolve().parent.parent
SEED = 42
POLISH_STRENGTH = 0.40


def _resolve_variants_dir(output_dir: Path | None) -> Path:
    if output_dir is not None:
        return output_dir if output_dir.is_absolute() else (ROOT / output_dir)
    dh_out = os.getenv("DH_OUTPUT_DIR", "").strip()
    base_dir = Path(dh_out) if dh_out else (ROOT / "outputs")
    if not base_dir.is_absolute():
        base_dir = ROOT / base_dir
    return base_dir / "variants"


def _format_design_path(design_path: Path) -> str:
    try:
        return str(design_path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(design_path).replace("\\", "/")


def generate_design_set(
    heritage_id: str,
    on_progress: Callable[[int, str], None] | None = None,
    output_dir: Path | None = None,
) -> list[dict]:
    def report(progress: int, label: str) -> None:
        if on_progress:
            on_progress(progress, label)

    report(5, "Đang chuẩn bị hoa văn từ hiện vật...")
    prepared = cn.prepare(heritage_id, ornament_only=True, trim=True)
    source_colors = palette.dominant_colors(prepared["reference"], prepared["reference_mask"])
    target_dir = _resolve_variants_dir(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    generator = Generator()
    try:
        from evaluation.intensity_sweep import Scorer

        ver = generator.versions()
        scorer = Scorer()
        used_layouts: set[str] = set()
        results: list[dict] = []
        for index, variant in enumerate((
            {"level": 1, "palette": "original"},
            {"level": 2, "palette": "free"},
            {"level": 3, "palette": "free"},
            {"level": 4, "palette": "free"},
        ), start=1):
            t0 = time.time()
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
            design = garment.polish(chosen["image"], strength=POLISH_STRENGTH, seed=SEED)
            design_path = target_dir / f"{heritage_id}_V{index}_aodai.png"
            design.save(design_path)
            sha256_full = hashlib.sha256(design_path.read_bytes()).hexdigest()
            similarity = scorer.similarity(prepared["reference"], design_pattern)
            duration_s = round(time.time() - t0, 2)
            results.append({
                "variant_index": index,
                "heritage_id": heritage_id,
                "seed": SEED,
                "intensity_level": variant["level"],
                "level_name": result["level_name"],
                "controlnet_weight": result["weight"],
                "palette_mode": variant["palette"],
                "layout": chosen["layout"],
                "layout_label": chosen["label"],
                "polish_strength": POLISH_STRENGTH,
                "positive_prompt": result["positive_prompt"],
                "negative_prompt": result["negative_prompt"],
                "sha256_design": sha256_full,
                "sd_model_id": ver["sd_model_id"],
                "controlnet_id": ver["controlnet_id"],
                "torch_version": ver["torch"],
                "diffusers_version": ver["diffusers"],
                "gpu": ver["gpu"],
                "duration_s": duration_s,
                "similarity_pattern_vs_ceramic": round(similarity, 4),
                "source_palette": ";".join(
                    f"#{red:02x}{green:02x}{blue:02x}" for red, green, blue in source_colors
                ),
                "design_path": _format_design_path(design_path),
            })
        report(100, "Đã tạo xong bốn thiết kế.")
        return results
    finally:
        generator.close()
        garment.free_polish_pipe()
