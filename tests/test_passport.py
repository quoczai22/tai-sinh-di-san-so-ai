# -*- coding: utf-8 -*-
"""Design Passport: sổ cái băm nối chuỗi, phát hiện sửa trái phép, phiên bản."""
from __future__ import annotations

import copy
import glob
import json
from pathlib import Path

import pytest

from tsds.provenance import passport as P
from tsds.provenance import registry as R
from tsds.provenance.hashing import canonical_json, sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parent.parent


def _fresh() -> dict:
    p = P.new_passport(passport_id="DP-HV07-20261118-V1", design_id="R20261118T000000-HV07.V1",
                       run_id="R20261118T000000-HV07", heritage=R.get_item("LR3D_33"),
                       created_at="2026-11-18T00:00:00+00:00")
    art = {"role": "final_img2img", "path": "x.png", "sha256": "a" * 64}
    P.add_version(p, kind="ai_generated", artifact=art, created_by="pipeline", actor_type="ai", at="2026-11-18T00:00:01+00:00")
    P.set_approval(p, "pending_expert_review", by="quality_gate", actor_type="system", at="2026-11-18T00:00:02+00:00")
    return p


def test_canonical_json_is_order_independent():
    assert canonical_json({"b": 1, "a": [1, 2]}) == canonical_json({"a": [1, 2], "b": 1})
    assert sha256_json({"b": 1, "a": 2}) == sha256_json({"a": 2, "b": 1})
    assert len(sha256_bytes(b"x")) == 64


def test_fresh_passport_verifies():
    r = P.verify(_fresh(), ROOT, check_files=False)
    assert r["ok"], r["problems"]
    assert r["ledger_entries"] == 2


@pytest.mark.parametrize("tamper", ["payload", "reorder", "approval", "version_hash", "drop_review"])
def test_tampering_is_detected(tamper):
    p = _fresh()
    P.record_review(p, {"review_id": "RV1", "reviewer_id": "CG01", "decision": "approve", "scores": {"aesthetic": 4}})
    if tamper == "payload":
        p["ledger"][0]["payload"]["sha256"] = "b" * 64
    elif tamper == "reorder":
        p["ledger"][0], p["ledger"][1] = p["ledger"][1], p["ledger"][0]
    elif tamper == "approval":
        p["approval"]["status"] = "approved"            # tự phê duyệt mà không qua sổ cái
    elif tamper == "version_hash":
        p["versions"][0]["sha256"] = "c" * 64
    elif tamper == "drop_review":
        p["reviews"].clear()
    assert not P.verify(p, ROOT, check_files=False)["ok"]


def test_manual_edit_creates_child_version_and_requires_review():
    p = _fresh()
    edit = P.record_edit(p, editor_id="TK01", editor_role="designer", description="Làm đậm viền tà áo",
                         tool="Photoshop", artifact={"role": "human_edit", "path": "y.png", "sha256": "d" * 64})
    assert edit["before_sha256"] == "a" * 64 and edit["after_sha256"] == "d" * 64
    v2 = p["versions"][-1]
    assert (v2["version"], v2["parent_version"], v2["parent_sha256"], v2["actor_type"]) == (2, 1, "a" * 64, "human")
    assert p["approval"]["status"] == "pending_expert_review"
    assert p["ai_disclosure"]["human_steps"]
    assert P.verify(p, ROOT, check_files=False)["ok"]


def test_invalid_states_and_actors_rejected():
    p = _fresh()
    with pytest.raises(ValueError):
        P.set_approval(p, "auto_approved", by="x")
    with pytest.raises(ValueError):
        P.append_event(p, "x", "y", "robot")


def test_all_stored_passports_verify_with_files():
    files = sorted(glob.glob(str(ROOT / "outputs" / "passports" / "DP-*.json")))
    assert len(files) >= 24
    for f in files:
        r = P.verify(json.loads(Path(f).read_text(encoding="utf-8")), ROOT)
        assert r["ok"], (f, r["problems"])
        assert r["files_checked"] >= 5


def test_no_stored_passport_is_auto_approved():
    for f in glob.glob(str(ROOT / "outputs" / "passports" / "DP-*.json")):
        p = json.loads(Path(f).read_text(encoding="utf-8"))
        if p["approval"]["status"] == "approved":
            assert any(r["decision"] == "approve" for r in p["reviews"]), f


def test_passport_id_format():
    assert P.passport_id_for("HV09", "20261120", 2) == "DP-HV09-20261120-V2"


def test_label_roundtrip(tmp_path):
    from PIL import Image

    from tsds.provenance.labeling import label_image, read_label
    data, _ = label_image(Image.new("RGB", (320, 480), "white"), passport_id="DP-HV07-20261118-V1",
                          design_sha256="e" * 64, heritage_name="Bình", attribution="Ảnh: X", rights_warning=True)
    meta = read_label(data)
    assert meta["passport_id"] == "DP-HV07-20261118-V1"
    assert meta["design_sha256"] == "e" * 64
    assert meta["rights_warning"] == "true"
    with Image.open(__import__("io").BytesIO(data)) as im:
        assert im.size[1] > 480, "phải có dải nhãn nhìn thấy được"
