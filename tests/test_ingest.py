# -*- coding: utf-8 -*-
"""Tiếp nhận ảnh hiện vật mới: kiểm SHA-1, tách nền, C1–C4, không ghi khi chạy thử."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def ingest_mod(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("ingest", ROOT / "scripts" / "09_ingest_heritage_image.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "PREVIEW", tmp_path / "preview")
    return mod


@pytest.fixture
def fake_photo(tmp_path):
    h, w = 1100, 760
    yy, xx = np.mgrid[0:h, 0:w]
    img = np.dstack([120 + 30 * yy / h, 110 + 20 * xx / w, 100 + 0 * xx]).astype(np.uint8)
    mask = np.zeros((h, w), np.uint8)
    cv2.ellipse(mask, (380, 600), (250, 360), 0, 0, 360, 1, -1)
    pat = (np.sin(xx / 9.0) * np.cos(yy / 13.0)) > 0.1
    img[mask > 0] = (245, 245, 240)
    img[(mask > 0) & pat] = (40, 70, 150)
    path = tmp_path / "photo.jpg"
    Image.fromarray(img).save(path, quality=92)
    sha1 = hashlib.sha1(path.read_bytes()).hexdigest()
    cands = tmp_path / "cands.json"
    cands.write_text(json.dumps({"candidates": [{"id": "T1", "museum": "Bảo tàng thử", "title_en": "Test", "sha1": sha1,
                                                 "license": "CC0", "author": "A", "photo_date": None,
                                                 "page": "https://example.org"}]}), encoding="utf-8")
    return path, cands, mask


def test_dry_run_segments_and_writes_nothing(ingest_mod, fake_photo, capsys):
    path, cands, mask = fake_photo
    meta_before = (ROOT / "data" / "heritage" / "metadata.json").read_bytes()
    rc = ingest_mod.main(["--file", str(path), "--candidate", "T1", "--candidates", str(cands),
                          "--heritage-id", "PYTEST_Fake", "--name", "Thử", "--dating", "thế kỷ 19", "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    report = json.loads(out[: out.rindex("}") + 1])
    assert report["selection"]["C3_rights"]["level"] == "pass"
    assert report["selection"]["C4_heritage_authenticity"]["level"] == "pass"
    # Mặt nạ khớp hình elip thật (tỉ lệ diện tích tiền cảnh)
    assert report["segmentation"]["foreground_pct"] == pytest.approx(mask.mean() * 100, abs=2.5)
    assert (ROOT / "data" / "heritage" / "metadata.json").read_bytes() == meta_before
    assert not (ROOT / "data" / "heritage" / "PYTEST_Fake.png").exists()


def test_sha1_mismatch_aborts(ingest_mod, fake_photo, tmp_path):
    path, cands, _ = fake_photo
    other = tmp_path / "other.jpg"
    other.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(SystemExit) as e:
        ingest_mod.main(["--file", str(other), "--candidate", "T1", "--candidates", str(cands),
                         "--heritage-id", "PYTEST_Fake", "--name", "Thử", "--dry-run"])
    assert "SHA-1" in str(e.value)


def test_activate_requires_review(ingest_mod):
    with pytest.raises(SystemExit) as e:
        ingest_mod.main(["--heritage-id", "khong_co", "--activate"])
    assert "Không có" in str(e.value)
