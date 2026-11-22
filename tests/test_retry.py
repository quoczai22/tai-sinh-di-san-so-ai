"""Kiểm thử vòng loại và thử lại của polish (tsds/quality/retry.py) bằng polish giả, không cần GPU."""
import csv

import pytest
from PIL import Image

from tsds.quality import retry as R


def g3_gia(**status):
    """Kết quả G3 giả. Mặc định mọi chỉ số PASS; truyền tên_chỉ_số="FAIL" để đặt lỗi."""
    names = {"garment_shape_iou": ("Giữ dáng áo (GSC)", 0.92), "pattern_preservation": ("Giữ họa tiết (PPS)", 0.40),
             "sharpness_ratio": ("Độ nét", 0.25), "palette_shift_de": ("Lệch màu", 20.0)}
    metrics = {k: {"value": 0.1 if status.get(k) == "FAIL" else 0.99, "status": status.get(k, "PASS"),
                   "label": lab, "fail": thr} for k, (lab, thr) in names.items()}
    bad = any(v == "FAIL" for v in status.values())
    return {"decision": "FAIL" if bad else "PASS", "metrics": metrics}


class Kich_ban:
    """Polish giả ghi lại (seed, strength) mỗi lần gọi; phép đo giả trả lỗi theo danh sách cho trước."""

    def __init__(self, ket_qua):
        self.ket_qua = list(ket_qua)   # mỗi phần tử: dict trạng thái G3 của lần gọi tương ứng, hoặc "loi"
        self.goi = []

    def polish(self, raw, strength, seed):
        self.goi.append((seed, strength))
        if self.ket_qua[len(self.goi) - 1] == "loi":
            raise RuntimeError("hết VRAM")
        return Image.new("RGB", raw.size, (seed % 256, 0, 0))   # màu đỏ theo seed để phân biệt từng lần

    def evaluate(self, img):
        kq = self.ket_qua[len(self.goi) - 1]
        return g3_gia(**kq)


def chay(kich_ban, tmp_path, seed=42, strength=0.30):
    raw = Image.new("RGB", (32, 32), (7, 7, 7))
    return raw, R.polish_with_retry(raw, kich_ban.polish, kich_ban.evaluate, seed=seed, strength=strength,
                                    qc_dir=tmp_path, tag="t")


def doc_rejects(tmp_path):
    p = tmp_path / "rejects.csv"
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def test_dat_ngay_lan_dau_khong_ghi_loai(tmp_path):
    kb = Kich_ban([{}])
    _, r = chay(kb, tmp_path)
    assert r["status"] == "passed" and r["label"] is None and r["seed"] == 42 and r["strength"] == 0.30
    assert kb.goi == [(42, 0.30)] and len(r["attempts"]) == 1
    assert doc_rejects(tmp_path) == []


def test_loi_hai_lan_roi_dat_o_seed_thu_ba(tmp_path):
    kb = Kich_ban([{"pattern_preservation": "FAIL"}, {"garment_shape_iou": "FAIL"}, {}])
    _, r = chay(kb, tmp_path)
    assert r["status"] == "retried_seed" and r["seed"] == 44        # 42, 43 lỗi, 44 đạt
    assert kb.goi == [(42, 0.30), (43, 0.30), (44, 0.30)]
    rows = doc_rejects(tmp_path)
    assert [x["attempt"] for x in rows] == ["1", "2"]
    assert rows[0]["failed_metrics"] == "pattern_preservation"
    assert rows[1]["failed_metrics"] == "garment_shape_iou"
    assert rows[0]["next_action"] == "thử lại với seed kế tiếp"
    assert all((tmp_path / x["image"]).exists() for x in rows)       # ảnh bị loại được lưu


def test_het_ba_lan_doi_seed_thi_ha_do_nhieu(tmp_path):
    loi = {"pattern_preservation": "FAIL"}
    kb = Kich_ban([loi, loi, loi, loi, {}])                         # 4 lần cùng độ nhiễu (seed 42 đến 45) rồi lần 5 đạt
    _, r = chay(kb, tmp_path)
    assert r["status"] == "lower_strength" and r["strength"] == 0.22 and r["seed"] == 42
    assert kb.goi == [(42, 0.30), (43, 0.30), (44, 0.30), (45, 0.30), (42, 0.22)]
    rows = doc_rejects(tmp_path)
    assert len(rows) == 4 and rows[3]["next_action"] == "hạ độ nhiễu và thử lần cuối"


def test_van_loi_thi_tra_anh_ghep_tho_kem_nhan(tmp_path):
    loi = {"garment_shape_iou": "FAIL"}
    kb = Kich_ban([loi] * 5)
    raw, r = chay(kb, tmp_path)
    assert r["status"] == "raw_fallback" and r["label"] == "chưa qua bước hoàn thiện"
    assert r["image"] is raw and r["seed"] is None and len(r["attempts"]) == 5
    rows = doc_rejects(tmp_path)
    assert len(rows) == 5 and rows[-1]["next_action"] == "trả ảnh ghép thô"


def test_chi_so_khac_loi_khong_kich_hoat_thu_lai(tmp_path):
    kb = Kich_ban([{"sharpness_ratio": "FAIL", "palette_shift_de": "FAIL"}])
    _, r = chay(kb, tmp_path)
    assert r["status"] == "passed" and len(kb.goi) == 1
    assert doc_rejects(tmp_path) == []


def test_polish_nem_loi_thi_tinh_la_mot_lan_that_bai(tmp_path):
    kb = Kich_ban(["loi", {}])
    _, r = chay(kb, tmp_path)
    assert r["status"] == "retried_seed" and r["seed"] == 43
    rows = doc_rejects(tmp_path)
    assert len(rows) == 1 and "RuntimeError" in rows[0]["reason"] and rows[0]["image"] == ""
    assert r["attempts"][0]["status"] == "error"


def test_so_lan_thu_lai_seed_tuy_chinh(tmp_path):
    loi = {"pattern_preservation": "FAIL"}
    kb = Kich_ban([loi, loi, {}])
    raw = Image.new("RGB", (16, 16))
    r = R.polish_with_retry(raw, kb.polish, kb.evaluate, seed=1, strength=0.3, max_seed_retries=1,
                            qc_dir=tmp_path, tag="t")
    assert kb.goi == [(1, 0.3), (2, 0.3), (1, 0.22)] and r["status"] == "lower_strength"


def test_failed_gated_chi_lay_m1_m3():
    assert R.failed_gated(g3_gia(garment_shape_iou="FAIL", sharpness_ratio="FAIL")) == ["garment_shape_iou"]
    assert R.failed_gated(g3_gia()) == []
