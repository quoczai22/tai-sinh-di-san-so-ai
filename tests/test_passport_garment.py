"""Kiểm thử việc ghi áo nền (áo do LoRA sinh hoặc áo mẫu cố định) vào Design Passport."""
import shutil
import uuid
from pathlib import Path

import pytest
from PIL import Image

from tsds.provenance import passport as P
from tsds.provenance.builder import build_design_passport
from tsds.provenance.registry import get_item

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def work():
    """Thư mục tạm TRONG repo (file_record cần đường dẫn tương đối so với gốc repo); xóa sau test."""
    d = ROOT / "outputs" / f"_pytest_garment_{uuid.uuid4().hex[:8]}"
    d.mkdir(parents=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


def anh(path, mau):
    Image.new("RGB", (16, 16), mau).save(path)
    return path


def tao_passport(work, garment, builder_extra=None, **rec_extra):
    item = get_item("LR3D_61", ROOT)
    paths = {k: anh(work / f"{k}.png", (i * 30, 0, 0)) for i, k in
             enumerate(("source", "reference", "canny", "pattern", "raw", "final"))}
    rec = {"variant_index": 1, "timestamp": "2026-11-19T00:00:00+00:00", "sd_model_id": "sd15", "controlnet_id": "canny",
           "positive_prompt": "p", "negative_prompt": "n", "seed": 42, "steps": 25, "guidance": 7.5,
           "controlnet_weight": 0.85, "intensity_level": 1, "level_name": "Nguyên bản", "control_mode": "ornament_only",
           "n_edge_px": 100, "palette_mode": "original", "source_palette": "#000000;#ffffff", "layout": "front_panel",
           "layout_label": "Dải thân trước", "layout_scale": 0.95, "layout_score": 0.1, "polish_strength": 0.30,
           "similarity_pattern_vs_ceramic": 0.8, **rec_extra}
    return build_design_passport(item=item, run_id="R20261119T000000-HV08", run_stamp="20261119T000000", rec=rec,
                                 paths=paths, assessment=None, now="2026-11-19T00:00:01+00:00", root=ROOT,
                                 garment=garment, **(builder_extra or {}))


def thong_tin_ao_lora(work):
    anh(work / "garment.png", (200, 200, 200))
    anh(work / "garment_mask.png", (255, 255, 255))
    return {"source": "lora", "seed": 43, "lora": str(ROOT / "data" / "lora" / "aodai_r16_512"),
            "tried": [{"seed": 42, "status": "rejected", "reason": "áo chạm mép"},
                      {"seed": 43, "status": "accepted", "reason": ""}],
            "image": (work / "garment.png").relative_to(ROOT).as_posix(),
            "mask": (work / "garment_mask.png").relative_to(ROOT).as_posix(), "fallback_reason": None}


def test_ao_lora_vao_artifacts_generation_va_buoc_sinh_ao(work):
    pp = tao_passport(work, thong_tin_ao_lora(work))
    roles = {a["role"]: a for a in pp["artifacts"]}
    assert "garment" in roles and "garment_mask" in roles and len(roles["garment"]["sha256"]) == 64
    g = pp["generation"]["garment"]
    assert g["source"] == "lora" and g["seed"] == 43 and len(g["candidates"]) == 2
    assert g["lora"]["path"] == "data/lora/aodai_r16_512"
    assert "CC BY-NC 4.0" in g["lora"]["license"] and "ICMR 2026" in g["lora"]["citation"]
    steps = {s["step"]: s for s in pp["process_steps"]}
    assert steps["generate_garment"]["actor_type"] == "ai"
    assert steps["generate_garment"]["outputs"] == [roles["garment"]["sha256"], roles["garment_mask"]["sha256"]]
    assert "CC BY-NC 4.0" in steps["generate_garment"]["note"]
    assert roles["garment"]["sha256"] in steps["composite"]["inputs"] and "LoRA" in steps["composite"]["label"]
    # Nhãn AI tự có bước sinh áo vì add_step ghi vào ai_steps
    assert any("Sinh áo dài nền bằng LoRA" in s for s in pp["ai_disclosure"]["ai_steps"])


def test_passport_co_ao_lora_van_toan_ven_va_phat_hien_sua_ao(work):
    pp = tao_passport(work, thong_tin_ao_lora(work))
    assert P.verify(pp, ROOT)["ok"]
    anh(work / "garment.png", (1, 2, 3))                       # đổi ảnh áo sau khi lập Passport
    ket_qua = P.verify(pp, ROOT)
    assert not ket_qua["ok"] and any("garment.png" in p for p in ket_qua["problems"])


def test_ao_co_dinh_khong_co_hien_vat_ao_va_ghi_ly_do_quay_ve(work):
    pp = tao_passport(work, {"source": "fixed", "fallback_reason": "GarmentError: Cả 6 ứng viên đều bị loại"})
    assert {a["role"] for a in pp["artifacts"]} == {"source_image", "reference_512", "control_canny", "pattern",
                                                     "composite_raw", "final_img2img"}
    g = pp["generation"]["garment"]
    assert g["source"] == "fixed" and "bị loại" in g["fallback_reason"] and g["template"].endswith("aodai_template.png")
    assert "generate_garment" not in {s["step"] for s in pp["process_steps"]}
    assert "áo mẫu" in {s["step"]: s for s in pp["process_steps"]}["composite"]["label"]


def test_khong_truyen_thong_tin_ao_la_ao_co_dinh_nhu_truoc(work):
    pp = tao_passport(work, None)
    assert pp["generation"]["garment"]["source"] == "fixed"
    assert pp["generation"]["garment"]["fallback_reason"] is None


def test_polish_co_mat_na_duoc_ghi_vao_passport(work):
    pp = tao_passport(work, None, polish_mask=True, polish_status="retried_seed", polish_attempts=3)
    p = pp["generation"]["polish_img2img"]
    assert p["masked"] is True and p["status"] == "retried_seed" and p["attempts"] == 3
    assert "chỉ vùng áo" in {s["step"]: s for s in pp["process_steps"]}["polish"]["label"]
    cu = tao_passport(work, None)
    assert cu["generation"]["polish_img2img"]["masked"] is False and cu["generation"]["polish_img2img"]["attempts"] == 1


def test_khoa_hoa_tiet_duoc_ghi_vao_passport(work):
    pp = tao_passport(work, None, polish_mask=True, polish_lock=True)
    p = pp["generation"]["polish_img2img"]
    assert p["pattern_lock"]["method"] == "pattern_lock_v1" and "dog_sigma_low" in p["pattern_lock"]["params"]
    buoc = {s["step"]: s for s in pp["process_steps"]}["polish"]
    assert "khóa họa tiết" in buoc["label"] and "pattern_lock_v1" in buoc["note"]
    assert "pattern_lock" not in tao_passport(work, None, polish_mask=True)["generation"]["polish_img2img"]


def test_passport_ghi_seed_hoa_van_thuc_dung_va_cac_lan_sinh_lai(work):
    """Hoa văn sinh lại ở seed khác seed gốc: Passport ghi seed thực dùng và các lần thử để tái lập."""
    log = [{"attempt": 1, "seed": 42, "status": "failed", "failed_metrics": ["seam_ratio"], "values": {"seam_ratio": 2.4}},
           {"attempt": 2, "seed": 43, "status": "ok", "failed_metrics": [], "values": {"seam_ratio": 1.1}}]
    pp = tao_passport(work, None, pattern_seed=43, pattern_status="retried_seed", pattern_attempt_log=log)
    g = pp["generation"]
    assert g["seed"] == 42 and g["pattern_seed"] == 43            # seed gốc (dùng cho polish) khác seed hoa văn thực dùng
    assert g["pattern_retry"]["status"] == "retried_seed" and g["pattern_retry"]["attempts"] == log
    assert any("seed 43" in s["label"] for s in pp["process_steps"] if s["step"] == "generate_pattern")


def test_passport_khong_sinh_lai_pattern_seed_bang_seed_goc(work):
    pp = tao_passport(work, None)
    assert pp["generation"]["pattern_seed"] == 42 and pp["generation"]["pattern_retry"] == {"status": "single_pass", "attempts": []}
