// components/lightbox.js — CỬA SỔ PHÓNG TO một thiết kế (trang Kết quả): ảnh phóng 100–400% (thanh trượt, lăn chuột,
// bấm đúp, kéo để xê dịch), nút TẢI XUỐNG / QUAY LẠI, dấu X. Đóng bằng Esc hoặc bấm ra ngoài; giữ tiêu điểm bàn phím.
// Ra: openLightbox({ src, alt, filename, opener }). Gắn vào #overlay-root trong index.html.
import { h } from '../core/dom.js';
import { icon } from '../core/icons.js';
import { downloadImage } from '../core/download.js';
import { aiMark } from './badges.js';

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
export function openLightbox({ src, alt, filename, opener }) {
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
