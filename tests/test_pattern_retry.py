"""Kiểm thử vòng sinh lại hoa văn khi cổng G2 LỖI (quality/pattern_retry.py) bằng bộ sinh giả, không cần GPU."""
import csv

import numpy as np
import pytest
from PIL import Image

from quality import gate as QG
from quality import pattern_retry as PR


def g2_gia(seam=1.0, vls=0.0):
    """Kết quả G2 giả theo đúng ngưỡng trong config/quality_gate.json: seam WARN 1,5 LỖI 2,0; VLS WARN 0,20 LỖI 0,40."""
    def tinh(v, warn, fail, label):
        return {"value": v, "status": "FAIL" if v >= fail else "WARN" if v >= warn else "PASS",
                "warn": warn, "fail": fail, "label": label}
    metrics = {"vessel_leakage": tinh(vls, 0.20, 0.40, "Rò dáng vật chứa (VLS)"),
               "seam_ratio": tinh(seam, 1.5, 2.0, "Đường nối khi lát")}
    order = {"PASS": 0, "WARN": 1, "FAIL": 2}
    decision = max((m["status"] for m in metrics.values()), key=order.get)
    return {"gate": "G2_pattern", "decision": decision, "metrics": metrics}


class Kich_ban:
    """Bộ sinh giả: lần gọi thứ n trả ảnh màu theo seed và kết quả G2 lấy từ danh sách cho trước."""

    def __init__(self, g2_theo_lan):
        self.g2_theo_lan = list(g2_theo_lan)   # mỗi phần tử: dict tham số cho g2_gia, hoặc "loi" để ném ngoại lệ
        self.seeds = []

    def make(self, seed):
        self.seeds.append(seed)
        if self.g2_theo_lan[len(self.seeds) - 1] == "loi":
            raise RuntimeError("hết VRAM")
        return Image.new("RGB", (16, 16), (seed % 256, 0, 0)), {"seed": seed, "duration_s": 1.0}

    def evaluate(self, img):
        return g2_gia(**self.g2_theo_lan[len(self.seeds) - 1])   # đo ngay sau lần sinh vừa gọi


def chay(kich_ban, tmp_path, seed=42, **kw):
    return PR.generate_with_retry(kich_ban.make, kich_ban.evaluate, seed=seed, qc_dir=tmp_path, tag="T", **kw)


def doc_csv(tmp_path):
    p = tmp_path / "pattern_rejects.csv"
    return list(csv.DictReader(open(p, encoding="utf-8"))) if p.exists() else []


def test_dat_ngay_lan_dau_khong_sinh_lai_va_khong_ghi_loai(tmp_path):
    kb = Kich_ban([dict(seam=1.1)])
    kq = chay(kb, tmp_path)
    assert kb.seeds == [42] and kq["status"] == "passed" and kq["seed"] == 42
    assert len(kq["attempts"]) == 1 and kq["attempts"][0]["status"] == "ok"
    assert doc_csv(tmp_path) == []


def test_canh_bao_khong_kich_hoat_sinh_lai(tmp_path):
    kb = Kich_ban([dict(seam=1.7, vls=0.25)])          # cả hai chỉ số ở mức WARN, chưa tới LỖI
    kq = chay(kb, tmp_path)
    assert kb.seeds == [42] and kq["status"] == "passed" and kq["g2"]["decision"] == "WARN"


def test_loi_roi_dat_o_lan_hai_doi_seed_va_ghi_mot_dong_loai(tmp_path):
    kb = Kich_ban([dict(seam=2.4), dict(seam=1.2)])
    kq = chay(kb, tmp_path)
    assert kb.seeds == [42, 43]
    assert kq["status"] == "retried_seed" and kq["seed"] == 43 and kq["result"]["seed"] == 43
    assert [a["status"] for a in kq["attempts"]] == ["failed", "ok"]
    rows = doc_csv(tmp_path)
    assert len(rows) == 1 and rows[0]["seed"] == "42" and rows[0]["failed_metrics"] == "seam_ratio"
    assert rows[0]["values"] == "seam_ratio=2.4" and (tmp_path / "pattern_rejects" / rows[0]["image"].split("/")[-1]).exists()


def test_vls_loi_cung_kich_hoat_sinh_lai(tmp_path):
    kb = Kich_ban([dict(vls=0.55), dict(vls=0.05)])
    kq = chay(kb, tmp_path)
    assert kq["status"] == "retried_seed" and doc_csv(tmp_path)[0]["failed_metrics"] == "vessel_leakage"


def test_moi_lan_deu_loi_tra_ban_it_loi_nhat_va_van_bao_loi(tmp_path):
    # độ tệ = giá trị / ngưỡng lỗi: lần 1 là 3,0/2,0 = 1,5; lần 2 là 0,6/0,4 = 1,5; lần 3 là 2,2/2,0 = 1,1; lần 4 là 2,6/2,0 = 1,3
    kb = Kich_ban([dict(seam=3.0), dict(vls=0.6), dict(seam=2.2), dict(seam=2.6)])
    kq = chay(kb, tmp_path)
    assert kb.seeds == [42, 43, 44, 45]                  # 1 lần đầu cộng max_retries = 3 lần sinh lại
    assert kq["status"] == "best_of_failed" and kq["seed"] == 44
    assert kq["g2"]["decision"] == "FAIL"
    assert len(doc_csv(tmp_path)) == 4
    assert doc_csv(tmp_path)[-1]["next_action"].startswith("dùng bản ít lỗi nhất")


def test_bang_do_tre_lay_lan_som_hon(tmp_path):
    kb = Kich_ban([dict(seam=2.4), dict(seam=2.4)])
    kq = chay(kb, tmp_path, max_retries=1)
    assert kq["status"] == "best_of_failed" and kq["seed"] == 42


def test_max_retries_bang_0_chi_sinh_mot_lan(tmp_path):
    kb = Kich_ban([dict(seam=2.4)])
    kq = chay(kb, tmp_path, max_retries=0)
    assert kb.seeds == [42] and kq["status"] == "best_of_failed" and len(kq["attempts"]) == 1


def test_mac_dinh_max_retries_lay_tu_cau_hinh_cong(tmp_path):
    kb = Kich_ban([dict(seam=3.0)] * 10)
    chay(kb, tmp_path)
    assert len(kb.seeds) == QG.load_config()["max_retries"] + 1


def test_ngoai_le_o_lan_dau_van_sinh_lai(tmp_path):
    kb = Kich_ban(["loi", dict(seam=1.1)])
    kq = chay(kb, tmp_path)
    assert kb.seeds == [42, 43] and kq["status"] == "retried_seed" and kq["seed"] == 43
    assert kq["attempts"][0] == {"attempt": 1, "seed": 42, "status": "error", "error": "RuntimeError"}
    assert doc_csv(tmp_path) == []                       # lỗi kỹ thuật không phải ảnh bị cổng G2 loại


def test_moi_lan_deu_ngoai_le_thi_nem_lai(tmp_path):
    kb = Kich_ban(["loi"] * 4)
    with pytest.raises(RuntimeError):
        chay(kb, tmp_path)
    assert len(kb.seeds) == 4


def test_goi_on_retry_voi_lan_va_seed_moi(tmp_path):
    kb = Kich_ban([dict(seam=2.4), dict(seam=2.4), dict(seam=1.0)])
    goi = []
    kq = chay(kb, tmp_path, on_retry=lambda n, s: goi.append((n, s)))
    assert goi == [(2, 43), (3, 44)] and kq["seed"] == 44


def test_do_te_va_chi_so_loi():
    g = g2_gia(seam=3.0, vls=0.1)
    assert PR.failed_metrics(g) == ["seam_ratio"]
    assert PR.severity(g) == pytest.approx(1.5)
    assert PR.severity(g2_gia(seam=0.5, vls=0.0)) == pytest.approx(0.25)
    assert PR.severity({"metrics": {"seam_ratio": {"value": None, "fail": 2.0}}}) == 0.0


def test_cong_g2_that_nhan_ra_duong_noi_va_vong_sinh_lai_dung_no(tmp_path):
    """Dùng đúng cổng G2 thật: ảnh dốc sáng từ trái sang phải có đường nối lớn, ảnh sóng tuần hoàn thì liền mạch."""
    x = np.arange(128, dtype=np.float32)
    song = (127 + 100 * np.sin(2 * np.pi * x / 32))[None, :].repeat(128, 0)           # chu kỳ chia hết 128: liền mạch
    ram = np.tile(np.linspace(0, 255, 128, dtype=np.float32)[None, :], (128, 1))      # mép trái đen, mép phải trắng
    anh = lambda a: np.stack([a, a, a], -1).astype(np.uint8)   # noqa: E731
    ref = anh(song)
    seeds = {42: anh(ram), 43: anh(song)}

    def make(s):
        return Image.fromarray(seeds[s]), {"seed": s}

    kq = PR.generate_with_retry(make, lambda im: QG.evaluate_pattern(np.asarray(im), ref), seed=42, qc_dir=tmp_path)
    assert kq["status"] == "retried_seed" and kq["seed"] == 43
    assert kq["attempts"][0]["failed_metrics"] == ["seam_ratio"] and kq["attempts"][0]["values"]["seam_ratio"] >= 2.0
    assert kq["g2"]["metrics"]["seam_ratio"]["status"] != "FAIL"


def test_ban_it_loi_nhat_bo_qua_lan_ngoai_le_xen_ke(tmp_path):
    # lần 1: độ tệ 2,4/2,0 = 1,2; lần 2 và 4 ném ngoại lệ (không có độ tệ); lần 3: 2,2/2,0 = 1,1 nên được chọn
    kb = Kich_ban([dict(seam=2.4), "loi", dict(seam=2.2), "loi"])
    kq = chay(kb, tmp_path)
    assert kq["status"] == "best_of_failed" and kq["seed"] == 44
    assert [a["status"] for a in kq["attempts"]] == ["failed", "error", "failed", "error"]
    assert len(doc_csv(tmp_path)) == 2                   # chỉ hai lần bị cổng G2 loại mới ghi nhật ký


def test_loi_o_buoc_do_giu_anh_va_khong_sinh_lai(tmp_path):
    """Bước đo G2 ném ngoại lệ: dùng ảnh vừa sinh với trạng thái unmeasured, không sinh lại (không đốt thêm GPU)."""
    kb = Kich_ban([dict(seam=1.0)] * 4)

    def do_hong(img):
        raise ValueError("lệch kích thước")

    kq = PR.generate_with_retry(kb.make, do_hong, seed=42, qc_dir=tmp_path, tag="T")
    assert kb.seeds == [42] and kq["status"] == "unmeasured" and kq["g2"] is None and kq["seed"] == 42
    assert kq["attempts"] == [{"attempt": 1, "seed": 42, "status": "unmeasured", "error": "ValueError"}]


def test_loi_ghi_nhat_ky_khong_lam_hong_vong_sinh_lai(tmp_path, monkeypatch):
    def hong(*a, **k):
        raise PermissionError("file đang mở")

    monkeypatch.setattr(PR, "_log_reject", hong)
    kb = Kich_ban([dict(seam=2.4), dict(seam=1.1)])
    kq = chay(kb, tmp_path)
    assert kq["status"] == "retried_seed" and kq["seed"] == 43
