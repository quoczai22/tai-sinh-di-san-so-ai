# -*- coding: utf-8 -*-
"""Danh mục nguồn, độ đầy đủ hồ sơ, cổng quyền, tiêu chí tuyển ảnh."""
from __future__ import annotations

import copy

import pytest

from provenance import registry as R


def _item(status="unverified", item_status="active", **prov):
    it = copy.deepcopy(R.get_item("BT_Hac_XP"))
    it["status"] = item_status
    it["provenance"] = {**it["provenance"], "rights_status": status, **prov}
    return it


def test_registry_has_twelve_items_six_active():
    items = R.all_items()
    assert len(items) == 12  # 6 vật LR3D (chính) + 6 vật cũ (retired)
    assert sorted(i["code"] for i in items if R.item_status(i) == "active") == ["HV07", "HV08", "HV09", "HV10", "HV11", "HV12"]
    retired = [i for i in items if R.item_status(i) == "retired"]
    assert all(i.get("retired_reason") for i in retired), "hiện vật ngừng dùng phải ghi lý do"


def test_completeness_reports_missing_fields_honestly():
    for it in R.all_items():
        c = R.completeness(it)
        assert c["total"] == len(R.REQUIRED_PROVENANCE) == 10
        missing = {m["field"] for m in c["missing"]}
        # Nhóm không biết tác giả ảnh, giấy phép, ngày thu thập chính xác → phải hiện là thiếu
        assert {"license", "collected_on"} <= missing


@pytest.mark.parametrize("status,action,allowed,level", [
    ("unverified", "experiment", True, "warn"),
    ("unverified", "demo_display", True, "warn"),
    ("unverified", "publish_public", False, "block"),
    ("unverified", "commercial_use", False, "block"),
    ("permission_requested", "publish_public", False, "block"),
    ("public_domain", "publish_public", True, "ok"),
    ("public_domain", "commercial_use", True, "ok"),
    ("open_license", "publish_public", True, "ok"),
    ("permission_denied", "experiment", False, "block"),
    ("permission_denied", "demo_display", False, "block"),
])
def test_rights_gate_matrix(status, action, allowed, level):
    g = R.rights_gate(_item(status), action)
    assert (g.allowed, g.level) == (allowed, level)
    assert g.reason


def test_rights_gate_open_license_noncommercial_blocks_commercial():
    assert not R.rights_gate(_item("open_license", license="CC BY-NC 4.0"), "commercial_use").allowed
    assert R.rights_gate(_item("open_license", license="CC BY 4.0"), "commercial_use").allowed


def test_rights_gate_permission_scope():
    granted = _item("permission_granted", permission={"scope": "non-commercial display"})
    assert R.rights_gate(granted, "publish_public").allowed
    assert not R.rights_gate(granted, "commercial_use").allowed


def test_retired_item_only_allowed_for_experiment():
    it = _item("public_domain", item_status="retired")
    assert R.rights_gate(it, "experiment").allowed
    for action in ("demo_display", "publish_public", "commercial_use"):
        assert not R.rights_gate(it, action).allowed


def test_rights_gate_rejects_unknown_action():
    with pytest.raises(ValueError):
        R.rights_gate(_item(), "sell_nft")


@pytest.mark.parametrize("hid,c1", [
    ("BT_Hac_XP", "pass"),
    ("HSBT_XP-300x300", "fail"),
    ("BT010_2", "fail"),
    ("BHV_UU_XP1-600x600", "warn"),
])
def test_selection_c1_resolution_on_real_images(hid, c1):
    res = R.assess_selection(R.get_item(hid))
    assert res["C1_resolution"]["level"] == c1


def test_selection_c2_baseline_is_hv01():
    res = R.assess_selection(R.get_item("BT_Hac_XP"))
    assert res["C2_ornament_density"]["edge_px"] == 20092
    assert res["C2_ornament_density"]["threshold"] == 12055


def test_rights_gate_permission_scope_list_and_case():
    ok = _item("permission_granted", permission={"scope": ["Display", "Commercial_Use"]})
    assert R.rights_gate(ok, "commercial_use").allowed


def test_streamlit_loader_hides_retired_by_default():
    from streamlit_ui.heritage_data import load_heritage_metadata
    assert len(load_heritage_metadata(R.ROOT)) == 6
    assert len(load_heritage_metadata(R.ROOT, include_retired=True)) == 12
