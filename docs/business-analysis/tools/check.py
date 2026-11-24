# -*- coding: utf-8 -*-
"""Kiểm định ngữ nghĩa các tệp BPMN 2.0 (bổ sung cho việc nạp bằng bpmn-js).

Kiểm tra cho từng process: có sự kiện bắt đầu và kết thúc; mọi nút đi được từ một sự kiện bắt đầu và tới được một
sự kiện kết thúc; cổng rẽ nhánh có ít nhất 2 luồng ra và luồng ra có tên/điều kiện; sequence flow không vượt pool;
message flow nối hai pool khác nhau; boundary event gắn vào tác vụ có thật; mọi nút có hình (DI).

    python check.py <thư mục .bpmn>      → in bảng kết quả, mã thoát 1 nếu có lỗi
"""
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

NS = {"b": "http://www.omg.org/spec/BPMN/20100524/MODEL", "di": "http://www.omg.org/spec/BPMN/20100524/DI",
      "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI"}
B = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
FLOW_NODES = {"startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent", "boundaryEvent",
              "task", "userTask", "serviceTask", "manualTask", "businessRuleTask", "sendTask", "receiveTask",
              "scriptTask", "subProcess", "callActivity", "exclusiveGateway", "parallelGateway",
              "inclusiveGateway", "eventBasedGateway"}


def check(path: Path) -> dict:
    root = ET.parse(path).getroot()
    errors, info = [], defaultdict(int)
    shapes = {s.get("bpmnElement") for s in root.iter("{http://www.omg.org/spec/BPMN/20100524/DI}BPMNShape")}
    edges = {e.get("bpmnElement") for e in root.iter("{http://www.omg.org/spec/BPMN/20100524/DI}BPMNEdge")}
    owner = {}
    procs = root.findall("b:process", NS)
    for proc in procs:
        nodes = {el.get("id"): el.tag.replace(B, "") for el in proc if el.tag.replace(B, "") in FLOW_NODES}
        for nid in nodes:
            owner[nid] = proc.get("id")
        flows = [(f.get("id"), f.get("sourceRef"), f.get("targetRef"), f.get("name"), f.find("b:conditionExpression", NS))
                 for f in proc.findall("b:sequenceFlow", NS)]
        out, inc = defaultdict(list), defaultdict(list)
        for fid, s, t, name, cond in flows:
            if s not in nodes or t not in nodes:
                errors.append(f"{fid}: sequence flow trỏ tới nút ngoài process (vượt pool)")
                continue
            out[s].append((fid, t, name, cond))
            inc[t].append(s)
            if fid not in edges:
                errors.append(f"{fid}: thiếu hình (BPMNEdge)")
        for nid, kind in nodes.items():
            info[kind] += 1
            if nid not in shapes:
                errors.append(f"{nid}: thiếu hình (BPMNShape)")
        starts = [n for n, k in nodes.items() if k == "startEvent"]
        ends = [n for n, k in nodes.items() if k == "endEvent"]
        if not starts:
            errors.append(f"{proc.get('id')}: không có sự kiện bắt đầu")
        if not ends:
            errors.append(f"{proc.get('id')}: không có sự kiện kết thúc")
        # đồ thị mở rộng: boundary event là điểm xuất phát phụ (đi ra từ tác vụ nó gắn vào)
        boundary = {el.get("id"): el.get("attachedToRef") for el in proc.findall("b:boundaryEvent", NS)}
        for bid, host in boundary.items():
            if host not in nodes:
                errors.append(f"{bid}: gắn vào nút không tồn tại")
            out[host].append((None, bid, None, None))
        seen, stack = set(starts), list(starts)
        while stack:
            n = stack.pop()
            for _, t, _, _ in out[n]:
                if t not in seen:
                    seen.add(t)
                    stack.append(t)
        for nid in nodes:
            if nid not in seen:
                errors.append(f"{nid}: không đi tới được từ sự kiện bắt đầu")
        rev = defaultdict(list)
        for s, lst in out.items():
            for _, t, _, _ in lst:
                rev[t].append(s)
        seen2, stack = set(ends), list(ends)
        while stack:
            n = stack.pop()
            for s in rev[n]:
                if s not in seen2:
                    seen2.add(s)
                    stack.append(s)
        for nid in nodes:
            if nid not in seen2:
                errors.append(f"{nid}: không tới được sự kiện kết thúc")
        for nid, kind in nodes.items():
            if kind in ("exclusiveGateway", "inclusiveGateway"):
                o = [x for x in out[nid] if x[0]]
                if len(o) >= 2:
                    for fid, _, name, cond in o:
                        if not name or cond is None:
                            errors.append(f"{fid}: nhánh ra của cổng {nid} thiếu tên hoặc điều kiện")
                elif len(inc[nid]) < 2:
                    errors.append(f"{nid}: cổng chỉ có 1 vào 1 ra (cổng trang trí)")
            if kind == "eventBasedGateway":
                for _, t, _, _ in out[nid]:
                    if nodes.get(t) not in ("intermediateCatchEvent", "receiveTask"):
                        errors.append(f"{nid}: cổng sự kiện phải dẫn tới sự kiện bắt/nhận")
            if kind not in ("endEvent", "boundaryEvent") and not [x for x in out[nid] if x[0]] and kind != "startEvent":
                if kind not in ("endEvent",):
                    errors.append(f"{nid}: không có luồng ra (cụt)")
    parts = {p.get("id"): p.get("processRef") for p in root.iter(B + "participant")}
    for m in root.iter(B + "messageFlow"):
        s, t = m.get("sourceRef"), m.get("targetRef")
        ps = owner.get(s) or parts.get(s, s)
        pt = owner.get(t) or parts.get(t, t)
        info["messageFlow"] += 1
        if ps == pt:
            errors.append(f"{m.get('id')}: message flow nằm trong cùng một pool")
        if m.get("id") not in edges:
            errors.append(f"{m.get('id')}: thiếu hình (BPMNEdge)")
    info["pool"] = len(parts)
    info["lane"] = len(list(root.iter(B + "lane")))
    return {"errors": errors, "elements": dict(info)}


if __name__ == "__main__":
    folder = Path(sys.argv[1])
    res = {f.name: check(f) for f in sorted(folder.glob("*.bpmn"))}
    bad = 0
    for name, r in res.items():
        print(f"{name}: {'ĐẠT' if not r['errors'] else 'LỖI'} ({len(r['errors'])} lỗi)")
        for e in r["errors"]:
            print("   -", e)
        bad += bool(r["errors"])
    (folder / "check_report.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.exit(1 if bad else 0)
