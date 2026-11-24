"""Kiểm thử script thí nghiệm mặt nạ vùng in (scripts/eval/print_region_mask.py) bằng lần chạy giả nhỏ, không cần GPU hay CLIP."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("print_region_mask", ROOT / "scripts" / "eval" / "print_region_mask.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

W, H = 200, 300
GARMENT_BOX = (40, 20, 160, 280)    # x0, y0, x1, y1 của vùng áo giả


def _ranked(*names: str) -> list[dict]:
    return [{"layout": n, "label": n, "score": 1.0 - i / 10, "scale": 1.0, "image": None} for i, n in enumerate(names)]


def test_choose_layout_takes_top_unused():
    ranked = _ranked("a", "b", "c")
    chosen, how = M.choose_layout(ranked, used={"a"})
    assert chosen["layout"] == "b" and how == "clip_auto"


def test_choose_layout_falls_back_to_top_when_all_used():
    chosen, _ = M.choose_layout(_ranked("a", "b"), used={"a", "b"})
    assert chosen["layout"] == "a"


def test_choose_layout_fixed_ignores_rank_and_used():
    chosen, how = M.choose_layout(_ranked("a", "b", "c"), used={"c"}, fixed="c")
    assert chosen["layout"] == "c" and how == "fixed"


def test_outside_ratio_counts_only_changed_pixels_outside_mask():
    tpl = Image.new("RGB", (10, 10), (255, 255, 255))
    raw = tpl.copy()
    raw.putpixel((1, 1), (0, 0, 0))     # đổi trong vùng in
    raw.putpixel((8, 8), (0, 0, 0))     # đổi ngoài vùng in
    raw.putpixel((2, 2), (254, 255, 255))  # chênh 1 mức, dưới ngưỡng nên không tính là đổi
    mask = np.zeros((10, 10), np.float32)
    mask[:5, :5] = 1.0
    assert M.outside_ratio(raw, tpl, mask) == pytest.approx(0.5)
    assert M.outside_ratio(tpl, tpl, mask) == 0.0      # không pixel nào đổi


@pytest.fixture()
def fake_run(tmp_path):
    """Lần chạy giả: áo xám có vùng áo hình chữ nhật, một thiết kế chọn bố cục front_panel."""
    run = tmp_path / "R_fake-HV00"
    run.mkdir()
    tpl = Image.new("RGB", (W, H), (120, 120, 120))
    tpl.paste((250, 250, 250), GARMENT_BOX)
    tpl.save(run / "garment.png")
    region = np.zeros((H, W), np.uint8)
    region[GARMENT_BOX[1]:GARMENT_BOX[3], GARMENT_BOX[0]:GARMENT_BOX[2]] = 255
    Image.fromarray(region).save(run / "garment_mask.png")
    Image.new("RGB", (64, 64), (0, 0, 200)).save(run / "V1_pattern.png")
    raw = tpl.copy()
    raw.paste((0, 0, 200), (90, 100, 110, 200))       # hoa văn giả nằm giữa thân trước, trong vùng in
    raw.save(run / "V1_aodai_raw.png")
    manifest = {"designs": [{"status": "completed", "variant_index": 1, "layout": "front_panel",
                             "layout_selected_by": "clip_auto"}]}
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return run


def test_simulate_mask_matches_run(fake_run, monkeypatch):
    monkeypatch.setattr(M.layout_select, "rank", lambda *a, **k: _ranked("front_panel", "shoulder"))
    (row,) = M.simulate(fake_run)
    mask = row["mask"]
    assert row["layout"] == "front_panel" and row["match"]
    # Áo giả nhỏ nên lớp nhòe mép (14 px) làm đỉnh mặt nạ dưới 1; chỉ cần có vùng in rõ ràng (trên 0.5)
    assert mask.shape == (H, W) and 0.0 <= mask.min() and mask.max() <= 1.0 and mask.max() > 0.5
    # Vùng in không được tràn ra ngoài vùng áo
    outside_garment = np.ones((H, W), bool)
    outside_garment[GARMENT_BOX[1]:GARMENT_BOX[3], GARMENT_BOX[0]:GARMENT_BOX[2]] = False
    assert mask[outside_garment].max() == 0.0
    assert row["outside"] == 0.0


def test_simulate_flags_layout_mismatch(fake_run, monkeypatch):
    monkeypatch.setattr(M.layout_select, "rank", lambda *a, **k: _ranked("shoulder", "front_panel"))
    (row,) = M.simulate(fake_run)
    assert row["layout"] == "shoulder" and not row["match"] and row["run_layout"] == "front_panel"
