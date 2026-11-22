# -*- coding: utf-8 -*-
"""Đánh giá một thiết kế qua cả hai cổng + tự tạo ứng viên sửa khi cần.

Dùng chung cho: luồng sản phẩm (API/Streamlit), script dựng lại lần chạy cũ và
thí nghiệm có kiểm soát — để mọi nơi đo bằng CÙNG một cách.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from tsds.generation.garment import garment

from . import gate as QG
from tsds.core.pattern_lock import pattern_lock


def _arr(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def assess_design(*, reference: Path, pattern: Path, raw: Path, final: Path, layout: str,
                  repair_dir: Path | None = None, repair_name: str | None = None,
                  cfg: dict | None = None, template_path: Path | None = None,
                  garment_region: np.ndarray | None = None, clip_layout: bool = True) -> dict:
    """template_path và garment_region: áo và vùng áo tính sẵn (áo do LoRA sinh); mặc định áo mẫu cố định.

    clip_layout=False: tính lại thiết kế cũ (trước khi sửa lỗi hoa văn tràn ra ngoài áo) bằng đúng mặt nạ cũ."""
    cfg = cfg or QG.load_config()
    tpl_img = Image.open(template_path or garment.TEMPLATE).convert("RGB")
    template = np.asarray(tpl_img)
    prior = garment.garment_mask(tpl_img) if garment_region is None else garment_region
    layout_mask = garment._layout_mask(tpl_img, garment.get_layout(layout), garment_region, clip_layout)
    raw_a, fin_a = _arr(raw), _arr(final)
    g2 = QG.evaluate_pattern(_arr(pattern), _arr(reference), cfg)
    g3 = QG.evaluate_final(raw_a, fin_a, template, layout_mask, prior, cfg)
    ov = QG.overall(g2, g3, cfg)
    result = {"config_version": cfg["version"], "G2_pattern": g2, "G3_final": g3, "overall": ov, "repair": None}
    if repair_dir is not None and g2["decision"] != "FAIL" and g3["decision"] == "FAIL":
        locked, info = pattern_lock(raw_a, fin_a, layout_mask)
        repair_dir.mkdir(parents=True, exist_ok=True)
        path = repair_dir / (repair_name or f"{Path(final).stem}_pattern_lock.png")
        Image.fromarray(locked).save(path)
        g3r = QG.evaluate_final(raw_a, locked, template, layout_mask, prior, cfg)
        result["repair"] = {"path": path, "info": info, "G3_final": g3r, "overall": QG.overall(g2, g3r, cfg)}
    return result


def approval_from_assessment(assessment: dict) -> tuple[str, str]:
    """Trạng thái Passport sau cổng kỹ thuật. Không bao giờ trả 'approved'."""
    ov = assessment["overall"]
    rep = assessment.get("repair")
    if ov["decision"] == "FAIL" and not (rep and rep["overall"]["decision"] != "FAIL"):
        return "qa_failed", ov["message"]
    if ov["decision"] == "WARN" or (rep and rep["overall"]["decision"] == "WARN"):
        return "qa_warning", "Chờ QC Officer xem xét cảnh báo trước khi chuyển chuyên gia."
    return "pending_expert_review", "Đạt cổng kỹ thuật — chờ chuyên gia thẩm định văn hoá và thẩm mỹ."


def assess_edit(passport: dict, edited: Path, root: Path, cfg: dict | None = None) -> dict | None:
    """Cổng G3 cho phiên bản do NGƯỜI chỉnh sửa (BPMN: tải bản sửa lên → G3).

    So bản sửa với bản ghép tất định (composite_raw) của cùng lần chạy, dùng lại
    kết quả G2 đã lưu. Trả None nếu Passport không có bản ghép gốc (không đủ dữ
    liệu để đo — khi đó API giữ trạng thái chờ QC, không tự cho qua)."""
    raw_art = next((a for a in passport.get("artifacts", []) if a.get("role") == "composite_raw"), None)
    g2 = (passport.get("quality") or {}).get("G2_pattern")
    layout = ((passport.get("generation") or {}).get("layout") or {}).get("name")
    if raw_art is None or g2 is None or not layout or not (root / raw_art["path"]).exists():
        return None
    cfg = cfg or QG.load_config()
    # Áo nền và vùng áo của đúng thiết kế này (áo do LoRA sinh nằm trong artifacts); Passport cũ không có thì dùng áo mẫu
    art = {a.get("role"): root / a["path"] for a in passport.get("artifacts", []) if a.get("path")}
    if art.get("garment", Path("?")).exists() and art.get("garment_mask", Path("?")).exists():
        tpl_img = Image.open(art["garment"]).convert("RGB")
        region = (np.asarray(Image.open(art["garment_mask"]).convert("L")) > 0).astype(np.uint8)
    else:
        tpl_img, region = Image.open(garment.TEMPLATE).convert("RGB"), None
    template = np.asarray(tpl_img)
    prior = garment.garment_mask(tpl_img) if region is None else region
    layout_mask = garment._layout_mask(tpl_img, garment.get_layout(layout), region)
    g3 = QG.evaluate_final(_arr(root / raw_art["path"]), _arr(Path(edited)), template, layout_mask, prior, cfg)
    return {"config_version": cfg["version"], "G2_pattern": g2, "G3_final": g3,
            "overall": QG.overall(g2, g3, cfg), "repair": None}
