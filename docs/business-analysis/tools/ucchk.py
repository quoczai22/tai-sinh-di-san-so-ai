# -*- coding: utf-8 -*-
"""Đo chữ bị chèn trong sơ đồ Use Case (SVG do ucgen.py sinh), dùng trình duyệt để lấy khung chữ thật.

    python ucchk.py <thư mục chứa UC-*.svg>

Báo: chữ đè chữ, đường đè chữ, nhãn «include»/«extend» che đường khác, đường xuyên qua elip không phải
điểm đầu/cuối, chữ tràn khỏi elip của chính nó, chữ đè elip hoặc hộp hệ thống ngoài khác.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

JS = r"""
() => {
  const svg = document.querySelector('svg');
  const issues = [];
  const R = b => ({ x: b.x, y: b.y, w: b.width, h: b.height });
  const shrink = (r, d) => ({ x: r.x + d, y: r.y + d, w: r.w - 2 * d, h: r.h - 2 * d });
  const hit = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
  const segRect = (l, r) => { for (let i = 0; i <= 80; i++) { const t = i / 80;
      const x = l.x1 + (l.x2 - l.x1) * t, y = l.y1 + (l.y2 - l.y1) * t;
      if (x > r.x && x < r.x + r.w && y > r.y && y < r.y + r.h) return true; } return false; };
  const inEll = (e, x, y, k) => ((x - e.cx) / (e.rx * k)) ** 2 + ((y - e.cy) / (e.ry * k)) ** 2 < 1;
  const num = (el, a) => parseFloat(el.getAttribute(a));
  const lines = [...svg.querySelectorAll('line')].map(el => ({ el, k: el.getAttribute('data-k') || 'figure',
      s: el.getAttribute('data-s'), t: el.getAttribute('data-t'),
      x1: num(el, 'x1'), y1: num(el, 'y1'), x2: num(el, 'x2'), y2: num(el, 'y2') }));
  const ells = [...svg.querySelectorAll('ellipse[data-o]')].map(el => ({ o: el.getAttribute('data-o'),
      cx: num(el, 'cx'), cy: num(el, 'cy'), rx: num(el, 'rx'), ry: num(el, 'ry') }));
  const boxes = [...svg.querySelectorAll('rect[fill="#F2F2F2"]')].map(el => ({ x: num(el, 'x'), y: num(el, 'y'), w: num(el, 'width'), h: num(el, 'height') }));
  const texts = [...svg.querySelectorAll('text[data-k]')].map(el => ({ el, k: el.getAttribute('data-k'),
      o: el.getAttribute('data-o'), s: el.getAttribute('data-s'), t: el.getAttribute('data-t'),
      txt: el.textContent, r: shrink(R(el.getBBox()), 1) }));
  const sysTexts = [...svg.querySelectorAll('text')].filter(el => !el.hasAttribute('data-k')).map(el => ({ txt: el.textContent, r: shrink(R(el.getBBox()), 1) }));
  // chữ đè chữ
  for (let i = 0; i < texts.length; i++) for (let j = i + 1; j < texts.length; j++) {
    const a = texts[i], b = texts[j];
    if (a.o && a.o === b.o) continue;
    if (hit(a.r, b.r)) issues.push(`chữ "${a.txt}" đè chữ "${b.txt}"`);
  }
  // đường đè chữ (trừ nhãn «include» nằm trên chính đường của nó)
  for (const T of texts) for (const l of lines) {
    if (T.k === 'rel-label' && l.k === 'rel' && l.s === T.s && l.t === T.t) continue;
    if (segRect(l, T.r)) issues.push(`đường ${l.k}${l.s ? ' ' + l.s + '→' + l.t : ''} đè chữ "${T.txt}"`);
  }
  // nền trắng của nhãn «include» che mất đường khác
  const bgs = [...svg.querySelectorAll('rect[data-k="rel-bg"]')];
  texts.filter(T => T.k === 'rel-label').forEach((T, i) => {
    const b = bgs[i]; const r = shrink({ x: num(b, 'x'), y: num(b, 'y'), w: num(b, 'width'), h: num(b, 'height') }, 1);
    for (const l of lines) if (!(l.k === 'rel' && l.s === T.s && l.t === T.t) && segRect(l, r)) issues.push(`nhãn ${T.s}→${T.t} che đường ${l.k} ${l.s || ''}→${l.t || ''}`);
  });
  // đường xuyên elip không phải điểm đầu / cuối
  for (const l of lines) { if (l.k === 'figure') continue;
    for (const e of ells) { if (e.o === l.s || e.o === l.t) continue;
      for (let i = 0; i <= 80; i++) { const t = i / 80;
        if (inEll(e, l.x1 + (l.x2 - l.x1) * t, l.y1 + (l.y2 - l.y1) * t, 0.98)) { issues.push(`đường ${l.s}→${l.t} xuyên elip ${e.o}`); break; } } } }
  // chữ ca sử dụng tràn khỏi elip của nó; chữ khác đè elip
  for (const T of texts) for (const e of ells) {
    const c = [[T.r.x, T.r.y], [T.r.x + T.r.w, T.r.y], [T.r.x, T.r.y + T.r.h], [T.r.x + T.r.w, T.r.y + T.r.h]];
    if (T.k === 'uc' && T.o === e.o) { if (c.some(([x, y]) => !inEll(e, x, y, 1.0))) issues.push(`chữ "${T.txt}" tràn khỏi elip ${e.o}`); }
    else if (hit(T.r, { x: e.cx - e.rx, y: e.cy - e.ry, w: 2 * e.rx, h: 2 * e.ry })) {
      let inside = false;
      for (let i = 0; i <= 10 && !inside; i++) for (let j = 0; j <= 4 && !inside; j++)
        if (inEll(e, T.r.x + T.r.w * i / 10, T.r.y + T.r.h * j / 4, 1.0)) inside = true;
      if (inside) issues.push(`chữ "${T.txt}" đè elip ${e.o}`);
    }
  }
  // chữ đè hộp hệ thống ngoài, chữ trong hộp đè đường
  for (const T of texts) for (const b of boxes) if (hit(T.r, b)) issues.push(`chữ "${T.txt}" đè hộp hệ thống ngoài`);
  for (const S of sysTexts) for (const l of lines) if (segRect(l, S.r)) issues.push(`đường ${l.k} ${l.s || ''}→${l.t || ''} đè chữ "${S.txt}"`);
  return issues;
}
"""

folder = Path(sys.argv[1])
total = 0
with sync_playwright() as pw:
    br = pw.chromium.launch(channel="msedge")
    pg = br.new_page()
    for f in sorted(folder.glob("UC-*.svg")):
        pg.goto(f.resolve().as_uri())
        issues = pg.evaluate(JS)
        total += len(issues)
        print(f"{f.name}: {len(issues)} chỗ")
        for i in issues:
            print("   -", i)
    br.close()
print("TỔNG", total)
