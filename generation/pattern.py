# -*- coding: utf-8 -*-
"""GIAI ĐOẠN 1 — sinh hoa văn phẳng từ ảnh gốm (v6).

Đây là nơi Creative Intensity thực sự có ý nghĩa: nó điều tiết mức độ biến tấu
của HOA VĂN, không phải chọn giữa "ra cái bình" hay "ra cái áo".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

from . import controlnet as cn
from .prompt_template import NEG_PATTERN, assemble_pattern, assert_fits

for _s in (sys.stdout, sys.stderr):
    if getattr(_s, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parent.parent
TERMS_FILE = ROOT / "data" / "prompt_terms.json"

# v6 mục 5.3 — 4 mức Creative Intensity
INTENSITY = {
    1: {"name": "Nguyên bản",      "weight": 0.85, "modifier": ""},
    2: {"name": "Gần nguyên bản",  "weight": 0.65, "modifier": ""},
    3: {"name": "Cân bằng",        "weight": 0.45, "modifier": "modern simplified interpretation"},
    4: {"name": "Tự do sáng tạo",  "weight": 0.25, "modifier": "bold contemporary reinterpretation"},
}

_raw = json.loads(TERMS_FILE.read_text(encoding="utf-8"))
TERMS: dict = _raw["terms"]


def build_prompt(heritage_id: str, level: int, user_direction: str = "") -> dict:
    """Ghép prompt giai đoạn 1 và kiểm ngân sách token trước khi nạp model."""
    if level not in INTENSITY:
        raise ValueError(f"Creative Intensity phải là 1-4, nhận {level!r}")
    t = TERMS[heritage_id]
    bits = [x for x in (INTENSITY[level]["modifier"], user_direction) if x]
    positive = assemble_pattern(t["name_en"], t["base_description"], ", ".join(bits))
    assert_fits(positive, f"{heritage_id}/L{level}")
    return {"positive_prompt": positive, "negative_prompt": NEG_PATTERN,
            "weight": INTENSITY[level]["weight"], "level": level,
            "level_name": INTENSITY[level]["name"], "heritage_id": heritage_id,
            "user_direction": user_direction}


def generate(gen, heritage_id: str, level: int, seed: int,
             user_direction: str = "", prepared: dict | None = None) -> dict:
    """Sinh một ảnh hoa văn. `gen` là generation.stable_diffusion.Generator."""
    p = prepared or cn.prepare(heritage_id)
    spec = build_prompt(heritage_id, level, user_direction)
    # Hoa van PHAI lat lien mach: no se duoc lat kin vung in o giai doan 2.
    # Khong bat thi mep trai/phai khong khop va lo duong noi cat ngang hoa tiet.
    if not getattr(gen, "seamless", False):
        gen.set_seamless(True)
    img, secs, peak = gen.generate(spec["positive_prompt"], spec["negative_prompt"],
                                   p["control"], spec["weight"], seed)
    return {**spec, "image": img, "reference": p["reference"],
            "control_mode": p["mode"], "edge_density": p["edge_density"],
            "seed": seed, "duration_s": secs, "peak_vram_gb": peak}


def save(result: dict, out_dir: Path, tag: str | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    name = tag or f"{result['heritage_id']}_L{result['level']}_seed{result['seed']}"
    path = out_dir / f"{name}.png"
    result["image"].save(path)
    return path
