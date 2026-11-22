# -*- coding: utf-8 -*-
"""Vòng loại và thử lại cho bước polish (kế hoạch mục 3.3).

Quy trình cho một thiết kế:
  1. Polish với (seed, strength) ban đầu rồi đo cổng G3.
  2. Nếu M1 (giữ dáng áo) hoặc M3 (giữ họa tiết) vượt ngưỡng LỖI: thử lại với seed kế tiếp,
     tối đa `max_seed_retries` lần (mặc định 3).
  3. Vẫn lỗi: hạ độ nhiễu xuống `fallback_strength` (mặc định 0,22) và thử thêm đúng 1 lần.
  4. Vẫn lỗi: trả ảnh ghép thô kèm nhãn "chưa qua bước hoàn thiện", không trả ảnh lỗi.
Mọi lần bị loại được ghi vào `outputs/qc/rejects.csv` và lưu ảnh vào `outputs/qc/rejects/`.
Đây là "ví dụ bị loại hoặc sửa" cho minh chứng nộp.

Hàm `polish_with_retry` không tự gọi GPU: polish và phép đo được truyền vào, nên kiểm thử
được bằng polish giả.
"""
from __future__ import annotations

import csv
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from tsds.core.paths import QC_DIR, ROOT
# M1 và M3 trong kế hoạch. Các chỉ số khác (độ nét, lệch màu) chỉ cảnh báo, không kích hoạt thử lại.
GATED = ("garment_shape_iou", "pattern_preservation")
FALLBACK_LABEL = "chưa qua bước hoàn thiện"
REJECT_COLUMNS = ["timestamp", "tag", "attempt", "seed", "strength", "failed_metrics", "values",
                  "thresholds", "reason", "next_action", "image"]


def make_g3_evaluator(raw: Image.Image, layout: str, cfg: dict | None = None, template_path: Path | None = None,
                      garment_region: np.ndarray | None = None) -> Callable[[Image.Image], dict]:
    """Tạo hàm đo cổng G3 cho một thiết kế: nhận ảnh polish, trả kết quả `evaluate_final`.

    template_path và garment_region: áo và vùng áo tính sẵn; mặc định áo mẫu cố định."""
    from tsds.generation.garment import garment                                  # noqa: PLC0415
    from tsds.quality import gate as QG                                  # noqa: PLC0415

    tpl = Image.open(template_path or garment.TEMPLATE).convert("RGB")
    template = np.asarray(tpl)
    prior = garment.garment_mask(tpl) if garment_region is None else garment_region
    layout_mask = garment._layout_mask(tpl, garment.get_layout(layout), garment_region)
    raw_a = np.asarray(raw.convert("RGB"))
    cfg = cfg or QG.load_config()
    return lambda final: QG.evaluate_final(raw_a, np.asarray(final.convert("RGB")), template,
                                           layout_mask, prior, cfg)


def failed_gated(g3: dict) -> list[str]:
    """Các chỉ số M1/M3 đang ở mức LỖI trong kết quả cổng G3."""
    return [k for k in GATED if g3["metrics"].get(k, {}).get("status") == "FAIL"]


def _log_reject(qc_dir: Path, tag: str, attempt: int, seed: int, strength: float, image: Image.Image | None,
                g3: dict | None, failed: list[str], reason: str, next_action: str) -> None:
    """Ghi một dòng vào rejects.csv và lưu ảnh bị loại (nếu có)."""
    qc_dir.mkdir(parents=True, exist_ok=True)
    img_rel = ""
    if image is not None:
        (qc_dir / "rejects").mkdir(exist_ok=True)
        path = qc_dir / "rejects" / f"{tag}_a{attempt}_s{seed}_st{strength:.2f}.png"
        image.save(path)
        img_rel = path.relative_to(qc_dir).as_posix()
    metrics = (g3 or {}).get("metrics", {})
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tag": tag,
        "attempt": attempt, "seed": seed, "strength": strength, "failed_metrics": ";".join(failed),
        "values": ";".join(f"{k}={metrics[k]['value']}" for k in failed if k in metrics),
        "thresholds": ";".join(f"{k}<{metrics[k]['fail']}" if metrics[k].get("fail") is not None else k
                               for k in failed if k in metrics),
        "reason": reason, "next_action": next_action, "image": img_rel,
    }
    csv_path = qc_dir / "rejects.csv"
    new = not csv_path.exists()
    with open(csv_path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REJECT_COLUMNS)
        if new:
            w.writeheader()
        w.writerow(row)


def polish_with_retry(raw: Image.Image, polish_fn: Callable[[Image.Image, float, int], Image.Image],
                      evaluate: Callable[[Image.Image], dict], *, seed: int, strength: float,
                      fallback_strength: float = 0.22, max_seed_retries: int = 3,
                      qc_dir: Path | None = None, tag: str = "design") -> dict:
    """Chạy polish, đo G3, thử lại theo quy tắc ở đầu file.

    polish_fn(ảnh_ghép_thô, strength, seed) -> ảnh polish
    evaluate(ảnh polish) -> kết quả `quality.gate.evaluate_final`

    Trả về dict: image, status, label, seed, strength, attempts (danh sách từng lần thử).
    status: "passed" (đạt ngay), "retried_seed" (đạt sau khi đổi seed),
            "lower_strength" (đạt sau khi hạ độ nhiễu), "raw_fallback" (trả ảnh ghép thô).
    """
    qc_dir = Path(qc_dir) if qc_dir else QC_DIR
    # Chuỗi thử: seed ban đầu, rồi các seed kế tiếp cùng độ nhiễu, cuối cùng hạ độ nhiễu một lần.
    plan = [(seed + i, strength, "retried_seed" if i else "passed") for i in range(max_seed_retries + 1)]
    plan.append((seed, fallback_strength, "lower_strength"))
    attempts: list[dict] = []
    for n, (s, st, ok_status) in enumerate(plan, start=1):
        is_last = n == len(plan)
        next_action = ("trả ảnh ghép thô" if is_last else
                       "hạ độ nhiễu và thử lần cuối" if n == len(plan) - 1 else "thử lại với seed kế tiếp")
        try:
            img = polish_fn(raw, st, s)
            g3 = evaluate(img)
        except Exception as exc:                                    # noqa: BLE001
            attempts.append({"attempt": n, "seed": s, "strength": st, "status": "error",
                             "error": type(exc).__name__})
            _log_reject(qc_dir, tag, n, s, st, None, None, [], f"Lỗi khi polish hoặc đo: {type(exc).__name__}",
                        next_action)
            continue
        failed = failed_gated(g3)
        attempts.append({"attempt": n, "seed": s, "strength": st, "status": "failed" if failed else "ok",
                         "failed_metrics": failed, "decision": g3["decision"]})
        if not failed:
            return {"image": img, "status": ok_status, "label": None, "seed": s, "strength": st,
                    "attempts": attempts, "g3": g3}
        reason = "; ".join(f"{g3['metrics'][k]['label']} = {g3['metrics'][k]['value']} "
                           f"(ngưỡng lỗi {g3['metrics'][k]['fail']})" for k in failed)
        _log_reject(qc_dir, tag, n, s, st, img, g3, failed, reason, next_action)
    return {"image": raw, "status": "raw_fallback", "label": FALLBACK_LABEL, "seed": None, "strength": None,
            "attempts": attempts, "g3": None}
