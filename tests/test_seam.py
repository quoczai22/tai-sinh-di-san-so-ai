"""Kiểm thử evaluation/seam.py (chỉ số M5) bằng ảnh tổng hợp, không cần GPU."""
import numpy as np
import pytest
from PIL import Image

from evaluation.seam import NGUONG_M5, seam_score

K = 16  # độ rộng bộ lọc làm mượt: ảnh mượt hơn thì cặp cột kề nhau càng giống nhau


def nhieu_lien_mach(size=256, seed=0):
    """Nhiễu làm mượt theo vòng (np.roll) nên LIỀN MẠCH theo cả hai chiều."""
    rng = np.random.default_rng(seed)
    a = rng.normal(128, 40, (size, size, 3))
    for axis in (0, 1):
        a = sum(np.roll(a, s, axis=axis) for s in range(K)) / K
    return a.astype(np.float32)


def nhieu_co_duong_noi(size=256, seed=0):
    """Cắt một ô từ ảnh liền mạch lớn hơn: cột đầu và cột cuối cách xa nhau nên không liên quan."""
    return nhieu_lien_mach(size * 2, seed)[:size, :size]


def test_anh_phang_cho_1():
    r = seam_score(np.full((64, 64, 3), 200, np.uint8))
    assert r["m5"] == 1.0 and r["ok"]


def test_doc_dai_do_sang_tang_deu_co_duong_noi_lon():
    # Mỗi cột sáng hơn cột trước đúng 1 đơn vị (0 đến 255): lệch giữa hai cột kề = 1,
    # lệch giữa cột đầu và cột cuối = 255. Trên-dưới: mọi hàng giống nhau nên = 1.
    a = np.tile(np.arange(256, dtype=np.float32)[None, :, None], (256, 1, 3))
    r = seam_score(a)
    assert r["ratio_x"] == pytest.approx(255.0)
    assert r["ratio_y"] == 1.0
    assert r["m5"] == pytest.approx(255.0) and not r["ok"]


def test_duong_noi_tren_duoi_duoc_phat_hien():
    # Chuyển vị ảnh trên: lỗi nối nằm ở chiều dọc thay vì ngang.
    a = np.tile(np.arange(256, dtype=np.float32)[:, None, None], (1, 256, 3))
    r = seam_score(a)
    assert r["ratio_y"] == pytest.approx(255.0)
    assert r["ratio_x"] == 1.0
    assert not r["ok"]


def test_anh_lien_mach_dat_nguong():
    for seed in range(3):
        r = seam_score(nhieu_lien_mach(seed=seed))
        assert 0.85 < r["ratio_x"] < 1.15, r
        assert 0.85 < r["ratio_y"] < 1.15, r
        assert r["ok"]


def test_anh_co_duong_noi_vuot_nguong():
    # Hai cột cách xa nhau lệch gấp khoảng căn bậc hai của K (=4) lần hai cột kề nhau.
    r = seam_score(nhieu_co_duong_noi())
    assert r["m5"] > 2.5 and not r["ok"]
    assert r["m5"] > NGUONG_M5 * 2


def test_cat_lech_lam_hong_anh_lien_mach():
    # Cắt ảnh liền mạch tại vị trí bất kỳ rồi lát lại thì vẫn liền (cuộn vòng),
    # nhưng bỏ bớt cột ở một đầu thì mất tính liền mạch.
    a = nhieu_lien_mach()
    assert seam_score(np.roll(a, 77, axis=1))["ok"]
    assert not seam_score(a[:, :200])["ok"]


def test_nhan_anh_pil_duong_dan_va_anh_xam(tmp_path):
    a = np.clip(nhieu_lien_mach(), 0, 255).astype(np.uint8)
    p = tmp_path / "o.png"
    Image.fromarray(a).save(p)
    ket_qua_mang = seam_score(a)["m5"]
    assert seam_score(Image.fromarray(a))["m5"] == pytest.approx(ket_qua_mang)
    assert seam_score(p)["m5"] == pytest.approx(ket_qua_mang)
    assert seam_score(a[..., 0])["ok"]                       # ảnh xám 2 chiều
    rgba = np.dstack([a, np.full(a.shape[:2], 255, np.uint8)])
    assert seam_score(rgba)["m5"] == pytest.approx(ket_qua_mang)  # kênh alpha bị bỏ


def test_anh_qua_nho_va_hinh_dang_sai():
    with pytest.raises(ValueError):
        seam_score(np.zeros((2, 50, 3)))
    with pytest.raises(ValueError):
        seam_score(np.zeros((5, 5, 2)))
