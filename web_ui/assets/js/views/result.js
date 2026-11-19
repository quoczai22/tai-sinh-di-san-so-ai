import { h } from '../lib/dom.js';
import * as data from '../lib/data.js';
import { aiMark, stateBox } from '../lib/ui.js';

// ---------------------------------------------------------------------------------------------
// Trang Kết quả: bốn tà áo của bộ thiết kế mới nhất của hiện vật (#/result/<mã hiện vật>).
// Chỉ có ảnh: không bảng chỉ số, không khung chi tiết, không ghi chú.
// ---------------------------------------------------------------------------------------------
const latestOf = (d) => (d.latest_version_kind === 'system_repair' && d.repair_thumb ? d.repair_thumb : d.thumb);

function designCard(d, n) {
    return h('article', { class: 'design out-card', style: { '--k': String(n - 1) } },
        h('div', { class: 'pic' }, h('img', { src: data.media(d.final_path, latestOf(d)), alt: `Thiết kế ${n}`, loading: 'lazy' }), aiMark()),
        h('div', { class: 'body' },
            h('span', { class: 'title' }, `Thiết kế ${n}`)));
}

export async function render([heritageId]) {
    const { items } = await data.heritage();
    const item = items.find((i) => i.id === heritageId);
    const all = (await data.passports()).filter((p) => p.heritage_id === heritageId && p.thumb);
    const run = [...new Set(all.map((p) => p.run_id))].sort().reverse()[0];
    const designs = all.filter((p) => p.run_id === run).sort((a, b) => a.passport_id.localeCompare(b.passport_id));
    const studio = item ? `#/studio/${encodeURIComponent(item.id)}` : '#/studio';
    if (!item || !designs.length) {
        return stateBox('', 'Chưa có thiết kế', 'Hiện vật này chưa có bộ thiết kế nào.', h('a', { class: 'btn primary', href: '#/studio' }, 'Về Studio'));
    }
    const grid = h('div', { class: 'out-grid' }, designs.map((d, k) => designCard(d, k + 1)));
    requestAnimationFrame(() => grid.classList.add('shown'));
    return h('div', { class: 'result' },
        h('div', { class: 'result-head' },
            h('div', { class: 'result-artifact' }, h('img', { src: item.image, alt: '' })),
            h('h2', { class: 'io-name' }, item.name)),
        grid,
        h('div', { class: 'result-actions' },
            h('a', { class: 'btn hero-btn primary', href: studio }, 'Tạo lại'),
            h('a', { class: 'btn hero-btn ghost', href: '#/studio' }, 'Chọn hiện vật khác')));
}
