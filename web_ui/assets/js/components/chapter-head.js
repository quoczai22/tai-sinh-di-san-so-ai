// components/chapter-head.js — TIÊU ĐỀ MỘT PHẦN của trang chủ: dòng nhỏ (kicker) + tiêu đề lớn + mô tả.
// Dùng ở: views/library.js (Bộ sưu tập, Tà áo).
import { h } from '../core/dom.js';

export function chapterHead(kicker, title, lede) {
    return h('div', { class: 'chapter-intro' },
        kicker ? h('p', { class: 'kicker' }, kicker) : null,
        h('h2', { class: 'display' }, title),
        lede ? h('p', { class: 'lede' }, lede) : null);
}
