"""Kiểm thử gói đánh giá mù (scripts/18_build_blind_review.py): đủ thiết kế, không lộ thông tin, khóa giải mã đúng."""
import csv
import importlib.util
import re
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("blind_review", ROOT / "scripts" / "18_build_blind_review.py")
BR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BR)


@pytest.fixture(scope="module")
def goi(tmp_path_factory):
    out = tmp_path_factory.mktemp("blind")
    return out, BR.build(out / "goi")


def test_du_so_thiet_ke_va_ma_khong_trung(goi):
    out, r = goi
    send, keep = out / "goi" / "GOI_GUI", out / "goi" / "GIU_RIENG"
    key = list(csv.DictReader((keep / "key.csv").open(encoding="utf-8-sig")))
    assert r["total"] == len(key) and len(key) >= 24
    codes = [k["code"] for k in key]
    assert len(set(codes)) == len(codes) and all(re.fullmatch(r"B\d{4}", c) for c in codes)
    assert sorted(p.stem for p in (send / "images").glob("*.png")) == sorted(codes)
    assert len({k["passport_id"] for k in key}) == len(key)


def test_goi_gui_khong_lo_thong_tin_nhan_dang(goi):
    out, _ = goi
    send = out / "goi" / "GOI_GUI"
    page = (send / "index.html").read_text(encoding="utf-8")
    for bad in ("DP-HV", "passport", "intensity", "qa_", "pending_expert", "garment_seed", "layout_ranking"):
        assert bad not in page, bad
    names = [p.name for p in send.rglob("*") if p.is_file()]
    assert not any(re.search(r"V\d|HV\d|R2026|LR3D|aodai|final|pattern", n) for n in names), names
    with zipfile.ZipFile(out / "goi" / "GOI_GUI.zip") as z:
        assert "index.html" in z.namelist() and not any("key" in n for n in z.namelist())


def test_khoa_giai_ma_o_thu_muc_rieng_va_co_ket_qua_cong(goi):
    out, _ = goi
    keep = out / "goi" / "GIU_RIENG"
    key = list(csv.DictReader((keep / "key.csv").open(encoding="utf-8-sig")))
    assert {"code", "passport_id", "heritage_id", "intensity_level", "g2", "g3", "approval"} <= set(key[0])
    assert {k["g2"] for k in key} <= {"PASS", "WARN", "FAIL"}
    assert not (out / "goi" / "GOI_GUI" / "key.csv").exists()


def test_vai_chuyen_gia_chia_dung_tieu_chi():
    import json
    rubric = json.loads((ROOT / "config" / "expert_rubric.json").read_text(encoding="utf-8"))
    roles = BR.role_criteria(rubric)
    assert roles["heritage"] == ["motif_recognizability", "cultural_appropriateness"]
    assert set(roles["design"]) == {"aesthetic", "garment_integrity", "looks_like_printed_fabric"}
    assert set(roles["both"]) == set(roles["heritage"]) | set(roles["design"])


def test_ten_hien_vat_bo_ma_bo_du_lieu():
    assert BR.plain_name("Hiện vật men lam: nét lam thưa trên men kem (LR3D-CULT2 #97)") == "Nét lam thưa trên men kem"


def test_dung_lai_ra_cung_ma_anh(tmp_path):
    a = BR.build(tmp_path / "a")["key"].read_text(encoding="utf-8-sig")
    b = BR.build(tmp_path / "b")["key"].read_text(encoding="utf-8-sig")
    assert a == b
