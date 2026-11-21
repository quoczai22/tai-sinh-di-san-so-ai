// components/picker-card.js — THẺ CHỌN HIỆN VẬT ở Studio (bước 1 của pipeline: chọn đầu vào).
// Rê chuột vào thì bình xoay 3D, rê ra thì đứng yên. Bấm → #/studio/<mã hiện vật>.
import { h } from '../core/dom.js';
import { hoverSpin } from './viewer3d.js';

export function pickerCard(it) {
    const pic = h('div', { class: 'pic' }, h('img', { src: it.image, alt: '', loading: 'lazy' }));
    const card = h('a', { class: 'artifact', href: `#/studio/${encodeURIComponent(it.id)}`, style: { textDecoration: 'none' } },
        pic,
        h('div', { class: 'body' }, h('div', { class: 'code' }, it.dating || 'Gốm Bát Tràng'), h('div', { class: 'name' }, it.name)));
    hoverSpin(card, pic, it.id);
    return card;
}
