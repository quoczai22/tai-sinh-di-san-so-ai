// components/gallery-item.js — MỘT TÀ ÁO trong lưới "Áo dài từ hoa văn gốm" trang chủ. Chỉ để xem, không dẫn tới trang nào.
// Props: (d: Passport, name: tên hiện vật nguồn). Ảnh luôn mang nhãn AI.
import { h } from '../core/dom.js';
import { latestOf } from '../core/designs.js';
import { aiMark } from './badges.js';

export function galleryItem(d, name) {
    return h('div', { class: 'gallery-item', 'data-scene': '' },
        h('div', { class: 'gi-img' }, h('img', { src: `./${latestOf(d)}`, alt: `Áo dài hoa văn ${name || ''}`, loading: 'lazy' }), aiMark()));
}
