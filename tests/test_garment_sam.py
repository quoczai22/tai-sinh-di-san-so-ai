"""Kiểm thử phần không cần mô hình của generation/garment_sam.py và việc truyền vùng áo tính sẵn."""
import numpy as np
import pytest
from PIL import Image

from generation import garment, garment_sam as gs


def test_diem_goi_y_dung_toa_do_va_nhan():
    pts, lab = gs.prompt_points(200, 400)
    assert lab == [1, 1, 1, 1, 0, 0, 0, 0]
    assert pts[:4] == [[100, 120], [100, 180], [100, 240], [100, 300]]   # trục giữa ở 30%, 45%, 60%, 75% chiều cao
    assert pts[4] == [8, 16] and pts[7] == [192, 384]                      # bốn góc làm điểm nền
    assert all(0 <= x < 200 and 0 <= y < 400 for x, y in pts)


def test_clean_mask_giu_thanh_phan_lon_nhat_va_lap_lo():
    m = np.zeros((100, 100), np.uint8)
    m[20:80, 30:70] = 1            # thân áo 60 x 40
    m[40:44, 45:49] = 0            # lỗ nhỏ bên trong
    m[2:6, 2:6] = 1                # mảng rời ở góc
    out = gs.clean_mask(m)
    assert out[42, 47] == 1                        # lỗ được lấp
    assert out[3, 3] == 0                          # mảng rời bị bỏ
    assert out[50, 50] == 1 and out[10, 50] == 0   # thân còn, ngoài thân không


def test_clean_mask_khong_lap_vung_nen_cham_mep():
    m = np.ones((60, 60), np.uint8)
    m[:, 20:30] = 0                 # dải nền cắt ngang từ mép trên xuống mép dưới
    out = gs.clean_mask(m)
    assert out[30, 25] == 0


def test_chon_mat_na_diem_cao_nhat_trong_dien_tich_hop_ly():
    nho = np.zeros((100, 100), np.uint8); nho[0:10, 0:10] = 1          # 1% khung: quá nhỏ
    vua = np.zeros((100, 100), np.uint8); vua[10:60, 20:60] = 1        # 20%
    vua2 = np.zeros((100, 100), np.uint8); vua2[10:70, 10:70] = 1      # 36%
    lon = np.ones((100, 100), np.uint8)                                # 100%: quá lớn
    assert gs.choose([nho, vua, vua2, lon], [0.99, 0.80, 0.90, 0.95]) == 2
    assert gs.choose([nho, lon], [0.9, 0.9]) is None


def test_layout_mask_dung_vung_ao_tinh_san_thay_vi_tach_theo_mau():
    tpl = Image.new("RGB", (200, 300), (255, 255, 255))     # ảnh trắng: tách theo màu sẽ tràn cả ảnh
    vung = np.zeros((300, 200), np.uint8)
    vung[50:250, 70:130] = 1                                # thân áo hẹp ở giữa
    m = garment._layout_mask(tpl, garment.get_layout("front_panel"), vung)
    # Mép được làm mềm (độ lệch chuẩn 14 px) nên có rò nhẹ; ngoài 3 độ lệch chuẩn (42 px) phải bằng 0.
    # Nếu tách theo màu trên ảnh trắng thì mặt nạ sẽ phủ cả ảnh và phép thử này lỗi.
    ys, xs = np.where(m > 0.01)
    assert xs.min() >= 70 - 45 and xs.max() < 130 + 45 and ys.min() >= 50 - 45 and ys.max() < 250 + 45
    assert m[150, 100] > 0.5                                  # giữa thân áo vẫn có hoa văn
