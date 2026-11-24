# -*- coding: utf-8 -*-
"""Bộ dựng BPMN 2.0 XML có DI (làn dọc, luồng chạy từ trên xuống) và màu theo chuẩn BPMN in Color.

Mỗi nút đặt theo lưới: (lane, bước, cột phụ). "Bước" là vị trí theo chiều dọc (thứ tự thời gian), "cột phụ" là vị trí
ngang trong lane. Đường nối vuông góc; có thể chỉ định cạnh ra/vào và kênh trung gian.
Tệp mở được bằng Camunda Modeler, bpmn.io; ảnh dựng bằng bpmn-js (render.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from xml.sax.saxutils import escape as _esc


def escape(text):
    return _esc(str(text), {'"': '&quot;'})


STEP = 128           # khoảng cách giữa hai bước (dọc)
ROWW = 200           # bề rộng một cột phụ trong lane
POOLHEAD = 34        # chiều cao tiêu đề pool
LANEHEAD = 34        # chiều cao tiêu đề lane
Y0 = 30              # lề trên phần nội dung
BBW = 64             # bề rộng pool hộp đen
SIZES = {"task": (164, 92), "event": (36, 36), "gateway": (50, 50), "data": (36, 50), "store": (50, 50)}
TASKS = {"task", "userTask", "serviceTask", "manualTask", "businessRuleTask", "sendTask", "receiveTask",
         "scriptTask", "subProcess", "callActivity"}
EVENTS = {"startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent", "boundaryEvent"}
GATEWAYS = {"exclusiveGateway", "parallelGateway", "inclusiveGateway", "eventBasedGateway"}

# Màu: người (vàng), hệ thống (lam), quy tắc nghiệp vụ (tím), đề xuất mới (xanh lá), bên ngoài (xám), lỗi (đỏ)
COLORS = {
    "human": ("#FFF4D6", "#8A6100"),
    "system": ("#E4EEF9", "#1F5A99"),
    "rule": ("#EEE8FA", "#5A3E99"),
    "new": ("#E1F3E4", "#2E7D32"),
    "external": ("#F2F2F2", "#5F6368"),
    "error": ("#FCE8E6", "#B3261E"),
    "data": ("#FFFFFF", "#455A64"),
}


def kind_of(t: str) -> str:
    if t in TASKS:
        return "task"
    if t in EVENTS:
        return "event"
    if t in GATEWAYS:
        return "gateway"
    if t == "dataObjectReference":
        return "data"
    if t == "dataStoreReference":
        return "store"
    raise ValueError(t)


@dataclass
class Node:
    id: str
    type: str
    name: str
    pool: str
    lane: str | None
    step: float
    row: float = 0
    ev: str | None = None             # message | timer | error | conditional | signal | terminate
    attach: str | None = None
    attach_side: str = "bottom"
    multi: str | None = None          # sequential | parallel
    color: str | None = None
    timer: str | None = None
    error_name: str | None = None
    default: str | None = None
    interrupting: bool = True
    label: str = "right"              # vị trí nhãn của sự kiện/cổng: right | left | below | above
    x: float = 0
    y: float = 0
    w: float = 0
    h: float = 0


@dataclass
class Flow:
    id: str
    src: str
    dst: str
    name: str = ""
    cond: str | None = None
    exit: str | None = None
    enter: str | None = None
    via: list | None = None
    message: bool = False
    assoc: str | None = None
    offset: float = 0                 # thông điệp tới pool hộp đen: lệch dọc
    eoff: float = 0                   # lệch điểm vào so với tâm cạnh đích


@dataclass
class Pool:
    id: str
    name: str
    lanes: list
    black_box: bool = False
    side: str = "right"
    multi: bool = False


class Diagram:
    def __init__(self, id: str, title: str):
        self.id, self.title = id, title
        self.pools: list[Pool] = []
        self.nodes: dict[str, Node] = {}
        self.flows: list[Flow] = []
        self.errors: dict[str, str] = {}
        self.box, self.lane_box = {}, {}

    def pool(self, id, name, lanes=None, black_box=False, side="right", multi=False):
        self.pools.append(Pool(id, name, lanes or [], black_box, side, multi))

    def n(self, id, type, name, pool, lane, step, row=0, **kw):
        node = Node(id, type, name, pool, lane, step, row, **kw)
        self.nodes[id] = node
        return node

    def f(self, src, dst, name="", **kw):
        self.flows.append(Flow(f"Flow_{src}_{dst}", src, dst, name, **kw))

    def m(self, src, dst, name="", **kw):
        self.flows.append(Flow(f"Msg_{src}_{dst}", src, dst, name, message=True, **kw))

    def d(self, src, dst, **kw):
        direction = "out" if self.nodes[dst].type in ("dataStoreReference", "dataObjectReference") else "in"
        self.flows.append(Flow(f"Data_{src}_{dst}", src, dst, assoc=direction, **kw))

    # ---------------------------------------------------------------- bố cục
    def layout(self):
        steps = [n.step for n in self.nodes.values()]
        nsteps = (max(steps) + 1) if steps else 1
        top = 20
        height = POOLHEAD + LANEHEAD + Y0 + nsteps * STEP + 30
        x = 20
        order = [p for p in self.pools if p.black_box and p.side == "left"] + \
                [p for p in self.pools if not p.black_box] + \
                [p for p in self.pools if p.black_box and p.side == "right"]
        for p in order:
            if p.black_box:
                self.box[p.id] = (x, top, BBW, height)
                x += BBW + 130
                continue
            x0 = x
            for lid, _ in p.lanes:
                rows = [n.row for n in self.nodes.values() if n.lane == lid and not n.attach]
                lo, hi = (min(rows), max(rows)) if rows else (0, 0)
                w = (hi - lo + 1) * ROWW + 16
                self.lane_box[lid] = (x, top + POOLHEAD, w, height - POOLHEAD, lo)
                x += w
            self.box[p.id] = (x0, top, x - x0, height)
            x += 130
        self.width, self.height = x, top + height + 20
        for n in self.nodes.values():
            n.w, n.h = SIZES[kind_of(n.type)]
            if n.attach:
                continue
            lx, ly, lw, lh, lo = self.lane_box[n.lane]
            cx = lx + 8 + (n.row - lo) * ROWW + ROWW / 2
            cy = top + POOLHEAD + LANEHEAD + Y0 + n.step * STEP + 40
            n.x, n.y = cx - n.w / 2, cy - n.h / 2
        for n in self.nodes.values():
            if n.attach:
                t = self.nodes[n.attach]
                if n.attach_side == "bottom":
                    n.x, n.y = t.x + t.w - n.w - 6, t.y + t.h - n.h / 2
                elif n.attach_side == "right":
                    n.x, n.y = t.x + t.w - n.w / 2, t.y + t.h - n.h - 4
                else:
                    n.x, n.y = t.x - n.w / 2, t.y + t.h - n.h - 4
                n.lane = t.lane

    # tiện ích toạ độ cho kênh trung gian (gọi sau layout)
    def fy(self, step):
        return 20 + POOLHEAD + LANEHEAD + Y0 + step * STEP + 40

    def lx(self, lane, row=0):
        lx, ly, lw, lh, lo = self.lane_box[lane]
        return lx + 8 + (row - lo) * ROWW + ROWW / 2

    def lane_left(self, lane):
        return self.lane_box[lane][0]

    def lane_right(self, lane):
        b = self.lane_box[lane]
        return b[0] + b[2]

    # ---------------------------------------------------------------- đường nối
    @staticmethod
    def port(n: Node, side: str):
        cx, cy = n.x + n.w / 2, n.y + n.h / 2
        return {"right": (n.x + n.w, cy), "left": (n.x, cy), "top": (cx, n.y), "bottom": (cx, n.y + n.h)}[side]

    def route(self, fl: Flow):
        if fl.message and (fl.dst in self.box or fl.src in self.box):
            node = self.nodes[fl.src if fl.dst in self.box else fl.dst]
            bx, by, bw, bh = self.box[fl.dst if fl.dst in self.box else fl.src]
            y = node.y + node.h / 2 + fl.offset
            if bx > node.x:
                a, b = (node.x + node.w, y), (bx, y)
            else:
                a, b = (node.x, y), (bx + bw, y)
            return [a, b] if fl.dst in self.box else [b, a]
        a, b = self.nodes[fl.src], self.nodes[fl.dst]
        acx, acy = a.x + a.w / 2, a.y + a.h / 2
        bcx, bcy = b.x + b.w / 2, b.y + b.h / 2
        if fl.message:
            ex = fl.exit or ("right" if bcx > acx else "left")
            en = fl.enter or ("left" if bcx > acx else "right")
        elif bcy > acy + 5:
            ex, en = fl.exit or "bottom", fl.enter or "top"
        elif abs(bcy - acy) <= 5:
            ex, en = (fl.exit or "right", fl.enter or "left") if bcx > acx else (fl.exit or "left", fl.enter or "right")
        else:
            ex, en = fl.exit or "left", fl.enter or "left"
        p1, p2 = self.port(a, ex), self.port(b, en)
        if fl.eoff:
            p2 = (p2[0], p2[1] + fl.eoff) if en in ("left", "right") else (p2[0] + fl.eoff, p2[1])
        pts = [p1]
        if fl.via:
            for v in fl.via:
                if callable(v):
                    v = v(self)
                last = pts[-1]
                if v[0] == "y":            # đi dọc tới tung độ y
                    pts.append((last[0], v[1]))
                elif v[0] == "x":          # đi ngang tới hoành độ x
                    pts.append((v[1], last[1]))
                else:
                    pts.append(v)
            last = pts[-1]
            if abs(last[0] - p2[0]) > 0.5 and abs(last[1] - p2[1]) > 0.5:
                pts.append((p2[0], last[1]) if en in ("top", "bottom") else (last[0], p2[1]))
            pts.append(p2)
        else:
            horiz_out, horiz_in = ex in ("left", "right"), en in ("left", "right")
            if horiz_out and horiz_in:
                if ex == en:
                    xx = (max(p1[0], p2[0]) + 30) if ex == "right" else (min(p1[0], p2[0]) - 30)
                    pts += [(xx, p1[1]), (xx, p2[1]), p2]
                elif abs(p1[1] - p2[1]) < 1:
                    pts.append(p2)
                else:
                    mx = (p1[0] + p2[0]) / 2
                    pts += [(mx, p1[1]), (mx, p2[1]), p2]
            elif horiz_out and not horiz_in:
                pts += [(p2[0], p1[1]), p2]
            elif not horiz_out and horiz_in:
                pts += [(p1[0], p2[1]), p2]
            else:
                if ex == en:
                    yy = (max(p1[1], p2[1]) + 30) if ex == "bottom" else (min(p1[1], p2[1]) - 30)
                    pts += [(p1[0], yy), (p2[0], yy), p2]
                elif abs(p1[0] - p2[0]) < 1:
                    pts.append(p2)
                else:
                    my = (p1[1] + p2[1]) / 2
                    pts += [(p1[0], my), (p2[0], my), p2]
        clean = [pts[0]]
        for p in pts[1:]:
            if abs(p[0] - clean[-1][0]) > 0.5 or abs(p[1] - clean[-1][1]) > 0.5:
                clean.append(p)
        return clean

    # ---------------------------------------------------------------- XML
    def to_xml(self) -> str:
        self.layout()
        X = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
             'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" '
             'xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
             'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" '
             'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
             'xmlns:color="http://www.omg.org/spec/BPMN/non-normative/color/1.0" '
             f'id="Defs_{self.id}" targetNamespace="https://tai-sinh-di-san-so/bpmn/{self.id}" '
             'exporter="tsds-ba-kit" exporterVersion="2.0">']
        errs = sorted({n.error_name for n in self.nodes.values() if n.ev == "error" and n.error_name})
        for i, e in enumerate(errs, 1):
            self.errors[e] = f"Error_{i}"
            X.append(f'  <bpmn:error id="Error_{i}" name="{escape(e)}" errorCode="{escape(e)}"/>')
        for s in (n for n in self.nodes.values() if n.type == "dataStoreReference"):
            X.append(f'  <bpmn:dataStore id="Store_{s.id}" name="{escape(s.name)}"/>')
        msgs = [fl for fl in self.flows if fl.message]
        X.append(f'  <bpmn:collaboration id="Collab_{self.id}">')
        for p in self.pools:
            ref = "" if p.black_box else f' processRef="Proc_{p.id}"'
            inner = '<bpmn:participantMultiplicity minimum="2" maximum="5"/>' if p.multi else ""
            X.append(f'    <bpmn:participant id="{p.id}" name="{escape(p.name)}"{ref}>{inner}</bpmn:participant>')
        for fl in msgs:
            X.append(f'    <bpmn:messageFlow id="{fl.id}" name="{escape(fl.name)}" sourceRef="{fl.src}" targetRef="{fl.dst}"/>')
        X.append('  </bpmn:collaboration>')
        for p in self.pools:
            if p.black_box:
                continue
            X.append(f'  <bpmn:process id="Proc_{p.id}" name="{escape(p.name)}" isExecutable="false">')
            pn = [n for n in self.nodes.values() if n.pool == p.id]
            if p.lanes:
                X.append(f'    <bpmn:laneSet id="LaneSet_{p.id}">')
                for lid, lname in p.lanes:
                    X.append(f'      <bpmn:lane id="{lid}" name="{escape(lname)}">')
                    X += [f'        <bpmn:flowNodeRef>{n.id}</bpmn:flowNodeRef>' for n in pn
                          if n.type not in ("dataStoreReference", "dataObjectReference") and n.lane == lid]
                    X.append('      </bpmn:lane>')
                X.append('    </bpmn:laneSet>')
            seq = [fl for fl in self.flows if not fl.message and not fl.assoc and self.nodes[fl.src].pool == p.id]
            X += [self._node_xml(n, seq) for n in pn]
            for fl in seq:
                if fl.cond:
                    X.append(f'    <bpmn:sequenceFlow id="{fl.id}" name="{escape(fl.name)}" sourceRef="{fl.src}" targetRef="{fl.dst}">'
                             f'<bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">{escape(fl.cond)}</bpmn:conditionExpression>'
                             '</bpmn:sequenceFlow>')
                else:
                    X.append(f'    <bpmn:sequenceFlow id="{fl.id}" name="{escape(fl.name)}" sourceRef="{fl.src}" targetRef="{fl.dst}"/>')
            X.append('  </bpmn:process>')
        X.append(self._di())
        X.append('</bpmn:definitions>')
        return "\n".join(X) + "\n"

    def _node_xml(self, n: Node, seq) -> str:
        if n.type == "dataStoreReference":
            return f'    <bpmn:dataStoreReference id="{n.id}" name="{escape(n.name)}" dataStoreRef="Store_{n.id}"/>'
        if n.type == "dataObjectReference":
            return (f'    <bpmn:dataObject id="DO_{n.id}"/>\n'
                    f'    <bpmn:dataObjectReference id="{n.id}" name="{escape(n.name)}" dataObjectRef="DO_{n.id}"/>')
        attrs = f'id="{n.id}" name="{escape(n.name)}"'
        if n.type == "boundaryEvent":
            attrs += f' attachedToRef="{n.attach}"' + ('' if n.interrupting else ' cancelActivity="false"')
        if n.default:
            attrs += f' default="Flow_{n.id}_{n.default}"'
        inner = [f'<bpmn:incoming>{fl.id}</bpmn:incoming>' for fl in seq if fl.dst == n.id]
        inner += [f'<bpmn:outgoing>{fl.id}</bpmn:outgoing>' for fl in seq if fl.src == n.id]
        ins = [fl for fl in self.flows if fl.assoc == "in" and fl.dst == n.id]
        outs = [fl for fl in self.flows if fl.assoc == "out" and fl.src == n.id]
        if ins:
            inner.append(f'<bpmn:property id="Prop_{n.id}" name="__targetRef_placeholder"/>')
            inner += [f'<bpmn:dataInputAssociation id="{fl.id}"><bpmn:sourceRef>{fl.src}</bpmn:sourceRef>'
                      f'<bpmn:targetRef>Prop_{n.id}</bpmn:targetRef></bpmn:dataInputAssociation>' for fl in ins]
        inner += [f'<bpmn:dataOutputAssociation id="{fl.id}"><bpmn:targetRef>{fl.dst}</bpmn:targetRef></bpmn:dataOutputAssociation>'
                  for fl in outs]
        if n.multi:
            inner.append('<bpmn:multiInstanceLoopCharacteristics' + (' isSequential="true"' if n.multi == "sequential" else "") + '/>')
        ev = n.ev
        if ev == "message":
            inner.append(f'<bpmn:messageEventDefinition id="MED_{n.id}"/>')
        elif ev == "timer":
            inner.append(f'<bpmn:timerEventDefinition id="TED_{n.id}"><bpmn:timeDuration xsi:type="bpmn:tFormalExpression">'
                         f'{escape(n.timer or "PT1H")}</bpmn:timeDuration></bpmn:timerEventDefinition>')
        elif ev == "error":
            ref = f' errorRef="{self.errors[n.error_name]}"' if n.error_name in self.errors else ""
            inner.append(f'<bpmn:errorEventDefinition id="EED_{n.id}"{ref}/>')
        elif ev == "conditional":
            inner.append(f'<bpmn:conditionalEventDefinition id="CED_{n.id}"><bpmn:condition xsi:type="bpmn:tFormalExpression">'
                         f'{escape(n.timer or "true")}</bpmn:condition></bpmn:conditionalEventDefinition>')
        elif ev == "terminate":
            inner.append(f'<bpmn:terminateEventDefinition id="TerED_{n.id}"/>')
        elif ev == "signal":
            inner.append(f'<bpmn:signalEventDefinition id="SED_{n.id}"/>')
        return f'    <bpmn:{n.type} {attrs}>' + "".join(inner) + f'</bpmn:{n.type}>'

    def _color(self, n: Node) -> str:
        c = n.color
        if c is None:
            if n.type in ("userTask", "manualTask"):
                c = "human"
            elif n.type == "businessRuleTask":
                c = "rule"
            elif n.type in ("serviceTask", "sendTask", "receiveTask", "scriptTask", "subProcess"):
                c = "system"
            elif n.ev == "error" and n.type == "endEvent":
                c = "error"
            elif n.type in ("dataStoreReference", "dataObjectReference"):
                c = "data"
        if not c:
            return ""
        fill, stroke = COLORS[c]
        return f' color:background-color="{fill}" color:border-color="{stroke}"'

    def _label_bounds(self, n: Node) -> str:
        if not n.name or kind_of(n.type) == "task":
            return ""
        lw, lh = 112, 40
        dy = -18 if kind_of(n.type) == "gateway" else 0
        if n.label == "right":
            lx, ly = n.x + n.w + 6, n.y + n.h / 2 - lh / 2 + dy
        elif n.label == "left":
            lx, ly = n.x - lw - 6, n.y + n.h / 2 - lh / 2 + dy
        elif n.label == "belowleft":
            lx, ly = n.x - lw + 8, n.y + n.h - 2
        elif n.label == "belowright":
            lx, ly = n.x + n.w - 8, n.y + n.h - 2
        elif n.label == "above":
            lx, ly = n.x + n.w / 2 - lw / 2, n.y - lh - 2
        else:
            lx, ly = n.x + n.w / 2 - lw / 2, n.y + n.h + 4
        return f'<bpmndi:BPMNLabel><dc:Bounds x="{lx:.0f}" y="{ly:.0f}" width="{lw}" height="{lh}"/></bpmndi:BPMNLabel>'

    def _di(self) -> str:
        D = [f'  <bpmndi:BPMNDiagram id="Diagram_{self.id}" name="{escape(self.title)}">',
             f'    <bpmndi:BPMNPlane id="Plane_{self.id}" bpmnElement="Collab_{self.id}">']
        for p in self.pools:
            x, y, w, h = self.box[p.id]
            col = ""
            if p.black_box:
                fill, stroke = COLORS["external"]
                col = f' color:background-color="{fill}" color:border-color="{stroke}"'
            D.append(f'      <bpmndi:BPMNShape id="{p.id}_di" bpmnElement="{p.id}" isHorizontal="false"{col}>'
                     f'<dc:Bounds x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}"/></bpmndi:BPMNShape>')
            for lid, _ in p.lanes:
                lx, ly, lw, lh, _lo = self.lane_box[lid]
                D.append(f'      <bpmndi:BPMNShape id="{lid}_di" bpmnElement="{lid}" isHorizontal="false">'
                         f'<dc:Bounds x="{lx:.0f}" y="{ly:.0f}" width="{lw:.0f}" height="{lh:.0f}"/></bpmndi:BPMNShape>')
        for n in self.nodes.values():
            extra = ' isExpanded="false"' if n.type == "subProcess" else ""
            D.append(f'      <bpmndi:BPMNShape id="{n.id}_di" bpmnElement="{n.id}"{extra}{self._color(n)}>'
                     f'<dc:Bounds x="{n.x:.0f}" y="{n.y:.0f}" width="{n.w:.0f}" height="{n.h:.0f}"/>{self._label_bounds(n)}'
                     '</bpmndi:BPMNShape>')
        for fl in self.flows:
            pts = self.route(fl)
            wp = "".join(f'<di:waypoint x="{x:.0f}" y="{y:.0f}"/>' for x, y in pts)
            label = ""
            if fl.name and not fl.assoc:
                (x1, y1), (x2, y2) = (pts[-2], pts[-1]) if fl.message else (pts[0], pts[1])
                if fl.message:
                    lx, ly = min(x1, x2) + 12, y1 - 30
                elif abs(y1 - y2) < 1:
                    lx, ly = min(x1, x2) + 8, y1 - 30
                else:
                    lx, ly = x1 + 6, min(y1, y2) + 4
                label = f'<bpmndi:BPMNLabel><dc:Bounds x="{lx:.0f}" y="{ly:.0f}" width="104" height="28"/></bpmndi:BPMNLabel>'
            D.append(f'      <bpmndi:BPMNEdge id="{fl.id}_di" bpmnElement="{fl.id}">{wp}{label}</bpmndi:BPMNEdge>')
        D += ['    </bpmndi:BPMNPlane>', '  </bpmndi:BPMNDiagram>']
        return "\n".join(D)

    # ---------------------------------------------------------------- số liệu mô hình (đếm phần tử, không phải đo thực tế)
    def stats(self) -> dict:
        nodes = [n for n in self.nodes.values() if n.type not in ("dataStoreReference", "dataObjectReference")]
        tasks = [n for n in nodes if kind_of(n.type) == "task"]
        human = [n for n in tasks if n.type in ("userTask", "manualTask")]
        seq = [fl for fl in self.flows if not fl.message and not fl.assoc]
        lane = {n.id: n.lane for n in nodes}
        human_lanes = {n.lane for n in human}
        handoffs = sum(1 for fl in seq if lane.get(fl.src) and lane.get(fl.dst) and lane[fl.src] != lane[fl.dst]
                       and (lane[fl.src] in human_lanes or lane[fl.dst] in human_lanes))
        return {"tasks": len(tasks), "human": len(human), "auto": len(tasks) - len(human),
                "gateways": sum(1 for n in nodes if kind_of(n.type) == "gateway"),
                "ends": sum(1 for n in nodes if n.type == "endEvent"),
                "handoffs": handoffs, "messages": sum(1 for fl in self.flows if fl.message),
                "pools": len(self.pools), "lanes": sum(len(p.lanes) for p in self.pools)}
