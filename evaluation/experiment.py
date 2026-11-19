# -*- coding: utf-8 -*-
"""Experiment Management — đối chứng có kiểm soát, nhiều seed, đánh giá mù.

Nguyên tắc cưỡng chế bằng mã (không chỉ ghi trong tài liệu):
  1. MỘT biến độc lập mỗi thí nghiệm. `validate_plan` từ chối kế hoạch nếu trong
     cùng một đơn vị (hiện vật) có tham số nào ngoài biến độc lập và biến lặp
     (seed) thay đổi.
  2. Lặp nhiều seed để đo DAO ĐỘNG, không kết luận từ một seed.
  3. Đánh giá mù: người chấm nhận ảnh đã đổi tên ngẫu nhiên; khoá giải mã nằm ở
     tệp riêng, chỉ mở sau khi thu đủ phiếu.

Lệnh:
    python -m evaluation.experiment plan  evaluation/experiments/EXP-A_controlnet_weight.json
    python -m evaluation.experiment run   evaluation/experiments/EXP-C_composite_ablation.json   # CPU
    python -m evaluation.experiment run   ...EXP-A...  # cần GPU
    python -m evaluation.experiment blind outputs/experiments/EXP-C --raters CG01,CG02,CG03
    python -m evaluation.experiment analyze outputs/experiments/EXP-C
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import shutil
import sys
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "outputs" / "experiments"

BASE_CONFIG = {
    "controlnet_weight": 0.65, "seed": 42, "prompt_modifier": "", "palette_mode": "free",
    "layout": "front_panel", "polish_strength": 0.40, "polish_seed": "same_as_seed",
    "steps": 25, "guidance": 7.5, "composite_mode": "full", "stage2_finish": "img2img_0.40",
    "garment_source": "fixed",   # "fixed" là áo mẫu cố định, "lora" là áo do LoRA sinh (EXP-D)
    "source": "render",          # ảnh nạp cho ControlNet: "render" (cả bình), "panel" (mảng phẳng), "elements" (EXP-E)
}


class PlanError(ValueError):
    pass


def load_spec(path: Path | str) -> dict:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("id", "independent_variable", "fixed", "units"):
        if key not in spec:
            raise PlanError(f"Thiếu trường '{key}' trong đặc tả thí nghiệm")
    iv = spec["independent_variable"]["name"]
    if iv in spec["fixed"]:
        raise PlanError(f"Biến độc lập '{iv}' không được đồng thời nằm trong 'fixed'")
    rep = (spec.get("replicates") or {}).get("name")
    if rep and rep in spec["fixed"]:
        raise PlanError(f"Biến lặp '{rep}' không được nằm trong 'fixed'")
    if len(spec["independent_variable"]["levels"]) < 2:
        raise PlanError("Biến độc lập cần ít nhất 2 mức")
    return spec


def resolve_units(spec: dict, root: Path = ROOT) -> list[str]:
    from provenance.registry import all_items                     # noqa: PLC0415
    mode = spec["units"]["heritage"]
    items = all_items(root)
    if mode == "active":
        return [it["heritage_id"] for it in items if it.get("status", "active") == "active"]
    if mode == "legacy_all":
        logged = {r["heritage_id"] for r in csv.DictReader((root / "evaluation" / "variants.csv").open(encoding="utf-8"))}
        return [it["heritage_id"] for it in items if it["heritage_id"] in logged]
    if isinstance(mode, list):
        return mode
    raise PlanError(f"units.heritage không hợp lệ: {mode}")


def expand_plan(spec: dict, root: Path = ROOT) -> list[dict]:
    iv = spec["independent_variable"]
    rep = spec.get("replicates") or {"name": None, "levels": [None]}
    rows = []
    for unit, level, replicate in product(resolve_units(spec, root), iv["levels"], rep["levels"]):
        cfg = {**BASE_CONFIG, **spec["fixed"], iv["name"]: level}
        if rep["name"]:
            cfg[rep["name"]] = replicate
        run_key = f"{spec['id']}|{unit}|{iv['name']}={level}" + (f"|{rep['name']}={replicate}" if rep["name"] else "")
        rows.append({"experiment_id": spec["id"], "run_key": run_key, "heritage_id": unit,
                     "iv_name": iv["name"], "iv_level": level, "replicate_name": rep["name"],
                     "replicate": replicate, "status": "planned", **{f"cfg.{k}": v for k, v in sorted(cfg.items())}})
    validate_plan(spec, rows)
    return rows


def validate_plan(spec: dict, rows: list[dict]) -> None:
    """Chặn thí nghiệm đổi nhiều biến cùng lúc."""
    iv = spec["independent_variable"]["name"]
    rep = (spec.get("replicates") or {}).get("name")
    allowed = {f"cfg.{iv}"} | ({f"cfg.{rep}"} if rep else set())
    if spec["fixed"].get("polish_seed") == "same_as_seed" and rep == "seed":
        allowed.add("cfg.polish_seed")
    by_unit: dict[str, list[dict]] = {}
    for r in rows:
        by_unit.setdefault(r["heritage_id"], []).append(r)
    for unit, group in by_unit.items():
        keys = [k for k in group[0] if k.startswith("cfg.")]
        varying = {k for k in keys if len({json.dumps(g[k]) for g in group}) > 1}
        extra = varying - allowed
        if extra:
            raise PlanError(f"[{unit}] có tham số thay đổi ngoài biến độc lập: {sorted(extra)}")
        if f"cfg.{iv}" not in varying:
            raise PlanError(f"[{unit}] biến độc lập '{iv}' không thay đổi")


def write_plan(spec: dict, rows: list[dict], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "plan.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (out_dir / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------- thực thi ----

def _legacy_pattern(heritage_id: str, variant: int = 2) -> Path:
    return ROOT / "outputs" / "variants" / f"{heritage_id}_V{variant}_pattern.png"


def run_cpu_composite(spec: dict, rows: list[dict], out_dir: Path) -> list[dict]:
    """EXP-C: chạy được trên CPU vì giai đoạn 2 ghép ảnh là tất định."""
    from PIL import Image                                          # noqa: PLC0415
    from generation import garment                                 # noqa: PLC0415
    from provenance.hashing import sha256_file                     # noqa: PLC0415
    from quality.metrics import pattern_preservation, to_rgb_array  # noqa: PLC0415
    import numpy as np                                             # noqa: PLC0415

    flags = {"full": {}, "no_displacement": {"displace": 0.0}, "no_shading": {"shading": False},
             "no_grade": {"grade": False}}
    tpl = Image.open(garment.TEMPLATE).convert("RGB")
    template = np.asarray(tpl)
    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    full_cache: dict[str, np.ndarray] = {}
    results = []
    for r in rows:
        pat = Image.open(_legacy_pattern(r["heritage_id"])).convert("RGB")
        layout = r["cfg.layout"]
        img = garment.apply(pat, layout=layout, **flags[r["iv_level"]])
        name = f"{r['heritage_id']}__{r['iv_level']}.png"
        img.save(img_dir / name)
        arr = to_rgb_array(img)
        if r["iv_level"] == "full":
            full_cache[r["heritage_id"]] = arr
        results.append({**r, "status": "completed", "image": f"images/{name}",
                        "sha256": sha256_file(img_dir / name),
                        "pattern_sha256": sha256_file(_legacy_pattern(r["heritage_id"]))})
    mask_cache = garment._layout_mask(tpl, garment.get_layout(rows[0]["cfg.layout"]))
    for res in results:
        ref = full_cache[res["heritage_id"]]
        cur = np.asarray(Image.open(out_dir / res["image"]).convert("RGB"))
        m = pattern_preservation(ref, cur, template, mask_cache)
        res["pattern_preservation_vs_full"] = m["pattern_preservation"]
    return results


def parse_finish(finish: str) -> tuple[str, float, bool]:
    """Đọc giá trị của biến `stage2_finish` thành (kiểu, độ nhiễu, có khóa họa tiết).

    Các giá trị hợp lệ:
      "none"                     bản ghép tất định, không polish (đối chứng)
      "img2img_0.40"             polish toàn ảnh (cách cũ)
      "img2img_0.40+pattern_lock"  polish toàn ảnh rồi khóa họa tiết
      "masked_0.30"              polish chỉ vùng áo, ngoài áo giữ nguyên từng pixel
      "masked_0.30+pattern_lock" polish vùng áo rồi khóa họa tiết
    """
    if finish == "none":
        return "none", 0.0, False
    body, _, lock = finish.partition("+")
    kind, _, num = body.partition("_")
    if kind not in ("img2img", "masked") or lock not in ("", "pattern_lock"):
        raise ValueError(f"stage2_finish không hợp lệ: {finish!r}")
    try:
        strength = float(num)
    except ValueError:
        raise ValueError(f"stage2_finish thiếu độ nhiễu: {finish!r}") from None
    if not 0.0 < strength <= 1.0:
        raise ValueError(f"Độ nhiễu ngoài khoảng (0, 1]: {finish!r}")
    return kind, strength, lock == "pattern_lock"


def lora_garment_seeds(rows: list[dict]) -> list[int]:
    """Các seed cần sinh áo LoRA: seed của những lượt có garment_source = lora, không trùng, đã sắp xếp."""
    return sorted({int(r["cfg.seed"]) for r in rows if r.get("cfg.garment_source") == "lora"})


def pregenerate_garments(seeds: list[int], out_dir: Path, generate=None) -> dict[int, dict]:
    """Sinh sẵn một áo LoRA cho mỗi seed, lưu ở out_dir/garments/seed_<seed>/.

    Chạy TRƯỚC khi nạp bộ sinh hoa văn để hai mô hình không chiếm VRAM cùng lúc, và để 6 hiện vật cùng seed
    dùng chung một áo. Trả về {seed: {"ok": True, "info": ...}} hoặc {"ok": False, "error": ...} khi
    không có áo hợp lệ. Cố ý KHÔNG quay về áo mẫu: quay về sẽ làm hai mức của thí nghiệm lẫn vào nhau.

    generate: hàm (out_dir, seed) -> dict của garment_lora.generate_garment; mặc định gọi hàm thật (để test thay bằng giả).
    """
    if generate is None:
        from generation import garment_lora                          # noqa: PLC0415
        generate = lambda d, s: garment_lora.generate_garment(d, seed=s)  # noqa: E731
    from generation.garment_lora import GarmentError                 # noqa: PLC0415
    out: dict[int, dict] = {}
    for s in seeds:
        try:
            out[s] = {"ok": True, "info": generate(out_dir / "garments" / f"seed_{s}", s)}
        except GarmentError as exc:
            out[s] = {"ok": False, "error": str(exc)}
    return out


def source_prepared(cache: dict, heritage_id: str, source: str) -> dict:
    """Ảnh điều kiện cho ControlNet của một hiện vật theo nguồn (render, panel, elements), có nhớ lại để khỏi tính lại.

    elements: lấy phần tử đầu tiên trong kho (thí nghiệm cần một ảnh cố định). Thiếu nguồn thì quay về bậc thấp hơn
    như `element_library.variant_inputs`.
    """
    from generation import controlnet as cn, element_library      # noqa: PLC0415
    key = (heritage_id, source)
    if key not in cache:
        _, path = element_library.variant_inputs(heritage_id, source)[0]
        cache[key] = cn.prepare(heritage_id, ornament_only=True, trim=True, image_path=path)
    return cache[key]


def run_gpu(spec: dict, rows: list[dict], out_dir: Path) -> list[dict]:  # pragma: no cover - cần GPU
    """EXP-A / EXP-B / EXP-D / EXP-E: cần GPU CUDA. Nạp model một lần cho cả kế hoạch.

    Mức garment_source="fixed" (áo mẫu cố định) chỉ còn để chạy lại các thí nghiệm cũ; luồng sản phẩm đã bỏ nó."""
    from PIL import Image                                          # noqa: PLC0415
    from generation import controlnet as cn, garment, pattern     # noqa: PLC0415
    from generation.stable_diffusion import Generator             # noqa: PLC0415
    from provenance.hashing import sha256_file                     # noqa: PLC0415
    from quality.assess import assess_design                       # noqa: PLC0415
    from quality.repair import pattern_lock                         # noqa: PLC0415
    import numpy as np                                             # noqa: PLC0415

    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    # Áo LoRA sinh trước khi nạp bộ sinh hoa văn (xem pregenerate_garments)
    garments = pregenerate_garments(lora_garment_seeds(rows), out_dir)
    gen = Generator()
    results, prepared = [], {}
    try:
        for r in rows:
            hid = r["heritage_id"]
            seed = int(r["cfg.seed"] if r["cfg.seed"] is not None else 42)
            # Áo nền của lượt này: mặc định áo mẫu cố định; mức "lora" dùng áo đã sinh cho seed này
            tpl_path, region, g_info = garment.TEMPLATE, None, {}
            if r.get("cfg.garment_source") == "lora":
                g = garments[seed]
                if not g["ok"]:
                    results.append({**r, "status": "garment_failed", "garment_error": g["error"]})
                    continue
                g_info = g["info"]
                tpl_path, region = g_info["path"], g_info["mask"]
            prep = source_prepared(prepared, hid, r.get("cfg.source", "render"))
            pattern_seed = int(r.get("cfg.pattern_seed") or seed)
            res = pattern.generate_custom(gen, hid, float(r["cfg.controlnet_weight"]), pattern_seed,
                                          r["cfg.prompt_modifier"] or "", prepared=prep)
            key = r["run_key"].replace("|", "__").replace("=", "-")
            pat_path = img_dir / f"{key}__pattern.png"
            res["image"].save(pat_path)
            raw = garment.apply(res["image"], layout=r["cfg.layout"], template_path=tpl_path, garment_region=region)
            raw_path = img_dir / f"{key}__raw.png"
            raw.save(raw_path)
            finish = r.get("cfg.stage2_finish", "img2img_0.40")
            polish_seed = int(r.get("cfg.polish_seed") if str(r.get("cfg.polish_seed")).isdigit() else seed)
            kind, strength, lock = parse_finish(finish)
            if kind == "none":
                final = raw
            else:
                if kind == "masked":
                    final = garment.polish_masked(raw, strength=strength, seed=polish_seed, mask=region)
                else:
                    final = garment.polish(raw, strength=strength, seed=polish_seed)
                if lock:
                    tpl = Image.open(tpl_path).convert("RGB")
                    lm = garment._layout_mask(tpl, garment.get_layout(r["cfg.layout"]), region)
                    locked, _ = pattern_lock(np.asarray(raw), np.asarray(final.convert("RGB")), lm)
                    final = Image.fromarray(locked)
            fin_path = img_dir / f"{key}__final.png"
            final.save(fin_path)
            ref_path = img_dir / f"{hid}__reference.png"
            if not ref_path.exists():
                prep["reference"].save(ref_path)
            qa = assess_design(reference=ref_path, pattern=pat_path, raw=raw_path, final=fin_path,
                               layout=r["cfg.layout"], template_path=tpl_path, garment_region=region)
            results.append({**r, "status": "completed", "image": f"images/{fin_path.name}",
                            "sha256": sha256_file(fin_path), "duration_s": round(res["duration_s"], 2),
                            "garment_tries": len(g_info.get("tried", [])) if g_info else "",
                            **{k: v["value"] for k, v in qa["G2_pattern"]["metrics"].items()},
                            **{k: v["value"] for k, v in qa["G3_final"]["metrics"].items()}})
    finally:
        gen.close()
        garment.free_polish_pipe()
    return results


def write_results(results: list[dict], out_dir: Path) -> Path:
    path = out_dir / "results.csv"
    keys: list[str] = []
    for r in results:
        keys += [k for k in r if k not in keys]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(results)
    return path


# ------------------------------------------------------------ đánh giá mù ----

def build_blind_packet(out_dir: Path, raters: list[str], seed: int = 20261118) -> Path:
    """Đổi tên ảnh thành mã ngẫu nhiên, xáo thứ tự riêng cho từng người chấm.

    blind/key.csv      — mã → run_key (KHÔNG gửi cho người chấm)
    blind/images/      — ảnh đã đổi tên
    blind/ratings_<rater>.csv — phiếu chấm, thứ tự riêng mỗi người
    """
    rubric = json.loads((ROOT / "config" / "expert_rubric.json").read_text(encoding="utf-8"))
    spec = json.loads((out_dir / "spec.json").read_text(encoding="utf-8"))
    wanted = spec["metrics"]["human"]
    crit = [c for c in rubric["criteria"] if c["key"] in wanted]
    results = [r for r in csv.DictReader((out_dir / "results.csv").open(encoding="utf-8"))
               if r.get("status", "completed") == "completed"]       # lượt không ra ảnh (garment_failed) không đưa đi chấm
    rng = random.Random(seed)
    codes = rng.sample(range(1000, 9999), len(results))
    blind = out_dir / "blind"
    if blind.exists():
        shutil.rmtree(blind)
    (blind / "images").mkdir(parents=True)
    key_rows = []
    for code, r in zip(codes, results):
        name = f"B{code}.png"
        shutil.copy2(out_dir / r["image"], blind / "images" / name)
        key_rows.append({"code": f"B{code}", "run_key": r["run_key"], "heritage_id": r["heritage_id"],
                         "iv_level": r["iv_level"], "replicate": r.get("replicate", "")})
    with (blind / "key.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(key_rows[0]))
        w.writeheader()
        w.writerows(key_rows)
    for rater in raters:
        order = key_rows[:]
        random.Random(f"{seed}-{rater}").shuffle(order)
        with (blind / f"ratings_{rater}.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["rater_id", "code", "heritage_reference"] + [c["key"] for c in crit] + ["comment"])
            for row in order:
                w.writerow([rater, row["code"], row["heritage_id"]] + [""] * len(crit) + [""])
    (blind / "HUONG_DAN_CHAM.md").write_text(
        "# Hướng dẫn chấm mù\n\n"
        f"Thang điểm 1–5 ({', '.join(f'{k}={v}' for k, v in rubric['scale']['labels'].items())}).\n\n"
        + "\n".join(f"- **{c['label']}** (`{c['key']}`): {c['question']}" for c in crit)
        + "\n\nKhông mở `key.csv`. Ảnh hiện vật đối chiếu: xem cột heritage_reference trong Thư viện di sản.\n",
        encoding="utf-8")
    return blind


def krippendorff_alpha_interval(matrix: list[list[float | None]]) -> float:
    """Krippendorff's alpha (dữ liệu khoảng). matrix[rater][unit], None = thiếu."""
    units = list(zip(*matrix))
    pairs_d, values = 0.0, []
    n_pairable = 0
    for unit in units:
        vals = [v for v in unit if v is not None]
        m = len(vals)
        if m < 2:
            continue
        values.extend(vals)
        n_pairable += m
        s = sum((a - b) ** 2 for i, a in enumerate(vals) for j, b in enumerate(vals) if i != j)
        pairs_d += s / (m - 1)
    if n_pairable < 2:
        return float("nan")
    do = pairs_d / n_pairable
    de = sum((a - b) ** 2 for i, a in enumerate(values) for j, b in enumerate(values) if i != j) / (
        n_pairable * (n_pairable - 1))
    return 1 - do / de if de > 0 else float("nan")


def _t95(df: int) -> float:
    table = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262,
             10: 2.228, 15: 2.131, 20: 2.086, 30: 2.042}
    return table.get(df) or table[min(table, key=lambda k: abs(k - df))] if df > 0 else float("nan")


def describe(values: list[float]) -> dict:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    n = len(vals)
    if n == 0:
        return {"n": 0}
    mean = sum(vals) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / (n - 1)) if n > 1 else 0.0
    half = _t95(n - 1) * sd / math.sqrt(n) if n > 1 else float("nan")
    return {"n": n, "mean": round(mean, 4), "sd": round(sd, 4), "ci95": [round(mean - half, 4), round(mean + half, 4)]
            if n > 1 else None, "min": round(min(vals), 4), "max": round(max(vals), 4),
            "cv": round(sd / mean, 4) if mean else None}


def paired_tests(results: list[dict], metric: str, levels: list[str]) -> dict:
    """So sánh cặp trên cùng khối (hiện vật + seed/lần lặp): mỗi mức so với mức đầu
    (đối chứng) bằng Wilcoxon có dấu; tất cả các mức cùng lúc bằng Friedman.

    Chỉ báo p khi có scipy và đủ khối (Wilcoxon ≥ 6 cặp, Friedman ≥ 3 khối); ít hơn
    thì chỉ báo hiệu trung vị — tránh diễn giải p-value trên mẫu quá nhỏ."""
    blocks: dict[tuple, dict[str, float]] = {}
    for r in results:
        v = r.get(metric)
        if v in ("", None) or r.get("status", "completed") != "completed":
            continue
        blocks.setdefault((r["heritage_id"], r.get("replicate", "")), {})[str(r["iv_level"])] = float(v)
    try:
        from scipy import stats                                     # noqa: PLC0415
    except ImportError:                                             # pragma: no cover
        stats = None
    control = levels[0]
    out: dict = {"control": control, "vs_control": {}, "friedman": None}
    for lv in levels[1:]:
        diffs = [b[lv] - b[control] for b in blocks.values() if lv in b and control in b]
        entry = {"n_pairs": len(diffs),
                 "median_diff": round(sorted(diffs)[len(diffs) // 2] if len(diffs) % 2 else
                                      sum(sorted(diffs)[len(diffs) // 2 - 1:len(diffs) // 2 + 1]) / 2, 4) if diffs else None,
                 "wilcoxon_p": None}
        if stats is not None and len(diffs) >= 6 and any(d != 0 for d in diffs):
            entry["wilcoxon_p"] = round(float(stats.wilcoxon(diffs).pvalue), 4)
        out["vs_control"][lv] = entry
    full = [b for b in blocks.values() if all(lv in b for lv in levels)]
    if stats is not None and len(full) >= 3 and len(levels) >= 3:
        res = stats.friedmanchisquare(*[[b[lv] for b in full] for lv in levels])
        out["friedman"] = {"n_blocks": len(full), "statistic": round(float(res.statistic), 3),
                           "p": round(float(res.pvalue), 4)}
    return out


def analyze(out_dir: Path) -> dict:
    """Tổng hợp chỉ số tự động (results.csv) và điểm người chấm (blind/ratings_*.csv)."""
    spec = json.loads((out_dir / "spec.json").read_text(encoding="utf-8"))
    results = list(csv.DictReader((out_dir / "results.csv").open(encoding="utf-8")))
    auto = [m for m in spec["metrics"]["automatic"] if results and m in results[0]]
    summary: dict = {"experiment_id": spec["id"], "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     "automatic": {}, "human": {}, "agreement": {}}
    levels = [str(x) for x in spec["independent_variable"]["levels"]]
    # Số lượt theo trạng thái ở từng mức: cho biết tỉ lệ lượt không ra ảnh (ví dụ LoRA không sinh được áo)
    summary["status_counts"] = {lv: {} for lv in levels}
    for r in results:
        counts = summary["status_counts"].setdefault(str(r["iv_level"]), {})
        st = r.get("status") or "completed"
        counts[st] = counts.get(st, 0) + 1
    for m in auto:
        summary["automatic"][m] = {lv: describe([float(r[m]) for r in results if r["iv_level"] == lv and r.get(m)])
                                   for lv in levels}
        summary.setdefault("automatic_tests", {})[m] = paired_tests(results, m, levels)
    blind = out_dir / "blind"
    rating_files = sorted(blind.glob("ratings_*.csv")) if blind.exists() else []
    if rating_files and (blind / "key.csv").exists():
        key = {r["code"]: r for r in csv.DictReader((blind / "key.csv").open(encoding="utf-8"))}
        crit = spec["metrics"]["human"]
        per_rater = {}
        for f in rating_files:
            rows = list(csv.DictReader(f.open(encoding="utf-8")))
            per_rater[f.stem.replace("ratings_", "")] = {r["code"]: r for r in rows}
        codes = sorted(key)
        for c in crit:
            scores_by_level: dict[str, list[float]] = {lv: [] for lv in levels}
            matrix = []
            for rater, rows in per_rater.items():
                line = []
                for code in codes:
                    v = rows.get(code, {}).get(c, "")
                    val = float(v) if v not in ("", None) else None
                    line.append(val)
                    if val is not None:
                        scores_by_level[str(key[code]["iv_level"])].append(val)
                matrix.append(line)
            summary["human"][c] = {lv: describe(v) for lv, v in scores_by_level.items()}
            alpha = krippendorff_alpha_interval(matrix)
            summary["agreement"][c] = None if math.isnan(alpha) else round(alpha, 3)
        summary["raters"] = list(per_rater)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "run"):
        p = sub.add_parser(name)
        p.add_argument("spec")
    p = sub.add_parser("blind")
    p.add_argument("dir")
    p.add_argument("--raters", required=True)
    p = sub.add_parser("analyze")
    p.add_argument("dir")
    args = ap.parse_args(argv)
    if args.cmd in ("plan", "run"):
        spec = load_spec(args.spec)
        rows = expand_plan(spec)
        out_dir = OUT / spec["id"]
        plan = write_plan(spec, rows, out_dir)
        print(f"{spec['id']}: {len(rows)} lượt chạy → {plan.relative_to(ROOT)}")
        if args.cmd == "run":
            results = run_gpu(spec, rows, out_dir) if spec.get("requires_gpu") else run_cpu_composite(spec, rows, out_dir)
            print(f"→ {write_results(results, out_dir).relative_to(ROOT)}")
    elif args.cmd == "blind":
        blind = build_blind_packet(Path(args.dir), [r.strip() for r in args.raters.split(",") if r.strip()])
        print(f"Gói chấm mù → {blind}")
    else:
        print(json.dumps(analyze(Path(args.dir)), ensure_ascii=False, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
