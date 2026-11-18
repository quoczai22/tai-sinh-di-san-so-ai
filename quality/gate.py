# -*- coding: utf-8 -*-
"""Quality Gate G2 (hoa văn) và G3 (thiết kế cuối) — ngưỡng đọc từ config.

Đầu ra của cổng KHÔNG phải "đạt/không đạt" chung chung mà là:
  · trạng thái từng chỉ số (PASS/WARN/FAIL) kèm giá trị và ngưỡng,
  · quyết định cổng (FAIL > WARN > PASS),
  · bước quay lại cụ thể trong quy trình BPMN (stage1_regenerate / stage2_repair),
  · việc tiếp theo cho người (QC Officer, Nhà thiết kế, Chuyên gia).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from . import metrics as M

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "quality_gate.json"
ORDER = {"PASS": 0, "WARN": 1, "FAIL": 2, "N/A": -1}


def load_config(path: Path = CONFIG) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def classify(value: float, rule: dict) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    if rule["direction"] == "higher_is_better":
        return "FAIL" if value < rule["fail"] else "WARN" if value < rule["warn"] else "PASS"
    return "FAIL" if value >= rule["fail"] else "WARN" if value >= rule["warn"] else "PASS"


def _decide(results: dict) -> str:
    worst = max((r["status"] for r in results.values()), key=lambda s: ORDER[s], default="PASS")
    return "PASS" if worst == "N/A" else worst


def evaluate_pattern(pattern: np.ndarray, reference: np.ndarray, cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    gate = cfg["gates"]["G2_pattern"]
    raw = {**M.vessel_leakage(pattern, reference), **M.seam_ratio(pattern)}
    results = {k: {"value": raw[k], "status": classify(raw[k], rule), "warn": rule["warn"],
                   "fail": rule["fail"], "label": rule["label"]}
               for k, rule in gate["metrics"].items()}
    decision = _decide(results)
    return {"gate": "G2_pattern", "decision": decision, "metrics": results, "details": raw,
            "next": gate["on_fail"] if decision == "FAIL" else None}


def evaluate_final(raw_img: np.ndarray, final: np.ndarray, template: np.ndarray,
                   layout_mask: np.ndarray, garment_prior: np.ndarray,
                   cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    gate = cfg["gates"]["G3_final"]
    pres = M.pattern_preservation(raw_img, final, template, layout_mask)
    shape = M.garment_shape_consistency(raw_img, final, garment_prior)
    vq = M.visual_quality(raw_img, final, garment_prior > 0)
    values = {**pres, **shape, **vq, **M.outside_drift(raw_img, final, garment_prior)}
    results = {k: {"value": values[k], "status": classify(values[k], rule), "warn": rule["warn"],
                   "fail": rule["fail"], "label": rule["label"]}
               for k, rule in gate["metrics"].items()}
    decision = _decide(results)
    failing = [k for k, r in results.items() if r["status"] == "FAIL"]
    routes = [{"metric": k, **gate["routing"][k]} for k in failing]
    return {"gate": "G3_final", "decision": decision, "metrics": results,
            "details": {k: v for k, v in values.items() if k not in results},
            "routes": routes}


def overall(g2: dict, g3: dict, cfg: dict | None = None) -> dict:
    """Gộp hai cổng thành quyết định chuyển tiếp trong quy trình."""
    cfg = cfg or load_config()
    if g2["decision"] == "FAIL":
        return {"decision": "FAIL", "route_to": "stage1_regenerate", "message": g2["next"]["action"],
                "eligible_for_expert": False}
    if g3["decision"] == "FAIL":
        return {"decision": "FAIL", "route_to": "stage2_repair",
                "message": "; ".join(r["action"] for r in g3["routes"]), "eligible_for_expert": False}
    worst = "WARN" if "WARN" in (g2["decision"], g3["decision"]) else "PASS"
    return {"decision": worst, "route_to": "qc_review" if worst == "WARN" else "expert_review",
            "message": cfg["decision"][worst], "eligible_for_expert": worst == "PASS"}
