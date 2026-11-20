"""Điều phối end-to-end một lần sinh bộ thiết kế (dùng chung cho API và Streamlit).

Thay đổi ở bản chung kết (giữ nguyên chữ ký cũ, chỉ THÊM tham số tuỳ chọn):
  · Mỗi lần chạy có `run_id` riêng và thư mục riêng `outputs/runs/<run_id>/` —
    không còn ghi đè `outputs/variants/<id>_V<n>_aodai.png` (nguyên nhân 20/24 ảnh
    lệch mã băm so với nhật ký).
  · Ghi `manifest.json` đủ tham số (seed, prompt, model, phiên bản thư viện, bố
    cục, strength img2img, SHA-256 từng tệp) và Design Passport cho từng thiết kế.
  · Một biến thể lỗi không làm hỏng cả bộ: biến thể đó được đánh dấu `failed`.
  · Seed nhận từ người dùng (mặc định 42 để tái lập bộ cũ).
  · Sau khi sinh, chạy Cổng chất lượng G2/G3 (CPU) và tạo ứng viên sửa nếu cần.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from generation import controlnet as cn, element_library, garment, layout_select, palette, pattern
from generation.stable_diffusion import Generator

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "outputs" / "runs"
PASSPORT_DIR = ROOT / "outputs" / "passports"
SEED = 42
POLISH_STRENGTH = 0.40
DEFAULT_VARIANTS = (
    {"level": 1, "palette": "original"},
    {"level": 2, "palette": "free"},
    {"level": 3, "palette": "free"},
    {"level": 4, "palette": "free"},
)
log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_run_id(code: str, when: datetime | None = None) -> tuple[str, str]:
    when = when or datetime.now(timezone.utc)
    stamp = when.strftime("%Y%m%dT%H%M%S")
    return f"R{stamp}-{code}", stamp


def generate_design_set(
    heritage_id: str,
    on_progress: Callable[[int, str], None] | None = None,
    output_dir: Path | None = None,
    seed: int = SEED,
    variants: tuple[dict, ...] = DEFAULT_VARIANTS,
    run_id: str | None = None,
    source: str = "render",
    garment_lora_dir: Path | None = None,
    garment_seed: int | None = None,
) -> list[dict]:
    """Sinh bộ thiết kế cho một hiện vật.

    source chọn ảnh nạp cho ControlNet (thiếu phần tử thì tự quay về ảnh hiện vật):
    - "render" (mặc định): ảnh hiện vật gốc trong data/heritage/ (với LR3D là ảnh render cả bình). Pipeline đi thẳng từ
      ảnh bình gốc, không qua mảng hoa văn trải phẳng làm sẵn. Vòng kiểm tra G2 (lọt hình bình, đường nối) và sinh lại
      hoa văn bù cho việc ControlNet có thể bám theo dáng bình.
    - "elements": mỗi biến thể một phần tử trong kho data/elements/.

    Áo dài nền luôn do SD 1.5 + LoRA dáng áo dài sinh mới mỗi lần chạy, vùng áo tách bằng SAM
    (generation/garment_lora.py). Không còn áo mẫu cố định: thiếu LoRA hoặc không sinh được áo hợp lệ thì
    ném GarmentError, không quay về áo khác. garment_lora_dir chọn thư mục LoRA (mặc định data/lora/aodai_r16_512).
    garment_seed: seed sinh áo, độc lập với `seed` (hoa văn và polish). Mặc định None là ngẫu nhiên mỗi lần chạy nên
    mỗi lần ra một áo khác; seed áo thực dùng được ghi vào manifest và Passport để tái lập.
    """
    from provenance import passport as P                          # noqa: PLC0415
    from provenance.builder import build_design_passport          # noqa: PLC0415
    from provenance.registry import get_item, rights_gate         # noqa: PLC0415
    from quality.assess import assess_design                      # noqa: PLC0415

    def report(progress: int, label: str) -> None:
        if on_progress:
            on_progress(progress, label)

    item = get_item(heritage_id, ROOT)
    if item is None:
        raise KeyError(heritage_id)
    gate = rights_gate(item, "experiment", ROOT)
    if not gate.allowed:
        raise PermissionError(gate.reason)

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
    prepared = prepared_list[0]  # ảnh tham chiếu của bộ (lưu và ghi vào Passport) lấy theo biến thể 1
    base = output_dir or OUT_DIR
    base = base if base.is_absolute() else ROOT / base
    if run_id is None:
        run_id, run_stamp = make_run_id(item["code"])
    else:
        run_stamp = run_id[1:16]
    run_dir = base / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    ref_path, canny_path = run_dir / "00_reference.png", run_dir / "01_canny.png"
    prepared["reference"].save(ref_path)
    prepared["control"].save(canny_path)

    # Áo nền: sinh mới bằng LoRA. Sinh áo xong mới nạp bộ sinh hoa văn để hai mô hình không chiếm VRAM cùng lúc.
    report(8, "Đang sinh áo dài nền bằng LoRA...")
    from generation import garment_lora                                 # noqa: PLC0415
    g = garment_lora.generate_garment(run_dir, seed=garment_lora.pick_seed(garment_seed), lora_dir=garment_lora_dir)
    tpl_path, region = g["path"], g["mask"]
    garment_info = {"source": "lora", "seed": g["seed"], "lora": g["lora"], "tried": g["tried"],
                    "image": g["path"].relative_to(ROOT).as_posix(),
                    "mask": g["mask_path"].relative_to(ROOT).as_posix()}

    generator = Generator()
    versions = generator.versions()
    records: list[dict] = []
    try:
        from evaluation.intensity_sweep import Scorer             # noqa: PLC0415

        scorer = Scorer()
        # Cổng G2 đo hoa văn ngay sau khi sinh (để sinh lại khi LỖI). Đo trên đúng ảnh tham chiếu đã lưu, giống bước
        # kiểm tra chất lượng cuối lượt chạy, nên kết quả hai lần đo khớp nhau.
        from quality import gate as QG, pattern_retry as PR            # noqa: PLC0415

        qg_cfg = QG.load_config()
        ref_arr = np.asarray(Image.open(ref_path).convert("RGB"))
        used_layouts: set[str] = set()
        total = len(variants)
        for index, variant in enumerate(variants, start=1):
            report(10 + (index - 1) * (80 // total), f"Đang tạo thiết kế {index}/{total}...")
            try:
                prepared = prepared_list[(index - 1) % len(prepared_list)]
                source_colors = palette.dominant_colors(prepared["reference"], prepared["reference_mask"])

                def make_pattern(s: int, prepared=prepared, variant=variant) -> tuple[Image.Image, dict]:
                    res = pattern.generate(generator, heritage_id, variant["level"], s, prepared=prepared)
                    img = res["image"]
                    if variant["palette"] == "original":
                        img = palette.match_palette(img, prepared["reference"], prepared["reference_mask"])
                    return img, res

                # Sinh lại hoa văn khi G2 LỖI (mặc định bật): đổi seed, tối đa max_retries lần (quality/pattern_retry.py)
                pattern_retry = None
                if variant.get("pattern_retry", True):
                    pattern_retry = PR.generate_with_retry(
                        make_pattern,
                        lambda im: QG.evaluate_pattern(np.asarray(im.convert("RGB")), ref_arr, qg_cfg),
                        seed=seed, tag=f"{run_id}_V{index}",
                        on_retry=lambda n, s, i=index: report(
                            10 + (i - 1) * (80 // total), f"Đang sinh lại hoa văn thiết kế {i}/{total} (lần {n})..."))
                    design_pattern, result = pattern_retry["image"], pattern_retry["result"]
                else:
                    design_pattern, result = make_pattern(seed)
                pat_path = run_dir / f"V{index}_pattern.png"
                design_pattern.save(pat_path)
                ranked = layout_select.rank(design_pattern, template_path=tpl_path, garment_region=region)
                if variant.get("layout"):
                    chosen = next(x for x in ranked if x["layout"] == variant["layout"])
                    selected_by = "fixed"
                else:
                    chosen = next((x for x in ranked if x["layout"] not in used_layouts), ranked[0])
                    selected_by = "clip_auto"
                used_layouts.add(chosen["layout"])
                raw_path = run_dir / f"V{index}_aodai_raw.png"
                chosen["image"].save(raw_path)
                # polish_mask: chỉ polish vùng áo, ngoài áo giữ nguyên từng pixel (mặc định bật; False là polish toàn ảnh,
                # làm nền bị vẽ lại: đo được 14 đến 17% pixel ngoài áo đổi hơn 12 mức xám)
                masked = bool(variant.get("polish_mask", True))
                # polish_lock: khóa họa tiết sau polish (mặc định bật; chỉ dùng kèm polish_mask), trả lại nét vẽ và màu từ bản thô
                lock = masked and bool(variant.get("polish_lock", True))
                strength = float(variant.get(
                    "polish_strength", garment.POLISH_MASKED_STRENGTH if masked else POLISH_STRENGTH))
                if lock:
                    tpl_img = Image.open(tpl_path).convert("RGB")
                    layout_mask = garment._layout_mask(tpl_img, garment.get_layout(chosen["layout"]), region)
                    polish_fn = lambda im, strength, seed: garment.polish_locked(    # noqa: E731
                        im, layout_mask, strength=strength, seed=seed, mask=region)
                elif masked:
                    polish_fn = lambda im, strength, seed: garment.polish_masked(    # noqa: E731
                        im, strength=strength, seed=seed, mask=region)
                else:
                    polish_fn = garment.polish
                retry_info = None
                if strength > 0 and variant.get("polish_retry", True):
                    # Vòng loại và thử lại (mặc định bật): lỗi M1/M3 thì đổi seed, hạ độ nhiễu, cuối cùng trả ảnh ghép thô (quality/retry.py)
                    from quality import retry as QR                    # noqa: PLC0415
                    retry_info = QR.polish_with_retry(
                        chosen["image"], lambda im, st, sd: polish_fn(im, strength=st, seed=sd),
                        QR.make_g3_evaluator(chosen["image"], chosen["layout"], template_path=tpl_path, garment_region=region),
                        seed=seed, strength=strength, fallback_strength=garment.POLISH_FALLBACK_STRENGTH,
                        tag=f"{run_id}_V{index}")
                    design, strength = retry_info["image"], retry_info["strength"] or 0.0
                else:
                    design = polish_fn(chosen["image"], strength=strength, seed=seed) if strength > 0 else chosen["image"]
                design_path = run_dir / f"V{index}_aodai.png"
                design.save(design_path)
                similarity = scorer.similarity(prepared["reference"], design_pattern)
                records.append({
                    "status": "completed", "variant_index": index, "timestamp": _now(),
                    "source_element": source_ids[(index - 1) % len(source_ids)],  # mã phần tử hoặc "hien_vat"
                    "seed": seed, "intensity_level": variant["level"], "level_name": result["level_name"],
                    "controlnet_weight": result["weight"], "palette_mode": variant["palette"],
                    "layout": chosen["layout"], "layout_label": chosen["label"], "layout_scale": chosen["scale"],
                    "layout_score": chosen["score"], "layout_selected_by": selected_by,
                    "layout_ranking": ";".join(f"{x['layout']}:{x['score']}" for x in ranked),
                    "pattern_seed": pattern_retry["seed"] if pattern_retry else seed,
                    "pattern_status": pattern_retry["status"] if pattern_retry else "single_pass",
                    "pattern_attempts": len(pattern_retry["attempts"]) if pattern_retry else 1,
                    "pattern_attempt_log": pattern_retry["attempts"] if pattern_retry else [],
                    "polish_strength": strength, "polish_mask": masked, "polish_lock": lock,
                    "polish_status": retry_info["status"] if retry_info else "single_pass",
                    "polish_attempts": len(retry_info["attempts"]) if retry_info else 1,
                    "polish_label": retry_info["label"] if retry_info else None,
                    "positive_prompt": result["positive_prompt"], "negative_prompt": result["negative_prompt"],
                    "steps": versions["steps"], "guidance": versions["guidance"],
                    "sd_model_id": versions["sd_model_id"], "controlnet_id": versions["controlnet_id"],
                    "torch_version": versions["torch"], "diffusers_version": versions["diffusers"],
                    "gpu": versions["gpu"], "duration_s": round(result["duration_s"], 2),
                    "n_edge_px": prepared["n_edge_px"], "control_mode": prepared["mode"],
                    "similarity_pattern_vs_ceramic": round(similarity, 4),
                    "source_palette": ";".join(f"#{r:02x}{g:02x}{b:02x}" for r, g, b in source_colors),
                    "pattern_path": pat_path, "raw_path": raw_path, "design_path_abs": design_path,
                })
            except Exception as exc:                               # noqa: BLE001
                log.exception("Biến thể %s của %s lỗi", index, heritage_id)
                records.append({"status": "failed", "variant_index": index, "timestamp": _now(),
                                "error_type": type(exc).__name__})
    finally:
        generator.close()
        garment.free_polish_pipe()

    report(92, "Đang kiểm tra chất lượng và lập Design Passport...")
    now = _now()
    results, manifest_designs = [], []
    for rec in records:
        if rec["status"] != "completed":
            results.append({"variant_index": rec["variant_index"], "status": "failed",
                            "error_type": rec["error_type"], "run_id": run_id})
            manifest_designs.append(rec)
            continue
        paths = {"source": ROOT / item["image_path"], "reference": ref_path, "canny": canny_path,
                 "pattern": rec["pattern_path"], "raw": rec["raw_path"], "final": rec["design_path_abs"]}
        try:
            assessment = assess_design(reference=ref_path, pattern=rec["pattern_path"], raw=rec["raw_path"],
                                       final=rec["design_path_abs"], layout=rec["layout"], repair_dir=run_dir,
                                       repair_name=f"V{rec['variant_index']}_pattern_lock.png",
                                       template_path=tpl_path, garment_region=region)
        except Exception:                                          # noqa: BLE001
            log.exception("Cổng chất lượng lỗi")
            assessment = None
        pp = build_design_passport(item=item, run_id=run_id, run_stamp=run_stamp, rec=rec, paths=paths,
                                   assessment=assessment, now=now, root=ROOT,
                                   polish_prompt=garment.POLISH_PROMPT, polish_negative=garment.POLISH_NEG,
                                   garment=garment_info)
        P.save(pp, PASSPORT_DIR)
        rel = rec["design_path_abs"].relative_to(ROOT).as_posix()
        results.append({
            "status": "completed", "variant_index": rec["variant_index"], "run_id": run_id,
            "design_id": pp["design_id"], "passport_id": pp["passport_id"],
            "layout_label": rec["layout_label"], "seed": seed,
            "controlnet_weight": rec["controlnet_weight"], "polish_strength": rec["polish_strength"],
            "polish_status": rec["polish_status"], "polish_label": rec["polish_label"],
            "similarity_pattern_vs_ceramic": rec["similarity_pattern_vs_ceramic"],
            "source_palette": rec["source_palette"], "design_path": rel,
            "quality_decision": assessment["overall"]["decision"] if assessment else None,
            "approval_status": pp["approval"]["status"],
        })
        manifest_designs.append({k: (v.relative_to(ROOT).as_posix() if isinstance(v, Path) else v)
                                 for k, v in rec.items()} | {"passport_id": pp["passport_id"]})
    manifest = {"schema": "run-manifest/1.0", "run_id": run_id, "heritage_id": heritage_id,
                "code": item["code"], "seed": seed, "created_at": now, "versions": versions,
                "rights_gate_experiment": gate.as_dict(), "garment": garment_info, "designs": manifest_designs}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n",
                                           encoding="utf-8")
    done = sum(1 for r in results if r["status"] == "completed")
    report(100, f"Đã tạo xong {done}/{len(results)} thiết kế.")
    if done == 0:
        raise RuntimeError("Không biến thể nào sinh thành công.")
    return results
