// Mặt trống đồng Đông Sơn (vẽ lại tối giản theo bố cục mặt trống Ngọc Lũ):
//   mặt trời 14 cánh ở tâm, xen giữa các cánh là hoạ tiết lông công;
//   các vành: vòng tròn chấm có tiếp tuyến, vạch song song, răng cưa;
//   vành ngoài: đàn chim Lạc bay ngược chiều kim đồng hồ.
// Mọi phần tử dựng bằng createElementNS (không innerHTML). Các vành có class .ring-k với --k là thứ tự
// từ tâm ra ngoài, CSS dùng --e/--p của khối [data-scene] để vành hiện dần và mặt trống xoay theo cuộn.
// Ngoài ra là "mây cát tường" (mây tản) dùng làm nút trên sợi chỉ dẫn đường.

const NS = 'http://www.w3.org/2000/svg';
const el = (tag, attrs = {}, children = []) => {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, String(v));
    for (const c of children) n.append(c);
    return n;
};
const C = 300; // tâm
const pt = (r, deg) => { const a = (deg - 90) * Math.PI / 180; return [C + r * Math.cos(a), C + r * Math.sin(a)]; };
const f = (n) => n.toFixed(1);

function ring(k, children) {
    return el('g', { class: 'ring', style: `--k:${k}` }, children);
}

function sun() {
    // Ngôi sao 14 cánh: đỉnh ở r=78, chân ở r=26
    const pts = [];
    for (let i = 0; i < 28; i++) {
        const [x, y] = pt(i % 2 ? 26 : 78, i * (360 / 28));
        pts.push(`${f(x)},${f(y)}`);
    }
    const star = el('polygon', { points: pts.join(' '), class: 'drum-gold' });
    // Hoạ tiết lông công giữa các cánh: tam giác nhỏ có gạch
    const feathers = [];
    for (let i = 0; i < 14; i++) {
        const a = i * (360 / 14) + 360 / 28;
        const [x1, y1] = pt(34, a - 6); const [x2, y2] = pt(34, a + 6); const [x3, y3] = pt(70, a);
        feathers.push(el('path', { d: `M${f(x1)} ${f(y1)} L${f(x3)} ${f(y3)} L${f(x2)} ${f(y2)}`, class: 'drum-line' }));
        const [hx1, hy1] = pt(46, a - 3); const [hx2, hy2] = pt(46, a + 3);
        feathers.push(el('path', { d: `M${f(hx1)} ${f(hy1)} L${f(hx2)} ${f(hy2)}`, class: 'drum-line thin' }));
    }
    return ring(0, [el('circle', { cx: C, cy: C, r: 18, class: 'drum-gold' }), star, ...feathers,
        el('circle', { cx: C, cy: C, r: 84, class: 'drum-line' })]);
}

function circlesRing(k, r, n) {
    // Vòng tròn chấm có tiếp tuyến nối nhau
    const kids = [el('circle', { cx: C, cy: C, r: r - 9, class: 'drum-line thin' }), el('circle', { cx: C, cy: C, r: r + 9, class: 'drum-line thin' })];
    for (let i = 0; i < n; i++) {
        const [x, y] = pt(r, i * 360 / n);
        kids.push(el('circle', { cx: f(x), cy: f(y), r: 5.2, class: 'drum-line' }), el('circle', { cx: f(x), cy: f(y), r: 1.6, class: 'drum-dot' }));
        const [ax, ay] = pt(r + 5.2, i * 360 / n); const [bx, by] = pt(r - 5.2, (i + 1) * 360 / n);
        kids.push(el('path', { d: `M${f(ax)} ${f(ay)} L${f(bx)} ${f(by)}`, class: 'drum-line thin' }));
    }
    return ring(k, kids);
}

function ticksRing(k, r0, r1, n) {
    const kids = [el('circle', { cx: C, cy: C, r: r1, class: 'drum-line thin' })];
    for (let i = 0; i < n; i++) {
        const [ax, ay] = pt(r0, i * 360 / n); const [bx, by] = pt(r1, i * 360 / n);
        kids.push(el('path', { d: `M${f(ax)} ${f(ay)} L${f(bx)} ${f(by)}`, class: 'drum-line thin' }));
    }
    return ring(k, kids);
}

function zigzagRing(k, r, n, h) {
    let d = '';
    for (let i = 0; i <= n; i++) {
        const [x, y] = pt(i % 2 ? r + h : r - h, i * 360 / n);
        d += `${i ? 'L' : 'M'}${f(x)} ${f(y)} `;
    }
    return ring(k, [el('path', { d, class: 'drum-line' }), el('circle', { cx: C, cy: C, r: r + h + 6, class: 'drum-line thin' })]);
}

// Chim Lạc cách điệu, mỏ dài hướng theo chiều bay (sang phải ở toạ độ gốc)
const BIRD = 'M 30 -1 L 6 -4 C 2 -9 -6 -10 -11 -6 L -36 -19 L -24 -5 L -50 0 L -24 4 L -38 17 L -11 6 C -5 8 1 6 6 2 Z M -5 -8 L -1 -18 L 2 -8';
function birdsRing(k, r, n) {
    const flock = [];
    for (let i = 0; i < n; i++) {
        const deg = i * 360 / n;
        const [x, y] = pt(r, deg);
        // Bay ngược chiều kim đồng hồ: hướng tiếp tuyến = góc - 90°
        flock.push(el('path', { d: BIRD, class: 'drum-bird', transform: `translate(${f(x)} ${f(y)}) rotate(${f(deg - 180)}) scale(1.05)` }));
    }
    return ring(k, [el('circle', { cx: C, cy: C, r: r - 30, class: 'drum-line thin' }), el('g', { class: 'drum-flock' }, flock),
        el('circle', { cx: C, cy: C, r: r + 30, class: 'drum-line' })]);
}

/** Mặt trống đồng, trả về <svg>. */
export function drum() {
    const svg = el('svg', { viewBox: '0 0 600 600', class: 'drum', 'aria-hidden': 'true', focusable: 'false' });
    svg.append(el('circle', { cx: C, cy: C, r: 296, class: 'drum-plate' }));
    svg.append(el('g', { class: 'drum-spin' }, [
        sun(),
        circlesRing(1, 104, 22),
        ticksRing(2, 124, 138, 72),
        zigzagRing(3, 152, 64, 6),
        ticksRing(4, 166, 176, 96),
        birdsRing(5, 214, 12),
        ticksRing(6, 250, 262, 120),
        circlesRing(7, 278, 48),
    ]));
    return svg;
}

/** Mây cát tường (mây tản) — nút trang trí trên sợi chỉ dẫn đường. */
export function cloud(cls = '') {
    const svg = el('svg', { viewBox: '0 0 120 60', class: `cloud ${cls}`, 'aria-hidden': 'true', focusable: 'false' });
    svg.append(
        el('path', { class: 'cloud-line', d: 'M 14 42 C 2 42 2 26 14 26 C 14 14 30 10 38 18 C 42 6 62 4 68 16 C 76 8 92 12 92 24 C 104 22 112 34 104 42 Z' }),
        el('path', { class: 'cloud-line thin', d: 'M 30 42 C 30 34 40 30 46 36 C 50 30 60 30 62 38' }),
        el('path', { class: 'cloud-line thin', d: 'M 66 26 C 70 20 80 20 82 28' }),
        el('path', { class: 'cloud-line', d: 'M 104 42 C 112 46 116 52 108 56 C 102 58 98 52 104 50' }),
    );
    return svg;
}

/** Đoạn sợi chỉ vàng nối hai phần trang, vẽ dần theo cuộn; giữa đoạn là một cụm mây. */
export function thread() {
    const svg = el('svg', { viewBox: '0 0 40 220', class: 'thread-line', preserveAspectRatio: 'none', 'aria-hidden': 'true', focusable: 'false' });
    svg.append(el('path', { d: 'M 20 0 C 4 50, 36 90, 20 110 C 4 130, 36 170, 20 220', pathLength: 1, class: 'thread-path' }));
    const wrap = document.createElement('div');
    wrap.className = 'thread';
    wrap.setAttribute('aria-hidden', 'true');
    wrap.setAttribute('data-scene', '');
    wrap.append(svg, cloud('thread-cloud'));
    return wrap;
}
