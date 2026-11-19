import { clear, h, icon } from './lib/dom.js';
import * as data from './lib/data.js';
import { renderHero } from './lib/hero.js';
import { applyMotionClass, enhance, reduced, scenes, setMotion } from './lib/motion.js';
import { stateBox } from './lib/ui.js';

// Web chỉ dành cho người xem: Trang chủ, Studio (chọn hiện vật) và Kết quả (4 tà áo). Hồ sơ nghiệp vụ (kiểm định, thí nghiệm, thẩm định, Passport,
// BPMN, KPI) nằm trong dữ liệu, API và docs/finals — không đưa lên web.
const CHAPTER = { 'Khám phá': '01' };
const CHAPTER_NOTE = {};

const ROUTES = [
    { group: 'Khám phá', id: 'library', label: 'Trang chủ', short: 'Trang chủ', icon: 'library', primary: true, load: () => import('./views/library.js'),
      title: 'Thư viện di sản', lede: 'Hoa văn trên gốm Bát Tràng, chọn lọc và ghi nguồn, làm chất liệu cho tà áo dài.' },
    { group: 'Khám phá', id: 'studio', label: 'Studio thiết kế', short: 'Studio', icon: 'studio', primary: true, load: () => import('./views/studio.js'),
      title: 'Studio thiết kế', lede: 'Chọn một hiện vật, bấm tạo, nhận bốn thiết kế áo dài dệt từ hoa văn của nó.' },
    // Trang Kết quả chỉ vào qua nút Tạo thiết kế, không nằm trong menu
    { group: 'Khám phá', id: 'result', label: 'Kết quả', short: 'Kết quả', icon: 'studio', hidden: true, load: () => import('./views/result.js'),
      title: 'Kết quả thiết kế', lede: 'Bốn thiết kế áo dài dệt từ hoa văn của hiện vật bạn chọn.' },
].map((r) => ({ ...r, chapter: CHAPTER[r.group] }));

let info = { mode: 'demo' };

/* ---------- Điều hướng trên cùng + menu toàn màn hình ---------- */
function renderNav(active) {
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
function closeMenu() {
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
function onScroll() {
    ticking = false;
    const hero = document.getElementById('hero');
    const y = window.scrollY;
    topnav.classList.toggle('solid', y > Math.max(40, hero.offsetHeight - 80));
    const max = document.documentElement.scrollHeight - window.innerHeight;
    thread.style.transform = `scaleX(${max > 0 ? Math.min(1, y / max) : 0})`;
}
window.addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });

/* ---------- Định tuyến ---------- */
let seq = 0;
async function route() {
    const my = ++seq;
    const [, id = 'library', ...params] = (location.hash || '#/library').split('/');
    const r = ROUTES.find((x) => x.id === id) || ROUTES[0];
    closeMenu();
    renderNav(r.id);
    document.title = `${r.title} — Tái Sinh Di Sản Số`;
    const main = document.getElementById('main');
    const args = params.map(decodeURIComponent);
    // Chuẩn bị trang mới trong khi trang cũ vẫn hiển thị; chỉ hiện khung chờ nếu tải lâu.
    const slow = setTimeout(() => { if (my === seq) clear(main).append(h('div', { class: 'skeleton', style: { minHeight: '240px' }, 'aria-label': 'Đang tải' })); }, 450);
    let view;
    try {
        const mod = await r.load();
        view = await mod.render(args);
    } catch (err) {
        console.error(err);
        view = stateBox('error', 'Không tải được trang này', err.message || String(err),
            h('button', { class: 'btn', onclick: route }, 'Tải lại'));
    }
    clearTimeout(slow);
    if (my !== seq) return;
    let heroDone;
    let swapped = false;
    const swap = () => {
        if (swapped) return;
        swapped = true;
        window.scrollTo({ top: 0, behavior: 'instant' });
        heroDone = renderHero(r, args, info);
        clear(main).append(view);
        enhance(main);
        scenes();
    };
    // Chuyển cảnh mờ chéo khi trình duyệt hỗ trợ và tab đang hiển thị. Trình duyệt có thể huỷ
    // chuyển cảnh (tab ẩn, đổi kích thước giữa chừng) — khi đó vẫn đổi trang ngay, không để trống.
    // Lần tải đầu không cần chuyển cảnh (chưa có trang cũ để mờ chéo).
    if (main.childElementCount && document.startViewTransition && !reduced() && document.visibilityState === 'visible') {
        try {
            const vt = document.startViewTransition(swap);
            vt.ready.catch(() => {});
            vt.finished.catch(() => {});
            // Chuyển cảnh chờ khung hình kế tiếp; nếu trình duyệt chưa vẽ (cửa sổ bị che, máy bận)
            // thì không chờ quá 400 ms và huỷ hẳn để lớp ảnh chụp trang cũ không phủ lên trang mới.
            const done = await Promise.race([vt.updateCallbackDone.then(() => true, () => true), new Promise((res) => setTimeout(() => res(false), 400))]);
            if (!done) vt.skipTransition();
        } catch { /* trình duyệt từ chối: đổi trang thường */ }
        swap();
    } else {
        swap();
    }
    await heroDone;
    main.focus({ preventScroll: true });
    onScroll();
}

// Liên kết nội bộ dạng "#id" (không phải "#/route") chỉ cuộn tới phần tử, không đổi trang
window.addEventListener('click', (e) => {
    const a = e.target.closest?.('a[href^="#"]');
    if (!a) return;
    const href = a.getAttribute('href');
    if (href.startsWith('#/') || href === '#') return;
    const target = document.getElementById(href.slice(1));
    if (target) { e.preventDefault(); target.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'start' }); if (target.tabIndex >= -1) target.focus?.({ preventScroll: true }); }
});

applyMotionClass();
(async () => {
    info = await data.init();
    window.addEventListener('hashchange', route);
    route();
})();
