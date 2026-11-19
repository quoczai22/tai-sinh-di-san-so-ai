// Bộ sưu tập cho người xem: chỉ ảnh áo dài, tên hiện vật nguồn và cách đặt hoa văn.
// Bấm vào một tà áo để xem chi tiết (ảnh lớn, hiện vật nguồn, ghi công). Không hiện chỉ số kỹ thuật.
import { h } from '../lib/dom.js';
import * as data from '../lib/data.js';
import { aiMark, stateBox } from '../lib/ui.js';
import { openDesign } from '../lib/detail.js';

const latestOf = (d) => (d.latest_version_kind === 'system_repair' && d.repair_thumb ? d.repair_thumb : d.thumb);

export async function render() {
    const [{ items }, passports] = await Promise.all([data.heritage(), data.passports().catch(() => [])]);
    const shown = passports.filter((d) => d.thumb && d.approval.status !== 'qa_failed');
    if (!shown.length) {
        return stateBox('', 'Bộ sưu tập đang trống', 'Tạo thiết kế đầu tiên trong Studio.', h('a', { class: 'btn primary', href: '#/studio' }, 'Mở Studio'));
    }
    const groups = items.filter((it) => shown.some((d) => d.heritage_id === it.id));
    return h('div', { class: 'exhibit collection' },
        groups.map((it) => {
            const list = shown.filter((d) => d.heritage_id === it.id).sort((a, b) => a.passport_id.localeCompare(b.passport_id));
            return h('section', { class: 'section chapter coll-group' },
                h('div', { class: 'coll-head' },
                    h('div', { class: 'coll-artifact' }, h('img', { src: it.image, alt: '', loading: 'lazy' })),
                    h('div', {},
                        h('p', { class: 'kicker' }, it.dating || 'Gốm Bát Tràng'),
                        h('h2', { class: 'display coll-name' }, it.name),
                        it.status === 'active' ? h('a', { class: 'coll-try', href: `#/studio/${encodeURIComponent(it.id)}` }, 'Thử tạo trong Studio', h('i', { class: 'arr', 'aria-hidden': 'true' })) : null)),
                h('div', { class: 'coll-grid' }, list.map((d, k) => h('a', { class: 'gallery-item', href: '#/collection', onclick: (e) => { e.preventDefault(); openDesign(d.passport_id); } },
                    h('div', { class: 'gi-img' }, h('img', { src: `./${latestOf(d)}`, alt: `Áo dài hoa văn ${it.name}`, loading: 'lazy' }), aiMark()),
                    h('div', { class: 'gi-cap' },
                        h('span', { class: 'gi-from' }, `Thiết kế ${k + 1}`),
                        h('span', { class: 'gi-title' }, d.layout || 'Áo dài', h('i', { class: 'arr', 'aria-hidden': 'true' })))))));
        }));
}
