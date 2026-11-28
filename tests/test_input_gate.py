"""Kiểm thử cổng kiểm tra ảnh đầu vào. Không nạp CLIP: các hàm nhúng được thay bằng vector giả."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tsds.provenance import passport as P
from tsds.quality import input_gate as G
from tests.test_passport_garment import tao_passport, thong_tin_ao_lora, work    # noqa: F401  (work là fixture)

ROOT = Path(__file__).resolve().parent.parent
CFG = {"version": "test", "calibrated": True, "P": {"k": 1, "t": 0.6}}


def test_verdict_dung_o_nguong_bien():
    assert G.verdict(0.1, 0.1) == "pass"            # bằng ngưỡng thì pass
    assert G.verdict(0.0999, 0.1) == "block"


def test_khong_con_phan_quyet_warn():
    assert {G.verdict(s, 0.1) for s in (-1.0, 0.0, 0.05, 0.1, 0.5)} == {"pass", "block"}


def test_score_p_lay_trung_binh_top_k_va_bo_mot_binh_ra():
    emb = np.array([[1.0, 0.0]])
    protos = np.array([[1.0, 0.0], [0.8, 0.6], [0.0, 1.0]])
    assert G.score_p(emb, protos, k=2)[0] == pytest.approx((1.0 + 0.8) / 2)
    bo = np.array([[True, False, False]])                                    # bỏ nguyên mẫu giống nhất
    assert G.score_p(emb, protos, k=1, exclude=bo)[0] == pytest.approx(0.8)
    assert G.score_p(emb, protos, k=3, exclude=bo)[0] == pytest.approx((0.8 + 0.0) / 2)    # k lớn hơn số nguyên mẫu còn lại
    assert G.score_p(emb, protos, k=3, exclude=np.array([[True, True, True]]))[0] == -1.0  # hết nguyên mẫu


def test_wilson():
    lo, hi = G.wilson(0, 0)
    assert (lo, hi) == (0.0, 1.0)
    lo, hi = G.wilson(10, 10)
    assert hi == pytest.approx(1.0) and 0.7 < lo < 1.0


def test_prepare_image_rgba_len_nen_trang_va_dem_vuong():
    img = Image.new("RGBA", (40, 20), (0, 0, 0, 0))                          # trong suốt hoàn toàn
    out = G.prepare_image(img)
    assert out.mode == "RGB" and out.size == (40, 40)
    assert set(out.getdata()) == {(255, 255, 255)}                           # nền trong suốt thành trắng, phần đệm cũng trắng


def test_input_rejected_khong_bi_except_valueerror_nuot():
    # generate_design_set bắt (OSError, ValueError) để quay về ảnh mặc định: InputRejected không được là lớp con của chúng
    assert not issubclass(G.InputRejected, (OSError, ValueError))


# ---- check_inputs với vector giả -------------------------------------------------------------
@pytest.fixture
def anh(tmp_path):
    paths = {}
    for name in ("tot", "xau", "giua"):
        p = tmp_path / f"{name}.png"
        Image.new("RGB", (8, 8), (10, 10, 10)).save(p)
        paths[name] = p
    return paths


def gia_lap(monkeypatch, emb_theo_thu_tu):
    """Thay nhúng bằng vector cho trước. Nguyên mẫu duy nhất là trục x, nên s_proto bằng thành phần x của ảnh."""
    monkeypatch.setattr(G, "embed_images", lambda imgs: np.array(emb_theo_thu_tu[:len(imgs)], dtype=np.float32))
    monkeypatch.setattr(G, "load_prototypes", lambda: (np.array([[1.0, 0.0]], dtype=np.float32), ["v1"]))


def doc_log(d):
    f = d / "input_gate.jsonl"
    return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []


def test_anh_tot_di_qua_khong_ghi_log(monkeypatch, anh, tmp_path):
    gia_lap(monkeypatch, [[1.0, 0.0]])
    kq = G.check_inputs([("hien_vat", anh["tot"])], cfg=CFG, log_dir=tmp_path)
    assert kq[0]["verdict"] == "pass" and doc_log(tmp_path) == []
    assert G.gate_block(kq, CFG)["verdict"] == "pass"


def test_anh_lac_de_bi_chan_va_ghi_log_khong_co_noi_dung_anh(monkeypatch, anh, tmp_path):
    gia_lap(monkeypatch, [[0.0, 1.0]])
    with pytest.raises(G.InputRejected) as e:
        G.check_inputs([("el1", anh["xau"])], context={"heritage_id": "LR3D_61"}, cfg=CFG, log_dir=tmp_path)
    assert e.value.results[0]["verdict"] == "block"
    log = doc_log(tmp_path)
    assert len(log) == 1 and log[0]["event"] == "input_blocked" and log[0]["heritage_id"] == "LR3D_61"
    assert len(log[0]["sha256"]) == 64 and "ip" not in log[0]


def test_diem_bang_nguong_thi_pass_thap_hon_thi_chan(monkeypatch, anh, tmp_path):
    gia_lap(monkeypatch, [[0.6, 0.0]])                                       # s_proto = 0.6 = ngưỡng
    assert G.check_inputs([("el1", anh["giua"])], cfg=CFG, log_dir=tmp_path)[0]["verdict"] == "pass"
    gia_lap(monkeypatch, [[0.59, 0.0]])
    with pytest.raises(G.InputRejected):
        G.check_inputs([("el1", anh["giua"])], cfg=CFG, log_dir=tmp_path)


def test_cong_loi_thi_chan_va_ghi_log(monkeypatch, anh, tmp_path):
    def hong(_):
        raise RuntimeError("hết bộ nhớ")
    monkeypatch.setattr(G, "embed_images", hong)
    with pytest.raises(G.InputRejected):
        G.check_inputs([("el1", anh["tot"])], cfg=CFG, log_dir=tmp_path)
    assert doc_log(tmp_path)[0]["event"] == "input_gate_error"


def test_anh_trung_duong_dan_chi_kiem_mot_lan(monkeypatch, anh, tmp_path):
    gia_lap(monkeypatch, [[1.0, 0.0]])
    kq = G.check_inputs([("panel", anh["tot"])] * 4, cfg=CFG, log_dir=tmp_path)
    assert len(kq) == 1


# ---- Passport -------------------------------------------------------------------------------
def test_passport_ghi_khoi_input_gate_va_verify_bat_sua(work):                       # noqa: F811
    gate = {"schema": "input-gate/1.0", "verdict": "pass", "images": [{"label": "hien_vat", "verdict": "pass"}]}
    pp = tao_passport(work, thong_tin_ao_lora(work), builder_extra={"input_gate": gate})
    assert pp["generation"]["input_gate"]["verdict"] == "pass" and pp["approval"]["status"] == "draft"
    assert P.verify(json.loads(json.dumps(pp)), check_files=False)["ok"]
    sua = json.loads(json.dumps(pp))
    sua["generation"]["input_gate"]["verdict"] = "pass "                                # sửa lén khối, sổ cái giữ bản cũ
    sua["generation"]["input_gate"]["images"] = []
    assert any("cổng ảnh đầu vào" in p for p in P.verify(sua, check_files=False)["problems"])


def test_khoi_cu_co_verdict_warn_khong_doi_trang_thai_duyet(work):                    # noqa: F811
    # Passport tạo từ bản cổng cũ (có vùng warn) vẫn đọc được, và cổng không còn tự đặt qa_warning
    gate = {"schema": "input-gate/1.0", "verdict": "warn", "images": []}
    pp = tao_passport(work, thong_tin_ao_lora(work), builder_extra={"input_gate": gate})
    assert pp["approval"]["status"] == "draft"
    assert P.verify(json.loads(json.dumps(pp)), check_files=False)["ok"]


def test_passport_cu_khong_co_input_gate_van_hop_le(work):                           # noqa: F811
    pp = tao_passport(work, thong_tin_ao_lora(work))
    assert "input_gate" not in pp["generation"] and P.verify(pp, check_files=False)["ok"]


# ---- chọn ngưỡng trong script đo ---------------------------------------------------------------
def tai_script_do():
    spec = importlib.util.spec_from_file_location("run_input_gate_eval", ROOT / "scripts" / "eval" / "run_input_gate_eval.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_chon_nguong_la_diem_giua_hai_phan_vi():
    m = tai_script_do()
    pos = np.linspace(0.6, 1.0, 11)
    neg = np.linspace(0.0, 0.4, 11)
    t = m.threshold(pos, neg, 10, 90)
    assert t == pytest.approx((np.percentile(pos, 10) + np.percentile(neg, 90)) / 2)
    assert np.percentile(neg, 90) < t < np.percentile(pos, 10)
    assert np.isfinite(m.threshold(np.array([0.2, 0.3]), np.array([0.25, 0.35]), 10, 90))    # hai nhóm chồng nhau vẫn ra một ngưỡng
