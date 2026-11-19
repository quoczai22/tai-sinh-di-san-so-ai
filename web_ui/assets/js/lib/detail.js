// Khung chi tiết cho người xem — chỉ những gì nhìn thấy được: ảnh, tên, mô tả, nguồn ảnh (ghi công)
// và một nút đi tiếp. Không có bảng tiêu chí, chỉ số kỹ thuật hay mã băm; các thông tin đó nằm trong
// dữ liệu (outputs/passports, data/heritage) và hồ sơ docs/finals cho Ban giám khảo.
import { h, icon } from './dom.js';
import * as data from './data.js';
import { RIGHTS, aiMark, drawer, externalLink } from './ui.js';

const latestOf = (d) => (d.latest_version_kind === 'system_repair' && d.repair_thumb ? d.repair_thumb : d.thumb);
const dateOf = (iso) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || ''); return m ? `${m[3]}/${m[2]}/${m[1]}` : ''; };

function sourceBlock(item) {
    const p = item.provenance || {};
    const rights = (RIGHTS[p.rightsStatus] || RIGHTS.unverified).text;
    return h('div', { class: 'dt-source' },
        h('p', { class: 'dt-label' }, 'Nguồn ảnh hiện vật'),
        p.attribution ? h('p', {}, p.attribution) : (p.holder ? h('p', {}, p.holder) : null),
        p.sourceUrl ? h('p', {}, externalLink(p.sourceUrl, 'Xem trang nguồn')) : null,
        h('p', { class: 'dt-muted' }, rights));
}

/** Chi tiết một tà áo. */
export async function openDesign(pid) {
    const [{ items }, list] = await Promise.all([data.heritage(), data.passports()]);
    const d = list.find((x) => x.passport_id === pid);
    if (!d) return;
    const item = items.find((i) => i.id === d.heritage_id) || { name: d.heritage_name };
    data.audit('design_viewed', { step: 4, passport_id: pid });
    const body = h('div', { class: 'dt' },
        h('div', { class: 'dt-hero' }, h('img', { src: data.media(d.final_path, latestOf(d)), alt: `Áo dài hoa văn ${item.name}` }), aiMark()),
        h('p', { class: 'dt-label' }, 'Dệt từ hoa văn'),
        h('p', { class: 'dt-title' }, item.name),
        d.layout ? h('p', { class: 'dt-muted' }, `Cách đặt hoa văn: ${d.layout}`) : null,
        dateOf(d.created_at) ? h('p', { class: 'dt-muted' }, `Tạo ngày ${dateOf(d.created_at)}`) : null,
        h('p', { class: 'dt-note' }, 'Thiết kế có AI hỗ trợ tạo, từ hoa văn trên hiện vật gốm.'),
        item.provenance ? sourceBlock(item) : null,
        item.id ? h('a', { class: 'btn hero-btn primary dt-cta', href: `#/studio/${encodeURIComponent(item.id)}` }, 'Thử với hiện vật này', icon('arrow')) : null);
    drawer(`Thiết kế áo dài`, body);
}

/** Chi tiết một hiện vật. */
export async function openArtifact(item) {
    data.audit('provenance_viewed', { step: 2, heritage_id: item.id });
    const designs = (await data.passports().catch(() => [])).filter((d) => d.heritage_id === item.id && d.thumb && d.approval.status !== 'qa_failed');
    const body = h('div', { class: 'dt' },
        h('div', { class: 'dt-hero vitrine' }, h('img', { src: item.image, alt: item.name })),
        h('p', { class: 'dt-label' }, item.dating || 'Gốm Bát Tràng'),
        h('p', { class: 'dt-title' }, item.name),
        item.visualSummary ? h('p', { class: 'dt-text' }, item.visualSummary) : null,
        sourceBlock(item),
        designs.length ? h('div', {},
            h('p', { class: 'dt-label' }, 'Áo dài từ hiện vật này'),
            h('div', { class: 'dt-thumbs' }, designs.map((d) => h('button', { type: 'button', class: 'dt-thumb', 'aria-label': `Xem thiết kế ${d.layout || ''}`, onclick: () => openDesign(d.passport_id) },
                h('img', { src: `./${latestOf(d)}`, alt: '' }))))) : null,
        item.status === 'active' ? h('a', { class: 'btn hero-btn primary dt-cta', href: `#/studio/${encodeURIComponent(item.id)}` }, 'Tạo thiết kế từ hiện vật này', icon('arrow')) : null);
    drawer(item.name, body);
}
