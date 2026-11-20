// Ảnh bìa (hero) cho từng khu vực, theo lối trình bày triển lãm số:
//  · Thư viện: "quạt thẻ" kể chuỗi Hiện vật → Hoa văn → Áo dài, tự chuyển giữa các hiện vật đang dùng.
//  · Studio có hiện vật: ảnh hiện vật tách nền lơ lửng.
//  · Các khu vực khác: số chương lớn + băng ảnh thiết kế trôi chậm phía sau.
// Mọi ảnh do AI hỗ trợ tạo đều mang nhãn AI (aiMark). Không có số liệu nào viết cứng.
import { clear, h, icon } from './dom.js';
import * as data from './data.js';
import { cycle, parallax, pauseOffscreen, reduced, splitWords } from './motion.js';
import { aiMark } from './ui.js';

let current = null;
const PREF = ['pending_expert_review', 'qa_warning', 'revision_requested', 'approved', 'qa_failed'];

const patternOf = (d) => (d.thumb ? d.thumb.replace(/final_img2img\.webp$/, 'pattern.webp') : null);
const latestOf = (d) => (d.latest_version_kind === 'system_repair' && d.repair_thumb ? d.repair_thumb : d.thumb);

function pickPassport(list) {
    return [...list].filter((d) => d.thumb)
        .sort((a, b) => (PREF.indexOf(a.approval.status) - PREF.indexOf(b.approval.status)) || a.passport_id.localeCompare(b.passport_id))[0];
}

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

async function libraryVisual(root) {
    const [{ items }, passports] = await Promise.all([data.heritage(), data.passports()]);
    const sets = items.filter((i) => i.status === 'active').map((it) => ({ it, d: pickPassport(passports.filter((p) => p.heritage_id === it.id)) }))
        .filter((s) => s.d);
    if (!sets.length) return null;
    const stage = h('div', { class: 'fan-stage' });
    const dots = h('div', { class: 'fan-dots', role: 'group', 'aria-label': 'Chọn hiện vật trình chiếu' });
    const setEls = sets.map(({ it, d }) => h('div', { class: 'fan-set' },
        fanCard('c1', 'Hiện vật', it.image, false, true),
        fanCard('c2', 'Hoa văn', `./${patternOf(d)}`, true),
        fanCard('c3', 'Áo dài', `./${latestOf(d)}`, true)));
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

async function studioVisual(root, heritageId) {
    const { items } = await data.heritage();
    const it = items.find((i) => i.id === heritageId);
    if (!it) return null;
    root.append(h('div', { class: 'float-artifact', 'data-parallax': '-0.08' },
        h('div', { class: 'float-halo', 'aria-hidden': 'true' }),
        h('img', { src: it.image, alt: it.name }),
        h('p', { class: 'float-cap' }, it.name)));
    return null;
}

async function marquee(el) {
    clear(el);
    let list = [];
    try { list = (await data.passports()).filter((d) => d.thumb); } catch { return; }
    if (!list.length) return;
    const row = (items, cls) => h('div', { class: `mq-row ${cls}` },
        [...items, ...items].map((d) => h('img', { src: `./${d.thumb}`, alt: '', loading: 'lazy', decoding: 'async' })));
    const half = Math.ceil(list.length / 2);
    el.append(row(list.slice(0, half), 'a'), row(list.slice(half), 'b'));
}

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
    } else if (route.id === 'studio' && params[0]) {
        // Ảnh hiện vật đã nằm ở khung "Đầu vào" bên dưới, không lặp lại trên ảnh bìa
    } else {
        visual.append(h('div', { class: 'chapter-mark', 'aria-hidden': 'true' }, route.chapter));
    }
}
