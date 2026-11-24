// core/router.js — ĐỊNH TUYẾN theo hash (#/library, #/studio/<mã>, #/result/<mã>) và vòng đời một lần đổi trang:
// tải view (lười) → dựng trang mới trong lúc trang cũ còn hiện → mờ chéo (View Transitions) → renderHero +
// gắn nội dung → enhance (hiện dần) + scenes (cảnh cuộn). Lỗi tải trang hiện stateBox có nút Tải lại.
// Ra: startRouter(info) (app.js gọi một lần sau data.init).
import { clear, h } from './dom.js';
import { reduced } from './motion.js';
import { enhance } from './reveal.js';
import { scenes } from './scenes.js';
import { ROUTES } from './routes.js';
import { renderHero } from '../components/hero/index.js';
import { stateBox } from '../components/layout.js';
import { closeMenu, onScroll, renderNav } from '../components/nav.js';

let info = { mode: 'demo' };

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
    const args = params.map((p) => { try { return decodeURIComponent(p); } catch { return p; } });   // tham số sai định dạng giữ nguyên, không làm hỏng việc đổi trang
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

export function startRouter(initInfo) {
    info = initInfo;
    window.addEventListener('hashchange', route);
    route();
}
