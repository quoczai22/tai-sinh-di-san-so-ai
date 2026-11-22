"""Kiểm thử tsds/generation/pattern/elements.py bằng ảnh tổng hợp và bộ phân đoạn giả (không cần GPU, không cần SAM)."""
import json
from pathlib import Path

import cv2
import numpy as np

from tsds.generation.pattern import elements as el

# Hai hình bất đối xứng dùng làm "họa tiết" thử. Đa giác theo tọa độ (x, y).
HINH_L = np.array([[0, 0], [80, 0], [80, 30], [40, 30], [40, 90], [0, 90]])
HINH_SAO = np.array([[10, 0], [60, 20], [90, 10], [70, 60], [95, 95], [40, 70], [0, 90], [20, 40]])


def mat_na(poly, size=100):
    m = np.zeros((size, size), np.uint8)
    cv2.fillPoly(m, [poly.astype(np.int32)], 1)
    return m.astype(bool)


def dan_hoa_tiet(canvas, m, x, y):
    """Dán hình m lên canvas tại (x, y), tô sọc xanh lam để có độ lệch chuẩn và nét mực."""
    h, w = m.shape
    yy, xx = np.mgrid[0:h, 0:w]
    mau = np.where(((xx // 4) % 2 == 0)[..., None], np.array([20, 50, 150]), np.array([120, 150, 220]))
    vung = canvas[y:y + h, x:x + w]
    vung[m] = mau[m]


def canvas_trang(size=800):
    return np.full((size, size, 3), 245, np.uint8)


def phan_doan_gia(tile):
    """Bộ phân đoạn giả: mỗi thành phần liên thông của pixel không phải nền trắng là một mặt nạ.

    Pixel xám đúng (128,128,128) là vùng ngoài UV do quy trình tô, bỏ qua giống SAM không coi nó là họa tiết.
    """
    ink = ((tile.mean(axis=2) < 220) & ~(tile == 128).all(axis=2)).astype(np.uint8)
    n, lab = cv2.connectedComponents(ink)
    return [lab == i for i in range(1, n)]


def phan_doan_gia_to(tile):
    """Như phan_doan_gia nhưng nở mặt nạ thêm 3 pixel, mô phỏng SAM cho mặt nạ rộng hơn vật thật."""
    return [cv2.dilate(m.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0 for m in phan_doan_gia(tile)]


def ghi_anh(path, rgb):
    cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


def cfg_nho(**kw):
    base = dict(work_max=800, tile=800, overlap=100, min_side_src=40, min_std=10.0, pad=4, erode_px=1)
    base.update(kw)
    return el.Config(**base)


def viet_obj_nua_trai(path):
    """File .obj có UV chỉ phủ nửa trái texture (u từ 0 đến 0.5)."""
    path.write_text(
        "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\n"
        "vt 0 0\nvt 0.5 0\nvt 0.5 1\nvt 0 1\n"
        "f 1/1 2/2 3/3\nf 1/1 3/3 4/4\n")


# ---------- UV và mật độ texel ----------

def test_uv_mask_nua_trai(tmp_path):
    p = tmp_path / "a.obj"
    viet_obj_nua_trai(p)
    m = el.uv_valid_mask(p, 200, 100, erode=0)
    assert m[:, :95].all()           # nửa trái được phủ
    assert not m[:, 105:].any()      # nửa phải không được phủ


def test_uv_truc_v_lat(tmp_path):
    # tam giác nằm ở v từ 0.8 đến 1 (phía trên của UV) phải rơi vào hàng ảnh phía trên
    p = tmp_path / "b.obj"
    p.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0.8\nvt 1 0.8\nvt 0 1\nf 1/1 2/2 3/3\n")
    m = el.uv_valid_mask(p, 100, 100, erode=0)
    assert m[:15].any() and not m[30:].any()


def test_chi_so_am_va_khong_co_uv(tmp_path):
    p = tmp_path / "c.obj"
    p.write_text("v 0 0 0\nv 1 0 0\nv 1 1 0\nvt 0 0\nvt 1 0\nvt 1 1\nf -3/-3 -2/-2 -1/-1\n")
    assert len(el.read_uv_polygons(p)) == 1
    q = tmp_path / "d.obj"
    q.write_text("v 0 0 0\nv 1 0 0\nv 1 1 0\nf 1 2 3\n")  # không có vt
    assert el.uv_valid_mask(q, 50, 50) is None


def test_mat_do_texel(tmp_path):
    # hai hình vuông 3D cùng diện tích 1; hình thứ hai chiếm UV gấp 4 lần diện tích, nên mật độ dài gấp 2
    p = tmp_path / "e.obj"
    p.write_text(
        "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\n"
        "vt 0 0\nvt 0.2 0\nvt 0.2 0.2\nvt 0 0.2\n"        # UV cạnh 0.2
        "vt 0.5 0.5\nvt 0.9 0.5\nvt 0.9 0.9\nvt 0.5 0.9\n"  # UV cạnh 0.4
        "f 1/1 2/2 3/3 4/4\nf 1/5 2/6 3/7 4/8\n")
    d = el.texel_density_map(p, 1000, 1000)
    nho = d[800:810, 100:110].mean()   # ô UV cạnh 0.2 (v 0 đến 0.2 nằm phía dưới ảnh)
    lon = d[300:310, 600:610].mean()   # ô UV cạnh 0.4
    assert abs(lon / nho - 2.0) < 0.05


# ---------- Quy trình cắt phần tử ----------

def chay(tmp_path, canvas, obj=None, cfg=None, ten="vat_01", seg=phan_doan_gia):
    tex = tmp_path / "tex.png"
    ghi_anh(tex, canvas)
    return el.build_object(tex, obj, ten, tmp_path / "out", seg, cfg or cfg_nho())


def test_loai_nen_phang_va_bo_trung_khi_xoay(tmp_path):
    c = canvas_trang()
    dan_hoa_tiet(c, mat_na(HINH_L), 100, 100)
    dan_hoa_tiet(c, np.rot90(mat_na(HINH_L)), 500, 100)      # cùng hình, xoay 90 độ: phải bị coi là trùng
    dan_hoa_tiet(c, mat_na(HINH_SAO), 100, 500)             # hình khác: phải giữ
    c[500:560, 500:600] = (60, 60, 160)                     # mảng xanh phẳng, độ lệch chuẩn 0: phải loại
    recs = chay(tmp_path, c)
    assert len(recs) == 2
    assert all(r["license_status"] == "unverified" and r["source_dataset"] == "LR3D-CULT2" for r in recs)
    assert all(r["valid_mask_method"] == "nonblack" for r in recs)


def test_pixel_ben_trong_giu_nguyen(tmp_path):
    c = canvas_trang()
    dan_hoa_tiet(c, mat_na(HINH_SAO), 200, 300)
    recs = chay(tmp_path, c)
    assert len(recs) == 1
    r = recs[0]
    img = cv2.imread(r["file"], cv2.IMREAD_UNCHANGED)
    assert img.shape[2] == 4
    x0, y0, x1, y1 = r["box_xyxy"]
    goc = cv2.cvtColor(img[..., :3], cv2.COLOR_BGR2RGB)
    loi = img[..., 3] == 255
    assert loi.sum() > 1000
    assert np.array_equal(goc[loi], c[y0:y1, x0:x1][loi])   # pixel lõi trùng từng bit với ảnh gốc
    assert img[0, 0, 3] == 0                                # góc viền thêm phải trong suốt


def test_phan_tu_qua_bien_o_van_tron_va_khong_trung(tmp_path):
    c = canvas_trang()
    dan_hoa_tiet(c, mat_na(HINH_L), 380, 100)   # nằm vắt qua biên ô tại x = 400
    recs = chay(tmp_path, c, cfg=cfg_nho(tile=400, overlap=150))
    assert len(recs) == 1                       # không bị mất, không bị nhân đôi
    assert recs[0]["size_wh"][0] >= 80          # trọn chiều ngang 80 pixel của hình L


def test_uv_loai_vung_ngoai(tmp_path):
    c = canvas_trang()
    dan_hoa_tiet(c, mat_na(HINH_L), 100, 100)    # nửa trái: hợp lệ
    dan_hoa_tiet(c, mat_na(HINH_SAO), 600, 100)  # nửa phải: ngoài UV
    obj = tmp_path / "m.obj"
    viet_obj_nua_trai(obj)
    recs = chay(tmp_path, c, obj=obj)
    assert len(recs) == 1
    assert recs[0]["valid_mask_method"] == "uv"
    assert recs[0]["box_xyxy"][2] < 400


def test_obj_khong_uv_dung_phuong_an_du_phong(tmp_path):
    c = canvas_trang()
    dan_hoa_tiet(c, mat_na(HINH_L), 100, 100)
    obj = tmp_path / "n.obj"
    obj.write_text("v 0 0 0\nv 1 0 0\nv 1 1 0\nf 1 2 3\n")
    recs = chay(tmp_path, c, obj=obj)
    assert recs and recs[0]["valid_mask_method"] == "nonblack"


def test_chay_lai_khong_con_file_cu(tmp_path):
    c = canvas_trang()
    dan_hoa_tiet(c, mat_na(HINH_L), 100, 100)
    dan_hoa_tiet(c, mat_na(HINH_SAO), 400, 400)
    r1 = chay(tmp_path, c)
    assert len(r1) == 2
    c2 = canvas_trang()
    dan_hoa_tiet(c2, mat_na(HINH_L), 100, 100)
    r2 = chay(tmp_path, c2)
    assert len(r2) == 1
    assert len(list((tmp_path / "out" / "vat_01").glob("vat_01_e*.png"))) == 1


def test_ghi_index(tmp_path):
    c = canvas_trang()
    dan_hoa_tiet(c, mat_na(HINH_L), 100, 100)
    recs = chay(tmp_path, c)
    el.update_index(tmp_path / "index.json", recs, ["vat_01"])
    doc = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert doc[0]["element_id"] == "vat_01_e000" and Path(doc[0]["file"]).exists()


# ---------- Các ca bổ sung sau khi rà soát mã ----------

def test_doi_toa_do_khi_thu_nho(tmp_path):
    # ảnh 1600x1600, ảnh làm việc 800x800 (tỉ lệ 0.5): khung bao và pixel lõi vẫn phải đúng trên ảnh gốc
    c = canvas_trang(1600)
    big = cv2.resize(mat_na(HINH_L).astype(np.uint8), (200, 200), interpolation=cv2.INTER_NEAREST).astype(bool)
    dan_hoa_tiet(c, big, 400, 600)
    recs = chay(tmp_path, c, cfg=cfg_nho(min_side_src=96))
    assert len(recs) == 1
    r = recs[0]
    x0, y0, x1, y1 = r["box_xyxy"]
    assert abs(x0 - (400 - 4)) <= 6 and abs(y0 - (600 - 4)) <= 6      # khung bao quanh vị trí thật, cộng viền
    assert x1 - x0 >= 160 and y1 - y0 >= 180            # hình L rộng 80 và cao 90 khi phóng 2 lần, chưa tính viền
    img = cv2.imread(r["file"], cv2.IMREAD_UNCHANGED)
    loi = img[..., 3] == 255
    assert np.array_equal(cv2.cvtColor(img[..., :3], cv2.COLOR_BGR2RGB)[loi], c[y0:y1, x0:x1][loi])


def test_phan_tu_rong_gan_bang_overlap_van_giu_duoc(tmp_path):
    # ô 400, chồng 200 (bước 200): phần tử rộng 190 vắt qua x = 400 vẫn phải nằm trọn trong một ô
    c = canvas_trang()
    lon = cv2.resize(mat_na(HINH_L).astype(np.uint8), (190, 190), interpolation=cv2.INTER_NEAREST).astype(bool)
    dan_hoa_tiet(c, lon, 250, 100)
    recs = chay(tmp_path, c, cfg=cfg_nho(tile=400, overlap=200))
    assert len(recs) == 1 and recs[0]["size_wh"][0] >= 152   # hình L phóng 1,9 lần rộng 152, chưa tính viền


def test_alpha_khong_nam_ngoai_uv_du_mat_na_to(tmp_path):
    # mặt nạ SAM giả to hơn vật 3 pixel, vật sát biên UV (x = 400): pixel lõi vẫn không được vượt biên
    c = canvas_trang()
    dan_hoa_tiet(c, mat_na(HINH_L), 322, 100)          # chiều ngang 80, chạm sát biên UV
    obj = tmp_path / "u.obj"
    viet_obj_nua_trai(obj)
    recs = chay(tmp_path, c, obj=obj, seg=phan_doan_gia_to)
    assert len(recs) == 1
    valid = el.uv_valid_mask(obj, 800, 800)             # cùng cách tính với quy trình
    img = cv2.imread(recs[0]["file"], cv2.IMREAD_UNCHANGED)
    x0, y0, x1, y1 = recs[0]["box_xyxy"]
    loi = img[..., 3] == 255
    assert loi.any()
    assert valid[y0:y1, x0:x1][loi].all()               # mọi pixel alpha 255 đều nằm trong vùng hợp lệ


def test_hinh_don_gian_khac_nhau_khong_bi_gop(tmp_path):
    # hình tròn và hình vuông đối xứng: không đủ thông tin để so hình dạng bất kể cỡ, phải giữ cả hai
    c = canvas_trang()
    disc = np.zeros((100, 100), np.uint8)
    cv2.circle(disc, (50, 50), 45, 1, -1)
    dan_hoa_tiet(c, disc.astype(bool), 100, 100)
    dan_hoa_tiet(c, np.ones((100, 100), bool), 400, 400)
    recs = chay(tmp_path, c)
    assert len(recs) == 2


def test_update_index_chi_thay_vat_vua_xu_ly(tmp_path):
    p = tmp_path / "index.json"
    a = [{"element_id": "vat_01_e000", "object_id": "vat_01"}, {"element_id": "vat_01_e001", "object_id": "vat_01"}]
    b = [{"element_id": "vat_02_e000", "object_id": "vat_02"}]
    el.update_index(p, a + b, ["vat_01", "vat_02"])
    merged = el.update_index(p, [{"element_id": "vat_01_e000", "object_id": "vat_01"}], ["vat_01"])
    ids = [r["element_id"] for r in merged]
    assert ids == ["vat_01_e000", "vat_02_e000"]         # vật 01 bị thay, vật 02 giữ nguyên
    assert json.loads(p.read_text(encoding="utf-8")) == merged


def test_to_rgba_he_so_khong_vuong(tmp_path):
    # khung bao 100..300 x 200..500 trên ảnh làm việc, tỉ lệ 0.25: ra 400..1200 x 800..2000 trên ảnh gốc
    r = el.Region(np.ones((300, 200), bool), 100, 200)
    rgb = np.full((8192, 8192, 3), 200, np.uint8)
    out, box = el.to_rgba(rgb, r, (0.25, 0.25), el.Config(pad=0, erode_px=0))
    assert box == (400, 800, 1200, 2000)
    assert (out[..., 3] == 255).all() or (out[..., 3] > 0).mean() > 0.99


# ---------- Lọc sau khi xuất: mảnh mỏng và bản gần trùng ----------

def _rgba_hinh(poly, scale=3.0, xoay=0):
    m = mat_na(poly)
    n = int(100 * scale)
    m = cv2.resize(m.astype(np.uint8), (n, n), interpolation=cv2.INTER_NEAREST).astype(bool)
    yy, xx = np.mgrid[0:n, 0:n]
    mau = np.where(((xx // 8) % 2 == 0)[..., None], np.array([20, 50, 150]), np.array([120, 150, 220])).astype(np.uint8)
    rgba = np.dstack([mau, m.astype(np.uint8) * 255])
    ys, xs = np.where(m)
    return np.ascontiguousarray(np.rot90(rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1], xoay // 90))


def _bang_ghi(tmp_path, items):
    """items: danh sách (element_id, rgba). Ghi PNG và trả về danh sách bản ghi giống index.json."""
    recs = []
    for eid, rgba in items:
        f = tmp_path / f"{eid}.png"
        el.write_rgba_png(f, rgba)
        recs.append({"element_id": eid, "file": str(f), "size_wh": [rgba.shape[1], rgba.shape[0]]})
    return recs


def test_postfilter_loai_soi_chi(tmp_path):
    soi = np.zeros((220, 14, 4), np.uint8)
    soi[..., :3] = (20, 50, 150)
    soi[..., 3] = 255                                   # dải 14 pixel rộng, 220 pixel dài
    recs = _bang_ghi(tmp_path, [("hinh", _rgba_hinh(HINH_L)), ("soi", soi)])
    kept, dropped = el.postfilter(recs)
    assert [r["element_id"] for r in kept] == ["hinh"]
    assert [(r["element_id"], why) for r, why in dropped] == [("soi", "mỏng")]


def test_postfilter_gop_ban_xoay_va_giu_hinh_khac(tmp_path):
    recs = _bang_ghi(tmp_path, [("a", _rgba_hinh(HINH_L)), ("a_xoay", _rgba_hinh(HINH_L, xoay=90)),
                                ("sao", _rgba_hinh(HINH_SAO))])
    kept, dropped = el.postfilter(recs)
    assert sorted(r["element_id"] for r in kept) == ["a", "sao"] or sorted(r["element_id"] for r in kept) == ["a_xoay", "sao"]
    assert len(dropped) == 1 and dropped[0][1] == "trùng"


def _dia(kieu, n=200):
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.hypot(yy - n / 2, xx - n / 2)
    if kieu == "vong":
        sang = ((r // 12) % 2 == 0)
    else:                                               # kiểu tia
        sang = ((np.arctan2(yy - n / 2, xx - n / 2) * 6 / np.pi).astype(int) % 2 == 0)
    mau = np.where(sang[..., None], np.array([20, 50, 150]), np.array([120, 150, 220])).astype(np.uint8)
    return np.dstack([mau, ((r < n / 2 - 2) * 255).astype(np.uint8)])


def test_postfilter_khong_gop_hai_dia_tron_khac_ben_trong(tmp_path):
    # cùng hình tròn, cùng tông màu, nhưng bên trong khác (vòng tròn đồng tâm so với tia): phải giữ cả hai
    recs = _bang_ghi(tmp_path, [("vong", _dia("vong")), ("tia", _dia("tia")), ("vong_2", _dia("vong"))])
    kept, dropped = el.postfilter(recs)
    ids = sorted(r["element_id"] for r in kept)
    assert "tia" in ids and len(ids) == 2               # chỉ một trong hai đĩa vòng bị coi là trùng
    assert [why for _, why in dropped] == ["trùng"]


def test_postfilter_khong_sap_khi_mat_file(tmp_path):
    recs = _bang_ghi(tmp_path, [("a", _rgba_hinh(HINH_L)), ("b", _rgba_hinh(HINH_SAO))])
    (tmp_path / "b.png").unlink()                       # bản ghi trỏ tới file đã mất
    kept, dropped = el.postfilter(recs)
    assert [r["element_id"] for r in kept] == ["a"]
    assert [(r["element_id"], why) for r, why in dropped] == [("b", "lỗi file")]
