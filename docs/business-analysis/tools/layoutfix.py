# -*- coding: utf-8 -*-
"""Đo và sửa chữ bị chèn trong sơ đồ BPMN bằng bpmn-js Modeler (đo khung chữ thật đã dựng).

Với mỗi tệp .bpmn:
  1. Nạp vào bpmn-js Modeler.
  2. Đặt lại nhãn ngoài (sự kiện, cổng, kho dữ liệu, luồng): thử nhiều vị trí quanh phần tử, chọn vị trí ít đè nhất
     lên hình, nhãn khác và đường nối (chỉ khi chạy với --fix).
  3. Đo lỗi còn lại: nhãn đè nhãn, nhãn đè hình, nhãn đè đường nối, nhãn đè hoặc sát đường kẻ pool/lane, hai
     đường nối chồng lên nhau, đường nối chạy dọc đường kẻ pool/lane hoặc xuyên qua hình không phải đầu/cuối của nó,
     chữ trong ô bị biểu tượng che hoặc tràn khỏi ô.
  4. --fix: ghi lại .bpmn (DI mới).

    python layoutfix.py <thư mục .bpmn> [--fix]
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/bpmn-js@17.11.1/dist/assets/diagram-js.css">
<link rel="stylesheet" href="https://unpkg.com/bpmn-js@17.11.1/dist/assets/bpmn-js.css">
<script src="https://unpkg.com/bpmn-js@17.11.1/dist/bpmn-modeler.development.js"></script>
<style>html,body{margin:0}#c{width:3000px;height:6000px}</style></head><body><div id="c"></div></body></html>"""

JS = r"""
async ([xml, fix]) => {
  const el = document.getElementById('c'); el.innerHTML = '';
  const m = new BpmnJS({ container: el });
  await m.importXML(xml);
  const reg = m.get('elementRegistry'), modeling = m.get('modeling'), canvas = m.get('canvas');
  canvas.zoom(1, { x: 0, y: 0 });
  const all = reg.getAll();
  const isLabel = e => e.type === 'label';
  const shapes = all.filter(e => !e.waypoints && !isLabel(e) && e.type !== 'bpmn:Process' && e.type !== 'bpmn:Collaboration'
                                && e.type !== 'bpmn:Participant' && e.type !== 'bpmn:Lane' && e.parent);
  const conns = all.filter(e => e.waypoints && e.type !== 'label');
  const parts = all.filter(e => e.type === 'bpmn:Participant');
  const rect = e => ({ x: e.x, y: e.y, w: e.width, h: e.height });
  const ov = (a, b) => Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x)) * Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));
  const pad = r => ({ x: r.x - 5, y: r.y - 3, w: r.w + 10, h: r.h + 6 });  // chừa khoảng thở với đường kẻ pool/lane
  const segHit = (r, p, q) => {  // đoạn thẳng (gần như vuông góc) cắt hình chữ nhật r (thu nhỏ 1px)
    const x1 = Math.min(p.x, q.x), x2 = Math.max(p.x, q.x), y1 = Math.min(p.y, q.y), y2 = Math.max(p.y, q.y);
    return x2 >= r.x + 1 && x1 <= r.x + r.w - 1 && y2 >= r.y + 1 && y1 <= r.y + r.h - 1;
  };
  const inPart = r => parts.some(p => r.x >= p.x + 2 && r.y >= p.y + 36 && r.x + r.w <= p.x + p.width - 2 && r.y + r.h <= p.y + p.height - 2);
  const labels = all.filter(isLabel);
  const pos = new Map(labels.map(l => [l.id, rect(l)]));
  // đường kẻ của pool và lane (biên dọc, vạch dưới tiêu đề)
  const rules = [];
  for (const e of all.filter(e => e.type === 'bpmn:Lane' || e.type === 'bpmn:Participant')) {
    rules.push([{ x: e.x, y: e.y }, { x: e.x, y: e.y + e.height }], [{ x: e.x + e.width, y: e.y }, { x: e.x + e.width, y: e.y + e.height }]);
    rules.push([{ x: e.x, y: e.y + 30 }, { x: e.x + e.width, y: e.y + 30 }]);
  }

  function cost(l, r) {
    let c = 0;
    const owner = l.labelTarget;
    for (const s of shapes) { const a = ov(r, rect(s)); if (a) c += a * (s === owner ? 3 : 2) + 400; }
    for (const o of labels) { if (o === l) continue; const a = ov(r, pos.get(o.id)); if (a) c += a * 3 + 400; }
    for (const cn of conns) { const wp = cn.waypoints; for (let i = 0; i < wp.length - 1; i++) if (segHit(r, wp[i], wp[i + 1])) c += (cn === owner ? 250 : 500); }
    for (const [p, q] of rules) if (segHit(pad(r), p, q)) c += 450;
    if (!inPart(r)) c += 5000;
    return c;
  }
  function candidates(l) {
    const w = l.width, h = l.height, t = l.labelTarget, out = [];
    if (t.waypoints) {
      const wp = t.waypoints;
      for (let i = 0; i < wp.length - 1; i++) {
        const p = wp[i], q = wp[i + 1], len = Math.hypot(q.x - p.x, q.y - p.y);
        if (len < 24) continue;
        const near = i === 0 ? 0 : 30 * i;           // ưu tiên gần điểm xuất phát
        for (const f of [0.15, 0.5, 0.85]) {
          const mx = p.x + (q.x - p.x) * f, my = p.y + (q.y - p.y) * f;
          if (Math.abs(p.y - q.y) < 1) { out.push([mx - w / 2, my - h - 4, near]); out.push([mx - w / 2, my + 4, near + 5]); }
          else { out.push([mx + 6, my - h / 2, near]); out.push([mx - w - 6, my - h / 2, near + 5]); }
        }
      }
    } else {
      const x = t.x, y = t.y, W = t.width, H = t.height;
      for (const [g, pen] of [[5, 0], [24, 25], [44, 50]]) {
        out.push([x + W + g, y + H / 2 - h / 2, pen], [x - w - g, y + H / 2 - h / 2, pen + 2], [x + W / 2 - w / 2, y + H + g, pen + 1],
                 [x + W / 2 - w / 2, y - h - g, pen + 3], [x + W + g, y - h - g + 5, pen + 2], [x + W + g, y + H + g - 5, pen + 2],
                 [x - w - g, y - h - g + 5, pen + 4], [x - w - g, y + H + g - 5, pen + 4]);
      }
    }
    return out;
  }
  if (fix) {
    for (let pass = 0; pass < 3; pass++) {
      for (const l of labels) {
        let best = null;
        for (const [cx, cy, pen] of candidates(l)) {
          const r = { x: cx, y: cy, w: l.width, h: l.height };
          const c = cost(l, r) + pen;
          if (!best || c < best.c) best = { c, r };
        }
        const cur = pos.get(l.id);
        if (best && cost(l, best.r) < cost(l, cur)) pos.set(l.id, best.r);
      }
    }
    for (const l of labels) { const r = pos.get(l.id); const dx = Math.round(r.x - l.x), dy = Math.round(r.y - l.y);
      if (dx || dy) modeling.moveShape(l, { x: dx, y: dy }, l.parent, { layout: false }); }
  }
  // ---- đo lỗi còn lại
  const issues = [];
  const name = e => (e.businessObject && e.businessObject.name) || e.id;
  for (const l of labels) {
    const r = rect(l), owner = l.labelTarget;
    for (const s of shapes) if (ov(r, rect(s)) > 4) issues.push(`nhãn "${name(owner)}" đè lên "${name(s)}"`);
    for (const o of labels) if (o.id < l.id && ov(r, rect(o)) > 4) issues.push(`nhãn "${name(owner)}" đè nhãn "${name(o.labelTarget)}"`);
    for (const cn of conns) { const wp = cn.waypoints; for (let i = 0; i < wp.length - 1; i++)
      if (segHit(r, wp[i], wp[i + 1])) { issues.push(`nhãn "${name(owner)}" đè đường ${cn === owner ? '(của chính nó)' : cn.id}`); break; } }
  }
  for (const l of labels) { const r = rect(l);
    for (const [p, q] of rules) if (segHit(pad(r), p, q)) { issues.push(`nhãn "${name(l.labelTarget)}" đè đường kẻ pool/lane`); break; } }
  // hai đường nối chồng lên nhau trên cùng một đoạn
  for (let i = 0; i < conns.length; i++) for (let j = i + 1; j < conns.length; j++) {
    const A = conns[i].waypoints, B = conns[j].waypoints; let hit = false;
    for (let a = 0; a < A.length - 1 && !hit; a++) for (let b = 0; b < B.length - 1 && !hit; b++) {
      const p = A[a], q = A[a + 1], u = B[b], v = B[b + 1];
      if (Math.abs(p.y - q.y) < 1 && Math.abs(u.y - v.y) < 1 && Math.abs(p.y - u.y) < 3) {
        const o = Math.min(Math.max(p.x, q.x), Math.max(u.x, v.x)) - Math.max(Math.min(p.x, q.x), Math.min(u.x, v.x)); if (o > 10) hit = true; }
      if (Math.abs(p.x - q.x) < 1 && Math.abs(u.x - v.x) < 1 && Math.abs(p.x - u.x) < 3) {
        const o = Math.min(Math.max(p.y, q.y), Math.max(u.y, v.y)) - Math.max(Math.min(p.y, q.y), Math.min(u.y, v.y)); if (o > 10) hit = true; }
    }
    // hai luồng cùng vào một điểm (nhập nhánh) là bình thường: bỏ qua khi chung đích hoặc chung nguồn
    const sameEnd = conns[i].type === conns[j].type &&
      (conns[i].target === conns[j].target || conns[i].source === conns[j].source);
    if (hit && !sameEnd) issues.push(`đường ${conns[i].id} chồng lên đường ${conns[j].id}`);
  }
  // đường nối chạy dọc theo đường kẻ pool/lane (khó phân biệt)
  for (const cn of conns) { const wp = cn.waypoints; let hit = false;
    for (let i = 0; i < wp.length - 1 && !hit; i++) for (const [u, v] of rules) {
      const p = wp[i], q = wp[i + 1];
      if (Math.abs(p.x - q.x) < 1 && Math.abs(u.x - v.x) < 1 && Math.abs(p.x - u.x) < 8 &&
          Math.min(Math.max(p.y, q.y), Math.max(u.y, v.y)) - Math.max(Math.min(p.y, q.y), Math.min(u.y, v.y)) > 10) { hit = true; break; }
      if (Math.abs(p.y - q.y) < 1 && Math.abs(u.y - v.y) < 1 && Math.abs(p.y - u.y) < 8 &&
          Math.min(Math.max(p.x, q.x), Math.max(u.x, v.x)) - Math.max(Math.min(p.x, q.x), Math.min(u.x, v.x)) > 10) { hit = true; break; } }
    if (hit) issues.push(`đường ${cn.id} chạy dọc đường kẻ pool/lane`); }
  // đường nối chạy xuyên qua hình không phải điểm đầu / điểm cuối của nó
  for (const cn of conns) {
    const ends = new Set([cn.source && cn.source.id, cn.target && cn.target.id]);
    if (cn.source && cn.source.host) ends.add(cn.source.host.id);
    for (const s of shapes) {
      if (ends.has(s.id) || s.type === 'bpmn:BoundaryEvent' || (s.host && ends.has(s.host.id))) continue;
      const r = { x: s.x + 3, y: s.y + 3, w: s.width - 6, h: s.height - 6 };
      const wp = cn.waypoints;
      for (let i = 0; i < wp.length - 1; i++) if (segHit(r, wp[i], wp[i + 1])) { issues.push(`đường ${cn.id} chạy xuyên "${name(s)}"`); break; }
    }
  }
  // chữ trong ô tác vụ: đo bằng DOM
  const gfx = m.get('elementRegistry');
  for (const s of shapes) {
    if (!/Task|SubProcess|CallActivity/.test(s.type)) continue;
    const g = gfx.getGraphics(s); const t = g.querySelector('text'); if (!t) continue;
    const b = t.getBBox();  // toạ độ trong nhóm của phần tử (gốc ở góc trên trái ô)
    const iconZone = { x: 4, y: 4, w: 22, h: 18 };
    if (b.y < 2 || b.y + b.height > s.height - 2 || b.x < 1 || b.x + b.width > s.width - 1) issues.push(`chữ tràn ô "${name(s)}"`);
    else if (/User|Manual|Service|Send|Receive|Script|BusinessRule/.test(s.type)) {
      // dòng đầu của chữ có nằm trong vùng biểu tượng không
      const first = t.querySelector('tspan'); const fb = first.getBBox();
      if (ov({ x: fb.x, y: fb.y, w: fb.width, h: fb.height }, iconZone) > 2) issues.push(`biểu tượng che chữ "${name(s)}"`);
    }
  }
  const { xml: out } = await m.saveXML({ format: true });
  return { issues, xml: out };
}
"""

folder = Path(sys.argv[1])
fix = "--fix" in sys.argv
report = {}
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="msedge")
    pg = b.new_page(viewport={"width": 1600, "height": 1000})
    pg.set_content(PAGE)
    pg.wait_for_function("typeof BpmnJS === 'function'", timeout=60000)
    for f in sorted(folder.glob("*.bpmn")):
        res = pg.evaluate(JS, [f.read_text(encoding="utf-8"), fix])
        report[f.name] = res["issues"]
        if fix:
            f.write_text(res["xml"], encoding="utf-8")
    b.close()
total = 0
for k, v in report.items():
    print(f"{k}: {len(v)} chỗ")
    for i in v:
        print("   -", i)
    total += len(v)
print("TỔNG", total)
