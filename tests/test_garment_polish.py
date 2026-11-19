"""Kiểm thử phần ghép mặt nạ của polish có mặt nạ (generation/garment.py), không cần GPU."""
import numpy as np
import pytest
from PIL import Image

from generation import garment


def anh_ngau_nhien(size=64, seed=0):
    rng = np.random.default_rng(seed)
    return Image.fromarray(rng.integers(0, 256, (size, size, 3), dtype=np.uint8))


def mat_na_hinh_chu_nhat(size=64, y0=16, y1=48, x0=16, x1=48):
    m = np.zeros((size, size), np.uint8)
    m[y0:y1, x0:x1] = 1
    return m


def test_ngoai_mat_na_trung_anh_ghep_tho_tuyet_doi():
    comp = anh_ngau_nhien()
    pol = Image.new("RGB", comp.size, (255, 255, 255))
    m = mat_na_hinh_chu_nhat()
    out = np.asarray(garment.blend_with_mask(pol, comp, m, feather_px=3.0)).astype(int)
    ngoai = m == 0
    assert np.abs(out - np.asarray(comp).astype(int))[ngoai].max() == 0


def test_xa_mep_ben_trong_lay_anh_polish():
    comp = Image.new("RGB", (64, 64), (0, 0, 0))
    pol = Image.new("RGB", (64, 64), (200, 100, 50))
    out = np.asarray(garment.blend_with_mask(pol, comp, mat_na_hinh_chu_nhat(), feather_px=1.0))
    # Tâm vùng cách mép 16 pixel, gấp 16 lần độ lệch chuẩn làm mềm → trọng số polish ≈ 1
    assert np.abs(out[32, 32].astype(int) - np.array([200, 100, 50])).max() <= 1


def test_mep_trong_mat_na_chuyen_dan():
    comp = Image.new("RGB", (64, 64), (0, 0, 0))
    pol = Image.new("RGB", (64, 64), (200, 200, 200))
    out = np.asarray(garment.blend_with_mask(pol, comp, mat_na_hinh_chu_nhat(), feather_px=4.0))[:, :, 0]
    # Hàng 32, từ mép trái vùng (cột 16) vào giữa (cột 32): giá trị tăng dần, không nhảy vọt
    hang = out[32, 16:33].astype(int)
    assert 0 < hang[0] < 200 and hang[-1] >= 195
    assert np.all(np.diff(hang) >= 0)


def test_polish_khac_kich_thuoc_duoc_co_ve_kich_thuoc_anh_ghep():
    comp = anh_ngau_nhien(64)
    pol = Image.new("RGB", (128, 128), (10, 20, 30))
    out = garment.blend_with_mask(pol, comp, mat_na_hinh_chu_nhat(), feather_px=2.0)
    assert out.size == comp.size


def test_polish_masked_chi_doi_vung_ao(monkeypatch):
    comp = anh_ngau_nhien()
    monkeypatch.setattr(garment, "polish", lambda im, strength, seed, steps: Image.new("RGB", im.size, (9, 9, 9)))
    m = mat_na_hinh_chu_nhat()
    out = np.asarray(garment.polish_masked(comp, mask=m, feather_px=2.0)).astype(int)
    assert np.abs(out - np.asarray(comp).astype(int))[m == 0].max() == 0
    assert (out[24:40, 24:40] == 9).all()                       # sâu trong vùng áo là ảnh polish


def test_polish_masked_nhan_do_nhieu_mac_dinh_thap_hon_polish_toan_anh(monkeypatch):
    thu = {}
    monkeypatch.setattr(garment, "polish", lambda im, strength, seed, steps: thu.update(s=strength) or im)
    garment.polish_masked(anh_ngau_nhien(), mask=mat_na_hinh_chu_nhat())
    assert thu["s"] == garment.POLISH_MASKED_STRENGTH < garment.POLISH_STRENGTH


def test_mat_na_ao_trang_goc_hop_ly():
    tpl = Image.open(garment.TEMPLATE).convert("RGB")
    m = garment.garment_mask(tpl)
    ti_le = float(m.mean())
    assert m.shape == (tpl.height, tpl.width)
    assert 0.02 < ti_le < 0.7, ti_le


def test_polish_locked_tra_lai_net_ve_va_giu_nguyen_ngoai_ao(monkeypatch):
    import cv2
    y, x = np.mgrid[0:96, 0:96]
    nen = (128 + 60 * np.sin(x / 2.3) * np.cos(y / 3.1)).clip(0, 255).astype(np.uint8)
    comp = Image.fromarray(np.stack([nen, nen // 2 + 40, 255 - nen], axis=-1))
    # polish giả làm mờ toàn bộ: mất nét vẽ của họa tiết
    monkeypatch.setattr(garment, "polish", lambda im, strength, seed, steps: Image.fromarray(
        cv2.GaussianBlur(np.asarray(im), (0, 0), 3)))
    m = mat_na_hinh_chu_nhat(size=96, y0=20, y1=76, x0=20, x1=76)
    mo = garment.polish_masked(comp, mask=m, feather_px=2.0)
    khoa = garment.polish_locked(comp, m.astype(np.float32), mask=m)

    def bien_do_net_ve(im):                            # độ mạnh nét vẽ: độ lệch chuẩn dải tần trung của kênh sáng, trong vùng áo
        g = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2GRAY).astype(np.float32)
        return float((cv2.GaussianBlur(g, (0, 0), 1.2) - cv2.GaussianBlur(g, (0, 0), 4.0))[30:66, 30:66].std())

    goc = bien_do_net_ve(comp)
    assert bien_do_net_ve(mo) < 0.5 * goc                # polish giả làm mất hơn nửa nét vẽ
    assert bien_do_net_ve(khoa) > 0.7 * goc              # khóa trả lại phần lớn (đo thực tế khoảng 0,78)
    ngoai = m == 0
    assert np.abs(np.asarray(khoa).astype(int) - np.asarray(comp).astype(int))[ngoai].max() == 0   # ngoài áo giữ nguyên tuyệt đối
