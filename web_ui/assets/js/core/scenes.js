// core/scenes.js — CẢNH CUỘN: "cuộn tới đâu, hình biến đổi tới đó" (không vẽ giao diện).
// Ra: scenes() (router gọi sau mỗi lần đổi trang), requestScene(), parallax() (ảnh bìa trôi chậm).
// Ghi biến CSS --e/--p/--x lên [data-scene] và --pp lên [data-pin]; CSS của từng component đọc các biến này.
import { reduced } from './motion.js';

/** Thị sai: phần tử có data-parallax="0.25" trôi chậm hơn trang khi cuộn. */
let parallaxBound = false;
export function parallax() {
    if (parallaxBound || reduced()) return;
    parallaxBound = true;
    let ticking = false;
    const run = () => {
        ticking = false;
        const y = window.scrollY;
        for (const el of document.querySelectorAll('[data-parallax]')) {
            const f = Number(el.dataset.parallax) || 0;
            el.style.transform = `translate3d(0, ${(y * f).toFixed(1)}px, 0)`;
        }
    };
    window.addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(run); } }, { passive: true });
}

/* ------------------------------------------------------------------------------------------
   Cảnh cuộn: "cuộn tới đâu, hình biến đổi tới đó".
   Phần tử [data-scene] nhận ba biến CSS theo vị trí của nó trong khung nhìn:
     --e  vào khung: 0 khi mép trên chạm đáy màn hình → 1 khi mép trên lên tới ~30% từ đỉnh
     --p  đi qua:    0 khi mép trên chạm đáy → 1 khi mép dưới chạm đỉnh (0,5 ≈ nằm giữa)
     --x  rời khung: 0 khi mép trên ở đỉnh → 1 khi đã cuộn hết chiều cao phần tử
   Khối [data-pin] (màn hình rộng): phần dính giữ nguyên, băng [data-pin-track] trượt ngang theo
   tiến độ cuộn dọc; khối tự kéo dài đúng bằng quãng trượt. Biến --pp = tiến độ 0→1.
   Giá trị được nội suy mỗi khung hình nên chuyển động trôi mượt, không giật theo nấc bánh xe.
   Giảm chuyển động: biến nhảy thẳng tới giá trị đích, khối dính tắt.
   ------------------------------------------------------------------------------------------ */
const clamp01 = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);
const sceneState = new WeakMap();
let sceneBound = false;
let sceneQueued = false;
const pinWide = window.matchMedia ? window.matchMedia('(min-width: 981px)') : { matches: true };

function sceneTargets(el, vh) {
    const r = el.getBoundingClientRect();
    return [clamp01((vh - r.top) / (vh * 0.7)), clamp01((vh - r.top) / (vh + r.height)), clamp01(-r.top / Math.max(r.height, 1))];
}

// Giá trị biến CSS đã ghi lần trước: chỉ ghi lại khi đổi, tránh làm trình duyệt tính lại style
// cho cả cây con của mọi khối [data-scene] ở mỗi khung hình khi trang đứng yên hoặc khối ở xa.
const sceneWritten = new WeakMap();

function sceneFrame() {
    sceneQueued = false;
    const vh = window.innerHeight;
    const k = reduced() ? 1 : 0.13;
    let moving = false;
    const step = (el, target, names) => {
        const cur = sceneState.get(el) || target;
        const next = cur.map((c, i) => {
            const d = target[i] - c;
            if (Math.abs(d) > 0.0005) { moving = true; return c + d * k; }
            return target[i];
        });
        sceneState.set(el, next);
        const prev = sceneWritten.get(el) || [];
        const vals = next.map((v) => v.toFixed(4));
        vals.forEach((v, i) => { if (prev[i] !== v) el.style.setProperty(names[i], v); });
        sceneWritten.set(el, vals);
    };
    // Đọc vị trí của mọi khối TRƯỚC, rồi mới ghi biến CSS: đọc-ghi xen kẽ bắt trình duyệt tính lại
    // bố cục (forced layout) một lần cho mỗi khối trong cùng một khung hình.
    const scenesNow = [...document.querySelectorAll('[data-scene]')];
    const targets = scenesNow.map((el) => sceneTargets(el, vh));
    scenesNow.forEach((el, i) => step(el, targets[i], ['--e', '--p', '--x']));
    for (const wrap of document.querySelectorAll('[data-pin]')) {
        const track = wrap.querySelector('[data-pin-track]');
        const sticky = track?.parentElement;
        if (!track || !sticky) continue;
        if (!pinWide.matches || reduced()) {
            wrap.classList.remove('pinned');
            wrap.style.height = '';
            track.style.transform = '';
            continue;
        }
        wrap.classList.add('pinned');
        const travel = Math.max(0, track.scrollWidth - sticky.clientWidth);
        const want = `${Math.round(vh + travel)}px`;
        if (wrap.style.height !== want) wrap.style.height = want;
        const r = wrap.getBoundingClientRect();
        const t = travel > 0 ? clamp01(-r.top / travel) : 0;
        step(wrap, [t], ['--pp']);
        const pp = sceneState.get(wrap)[0];
        track.style.transform = `translate3d(${(-travel * pp).toFixed(1)}px, 0, 0)`;
    }
    if (moving) requestScene();
}

export function requestScene() {
    if (sceneQueued) return;
    sceneQueued = true;
    requestAnimationFrame(sceneFrame);
}

export function scenes() {
    if (sceneBound) { requestScene(); return; }
    sceneBound = true;
    window.addEventListener('scroll', requestScene, { passive: true });
    window.addEventListener('resize', requestScene);
    pinWide.addEventListener?.('change', requestScene);
    requestScene();
}
