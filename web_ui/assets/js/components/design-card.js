// components/design-card.js — THẺ MỘT THIẾT KẾ áo dài ở trang Kết quả (bước cuối của pipeline: xem đầu ra).
// Bấm / Enter / Space → mở lightbox với ảnh PNG gốc. Ảnh luôn mang nhãn AI. Props: (d: Passport, n: số thứ tự, heritageId).
import { h } from '../core/dom.js';
import * as data from '../core/data.js';
import { fullImage, latestOf, shownPath } from '../core/designs.js';
import { aiMark, editedMark } from './badges.js';
import { openLightbox } from './lightbox.js';

// Nút "Tải lên chỉnh sửa" trong cửa sổ phóng to: chỉ dùng được với thiết kế tạo trực tiếp (có Passport trên máy chủ)
const EDIT_LOCKED = 'Chỉ thiết kế bạn tạo trực tiếp ở Studio mới chỉnh sửa được. Thiết kế sinh sẵn của bản trình diễn thì không.';

export function designCard(d, n, heritageId) {
    const src = data.media(shownPath(d), latestOf(d));
    const fullSrc = fullImage(d, heritageId, src);
    const card = h('article', { class: 'design out-card', role: 'button', tabindex: '0', 'aria-label': `Xem thiết kế ${n}`, style: { '--k': String(n - 1) } },
        h('div', { class: 'pic' }, h('img', {
            src, alt: `Thiết kế ${n}`, loading: data.isLive() ? 'eager' : 'lazy',
            decoding: 'async', fetchpriority: n === 1 ? 'high' : 'auto',
        }), aiMark(), d.edits > 0 ? editedMark() : null));
    const edit = data.isLive() && d.passport_id ? { href: `#/edit/${encodeURIComponent(d.passport_id)}` } : { locked: EDIT_LOCKED };
    const open = () => openLightbox({ src: fullSrc, alt: `Thiết kế ${n}`, filename: `thiet-ke-${heritageId}-${n}`, opener: card, edit, edited: d.edits > 0 });
    card.addEventListener('click', open);
    card.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } });
    return card;
}
