# -*- coding: utf-8 -*-
"""Cấu hình chung cho bộ kiểm thử.

Nguyên tắc: kiểm thử KHÔNG được sửa dữ liệu thật trong repo. Mọi ca ghi
(phiếu thẩm định, chỉnh sửa, QC) chạy trên bản sao Passport trong thư mục tạm.
Không cần PyTorch/GPU; ca nào cần GPU được bỏ qua.
"""
from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(20261118)


@pytest.fixture
def api_client(monkeypatch, tmp_path):
    """TestClient trên bản sao Passport; nhật ký audit ghi vào danh sách thay vì tệp."""
    from fastapi.testclient import TestClient

    import api.main as main
    from api import store

    passports = tmp_path / "passports"
    shutil.copytree(store.PASSPORTS, passports)
    edits = ROOT / "outputs" / "edits" / f"_pytest_{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(store, "PASSPORTS", passports)
    monkeypatch.setattr(store, "EDITS", edits)
    events: list[dict] = []
    monkeypatch.setattr(main, "append_audit_event", lambda _root, ev: events.append(ev) or True)
    monkeypatch.setattr(main, "WRITE_KEY", "")
    client = TestClient(main.app)
    client.audit_events = events
    client.passports_dir = passports
    yield client
    shutil.rmtree(edits, ignore_errors=True)
    try:
        edits.parent.rmdir()            # chỉ xoá khi thư mục outputs/edits rỗng
    except OSError:
        pass


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
