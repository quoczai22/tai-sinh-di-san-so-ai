"""Kiểm thử chọn phần tử từ kho và việc nạp phần tử vào generation.controlnet.prepare (không cần GPU)."""
import json

import cv2
import numpy as np
import pytest

from generation import controlnet as cn
from generation import element_library as lib
from generation import elements as el

HINH_L = np.array([[0, 0], [80, 0], [80, 30], [40, 30], [40, 90], [0, 90]])
HINH_SAO = np.array([[10, 0], [60, 20], [90, 10], [70, 60], [95, 95], [40, 70], [0, 90], [20, 40]])


def rgba_phan_tu(poly, scale=3.0, xoay=0):
    """Ảnh RGBA của một hình bất đối xứng tô sọc xanh lam, nền trong suốt."""
    m = np.zeros((100, 100), np.uint8)
    cv2.fillPoly(m, [poly.astype(np.int32)], 1)
    n = int(100 * scale)
    m = cv2.resize(np.ascontiguousarray(m), (n, n), interpolation=cv2.INTER_NEAREST).astype(bool)
    yy, xx = np.mgrid[0:n, 0:n]
    mau = np.where(((xx // 8) % 2 == 0)[..., None], np.array([20, 50, 150]), np.array([120, 150, 220])).astype(np.uint8)
    rgba = np.dstack([mau, m.astype(np.uint8) * 255])
    ys, xs = np.where(m)
    cat = rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return np.ascontiguousarray(np.rot90(cat, xoay // 90))  # xoay cả màu lẫn mặt nạ, như một bản sao thật bị xoay


def ghi_kho(tmp_path, items):
    """Tạo kho giả: items là danh sách (element_id, rgba, ink_frac, density). Trả về (root, index_path, crops_path)."""
    folder = tmp_path / "data" / "elements" / "obj_a"
    folder.mkdir(parents=True)
    recs = []
    for eid, rgba, ink, dens in items:
        f = folder / f"{eid}.png"
        el.write_rgba_png(f, rgba)
        recs.append({"element_id": eid, "object_id": "obj_a", "size_wh": [rgba.shape[1], rgba.shape[0]],
                     "ink_frac": ink, "texel_density_rel": dens, "file": f"data/elements/obj_a/{eid}.png"})
    index = tmp_path / "data" / "elements" / "index.json"
    index.write_text(json.dumps(recs), encoding="utf-8")
    crops = tmp_path / "crops.json"
    crops.write_text(json.dumps({"H1": {"object_id": "obj_a"}}), encoding="utf-8")
    return tmp_path, index, crops


def test_diem_la_canh_ngan_nhan_net_muc_nhan_mat_do():
    rec = {"size_wh": [300, 400], "ink_frac": 0.5, "texel_density_rel": 0.8}
    assert lib.score(rec) == pytest.approx(300 * 0.5 * 0.8)
    rec2 = {"size_wh": [300, 400], "ink_frac": 0.5, "texel_density_rel": 2.0}   # mật độ cao hơn trung bình không được thưởng thêm
    assert lib.score(rec2) == pytest.approx(300 * 0.5)
    assert lib.score({"size_wh": [300, 400], "ink_frac": 0.5}) == pytest.approx(150)  # thiếu mật độ thì coi là 1


def test_chon_theo_diem_giam_dan(tmp_path):
    a = rgba_phan_tu(HINH_L, 3.0)      # to
    b = rgba_phan_tu(HINH_SAO, 2.5)    # nhỏ hơn
    root, index, crops = ghi_kho(tmp_path, [("b", b, 0.5, 1.0), ("a", a, 0.5, 1.0)])
    got = lib.pick("H1", k=2, root=root, index_path=index, crops_path=crops)
    assert [r["element_id"] for r in got] == ["a", "b"]


def test_bo_ban_xoay_gan_trung(tmp_path):
    a = rgba_phan_tu(HINH_L, 3.0)
    a_xoay = rgba_phan_tu(HINH_L, 3.0, xoay=90)   # cùng hình xoay 90 độ
    c = rgba_phan_tu(HINH_SAO, 3.0)
    root, index, crops = ghi_kho(tmp_path, [("a", a, 0.5, 1.0), ("a_xoay", a_xoay, 0.45, 1.0), ("c", c, 0.4, 1.0)])
    got = lib.pick("H1", k=3, root=root, index_path=index, crops_path=crops)
    ids = [r["element_id"] for r in got]
    assert "c" in ids and not ({"a", "a_xoay"} <= set(ids))


def test_toi_da_k_phan_tu(tmp_path):
    items = [("a", rgba_phan_tu(HINH_L, 3.0), 0.5, 1.0), ("c", rgba_phan_tu(HINH_SAO, 3.0), 0.4, 1.0)]
    root, index, crops = ghi_kho(tmp_path, items)
    assert len(lib.pick("H1", k=1, root=root, index_path=index, crops_path=crops)) == 1


def test_thieu_phan_tu_lon_thi_ha_dieu_kien_kich_thuoc(tmp_path):
    nho = rgba_phan_tu(HINH_L, 1.0)   # cạnh ngắn dưới MIN_SIDE
    assert min(nho.shape[:2]) < lib.MIN_SIDE
    root, index, crops = ghi_kho(tmp_path, [("nho", nho, 0.5, 1.0)])
    got = lib.pick("H1", k=2, root=root, index_path=index, crops_path=crops)
    assert [r["element_id"] for r in got] == ["nho"]


def test_hien_vat_la_hoac_kho_thieu_tra_ve_rong(tmp_path):
    root, index, crops = ghi_kho(tmp_path, [("a", rgba_phan_tu(HINH_L, 3.0), 0.5, 1.0)])
    assert lib.pick("KHONG_CO", root=root, index_path=index, crops_path=crops) == []
    assert lib.pick("H1", root=root, index_path=tmp_path / "khong_co.json", crops_path=crops) == []
    assert lib.pick("H1", root=root, index_path=index, crops_path=tmp_path / "khong_co.json") == []


def test_bo_qua_ban_ghi_mat_file(tmp_path):
    root, index, crops = ghi_kho(tmp_path, [("a", rgba_phan_tu(HINH_L, 3.0), 0.5, 1.0),
                                            ("c", rgba_phan_tu(HINH_SAO, 3.0), 0.4, 1.0)])
    (root / "data/elements/obj_a/a.png").unlink()
    got = lib.pick("H1", k=2, root=root, index_path=index, crops_path=crops)
    assert [r["element_id"] for r in got] == ["c"]


def test_prepare_nhan_phan_tu_rgba(tmp_path):
    f = tmp_path / "pt.png"
    el.write_rgba_png(f, rgba_phan_tu(HINH_SAO, 3.0))
    p = cn.prepare("KHONG_CO_ANH_NAY", ornament_only=True, trim=True, image_path=f)
    assert p["has_alpha"] is True
    assert p["control"].size == (512, 512) and p["reference"].size == (512, 512)
    assert p["n_edge_px"] > 100                      # có nét họa tiết thật
    assert p["reference_mask"].shape == (512, 512) and p["reference_mask"].any()


def test_prepare_khong_co_anh_van_bao_loi():
    with pytest.raises(FileNotFoundError):
        cn.prepare("KHONG_CO_ANH_NAY")


def test_bo_qua_file_hong(tmp_path):
    root, index, crops = ghi_kho(tmp_path, [("a", rgba_phan_tu(HINH_L, 3.0), 0.5, 1.0),
                                            ("c", rgba_phan_tu(HINH_SAO, 3.0), 0.4, 1.0)])
    (root / "data/elements/obj_a/a.png").write_bytes(b"day khong phai anh png")   # file tồn tại nhưng hỏng
    got = lib.pick("H1", k=2, root=root, index_path=index, crops_path=crops)
    assert [r["element_id"] for r in got] == ["c"]


# ---------- Chọn nguồn ảnh nạp cho bốn biến thể ----------

def test_nguon_mac_dinh_la_anh_hien_vat(tmp_path):
    got = lib.variant_inputs("H1", root=tmp_path)
    assert got == [("hien_vat", None)] * 4


def test_nguon_elements_quay_vong_du_4_bien_the(tmp_path):
    items = [("a", rgba_phan_tu(HINH_L, 3.0), 0.5, 1.0), ("c", rgba_phan_tu(HINH_SAO, 3.0), 0.4, 1.0)]
    root, index, crops = ghi_kho(tmp_path, items)
    got = lib.variant_inputs("H1", "elements", root=root, index_path=index, crops_path=crops)
    assert [lab for lab, _ in got] == ["a", "c", "a", "c"]
    assert all(p == root / f"data/elements/obj_a/{lab}.png" for lab, p in got)


def test_nguon_elements_thieu_kho_quay_ve_anh_hien_vat(tmp_path):
    got = lib.variant_inputs("H2", "elements", root=tmp_path, index_path=tmp_path / "x.json", crops_path=tmp_path / "y.json")
    assert got == [("hien_vat", None)] * 4


def test_nguon_khong_hop_le_bao_loi(tmp_path):
    with pytest.raises(ValueError):
        lib.variant_inputs("H1", "linh_tinh", root=tmp_path)


def test_nguon_panel_da_bi_bo_khoi_luong_san_pham(tmp_path):
    """Luồng sản phẩm đi từ ảnh bình gốc; mảng phẳng làm sẵn không còn là nguồn hợp lệ."""
    with pytest.raises(ValueError):
        lib.variant_inputs("H1", "panel", root=tmp_path)
    assert "panel" not in lib.SOURCES


# ---------- Ảnh hiện vật nền xám (ảnh render) phải được tách nền đúng ----------

def _anh_nen_xam(nen=213, w=300, h=420, trang=False):
    """Ảnh RGB không vuông: nền phẳng, ở giữa một vật hình chữ nhật có sọc xanh sẫm."""
    img = np.full((h, w, 3), 255 if trang else nen, np.uint8)
    y0, y1, x0, x1 = h // 5, h * 4 // 5, w // 4, w * 3 // 4
    yy, xx = np.mgrid[y0:y1, x0:x1]
    img[y0:y1, x0:x1] = np.where(((xx // 6) % 2 == 0)[..., None], np.array([20, 50, 150]), np.array([225, 230, 240])).astype(np.uint8)
    return img


def test_anh_nen_xam_khong_bi_coi_la_vat(tmp_path):
    f = tmp_path / "render.png"
    cv2.imwrite(str(f), cv2.cvtColor(_anh_nen_xam(), cv2.COLOR_RGB2BGR))
    p = cn.prepare("KHONG_CO_ANH_NAY", ornament_only=True, trim=True, image_path=f)
    frac = float(p["reference_mask"].mean())
    assert 0.25 < frac < 0.7                        # vật chỉ chiếm một phần khung, nền xám không bị tính vào
    nen = np.array(p["reference"])[2, 2]
    assert abs(int(nen[0]) - 213) <= 2              # viền letterbox mang màu nền xám, không phải trắng


def test_anh_nen_xam_bo_duong_bao_vat(tmp_path):
    f = tmp_path / "render.png"
    cv2.imwrite(str(f), cv2.cvtColor(_anh_nen_xam(), cv2.COLOR_RGB2BGR))
    p = cn.prepare("KHONG_CO_ANH_NAY", ornament_only=True, trim=True, image_path=f)
    ref = np.array(p["reference"]).astype(int)
    # vật thật xác định độc lập với mã đang kiểm: pixel không gần màu nền xám 213 và không gần trắng
    gan = lambda c: np.abs(ref - c).max(axis=2) < 10
    m = (~(gan(213) | gan(255))).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    vien = (m - cv2.erode(m, np.ones((9, 9), np.uint8))) > 0   # dải ngay sát đường bao vật
    nets = np.array(p["control"])[:, :, 0] > 0
    assert nets.sum() > 100                         # vẫn có nét họa tiết bên trong
    assert int((nets & vien).sum()) == 0            # nhưng không có nét ở đường bao


def test_anh_nen_trang_van_nhu_cu(tmp_path):
    f = tmp_path / "trang.png"
    cv2.imwrite(str(f), cv2.cvtColor(_anh_nen_xam(trang=True), cv2.COLOR_RGB2BGR))
    p = cn.prepare("KHONG_CO_ANH_NAY", ornament_only=True, trim=True, image_path=f)
    assert 0.25 < float(p["reference_mask"].mean()) < 0.7
    assert tuple(np.array(p["reference"])[2, 2]) == (255, 255, 255)


def _vat_men_sang(w=300, h=420):
    """Vật có viền xanh sẫm khép kín, bên trong men sáng gần màu nền xám 213 và một họa tiết nhỏ sẫm."""
    img = np.full((h, w, 3), 213, np.uint8)
    y0, y1, x0, x1 = h // 5, h * 4 // 5, w // 4, w * 3 // 4
    img[y0:y1, x0:x1] = (231, 232, 235)                       # men sáng: lệch màu nền chỉ khoảng 20, dưới ngưỡng tách nền (26)
    cv2.rectangle(img, (x0, y0), (x1 - 1, y1 - 1), (20, 50, 150), 6)  # viền khép kín
    cv2.circle(img, ((x0 + x1) // 2, (y0 + y1) // 2), 40, (20, 50, 150), 5)  # họa tiết nằm giữa vùng men sáng
    return img


def test_men_sang_khong_lam_thung_mat_na(tmp_path):
    f = tmp_path / "men_sang.png"
    cv2.imwrite(str(f), cv2.cvtColor(_vat_men_sang(), cv2.COLOR_RGB2BGR))
    p = cn.prepare("KHONG_CO_ANH_NAY", ornament_only=True, trim=True, image_path=f)
    m = p["reference_mask"]
    ys, xs = np.where(m > 0)
    cy, cx = int(ys.mean()), int(xs.mean())
    assert m[cy, cx] > 0                                           # tâm vùng men sáng thuộc vật, không bị thủng
    nets = np.array(p["control"])[:, :, 0] > 0
    assert int(nets[cy - 60:cy + 60, cx - 60:cx + 60].sum()) > 50   # nét của họa tiết giữa thân còn giữ lại


def test_lap_lo_khong_lap_nen_ngoai():
    m = np.zeros((20, 20), np.uint8)
    m[5:15, 5:15] = 1
    m[8:12, 8:12] = 0                                              # lỗ trong vật
    out = cn._fill_holes(m)
    assert out[10, 10] == 1 and out[0, 0] == 0 and out[19, 19] == 0
    assert out.sum() == 100                                        # chỉ lấp lỗ, không nở thêm
