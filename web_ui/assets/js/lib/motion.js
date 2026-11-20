// Chuyển động của giao diện triển lãm. Nguyên tắc:
//  · chỉ dùng transform / opacity (không làm giật bố cục);
//  · tôn trọng prefers-reduced-motion: tắt hết, nội dung hiện ngay;
//  · số đếm chạy chỉ là hiệu ứng hiển thị — giá trị cuối luôn đúng số liệu thật.
import { h, icon } from './dom.js';

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

const REVEAL = [
    '.section-head', '.panel', '.stat', '.artifact', '.design', '.journey-card', '.table-wrap',
    '.chain-node', '.state', '.criteria-card', '.diagram', '.compare .side', '.queue-layout', '.studio-head',
    '.passport-head', '.review-layout', '.rail-card', '.chapter-intro', '.quote-band',
].join(',');

let observer = null;
function getObserver() {
    if (observer) return observer;
    observer = new IntersectionObserver((entries) => {
        for (const e of entries) {
            if (!e.isIntersecting) continue;
            const el = e.target;
            el.classList.add('in');
            observer.unobserve(el);
            el.querySelectorAll?.('.stat .value, .count-up').forEach(countUp);
            if (el.matches?.('.stat .value, .count-up')) countUp(el);
            if (el.classList.contains('stat')) el.querySelectorAll('.value').forEach(countUp);
        }
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    return observer;
}

/** Gắn hiệu ứng "hiện dần khi cuộn" cho mọi khối nội dung trong root, so le theo thứ tự anh em. */
export function enhance(root) {
    if (!root) return;
    const els = [...root.querySelectorAll(REVEAL)];
    if (root.matches?.(REVEAL)) els.unshift(root);
    if (reduced() || !('IntersectionObserver' in window)) {
        els.forEach((el) => el.classList.add('reveal', 'in'));
        return;
    }
    const obs = getObserver();
    for (const el of els) {
        if (el.classList.contains('reveal')) continue;
        const siblings = el.parentElement ? [...el.parentElement.children] : [el];
        const i = Math.min(siblings.indexOf(el), 8);
        el.style.setProperty('--i', String(Math.max(0, i)));
        el.classList.add('reveal');
        obs.observe(el);
    }
}

/** Đếm số từ 0 tới giá trị thật. Chỉ áp cho chữ dạng "24" hoặc "24/120". */
export function countUp(el) {
    if (!el || el.dataset.counted) return;
    el.dataset.counted = '1';
    const text = el.firstChild && el.firstChild.nodeType === 3 ? el.firstChild.textContent : el.textContent;
    const m = /^\s*(\d{1,6})(?:\/(\d{1,6}))?\s*$/.exec(text || '');
    if (!m || reduced()) return;
    const a = Number(m[1]);
    const b = m[2] !== undefined ? Number(m[2]) : null;
    const node = el.firstChild && el.firstChild.nodeType === 3 ? el.firstChild : el;
    const final = text;
    const t0 = performance.now();
    const dur = 1100;
    const tick = (now) => {
        const p = Math.min(1, (now - t0) / dur);
        const k = 1 - (1 - p) ** 3;
        node.textContent = b === null ? String(Math.round(a * k)) : `${Math.round(a * k)}/${Math.round(b * k)}`;
        if (p < 1) requestAnimationFrame(tick);
        else node.textContent = final;
    };
    requestAnimationFrame(tick);
}

/** Tách tiêu đề thành từng từ để chạy hiệu ứng trồi lên. Dùng textContent, không innerHTML. */
export function splitWords(el, text) {
    el.replaceChildren();
    el.setAttribute('aria-label', text);
    text.split(/\s+/).filter(Boolean).forEach((w, i, arr) => {
        const outer = h('span', { class: 'w', 'aria-hidden': 'true' }, h('span', { style: { '--i': String(i) } }, w));
        el.append(outer, i < arr.length - 1 ? ' ' : '');
    });
}

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

/** Nghiêng 3D nhẹ theo con trỏ (chỉ thiết bị có chuột). */
export function tilt(el, max = 7) {
    if (reduced() || !window.matchMedia('(hover: hover) and (pointer: fine)').matches) return el;
    el.addEventListener('pointermove', (e) => {
        const r = el.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        el.style.setProperty('--ry', `${(x * max).toFixed(2)}deg`);
        el.style.setProperty('--rx', `${(-y * max).toFixed(2)}deg`);
    });
    el.addEventListener('pointerleave', () => { el.style.setProperty('--ry', '0deg'); el.style.setProperty('--rx', '0deg'); });
    return el;
}

/** Băng thẻ cuộn ngang có nút trước/sau, cuộn bằng bánh xe/vuốt, bám điểm (scroll-snap). */
export function rail(cards, { label = 'Danh sách', className = '' } = {}) {
    const track = h('div', { class: 'rail-track', role: 'list', 'aria-label': label, tabindex: '0' }, cards);
    const prev = h('button', { class: 'rail-btn prev', type: 'button', 'aria-label': 'Xem mục trước' }, icon('chev'));
    const next = h('button', { class: 'rail-btn next', type: 'button', 'aria-label': 'Xem mục tiếp' }, icon('chev'));
    const bar = h('span');
    const progress = h('div', { class: 'rail-progress', 'aria-hidden': 'true' }, bar);
    const step = () => Math.max(track.clientWidth * 0.8, 240);
    prev.addEventListener('click', () => track.scrollBy({ left: -step(), behavior: reduced() ? 'auto' : 'smooth' }));
    next.addEventListener('click', () => track.scrollBy({ left: step(), behavior: reduced() ? 'auto' : 'smooth' }));
    const update = () => {
        const max = track.scrollWidth - track.clientWidth;
        prev.disabled = track.scrollLeft <= 4;
        next.disabled = track.scrollLeft >= max - 4;
        const ratio = max > 0 ? track.clientWidth / track.scrollWidth : 1;
        bar.style.width = `${Math.max(ratio, 0.08) * 100}%`;
        bar.style.transform = `translateX(${max > 0 ? (track.scrollLeft / max) * ((1 / Math.max(ratio, 0.08)) - 1) * 100 : 0}%)`;
        navEl.hidden = max <= 4;
    };
    const navEl = h('div', { class: 'rail-nav' }, progress, prev, next);
    track.addEventListener('scroll', update, { passive: true });
    new ResizeObserver(update).observe(track);
    requestAnimationFrame(update);
    return h('div', { class: `rail ${className}` }, track, navEl);
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

/** Câu văn sáng dần từng chữ theo vị trí cuộn (dùng --p của khối cha [data-scene]). */
export function litWords(el, text) {
    el.replaceChildren();
    el.setAttribute('aria-label', text);
    const words = text.split(/\s+/).filter(Boolean);
    el.style.setProperty('--n', String(words.length));
    words.forEach((w, i) => el.append(h('span', { class: 'lw', 'aria-hidden': 'true', style: { '--i': String(i) } }, w), i < words.length - 1 ? ' ' : ''));
    return el;
}
