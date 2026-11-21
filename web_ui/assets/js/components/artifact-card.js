// components/artifact-card.js — THẺ HIỆN VẬT trong lưới "Bộ sưu tập" trang chủ: bình trên bệ, trồi lên theo cuộn
// ([data-scene]), rê chuột thì bình xoay 3D (viewer3d.hoverSpin). Bấm → Studio của hiện vật đó.
// Props: (it: hiện vật từ data.heritage(), k: vị trí trong lưới, dùng để so le cột).
import { h } from '../core/dom.js';
import { hoverSpin } from './viewer3d.js';

export function artifactCard(it, k) {
    const stage = h('div', { class: 'ac-stage' }, h('div', { class: 'ac-halo', 'aria-hidden': 'true' }), h('img', { src: it.image, alt: '', loading: 'lazy' }));
    const card = h('a', { class: 'artifact-card', href: `#/studio/${encodeURIComponent(it.id)}`, 'data-scene': '', style: { '--k': String(k % 3) },
        'aria-label': `${it.name}, tạo thiết kế` },
    stage,
    h('div', { class: 'ac-body' },
        h('div', { class: 'code' }, it.dating || (it.info ? 'Gốm hoa lam' : 'Gốm Bát Tràng')),
        h('div', { class: 'name' }, it.name)));
    hoverSpin(card, stage, it.id);                              // rê chuột vào thẻ: bình xoay 3D, rê ra: đứng yên
    return card;
}
