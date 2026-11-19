import { h, icon } from '../lib/dom.js';
import * as data from '../lib/data.js';
import { aiMark, stateBox } from '../lib/ui.js';

// ---------------------------------------------------------------------------------------------
// Trang Kết quả: bốn tà áo của bộ thiết kế mới nhất của hiện vật (#/result/<mã hiện vật>).
// Chỉ có ảnh: không bảng chỉ số, không khung chi tiết, không ghi chú, không nhãn "Thiết kế n".
// Bấm vào một ảnh thì mở cửa sổ phóng to, có nút TẢI XUỐNG và QUAY LẠI, dấu X ở góc trên bên phải để đóng.
// ---------------------------------------------------------------------------------------------
const latestOf = (d) => (d.latest_version_kind === 'system_repair' && d.repair_thumb ? d.repair_thumb : d.thumb);

// Tải ảnh về máy: lấy ảnh dạng blob rồi bấm một liên kết download (thuộc tính download không chạy với ảnh khác nguồn).
// Nếu không lấy được thì mở ảnh ở thẻ mới để người xem tự lưu.
async function downloadImage(src, filename) {
    try {
        const res = await fetch(src);
        if (!res.ok) throw new Error(res.status);
        const blob = await res.blob();
        // Đuôi file: theo loại ảnh máy chủ báo; nếu không có thì lấy theo đuôi trong đường dẫn ảnh
        const ext = { 'image/png': 'png', 'image/webp': 'webp', 'image/jpeg': 'jpg' }[blob.type]
            || (decodeURIComponent(src).match(/\.(png|webp|jpe?g)(?:$|[?&#])/i)?.[1] || 'png').toLowerCase();
        const url = URL.createObjectURL(blob);
        const a = h('a', { href: url, download: `${filename}.${ext}` });
        document.body.append(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 4000);
    } catch {
        window.open(src, '_blank', 'noopener');
    }
}

// Cửa sổ phóng to ảnh. Đóng bằng dấu X, nút QUAY LẠI, phím Esc hoặc bấm ra ngoài; trả tiêu điểm về ảnh đã bấm.
function openLightbox({ src, alt, filename, opener }) {
    const close = () => {
        document.removeEventListener('keydown', onKey);
        box.remove();
        document.body.classList.remove('lb-open');
        opener?.focus();
    };
    const closeBtn = h('button', { class: 'lb-close', type: 'button', 'aria-label': 'Đóng', onclick: close }, icon('close'));
    const download = h('button', { class: 'btn hero-btn primary', type: 'button', onclick: () => downloadImage(src, filename) }, icon('download'), 'Tải xuống');
    const back = h('button', { class: 'btn hero-btn ghost', type: 'button', onclick: close }, 'Quay lại');
    const focusables = [closeBtn, download, back];
    const onKey = (e) => {
        if (e.key === 'Escape') { close(); return; }
        if (e.key !== 'Tab') return;                                // giữ tiêu điểm bàn phím trong cửa sổ
        const i = focusables.indexOf(document.activeElement);
        const next = e.shiftKey ? (i <= 0 ? focusables.length - 1 : i - 1) : (i + 1) % focusables.length;
        e.preventDefault();
        focusables[next].focus();
    };
    const box = h('div', { class: 'lightbox', role: 'dialog', 'aria-modal': 'true', 'aria-label': alt, onclick: (e) => { if (e.target === box) close(); } },
        h('div', { class: 'lb-panel' },
            closeBtn,
            h('div', { class: 'lb-pic' }, h('img', { src, alt }), aiMark()),
            h('div', { class: 'lb-actions' }, download, back)));
    document.body.classList.add('lb-open');
    document.getElementById('overlay-root').append(box);
    document.addEventListener('keydown', onKey);
    download.focus();
}

function designCard(d, n, heritageId) {
    const src = data.media(d.final_path, latestOf(d));
    const card = h('article', { class: 'design out-card', role: 'button', tabindex: '0', 'aria-label': `Xem thiết kế ${n}`, style: { '--k': String(n - 1) } },
        h('div', { class: 'pic' }, h('img', { src, alt: `Thiết kế ${n}`, loading: 'lazy' }), aiMark()));
    const open = () => openLightbox({ src, alt: `Thiết kế ${n}`, filename: `thiet-ke-${heritageId}-${n}`, opener: card });
    card.addEventListener('click', open);
    card.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } });
    return card;
}

export async function render([heritageId]) {
    const { items } = await data.heritage();
    const item = items.find((i) => i.id === heritageId);
    const all = (await data.passports()).filter((p) => p.heritage_id === heritageId && p.thumb);
    const run = [...new Set(all.map((p) => p.run_id))].sort().reverse()[0];
    const designs = all.filter((p) => p.run_id === run).sort((a, b) => a.passport_id.localeCompare(b.passport_id));
    const studio = item ? `#/studio/${encodeURIComponent(item.id)}` : '#/studio';
    if (!item || !designs.length) {
        return stateBox('', 'Chưa có thiết kế', 'Hiện vật này chưa có bộ thiết kế nào.', h('a', { class: 'btn primary', href: '#/studio' }, 'Về Studio'));
    }
    const grid = h('div', { class: 'out-grid' }, designs.map((d, k) => designCard(d, k + 1, heritageId)));
    requestAnimationFrame(() => grid.classList.add('shown'));
    return h('div', { class: 'result' },
        h('div', { class: 'result-head' },
            h('div', { class: 'result-artifact' }, h('img', { src: item.image, alt: '' })),
            h('h2', { class: 'io-name' }, item.name)),
        grid,
        h('div', { class: 'result-actions' },
            h('a', { class: 'btn hero-btn primary', href: studio }, 'Tạo lại'),
            h('a', { class: 'btn hero-btn ghost', href: '#/studio' }, 'Chọn hiện vật khác')));
}
