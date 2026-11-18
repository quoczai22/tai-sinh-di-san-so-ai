# -*- coding: utf-8 -*-
"""Cổng chất lượng G2/G3, khoá họa tiết, và hồi quy trên 24 thiết kế thật."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from quality import gate as QG
from quality import metrics as M
from quality.repair import pattern_lock

ROOT = Path(__file__).resolve().parent.parent
CFG = QG.load_config()


# ----------------------------------------------------------------- ngưỡng ---

@pytest.mark.parametrize("value,expect", [(0.80, "PASS"), (0.60, "PASS"), (0.59, "WARN"), (0.40, "WARN"), (0.39, "FAIL")])
def test_classify_higher_is_better(value, expect):
    assert QG.classify(value, CFG["gates"]["G3_final"]["metrics"]["pattern_preservation"]) == expect


@pytest.mark.parametrize("value,expect", [(0.0, "PASS"), (0.19, "PASS"), (0.20, "WARN"), (0.40, "FAIL")])
def test_classify_lower_is_better(value, expect):
    assert QG.classify(value, CFG["gates"]["G2_pattern"]["metrics"]["vessel_leakage"]) == expect


def test_nan_is_not_a_pass_or_fail():
    assert QG.classify(float("nan"), CFG["gates"]["G3_final"]["metrics"]["sharpness_ratio"]) == "N/A"


def test_config_is_marked_provisional_and_never_approves():
    assert CFG["status"] == "provisional"
    assert "Không chỉ số nào tự phê duyệt" in CFG["principle"]
    from quality.assess import approval_from_assessment
    best = {"overall": {"decision": "PASS", "message": ""}, "repair": None}
    assert approval_from_assessment(best)[0] == "pending_expert_review"


def test_overall_routing():
    ok = {"decision": "PASS", "next": None}
    bad = {"decision": "FAIL", "next": {"action": "x"}}
    g3_fail = {"decision": "FAIL", "routes": [{"action": "y"}]}
    assert QG.overall(bad, {"decision": "PASS"})["route_to"] == "stage1_regenerate"
    assert QG.overall(ok, g3_fail)["route_to"] == "stage2_repair"
    assert QG.overall(ok, {"decision": "WARN"})["route_to"] == "qc_review"
    assert QG.overall(ok, {"decision": "PASS"})["route_to"] == "expert_review"


# ------------------------------------------------------ phép đo tổng hợp ---

def _scene(rng, size=256):
    """Áo trắng (template) + vùng in có họa tiết nét mảnh, màu."""
    template = np.full((size, size, 3), 245, np.uint8)
    mask = np.zeros((size, size), np.float32)
    mask[48:208, 64:192] = 1.0
    yy, xx = np.mgrid[0:size, 0:size]
    motif = (np.sin(xx / 5.0) * np.cos(yy / 7.0) > 0.2)
    raw = template.copy()
    raw[(mask > 0) & motif] = (36, 80, 138)
    raw[(mask > 0) & ~motif] = (210, 170, 90)
    return template, mask, raw


def test_pps_identical_is_one(rng):
    template, mask, raw = _scene(rng)
    r = M.pattern_preservation(raw, raw.copy(), template, mask)
    assert r["pattern_preservation"] > 0.99


def test_pps_drops_when_motif_redrawn(rng):
    template, mask, raw = _scene(rng)
    final = raw.copy()
    noise = rng.integers(0, 2, raw.shape[:2]).astype(bool)
    region = mask > 0
    final[region & noise] = (36, 80, 138)
    final[region & ~noise] = (210, 170, 90)
    r = M.pattern_preservation(raw, final, template, mask)
    assert r["pattern_preservation"] < CFG["gates"]["G3_final"]["metrics"]["pattern_preservation"]["fail"]


def test_pattern_lock_restores_motif(rng):
    template, mask, raw = _scene(rng)
    # "img2img": cùng ánh sáng tần thấp, nét vẽ bị thay bằng nét khác
    redrawn = raw.copy()
    alt = (np.sin(np.arange(256)[None, :] / 3.0) > 0)[np.zeros((256, 1), int), np.arange(256)[None, :]]
    alt = np.broadcast_to(alt, (256, 256))
    redrawn[(mask > 0) & alt] = (40, 84, 140)
    redrawn[(mask > 0) & ~alt] = (205, 168, 92)
    before = M.pattern_preservation(raw, redrawn, template, mask)["pattern_preservation"]
    locked, info = pattern_lock(raw, redrawn, mask)
    after = M.pattern_preservation(raw, locked, template, mask)["pattern_preservation"]
    assert after > before + 0.2
    assert info["method"] == "pattern_lock_v1"
    assert locked.shape == raw.shape and locked.dtype == np.uint8


def test_seam_ratio_tileable_vs_broken(rng):
    # Nhiễu tuần hoàn (lọc tần thấp trong miền Fourier) lát liền mạch theo cấu tạo
    f = np.fft.fft2(rng.normal(size=(256, 256)))
    ky, kx = np.meshgrid(np.fft.fftfreq(256), np.fft.fftfreq(256), indexing="ij")
    field = np.real(np.fft.ifft2(f * np.exp(-(kx ** 2 + ky ** 2) / (2 * 0.03 ** 2))))
    field = (field - field.min()) / (field.max() - field.min()) * 220 + 15
    tileable = np.stack([field] * 3, -1).astype(np.uint8)
    broken = tileable.copy()
    broken[:, -6:] = 255
    broken[:, :6] = 0
    seam = CFG["gates"]["G2_pattern"]["metrics"]["seam_ratio"]
    assert M.seam_ratio(tileable)["seam_ratio"] < seam["warn"]
    assert M.seam_ratio(broken)["seam_ratio"] >= seam["fail"]


def test_sharpness_ratio_detects_blur(rng):
    template, mask, raw = _scene(rng)
    blurred = cv2.GaussianBlur(raw, (0, 0), 3)
    r = M.visual_quality(raw, blurred, mask > 0)
    assert r["sharpness_ratio"] < CFG["gates"]["G3_final"]["metrics"]["sharpness_ratio"]["fail"]


# --------------------------------------------- hồi quy trên dữ liệu thật ---

LEGACY = {r["passport_id"]: r for r in csv.DictReader((ROOT / "evaluation" / "quality_gate_legacy.csv").open(encoding="utf-8"))}


def test_legacy_summary_counts():
    rows = list(LEGACY.values())
    assert len(rows) == 24
    count = lambda k, v: sum(r[k] == v for r in rows)   # noqa: E731
    assert (count("G2", "PASS"), count("G2", "WARN"), count("G2", "FAIL")) == (21, 1, 2)
    assert (count("G3", "PASS"), count("G3", "WARN"), count("G3", "FAIL")) == (0, 4, 20)
    assert (count("repair_G3", "PASS"), count("repair_G3", "WARN")) == (10, 9)


@pytest.mark.parametrize("pid", ["DP-HV01-20260906-V2", "DP-HV03-20260906-V2", "DP-HV04-20260906-V2"])
def test_recompute_matches_recorded(pid, tmp_path):
    """Đo lại từ tệp gốc phải ra đúng con số đã ghi (phát hiện thay đổi ngoài ý muốn ở phép đo)."""
    from quality.assess import assess_design
    p = json.loads((ROOT / "outputs" / "passports" / f"{pid}.json").read_text(encoding="utf-8"))
    art = {a["role"]: ROOT / a["path"] for a in p["artifacts"]}
    res = assess_design(reference=art["reference_512"], pattern=art["pattern"], raw=art["composite_raw"],
                        final=art["final_img2img"], layout=p["generation"]["layout"]["name"],
                        repair_dir=tmp_path, repair_name="r.png")
    row = LEGACY[pid]
    g2, g3 = res["G2_pattern"]["metrics"], res["G3_final"]["metrics"]
    assert g2["vessel_leakage"]["value"] == pytest.approx(float(row["vessel_leakage"]), abs=1e-3)
    assert g3["pattern_preservation"]["value"] == pytest.approx(float(row["pattern_preservation"]), abs=1e-3)
    assert g3["garment_shape_iou"]["value"] == pytest.approx(float(row["garment_shape_iou"]), abs=2e-3)
    assert res["overall"]["decision"] == row["overall"]
    if row["repair_pps"]:
        assert res["repair"]["G3_final"]["metrics"]["pattern_preservation"]["value"] == pytest.approx(float(row["repair_pps"]), abs=2e-3)
