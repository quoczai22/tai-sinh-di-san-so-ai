// components/hero/index.js — ẢNH BÌA (hero) của mọi trang, dựng lại mỗi lần đổi trang (router gọi renderHero).
//  · Trang chủ: quạt thẻ Hiện vật → Hoa văn → Áo dài (fan.js) + hai nút kêu gọi.
//  · Studio, Kết quả: dải bìa hẹp, chỉ tiêu đề và mô tả.
// Mọi trang: băng ảnh thiết kế trôi phía sau (marquee.js). Mọi ảnh do AI hỗ trợ tạo đều mang nhãn AI.
// Vào: route (core/routes.js). Ghi vào các phần tử #hero, #page-title… có sẵn trong index.html.
import { clear, h } from '../../core/dom.js';
import { icon } from '../../core/icons.js';
import { parallax } from '../../core/scenes.js';
import { pauseOffscreen } from '../../core/motion.js';
import { splitWords } from '../../core/reveal.js';
import { libraryVisual } from './fan.js';
import { marquee } from './marquee.js';

let current = null;

export async function renderHero(route, params, info) {
    current?.destroy?.();
    current = null;
    const hero = document.getElementById('hero');
    pauseOffscreen(hero);
    const visual = clear(document.getElementById('hero-visual'));
    const actions = clear(document.getElementById('hero-actions'));
    const credit = document.getElementById('hero-credit');
    credit.textContent = '';
    const feature = route.id === 'library';
    hero.className = `hero ${feature ? 'feature' : 'band'} g-${route.chapter}`;
    hero.dataset.route = route.id;

    document.getElementById('page-eyebrow').replaceChildren(
        h('span', { class: 'eb-line', 'aria-hidden': 'true' }), route.group);
    splitWords(document.getElementById('page-title'), route.title);
    document.getElementById('page-lede').textContent = route.lede;

    const mq = document.getElementById('hero-marquee');
    if (!mq.childElementCount) marquee(mq);
    mq.dataset.parallax = '0.18';
    parallax();

    if (feature) {
        actions.append(
            h('a', { class: 'btn hero-btn primary', href: '#hien-vat', onclick: (e) => { e.preventDefault(); document.getElementById('hien-vat')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); } }, 'Khám phá hiện vật', icon('arrow')),
            h('a', { class: 'btn hero-btn ghost', href: '#/studio' }, 'Vào Studio thiết kế'));
        try { current = await libraryVisual(visual); } catch (e) { console.warn(e); }
    }
}
