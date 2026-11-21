"""Kiểm thử phần đọc dữ liệu và tham số của scripts/train/train_lora.py (không cần GPU)."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("tl", Path(__file__).resolve().parents[1] / "scripts" / "train" / "train_lora.py")
tl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tl)


def tao(tmp_path, dong):
    (tmp_path / "metadata.jsonl").write_text("\n".join(json.dumps(d, ensure_ascii=False) for d in dong), encoding="utf-8")
    return tmp_path


def test_doc_metadata_hop_le(tmp_path):
    (tmp_path / "a.png").write_bytes(b"x")
    d = tao(tmp_path, [{"file_name": "a.png", "text": "A photo of áo dài"}])
    assert tl.read_metadata(d) == [{"file_name": "a.png", "text": "A photo of áo dài"}]


def test_thieu_metadata_bao_loi_huong_dan(tmp_path):
    with pytest.raises(FileNotFoundError, match="export_lora_set"):
        tl.read_metadata(tmp_path)


def test_caption_rong_va_thieu_anh(tmp_path):
    (tmp_path / "a.png").write_bytes(b"x")
    with pytest.raises(ValueError, match="caption rỗng"):
        tl.read_metadata(tao(tmp_path, [{"file_name": "a.png", "text": "  "}]))
    with pytest.raises(FileNotFoundError, match="b.png"):
        tl.read_metadata(tao(tmp_path, [{"file_name": "b.png", "text": "x"}]))


def test_file_rong_bao_loi(tmp_path):
    with pytest.raises(ValueError, match="không có dòng nào"):
        tl.read_metadata(tao(tmp_path, []))


def test_tham_so_mac_dinh():
    a = tl.parse_args([])
    assert (a.steps, a.grad_accum, a.rank, a.lr, a.seed) == (800, 4, 32, 1e-4, 42)
    assert (a.width, a.height) == (768, 1032)
    b = tl.parse_args(["--steps", "5", "--rank", "4", "--width", "384"])
    assert (b.steps, b.rank, b.width) == (5, 4, 384)


def test_do_phan_giai_chia_het_cho_8():
    assert tl.WIDTH % 8 == 0 and tl.HEIGHT % 8 == 0


def test_do_phan_giai_khong_chia_het_cho_8_bi_tu_choi():
    with pytest.raises(ValueError, match="chia hết cho 8"):
        tl.main(["--width", "500", "--height", "688"])
