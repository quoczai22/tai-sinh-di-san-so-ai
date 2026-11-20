// components/design-card.js — THẺ MỘT THIẾT KẾ áo dài ở trang Kết quả (bước cuối của pipeline: xem đầu ra).
// Bấm / Enter / Space → mở lightbox với ảnh PNG gốc. Ảnh luôn mang nhãn AI. Props: (d: Passport, n: số thứ tự, heritageId).
import { h } from '../core/dom.js';
import * as data from '../core/data.js';
import { fullImage, latestOf } from '../core/designs.js';
import { aiMark } from './badges.js';
import { openLightbox } from './lightbox.js';

export function designCard(d, n, heritageId) {
    const src = data.media(d.latest_path || d.final_path, latestOf(d));
    const fullSrc = fullImage(d, heritageId, src);
    const card = h('article', { class: 'design out-card', role: 'button', tabindex: '0', 'aria-label': `Xem thiết kế ${n}`, style: { '--k': String(n - 1) } },
        h('div', { class: 'pic' }, h('img', { src, alt: `Thiết kế ${n}`, loading: 'lazy' }), aiMark()));
    const open = () => openLightbox({ src: fullSrc, alt: `Thiết kế ${n}`, filename: `thiet-ke-${heritageId}-${n}`, opener: card });
    card.addEventListener('click', open);
    card.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } });
    return card;
}
