// Dựng DOM an toàn: mọi dữ liệu đi qua textContent / setAttribute, không innerHTML
// với dữ liệu từ API (bản cũ dùng innerHTML — rủi ro chèn mã).

export function h(tag, attrs = {}, ...children) {
    const el = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
        if (value === null || value === undefined || value === false) continue;
        if (key === 'class') el.className = value;
        else if (key === 'dataset') Object.assign(el.dataset, value);
        else if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2), value);
        else if (key === 'style' && typeof value === 'object') {
            for (const [prop, v] of Object.entries(value)) {
                if (prop.startsWith('--')) el.style.setProperty(prop, String(v));
                else el.style[prop] = v;
            }
        }
        else el.setAttribute(key, value === true ? '' : String(value));
    }
    append(el, children);
    return el;
}

export function append(el, children) {
    for (const child of children.flat(Infinity)) {
        if (child === null || child === undefined || child === false) continue;
        el.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return el;
}

export function clear(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
    return el;
}

const ICONS = {
    library: '<path d="M4 5h4v14H4zM10 5h4v14h-4zM16.5 5.5l3.5 1-3.4 13-3.5-1z"/>',
    studio: '<path d="M12 3a7 7 0 0 0-7 7c0 5 7 11 7 11s7-6 7-11a7 7 0 0 0-7-7z"/><circle cx="12" cy="10" r="2.5"/>',
    quality: '<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
    lab: '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/>',
    review: '<path d="M4 20h4l10-10-4-4L4 16z"/><path d="M13 7l4 4"/>',
    passport: '<rect x="5" y="3" width="14" height="18" rx="2"/><circle cx="12" cy="10" r="3"/><path d="M9 16h6"/>',
    dashboard: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    process: '<rect x="3" y="4" width="6" height="5" rx="1"/><rect x="15" y="15" width="6" height="5" rx="1"/><path d="M6 9v4a2 2 0 0 0 2 2h7"/>',
    sources: '<path d="M12 3l9 4-9 4-9-4z"/><path d="M3 12l9 4 9-4M3 17l9 4 9-4"/>',
    pass: '<path d="M5 12.5l4 4 10-10"/>',
    warn: '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17v.5"/>',
    fail: '<path d="M6 6l12 12M18 6L6 18"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9M18 14v6H4V6h6"/>',
    maximize: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
    download: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
    close: '<path d="M6 6l12 12M18 6L6 18"/>',
    chev: '<path d="M9 6l6 6-6 6"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
};

export function icon(name, cls = '') {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '1.8');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('aria-hidden', 'true');
    if (cls) svg.setAttribute('class', cls);
    const doc = new DOMParser().parseFromString(`<svg xmlns="http://www.w3.org/2000/svg">${ICONS[name] || ''}</svg>`, 'image/svg+xml');
    for (const node of [...doc.documentElement.childNodes]) svg.appendChild(document.importNode(node, true));
    return svg;
}

export const fmt = {
    num(v, digits = 2) {
        if (v === null || v === undefined || v === '' || Number.isNaN(Number(v))) return '—';
        return Number(v).toLocaleString('vi-VN', { minimumFractionDigits: digits, maximumFractionDigits: digits });
    },
    pct(v, digits = 0) {
        if (v === null || v === undefined || Number.isNaN(Number(v))) return '—';
        return `${(Number(v) * 100).toLocaleString('vi-VN', { maximumFractionDigits: digits })}%`;
    },
    date(iso) {
        if (!iso) return 'Không ghi nhận';
        const d = new Date(iso);
        if (Number.isNaN(d.getTime())) return iso;
        return d.toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: iso.length > 10 ? 'short' : undefined });
    },
    hash(h, n = 10) { return h ? `${h.slice(0, n)}…` : '—'; },
};

export function toast(message) {
    const el = document.getElementById('toast');
    el.textContent = message;
    el.hidden = false;
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => { el.hidden = true; }, 3800);
}

export function downloadJson(filename, data) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const a = h('a', { href: URL.createObjectURL(blob), download: filename });
    document.body.append(a);
    a.click();
    a.remove();
}
