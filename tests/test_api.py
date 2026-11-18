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


def test_heritage_detail_and_media(api_client):
    assert api_client.get("/heritage/BT_Hac_XP").json()["id"] == "BT_Hac_XP"
    assert api_client.get("/heritage/khong-co").status_code == 404
    r = api_client.get("/media/heritage/BT_Hac_XP")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/")


def test_generate_without_gpu_is_explicit(api_client, monkeypatch):
    import api.main as main
    main._rate.clear()
    r = api_client.post("/generate", json={"heritage_id": "BT_Hac_XP"})
    try:
        import torch  # noqa: F401
        pytest.skip("máy có torch — ca này dành cho máy không có GPU")
    except ImportError:
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


def test_legacy_variant_media(api_client):
    assert api_client.get("/media/variant/BT_Hac_XP_V1_aodai.png").status_code == 200
    assert api_client.get("/media/variant/..%2F..%2FREADME.md").status_code == 404


# ----------------------------------------------------------- bảo mật ---

@pytest.mark.parametrize("path", ["../README.md", "outputs/../api/main.py", "/etc/passwd", "config/quality_gate.json",
                                  "outputs/passports/../../.env"])
def test_artifact_path_traversal_blocked(api_client, path):
    assert api_client.get("/media/artifact", params={"path": path}).status_code in (403, 404)


def test_artifact_allowed_root(api_client):
    assert api_client.get("/media/artifact", params={"path": "data/heritage/BT_Hac_XP.png"}).status_code == 200


@pytest.mark.parametrize("url", ["/media/run/R20260906T081936-HV01/..%2Fmanifest.json", "/media/run/khong-hop-le/a.png",
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
    assert api_client.post("/passports/DP-HV04-20260906-V2/qc", json=body).status_code == 401
    ok = api_client.post("/passports/DP-HV04-20260906-V2/qc", json=body, headers={"X-API-Key": "khoa-bi-mat"})
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
    d = api_client.get("/passports/DP-HV03-20260906-V2").json()
    assert d["integrity"]["ok"] and d["timeline"]


def test_qc_rules(api_client):
    assert api_client.post("/passports/DP-HV01-20260906-V1/qc",
                           json={"officer_id": "QC01", "decision": "forward_to_expert"}).status_code == 409
    r = api_client.post("/passports/DP-HV04-20260906-V2/qc", json={"officer_id": "QC01", "decision": "forward_to_expert"})
    assert r.status_code == 200 and r.json()["status"] == "pending_expert_review"


def test_review_requires_gate(api_client):
    # Thiết kế đang chờ QC (WARN) chưa được thẩm định
    assert api_client.post("/passports/DP-HV04-20260906-V2/reviews", json=_review()).status_code == 409
    bad = _review()
    bad["scores"]["made_up"] = 3
    assert api_client.post("/passports/DP-HV03-20260906-V2/reviews", json=bad).status_code == 422


def test_review_rule_conflict_flagged_and_name_consent(api_client):
    r = api_client.post("/passports/DP-HV03-20260906-V2/reviews",
                        json=_review(culture=3, reviewer_name="Nguyễn Văn A", consent_to_store_name=False))
    j = r.json()
    assert r.status_code == 200 and j["rule_conflict"] is True and j["reviewer_name"] is None
    p = api_client.get("/passports/DP-HV03-20260906-V2").json()
    assert p["approval"]["status"] == "approved" and p["integrity"]["ok"]


def test_publish_blocked_until_rights_cleared(api_client):
    assert api_client.post("/passports/DP-HV03-20260906-V4/publish").status_code == 409   # chưa duyệt
    api_client.post("/passports/DP-HV03-20260906-V4/reviews", json=_review())
    r = api_client.post("/passports/DP-HV03-20260906-V4/publish")
    detail = r.json()["detail"]  # DP-HV03 nay thuộc hiện vật retired nên bị chặn vì ngừng sử dụng hoặc quyền chưa rõ
    assert r.status_code == 403 and ("Không xuất bản" in detail or "ngừng sử dụng" in detail)


def test_export_is_labeled(api_client):
    from provenance.labeling import read_label
    r = api_client.get("/passports/DP-HV03-20260906-V2/export")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    meta = read_label(r.content)
    assert meta["passport_id"] == "DP-HV03-20260906-V2" and meta["rights_warning"] == "true"
    assert api_client.audit_events[-1]["event"] == "design_exported"


def _png_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_manual_edit_goes_back_through_g3(api_client, root):
    pid = "DP-HV03-20260906-V2"
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
    assert api_client.post("/passports/DP-HV03-20260906-V2/edits", json=body).status_code == 422


def test_real_passports_untouched(api_client, root):
    """Các ca ghi ở trên chạy trên bản sao; Passport thật không đổi."""
    p = json.loads((root / "outputs" / "passports" / "DP-HV03-20260906-V2.json").read_text(encoding="utf-8"))
    assert p["reviews"] == [] and p["edits"] == []


def test_quality_experiments_catalog(api_client):
    assert len(api_client.get("/quality/legacy").json()) == 24
    ids = {e["id"] for e in api_client.get("/experiments").json()}
    assert {"EXP-A", "EXP-B", "EXP-C"} <= ids
    cat = api_client.get("/provenance/catalog").json()
    assert cat
