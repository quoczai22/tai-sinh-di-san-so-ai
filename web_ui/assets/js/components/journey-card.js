// components/journey-card.js — THẺ MỘT CHẶNG trong khối "Hành trình" trang chủ (Hiện vật → Hoa văn → Tà áo).
// Chỉ để xem: không phải nút bấm, không dẫn tới trang nào. Props: { index, title, sub, img, ai, contain }.
// Dùng ở: views/library.js, nằm trong băng [data-pin-track] mà core/scenes.js trượt ngang theo cuộn.
import { h } from '../core/dom.js';
import { aiMark } from './badges.js';

export function journeyCard({ index, title, sub, img, ai, contain }) {
    return h('div', { class: 'journey-card' },
        h('div', { class: `jc-img ${contain ? 'contain' : ''}` }, img ? h('img', { src: img, alt: '', loading: 'lazy' }) : null),
        h('span', { class: 'jc-num' }, String(index + 1).padStart(2, '0')),
        ai ? aiMark() : null,
        h('div', { class: 'jc-body' }, h('h3', {}, title), h('p', {}, sub)));
}
