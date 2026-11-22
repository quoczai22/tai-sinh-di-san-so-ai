# -*- coding: utf-8 -*-
"""Danh mục nguồn, độ đầy đủ hồ sơ, cổng quyền, tiêu chí tuyển ảnh."""
from __future__ import annotations

import copy

import pytest

from tsds.provenance import registry as R

# Giá trị mặc định của ràng buộc LoRA phi thương mại, lấy trước khi fixture tắt nó
_MAC_DINH_RANG_BUOC = R.SYSTEM_NONCOMMERCIAL_REASON


def _item(status="unverified", item_status="active", **prov):
    it = copy.deepcopy(R.get_item("LR3D_33"))
    it["status"] = item_status
    it["provenance"] = {**it["provenance"], "rights_status": status, **prov}
    return it


def test_registry_has_six_active_items():
    items = R.all_items()
    assert len(items) == 6  # 6 vật của bộ LR3D-CULT2
    assert sorted(i["code"] for i in items) == ["HV07", "HV08", "HV09", "HV10", "HV11", "HV12"]
    assert all(R.item_status(i) == "active" for i in items)


def test_completeness_reports_missing_fields_honestly():
    for it in R.all_items():
        c = R.completeness(it)
        assert c["total"] == len(R.REQUIRED_PROVENANCE) == 10
        missing = {m["field"] for m in c["missing"]}
        # Chưa có nhật ký ngày thu thập → phải hiện là thiếu
        assert "collected_on" in missing
        # Giấy phép chỉ được coi là thiếu khi quyền còn chưa xác minh
        if it["provenance"].get("rights_status") == "unverified":
            assert "license" in missing
        else:
            assert "license" not in missing


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


@pytest.fixture(autouse=True)
def _bo_rang_buoc_he_thong(monkeypatch):
    """Các test giấy phép từng hiện vật chạy khi chưa có ràng buộc LoRA phi thương mại.
    Ràng buộc cấp hệ thống được test riêng ở test_system_noncommercial_*."""
    monkeypatch.setattr(R, "SYSTEM_NONCOMMERCIAL_REASON", None)


def test_system_noncommercial_blocks_commercial_for_every_status(monkeypatch):
    # LoRA phi thương mại có mặt trong mọi thiết kế → chặn thương mại dù ảnh nguồn cho phép
    monkeypatch.setattr(R, "SYSTEM_NONCOMMERCIAL_REASON", _MAC_DINH_RANG_BUOC)
    for it in (_item("public_domain"), _item("own_work"), _item("open_license", license="CC BY 4.0"),
               _item("permission_granted", permission={"scope": "commercial_use"})):
        g = R.rights_gate(it, "commercial_use")
        assert (g.allowed, g.level) == (False, "block")
        assert "LoRA" in g.reason and "CC BY-NC" in g.reason
    # Các mục đích phi thương mại không bị ảnh hưởng
    assert R.rights_gate(_item("open_license"), "publish_public").allowed
    assert R.rights_gate(_item("open_license"), "demo_display").allowed


def test_system_noncommercial_is_on_by_default():
    assert _MAC_DINH_RANG_BUOC and "CC BY-NC" in _MAC_DINH_RANG_BUOC


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


def _tao_anh_tong_hop(tmp_path, monkeypatch, canh_anh, canh_vat, ten="SYN"):
    """Ảnh PNG có nền trong suốt, vật là hình vuông có hoa văn kẻ sọc ở giữa; chạy tiêu chí tuyển ảnh trên đó."""
    import shutil

    import numpy as np
    from PIL import Image

    from tsds.generation.pattern import controlnet as cn
    rgba = np.zeros((canh_anh, canh_anh, 4), np.uint8)
    o = (canh_anh - canh_vat) // 2
    rgba[o:o + canh_vat, o:o + canh_vat, :3] = 255
    rgba[o:o + canh_vat:12, o:o + canh_vat, :3] = 30           # sọc ngang tạo cạnh cho Canny
    rgba[o:o + canh_vat, o:o + canh_vat, 3] = 255
    Image.fromarray(rgba, "RGBA").save(tmp_path / f"{ten}.png")
    (tmp_path / "config").mkdir(exist_ok=True)
    shutil.copy(R.ROOT / R.SELECTION_CONFIG, tmp_path / R.SELECTION_CONFIG)
    monkeypatch.setattr(cn, "HERITAGE_DIR", tmp_path)
    return {"heritage_id": ten, "image_path": f"{ten}.png", "provenance": {}}


@pytest.mark.parametrize("canh_anh,canh_vat,c1", [
    (1024, 900, "pass"),     # vật dài từ 768 px trở lên
    (1024, 600, "warn"),     # đủ 512 nhưng dưới 768
    (1024, 300, "fail"),     # vật dưới 512 px
    (400, 380, "fail"),      # cạnh ngắn ảnh dưới 512 px
])
def test_selection_c1_resolution_tren_anh_tong_hop(tmp_path, monkeypatch, canh_anh, canh_vat, c1):
    item = _tao_anh_tong_hop(tmp_path, monkeypatch, canh_anh, canh_vat)
    res = R.assess_selection(item, root=tmp_path)
    assert res["C1_resolution"]["level"] == c1


def test_selection_c2_nguong_tinh_tu_moc_trong_cau_hinh(tmp_path, monkeypatch):
    item = _tao_anh_tong_hop(tmp_path, monkeypatch, 1024, 900)
    res = R.assess_selection(item, root=tmp_path)
    cfg = R.load_selection_config(R.ROOT)["criteria"]["C2_ornament_density"]
    assert res["C2_ornament_density"]["threshold"] == round(cfg["baseline_edge_px"] * cfg["ratio"]) == 12055


def test_rights_gate_permission_scope_list_and_case():
    ok = _item("permission_granted", permission={"scope": ["Display", "Commercial_Use"]})
    assert R.rights_gate(ok, "commercial_use").allowed


def test_streamlit_loader_hides_retired_by_default(tmp_path):
    import json
    import shutil

    from tsds.provenance.heritage import load_heritage_metadata
    assert len(load_heritage_metadata(R.ROOT)) == 6
    # đánh dấu một hiện vật là retired trên bản sao: mặc định bị ẩn, include_retired thì hiện
    (tmp_path / "data" / "heritage").mkdir(parents=True)
    for it in R.all_items():                       # loader kiểm tra ảnh có thật: chép ảnh hiện vật sang thư mục tạm
        shutil.copy(R.ROOT / it["image_path"], tmp_path / "data" / "heritage")
    meta = json.loads((R.ROOT / "data" / "heritage" / "metadata.json").read_text(encoding="utf-8"))
    meta["items"]["LR3D_33"]["status"] = "retired"
    (tmp_path / "data" / "heritage" / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    assert len(load_heritage_metadata(tmp_path)) == 5
    assert len(load_heritage_metadata(tmp_path, include_retired=True)) == 6
