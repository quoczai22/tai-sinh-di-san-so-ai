# -*- coding: utf-8 -*-
"""Sinh toàn bộ tệp .bpmn từ models.py vào thư mục đích. python build.py <thư mục>"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from models import MODELS  # noqa: E402

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
stats = {}
for name, make in MODELS.items():
    d = make()
    (out / f"{name}.bpmn").write_bytes(d.to_xml().encode("utf-8"))
    stats[name] = d.stats()
(out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(stats, ensure_ascii=False))
