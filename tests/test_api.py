# -*- coding: utf-8 -*-
"""API: hồi quy endpoint cũ, quy tắc trạng thái, khoá ghi, chống duyệt đường dẫn."""
from __future__ import annotations

import base64
import io
import json

import pytest
from PIL import Image, ImageFilter

OLD_HERITAGE_KEYS = {"id", "name", "dynasty", "description", "conditioningMode", "image", "colors",
                     "colorNames", "licenseNote", "variantImageBase"}



# ---- Passport dùng trong test: lấy từ dữ liệu thật (bản sao trong thư mục tạm), không viết cứng mã ----

def _ids(api_client) -> list[str]:
    ids = sorted(p["passport_id"] for p in api_client.get("/passports").json())
    assert len(ids) >= 3, "cần ít nhất 3 Passport thật (chạy scripts/14_generate_demo_set.py)"
    return ids


def _theo_trang_thai(api_client, status: str) -> str | None:
    for p in sorted(api_client.get("/passports").json(), key=lambda x: x["passport_id"]):
        if p["approval"]["status"] == status:
            return p["passport_id"]
    return None


def _ep_trang_thai(api_client, status: str) -> str:
    """Passport ở đúng trạng thái `status`: lấy cái có sẵn trong dữ liệu thật, không có thì ép trên bản sao."""
    from api import store
    from provenance import passport as P
    pid = _theo_trang_thai(api_client, status)
    if pid is None:
        pid = _ids(api_client)[0]
        store.mutate_passport(pid, lambda p: P.set_approval(p, status, by="quality_gate", actor_type="system",
                                                            reason="Kiểm thử"))
    return pid


def _warn_id(api_client) -> str:
    """Một thiết kế đang ở trạng thái cảnh báo QC (chưa được chuyển chuyên gia)."""
    return _ep_trang_thai(api_client, "qa_warning")


def _expert_id(api_client) -> str:
    """Một thiết kế đang chờ chuyên gia thẩm định (đạt cổng, hoặc đã được QC Officer chuyển)."""
    pid = _theo_trang_thai(api_client, "pending_expert_review")
    if pid is None:
        pid = _warn_id(api_client)
        r = api_client.post(f"/passports/{pid}/qc", json={"officer_id": "QC01", "decision": "forward_to_expert"})
        assert r.status_code == 200 and r.json()["status"] == "pending_expert_review", r.text
    return pid


def _failed_id(api_client) -> str:
    """Một thiết kế không qua cổng chất lượng."""
    return _ep_trang_thai(api_client, "qa_failed")


# ---------------------------------------------------- hồi quy bản 09/2026 ---

def test_health_keeps_old_fields(api_client):
    j = api_client.get("/health").json()
    assert {"status", "cuda", "device"} <= set(j)
    assert j["status"] == "ok"


def test_heritage_list_keeps_old_shape(api_client):
    items = api_client.get("/heritage").json()
    assert isinstance(items, list) and len(items) == 6
    for it in items:
        assert OLD_HERITAGE_KEYS <= set(it), OLD_HERITAGE_KEYS - set(it)
        assert it["image"] == f"/media/heritage/{it['id']}"
    assert len(api_client.get("/heritage", params={"include_retired": True}).json()) == 12


def test_heritage_info_for_viewers(api_client):
    """Sổ hoa văn ở Studio: mọi hiện vật đang dùng có info; ý nghĩa hoa văn luôn kèm nguồn đã tra được."""
    for it in api_client.get("/heritage").json():
        info = it["info"]
        assert info and info["summary"] and info["motifText"] and info["origin"].startswith("Chưa xác định"), it["id"]
        keys = {s["key"] for s in info["sources"]}
        assert all(s["url"].startswith("https://") for s in info["sources"])
        for m in info["motifs"]:
            assert (m["meaning"] is None) == (m["source"] is None), (it["id"], m["name"])
            assert m["source"] is None or m["source"] in keys, (it["id"], m["name"])
        if info["comparison"]:
            assert info["comparison"]["url"].startswith("https://") and info["comparison"]["holder"]


def test_heritage_detail_and_media(api_client):
    assert api_client.get("/heritage/BT_Hac_XP").json()["id"] == "BT_Hac_XP"
    assert api_client.get("/heritage/khong-co").status_code == 404
    r = api_client.get("/media/heritage/BT_Hac_XP")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/")


def test_generate_without_gpu_is_explicit(api_client, monkeypatch):
    import json
    from pathlib import Path

    import api.main as main
    try:
        import torch  # noqa: F401
        # Phải bỏ qua TRƯỚC khi gửi /generate: máy có torch sẽ bắt đầu một lượt sinh ảnh thật ở nền
        pytest.skip("máy có torch — ca này dành cho máy không có GPU")
    except ImportError:
        pass
    main._rate.clear()
    items = json.loads((Path(__file__).resolve().parent.parent / "data" / "heritage" / "metadata.json").read_text(encoding="utf-8"))["items"]
    active = next(k for k, v in items.items() if v.get("status") == "active")
    r = api_client.post("/generate", json={"heritage_id": active})
    assert r.status_code == 503 and "PyTorch" in r.json()["detail"]
    assert api_client.post("/generate", json={"heritage_id": "HSBT_XP-300x300"}).status_code == 404
    assert api_client.post("/generate", json={"heritage_id": "khong-co"}).status_code == 404
    assert api_client.get("/generate/khong-co").status_code == 404


def test_generate_rate_limited(api_client, monkeypatch):
    import api.main as main
    main._rate.clear()
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 2)
    codes = [api_client.post("/generate", json={"heritage_id": "khong-co"}).status_code for _ in range(3)]
    assert codes[-1] == 429
    main._rate.clear()


# ----------------------------------------------------------- bảo mật ---

@pytest.mark.parametrize("path", ["../README.md", "outputs/../api/main.py", "/etc/passwd", "config/quality_gate.json",
                                  "outputs/passports/../../.env"])
def test_artifact_path_traversal_blocked(api_client, path):
    assert api_client.get("/media/artifact", params={"path": path}).status_code in (403, 404)


def test_artifact_allowed_root(api_client):
    assert api_client.get("/media/artifact", params={"path": "data/heritage/BT_Hac_XP.png"}).status_code == 200


@pytest.mark.parametrize("url", ["/media/run/R20000101T000000-HV01/..%2Fmanifest.json", "/media/run/khong-hop-le/a.png",
                                 "/passports/..%2Fsecret", "/runs/R1"])
def test_bad_ids_rejected(api_client, url):
    assert api_client.get(url).status_code in (404, 422)


def test_audit_whitelist(api_client):
    assert api_client.post("/audit", json={"step": 3, "event": "rm -rf"}).status_code == 422
    assert api_client.post("/audit", json={"step": 9, "event": "design_viewed"}).status_code == 422
    r = api_client.post("/audit", json={"step": 4, "event": "design_viewed", "heritage_id": "BT_Hac_XP"})
    assert r.status_code == 202 and api_client.audit_events[-1]["event"] == "design_viewed"


def test_write_key_enforced(api_client, monkeypatch):
    import api.main as main
    monkeypatch.setattr(main, "WRITE_KEY", "khoa-bi-mat")
    body = {"officer_id": "QC01", "decision": "forward_to_expert"}
    pid = _warn_id(api_client)
    assert api_client.post(f"/passports/{pid}/qc", json=body).status_code == 401
    ok = api_client.post(f"/passports/{pid}/qc", json=body, headers={"X-API-Key": "khoa-bi-mat"})
    assert ok.status_code == 200


# --------------------------------------------- quy trình phê duyệt ---

def _review(decision="approve", culture=5, **kw):
    scores = {"motif_recognizability": 4, "cultural_appropriateness": culture, "aesthetic": 4,
              "garment_integrity": 4, "looks_like_printed_fabric": 4}
    return {"reviewer_id": "CG01", "reviewer_role": "heritage_expert", "scores": scores, "decision": decision,
            "comment": "Kiểm thử", **kw}


def test_passport_list_and_detail(api_client):
    lst = api_client.get("/passports").json()
    assert len(lst) >= 24
    d = api_client.get(f"/passports/{_ids(api_client)[0]}").json()
    assert d["integrity"]["ok"] and d["timeline"]


def test_qc_rules(api_client):
    assert api_client.post(f"/passports/{_failed_id(api_client)}/qc",
                           json={"officer_id": "QC01", "decision": "forward_to_expert"}).status_code == 409
    r = api_client.post(f"/passports/{_warn_id(api_client)}/qc", json={"officer_id": "QC01", "decision": "forward_to_expert"})
    assert r.status_code == 200 and r.json()["status"] == "pending_expert_review"


def test_review_requires_gate(api_client):
    # Thiết kế đang chờ QC (WARN) chưa được thẩm định
    assert api_client.post(f"/passports/{_warn_id(api_client)}/reviews", json=_review()).status_code == 409
    bad = _review()
    bad["scores"]["made_up"] = 3
    assert api_client.post(f"/passports/{_expert_id(api_client)}/reviews", json=bad).status_code == 422


def test_review_rule_conflict_flagged_and_name_consent(api_client):
    pid = _expert_id(api_client)
    r = api_client.post(f"/passports/{pid}/reviews",
                        json=_review(culture=3, reviewer_name="Nguyễn Văn A", consent_to_store_name=False))
    j = r.json()
    assert r.status_code == 200 and j["rule_conflict"] is True and j["reviewer_name"] is None
    p = api_client.get(f"/passports/{pid}").json()
    assert p["approval"]["status"] == "approved" and p["integrity"]["ok"]


def test_publish_needs_review_then_allowed_for_open_license(api_client):
    pid = _expert_id(api_client)
    assert api_client.post(f"/passports/{pid}/publish").status_code == 409   # chưa duyệt
    api_client.post(f"/passports/{pid}/reviews", json=_review())
    r = api_client.post(f"/passports/{pid}/publish")
    # 6 vật LR3D dùng CC BY 4.0 (giấy phép mở) nên cổng quyền cho xuất bản sau khi duyệt
    assert r.status_code == 200, r.text


def test_export_is_labeled(api_client):
    from provenance.labeling import read_label
    pid = _ids(api_client)[0]
    r = api_client.get(f"/passports/{pid}/export")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    meta = read_label(r.content)
    assert meta["passport_id"] == pid and meta["rights_warning"] == "false"
    assert api_client.audit_events[-1]["event"] == "design_exported"


def _png_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_manual_edit_goes_back_through_g3(api_client, root):
    pid = _expert_id(api_client)
    api_client.post(f"/passports/{pid}/reviews", json=_review(decision="revise"))
    p = api_client.get(f"/passports/{pid}").json()
    assert p["approval"]["status"] == "revision_requested"
    raw = next(a for a in p["artifacts"] if a["role"] == "composite_raw")
    good = Image.open(root / raw["path"]).convert("RGB")
    body = {"editor_id": "TK01", "editor_role": "designer", "tool": "Photoshop 2025",
            "description": "Làm rõ nét viền họa tiết ở thân trước", "image_png_base64": _png_b64(good)}
    r = api_client.post(f"/passports/{pid}/edits", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["quality_decision"] == "PASS" and r.json()["approval_status"] == "pending_expert_review"
    p = api_client.get(f"/passports/{pid}").json()
    assert p["versions"][-1]["kind"] == "human_edit" and p["versions"][-1]["parent_version"] == p["versions"][-2]["version"]
    assert p["quality"]["evaluated_version"] == p["versions"][-1]["version"]
    assert p["integrity"]["ok"], p["integrity"]["problems"]
    # Bản sửa làm nhoè họa tiết thì không được chuyển thẳng chuyên gia
    body["image_png_base64"] = _png_b64(good.filter(ImageFilter.GaussianBlur(6)))
    r = api_client.post(f"/passports/{pid}/edits", json=body)
    assert r.json()["quality_decision"] == "FAIL" and r.json()["approval_status"] == "qa_failed"


def test_edit_rejects_non_images(api_client):
    body = {"editor_id": "TK01", "editor_role": "designer", "tool": "x" * 3, "description": "Thử tệp lỗi",
            "image_png_base64": base64.b64encode(b"not an image" * 20).decode()}
    assert api_client.post(f"/passports/{_ids(api_client)[0]}/edits", json=body).status_code == 422


def test_real_passports_untouched(api_client, root):
    """Các ca ghi ở trên chạy trên bản sao; Passport thật không đổi."""
    for f in sorted((root / "outputs" / "passports").glob("DP-*.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        assert p["reviews"] == [] and p["edits"] == [], f.name


def test_quality_experiments_catalog(api_client):
    assert len(api_client.get("/quality/designs").json()) >= 24
    ids = {e["id"] for e in api_client.get("/experiments").json()}
    assert {"EXP-A", "EXP-B", "EXP-C"} <= ids
    cat = api_client.get("/provenance/catalog").json()
    assert cat
