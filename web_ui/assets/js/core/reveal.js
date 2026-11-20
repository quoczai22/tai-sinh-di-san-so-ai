// core/reveal.js — HIỆU ỨNG HIỆN DẦN của nội dung: khối trồi lên khi cuộn tới, số đếm, chữ tách từng từ.
// Ra: enhance(root) (router gọi sau mỗi lần đổi trang), countUp(), splitWords() (tiêu đề ảnh bìa),
//     litWords() (câu "Lời mở" sáng dần theo --p của khối [data-scene]).
import { h } from './dom.js';
import { reduced } from './motion.js';

// Khối nội dung được "hiện dần" (chỉ các class còn có trong giao diện hiện tại)
const REVEAL = [
    '.section-head', '.artifact', '.design', '.journey-card', '.state', '.chapter-intro',
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

/** Câu văn sáng dần từng chữ theo vị trí cuộn (dùng --p của khối cha [data-scene]). */
export function litWords(el, text) {
    el.replaceChildren();
    el.setAttribute('aria-label', text);
    const words = text.split(/\s+/).filter(Boolean);
    el.style.setProperty('--n', String(words.length));
    words.forEach((w, i) => el.append(h('span', { class: 'lw', 'aria-hidden': 'true', style: { '--i': String(i) } }, w), i < words.length - 1 ? ' ' : ''));
    return el;
}
