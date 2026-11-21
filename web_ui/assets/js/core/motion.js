// core/motion.js — CHÍNH SÁCH CHUYỂN ĐỘNG dùng chung (không vẽ giao diện).
// Nguyên tắc: chỉ dùng transform / opacity; tôn trọng prefers-reduced-motion; số đếm chỉ là hiệu ứng.
// Ra: reduced()/calm() (đọc mức chuyển động), setMotion() (nút bật/tắt trong menu), applyMotionClass()
//     (gắn .motion-off/.calm lên <html> cho CSS), pauseOffscreen() (dừng hoạt ảnh khối khuất),
//     detectSlowMotion() (máy yếu → tự bật .calm), cycle() (trình chiếu tự chuyển của ảnh bìa).
// Hai mức:
//  · reduced(): người xem tự tắt chuyển động trong menu → tắt hết.
//  · calm():    hệ điều hành bật "giảm chuyển động" (người xem chưa chọn gì) → chỉ dừng các chuyển động
//               TỰ CHẠY (trình chiếu, băng ảnh trôi); hiệu ứng theo thao tác cuộn/rê chuột vẫn giữ.
const mq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };
const KEY = 'tsds-motion';
const AUTO_KEY = 'tsds-auto-calm';
const readPref = () => { try { return localStorage.getItem(KEY); } catch { return null; } };
let pref = readPref();
let autoCalm = false;
try { autoCalm = sessionStorage.getItem(AUTO_KEY) === '1'; } catch { /* bộ nhớ phiên có thể bị chặn */ }
export const reduced = () => pref === 'off';
export const calm = () => pref === 'off' || (pref !== 'on' && (mq.matches || autoCalm));
export function applyMotionClass() {
    document.documentElement.classList.toggle('motion-off', reduced());
    document.documentElement.classList.toggle('calm', calm());
}
export function setMotion(on) {
    pref = on ? 'on' : 'off';
    try { localStorage.setItem(KEY, pref); } catch { /* chế độ riêng tư: chỉ áp cho phiên này */ }
    applyMotionClass();
}
mq.addEventListener?.('change', applyMotionClass);

let offscreenObserver = null;
const offscreenObserved = new WeakSet();
/** Dừng hoạt ảnh CSS của một khối khi nó rời vùng nhìn. */
export function pauseOffscreen(el) {
    if (!el || !('IntersectionObserver' in window) || offscreenObserved.has(el)) return;
    if (!offscreenObserver) offscreenObserver = new IntersectionObserver((entries) => {
        for (const entry of entries) {
            if (entry.isIntersecting) delete entry.target.dataset.paused;
            else entry.target.dataset.paused = '';
        }
    }, { rootMargin: '100px' });
    offscreenObserved.add(el);
    offscreenObserver.observe(el);
}

/** Đo độ đều khung hình sau khi trang tải xong; chỉ áp cho lựa chọn mặc định. */
export function detectSlowMotion() {
    if (pref === 'on' || pref === 'off' || autoCalm || typeof requestAnimationFrame !== 'function') return;
    const measure = () => {
        if (document.hidden || pref === 'on' || pref === 'off') return;
        const intervals = [];
        let start = null;
        let previous = null;
        const onHidden = () => { if (document.hidden) cancelled = true; };
        let cancelled = false;
        document.addEventListener('visibilitychange', onHidden);
        const frame = (now) => {
            if (cancelled || document.hidden || pref === 'on' || pref === 'off') {
                document.removeEventListener('visibilitychange', onHidden);
                return;
            }
            if (start === null) start = now;
            if (previous !== null && now - start > 500) intervals.push(now - previous);
            previous = now;
            if (now - start < 2000) { requestAnimationFrame(frame); return; }
            document.removeEventListener('visibilitychange', onHidden);
            if (!intervals.length) return;
            intervals.sort((a, b) => a - b);
            const mid = Math.floor(intervals.length / 2);
            const median = intervals.length % 2 ? intervals[mid] : (intervals[mid - 1] + intervals[mid]) / 2;
            if (1000 / median >= 40) return;
            autoCalm = true;
            try { sessionStorage.setItem(AUTO_KEY, '1'); } catch { /* bộ nhớ phiên có thể bị chặn */ }
            applyMotionClass();
            console.info('FPS thấp: tự bật chế độ máy yếu.');
        };
        requestAnimationFrame(frame);
    };
    if (document.readyState === 'complete') measure();
    else window.addEventListener('load', measure, { once: true });
}

/** Trình chiếu tự chuyển: gọi show(i) theo chu kỳ, dừng khi rời tab hoặc khi người dùng giảm chuyển động. */
export function cycle(count, show, interval = 5200) {
    let i = 0;
    let timer = null;
    show(0);
    if (count < 2 || calm()) return { destroy() {}, pause() {}, go: (k) => { i = k; show(k); } };
    const stop = () => { if (timer) clearInterval(timer); timer = null; };
    const start = () => { stop(); timer = setInterval(() => { i = (i + 1) % count; show(i); }, interval); };
    const onVis = () => (document.hidden ? stop() : start());
    document.addEventListener('visibilitychange', onVis);
    start();
    let paused = false;
    return {
        destroy() { stop(); document.removeEventListener('visibilitychange', onVis); },
        // Người xem đã tương tác (bấm vào thẻ): dừng tự chuyển cho tới khi họ chọn bộ khác.
        pause() { paused = true; stop(); document.removeEventListener('visibilitychange', onVis); },
        go: (k) => { i = k; show(k); if (!paused) start(); },
    };
}
