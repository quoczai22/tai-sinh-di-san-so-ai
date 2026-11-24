"""Kiểm thử gói Google Form chấm mù (scripts/eval/build_google_form.py) bằng một thí nghiệm giả nhỏ, không cần GPU hay dữ liệu thật."""
import csv
import importlib.util
import json
import re
import shutil
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("google_form", ROOT / "scripts" / "eval" / "build_google_form.py")
GF = importlib.util.module_from_spec(spec)
spec.loader.exec_module(GF)

HERITAGE = ["LR3D_33", "LR3D_38"]
WEIGHTS = ["0.85", "0.25"]
SEEDS = [42, 7, 123]


def _img(path: Path, size: tuple, color: tuple) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


@pytest.fixture(scope="module")
def goi(tmp_path_factory):
    """Thí nghiệm giả: 2 hiện vật x 2 trọng số x 3 seed, kèm ảnh hiện vật và mảng phẳng giả."""
    root = tmp_path_factory.mktemp("root")
    exp = root / "exp"
    (exp / "images").mkdir(parents=True)
    (root / "config").mkdir()
    (root / "config" / "expert_rubric.json").write_text((ROOT / "config" / "expert_rubric.json").read_text(encoding="utf-8"), encoding="utf-8")
    (exp / "spec.json").write_text(json.dumps({"id": "EXP-T", "metrics": {"human": ["motif_recognizability", "aesthetic"]}}), encoding="utf-8")
    rows = []
    for h in HERITAGE:
        _img(root / "data" / "heritage" / "cutouts" / f"{h}.png", (60, 80), (200, 200, 220))
        _img(root / "data" / "heritage" / "panels" / f"{h}.png", (200, 220), (180, 200, 230))
        for w in WEIGHTS:
            for s in SEEDS:
                stem = f"EXP-T__{h}__w-{w}__seed-{s}"
                _img(exp / "images" / f"{stem}__final.png", (64, 86), (250, 250, 250))
                _img(exp / "images" / f"{stem}__pattern.png", (64, 64), (30, 60, 140))
                rows.append({"run_key": f"EXP-T|{h}|w={w}|seed={s}", "heritage_id": h, "iv_level": w, "replicate": s,
                             "status": "completed", "image": f"images/{stem}__final.png"})
    with (exp / "results.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w_ = csv.DictWriter(f, fieldnames=list(rows[0]))
        w_.writeheader()
        w_.writerows(rows)
    out = root / "out"
    r = GF.build(exp, out, SEEDS, root=root)
    key = list(csv.DictReader((out / "key.csv").open(encoding="utf-8-sig")))
    return out, r, key


def test_so_ban_va_so_thiet_ke(goi):
    out, r, key = goi
    cells = len(HERITAGE) * len(WEIGHTS)
    assert r["versions"] == len(SEEDS) and r["per_version"] == cells
    assert len(key) == cells * len(SEEDS) == r["images"] == len(list((out / "images").glob("*.jpg")))


def test_moi_o_dung_mot_lan_moi_ban_va_seed_khac_nhau_giua_cac_ban(goi):
    _, _, key = goi
    for v in "ABC":
        cells = [(k["heritage_id"], k["controlnet_weight"]) for k in key if k["version"] == v]
        assert len(cells) == len(set(cells)) == len(HERITAGE) * len(WEIGHTS)
    used = {(k["heritage_id"], k["controlnet_weight"], k["seed"]) for k in key}
    assert len(used) == len(key)                                      # mỗi (ô, seed) dùng đúng một lần: các bản không thấy cùng thiết kế
    for h in HERITAGE:
        for w in WEIGHTS:
            seeds = [k["seed"] for k in key if k["heritage_id"] == h and k["controlnet_weight"] == w]
            assert sorted(seeds) == sorted(str(s) for s in SEEDS)


def test_ma_anh_khong_trung_va_khop_tep(goi):
    out, _, key = goi
    codes = [k["code"] for k in key]
    assert len(set(codes)) == len(codes) and all(re.fullmatch(r"B\d{4}", c) for c in codes)
    assert sorted(p.stem for p in (out / "images").glob("*.jpg")) == sorted(codes)


def test_thu_tu_trong_form_spec_khop_key(goi):
    out, _, key = goi
    spec_ = json.loads((out / "form_spec.json").read_text(encoding="utf-8"))
    for v in spec_["versions"]:
        in_key = [k["code"] for k in sorted((k for k in key if k["version"] == v["name"]), key=lambda k: int(k["position"]))]
        assert [i["code"] for i in v["items"]] == in_key
        assert all(i["file"] == i["code"] + ".jpg" for i in v["items"])


def test_goi_gui_khong_lo_thong_tin_nhan_dang(goi):
    out, _, _ = goi
    for name in ("Code.gs", "form_spec.json"):
        text = (out / name).read_text(encoding="utf-8")
        for bad in ("controlnet", "LR3D", "EXP-T", "seed", "0.85", "0.25", "__final", "__pattern", "run_key"):
            assert bad not in text, (name, bad)
    assert not any(re.search(r"LR3D|EXP|final|pattern|seed", p.name) for p in (out / "images").iterdir())


def test_code_gs_nhung_spec_hop_le_va_chi_hien_tieu_chi_cua_thi_nghiem(goi):
    out, _, _ = goi
    gs = (out / "Code.gs").read_text(encoding="utf-8")
    assert "__SPEC__" not in gs and "const FOLDER_ID" in gs and "function createForms" in gs
    body = re.search(r"const SPEC = (\{.*?\n\});\n", gs, re.S).group(1)
    spec_ = json.loads(body)                                          # phần nhúng phải là JSON hợp lệ
    assert [c["key"] for c in spec_["criteria"]] == ["motif_recognizability", "aesthetic"]
    assert len(spec_["scale"]) == 5


def test_anh_ghep_dung_kich_thuoc_va_khong_phai_anh_trong(goi):
    out, _, key = goi
    im = Image.open(out / "images" / f"{key[0]['code']}.jpg")
    assert im.size == (1200, 1300)
    assert len(set(im.resize((60, 65)).getdata())) > 5                # có nội dung, không phải một màu


def test_chon_theo_ban_khi_it_ban_hon_seed(tmp_path):
    """Dùng ít bản hơn số seed: mỗi bản vẫn một thiết kế mỗi ô, chỉ dựng ảnh cho thiết kế được chọn."""
    designs = [{"heritage_id": h, "intensity_level": w, "seed": s, "passport_id": f"{h}|{w}|{s}"}
               for h in HERITAGE for w in WEIGHTS for s in SEEDS]
    for v in range(2):
        pick = GF.pick_for_version(designs, v)
        assert len(pick) == 4 and len({(d["heritage_id"], d["intensity_level"]) for d in pick}) == 4
    assert all(a["seed"] != b["seed"] for a, b in zip(GF.pick_for_version(designs, 0), GF.pick_for_version(designs, 1)))


def test_dung_lai_ra_cung_goi(goi, tmp_path):
    out, _, key = goi
    root = out.parent
    GF.build(root / "exp", tmp_path / "again", SEEDS, root=root)
    again = list(csv.DictReader((tmp_path / "again" / "key.csv").open(encoding="utf-8-sig")))
    assert [(k["version"], k["code"], k["run_key"]) for k in again] == [(k["version"], k["code"], k["run_key"]) for k in key]


def test_mang_phang_trong_suot_khong_ra_nen_den(tmp_path):
    """Mảng phẳng RGBA có vùng trong suốt mà RGB ẩn bên dưới là màu đen: ảnh ghép phải dùng alpha, không để nền đen."""
    panel = tmp_path / "panel.png"
    Image.new("RGBA", (200, 220), (0, 0, 0, 0)).save(panel)            # toàn trong suốt, RGB ẩn là đen
    for name, size in (("vessel.png", (60, 80)), ("pat.png", (64, 64)), ("fin.png", (64, 86))):
        Image.new("RGB", size, (255, 255, 255)).save(tmp_path / name)
    im = GF.compose(tmp_path / "vessel.png", panel, tmp_path / "pat.png", tmp_path / "fin.png")
    r, g, b = im.getpixel((40 + 270, 76 + 210))                        # giữa ô mảng phẳng
    assert min(r, g, b) > 200


def test_o_thieu_seed_thi_bao_loi_thay_vi_lap_am_tham():
    designs = [{"heritage_id": "H", "intensity_level": "1", "seed": s, "passport_id": f"H|1|{s}"} for s in (42, 7)]
    with pytest.raises(ValueError, match="không đủ"):
        GF.pick_for_version(designs, 2)


def test_seed_khong_gan_voi_chan_le_cua_muc():
    """Với 4 mức và 2 seed, seed bản A không được là một kiểu cố định theo chẵn lẻ của mức ở mọi hiện vật."""
    designs = [{"heritage_id": h, "intensity_level": str(w), "seed": s, "passport_id": f"{h}|{w}|{s}"}
               for h in ("H1", "H2", "H3", "H4", "H5", "H6") for w in range(4) for s in (42, 7)]
    first = GF.pick_for_version(designs, 0)
    pattern = {tuple(d["seed"] for d in first[i:i + 4]) for i in range(0, 24, 4)}
    assert len(pattern) > 1


def test_tu_choi_xoa_thu_muc_khong_phai_goi_cu(goi, tmp_path):
    _, _, _ = goi
    foreign = tmp_path / "du_lieu_khac"
    foreign.mkdir()
    (foreign / "quan_trong.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="từ chối xóa"):
        GF.build(goi[0].parent / "exp", foreign, SEEDS, root=goi[0].parent)
    assert (foreign / "quan_trong.txt").exists()


def test_ten_anh_ao_sai_duoi_thi_bao_loi():
    with pytest.raises(ValueError, match="__final.png"):
        GF.pattern_path(Path("a/b/anh_ao.png"))


def test_tieu_de_form_khong_lo_ban():
    gs = GF.APPS_SCRIPT
    assert "FormApp.create(SPEC.title)" in gs and "' (bản '" not in gs


def test_mot_form_chua_moi_thiet_ke_cua_moi_seed(goi, tmp_path):
    """one_form=True: đúng một bản, chứa đủ mọi (hiện vật, trọng số, seed), không bỏ sót hay lặp."""
    root = goi[0].parent
    r = GF.build(root / "exp", tmp_path / "one", SEEDS, root=root, one_form=True)
    key = list(csv.DictReader((tmp_path / "one" / "key.csv").open(encoding="utf-8-sig")))
    assert r["versions"] == 1 and r["per_version"] == r["images"] == len(key) == len(HERITAGE) * len(WEIGHTS) * len(SEEDS)
    assert {k["version"] for k in key} == {"A"}
    assert len({(k["heritage_id"], k["controlnet_weight"], k["seed"]) for k in key}) == len(key)
    assert [k["position"] for k in key] == [str(i) for i in range(1, len(key) + 1)]
    spec_ = json.loads((tmp_path / "one" / "form_spec.json").read_text(encoding="utf-8"))
    assert len(spec_["versions"]) == 1 and len(spec_["versions"][0]["items"]) == len(key)


def test_gop_nhieu_thiet_ke_moi_trang(goi, tmp_path):
    """per_page đi vào form_spec.json và Code.gs chỉ ngắt trang theo perPage, không còn ngắt trang cho từng thiết kế."""
    root = goi[0].parent
    GF.build(root / "exp", tmp_path / "p", SEEDS, root=root, one_form=True, per_page=6)
    spec_ = json.loads((tmp_path / "p" / "form_spec.json").read_text(encoding="utf-8"))
    assert spec_["perPage"] == 6
    gs = (tmp_path / "p" / "Code.gs").read_text(encoding="utf-8")
    assert gs.count("addPageBreakItem") == 1 and "SPEC.perPage > 0" in gs
    with pytest.raises(ValueError, match="âm"):
        GF.build(root / "exp", tmp_path / "q", SEEDS, root=root, per_page=-1)


# ---------------- chế độ chuyên gia ----------------
@pytest.fixture(scope="module")
def chuyen_gia(goi, tmp_path_factory):
    """Phiếu chuyên gia trên thí nghiệm giả: chỉ mức 0.85 của hai hiện vật, seed 42 và 7, tiêu chí đủ hai vai."""
    root = goi[0].parent
    exp = root / "exp_expert"                                          # bản sao riêng để không đổi spec.json dùng chung
    shutil.copytree(root / "exp", exp)
    (exp / "spec.json").write_text(json.dumps({"id": "EXP-T", "metrics": {"human": [
        "motif_recognizability", "cultural_appropriateness", "aesthetic", "garment_integrity"]}}), encoding="utf-8")
    out = tmp_path_factory.mktemp("exp") / "gf"
    r = GF.build(exp, out, [42], root=root, audience="expert", levels=[0.85])
    key = list(csv.DictReader((out / "key.csv").open(encoding="utf-8-sig")))
    return out, r, key


def test_expert_hai_form_dung_chung_cung_tap_anh(chuyen_gia):
    out, r, key = chuyen_gia
    assert r["versions"] == 2 and r["per_version"] == len(HERITAGE) == len(list((out / "images").glob("*.jpg")))
    assert {k["role"] for k in key} == {"heritage", "design"}
    a = {k["code"] for k in key if k["role"] == "heritage"}
    b = {k["code"] for k in key if k["role"] == "design"}
    assert a == b and len(a) == len(HERITAGE)
    assert {(k["controlnet_weight"], k["seed"]) for k in key} == {("0.85", "42")}                 # đã lọc đúng mức và seed


def test_expert_tieu_chi_theo_vai(chuyen_gia):
    out, _, _ = chuyen_gia
    spec_ = json.loads((out / "form_spec.json").read_text(encoding="utf-8"))
    assert spec_["mode"] == "expert"
    keys = {v["name"]: [c["key"] for c in v["criteria"]] for v in spec_["versions"]}
    assert keys == {"A": ["motif_recognizability", "cultural_appropriateness"], "B": ["aesthetic", "garment_integrity"]}
    assert [v["label"] for v in spec_["versions"]] == ["chuyên gia di sản", "chuyên gia thiết kế"]
    assert len(spec_["decisions"]) == 3 and len(spec_["closing"]) == 2
    assert [p["title"] for p in spec_["profile"]][0] == "Họ và tên"


def test_expert_khong_lo_thong_tin_nhan_dang(chuyen_gia):
    out, _, _ = chuyen_gia
    for name in ("Code.gs", "form_spec.json"):
        text = (out / name).read_text(encoding="utf-8")
        for bad in ("controlnet", "LR3D", "EXP-T", "seed", "0.85", "run_key", "__final"):
            assert bad not in text, (name, bad)
    assert "Phiếu thẩm định chuyên gia" in text and "chuyên gia di sản" in text


def test_expert_code_gs_co_quyet_dinh_va_nhan_xet(chuyen_gia):
    out, _, _ = chuyen_gia
    gs = (out / "Code.gs").read_text(encoding="utf-8")
    assert "SPEC.decisions" in gs and "SPEC.profile" in gs and "addParagraphTextItem" in gs
    assert re.search(r"const SPEC = \{.*?\n\};\n", gs, re.S)


def test_expert_giu_mac_dinh_cong_dong_va_loi_dau_vao(goi, tmp_path):
    root = goi[0].parent
    r = GF.build(root / "exp", tmp_path / "c", SEEDS, root=root, one_form=True)
    spec_ = json.loads((tmp_path / "c" / "form_spec.json").read_text(encoding="utf-8"))
    assert spec_["mode"] == "community" and spec_["perPage"] == 4 and "profile" not in spec_ and r["versions"] == 1
    with pytest.raises(ValueError, match="audience"):
        GF.build(root / "exp", tmp_path / "d", SEEDS, root=root, audience="khac")
    with pytest.raises(ValueError, match="mức"):
        GF.build(root / "exp", tmp_path / "e", SEEDS, root=root, levels=[0.99])


# ---------------- phiếu Word cho chuyên gia ----------------
_spec_ed = importlib.util.spec_from_file_location("expert_docx", ROOT / "scripts" / "eval" / "build_expert_docx.py")
ED = importlib.util.module_from_spec(_spec_ed)
_spec_ed.loader.exec_module(ED)
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@pytest.fixture(scope="module")
def phieu_word(chuyen_gia, tmp_path_factory):
    out, r, key = chuyen_gia
    paths = ED.write_docx(r["spec"], out / "images", tmp_path_factory.mktemp("docx"))
    return {p.name: p for p in paths}, r["spec"], key


def test_word_moi_vai_mot_file(phieu_word):
    files, _, _ = phieu_word
    assert sorted(files) == ["Phieu_chuyen_gia_di_san.docx", "Phieu_chuyen_gia_thiet_ke.docx"]
    assert ED.slug("chuyên gia thiết kế") == "chuyen_gia_thiet_ke" and ED.slug("Đạt!") == "dat"


def test_word_moi_thiet_ke_mot_trang_co_anh_va_dung_the_o_tich(phieu_word):
    from docx import Document
    files, spec_, _ = phieu_word
    for v in spec_["versions"]:
        doc = Document(files[f"Phieu_{ED.slug(v['label'])}.docx"])
        assert len(doc.inline_shapes) == len(v["items"])                                  # mỗi thiết kế một ảnh ghép
        heads = [p.text for p in doc.paragraphs if p.style.name == "Heading 2"]
        assert heads == [f"Thiết kế {n} / {len(v['items'])} (mã {i['code']})" for n, i in enumerate(v["items"], 1)]
        tags = [t.get(f"{_W}val") for t in doc.element.body.iter(f"{_W}tag")]
        expected = {f"{i['code']}|{c['key']}|{s}" for i in v["items"] for c in v["criteria"] for s in range(1, 6)}
        expected |= {f"{i['code']}|decision|{k}" for i in v["items"] for k in ("approve", "revise", "reject")}
        expected |= {"profile|consent|0", "profile|consent|1"}
        assert len(tags) == len(set(tags)) and set(tags) == expected                      # thẻ duy nhất, đủ ô, không thừa
        assert doc.sections[0].page_width.cm == pytest.approx(21, abs=0.01)             # A4, không phải Letter


def test_word_tieu_chi_theo_vai_va_ky_o_tick_la_content_control(phieu_word):
    from docx import Document
    files, _, _ = phieu_word
    heritage = Document(files["Phieu_chuyen_gia_di_san.docx"])
    design = Document(files["Phieu_chuyen_gia_thiet_ke.docx"])
    labels = lambda d: {c.text.split("\n")[0] for t in d.tables for c in (r.cells[0] for r in t.rows)}
    lab = {c["key"]: c["label"] for c in json.loads((ROOT / "config" / "expert_rubric.json").read_text(encoding="utf-8"))["criteria"]}
    h_keys, d_keys = ("motif_recognizability", "cultural_appropriateness"), ("aesthetic", "garment_integrity")
    assert {lab[k] for k in h_keys} <= labels(heritage) and not {lab[k] for k in d_keys} & labels(heritage)
    assert {lab[k] for k in d_keys} <= labels(design) and not {lab[k] for k in h_keys} & labels(design)
    assert list(heritage.element.body.iter("{http://schemas.microsoft.com/office/word/2010/wordml}checkbox"))


def test_word_khong_lo_thong_tin_nhan_dang(phieu_word):
    import zipfile
    files, _, _ = phieu_word
    for path in files.values():
        with zipfile.ZipFile(path) as z:
            xml = "".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith(".xml"))
            media = [n for n in z.namelist() if n.startswith("word/media/")]
        for bad in ("controlnet", "LR3D", "EXP-T", "seed", "0.85", "run_key", "python-docx"):
            assert bad not in xml, (path.name, bad)
        assert media and not any(re.search(r"LR3D|EXP|final|pattern|seed", n) for n in media)


def test_word_tu_choi_goi_khong_phai_chuyen_gia_hoac_thieu_anh(chuyen_gia, goi, tmp_path):
    out, r, _ = chuyen_gia
    with pytest.raises(ValueError, match="mode=expert"):
        ED.write_docx({**r["spec"], "mode": "community"}, out / "images", tmp_path / "a")
    with pytest.raises(FileNotFoundError, match="thiếu ảnh"):
        ED.write_docx(r["spec"], tmp_path / "khong_co_anh", tmp_path / "b")


def test_word_kiem_tra_spec_bao_loi_ro_rang(chuyen_gia, tmp_path):
    out, r, _ = chuyen_gia
    spec_ = r["spec"]
    v0, v1 = spec_["versions"]
    casos = [
        ({k: v for k, v in spec_.items() if k != "profile"}, "thiếu khóa"),
        ({**spec_, "profile": [{"title": "x", "type": "date"}]}, "text hoặc choice"),
        ({**spec_, "versions": [v0, {**v1, "label": v0["label"]}]}, "trùng nhau"),
        ({**spec_, "versions": [{**v0, "criteria": []}, v1]}, "không có tiêu chí"),
        ({**spec_, "versions": [{**v0, "items": []}, v1]}, "không có tiêu chí hoặc không có thiết kế"),
        ({**spec_, "versions": [{**v0, "items": v0["items"] + v0["items"][:1]}, v1]}, "mã ảnh trùng"),
    ]
    for bad, msg in casos:
        with pytest.raises(ValueError, match=msg):
            ED.write_docx(bad, out / "images", tmp_path / "x")
    assert not list((tmp_path / "x").glob("*.docx")) if (tmp_path / "x").exists() else True    # lỗi thì không ghi file dở


def test_word_ngat_trang_bang_thuoc_tinh_va_dat_ngon_ngu_viet(phieu_word):
    import zipfile
    files, spec_, _ = phieu_word
    path = files["Phieu_chuyen_gia_di_san.docx"]
    with zipfile.ZipFile(path) as z:
        doc_xml = z.read("word/document.xml").decode("utf-8")
        styles = z.read("word/styles.xml").decode("utf-8")
    assert doc_xml.count("<w:pageBreakBefore/>") == len(spec_["versions"][0]["items"]) + 1   # mỗi thiết kế và trang Góp ý chung
    assert 'w:type="page"' not in doc_xml                                                    # không còn đoạn rỗng ngắt trang
    assert "vi-VN" in styles


# ---------------- phiếu chuyên gia cho MỘT người (--single) ----------------
@pytest.fixture(scope="module")
def mot_nguoi(goi, tmp_path_factory):
    """Phiếu một người trên thí nghiệm giả: đủ 4 tiêu chí, không quyết định Đạt/Loại."""
    root = goi[0].parent
    exp = root / "exp_single"
    shutil.copytree(root / "exp", exp)
    (exp / "spec.json").write_text(json.dumps({"id": "EXP-T", "metrics": {"human": [
        "motif_recognizability", "cultural_appropriateness", "aesthetic", "garment_integrity"]}}), encoding="utf-8")
    out = tmp_path_factory.mktemp("single") / "gf"
    r = GF.build(exp, out, [42], root=root, audience="expert", levels=[0.85], single=True)
    paths = ED.write_docx(r["spec"], out / "images", out / "docx")
    return out, r, paths


def test_single_mot_form_du_tieu_chi_khong_quyet_dinh(mot_nguoi):
    out, r, paths = mot_nguoi
    spec_ = json.loads((out / "form_spec.json").read_text(encoding="utf-8"))
    assert r["versions"] == 1 and len(spec_["versions"]) == 1 and spec_["decisions"] == []
    assert [c["key"] for c in spec_["versions"][0]["criteria"]] == [
        "motif_recognizability", "cultural_appropriateness", "aesthetic", "garment_integrity"]
    assert spec_["versions"][0]["label"] == "chuyên gia"
    key = list(csv.DictReader((out / "key.csv").open(encoding="utf-8-sig")))
    assert {k["role"] for k in key} == {"both"} and len(key) == len(HERITAGE)
    assert "decisions.length" in (out / "Code.gs").read_text(encoding="utf-8")        # Apps Script bỏ câu quyết định khi rỗng


def test_single_word_mot_file_khong_co_hang_quyet_dinh(mot_nguoi):
    from docx import Document
    import zipfile
    out, r, paths = mot_nguoi
    assert [p.name for p in paths] == ["Phieu_chuyen_gia.docx"]
    doc = Document(paths[0])
    tags = [t.get(f"{_W}val") for t in doc.element.body.iter(f"{_W}tag")]
    assert not any("|decision|" in t for t in tags)
    assert len([t for t in tags if t.count("|") == 2 and not t.startswith("profile")]) == len(HERITAGE) * 4 * 5
    text = "\n".join(p.text for p in doc.paragraphs)
    for bad in ("Quyết định", "Loại", "Cần chỉnh sửa", "Đạt"):
        assert bad not in text, bad
    with zipfile.ZipFile(paths[0]) as z:
        xml = "".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith(".xml"))
    assert "|decision|" not in xml


def test_single_chi_dung_voi_expert(goi, tmp_path):
    with pytest.raises(ValueError, match="single"):
        GF.build(goi[0].parent / "exp", tmp_path / "s", SEEDS, root=goi[0].parent, single=True)
