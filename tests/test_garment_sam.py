"""Kiểm thử phần không cần mô hình của tsds/generation/garment/garment_sam.py và việc truyền vùng áo tính sẵn."""
import numpy as np
import pytest
from PIL import Image

from tsds.generation.garment import garment, garment_sam as gs


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


def _o_thua(nen, muc, canh=6, size=64):
    """Ô nền phẳng chỉ có một khối mực nhỏ (khoảng 0,9% diện tích): kiểu ô xếp từ vài phần tử."""
    a = np.full((size, size, 3), nen, np.uint8)
    a[30:30 + canh, 30:30 + canh] = muc
    return Image.fromarray(a)


def test_ground_alpha_o_thua_giu_nen_trong_suot():
    """Lỗi đã gặp: ô thưa có độ đục trung bình dưới 0,05 bị in cả màu nền thành mảng phẳng."""
    al = garment.ground_alpha(_o_thua((200, 205, 200), (60, 100, 200)))
    assert al[5, 5] < 0.05 and al[60, 60] < 0.05             # nền trong suốt
    assert al[32, 32] > 0.95                                  # mực đục


def test_ground_alpha_muc_nhat_tren_nen_xam_giu_nen_trong_suot():
    """Mực xanh nhạt (sắc độ thấp, không tối) trên nền sáng: cách tính tuyệt đối không thấy mực, cách theo độ lệch nền thấy."""
    al = garment.ground_alpha(_o_thua((205, 210, 205), (140, 165, 205), canh=10))
    assert al[5, 5] < 0.05
    assert al[34, 34] > 0.9


def test_ground_alpha_hoa_van_trang_tren_nen_kem_van_duc_hoan_toan():
    """Hành vi cũ giữ nguyên: hoa văn trắng trên nền kem chỉ lệch nền khoảng 14, không phải mực thật."""
    a = np.full((64, 64, 3), (238, 232, 214), np.uint8)
    a[10:30, 10:30] = (250, 250, 250)
    a[40:60, 35:55] = (250, 250, 250)
    assert garment.ground_alpha(Image.fromarray(a)).min() == 1.0


def test_ground_alpha_hoa_van_trang_co_dom_ban_van_duc_hoan_toan():
    """Ca đối kháng do kiểm tra độc lập tìm ra: đốm bẩn 5x5 (0,6%) không được làm hoa văn trắng bị khoét."""
    a = np.full((64, 64, 3), (238, 232, 214), np.uint8)
    a[10:30, 10:30] = (250, 250, 250)
    a[40:60, 35:55] = (250, 250, 250)
    a[5:10, 5:10] = (150, 140, 120)
    assert garment.ground_alpha(Image.fromarray(a)).min() == 1.0


def test_ground_alpha_hoa_van_trang_chiem_hon_nua_o_co_dom_ban():
    """Vùng sáng chiếm hơn nửa ô thì trung vị rơi vào vùng sáng: không được đảo nền thành mực."""
    a = np.full((64, 64, 3), (238, 232, 214), np.uint8)
    a[:, 10:60] = (250, 250, 250)
    a[5:10, 5:10] = (150, 140, 120)
    assert garment.ground_alpha(Image.fromarray(a)).min() == 1.0


def test_ground_alpha_nen_nhieu_manh_van_duc_hoan_toan():
    rng = np.random.default_rng(0)
    a = np.clip(np.full((64, 64, 3), (238, 232, 214), np.float32) + rng.normal(0, 10, (64, 64, 3)), 0, 255)
    assert garment.ground_alpha(Image.fromarray(a.astype(np.uint8))).min() == 1.0


def test_ground_alpha_khong_goi_nhanh_du_phong_khi_muc_du_day(monkeypatch):
    """Ô có độ đục từ 0,05 trở lên không đi qua nhánh mới: kết quả mọi ô thường giữ nguyên."""
    def boom(lab):
        raise AssertionError("nhánh dự phòng không được gọi")
    monkeypatch.setattr(garment, "_faint_ink_alpha", boom)
    al = garment.ground_alpha(_hoa_van_nen_kem())
    assert al[30, 30] > 0.95 and al[50, 10] < 0.05


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


# ---- khe nền lọt vào mặt nạ áo (khe giữa tay và thân, khe giữa hai tà) ----

def _ao_co_khe(slit=True, shadow=False, speck=False):
    """Ảnh giả 300x200: nền xám có dốc sáng ngang, áo trắng x 60..140, khe nền x 95..105 (y 80..250) nằm trong mặt nạ."""
    h, w = 300, 200
    wall = np.tile(np.linspace(100, 130, w, dtype=np.float32), (h, 1))
    img = np.stack([wall] * 3, axis=2)
    mask = np.zeros((h, w), np.uint8)
    mask[20:280, 60:140] = 1
    img[20:280, 60:140] = 235
    if slit:
        img[80:250, 95:105] = np.stack([wall[80:250, 95:105]] * 3, axis=2)      # khe là màu nền, vẫn nằm trong mặt nạ
    if shadow:
        img[100:200, 65:90] = 175                                               # bóng đổ trên vải: sáng hơn nền nhiều
    if speck:
        img[40:45, 70:75] = 105                                                 # đốm tối 5x5 trên vải
    return img.astype(np.uint8), mask


def test_khe_nen_trong_mat_na_bi_bo():
    from tsds.generation.garment import garment_sam as GS
    img, mask = _ao_co_khe()
    out = GS.remove_background_gaps(img, mask)
    assert out[150, 100] == 0                                    # giữa khe: đã bỏ
    assert out[150, 80] == 1 and out[150, 120] == 1              # vải hai bên khe giữ nguyên
    assert out[30, 100] == 1                                     # phần nối trên cùng vẫn là áo
    assert out.sum() < mask.sum() and out.sum() > 0.7 * mask.sum()


def test_bong_do_tren_vai_va_dom_nho_khong_bi_coi_la_khe():
    from tsds.generation.garment import garment_sam as GS
    img, mask = _ao_co_khe(slit=False, shadow=True, speck=True)
    out = GS.remove_background_gaps(img, mask)
    assert (out == mask).all()                                   # không có khe thì giữ nguyên từng điểm


def test_khong_khe_thi_tra_lai_dung_mat_na():
    from tsds.generation.garment import garment_sam as GS
    img, mask = _ao_co_khe(slit=False)
    assert (GS.remove_background_gaps(img, mask) == mask).all()


def test_expected_wall_noi_suy_giua_hai_ben_ao():
    from tsds.generation.garment import garment_sam as GS
    img, mask = _ao_co_khe(slit=False)
    est = GS.expected_wall(img, mask)
    # tại hàng 150, nền trái ~ 100 + 30*(50/199) = 107,5; phải ~ 100 + 30*(150/199) = 122,6; giữa áo nội suy ~ 115
    assert abs(float(est[150, 100, 0]) - 115) < 6


def test_phan_khe_trong_bong_noi_voi_loi_khe_cung_bi_bo():
    from tsds.generation.garment import garment_sam as GS
    img, mask = _ao_co_khe()
    img[170:220, 95:105] = 60                                    # nửa dưới của khe nằm trong bóng: tối hơn nền (100 đến 130)
    out = GS.remove_background_gaps(img, mask)
    assert out[120, 100] == 0 and out[190, 100] == 0             # lõi khe và phần bóng nối liền đều bị bỏ
    assert out[190, 80] == 1 and out[190, 120] == 1              # vải hai bên giữ nguyên


def test_vung_toi_xa_loi_khe_khong_bi_noi_toi():
    from tsds.generation.garment import garment_sam as GS
    img, mask = _ao_co_khe()
    img[80:250, 95:105] = 60                                     # cả khe tối hơn nền: không có lõi khe, không có gì để neo
    out = GS.remove_background_gaps(img, mask)
    assert (out == mask).all()


def test_vai_trang_trong_bong_nep_gap_sang_hon_nen_khong_bi_bo():
    from tsds.generation.garment import garment_sam as GS
    img, mask = _ao_co_khe(slit=False)
    img[60:260, 70:90] = 150                                     # nếp gấp tối nhưng vẫn sáng hơn nền 100 đến 130 từ 20 mức
    out = GS.remove_background_gaps(img, mask)
    assert (out == mask).all()


def test_max_gap_frac_la_nguong_hop_ly():
    from tsds.generation.garment import garment_sam as GS
    img, mask = _ao_co_khe()
    out = GS.remove_background_gaps(img, mask)
    removed = 1.0 - float(out.sum()) / float(mask.sum())
    assert 0 < removed < GS.MAX_GAP_FRAC * 2                     # khe giả chiếm vài phần trăm mặt nạ, xa mức nghi ngờ
