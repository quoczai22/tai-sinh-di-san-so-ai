# -*- coding: utf-8 -*-
"""EXP-G: các hàm tạo ô hoa văn chạy trên CPU (cắt ô, làm liền mạch, phần tử so le, đo SIFT) và đặc tả thí nghiệm."""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from tsds.evaluation import exp_g as G
from tsds.evaluation import experiment as E


def test_largest_rect_known_cases():
    m = np.zeros((10, 12), np.uint8)
    m[2:7, 3:11] = 1                                   # hình chữ nhật 5 hàng x 8 cột
    assert G.largest_rect(m) == (3, 2, 11, 7)
    m[4, 5] = 0                                        # một lỗ ở giữa: hình lớn nhất phải tránh lỗ
    # tối ưu: bỏ 3 cột bên trái lỗ, giữ cột 6..10 x hàng 2..6 = 5x5 = 25 ô
    assert G.largest_rect(m) == (6, 2, 11, 7)
    assert G.largest_rect(np.zeros((5, 5), np.uint8)) == (0, 0, 0, 0)


def test_crop_inscribed_stays_inside_valid_area():
    # mảng 400x600, chỉ nửa trái (x < 300) có nội dung màu đỏ, nửa phải trong suốt
    a = np.zeros((600, 400, 4), np.uint8)
    a[:, :300] = (200, 10, 10, 255)
    crop = G.crop_inscribed(Image.fromarray(a), tile_max=256)
    c = np.asarray(crop)
    assert max(crop.size) == 256
    assert (c[:, :, 0] > 150).all(), "ô cắt không được chứa vùng trong suốt (đen)"


def test_make_seamless_edges_match():
    # ảnh trơn (nhiễu thấp tần phóng to) để hai cột kề nhau có tính liên tục; nhiễu trắng thì không kiểm được gì
    img = _textured(0, 256)
    raw = np.asarray(img).astype(float)
    s = np.asarray(G.make_seamless(img)).astype(float)
    seam_raw = np.abs(raw[:, 0] - raw[:, -1]).mean()      # mép trái so với mép phải của ảnh gốc: chênh lớn
    seam_new = np.abs(s[:, 0] - s[:, -1]).mean()
    inner_new = np.abs(s[:, 127] - s[:, 128]).mean()       # hai cột kề nhau bên trong ô mới
    assert seam_new < 0.3 * seam_raw
    assert seam_new <= 2 * inner_new + 1, "chênh ở mép nối phải cỡ chênh giữa hai cột kề trong ô"
    # chiều dọc cũng vậy
    assert np.abs(s[0] - s[-1]).mean() < 0.3 * np.abs(raw[0] - raw[-1]).mean()


def test_tile_from_element_is_square_and_wraps():
    el = Image.new("RGBA", (100, 60), (0, 0, 0, 0))
    el.paste((10, 20, 200, 255), (0, 0, 100, 60))
    ground = (240, 240, 240)
    tile = G.tile_from_element(el, ground, fill=0.4)
    t = tile.width
    assert tile.size == (t, t) and abs(t - 250) <= 1      # cạnh ô = cạnh dài phần tử / fill
    a = np.asarray(tile).astype(int)
    ink = (np.abs(a - np.array(ground)).sum(axis=2) > 60)
    # bản giữa ở tâm ô và bản góc ở các góc: tâm và hai góc đối đều có mực
    assert ink[t // 2, t // 2] and ink[0, 0] and ink[t - 1, t - 1]
    # mật độ mực = 2 bản (diện tích mỗi bản 100x60) trên diện tích ô
    expect = 2 * 100 * 60 / (t * t)
    assert ink.mean() == pytest.approx(expect, rel=0.1)


def test_tile_from_element_rejects_overlap_and_empty():
    with pytest.raises(ValueError):
        G.tile_from_element(Image.new("RGBA", (10, 10), (1, 1, 1, 255)), (0, 0, 0), fill=0.8)
    with pytest.raises(ValueError):
        G.tile_from_element(Image.new("RGBA", (10, 10), (0, 0, 0, 0)), (0, 0, 0))


def test_ground_color_is_light_pixels():
    a = np.zeros((50, 50, 4), np.uint8)
    a[:, :, :3], a[:, :, 3] = (230, 230, 230), 255
    a[:20, :20, :3] = (10, 10, 120)                     # mực xanh chiếm 16% diện tích
    assert G.ground_color(Image.fromarray(a)) == (230, 230, 230)


def _textured(seed: int, size: int = 400) -> Image.Image:
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 255, (size // 8, size // 8), dtype=np.uint8)
    return Image.fromarray(base).resize((size, size), Image.BICUBIC).convert("RGB")


def test_sift_ratio_separates_copy_from_unrelated():
    panel = _textured(1, 600)
    crop = panel.crop((100, 100, 500, 500))             # bản sao một phần của mảng
    other = _textured(2, 400)                           # ảnh không liên quan
    same = G.sift_inlier_ratio(crop, panel)
    diff = G.sift_inlier_ratio(other, panel)
    assert same > 0.3
    assert diff < 0.1
    assert same > 3 * diff


def test_exp_g_spec_expands_to_126_single_factor_runs():
    spec = E.load_spec(G.SPEC)
    rows = E.expand_plan(spec)                          # validate_plan ném lỗi nếu đổi nhiều hơn một biến
    assert len(rows) == 6 * 7 * 3
    assert {r["iv_level"] for r in rows} == set(G.LEVELS)
    assert len({r["run_key"] for r in rows}) == 126
    assert spec["independent_variable"]["levels"][0] == "sd_controlnet", "mức đối chứng phải đứng đầu"


def test_make_seamless_keeps_center_pixels():
    img = _textured(3, 200)
    s = np.asarray(G.make_seamless(img, band=0.15)).astype(int)
    raw = np.asarray(img).astype(int)
    c = slice(40, 160)                                   # ruột ô, cách mép hơn 15% (30 điểm)
    assert (s[c, c] == raw[c, c]).all(), "phần giữa phải là pixel gốc, chỉ dải mép được hòa"
    with pytest.raises(ValueError):
        G.make_seamless(img, band=0.8)


def test_gate_runs_on_nonsquare_tile_resized_to_reference():
    """Lỗi đã gặp: ô 644x1024 không khớp ảnh tham chiếu 512x512 trong vessel_leakage. Đo trên bản 512x512 thì chạy được."""
    from tsds.quality import gate as QG
    tile = _textured(4, 400).resize((250, 400))
    ref = np.asarray(_textured(5, 512))
    qa = np.asarray(tile.resize((512, 512), Image.LANCZOS))
    res = QG.evaluate_pattern(qa, ref, QG.load_config())
    assert "vessel_leakage" in res["metrics"] and "seam_ratio" in res["metrics"]
    with pytest.raises(ValueError):                      # chứng minh lỗi cũ: kích thước lệch thì ném lỗi
        QG.evaluate_pattern(np.asarray(tile), ref, QG.load_config())


def _ink_tile(contrast: float, blue_stain: bool = False) -> Image.Image:
    """Ô giả: nền kem, nét mực xanh nhạt (tương phản thấp nếu contrast nhỏ), có thể thêm một vết ố vàng."""
    a = np.full((120, 120, 3), (232, 228, 214), np.uint8)
    ink = (np.array((232, 228, 214)) * (1 - contrast) + np.array((70, 100, 200)) * contrast).astype(np.uint8)
    a[30:90, 40:50] = ink
    a[30:40, 40:90] = ink
    if blue_stain:
        a[100:106, 100:106] = (200, 170, 60)
    return Image.fromarray(a)


def test_boost_ink_strengthens_faint_ink_and_keeps_ground():
    ground = (232, 228, 214)
    faint = _ink_tile(0.25)
    out = np.asarray(G.boost_ink(faint, ground)).astype(float)
    src = np.asarray(faint).astype(float)
    assert np.abs(out[5, 5] - src[5, 5]).max() <= 2, "màu nền neo tại màu nền, không được đổi"
    assert np.abs(out[50, 45] - np.array(ground)).sum() > 1.4 * np.abs(src[50, 45] - np.array(ground)).sum()
    # mực xanh đậm lên: kênh đỏ giảm so với bản gốc
    assert out[50, 45, 0] < src[50, 45, 0]


def test_boost_ink_leaves_contrasty_ink_nearly_unchanged():
    ground = (232, 228, 214)
    strong = _ink_tile(1.0)                              # mực đã đủ đậm, hệ số kéo phải về 1
    diff = np.abs(np.asarray(G.boost_ink(strong, ground)).astype(float) - np.asarray(strong).astype(float))
    assert diff.max() <= 12


def test_boost_ink_does_not_amplify_yellow_stains():
    ground = (232, 228, 214)
    tile = _ink_tile(0.25, blue_stain=True)
    boosted = np.asarray(G.boost_ink(tile, ground)).astype(float)
    base = np.asarray(tile).astype(float)
    # vết ố vàng (b dương) không được kéo sắc thêm: độ chênh với nền chỉ tăng theo hệ số khoảng cách kl, không thêm kc
    stain_before = np.abs(base[102, 102] - np.array(ground)).sum()
    stain_after = np.abs(boosted[102, 102] - np.array(ground)).sum()
    ink_before = np.abs(base[50, 45] - np.array(ground)).sum()
    ink_after = np.abs(boosted[50, 45] - np.array(ground)).sum()
    assert ink_after / ink_before > stain_after / stain_before


def _cand(i, size, fill, clip):
    return {"element_id": f"e{i}", "size_wh": size, "fill": fill, "clip": clip}


def test_rank_elements_filters_shape_then_orders_by_clip():
    cands = [
        _cand(0, (150, 150), 0.9, 0.40),     # quá nhỏ: bị loại dù CLIP cao nhất
        _cand(1, (2200, 600), 0.9, 0.35),    # dải quá dài (tỉ lệ 3,7): bị loại
        _cand(2, (600, 600), 0.2, 0.34),     # rời rạc (fill thấp): bị loại
        _cand(3, (600, 500), 0.7, 0.30),     # hợp lệ
        _cand(4, (700, 700), 0.8, 0.32),     # hợp lệ, CLIP cao hơn
    ]
    assert [c["element_id"] for c in G.rank_elements(cands)] == ["e4", "e3"]


def test_rank_elements_penalizes_small_and_falls_back_when_none_pass():
    big = _cand(0, (800, 800), 0.8, 0.290)
    small = _cand(1, (210, 210), 0.8, 0.300)    # CLIP nhỉnh hơn nhưng nhỏ: phạt (210/400)^0.25 = 0,85
    assert G.rank_elements([small, big])[0]["element_id"] == "e0"
    allbad = [_cand(0, (100, 100), 0.1, 0.2), _cand(1, (120, 90), 0.1, 0.3)]
    assert [c["element_id"] for c in G.rank_elements(allbad)] == ["e1", "e0"]   # không ai qua lọc: vẫn trả về hết


def test_rank_elements_is_deterministic_on_ties():
    a, b = _cand(7, (500, 500), 0.8, 0.3), _cand(3, (500, 500), 0.8, 0.3)
    assert [c["element_id"] for c in G.rank_elements([a, b])] == ["e3", "e7"]
    assert [c["element_id"] for c in G.rank_elements([b, a])] == ["e3", "e7"]


def test_element_fill():
    el = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    el.paste((9, 9, 9, 255), (20, 30, 60, 90))           # 40 x 60 đục
    assert G.element_fill(el) == pytest.approx(1.0)       # hộp bao chính là vùng đục
    el.paste((0, 0, 0, 0), (30, 40, 50, 60))              # khoét một lỗ 20 x 20
    assert G.element_fill(el) == pytest.approx(1 - 400 / 2400, abs=1e-6)
    assert G.element_fill(Image.new("RGBA", (10, 10), (0, 0, 0, 0))) == 0.0
