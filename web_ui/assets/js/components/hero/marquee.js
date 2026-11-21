// components/hero/marquee.js — BĂNG ẢNH THIẾT KẾ trôi chậm phía sau ảnh bìa (hai hàng, lặp đôi để trôi liền).
// Vào: data.passports(). Ra: marquee(el) — chỉ dựng một lần, các lần đổi trang sau giữ nguyên.
import { clear, h } from '../../core/dom.js';
import * as data from '../../core/data.js';
import { assetUrl } from '../../core/designs.js';

export async function marquee(el) {
    clear(el);
    let list = [];
    try { list = (await data.passports()).filter((d) => d.thumb); } catch { return; }
    if (!list.length) return;
    const row = (items, cls) => h('div', { class: `mq-row ${cls}` },
        [...items, ...items].map((d) => h('img', { src: assetUrl(d.thumb), alt: '', loading: 'lazy', decoding: 'async' })));
    const half = Math.ceil(list.length / 2);
    el.append(row(list.slice(0, half), 'a'), row(list.slice(half), 'b'));
}
