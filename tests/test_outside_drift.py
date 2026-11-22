"""Kiểm thử chỉ số M2 (quality.metrics.outside_drift): trôi ngoài vùng áo."""
import numpy as np

from tsds.quality import gate as QG
from tsds.quality import metrics as M


def mat_na(size=64):
    m = np.zeros((size, size), np.uint8)
    m[16:48, 16:48] = 1          # vùng áo 32x32 ở giữa
    return m


def test_giong_het_cho_0():
    raw = np.full((64, 64, 3), 100, np.uint8)
    r = M.outside_drift(raw, raw.copy(), mat_na())
    assert r == {"outside_drift": 0.0, "outside_drift_max": 0}


def test_chi_doi_ben_trong_ao_van_cho_0():
    raw = np.full((64, 64, 3), 100, np.uint8)
    fin = raw.copy()
    fin[16:48, 16:48] = 250
    assert M.outside_drift(raw, fin, mat_na())["outside_drift"] == 0.0


def test_doi_deu_toan_anh_10_don_vi_cho_10():
    raw = np.full((64, 64, 3), 100, np.uint8)
    r = M.outside_drift(raw, raw + 10, mat_na())
    assert r == {"outside_drift": 10.0, "outside_drift_max": 10}


def test_chi_doi_mot_phan_ngoai_ao():
    # Ngoài áo có 64*64 - 32*32 = 3072 pixel. Đổi đúng 1 hàng 64 pixel (hàng 0, nằm ngoài áo) thêm 30:
    # trung bình = 30 * 64 / 3072 = 0,625
    raw = np.full((64, 64, 3), 100, np.uint8)
    fin = raw.copy()
    fin[0, :] += 30
    r = M.outside_drift(raw, fin, mat_na())
    assert r["outside_drift"] == 0.625 and r["outside_drift_max"] == 30


def test_mat_na_phu_kin_anh_cho_nan():
    raw = np.zeros((8, 8, 3), np.uint8)
    r = M.outside_drift(raw, raw, np.ones((8, 8), np.uint8))
    assert np.isnan(r["outside_drift"])


def test_cong_g3_ghi_m2_vao_chi_tiet_khong_dung_lam_nguong():
    raw = np.full((512, 512, 3), 200, np.uint8)
    tpl = raw.copy()
    prior = np.zeros((512, 512), np.uint8)
    prior[100:400, 150:350] = 1
    layout = prior.astype(np.float32)
    fin = raw.copy()
    fin[:50] += 40                                  # trôi ngoài áo
    g3 = QG.evaluate_final(raw, fin, tpl, layout, prior)
    assert "outside_drift" in g3["details"] and g3["details"]["outside_drift"] > 0
    assert "outside_drift" not in g3["metrics"]     # chưa gắn ngưỡng loại
