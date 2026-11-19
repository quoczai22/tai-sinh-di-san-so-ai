# -*- coding: utf-8 -*-
"""Xuất dữ liệu THẬT đã sinh sẵn thành JSON tĩnh cho chế độ trình diễn của web_ui.

Chế độ trình diễn chạy khi trình duyệt không gọi được API GPU (ví dụ trang tĩnh
trên Vercel). Mọi con số trong đó lấy từ tệp thật: variants.csv, Passport, kết
quả Cổng chất lượng, kế hoạch/kết quả thí nghiệm. Không có số nào viết tay.

Ảnh hiển thị được nén WebP để trang nhẹ; mã băm SHA-256 trong Passport luôn tính
trên tệp PNG gốc (giao diện ghi rõ điều này).

    python scripts/11_export_demo_data.py
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api import store                                              # noqa: E402
from api.main import ui_items                                      # noqa: E402
from provenance import passport as P                               # noqa: E402
from provenance.registry import (all_items, assess_selection, completeness,  # noqa: E402
                                 load_selection_config, rights_gate)

OUT = ROOT / "web_ui" / "data"
MEDIA = OUT / "media"


def webp(src: Path, dst: Path, size: int = 640, quality: int = 82) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
        im.thumbnail((size, size), Image.LANCZOS)
        im.save(dst, "WEBP", quality=quality, method=6)
    return dst.relative_to(ROOT / "web_ui").as_posix()


def dump(name: str, obj) -> None:
    (OUT / name).parent.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # ---- Heritage -----------------------------------------------------------
    heritage = ui_items(include_retired=True)
    selection_cfg = load_selection_config(ROOT)["criteria"]
    raw_items = {it["heritage_id"]: it for it in all_items(ROOT)}
    for h in heritage:
        h["image"] = webp(ROOT / raw_items[h["id"]]["image_path"], MEDIA / "heritage" / f"{h['id']}.webp", 720)
        h["selection"] = assess_selection(raw_items[h["id"]], ROOT)
        h["rights"] = {a: rights_gate(raw_items[h["id"]], a, ROOT).as_dict()
                       for a in ("experiment", "demo_display", "publish_public", "commercial_use")}
    dump("heritage.json", {"items": heritage, "selection_criteria": selection_cfg})

    # ---- Passports ----------------------------------------------------------
    index = store.list_passports()
    media_roles = {"reference_512", "control_canny", "pattern", "composite_raw", "final_img2img",
                   "repair_pattern_lock", "human_edit"}
    integrity_ok = 0
    for entry in index:
        p = store.get_passport(entry["passport_id"])
        for art in p["artifacts"]:
            if art["role"] in media_roles:
                art["display"] = webp(ROOT / art["path"], MEDIA / "designs" / p["passport_id"] / f"{art['role']}.webp")
        for v in p["versions"]:
            v["display"] = next((a.get("display") for a in p["artifacts"] if a["path"] == v["path"]), None)
        entry["thumb"] = p["versions"][0]["display"] if p["versions"] else None
        entry["repair_thumb"] = next((v["display"] for v in p["versions"] if v["kind"] == "system_repair"), None)
        integ = P.verify(p, ROOT)
        integrity_ok += integ["ok"]
        dump(f"passports/{p['passport_id']}.json", {**p, "timeline": P.timeline(p), "integrity": integ})
    dump("passports.json", index)

    # ---- Quality ------------------------------------------------------------
    qrows = list(csv.DictReader((ROOT / "evaluation" / "quality_gate_legacy.csv").open(encoding="utf-8")))
    qcfg = json.loads((ROOT / "config" / "quality_gate.json").read_text(encoding="utf-8"))
    dump("quality.json", {"rows": qrows, "config": qcfg})

    # ---- Experiments --------------------------------------------------------
    exps = store.list_experiments()
    for e in exps:
        d = store.EXPERIMENTS / e["id"]
        if (d / "plan.csv").exists():
            shutil.copy2(d / "plan.csv", OUT / f"{e['id']}_plan.csv")
            e["plan_csv"] = f"data/{e['id']}_plan.csv"
        if (d / "summary.json").exists():
            e["summary"] = json.loads((d / "summary.json").read_text(encoding="utf-8"))
        if (d / "results.csv").exists():
            res = list(csv.DictReader((d / "results.csv").open(encoding="utf-8")))
            for r in res:
                r["display"] = webp(d / r["image"], MEDIA / "experiments" / e["id"] / Path(r["image"]).with_suffix(".webp").name, 480)
            e["results"] = res
    dump("experiments.json", exps)

    # ---- Dashboard (chỉ số tính từ dữ liệu thật) ----------------------------
    items = list(raw_items.values())
    statuses = Counter(it.get("status", "active") for it in items)
    rights = Counter((it.get("provenance") or {}).get("rights_status") for it in items if it.get("status") == "active")
    comp = [completeness(it)["ratio"] for it in items if it.get("status") == "active"]
    g2 = Counter(r["G2"] for r in qrows)
    g3 = Counter(r["G3"] for r in qrows)
    rep = Counter(r["repair_G3"] for r in qrows if r["repair_G3"])
    approvals = Counter(e["approval"]["status"] for e in index)
    durations = sorted(float(r["duration_s"]) for r in csv.DictReader(
        (ROOT / "evaluation" / "variants.csv").open(encoding="utf-8")) if r.get("duration_s"))
    mid = len(durations) // 2
    dur_median = (durations[mid] if len(durations) % 2 else (durations[mid - 1] + durations[mid]) / 2) if durations else None
    reviews = sum(e["reviews"] for e in index)
    edits = sum(e["edits"] for e in index)
    dump("dashboard.json", {
        "generated_at": generated_at,
        "heritage": {"total": len(items), "by_status": statuses, "rights_active": rights,
                     "completeness_active_mean": round(sum(comp) / len(comp), 3) if comp else None},
        "designs": {"total": len(index), "G2": g2, "G3_before_repair": g3, "G3_after_repair": rep,
                    "approval": approvals, "reviews": reviews, "manual_edits": edits,
                    "integrity": {"ok": integrity_ok, "total": len(index)}},
        "generation_duration_s": {"median": round(dur_median, 2) if dur_median else None, "n": len(durations),
                                  "source": "evaluation/variants.csv, cột duration_s, ngày 06/09/2026, RTX 4060 Laptop 8 GB"},
        "experiments": [{"id": e["id"], "status": e["status"], "planned": e["planned_runs"],
                         "completed": e["completed_runs"]} for e in exps],
    })
    dump("rubric.json", json.loads((ROOT / "config" / "expert_rubric.json").read_text(encoding="utf-8")))
    dump("meta.json", {
        "generated_at": generated_at,
        "source": "Lần chạy pipeline ngày 06/09/2026 trên RTX 4060 Laptop 8 GB (evaluation/variants.csv); "
                  "Cổng chất lượng, Passport và EXP-C chạy lại trên CPU ngày 18/11/2026.",
        "hash_note": "Ảnh hiển thị đã nén WebP; SHA-256 trong Passport tính trên tệp PNG gốc trong repo.",
    })
    for diagram in (ROOT / "docs" / "finals" / "diagrams").glob("*.svg"):
        target = OUT / "diagrams" / diagram.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(diagram, target)
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"Đã xuất web_ui/data ({size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
