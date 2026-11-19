# -*- coding: utf-8 -*-
"""Module thí nghiệm: chặn kế hoạch nhiều biến, thống kê, chấm mù."""
from __future__ import annotations

import copy
import csv
import math
from pathlib import Path

import pytest

from evaluation import experiment as E

ROOT = Path(__file__).resolve().parent.parent
SPECS = sorted((ROOT / "evaluation" / "experiments").glob("EXP-*.json"))


@pytest.mark.parametrize("path,n", [("EXP-A_controlnet_weight.json", 120), ("EXP-B_stage2_finish.json", 72),
                                    ("EXP-C_composite_ablation.json", 48)])
def test_specs_expand_and_pass_validation(path, n):
    spec = E.load_spec(ROOT / "evaluation" / "experiments" / path)
    rows = E.expand_plan(spec)
    assert len(rows) == n
    assert len({r["run_key"] for r in rows}) == n, "khoá lượt chạy phải duy nhất"


def test_gpu_experiments_use_only_active_items():
    for p in SPECS:
        spec = E.load_spec(p)
        if spec.get("requires_gpu"):
            assert spec["units"]["heritage"] == "active"


def test_legacy_v1_v4_design_is_rejected():
    """Dựng lại đúng bộ 4 biến thể bản 09/2026: đổi trọng số + prompt + bảng màu + bố cục cùng lúc."""
    spec = E.load_spec(ROOT / "evaluation" / "experiments" / "EXP-A_controlnet_weight.json")
    rows = E.expand_plan(spec)
    legacy = {0.85: ("", "original", "side_stripe"), 0.65: ("", "free", "front_panel"),
              0.45: ("modern simplified interpretation", "free", "center_medallion"),
              0.25: ("bold contemporary reinterpretation", "free", "shoulder")}
    rows = [r for r in rows if r["cfg.seed"] == 42]
    for r in rows:
        mod, pal, lay = legacy[r["cfg.controlnet_weight"]]
        r["cfg.prompt_modifier"], r["cfg.palette_mode"], r["cfg.layout"] = mod, pal, lay
    with pytest.raises(E.PlanError) as err:
        E.validate_plan(spec, rows)
    assert "cfg.layout" in str(err.value) and "cfg.palette_mode" in str(err.value)


def test_plan_without_iv_variation_is_rejected():
    spec = copy.deepcopy(E.load_spec(ROOT / "evaluation" / "experiments" / "EXP-C_composite_ablation.json"))
    spec["independent_variable"]["levels"] = ["full"]
    with pytest.raises(E.PlanError):
        E.expand_plan(spec)


def test_describe_and_ci():
    d = E.describe([1.0, 2.0, 3.0, 4.0])
    assert d["n"] == 4 and d["mean"] == 2.5
    assert d["sd"] == pytest.approx(1.2910, abs=1e-4)
    assert d["ci95"][0] < 2.5 < d["ci95"][1]
    assert E.describe([]) == {"n": 0}


def test_krippendorff_alpha():
    perfect = [[1, 2, 3, 4, 5], [1, 2, 3, 4, 5], [1, 2, 3, 4, 5]]
    assert E.krippendorff_alpha_interval(perfect) == pytest.approx(1.0)
    # Ví dụ chuẩn của Krippendorff (dữ liệu khoảng, có ô thiếu) — alpha ≈ 0,849
    m = [[1, 2, 3, 3, 2, 1, 4, 1, 2, None, None, None],
         [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, None, 3],
         [None, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, None],
         [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, None]]
    assert E.krippendorff_alpha_interval(m) == pytest.approx(0.849, abs=0.002)
    assert math.isnan(E.krippendorff_alpha_interval([[None, None], [None, None]]))


def test_paired_tests_report_direction():
    rows = [{"heritage_id": f"H{i}", "replicate": "", "iv_level": lv, "m": str(v), "status": "completed"}
            for i in range(6) for lv, v in (("a", 1.0), ("b", 0.8 - i * 0.01))]
    out = E.paired_tests(rows, "m", ["a", "b"])
    assert out["vs_control"]["b"]["n_pairs"] == 6
    assert out["vs_control"]["b"]["median_diff"] < 0
    assert out["vs_control"]["b"]["wilcoxon_p"] == pytest.approx(0.0312, abs=1e-3)


def test_exp_c_results_and_blind_packet_hide_identity():
    out = ROOT / "outputs" / "experiments" / "EXP-C"
    results = list(csv.DictReader((out / "results.csv").open(encoding="utf-8")))
    assert len(results) == 24 and all(r["status"] == "completed" for r in results)
    assert all(r["cfg.stage2_finish"] == "none" for r in results), "EXP-C không có img2img"
    key = list(csv.DictReader((out / "blind" / "key.csv").open(encoding="utf-8")))
    sheet = list(csv.DictReader((out / "blind" / "ratings_CG01.csv").open(encoding="utf-8")))
    assert len(key) == len(sheet) == 24
    assert "iv_level" not in sheet[0] and "run_key" not in sheet[0]
    assert all(r["code"].startswith("B") for r in sheet)
    orders = [[r["code"] for r in csv.DictReader((out / "blind" / f"ratings_{x}.csv").open(encoding="utf-8"))]
              for x in ("CG01", "CG02", "CG03")]
    assert orders[0] != orders[1] or orders[1] != orders[2], "thứ tự phải xáo theo người chấm"
    assert all(not any(r[c] for c in ("aesthetic", "looks_like_printed_fabric")) for r in sheet), \
        "không được có điểm điền sẵn"


def test_blind_packet_is_reproducible(tmp_path):
    import shutil
    src = ROOT / "outputs" / "experiments" / "EXP-C"
    dst = tmp_path / "EXP-C"
    dst.mkdir()
    for f in ("results.csv", "spec.json", "plan.csv"):
        shutil.copy2(src / f, dst / f)
    shutil.copytree(src / "images", dst / "images")
    E.build_blind_packet(dst, ["CG01", "CG02", "CG03"])
    assert (dst / "blind" / "key.csv").read_text(encoding="utf-8") == (src / "blind" / "key.csv").read_text(encoding="utf-8")
