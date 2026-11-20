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


def _thiet_ke_gia(tmp_path, seeds=(42, 43, 44), heritage=("LR3D_33", "LR3D_61"), levels=(1, 2)):
    """Thiết kế giả: mỗi (hiện vật, mức) có một thiết kế cho mỗi seed, ảnh nhỏ màu khác nhau."""
    from PIL import Image
    rows = []
    for h in heritage:
        for lv in levels:
            for sd in seeds:
                img = tmp_path / f"{h}_{lv}_{sd}.png"
                Image.new("RGB", (40, 60), (sd, lv * 40, 90)).save(img)
                rows.append({"passport_id": f"DP-{h}-{lv}-{sd}", "run_id": f"R{sd}", "heritage_id": h, "image": img,
                             "intensity_level": lv, "seed": sd, "layout": "front_panel", "garment_seed": sd,
                             "g2": "PASS", "g3": "PASS", "approval": "pending_expert_review"})
    return rows


def test_nhieu_seed_gom_theo_o_va_khoa_giai_ma_co_seed(tmp_path):
    out = tmp_path / "goi"
    r = BR.build(out, designs=_thiet_ke_gia(tmp_path))
    assert r["total"] == 12 and r["per_rater"] == 4              # 4 ô (2 hiện vật x 2 mức), mỗi ô 3 seed
    key = list(csv.DictReader((out / "GIU_RIENG" / "key.csv").open(encoding="utf-8-sig")))
    assert {"seed", "run_id", "cell"} <= set(key[0])
    cells = {}
    for k in key:
        cells.setdefault(k["cell"], set()).add(k["seed"])
    assert len(cells) == 4 and all(s == {"42", "43", "44"} for s in cells.values())
    page = (out / "GOI_GUI" / "index.html").read_text(encoding="utf-8")
    data_json = re.search(r"const DATA = (\{.*\});", page).group(1)      # dữ liệu nhúng trong trang (JS dùng chữ "seed" cho bộ xáo nên không dò cả trang)
    for bad in ("seed", "intensity", "DP-LR3D", "run_id", "garment_seed", "R42", "R43", "R44"):
        assert bad not in data_json, bad                         # trang gửi không lộ seed, mức sáng tạo hay mã Passport


@pytest.mark.skipif(__import__("shutil").which("node") is None, reason="cần Node.js")
def test_moi_nguoi_cham_thay_mot_thiet_ke_moi_o_va_ba_nguoi_phu_het_seed(tmp_path):
    import json
    import subprocess
    out = tmp_path / "goi"
    BR.build(out, designs=_thiet_ke_gia(tmp_path))
    page = (out / "GOI_GUI" / "index.html").read_text(encoding="utf-8")
    seed_from = next(l for l in page.splitlines() if l.startswith("function seedFrom"))
    block = page[page.index("// --- chọn thiết kế cho người chấm"):page.index("// --- hết khối chọn thiết kế ---")]
    items = json.loads(re.search(r"const DATA = (\{.*\});", page).group(1))["items"]
    js = seed_from + "\n" + block + f"\nconst items = {json.dumps(items)};\n" \
        "const out = {}; for (const id of ['CG01','CG02','CG03','CG04','CG06']) out[id] = pickForRater(items, id).map((x) => x.code);\n" \
        "console.log(JSON.stringify(out));"
    res = subprocess.run(["node", "-e", js], capture_output=True, text=True, encoding="utf-8", check=True)
    picked = json.loads(res.stdout)
    cell_of = {it["code"]: it["cell"] for it in items}
    for codes in picked.values():
        assert len(codes) == 4 and sorted(cell_of[c] for c in codes) == sorted(set(cell_of.values()))   # một thiết kế mỗi ô
    # CG01, CG02, CG03 liên tiếp: mỗi thiết kế được đúng một người trong ba người thấy
    all_codes = sorted(c for k in ("CG01", "CG02", "CG03") for c in picked[k])
    assert all_codes == sorted(cell_of) and len(all_codes) == 12
    assert picked["CG01"] == picked["CG04"] and picked["CG03"] == picked["CG06"]    # lệch ba thì quay lại chu kỳ


def test_mot_seed_thi_nguoi_cham_thay_het_nhu_cu(tmp_path):
    out = tmp_path / "goi"
    r = BR.build(out, designs=_thiet_ke_gia(tmp_path, seeds=(42,)))
    assert r["total"] == 4 and r["per_rater"] == 4
