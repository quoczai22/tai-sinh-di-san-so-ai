// components/hero/fan.js — QUẠT THẺ ở ảnh bìa trang chủ: kể chuỗi Hiện vật → Hoa văn → Áo dài, tự chuyển giữa
// các hiện vật đang dùng (cycle), bấm một thẻ thì thẻ đó rút lên trên cùng.
// Vào: data.heritage() + data.passports(). Ra: libraryVisual(root) → bộ điều khiển trình chiếu (destroy/pause/go).
import { h } from '../../core/dom.js';
import * as data from '../../core/data.js';
import { assetUrl, latestOf, patternOf, pickPassport } from '../../core/designs.js';
import { cycle, reduced } from '../../core/motion.js';
import { aiMark } from '../badges.js';

// Bấm vào một thẻ: thẻ trượt ra khỏi xấp, rồi chèn lên trên cùng (như rút một lá bài).
// Thứ tự lớp chỉ đổi ở giữa chuyển động, khi thẻ đã ra ngoài, nên không có cảnh hình đè giật.
function bringToFront(card) {
    const set = card.parentElement;
    if (!set || card.classList.contains('front')) return;
    const others = [...set.children].filter((c) => c !== card);
    const apply = () => {
        others.forEach((c) => { c.classList.remove('front'); c.style.zIndex = ''; });
        card.classList.add('front');
        card.style.zIndex = '6';
    };
    if (reduced() || !card.animate) { apply(); return; }
    const dir = card.classList.contains('c1') ? -1 : card.classList.contains('c3') ? 1 : 0;
    const out = `translate(${dir * 22}%, ${dir ? -6 : -24}%)`;
    const anim = card.animate([
        { transform: 'translate(0, 0)' },
        { transform: out, offset: 0.45 },
        { transform: 'translate(0, 0)' },
    ], { duration: 720, easing: 'cubic-bezier(.45, 0, .2, 1)', composite: 'add' });
    setTimeout(apply, 320);
    anim.finished.catch(() => {});
}

function fanCard(kind, label, src, ai, contain) {
    return h('figure', { class: `fan-card ${kind}`, onclick: (e) => bringToFront(e.currentTarget) },
        h('div', { class: `fan-img ${contain ? 'contain' : ''}` }, src ? h('img', { src, alt: '', loading: 'eager', decoding: 'async' }) : null),
        h('figcaption', {}, h('span', { class: 'fan-step' }, label), ai ? aiMark() : null));
}

export async function libraryVisual(root) {
    const [{ items }, passports] = await Promise.all([data.heritage(), data.passports()]);
    const sets = items.filter((i) => i.status === 'active').map((it) => ({ it, d: pickPassport(passports.filter((p) => p.heritage_id === it.id)) }))
        .filter((s) => s.d);
    if (!sets.length) return null;
    const stage = h('div', { class: 'fan-stage' });
    const dots = h('div', { class: 'fan-dots', role: 'group', 'aria-label': 'Chọn hiện vật trình chiếu' });
    const setEls = sets.map(({ it, d }) => h('div', { class: 'fan-set' },
        fanCard('c1', 'Hiện vật', it.image, false, true),
        fanCard('c2', 'Hoa văn', assetUrl(patternOf(d)), true),
        fanCard('c3', 'Áo dài', assetUrl(latestOf(d)), true)));
    stage.append(...setEls);
    const dotEls = sets.map(({ it }, k) => h('button', { type: 'button', 'aria-label': it.name, onclick: () => ctl.go(k) }));
    dots.append(...dotEls);
    const show = (k) => {
        setEls.forEach((el, j) => {
            el.classList.toggle('on', j === k);
            if (j !== k) [...el.children].forEach((c) => { c.classList.remove('front'); c.style.zIndex = ''; });
        });
        dotEls.forEach((el, j) => el.setAttribute('aria-pressed', String(j === k)));
    };
    const ctl = cycle(sets.length, show, 5600);
    stage.addEventListener('click', () => ctl.pause());
    root.append(stage, h('div', { class: 'fan-meta' }, dots));
    return ctl;
}
