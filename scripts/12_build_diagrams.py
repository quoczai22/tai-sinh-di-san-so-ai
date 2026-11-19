# -*- coding: utf-8 -*-
"""Sinh sơ đồ BPMN 2.0 (XML có Diagram Interchange + SVG) và UML Use Case (SVG + PlantUML).

Một mô hình dữ liệu → hai đầu ra, nên hình vẽ và tệp .bpmn không bao giờ lệch nhau.
Tệp .bpmn mở được bằng Camunda Modeler hoặc https://demo.bpmn.io để chỉnh tiếp.

    python scripts/12_build_diagrams.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "finals" / "diagrams"

INK, LINE, LAM, DAT, NGOC = "#1D2A36", "#7A8591", "#24508A", "#8B5E3C", "#2E7A64"
FONT = "Be Vietnam Pro, Segoe UI, Arial, sans-serif"
TASK_W, TASK_H, GW, EV = 132, 66, 46, 34
COL_W, POOL_LABEL, LANE_LABEL = 158, 34, 34


def wrap(text: str, width: int = 18) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


# --------------------------------------------------------------- mô hình BPMN --

class Bpmn:
    def __init__(self, name: str):
        self.name = name
        self.pools: list[dict] = []
        self.nodes: dict[str, dict] = {}
        self.flows: list[dict] = []
        self.messages: list[dict] = []

    def pool(self, pid, label, lanes, height_rows=None, process=True):
        self.pools.append({"id": pid, "label": label, "lanes": lanes, "process": process,
                           "rows": height_rows or {}})

    def node(self, nid, kind, pool, lane, col, label="", row=0, attach=None, dx=0):
        self.nodes[nid] = {"id": nid, "kind": kind, "pool": pool, "lane": lane, "col": col, "row": row,
                           "label": label, "attach": attach, "dx": dx}

    def flow(self, src, dst, label="", exit="right", enter="left", ch=None, edx=0):
        """exit/enter ∈ right|left|top|bottom. ch: độ lệch (px) của kênh đi vòng khi
        cả hai đầu cùng phía trên/dưới. edx: dịch điểm vào trên cạnh trên/dưới."""
        self.flows.append({"id": f"F_{src}_{dst}", "src": src, "dst": dst, "label": label,
                           "exit": exit, "enter": enter, "ch": ch, "edx": edx})

    def msg(self, src, dst, label=""):
        self.messages.append({"id": f"M_{src}_{dst}", "src": src, "dst": dst, "label": label})

    # ---- bố cục ----
    def layout(self):
        y = 20
        self.lane_box = {}
        self.pool_box = {}
        max_col = max(n["col"] for n in self.nodes.values())
        width = POOL_LABEL + LANE_LABEL + (max_col + 1) * COL_W + 40
        self.width = width + 40
        for p in self.pools:
            top = y
            for lane_id, lane_label in p["lanes"]:
                rows = [n["row"] for n in self.nodes.values() if n["pool"] == p["id"] and n["lane"] == lane_id] or [0]
                h = 120 + 70 * (max(rows) - min(rows))
                if not p["process"]:
                    h = 64
                self.lane_box[(p["id"], lane_id)] = {"x": 20 + POOL_LABEL, "y": y, "w": width - POOL_LABEL, "h": h,
                                                     "label": lane_label, "row0": min(rows)}
                y += h
            self.pool_box[p["id"]] = {"x": 20, "y": top, "w": width, "h": y - top, "label": p["label"]}
            y += 36
        self.height = y
        for n in self.nodes.values():
            lane = self.lane_box[(n["pool"], n["lane"])]
            cx = 20 + POOL_LABEL + LANE_LABEL + n["col"] * COL_W + COL_W / 2 + n["dx"]
            cy = lane["y"] + 60 + 70 * (n["row"] - lane["row0"])
            w, h = {"task": (TASK_W, TASK_H), "gateway": (GW, GW)}.get(self.family(n), (EV, EV))
            n.update(cx=cx, cy=cy, w=w, h=h, x=cx - w / 2, y=cy - h / 2)
        for n in self.nodes.values():
            if n["attach"]:
                host = self.nodes[n["attach"]]
                n.update(cx=host["cx"] + 30, cy=host["y"] + host["h"], x=host["cx"] + 30 - EV / 2, y=host["y"] + host["h"] - EV / 2)

    @staticmethod
    def family(n):
        k = n["kind"]
        return "task" if k.endswith("Task") else "gateway" if k.endswith("Gateway") else "event"

    @staticmethod
    def _port(n, side, dx=0):
        return {"right": (n["x"] + n["w"], n["cy"]), "left": (n["x"], n["cy"]),
                "top": (n["cx"] + dx, n["y"]), "bottom": (n["cx"] + dx, n["y"] + n["h"])}[side]

    def route(self, f):
        a, b = self.nodes[f["src"]], self.nodes[f["dst"]]
        ex, en = f["exit"], f["enter"]
        if a["attach"]:
            ex = "bottom"
        (x1, y1), (x2, y2) = self._port(a, ex), self._port(b, en, f.get("edx", 0))
        h1, h2 = ex in ("left", "right"), en in ("left", "right")
        if h1 and h2:
            if abs(y1 - y2) < 1:
                return [(x1, y1), (x2, y2)]
            mid = (x1 + x2) / 2 if f["ch"] is None else x1 + f["ch"]
            return [(x1, y1), (mid, y1), (mid, y2), (x2, y2)]
        if not h1 and h2:
            return [(x1, y1), (x1, y2), (x2, y2)]
        if h1 and not h2:
            return [(x1, y1), (x2, y1), (x2, y2)]
        if abs(x1 - x2) < 1:
            return [(x1, y1), (x2, y2)]
        if ex == en:    # vòng qua kênh phía dưới/trên
            base = max(y1, y2) if ex == "bottom" else min(y1, y2)
            off = f["ch"] if f["ch"] is not None else (22 if ex == "bottom" else -22)
            return [(x1, y1), (x1, base + off), (x2, base + off), (x2, y2)]
        mid = (y1 + y2) / 2 if f["ch"] is None else y1 + f["ch"]
        return [(x1, y1), (x1, mid), (x2, mid), (x2, y2)]

    def msg_route(self, m):
        a = self.nodes.get(m["src"]) or self.pool_box[m["src"]]
        b = self.nodes.get(m["dst"]) or self.pool_box[m["dst"]]
        ax = a.get("cx", None)
        bx = b.get("cx", None)
        x = ax if ax is not None else bx
        x2 = bx if bx is not None else ax
        ay = a["y"] + a["h"] if a["y"] < b["y"] else a["y"]
        by = b["y"] if a["y"] < b["y"] else b["y"] + b["h"]
        if abs(x - x2) < 1:
            return [(x, ay), (x2, by)]
        # đoạn ngang đi trong khe giữa hai pool, không cắt ngang lane nào
        lower = a if a["y"] > b["y"] else b
        pool = self.pool_box.get(lower.get("pool", lower.get("id"))) or lower
        gap = pool["y"] - 18
        return [(x, ay), (x, gap), (x2, gap), (x2, by)]

    # ---- XML BPMN 2.0 ----
    def to_xml(self) -> str:
        out = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
               'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
               'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Defs_TSDS" targetNamespace="https://tai-sinh-di-san-so/bpmn" '
               'exporter="scripts/12_build_diagrams.py" exporterVersion="1.0">']
        out.append('  <bpmn:collaboration id="Collab">')
        for p in self.pools:
            ref = f' processRef="Proc_{p["id"]}"' if p["process"] else ""
            out.append(f'    <bpmn:participant id="{p["id"]}" name="{escape(p["label"])}"{ref}/>')
        for m in self.messages:
            out.append(f'    <bpmn:messageFlow id="{m["id"]}" name="{escape(m["label"])}" sourceRef="{m["src"]}" targetRef="{m["dst"]}"/>')
        out.append('  </bpmn:collaboration>')
        for p in self.pools:
            if not p["process"]:
                continue
            out.append(f'  <bpmn:process id="Proc_{p["id"]}" isExecutable="false">')
            out.append(f'    <bpmn:laneSet id="LS_{p["id"]}">')
            for lane_id, label in p["lanes"]:
                out.append(f'      <bpmn:lane id="{lane_id}" name="{escape(label)}">')
                for n in self.nodes.values():
                    if n["pool"] == p["id"] and n["lane"] == lane_id:
                        out.append(f'        <bpmn:flowNodeRef>{n["id"]}</bpmn:flowNodeRef>')
                out.append('      </bpmn:lane>')
            out.append('    </bpmn:laneSet>')
            for n in self.nodes.values():
                if n["pool"] != p["id"]:
                    continue
                inc = [f["id"] for f in self.flows if f["dst"] == n["id"]]
                outg = [f["id"] for f in self.flows if f["src"] == n["id"]]
                kind = n["kind"]
                tag, extra, inner = kind, "", ""
                if kind in ("messageStartEvent", "messageEndEvent", "messageCatchEvent", "errorEndEvent", "errorBoundaryEvent"):
                    tag = {"messageStartEvent": "startEvent", "messageEndEvent": "endEvent", "messageCatchEvent": "intermediateCatchEvent",
                           "errorEndEvent": "endEvent", "errorBoundaryEvent": "boundaryEvent"}[kind]
                    inner = "<bpmn:errorEventDefinition/>" if "error" in kind else "<bpmn:messageEventDefinition/>"
                    if kind == "errorBoundaryEvent":
                        extra = f' attachedToRef="{n["attach"]}" cancelActivity="true"'
                body = "".join(f"<bpmn:incoming>{i}</bpmn:incoming>" for i in inc) + \
                       "".join(f"<bpmn:outgoing>{o}</bpmn:outgoing>" for o in outg) + inner
                out.append(f'    <bpmn:{tag} id="{n["id"]}" name="{escape(n["label"])}"{extra}>{body}</bpmn:{tag}>')
            for f in self.flows:
                if self.nodes[f["src"]]["pool"] == p["id"]:
                    out.append(f'    <bpmn:sequenceFlow id="{f["id"]}" name="{escape(f["label"])}" sourceRef="{f["src"]}" targetRef="{f["dst"]}"/>')
            out.append('  </bpmn:process>')
        out.append('  <bpmndi:BPMNDiagram id="Diagram"><bpmndi:BPMNPlane id="Plane" bpmnElement="Collab">')
        for p in self.pools:
            b = self.pool_box[p["id"]]
            out.append(f'    <bpmndi:BPMNShape id="{p["id"]}_di" bpmnElement="{p["id"]}" isHorizontal="true">'
                       f'<dc:Bounds x="{b["x"]:.0f}" y="{b["y"]:.0f}" width="{b["w"]:.0f}" height="{b["h"]:.0f}"/></bpmndi:BPMNShape>')
            if p["process"]:
                for lane_id, _ in p["lanes"]:
                    lb = self.lane_box[(p["id"], lane_id)]
                    out.append(f'    <bpmndi:BPMNShape id="{lane_id}_di" bpmnElement="{lane_id}" isHorizontal="true">'
                               f'<dc:Bounds x="{lb["x"]:.0f}" y="{lb["y"]:.0f}" width="{lb["w"]:.0f}" height="{lb["h"]:.0f}"/></bpmndi:BPMNShape>')
        for n in self.nodes.values():
            out.append(f'    <bpmndi:BPMNShape id="{n["id"]}_di" bpmnElement="{n["id"]}">'
                       f'<dc:Bounds x="{n["x"]:.0f}" y="{n["y"]:.0f}" width="{n["w"]:.0f}" height="{n["h"]:.0f}"/></bpmndi:BPMNShape>')
        for f in self.flows:
            pts = "".join(f'<di:waypoint x="{x:.0f}" y="{y:.0f}"/>' for x, y in self.route(f))
            out.append(f'    <bpmndi:BPMNEdge id="{f["id"]}_di" bpmnElement="{f["id"]}">{pts}</bpmndi:BPMNEdge>')
        for m in self.messages:
            pts = "".join(f'<di:waypoint x="{x:.0f}" y="{y:.0f}"/>' for x, y in self.msg_route(m))
            out.append(f'    <bpmndi:BPMNEdge id="{m["id"]}_di" bpmnElement="{m["id"]}">{pts}</bpmndi:BPMNEdge>')
        out.append('  </bpmndi:BPMNPlane></bpmndi:BPMNDiagram>')
        out.append('</bpmn:definitions>')
        return "\n".join(out)

    # ---- SVG ----
    def to_svg(self, title: str) -> str:
        W, H = self.width, self.height + 30
        o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" font-family="{FONT}" font-size="12">',
             '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">'
             f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>'
             '<marker id="oarr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">'
             f'<path d="M0,0 L10,5 L0,10 z" fill="#fff" stroke="{INK}"/></marker>'
             '<marker id="ocirc" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="8" markerHeight="8">'
             f'<circle cx="5" cy="5" r="4" fill="#fff" stroke="{INK}"/></marker></defs>',
             f'<rect width="100%" height="100%" fill="#fff"/>',
             f'<text x="20" y="{H - 10:.0f}" fill="{LINE}" font-size="11">{escape(title)}</text>']
        for p in self.pools:
            b = self.pool_box[p["id"]]
            o.append(f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["w"]}" height="{b["h"]}" fill="#fff" stroke="{INK}" stroke-width="1.4"/>')
            if not p["process"]:
                # pool hộp đen (black-box): tên đặt ngang ở giữa, không có lane
                o.append(f'<text x="{b["x"] + b["w"] / 2}" y="{b["y"] + b["h"] / 2}" text-anchor="middle" dominant-baseline="middle" font-weight="700" fill="{INK}">{escape(p["label"])} (pool hộp đen)</text>')
                continue
            o.append(f'<line x1="{b["x"] + POOL_LABEL}" y1="{b["y"]}" x2="{b["x"] + POOL_LABEL}" y2="{b["y"] + b["h"]}" stroke="{INK}"/>')
            cx, cy = b["x"] + POOL_LABEL / 2, b["y"] + b["h"] / 2
            plines = wrap(p["label"], max(8, int(b["h"] / 9.5)))
            for i, t in enumerate(plines):
                dx = (i - (len(plines) - 1) / 2) * 14
                o.append(f'<text x="{cx + dx}" y="{cy}" transform="rotate(-90 {cx + dx} {cy})" text-anchor="middle" dominant-baseline="middle" font-weight="700" fill="{INK}">{escape(t)}</text>')
            if p["process"]:
                for lane_id, label in p["lanes"]:
                    lb = self.lane_box[(p["id"], lane_id)]
                    o.append(f'<rect x="{lb["x"]}" y="{lb["y"]}" width="{lb["w"]}" height="{lb["h"]}" fill="none" stroke="{LINE}"/>')
                    o.append(f'<line x1="{lb["x"] + LANE_LABEL}" y1="{lb["y"]}" x2="{lb["x"] + LANE_LABEL}" y2="{lb["y"] + lb["h"]}" stroke="{LINE}"/>')
                    lx, ly = lb["x"] + LANE_LABEL / 2, lb["y"] + lb["h"] / 2
                    lines = wrap(label, 22)
                    for i, t in enumerate(lines):
                        dy = (i - (len(lines) - 1) / 2) * 13
                        o.append(f'<text x="{lx + dy}" y="{ly}" transform="rotate(-90 {lx + dy} {ly})" text-anchor="middle" dominant-baseline="middle" fill="{INK}" font-size="11.5">{escape(t)}</text>')
        for f in self.flows:
            pts = self.route(f)
            d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            o.append(f'<polyline points="{d}" fill="none" stroke="{INK}" stroke-width="1.3" marker-end="url(#arr)"/>')
            if f["label"]:
                (x1, y1), (x2, y2) = pts[0], pts[1]
                if abs(x1 - x2) < 1:
                    tx, ty, anchor = x1 + 6, y1 + (14 if y2 > y1 else -8), "start"
                else:
                    tx, ty, anchor = x1 + (8 if x2 > x1 else -8), y1 - 6, "start" if x2 > x1 else "end"
                o.append(f'<text x="{tx:.0f}" y="{ty:.0f}" text-anchor="{anchor}" fill="{DAT}" font-size="11">{escape(f["label"])}</text>')
        for m in self.messages:
            pts = self.msg_route(m)
            d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            o.append(f'<polyline points="{d}" fill="none" stroke="{INK}" stroke-width="1.2" stroke-dasharray="7 5" marker-start="url(#ocirc)" marker-end="url(#oarr)"/>')
            if m["label"]:
                if len(pts) == 4:
                    x, y = min(pts[1][0], pts[2][0]) + 8, pts[1][1] - 5
                else:
                    x, y = pts[0][0] + 6, (pts[0][1] + pts[-1][1]) / 2
                o.append(f'<text x="{x:.0f}" y="{y:.0f}" fill="{LAM}" font-size="11" font-style="italic">{escape(m["label"])}</text>')
        for n in self.nodes.values():
            o.extend(self._shape(n))
        o.append("</svg>")
        return "\n".join(o)

    def _shape(self, n):
        k, x, y, w, h, cx, cy = n["kind"], n["x"], n["y"], n["w"], n["h"], n["cx"], n["cy"]
        o = []
        if self.family(n) == "task":
            o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#fff" stroke="{INK}" stroke-width="1.4"/>')
            icon = {"userTask": self._user, "serviceTask": self._gear, "manualTask": self._hand, "sendTask": self._env}[k]
            o.extend(icon(x + 12, y + 12, k == "sendTask"))
            lines = wrap(n["label"], 18)
            for i, t in enumerate(lines):
                o.append(f'<text x="{cx + 6}" y="{cy + 9 + (i - (len(lines) - 1) / 2) * 13:.1f}" text-anchor="middle" fill="{INK}" font-size="11.5">{escape(t)}</text>')
        elif self.family(n) == "gateway":
            o.append(f'<path d="M{cx},{y} L{x + w},{cy} L{cx},{y + h} L{x},{cy} z" fill="#fff" stroke="{INK}" stroke-width="1.4"/>')
            o.append(f'<path d="M{cx - 9},{cy - 9} L{cx + 9},{cy + 9} M{cx + 9},{cy - 9} L{cx - 9},{cy + 9}" stroke="{INK}" stroke-width="3"/>')
            # tên cổng đặt chéo trên-trái để không đè nhãn của luồng đi ra phía trên
            lines = wrap(n["label"], 16)
            for i, t in enumerate(lines):
                o.append(f'<text x="{x - 2}" y="{y - 2 - (len(lines) - 1 - i) * 13}" text-anchor="end" fill="{INK}" font-size="11" font-weight="600">{escape(t)}</text>')
        else:
            r = EV / 2
            end = "End" in k or k == "endEvent"
            stroke = 3.2 if end else 1.4
            o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fff" stroke="{INK}" stroke-width="{stroke}"/>')
            if k in ("messageCatchEvent", "errorBoundaryEvent"):
                o.append(f'<circle cx="{cx}" cy="{cy}" r="{r - 4}" fill="none" stroke="{INK}" stroke-width="1.2"/>')
            if "message" in k:
                o.extend(self._env(cx - 8, cy - 6, k == "messageEndEvent"))
            if "error" in k:
                o.append(f'<path d="M{cx - 7},{cy + 7} L{cx - 3},{cy - 6} L{cx + 2},{cy + 2} L{cx + 7},{cy - 7} L{cx + 3},{cy + 7} L{cx - 2},{cy - 1} z" fill="{INK if end else "#fff"}" stroke="{INK}"/>')
            for i, t in enumerate(wrap(n["label"], 18)):
                o.append(f'<text x="{cx}" y="{cy + r + 14 + i * 13}" text-anchor="middle" fill="{INK}" font-size="11">{escape(t)}</text>')
        return o

    @staticmethod
    def _user(x, y, _=False):
        return [f'<circle cx="{x + 6}" cy="{y + 4}" r="3.5" fill="none" stroke="{INK}"/>',
                f'<path d="M{x},{y + 15} q0,-7 6,-7 q6,0 6,7 z" fill="none" stroke="{INK}"/>']

    @staticmethod
    def _gear(x, y, _=False):
        return [f'<circle cx="{x + 7}" cy="{y + 7}" r="6" fill="none" stroke="{INK}" stroke-dasharray="2.4 1.6" stroke-width="2.4"/>',
                f'<circle cx="{x + 7}" cy="{y + 7}" r="2.4" fill="none" stroke="{INK}"/>']

    @staticmethod
    def _hand(x, y, _=False):
        return [f'<path d="M{x},{y + 8} h4 v-6 h2 v6 h2 v-7 h2 v7 h2 v-5 h2 v8 q0,6 -6,6 h-4 q-4,0 -4,-4 z" fill="none" stroke="{INK}"/>']

    @staticmethod
    def _env(x, y, filled=False):
        fill = INK if filled else "#fff"
        stroke = "#fff" if filled else INK
        return [f'<rect x="{x}" y="{y}" width="16" height="11" fill="{fill}" stroke="{INK}"/>',
                f'<path d="M{x},{y} l8,6 l8,-6" fill="none" stroke="{stroke}"/>']


def to_be() -> Bpmn:
    m = Bpmn("TO-BE")
    m.pool("P_ORG", "Nền tảng Tái Sinh Di Sản Số", [
        ("L_DES", "Nhà thiết kế"),
        ("L_AI", "Hệ thống AI (GPU)"),
        ("L_QC", "Kiểm soát chất lượng"),
        ("L_DATA", "Dữ liệu và Passport"),
    ])
    m.pool("P_EXP", "Hội đồng chuyên gia", [("L_EXP", "Chuyên gia")])
    m.pool("P_OWN", "Chủ sở hữu ảnh", [("L_OWN", "")], process=False)
    N = m.node
    N("S1", "startEvent", "P_ORG", "L_DES", 0, "Có nhu cầu thiết kế")
    N("T1", "userTask", "P_ORG", "L_DES", 1, "Chọn hoặc tải lên hiện vật gốm")
    N("T2", "serviceTask", "P_ORG", "L_DATA", 2, "Kiểm tra dữ liệu, nguồn gốc (C1–C4)")
    N("G1", "exclusiveGateway", "P_ORG", "L_DATA", 3, "Đạt tiêu chí tuyển ảnh?")
    N("T3", "serviceTask", "P_ORG", "L_DATA", 4, "Kiểm tra quyền sử dụng, giấy phép")
    N("G2", "exclusiveGateway", "P_ORG", "L_DATA", 5, "Tình trạng quyền?")
    N("E_BLOCK", "endEvent", "P_ORG", "L_DATA", 6, "Không được dùng hiện vật", row=-1)
    N("T3b", "sendTask", "P_ORG", "L_DATA", 6, "Gửi đề nghị cấp phép, gắn nhãn phi thương mại", row=1)
    N("GM", "exclusiveGateway", "P_ORG", "L_DATA", 7, "")
    N("T4", "serviceTask", "P_ORG", "L_AI", 8, "Trích xuất đặc trưng: tách nền, Canny, bảng màu")
    N("T5", "serviceTask", "P_ORG", "L_AI", 9, "Sinh họa tiết SD1.5 + ControlNet")
    N("BE1", "errorBoundaryEvent", "P_ORG", "L_AI", 9, "", attach="T5")
    N("E_ERR", "errorEndEvent", "P_ORG", "L_AI", 9, "Lỗi GPU: job thất bại, đã ghi nhật ký", row=1, dx=30)
    N("TQ1", "serviceTask", "P_ORG", "L_QC", 10, "Cổng G2: kiểm tra hoa văn")
    N("GQ1", "exclusiveGateway", "P_ORG", "L_QC", 11, "Hoa văn đạt?")
    N("T_ADJ", "userTask", "P_ORG", "L_DES", 11, "Điều chỉnh tham số, chọn seed khác")
    N("T6", "serviceTask", "P_ORG", "L_AI", 12, "Chọn bố cục, ghép tất định lên áo mẫu")
    N("T7", "serviceTask", "P_ORG", "L_AI", 13, "Hoàn thiện img2img")
    N("TQ2", "serviceTask", "P_ORG", "L_QC", 14, "Cổng G3: kiểm tra thiết kế cuối")
    N("GQ2", "exclusiveGateway", "P_ORG", "L_QC", 15, "Kết quả G3?")
    N("T_REP", "serviceTask", "P_ORG", "L_AI", 16, "Sửa: khoá họa tiết hoặc giảm strength")
    N("T_QC", "userTask", "P_ORG", "L_QC", 16, "QC Officer xem cảnh báo", row=1)
    N("GQ3", "exclusiveGateway", "P_ORG", "L_QC", 17, "QC quyết định?", row=1)
    N("T_CUR", "userTask", "P_ORG", "L_DES", 18, "Xem bộ thiết kế, chọn phương án đề cử")
    N("T_SEND", "sendTask", "P_ORG", "L_QC", 19, "Gửi yêu cầu thẩm định ẩn danh")
    N("IC1", "messageCatchEvent", "P_ORG", "L_QC", 20, "Nhận kết quả thẩm định")
    N("GE", "exclusiveGateway", "P_ORG", "L_QC", 21, "Kết quả thẩm định?")
    N("E_REJ", "endEvent", "P_ORG", "L_QC", 21, "Bị loại, đã ghi lý do", row=-1, dx=60)
    N("T_LOG", "serviceTask", "P_ORG", "L_QC", 22, "Ghi lý do yêu cầu sửa vào Passport")
    N("T_EDIT", "manualTask", "P_ORG", "L_DES", 22, "Chỉnh sửa thủ công trên phần mềm đồ họa", row=1)
    N("T_UPL", "userTask", "P_ORG", "L_DES", 21, "Tải bản sửa lên, khai báo thay đổi", row=1)
    N("T_PP", "serviceTask", "P_ORG", "L_DATA", 22, "Phê duyệt, cập nhật Design Passport")
    N("T_SAVE", "serviceTask", "P_ORG", "L_DATA", 23, "Lưu phiên bản, seed, checksum, cấu hình")
    N("G_PUB", "exclusiveGateway", "P_ORG", "L_DATA", 24, "Quyền cho phép xuất bản?")
    N("T_PUB", "serviceTask", "P_ORG", "L_DATA", 25, "Xuất bản kèm nhãn AI, ghi công", row=-1)
    N("T_INT", "serviceTask", "P_ORG", "L_DATA", 25, "Cho tải xuống, nhãn phi thương mại", row=1)
    N("E_PUB", "endEvent", "P_ORG", "L_DATA", 26, "Đã xuất bản", row=-1)
    N("E_INT", "endEvent", "P_ORG", "L_DATA", 26, "Đã lưu, chờ giấy phép", row=1)
    N("ES", "messageStartEvent", "P_EXP", "L_EXP", 19, "Nhận yêu cầu")
    N("ET1", "userTask", "P_EXP", "L_EXP", 20, "Chấm mù 5 tiêu chí văn hoá, thẩm mỹ")
    N("ET2", "userTask", "P_EXP", "L_EXP", 21, "Ghi quyết định và lý do")
    N("EE", "messageEndEvent", "P_EXP", "L_EXP", 22, "Gửi phiếu")
    F = m.flow
    F("S1", "T1")
    F("T1", "T2", enter="top")
    F("T2", "G1")
    F("G1", "T3", "Đạt")
    F("G1", "T1", "Không đạt", exit="bottom", enter="bottom", ch=40)
    F("T3", "G2")
    F("G2", "E_BLOCK", "Bị từ chối", exit="top")
    F("G2", "T3b", "Chưa xác minh", exit="bottom")
    F("G2", "GM", "Hợp lệ")
    F("T3b", "GM", enter="bottom")
    F("GM", "T4", enter="bottom")
    F("T4", "T5")
    F("T5", "TQ1", enter="top")
    F("BE1", "E_ERR", exit="bottom", enter="top")
    F("TQ1", "GQ1")
    F("GQ1", "T6", "Đạt", enter="bottom")
    F("GQ1", "T5", "Không đạt, dưới 3 lần", exit="bottom", enter="bottom", ch=26, edx=-24)
    F("GQ1", "T_ADJ", "Không đạt, đủ 3 lần", exit="top", enter="bottom")
    F("T_ADJ", "T5", exit="left", enter="top")
    F("T6", "T7")
    F("T7", "TQ2", enter="top")
    F("TQ2", "GQ2")
    F("GQ2", "T_CUR", "Đạt", exit="top")
    F("GQ2", "T_REP", "Không đạt", enter="bottom")
    F("GQ2", "T_QC", "Cảnh báo", exit="bottom")
    F("T_REP", "TQ2", exit="left", enter="top", edx=30)
    F("T_QC", "GQ3")
    F("GQ3", "T_CUR", "Chuyển chuyên gia", exit="top", enter="bottom")
    F("GQ3", "T_REP", "Trả về sửa", exit="right", enter="right", ch=40)
    F("T_CUR", "T_SEND", enter="top")
    F("T_SEND", "IC1")
    F("IC1", "GE")
    F("GE", "T_PP", "Đạt", exit="bottom")
    F("GE", "T_LOG", "Cần sửa")
    F("GE", "E_REJ", "Loại", exit="top", enter="left")
    F("T_LOG", "T_EDIT", exit="top", enter="bottom")
    F("T_EDIT", "T_UPL", exit="left", enter="right")
    F("T_UPL", "TQ2", exit="left", enter="top", edx=-30)
    F("T_PP", "T_SAVE")
    F("T_SAVE", "G_PUB")
    F("G_PUB", "T_PUB", "Có", exit="top")
    F("G_PUB", "T_INT", "Chưa", exit="bottom")
    F("T_PUB", "E_PUB")
    F("T_INT", "E_INT")
    F("ES", "ET1")
    F("ET1", "ET2")
    F("ET2", "EE")
    m.msg("T3b", "P_OWN", "Thư đề nghị cấp phép")
    m.msg("T_SEND", "ES", "Yêu cầu thẩm định")
    m.msg("EE", "IC1", "Phiếu thẩm định")
    return m


def as_is() -> Bpmn:
    m = Bpmn("AS-IS")
    m.pool("P_ORG", "Tái Sinh Di Sản Số (bản 09/2026)", [
        ("L_USR", "Người dùng"), ("L_WEB", "Web UI + API"), ("L_AI", "Pipeline AI (GPU)")])
    N = m.node
    N("S1", "startEvent", "P_ORG", "L_USR", 0, "Mở trang")
    N("T1", "userTask", "P_ORG", "L_USR", 1, "Chọn 1 trong 6 hiện vật")
    N("T2", "userTask", "P_ORG", "L_USR", 2, "Bấm Tạo thiết kế")
    N("T3", "serviceTask", "P_ORG", "L_WEB", 3, "Tạo job, chặn job thứ hai (409)")
    N("T4", "serviceTask", "P_ORG", "L_AI", 4, "Sinh 4 hoa văn (seed 42 cố định)")
    N("T5", "serviceTask", "P_ORG", "L_AI", 5, "Chọn bố cục CLIP, ghép, img2img")
    N("T6", "serviceTask", "P_ORG", "L_AI", 6, "Ghi đè ảnh cũ cùng tên tệp")
    N("T7", "serviceTask", "P_ORG", "L_WEB", 7, "Trả 4 ảnh + Similarity của hoa văn")
    N("T8", "userTask", "P_ORG", "L_USR", 8, "Xem 4 thiết kế, mở Passport 4 trường")
    N("E1", "endEvent", "P_ORG", "L_USR", 9, "Kết thúc (không ghi lựa chọn)")
    for a, b in (("S1", "T1"), ("T1", "T2"), ("T2", "T3"), ("T3", "T4"), ("T4", "T5"), ("T5", "T6"), ("T6", "T7"), ("T7", "T8"), ("T8", "E1")):
        m.flow(a, b)
    return m


# ----------------------------------------------------------------- Use Case --

def use_case_svg() -> tuple[str, str]:
    W, H = 1500, 1210
    bx0, by0, bx1, by1 = 230, 40, 1170, 1050
    status_style = {"done": ("#E4EAF2", LAM, ""), "partial": ("#F6ECCF", "#8A6400", "6 4"), "planned": ("#FFFFFF", LINE, "3 4")}
    A, B, C = 400, 715, 1020
    ucs = {
        "UC02": ("Xem danh mục hiện vật", A, 110, "done"),
        "UC01": ("Đăng ký và đăng nhập", A, 220, "planned"),
        "UC15": ("Xem lịch sử chỉnh sửa", A, 330, "done"),
        "UC08": ("Tạo thiết kế áo dài", A, 440, "done"),
        "UC14": ("Quản lý Design Passport", A, 550, "done"),
        "UC03": ("Tải lên hiện vật", A, 660, "partial"),
        "UC16": ("Xuất thiết kế (gắn nhãn AI)", A, 770, "done"),
        "UC17": ("Quản lý người dùng và dữ liệu", A, 985, "planned"),
        "UC11": ("So sánh các phiên bản", B, 220, "done"),
        "UC09": ("Chỉnh sửa thiết kế", B, 440, "done"),
        "UC04": ("Kiểm tra nguồn gốc hiện vật", B, 660, "done"),
        "UC18": ("Kiểm tra quyền sử dụng", B, 770, "done"),
        "UC05": ("Quản lý giấy phép và bản quyền", B, 880, "partial"),
        "UC06": ("Phân tích họa tiết", C, 110, "done"),
        "UC07": ("Sinh họa tiết AI", C, 220, "done"),
        "UC10": ("Đánh giá chất lượng thiết kế", C, 330, "done"),
        "UC19": ("Thử nghiệm có kiểm soát", C, 440, "partial"),
        "UC12": ("Thẩm định chuyên gia", C, 660, "done"),
        "UC13": ("Phê duyệt thiết kế", C, 770, "done"),
    }
    actors = {
        "Guest": ("Khách (Guest)", 100, 120), "RU": ("Người dùng đã đăng ký", 100, 290),
        "DES": ("Nhà thiết kế", 100, 600), "ADM": ("Quản trị viên", 100, 960),
        "AI": ("Hệ thống xử lý AI (GPU)", 1300, 300), "EXP": ("Chuyên gia di sản", 1300, 720),
        "QC": ("QC Officer", 1300, 560),
    }
    assoc = [("Guest", "UC02"), ("RU", "UC01"), ("RU", "UC15"), ("DES", "UC08"), ("DES", "UC14"), ("DES", "UC03"),
             ("DES", "UC16"), ("EXP", "UC12"), ("QC", "UC10"), ("QC", "UC19"), ("QC", "UC13"), ("ADM", "UC05"), ("ADM", "UC17"),
             ("AI", "UC06"), ("AI", "UC07"), ("AI", "UC10"), ("AI", "UC19")]
    rel = [("UC03", "UC04", "include"), ("UC04", "UC18", "include"), ("UC16", "UC18", "include"),
           ("UC08", "UC07", "include"), ("UC07", "UC06", "include"), ("UC08", "UC10", "include"),
           ("UC12", "UC14", "include"), ("UC09", "UC08", "extend"), ("UC05", "UC18", "extend"),
           ("UC11", "UC15", "extend"), ("UC13", "UC12", "extend")]
    gen = [("RU", "Guest"), ("DES", "RU"), ("EXP", "RU"), ("QC", "RU"), ("ADM", "RU")]
    rx, ry = 112, 34
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}" font-size="12.5">',
         '<defs><marker id="open" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">'
         f'<path d="M0,0 L10,5 L0,10" fill="none" stroke="{INK}" stroke-width="1.4"/></marker>'
         '<marker id="tri" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="14" markerHeight="14" orient="auto">'
         f'<path d="M0,0 L12,6 L0,12 z" fill="#fff" stroke="{INK}"/></marker></defs>',
         '<rect width="100%" height="100%" fill="#fff"/>',
         f'<rect x="{bx0}" y="{by0}" width="{bx1 - bx0}" height="{by1 - by0}" rx="6" fill="none" stroke="{INK}" stroke-width="1.5"/>',
         f'<text x="{bx0 + 14}" y="{by0 + 22}" font-weight="700" fill="{INK}">Nền tảng Tái Sinh Di Sản Số (web + API)</text>']

    import math

    def edge_pt(cx, cy, tx, ty, a=rx, b=ry):
        ang = math.atan2((ty - cy) / b, (tx - cx) / a)
        return cx + a * math.cos(ang), cy + b * math.sin(ang)

    def stick(x, y, label, scale=1.0, bold=True):
        k = scale
        out = [f'<circle cx="{x}" cy="{y - 32 * k}" r="{9 * k}" fill="#fff" stroke="{INK}" stroke-width="1.4"/>',
               f'<path d="M{x},{y - 23 * k} v{24 * k} M{x - 15 * k},{y - 12 * k} h{30 * k} M{x},{y + 1 * k} l{-12 * k},{16 * k} M{x},{y + 1 * k} l{12 * k},{16 * k}" stroke="{INK}" stroke-width="1.4" fill="none"/>']
        for i, t in enumerate(wrap(label, 18)):
            out.append(f'<text x="{x}" y="{y + 34 * k + i * 14}" text-anchor="middle" fill="{INK}" font-weight="{600 if bold else 400}" font-size="{12.5 if k == 1 else 11}">{escape(t)}</text>')
        return out

    for a, u in assoc:
        _, ax, ay = actors[a]
        _, ux, uy, _ = ucs[u]
        x1, y1 = (ax + 22 if ux > ax else ax - 22), ay - 10
        x2, y2 = edge_pt(ux, uy, x1, y1)
        o.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{INK}" stroke-width="1.1"/>')
    for s_, t, kind in rel:
        _, sx, sy, _ = ucs[s_]
        _, tx, ty, _ = ucs[t]
        x1, y1 = edge_pt(sx, sy, tx, ty)
        x2, y2 = edge_pt(tx, ty, sx, sy)
        o.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{INK}" stroke-dasharray="6 4" marker-end="url(#open)"/>')
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        o.append(f'<rect x="{mx - 33}" y="{my - 11}" width="66" height="16" fill="#fff"/>')
        o.append(f'<text x="{mx:.0f}" y="{my + 1:.0f}" text-anchor="middle" fill="{LAM if kind == "include" else DAT}" font-size="11">«{kind}»</text>')
    for code, (label, x, y, st) in ucs.items():
        fill, stroke, dash = status_style[st]
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        o.append(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash_attr}/>')
        lines = wrap(label, 22)
        for i, t in enumerate(lines):
            o.append(f'<text x="{x}" y="{y + 7 + (i - (len(lines) - 1) / 2) * 14:.0f}" text-anchor="middle" fill="{INK}">{escape(t)}</text>')
        o.append(f'<text x="{x}" y="{y - ry + 13}" text-anchor="middle" fill="{LINE}" font-size="10">{code}</text>')
    for _, (label, x, y) in actors.items():
        o += stick(x, y, label)
    # Chú giải
    lx, ly = 1215, 1010
    o.append(f'<text x="{lx}" y="{ly}" font-weight="700" fill="{INK}">Chú giải</text>')
    for i, (st, text) in enumerate((("done", "Đã triển khai"), ("partial", "Một phần (qua tệp/dòng lệnh)"), ("planned", "Kế hoạch, chưa triển khai"))):
        fill, stroke, dash = status_style[st]
        yy = ly + 22 + i * 28
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        o.append(f'<ellipse cx="{lx + 22}" cy="{yy}" rx="20" ry="10" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash_attr}/>')
        o.append(f'<text x="{lx + 50}" y="{yy + 4}" fill="{INK}" font-size="11.5">{text}</text>')
    o.append(f'<text x="{lx}" y="{ly + 118}" fill="{INK}" font-size="11.5">Nét đứt, mũi tên mở: «include» / «extend»</text>')
    # Kế thừa tác nhân (generalization) — vẽ riêng ở dải dưới cho dễ đọc
    gy = 1150
    o.append(f'<text x="{bx0}" y="{gy - 62}" font-weight="700" fill="{INK}">Kế thừa tác nhân</text>')
    o += stick(330, gy, "Khách", 0.6, False)
    o += stick(560, gy, "Người dùng đã đăng ký", 0.6, False)
    o.append(f'<line x1="{560 - 20}" y1="{gy - 14}" x2="{330 + 22}" y2="{gy - 14}" stroke="{INK}" marker-end="url(#tri)"/>')
    roles = ["Nhà thiết kế", "Chuyên gia di sản", "QC Officer", "Quản trị viên"]
    xs = [780, 900, 1020, 1140]
    for x, r in zip(xs, roles):
        o += stick(x, gy, r, 0.6, False)
        o.append(f'<line x1="{x}" y1="{gy - 38}" x2="{x}" y2="{gy - 50}" stroke="{INK}"/>')
    o.append(f'<line x1="{xs[0]}" y1="{gy - 50}" x2="{xs[-1]}" y2="{gy - 50}" stroke="{INK}"/>')
    o.append(f'<line x1="{xs[0]}" y1="{gy - 50}" x2="{xs[0] - 60}" y2="{gy - 50}" stroke="{INK}"/>')
    o.append(f'<line x1="{xs[0] - 60}" y1="{gy - 50}" x2="{xs[0] - 60}" y2="{gy - 14}" stroke="{INK}"/>')
    o.append(f'<line x1="{xs[0] - 60}" y1="{gy - 14}" x2="{560 + 22}" y2="{gy - 14}" stroke="{INK}" marker-end="url(#tri)"/>')
    o.append("</svg>")

    puml = ["@startuml", "left to right direction", "skinparam packageStyle rectangle",
            'actor "Khách (Guest)" as Guest', 'actor "Người dùng đã đăng ký" as RU', 'actor "Nhà thiết kế" as DES',
            'actor "Chuyên gia di sản" as EXP', 'actor "QC Officer" as QC', 'actor "Quản trị viên" as ADM',
            'actor "Hệ thống xử lý AI (GPU)" as AI', "RU --|> Guest", "DES --|> RU", "EXP --|> RU", "QC --|> RU", "ADM --|> RU",
            'rectangle "Nền tảng Tái Sinh Di Sản Số (web + API)" {']
    for code, (label, *_rest) in ucs.items():
        puml.append(f'  usecase "{label}" as {code}')
    puml.append("}")
    puml += [f"{a} -- {u}" for a, u in assoc]
    puml += [f"{s_} .> {t} : <<{k}>>" for s_, t, k in rel]
    puml.append("@enduml")
    return "\n".join(o), "\n".join(puml)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, model, title in (("to_be", to_be(), "BPMN 2.0 TO-BE — Tái Sinh Di Sản Số (vòng chung kết)"),
                               ("as_is", as_is(), "BPMN 2.0 AS-IS — luồng sản phẩm bản 09/2026 (trước cải tiến)")):
        model.layout()
        (OUT / f"tsds_{name}.bpmn").write_text(model.to_xml(), encoding="utf-8")
        (OUT / f"bpmn_{name}.svg").write_text(model.to_svg(title), encoding="utf-8")
    svg, puml = use_case_svg()
    (OUT / "use_case.svg").write_text(svg, encoding="utf-8")
    (OUT / "use_case.puml").write_text(puml, encoding="utf-8")
    print("Đã sinh:", ", ".join(sorted(p.name for p in OUT.iterdir())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
