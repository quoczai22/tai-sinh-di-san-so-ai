import { h, icon } from '../lib/dom.js';
import * as data from '../lib/data.js';
import { aiMark, demoNotice, stateBox } from '../lib/ui.js';

// ---------------------------------------------------------------------------------------------
// Trang Kết quả: bốn tà áo của bộ thiết kế mới nhất của hiện vật (#/result/<mã hiện vật>).
// Chỉ có ảnh: không bảng chỉ số, không khung chi tiết, không ghi chú, không nhãn "Thiết kế n".
// Bấm vào một ảnh thì mở cửa sổ phóng to, có nút TẢI XUỐNG và QUAY LẠI, dấu X ở góc trên bên phải để đóng.
// ---------------------------------------------------------------------------------------------
const latestOf = (d) => (d.latest_version_kind === 'system_repair' && d.repair_thumb ? d.repair_thumb : d.thumb);

// Đổi ảnh bất kỳ (ví dụ WebP) sang PNG bằng canvas, để file người xem nhận luôn là định dạng ảnh phổ biến.
async function toPng(blob) {
    const bitmap = await createImageBitmap(blob);
    const canvas = document.createElement('canvas');
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    canvas.getContext('2d').drawImage(bitmap, 0, 0);
    return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('toBlob'))), 'image/png'));
}

// Tải ảnh về máy: lấy ảnh dạng blob rồi bấm một liên kết download (thuộc tính download không chạy với ảnh khác nguồn).
// File tải về luôn là PNG hoặc JPEG, không bao giờ là WebP. Nếu không lấy được thì mở ảnh ở thẻ mới để người xem tự lưu.
async function downloadImage(src, filename) {
    try {
        const res = await fetch(src);
        if (!res.ok) throw new Error(res.status);
        let blob = await res.blob();
        // Đuôi file: theo loại ảnh máy chủ báo; nếu không có thì lấy theo đuôi trong đường dẫn ảnh
        let ext = { 'image/png': 'png', 'image/webp': 'webp', 'image/jpeg': 'jpg' }[blob.type]
            || (decodeURIComponent(src).match(/\.(png|webp|jpe?g)(?:$|[?&#])/i)?.[1] || 'png').toLowerCase();
        if (ext === 'webp') { blob = await toPng(blob); ext = 'png'; }
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

// Ảnh có thể phóng to từ 100% đến 400%: kéo thanh trượt, lăn chuột trên ảnh (phóng về phía con trỏ),
// bấm đúp để phóng 2 lần hoặc về lại 100%. Khi đã phóng thì kéo chuột để xê dịch ảnh.
const ZOOM_MIN = 1, ZOOM_MAX = 4, ZOOM_STEP = 0.25;                 // nút − và + đổi 25% mỗi lần bấm

function zoomablePic(src, alt) {
    const img = h('img', { src, alt, draggable: 'false' });
    const pic = h('div', { class: 'lb-pic' }, img, aiMark());
    const slider = h('input', { class: 'lb-zoom', type: 'range', min: String(ZOOM_MIN * 100), max: String(ZOOM_MAX * 100), step: '5',
        value: '100', 'aria-label': 'Phóng to, thu nhỏ' });
    let z = 1, tx = 0, ty = 0;                                      // mức phóng và độ xê dịch (px) so với tâm ảnh

    const apply = () => {
        const maxX = ((z - 1) * img.clientWidth) / 2, maxY = ((z - 1) * img.clientHeight) / 2;
        tx = Math.max(-maxX, Math.min(maxX, tx));                   // không kéo ảnh ra khỏi khung
        ty = Math.max(-maxY, Math.min(maxY, ty));
        img.style.transform = `translate(${tx}px, ${ty}px) scale(${z})`;
        slider.value = String(Math.round(z * 100));
        pic.classList.toggle('zoomed', z > 1);
    };
    // (cx, cy): điểm trên ảnh được giữ cố định khi phóng, tính từ tâm khung
    const setZoom = (next, cx = 0, cy = 0) => {
        next = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, next));
        const k = next / z;
        tx = cx - (cx - tx) * k;
        ty = cy - (cy - ty) * k;
        z = next;
        apply();
    };
    const fromCenter = (e) => {
        const r = pic.getBoundingClientRect();
        return [e.clientX - (r.left + r.width / 2), e.clientY - (r.top + r.height / 2)];
    };

    pic.addEventListener('wheel', (e) => { e.preventDefault(); setZoom(z * Math.exp(-e.deltaY * 0.0015), ...fromCenter(e)); }, { passive: false });
    slider.addEventListener('input', () => setZoom(Number(slider.value) / 100));
    pic.addEventListener('dblclick', (e) => setZoom(z > 1 ? 1 : 2, ...fromCenter(e)));
    let drag = null;
    pic.addEventListener('pointerdown', (e) => {
        if (z === 1) return;
        drag = { x: e.clientX - tx, y: e.clientY - ty };
        pic.setPointerCapture(e.pointerId);
        pic.classList.add('dragging');
    });
    pic.addEventListener('pointermove', (e) => { if (drag) { tx = e.clientX - drag.x; ty = e.clientY - drag.y; apply(); } });
    const endDrag = () => { drag = null; pic.classList.remove('dragging'); };
    pic.addEventListener('pointerup', endDrag);
    pic.addEventListener('pointercancel', endDrag);

    const stepBtn = (label, text, delta) => h('button', { class: 'lb-step', type: 'button', 'aria-label': label,
        onclick: () => setZoom(Math.round((z + delta) * 100) / 100) }, text);
    const minus = stepBtn('Thu nhỏ', '−', -ZOOM_STEP), plus = stepBtn('Phóng to', '+', ZOOM_STEP);
    const row = h('div', { class: 'lb-zoomrow' }, minus, slider, plus);
    return { pic, row, controls: [minus, slider, plus] };
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
    const { pic, row, controls } = zoomablePic(src, alt);
    const focusables = [closeBtn, ...controls, download, back];
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
            pic,
            row,
            h('div', { class: 'lb-actions' }, download, back)));
    document.body.classList.add('lb-open');
    document.getElementById('overlay-root').append(box);
    document.addEventListener('keydown', onKey);
    download.focus();
}

// Ảnh gốc đầy đủ của thiết kế. Chế độ trực tiếp: tệp PNG từ máy chủ. Chế độ trình diễn: bản PNG gốc scripts/11_export_demo_data.py
// chép vào assets/images/variants/<mã hiện vật>_V<số>_aodai.png (thiết kế đã được hệ thống sửa thì chỉ có bản WebP nén).
function fullImage(d, heritageId, fallback) {
    if (data.isLive() || latestOf(d) !== d.thumb) return fallback;
    return `./assets/images/variants/${encodeURIComponent(heritageId)}_V${d.passport_id.split('-V').pop()}_aodai.png`;
}

function designCard(d, n, heritageId) {
    const src = data.media(d.final_path, latestOf(d));
    const fullSrc = fullImage(d, heritageId, src);
    const card = h('article', { class: 'design out-card', role: 'button', tabindex: '0', 'aria-label': `Xem thiết kế ${n}`, style: { '--k': String(n - 1) } },
        h('div', { class: 'pic' }, h('img', { src, alt: `Thiết kế ${n}`, loading: 'lazy' }), aiMark()));
    const open = () => openLightbox({ src: fullSrc, alt: `Thiết kế ${n}`, filename: `thiet-ke-${heritageId}-${n}`, opener: card });
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
        data.isLive() ? null : demoNotice(),
        grid,
        h('div', { class: 'result-actions' },
            h('a', { class: 'btn hero-btn primary', href: studio }, 'Tạo lại'),
            h('a', { class: 'btn hero-btn ghost', href: '#/studio' }, 'Chọn hiện vật khác')));
}
