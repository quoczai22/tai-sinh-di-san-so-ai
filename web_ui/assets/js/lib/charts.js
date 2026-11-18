// Biểu đồ SVG tự viết, không thư viện ngoài.
// Bảng màu 2 chuỗi đã chạy bộ kiểm tra màu (dataviz validate_palette): #B8742A / #24508A
// đạt độ tách CVD ΔE 23,9. Chữ luôn dùng màu mực, không dùng màu chuỗi.
import { h } from './dom.js';

const NS = 'http://www.w3.org/2000/svg';
const s = (tag, attrs = {}, ...kids) => {
    const el = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) if (v !== undefined && v !== null) el.setAttribute(k, v);
    for (const k of kids.flat()) if (k) el.append(k instanceof Node ? k : document.createTextNode(String(k)));
    return el;
};

let tip;
function tooltip() {
    if (!tip) { tip = h('div', { class: 'tooltip', hidden: true }); document.body.append(tip); }
    return tip;
}
function showTip(evt, text) {
    const t = tooltip();
    t.textContent = text;
    t.hidden = false;
    t.style.left = `${Math.min(evt.clientX + 12, window.innerWidth - 270)}px`;
    t.style.top = `${evt.clientY + 12}px`;
}
const hideTip = () => { if (tip) tip.hidden = true; };

/**
 * Dumbbell ngang: mỗi hàng một thiết kế, hai điểm (trước/sau sửa) trên cùng thang.
 * rows: [{label, a, b, note}], thresholds: [{value, label}]
 */
export function dumbbell({ rows, domain = [0, 1], thresholds = [], seriesA, seriesB, valueLabel }) {
    const rowH = 22;
    const left = 168;
    const right = 24;
    const top = 26;
    const width = 760;
    const height = top + rows.length * rowH + 30;
    const x = (v) => left + ((v - domain[0]) / (domain[1] - domain[0])) * (width - left - right);
    const svg = s('svg', { viewBox: `0 0 ${width} ${height}`, class: 'chart', role: 'img',
        'aria-label': `${valueLabel}: ${seriesA.name} so với ${seriesB.name} cho ${rows.length} thiết kế` });
    for (let t = domain[0]; t <= domain[1] + 1e-9; t += 0.2) {
        svg.append(s('line', { x1: x(t), x2: x(t), y1: top - 6, y2: height - 24, class: 'grid-line' }));
        svg.append(s('text', { x: x(t), y: height - 8, 'text-anchor': 'middle' }, t.toFixed(1).replace('.', ',')));
    }
    thresholds.forEach((th, i) => {
        svg.append(s('line', { x1: x(th.value), x2: x(th.value), y1: top - 10, y2: height - 24, class: 'threshold' }));
        // nhãn ngưỡng đầu bên trái vạch, ngưỡng sau bên phải — không chồng lên nhau
        const leftSide = i % 2 === 0;
        svg.append(s('text', { x: x(th.value) + (leftSide ? -6 : 6), y: top - 12, 'text-anchor': leftSide ? 'end' : 'start' }, th.label));
    });
    rows.forEach((r, i) => {
        const y = top + i * rowH + rowH / 2;
        svg.append(s('text', { x: left - 10, y: y + 4, 'text-anchor': 'end' }, r.label));
        if (r.a !== null && r.b !== null && r.a !== undefined && r.b !== undefined) {
            svg.append(s('line', { x1: x(r.a), x2: x(r.b), y1: y, y2: y, stroke: '#C9C1B1', 'stroke-width': 2 }));
        }
        for (const [val, color, name] of [[r.a, seriesA.color, seriesA.name], [r.b, seriesB.color, seriesB.name]]) {
            if (val === null || val === undefined || val === '') continue;
            const dot = s('circle', { cx: x(val), cy: y, r: 5, fill: color, stroke: '#FCFBF7', 'stroke-width': 2 });
            const hit = s('circle', { cx: x(val), cy: y, r: 10, fill: 'transparent', tabindex: 0,
                'aria-label': `${r.label} — ${name}: ${Number(val).toFixed(3)}` });
            const text = `${r.label} · ${name}: ${Number(val).toFixed(3).replace('.', ',')}${r.note ? ` · ${r.note}` : ''}`;
            hit.addEventListener('mousemove', (e) => showTip(e, text));
            hit.addEventListener('mouseleave', hideTip);
            hit.addEventListener('focus', (e) => { const b = e.target.getBoundingClientRect(); showTip({ clientX: b.right, clientY: b.top }, text); });
            hit.addEventListener('blur', hideTip);
            svg.append(dot, hit);
        }
    });
    const legend = h('div', { class: 'legend' },
        h('span', {}, h('span', { class: 'sw', style: { background: seriesA.color } }), seriesA.name),
        h('span', {}, h('span', { class: 'sw', style: { background: seriesB.color } }), seriesB.name));
    return h('figure', { style: { margin: 0 } }, legend, svg);
}

/** Thanh xếp chồng trạng thái (Đạt / Cảnh báo / Không đạt) kèm nhãn số bên dưới. */
export function statusBar(counts, total) {
    const order = [['PASS', 'var(--ngoc)', 'Đạt'], ['WARN', '#C49A2C', 'Cảnh báo'], ['FAIL', 'var(--fail)', 'Không đạt']];
    const bar = h('div', { class: 'stack-bar', role: 'img',
        'aria-label': order.map(([k, , t]) => `${t} ${counts[k] || 0}`).join(', ') });
    for (const [k, color] of order) {
        const n = counts[k] || 0;
        if (n) bar.append(h('span', { style: { width: `${(n / total) * 100}%`, background: color }, title: `${n}` }));
    }
    const labels = h('div', { class: 'legend' }, order.map(([k, color, t]) =>
        h('span', {}, h('span', { class: 'sw', style: { background: color, borderRadius: '2px' } }), `${t}: ${counts[k] || 0}`)));
    return h('div', {}, bar, labels);
}
