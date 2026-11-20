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
    # Mép vùng in được làm mềm nhưng KHÔNG được lan ra ngoài áo: ngoài vùng áo phải bằng đúng 0.
    # Nếu tách theo màu trên ảnh trắng thì mặt nạ sẽ phủ cả ảnh và phép thử này lỗi.
    assert m[vung == 0].max() == 0
    assert m[150, 100] > 0.5                                  # giữa thân áo vẫn có hoa văn


def test_hoa_van_khong_tran_vao_khe_giua_tay_va_than_ao(tmp_path):
    """Áo có khe nền giữa tay và thân (như áo LoRA tay loe): ghép hoa văn không được đổi pixel nào ngoài áo."""
    rng = np.random.default_rng(0)
    nen = rng.integers(60, 120, (300, 200, 3)).astype(np.uint8)             # nền xám có nhiễu
    vung = np.zeros((300, 200), np.uint8)
    vung[40:280, 70:130] = 1                                                 # thân
    vung[60:200, 20:45] = 1                                                  # tay trái, cách thân 25 px
    vung[60:200, 155:180] = 1                                                # tay phải
    ao = nen.copy()
    ao[vung > 0] = (235, 235, 235)
    pat = Image.fromarray(rng.integers(0, 255, (64, 64, 3)).astype(np.uint8))
    path = tmp_path / "ao_khe.png"
    Image.fromarray(ao).save(path)
    for lay in garment.layout_names():
        out = np.asarray(garment.apply(pat, layout=lay, template_path=path, garment_region=vung))
        assert (out[vung == 0] == ao[vung == 0]).all(), f"layout {lay} làm đổi pixel ngoài áo"


# ---------------------------------------------------------------- tách nền hoa văn ----

def _hoa_van_nen_kem():
    """Nền kem, một ô mực xanh ở giữa và một vạch đen: mực đục, nền trong suốt."""
    a = np.full((64, 64, 3), (238, 232, 214), np.uint8)
    a[20:44, 20:44] = (30, 60, 170)
    a[4:8, 4:60] = (35, 35, 35)
    return Image.fromarray(a)


def test_ground_alpha_nen_trong_suot_muc_duc():
    al = garment.ground_alpha(_hoa_van_nen_kem())
    assert al[50, 10] < 0.05 and al[60, 60] < 0.05          # nền kem
    assert al[30, 30] > 0.95                                  # mực xanh
    assert al[5, 30] > 0.95                                   # nét đen


def test_ground_alpha_khong_lam_bien_mat_hoa_van_khong_co_muc():
    trang = Image.fromarray(np.full((32, 32, 3), (240, 236, 220), np.uint8))
    assert garment.ground_alpha(trang).min() == 1.0          # không có mực thì giữ nguyên, không xóa sạch


def test_ground_alpha_giu_nen_co_mau_dam():
    do = Image.fromarray(np.full((32, 32, 3), (170, 40, 40), np.uint8))
    assert garment.ground_alpha(do).min() == 1.0             # nền đỏ là chính hoa văn, không tách


def test_apply_de_lo_vai_ao_o_cho_nen_hoa_van(tmp_path):
    vung = np.zeros((300, 200), np.uint8)
    vung[40:280, 40:160] = 1
    ao = np.full((300, 200, 3), 120, np.uint8)
    ao[vung > 0] = (240, 240, 240)
    path = tmp_path / "ao.png"
    Image.fromarray(ao).save(path)
    pat = _hoa_van_nen_kem()
    khong_tach = np.asarray(garment.apply(pat, layout="front_panel", template_path=path, garment_region=vung,
                                          remove_ground=False)).astype(int)
    tach = np.asarray(garment.apply(pat, layout="front_panel", template_path=path, garment_region=vung)).astype(int)
    trong_ao = vung > 0
    # Không tách: nền kem phủ lên cả vùng in, vải đổi màu. Có tách: chỉ vùng mực đổi, phần còn lại giữ vải trắng.
    doi_khong_tach = (np.abs(khong_tach - ao.astype(int)).max(2) > 6)[trong_ao].mean()
    doi_tach = (np.abs(tach - ao.astype(int)).max(2) > 6)[trong_ao].mean()
    assert doi_tach < doi_khong_tach * 0.6
