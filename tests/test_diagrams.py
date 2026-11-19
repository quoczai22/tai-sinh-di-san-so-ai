# -*- coding: utf-8 -*-
"""BPMN 2.0 và Use Case: kiểm tra ngữ nghĩa, không chỉ kiểm tra tệp tồn tại."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "docs" / "finals" / "diagrams"
NS = {"b": "http://www.omg.org/spec/BPMN/20100524/MODEL", "di": "http://www.omg.org/spec/BPMN/20100524/DI"}


def _load(name):
    return ET.parse(D / name).getroot()


def _owner_process(root):
    owner = {}
    for proc in root.findall("b:process", NS):
        for el in proc.iter():
            if el.get("id"):
                owner[el.get("id")] = proc.get("id")
    return owner


def test_to_be_has_required_bpmn_elements():
    r = _load("tsds_to_be.bpmn")
    for tag in ("startEvent", "endEvent", "userTask", "serviceTask", "manualTask", "sendTask",
                "exclusiveGateway", "sequenceFlow", "boundaryEvent"):
        assert r.findall(f".//b:{tag}", NS), f"thiếu {tag}"
    assert r.findall(".//b:boundaryEvent/b:errorEventDefinition", NS), "thiếu nhánh lỗi (error boundary)"
    assert len(r.findall(".//b:messageFlow", NS)) >= 3


def test_required_lanes_present():
    r = _load("tsds_to_be.bpmn")
    names = " | ".join(l.get("name") or "" for l in r.findall(".//b:lane", NS)) + " | " + \
            " | ".join(p.get("name") or "" for p in r.findall(".//b:participant", NS))
    for needle in ("Nhà thiết kế", "Hệ thống AI", "Kiểm soát chất lượng", "Dữ liệu và Passport", "chuyên gia"):
        assert needle.lower() in names.lower(), needle


@pytest.mark.parametrize("name", ["tsds_to_be.bpmn", "tsds_as_is.bpmn"])
def test_flows_reference_existing_nodes_and_stay_in_process(name):
    r = _load(name)
    owner = _owner_process(r)
    for f in r.findall(".//b:sequenceFlow", NS):
        s, t = f.get("sourceRef"), f.get("targetRef")
        assert s in owner and t in owner, f.get("id")
        assert owner[s] == owner[t], f"sequence flow {f.get('id')} vượt pool"
    participants = {p.get("id"): p.get("processRef") for p in r.findall(".//b:participant", NS)}
    for m in r.findall(".//b:messageFlow", NS):
        s, t = m.get("sourceRef"), m.get("targetRef")
        ps = owner.get(s) or participants.get(s)
        pt = owner.get(t) or participants.get(t)
        assert ps != pt, f"message flow {m.get('id')} phải đi giữa hai pool"


def test_gateways_are_real_decisions():
    r = _load("tsds_to_be.bpmn")
    for proc in r.findall("b:process", NS):
        flows = proc.findall("b:sequenceFlow", NS)
        for g in proc.findall("b:exclusiveGateway", NS):
            out = [f for f in flows if f.get("sourceRef") == g.get("id")]
            inc = [f for f in flows if f.get("targetRef") == g.get("id")]
            assert len(out) >= 2 or len(inc) >= 2, f"gateway trang trí: {g.get('id')}"
            if len(out) >= 2:
                assert all(f.get("name") for f in out), f"nhánh ra của {g.get('id')} phải có điều kiện"


def test_every_node_has_diagram_shape():
    r = _load("tsds_to_be.bpmn")
    shapes = {s.get("bpmnElement") for s in r.findall(".//di:BPMNShape", NS)}
    edges = {e.get("bpmnElement") for e in r.findall(".//di:BPMNEdge", NS)}
    for proc in r.findall("b:process", NS):
        for el in proc:
            tag = el.tag.split("}")[1]
            if tag in ("laneSet",):
                continue
            target = edges if tag == "sequenceFlow" else shapes
            assert el.get("id") in target, f"{el.get('id')} không có hình trong DI"


def test_loops_exist():
    """Có vòng quay lại: G2 → sinh lại, chỉnh sửa thủ công → G3."""
    r = _load("tsds_to_be.bpmn")
    flows = [(f.get("sourceRef"), f.get("targetRef")) for f in r.findall(".//b:sequenceFlow", NS)]
    graph = {}
    for s, t in flows:
        graph.setdefault(s, []).append(t)

    def reachable(a, b):
        seen, stack = set(), [a]
        while stack:
            n = stack.pop()
            if n == b:
                return True
            if n not in seen:
                seen.add(n)
                stack.extend(graph.get(n, []))
        return False
    assert reachable("GQ1", "T5") and reachable("T5", "GQ1")
    assert reachable("T_UPL", "TQ2") and reachable("TQ2", "T_UPL")


def test_use_case_puml():
    txt = (D / "use_case.puml").read_text(encoding="utf-8")
    actors = re.findall(r'^actor "', txt, flags=re.M)
    assert len(actors) == 7
    assert txt.count("<<include>>") >= 5 and txt.count("<<extend>>") >= 3
    assert "--|>" in txt, "thiếu generalization tác nhân"
    for uc in ("Đăng ký và đăng nhập", "Xem danh mục hiện vật", "Tải lên hiện vật", "Kiểm tra nguồn gốc hiện vật",
               "Quản lý giấy phép và bản quyền", "Phân tích họa tiết", "Sinh họa tiết AI", "Tạo thiết kế áo dài",
               "Chỉnh sửa thiết kế", "Đánh giá chất lượng thiết kế", "So sánh các phiên bản", "Thẩm định chuyên gia",
               "Phê duyệt thiết kế", "Quản lý Design Passport", "Xem lịch sử chỉnh sửa", "Xuất thiết kế",
               "Quản lý người dùng và dữ liệu"):
        assert uc in txt, uc
