# -*- coding: utf-8 -*-
"""Lưu trữ tệp cho API: passport, phiếu thẩm định, bản chỉnh sửa, manifest run.

Giữ nguyên lựa chọn kiến trúc của dự án (tệp JSON/CSV, không cơ sở dữ liệu).
Ghi theo kiểu "ghi tệp tạm rồi đổi tên" để không bao giờ để lại passport nửa vời.
"""
from __future__ import annotations

import csv
import json
import os
import re
import threading
from pathlib import Path

from provenance import passport as P

ROOT = Path(__file__).resolve().parent.parent
PASSPORTS = ROOT / "outputs" / "passports"
RUNS = ROOT / "outputs" / "runs"
EDITS = ROOT / "outputs" / "edits"
EXPERIMENTS = ROOT / "outputs" / "experiments"
PASSPORT_ID = re.compile(r"^DP-[A-Z0-9]{2,8}-[0-9T]{8,15}-V[0-9]{1,2}$")
RUN_ID = re.compile(r"^R[0-9]{8}T[0-9]{6}-[A-Z0-9]{2,8}$")
FILE_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,80}\.png$")
_lock = threading.RLock()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _metric(q: dict, gate: str, key: str):
    return ((q.get(gate) or {}).get("metrics") or {}).get(key, {}).get("value")


def list_passports() -> list[dict]:
    out = []
    for f in sorted(PASSPORTS.glob("DP-*.json")):
        p = P.load(f)
        final = next((v for v in reversed(p["versions"])), None)
        q = p.get("quality") or {}
        out.append({
            "passport_id": p["passport_id"], "design_id": p["design_id"], "run_id": p["run_id"],
            "heritage_id": p["heritage"]["heritage_id"], "heritage_name": p["heritage"]["name"],
            "heritage_status": p["heritage"].get("status"), "created_at": p["created_at"],
            "approval": p["approval"], "versions": len(p["versions"]),
            "latest_version_kind": final["kind"] if final else None,
            "quality_decision": (q.get("overall") or {}).get("decision"),
            "repair_decision": ((q.get("repair") or {}).get("overall") or {}).get("decision"),
            "layout": p["generation"].get("layout", {}).get("label"),
            "controlnet_weight": p["generation"].get("controlnet", {}).get("conditioning_scale"),
            "seed": p["generation"].get("seed"), "reviews": len(p["reviews"]), "edits": len(p["edits"]),
            "final_path": p["versions"][0]["path"] if p["versions"] else None,
            "repair_path": next((v["path"] for v in p["versions"] if v["kind"] == "system_repair"), None),
            "latest_path": final["path"] if final else None,
            "g2": (q.get("G2_pattern") or {}).get("decision"), "g3": (q.get("G3_final") or {}).get("decision"),
            "pps": _metric(q, "G3_final", "pattern_preservation"), "gsc": _metric(q, "G3_final", "garment_shape_iou"),
            "vls": _metric(q, "G2_pattern", "vessel_leakage"),
            "repair_pps": _metric(q.get("repair") or {}, "G3_final", "pattern_preservation"),
        })
    return out


def get_passport(passport_id: str) -> dict | None:
    if not PASSPORT_ID.match(passport_id):
        return None
    path = PASSPORTS / f"{passport_id}.json"
    return P.load(path) if path.exists() else None


def save_passport(passport: dict) -> None:
    with _lock:
        _atomic_write(PASSPORTS / f"{passport['passport_id']}.json",
                      json.dumps(passport, ensure_ascii=False, indent=2) + "\n")


def mutate_passport(passport_id: str, fn):
    """Đọc – sửa – ghi trong khoá để hai yêu cầu đồng thời không ghi đè nhau."""
    with _lock:
        p = get_passport(passport_id)
        if p is None:
            return None
        result = fn(p)
        save_passport(p)
        return result


def list_runs() -> list[dict]:
    out = []
    for f in sorted(RUNS.glob("R*/manifest.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        out.append({"run_id": m["run_id"], "heritage_id": m["heritage_id"], "code": m.get("code"),
                    "designs": len(m.get("designs", [])), "created_at": m.get("created_at") or m.get("reconstructed_on"),
                    "source": m.get("source", "api")})
    return out


def get_run(run_id: str) -> dict | None:
    if not RUN_ID.match(run_id):
        return None
    path = RUNS / run_id / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def safe_run_file(run_id: str, filename: str) -> Path | None:
    if not RUN_ID.match(run_id) or not FILE_NAME.match(filename):
        return None
    path = (RUNS / run_id / filename).resolve()
    if path.parent != (RUNS / run_id).resolve() or not path.is_file():
        return None
    return path


def list_experiments() -> list[dict]:
    specs = sorted((ROOT / "evaluation" / "experiments").glob("EXP-*.json"))
    out = []
    for spec_path in specs:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        d = EXPERIMENTS / spec["id"]
        plan = d / "plan.csv"
        results = d / "results.csv"
        n_plan = sum(1 for _ in csv.DictReader(plan.open(encoding="utf-8"))) if plan.exists() else 0
        n_res = sum(1 for _ in csv.DictReader(results.open(encoding="utf-8"))) if results.exists() else 0
        blind = d / "blind"
        ratings = list(blind.glob("ratings_*.csv")) if blind.exists() else []
        filled = 0
        for r in ratings:
            filled += sum(1 for row in csv.DictReader(r.open(encoding="utf-8"))
                          if any(v.strip() for k, v in row.items() if k not in ("rater_id", "code", "heritage_reference", "comment")))
        status = "completed" if n_res and filled else "awaiting_ratings" if n_res else "planned" if n_plan else "draft"
        out.append({"id": spec["id"], "title": spec["title"], "question": spec["question"], "why": spec.get("why"),
                    "design": spec.get("design"), "independent_variable": spec["independent_variable"],
                    "replicates": spec.get("replicates"), "fixed": spec["fixed"],
                    "requires_gpu": spec.get("requires_gpu", False), "metrics": spec.get("metrics"),
                    "planned_runs": n_plan, "completed_runs": n_res, "raters": len(ratings),
                    "filled_ratings": filled, "status": status})
    return out
