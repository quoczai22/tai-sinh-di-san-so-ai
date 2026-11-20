// components/nav.js — THANH ĐIỀU HƯỚNG + MENU TOÀN MÀN HÌNH + CHÂN TRANG + SỢI CHỈ TIẾN ĐỘ CUỘN.
// Ghi vào các khung có sẵn trong index.html (#nav-left, #nav, #menu-chapters, #foot-links, #scroll-thread).
// Ra: renderNav(mã trang đang mở) (router gọi mỗi lần đổi trang), closeMenu(), onScroll() (cập nhật nền thanh trên + sợi chỉ).
// Có nút bật/tắt chuyển động (core/motion.setMotion) trong menu.
import { clear, h } from '../core/dom.js';
import { icon } from '../core/icons.js';
import { reduced, setMotion } from '../core/motion.js';
import { CHAPTER_NOTE, ROUTES } from '../core/routes.js';

/* ---------- Điều hướng trên cùng + menu toàn màn hình ---------- */
export function renderNav(active) {
    // Logo ở giữa: các mục chính bên trái, nút menu bên phải.
    const primaries = ROUTES.filter((x) => x.primary);
    const link = (r) => h('a', { href: `#/${r.id}`, 'aria-current': r.id === active ? 'page' : null }, r.short);
    clear(document.getElementById('nav-left')).append(...primaries.slice(0, 2).map(link));
    clear(document.getElementById('nav')).append(...primaries.slice(2).map(link));
    const menu = clear(document.getElementById('menu-chapters'));
    const shown = ROUTES.filter((r) => !r.hidden);
    const groups = [...new Set(shown.map((r) => r.group))];
    groups.forEach((g, gi) => {
        menu.append(h('section', { class: 'menu-chapter', style: { '--i': String(gi) } },
            h('h2', { class: 'menu-group' }, g),
            CHAPTER_NOTE[g] ? h('p', { class: 'menu-note' }, CHAPTER_NOTE[g]) : null,
            h('ul', {}, shown.filter((r) => r.group === g).map((r) => h('li', {},
                h('a', { href: `#/${r.id}`, 'aria-current': r.id === active ? 'page' : null, onclick: () => closeMenu() },
                    icon(r.icon), h('span', {}, r.label), icon('arrow', 'go')))))));
    });
    const toggle = h('button', { class: 'motion-toggle', type: 'button', 'aria-pressed': String(!reduced()),
        onclick: () => { setMotion(reduced()); toggle.setAttribute('aria-pressed', String(!reduced())); label.textContent = reduced() ? 'Chuyển động: tắt' : 'Chuyển động: bật'; } },
    h('span', { class: 'sw', 'aria-hidden': 'true' }));
    const label = h('span', {}, reduced() ? 'Chuyển động: tắt' : 'Chuyển động: bật');
    toggle.append(label);
    menu.parentElement.querySelector('.motion-toggle')?.remove();
    menu.after(toggle);
    const foot = clear(document.getElementById('foot-links'));
    groups.forEach((g) => foot.append(h('div', {}, h('p', { class: 'foot-group' }, g),
        shown.filter((r) => r.group === g).map((r) => h('a', { href: `#/${r.id}` }, r.label)))));
}

const menuBtn = document.getElementById('menu-btn');
const overlay = document.getElementById('menu-overlay');
function openMenu() {
    overlay.hidden = false;
    document.body.classList.add('menu-open');
    menuBtn.setAttribute('aria-expanded', 'true');
    requestAnimationFrame(() => requestAnimationFrame(() => overlay.classList.add('open')));
    setTimeout(() => overlay.querySelector('a[aria-current="page"], a')?.focus(), reduced() ? 0 : 280);
}
export function closeMenu() {
    if (overlay.hidden) return;
    overlay.classList.remove('open');
    document.body.classList.remove('menu-open');
    menuBtn.setAttribute('aria-expanded', 'false');
    setTimeout(() => { overlay.hidden = true; }, reduced() ? 0 : 420);
    menuBtn.focus({ preventScroll: true });
}
menuBtn.addEventListener('click', () => (overlay.hidden ? openMenu() : closeMenu()));
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !overlay.hidden) closeMenu(); });

/* ---------- Cuộn: thanh điều hướng đổi nền, sợi chỉ lam báo tiến độ ---------- */
const topnav = document.getElementById('topnav');
const thread = document.querySelector('#scroll-thread span');
let ticking = false;
export function onScroll() {
    ticking = false;
    const hero = document.getElementById('hero');
    const y = window.scrollY;
    topnav.classList.toggle('solid', y > Math.max(40, hero.offsetHeight - 80));
    const max = document.documentElement.scrollHeight - window.innerHeight;
    thread.style.transform = `scaleX(${max > 0 ? Math.min(1, y / max) : 0})`;
}
window.addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
