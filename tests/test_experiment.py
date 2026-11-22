# -*- coding: utf-8 -*-
"""Module thí nghiệm: chặn kế hoạch nhiều biến, thống kê, chấm mù."""
from __future__ import annotations

import copy
import csv
import math
from pathlib import Path

import pytest

from tsds.evaluation import experiment as E

ROOT = Path(__file__).resolve().parent.parent
SPECS = sorted((ROOT / "tsds" / "evaluation" / "experiments").glob("EXP-*.json"))


@pytest.mark.parametrize("path,n", [("EXP-A_controlnet_weight.json", 120), ("EXP-B_stage2_finish.json", 126),
                                    ("EXP-D_garment_source.json", 60),
                                    ("EXP-E_pattern_source.json", 36)])
def test_specs_expand_and_pass_validation(path, n):
    spec = E.load_spec(ROOT / "tsds" / "evaluation" / "experiments" / path)
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
    spec = E.load_spec(ROOT / "tsds" / "evaluation" / "experiments" / "EXP-A_controlnet_weight.json")
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
    spec = copy.deepcopy(E.load_spec(ROOT / "tsds" / "evaluation" / "experiments" / "EXP-B_stage2_finish.json"))
    spec["independent_variable"]["levels"] = spec["independent_variable"]["levels"][:1]
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


def _bo_ket_qua_gia(tmp_path, n=12):
    """Thư mục thí nghiệm giả: n lượt, hai mức, ảnh nhỏ; đủ để dựng gói chấm mù."""
    import json
    from PIL import Image
    (tmp_path / "images").mkdir()
    rows = []
    for i in range(n):
        name = f"images/r{i}.png"
        Image.new("RGB", (8, 8), (i * 10, 0, 0)).save(tmp_path / name)
        rows.append({"run_key": f"k{i}", "heritage_id": f"H{i % 3}", "iv_level": "a" if i % 2 else "b",
                     "replicate": str(42 + i % 2), "status": "completed", "image": name})
    E.write_results(rows, tmp_path)
    spec = {"id": "EXP-T", "metrics": {"human": ["aesthetic", "looks_like_printed_fabric"], "automatic": []},
            "independent_variable": {"name": "x", "levels": ["a", "b"]}}
    (tmp_path / "spec.json").write_text(json.dumps(spec), encoding="utf-8")


def test_blind_packet_hide_identity(tmp_path):
    _bo_ket_qua_gia(tmp_path)
    blind = E.build_blind_packet(tmp_path, ["CG01", "CG02", "CG03"])
    key = list(csv.DictReader((blind / "key.csv").open(encoding="utf-8")))
    sheet = list(csv.DictReader((blind / "ratings_CG01.csv").open(encoding="utf-8")))
    assert len(key) == len(sheet) == 12
    assert "iv_level" not in sheet[0] and "run_key" not in sheet[0]
    assert all(r["code"].startswith("B") for r in sheet)
    orders = [[r["code"] for r in csv.DictReader((blind / f"ratings_{x}.csv").open(encoding="utf-8"))]
              for x in ("CG01", "CG02", "CG03")]
    assert orders[0] != orders[1] or orders[1] != orders[2], "thứ tự phải xáo theo người chấm"
    assert all(not any(r[c] for c in ("aesthetic", "looks_like_printed_fabric")) for r in sheet),         "không được có điểm điền sẵn"


def test_blind_packet_is_reproducible(tmp_path):
    _bo_ket_qua_gia(tmp_path)
    E.build_blind_packet(tmp_path, ["CG01", "CG02"])
    first = (tmp_path / "blind" / "key.csv").read_text(encoding="utf-8")
    E.build_blind_packet(tmp_path, ["CG01", "CG02"])
    assert (tmp_path / "blind" / "key.csv").read_text(encoding="utf-8") == first


@pytest.mark.parametrize("finish,expected", [
    ("none", ("none", 0.0, False)),
    ("img2img_0.40", ("img2img", 0.40, False)),
    ("img2img_0.40+pattern_lock", ("img2img", 0.40, True)),
    ("masked_0.30", ("masked", 0.30, False)),
    ("masked_0.25+pattern_lock", ("masked", 0.25, True)),
])
def test_parse_finish_hop_le(finish, expected):
    assert E.parse_finish(finish) == expected


@pytest.mark.parametrize("finish", ["", "img2img", "img2img_abc", "masked_0", "masked_1.5", "inpaint_0.3",
                                    "masked_0.30+khoa", "masked_0.30+pattern_lock+x"])
def test_parse_finish_khong_hop_le(finish):
    with pytest.raises(ValueError):
        E.parse_finish(finish)


def test_exp_b_co_muc_polish_co_mat_na_va_moi_muc_deu_doc_duoc():
    spec = E.load_spec(ROOT / "tsds" / "evaluation" / "experiments" / "EXP-B_stage2_finish.json")
    levels = spec["independent_variable"]["levels"]
    assert "masked_0.30" in levels
    for lv in levels:
        E.parse_finish(lv)


# ---------------------------------------------------------------- EXP-D: nền áo ----

def _spec_d():
    return E.load_spec(ROOT / "tsds" / "evaluation" / "experiments" / "EXP-D_garment_source.json")


def test_exp_d_chi_doi_nen_ao_va_cung_hoa_van_giua_hai_muc():
    rows = E.expand_plan(_spec_d())
    assert {r["iv_level"] for r in rows} == {"fixed", "lora"}
    assert {r["replicate"] for r in rows} == {42, 43, 44, 45, 46}
    assert len({r["heritage_id"] for r in rows}) == 6
    # Cùng hiện vật và seed: hai mức chỉ khác garment_source
    a = next(r for r in rows if r["iv_level"] == "fixed" and r["heritage_id"] == rows[0]["heritage_id"] and r["replicate"] == 44)
    b = next(r for r in rows if r["iv_level"] == "lora" and r["heritage_id"] == a["heritage_id"] and r["replicate"] == 44)
    diff = {k for k in a if k.startswith("cfg.") and a[k] != b[k]}
    assert diff == {"cfg.garment_source"}


def test_lora_garment_seeds_chi_lay_muc_lora_va_khong_trung():
    rows = E.expand_plan(_spec_d())
    assert E.lora_garment_seeds(rows) == [42, 43, 44, 45, 46]
    assert E.lora_garment_seeds([r for r in rows if r["iv_level"] == "fixed"]) == []


def test_pregenerate_garments_ghi_loi_khong_quay_ve_ao_mau(tmp_path):
    from tsds.generation.garment.garment_lora import GarmentError

    def gia(d, seed):
        if seed == 43:
            raise GarmentError("mọi ứng viên bị loại")
        return {"path": d / "garment.png", "seed": seed}

    out = E.pregenerate_garments([42, 43], tmp_path, generate=gia)
    assert out[42]["ok"] and out[42]["info"]["path"] == tmp_path / "garments" / "seed_42" / "garment.png"
    assert not out[43]["ok"] and "bị loại" in out[43]["error"]


def test_gach_cham_mu_bo_luot_khong_ra_anh_va_analyze_dem_trang_thai(tmp_path):
    from PIL import Image
    (tmp_path / "images").mkdir()
    Image.new("RGB", (8, 8)).save(tmp_path / "images" / "a.png")
    spec = _spec_d()
    (tmp_path / "spec.json").write_text(__import__("json").dumps(spec), encoding="utf-8")
    rows = [
        {"run_key": "k1", "heritage_id": "H1", "iv_level": "fixed", "replicate": "42", "status": "completed",
         "image": "images/a.png", "garment_shape_iou": "0.99"},
        {"run_key": "k2", "heritage_id": "H1", "iv_level": "lora", "replicate": "43", "status": "garment_failed",
         "image": "", "garment_shape_iou": ""},
    ]
    E.write_results(rows, tmp_path)
    E.build_blind_packet(tmp_path, ["CG01"])
    key = list(csv.DictReader((tmp_path / "blind" / "key.csv").open(encoding="utf-8")))
    assert len(key) == 1 and key[0]["iv_level"] == "fixed"
    summary = E.analyze(tmp_path)
    assert summary["status_counts"] == {"fixed": {"completed": 1}, "lora": {"garment_failed": 1}}


def test_source_prepared_nho_lai_theo_hien_vat_va_nguon(monkeypatch):
    from tsds.generation.pattern import controlnet as cn
    calls = []
    monkeypatch.setattr(cn, "prepare", lambda hid, **kw: calls.append((hid, kw.get("image_path"))) or {"x": len(calls)})
    cache = {}
    a = E.source_prepared(cache, "LR3D_61", "panel")
    b = E.source_prepared(cache, "LR3D_61", "panel")
    c = E.source_prepared(cache, "LR3D_61", "render")
    assert a is b and a is not c and len(calls) == 2
    assert calls[0][1] is not None and calls[0][1].name == "LR3D_61.png"      # mảng phẳng
    assert calls[1][1] is None                                                 # ảnh bình render mặc định
