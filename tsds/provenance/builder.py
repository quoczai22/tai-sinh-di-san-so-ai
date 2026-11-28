# -*- coding: utf-8 -*-
"""Dựng Design Passport từ một BẢN GHI THIẾT KẾ đã chuẩn hoá.

Hàm dùng chung cho luồng sinh ảnh qua API/Streamlit (tsds/pipeline/run.py).
Nhờ vậy Passport của luồng sản phẩm có ĐỦ trường như luồng đánh giá (sửa điểm
lệch #2 của bản rà soát: "luồng API không ghi seed, prompt, model, mã băm").
"""
from __future__ import annotations

import json
from pathlib import Path

from . import passport as P
from .registry import rights_gate

from tsds.core.paths import ROOT
from tsds.core.timing import SCHEMA as TIMING_SCHEMA
LORA_LICENSE = "VietFashion CC BY-NC 4.0: chỉ dùng phi thương mại"
LORA_CITATION = ("Cao, Bui, Vo, Tran, Le. VietFashion: Benchmarking Sketch-Text Composed Image Retrieval for "
                 "Cultural Outfits. ICMR 2026. doi:10.1145/3805622.3810590")


def _terms(heritage_id: str, root: Path) -> dict:
    data = json.loads((root / "data" / "prompt_terms.json").read_text(encoding="utf-8"))
    return data["terms"].get(heritage_id, {})


def _garment_block(garment: dict | None, rec: dict) -> dict:
    """Khối `generation.garment` của Passport: áo nền lấy từ đâu và nếu là áo do LoRA sinh thì sinh thế nào.

    Luồng sản phẩm hiện chỉ dùng áo LoRA. Nhánh "fixed" còn lại cho trường hợp ghép lên áo mẫu cố định."""
    if not garment or garment.get("source") != "lora":
        return {"source": "fixed", "template": "data/garment/aodai_template.png",
                "fallback_reason": (garment or {}).get("fallback_reason")}
    from tsds.generation.garment.garment_lora import NEG_EXTRA                        # noqa: PLC0415  (không nạp torch: garment_lora chỉ nạp torch khi sinh áo)
    lora = garment.get("lora") or ""
    try:
        lora = Path(lora).relative_to(ROOT).as_posix()
    except ValueError:
        pass                                    # đường dẫn ngoài repo: giữ nguyên
    return {"source": "lora", "seed": garment.get("seed"), "candidates": garment.get("tried") or [],
            "lora": {"path": lora, "base_model": rec["sd_model_id"], "training_data": "VietFashion (226 ảnh đã lọc)",
                     "license": LORA_LICENSE, "citation": LORA_CITATION},
            "mask_method": "SAM facebook/sam-vit-base, điểm gợi ý ở trục giữa thân áo",
            "prompt_negative_extra": NEG_EXTRA}                 # đúng chuỗi lúc sinh áo (tsds/generation/garment/garment_lora.py)


def build_design_passport(*, item: dict, run_id: str, run_stamp: str, rec: dict, paths: dict,
                          assessment: dict | None, now: str, root: Path = ROOT,
                          polish_prompt: str = "", polish_negative: str = "",
                          garment: dict | None = None, run_timing: dict | None = None) -> dict:
    """`rec`: bản ghi chuẩn hoá của một thiết kế. `paths`: Path tuyệt đối
    của source/reference/canny/pattern/raw/final.

    `run_timing`: thời gian dùng chung cả lượt chạy (áo nền, nạp model, tổng cả bộ), copy vào Passport
    của từng thiết kế kèm nhãn phạm vi. Có `rec["timing"]` thì Passport ghi khối `generation.timing`
    (định nghĩa từng số ở docs/DO_THOI_GIAN.md); Passport cũ không có khối này.

    `garment`: thông tin áo nền (khóa `garment` trong manifest của runner): source "lora" (luồng hiện tại) hay "fixed" (lần chạy cũ),
    seed, LoRA, các ứng viên đã thử, đường dẫn ảnh áo và mặt nạ. None nghĩa là áo mẫu cố định."""
    i = int(rec["variant_index"])
    design_id = f"{run_id}.V{i}"
    pid = P.passport_id_for(item["code"], run_stamp, i)
    pp = P.new_passport(passport_id=pid, design_id=design_id, run_id=run_id, heritage=item,
                        created_at=rec["timestamp"])
    src = P.file_record(paths["source"], "source_image", root)
    ref = P.file_record(paths["reference"], "reference_512", root)
    canny = P.file_record(paths["canny"], "control_canny", root)
    pat = P.file_record(paths["pattern"], "pattern", root)
    raw = P.file_record(paths["raw"], "composite_raw", root)
    extra = {"legacy_sha256_prefix": rec["sha256_design"]} if rec.get("sha256_design") else {}
    fin = P.file_record(paths["final"], "final_img2img", root, **extra)
    pp["artifacts"] = [src, ref, canny, pat, raw, fin]
    use_lora = bool(garment and garment.get("source") == "lora")
    gar = gmask = None
    if use_lora:
        gar = P.file_record(root / garment["image"], "garment", root)
        gmask = P.file_record(root / garment["mask"], "garment_mask", root)
        pp["artifacts"] += [gar, gmask]
    terms = _terms(item["heritage_id"], root)
    pp["generation"] = {
        "pipeline": rec.get("pipeline", "two-stage v6"),
        "models": {"sd": rec["sd_model_id"], "controlnet": rec["controlnet_id"],
                   "clip_layout_scorer": "openai/clip-vit-base-patch32", "description_llm": terms.get("llm_model")},
        "versions": {"torch": rec.get("torch_version"), "diffusers": rec.get("diffusers_version"), "gpu": rec.get("gpu")},
        "prompt": rec["positive_prompt"], "negative_prompt": rec["negative_prompt"],
        "seed": int(rec["seed"]), "steps": int(rec["steps"]), "guidance": float(rec["guidance"]),
        "scheduler": "UniPCMultistep",
        "controlnet": {"conditioning_scale": float(rec["controlnet_weight"]),
                       "intensity_level": int(rec["intensity_level"]), "intensity_name": rec["level_name"],
                       "canny_low": 100, "canny_high": 200, "resolution": 512, "control_mode": rec["control_mode"],
                       "outline_erode_px": 14, "edge_px": int(rec["n_edge_px"]),
                       "conditioning_mode": item.get("conditioning_mode")},
        "palette": {"mode": rec["palette_mode"], "source_palette": str(rec["source_palette"]).split(";")},
        "layout": {"name": rec["layout"], "label": rec["layout_label"], "scale": float(rec["layout_scale"]),
                   "selected_by": rec.get("layout_selected_by", "clip_auto"), "score": float(rec["layout_score"]),
                   "ranking": rec.get("layout_ranking", "")},
        "polish_img2img": {"strength": float(rec["polish_strength"]), "steps": 30, "guidance": 7.0,
                           "seed": int(rec["seed"]), "prompt": polish_prompt, "negative_prompt": polish_negative},
        "reference_metrics": {"clip_similarity_pattern_vs_ceramic": float(rec["similarity_pattern_vs_ceramic"]),
                              "note": "CLIP đo trên hoa văn GIAI ĐOẠN 1, trước ghép và img2img — chỉ để tham khảo."},
        # CHỈ là thời gian gọi Stable Diffusion của lần sinh hoa văn được chọn (không gồm áo nền, sinh lại, polish, kiểm tra).
        # Thời gian đầy đủ từng giai đoạn nằm ở generation.timing.
        "duration_s": float(rec.get("duration_s") or 0),
        "garment": _garment_block(garment, rec),
    }
    pp["generation"]["polish_img2img"].update({
        "masked": bool(rec.get("polish_mask", False)), "status": rec.get("polish_status", "single_pass"),
        "attempts": int(rec.get("polish_attempts", 1))})
    # Vòng sinh lại hoa văn khi G2 LỖI: seed hoa văn thực dùng (khác seed gốc nếu đã sinh lại) và các lần thử
    pp["generation"]["pattern_seed"] = int(rec.get("pattern_seed", rec["seed"]))
    pp["generation"]["pattern_retry"] = {"status": rec.get("pattern_status", "single_pass"),
                                         "attempts": rec.get("pattern_attempt_log") or []}
    if rec.get("polish_lock"):
        from tsds.core import pattern_lock as _repair
        pp["generation"]["polish_img2img"]["pattern_lock"] = {"method": _repair.METHOD, "params": _repair.PARAMS}
    prov = item.get("provenance") or {}
    ts = rec["timestamp"]
    P.add_step(pp, step="collect_image",
               label=f"Thu thập ảnh hiện vật ({prov.get('holder') or 'nguồn chưa rõ'})",
               actor_type="human", actor="Nhóm dự án", tool="Trình duyệt web",
               at=prov.get("collected_on") and f"{prov['collected_on']}T00:00:00+00:00",
               outputs=[src["sha256"]], note=prov.get("collected_note"))
    if terms:
        P.add_step(pp, step="describe_motif", label="Viết mô tả hoa văn tiếng Anh ≤21 token",
                   actor_type="ai" if terms.get("source") == "llm_vision" else "human",
                   actor=terms.get("llm_model") or terms.get("author") or "Nhóm dự án",
                   tool="scripts/data_prep/describe_heritage.py" if terms.get("source") == "llm_vision" else "Soạn tay",
                   at=f"{terms['generated_on']}T00:00:00+00:00" if terms.get("generated_on") else None,
                   note=terms.get("review_note"))
    P.add_step(pp, step="preprocess", label="Tách nền, letterbox 512, Canny chỉ giữ hoa văn",
               actor_type="system", actor="tsds/generation/pattern/controlnet.py", tool="OpenCV", at=ts,
               inputs=[src["sha256"]], outputs=[ref["sha256"], canny["sha256"]])
    P.add_step(pp, step="generate_pattern",
               label=f"Sinh hoa văn phẳng (ControlNet {rec['controlnet_weight']}, seed {rec.get('pattern_seed', rec['seed'])})",
               actor_type="ai", actor="Stable Diffusion 1.5 + ControlNet Canny", tool="tsds/generation/pattern/pattern.py",
               at=ts, inputs=[canny["sha256"]], outputs=[pat["sha256"]])
    if rec["palette_mode"] == "original":
        P.add_step(pp, step="palette_match", label="Khớp bảng màu hiện vật (thống kê LAB)",
                   actor_type="system", actor="tsds/generation/pattern/palette.py", tool="OpenCV", at=ts)
    P.add_step(pp, step="layout_select", label=f"Chọn bố cục '{rec['layout_label']}'",
               actor_type="ai" if rec.get("layout_selected_by", "clip_auto") == "clip_auto" else "human",
               actor="CLIP ViT-B/32" if rec.get("layout_selected_by", "clip_auto") == "clip_auto" else "Nhà thiết kế",
               tool="tsds/generation/garment/layout_select.py", at=ts)
    if use_lora:
        tried = garment.get("tried") or []
        P.add_step(pp, step="generate_garment",
                   label=f"Sinh áo dài nền bằng LoRA, SAM tách vùng áo (seed {garment.get('seed')}, thử {len(tried)} ứng viên)",
                   actor_type="ai", actor="Stable Diffusion 1.5 + LoRA dáng áo dài", tool="tsds/generation/garment/garment_lora.py",
                   at=ts, outputs=[gar["sha256"], gmask["sha256"]],
                   note=f"LoRA huấn luyện từ {LORA_LICENSE}. {LORA_CITATION}")
    base = "áo do LoRA sinh" if use_lora else "áo mẫu"
    P.add_step(pp, step="composite", label=f"Ghép tất định lên {base} (mask mềm, displacement, shading)",
               actor_type="system", actor="tsds/generation/garment/garment.py", tool="OpenCV/NumPy", at=ts,
               inputs=[pat["sha256"]] + ([gar["sha256"]] if use_lora else []), outputs=[raw["sha256"]])
    kind = "chỉ vùng áo" if rec.get("polish_mask") else "toàn ảnh"
    locked = bool(rec.get("polish_lock"))
    P.add_step(pp, step="polish",
               label=f"Hoàn thiện img2img {kind} (strength {rec['polish_strength']})" + (", khóa họa tiết" if locked else ""),
               actor_type="ai", actor="Stable Diffusion 1.5 img2img", tool="tsds/generation/garment/garment.py",
               at=ts, inputs=[raw["sha256"]], outputs=[fin["sha256"]],
               note=("Sau polish, tsds/core/pattern_lock.py (pattern_lock_v1, tất định) trả lại nét vẽ và màu họa tiết từ bản ghép thô; "
                     "phần ánh sáng và bóng vải lấy từ polish.") if locked else None)
    P.add_version(pp, kind="ai_generated", artifact=fin, created_by="pipeline", actor_type="ai", at=ts,
                  note="Thiết kế cuối do pipeline sinh.")
    if rec.get("timing"):
        P.record_timing(pp, {"schema": TIMING_SCHEMA, "clock": "perf_counter", "unit": "s",
                             "design": rec["timing"],
                             "run": {**(run_timing or {}), "scope": "chung cả lượt chạy, KHÔNG cộng cho từng thiết kế"}},
                      at=ts)                       # cùng mốc với các bước khác để dòng thời gian không bị đảo thứ tự
    if assessment:
        ov = assessment["overall"]
        P.add_step(pp, step="quality_gate", label=f"Cổng chất lượng G2+G3: {ov['decision']}",
                   actor_type="system", actor="tsds/quality/gate.py", tool=assessment["config_version"], at=now)
        P.record_quality(pp, {"G2_pattern": assessment["G2_pattern"], "G3_final": assessment["G3_final"],
                              "overall": ov}, assessment["config_version"], at=now)
        rep = assessment.get("repair")
        if rep:
            art = P.file_record(rep["path"], "repair_pattern_lock", root, method=rep["info"]["method"])
            pp["artifacts"].append(art)
            P.add_step(pp, step="repair_pattern_lock", label="Sửa tất định: khoá họa tiết (pattern-lock)",
                       actor_type="system", actor="tsds/core/pattern_lock.py", tool=rep["info"]["method"], at=now,
                       inputs=[raw["sha256"], fin["sha256"]], outputs=[art["sha256"]])
            P.add_version(pp, kind="system_repair", artifact=art, created_by="tsds/core/pattern_lock.py",
                          actor_type="system", at=now,
                          note=f"Ứng viên sửa; G3 sau sửa: {rep['G3_final']['decision']}. Chuyên gia so mù với v1.")
            pp["quality"]["repair"] = {"G3_final": rep["G3_final"], "overall": rep["overall"]}
        from tsds.quality.assess import approval_from_assessment          # noqa: PLC0415
        status, reason = approval_from_assessment(assessment)
        P.set_approval(pp, status, by="quality_gate", actor_type="system", at=now, reason=reason)
    pp["rights"] = {a: rights_gate(item, a, root).as_dict()
                    for a in ("demo_display", "publish_public", "commercial_use")}
    return pp
