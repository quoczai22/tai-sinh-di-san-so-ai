"""Kiểm thử phần không cần GPU của việc nối áo do LoRA sinh vào luồng thiết kế."""
import numpy as np
from PIL import Image

from generation import garment_lora as gl
from generation import layout_select
from quality import retry as R


def ao(h=688, w=512, y0=40, y1=660, x0=150, x1=370):
    m = np.zeros((h, w), np.uint8)
    m[y0:y1, x0:x1] = 1
    return m


def test_mat_na_hop_le():
    assert gl.mask_ok(ao()) == (True, "")


def test_mat_na_bi_loai_dung_ly_do():
    assert gl.mask_ok(np.zeros((100, 100)))[1] == "mặt nạ rỗng"
    assert "chạm mép" in gl.mask_ok(ao(x0=0))[1]
    assert "chạm mép" in gl.mask_ok(ao(x1=512))[1]
    assert "diện tích" in gl.mask_ok(ao(x0=240, x1=270))[1]                      # áo quá hẹp: dưới 8% khung
    assert "diện tích" in gl.mask_ok(ao(x0=5, x1=505, y0=5, y1=680))[1]           # phủ gần cả khung
    assert "thấp hơn 60%" in gl.mask_ok(ao(y0=300, y1=500, x0=100, x1=400))[1]    # áo chỉ cao 200/688 = 29%


def test_rank_chuyen_ao_va_vung_ao_xuong_apply(monkeypatch):
    goi = []
    monkeypatch.setattr(layout_select.garment, "apply", lambda p, layout, **kw: goi.append(kw) or Image.new("RGB", (8, 8)))
    monkeypatch.setattr(layout_select, "score_design", lambda img: 0.0)
    vung = ao()
    layout_select.rank(Image.new("RGB", (8, 8)), only=["front_panel"], template_path="a.png", garment_region=vung)
    assert goi[0]["template_path"] == "a.png" and goi[0]["garment_region"] is vung
    goi.clear()
    layout_select.rank(Image.new("RGB", (8, 8)), only=["front_panel"])
    assert "template_path" not in goi[0] and goi[0]["garment_region"] is None


def test_bo_do_g3_dung_ao_va_vung_ao_tinh_san(tmp_path):
    p = tmp_path / "ao.png"
    Image.new("RGB", (200, 300), (255, 255, 255)).save(p)
    vung = np.zeros((300, 200), np.uint8)
    vung[50:250, 70:130] = 1
    raw = Image.new("RGB", (200, 300), (230, 230, 230))
    ev = R.make_g3_evaluator(raw, "front_panel", template_path=p, garment_region=vung)
    g3 = ev(raw.copy())                                         # ảnh cuối giống hệt ảnh ghép thô
    assert g3["details"]["outside_drift"] == 0.0
    assert "garment_shape_iou" in g3["metrics"]


def test_pick_seed_ngau_nhien_khi_khong_chi_dinh_va_giu_nguyen_khi_co():
    from generation import garment_lora as gl
    assert gl.pick_seed(7) == 7 and gl.pick_seed(0) == 0          # seed 0 vẫn là seed hợp lệ
    seeds = {gl.pick_seed() for _ in range(20)}
    assert len(seeds) > 1 and all(0 <= s < 2**31 for s in seeds)  # không còn mặc định cố định 42


def _ao_mau(mau_than, ti_le_mau=0.0, nen=(240, 240, 240)):
    """Ảnh áo giả: nền xám, vùng áo trắng, có thể tô một mảng màu chiếm `ti_le_mau` vùng áo."""
    vung = ao()
    a = np.full((688, 512, 3), nen, np.uint8)
    a[vung > 0] = (245, 245, 245)
    ys, xs = np.where(vung > 0)
    n = int(len(ys) * ti_le_mau)
    a[ys[:n], xs[:n]] = mau_than                       # ys đã xếp theo hàng: mảng màu nằm ở phần trên áo
    return Image.fromarray(a), vung


def test_ao_trang_tron_hop_le():
    img, vung = _ao_mau((200, 30, 30), 0.0)
    assert gl.color_ok(img, vung) == (True, "")


def test_ao_co_mang_do_hoac_cam_bi_loai():
    for mau in ((200, 30, 30), (230, 140, 20)):         # đỏ, cam
        img, vung = _ao_mau(mau, 0.25)
        ok, why = gl.color_ok(img, vung)
        assert not ok and "màu rực" in why


def test_vien_mau_nho_van_chap_nhan():
    img, vung = _ao_mau((200, 30, 30), 0.02)           # thắt lưng hoặc viền chiếm 2% vùng áo
    assert gl.color_ok(img, vung)[0]


def test_mau_ngoai_vung_ao_khong_tinh():
    img, vung = _ao_mau((245, 245, 245), 0.0)
    a = np.asarray(img).copy()
    a[:100, :100] = (200, 30, 30)                       # đỏ ở nền, ngoài mặt nạ áo
    assert gl.color_ok(Image.fromarray(a), vung)[0]


def test_mau_sam_toi_khong_bi_coi_la_mau_ruc():
    # vùng áo xám đậm hay bóng đổ có độ bão hòa cao nhưng rất tối: không tính là màu rực
    vung = ao()
    a = np.full((688, 512, 3), 240, np.uint8)
    a[vung > 0] = (30, 8, 8)
    assert gl.color_ok(Image.fromarray(a), vung)[0]


def test_mat_na_rong_bi_loai_o_color_ok():
    assert gl.color_ok(Image.new("RGB", (10, 10)), np.zeros((10, 10)))[1] == "mặt nạ rỗng"


def test_bien_the_mac_dinh_dung_chung_bo_cuc_co_dinh():
    from generation import garment, streamlit_runner as sr
    assert {v["layout"] for v in sr.DEFAULT_VARIANTS} == {"front_panel"}
    garment.get_layout("front_panel")                   # bố cục phải tồn tại (không ném lỗi)
    assert [v["level"] for v in sr.DEFAULT_VARIANTS] == [1, 2, 3, 4]
