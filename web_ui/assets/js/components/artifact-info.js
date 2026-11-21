// components/artifact-info.js — Ô "VỀ HIỆN VẬT" bên phải bình ở Studio (bước 1 của pipeline: hiểu đầu vào trước khi tạo).
// Cho người xem biết: dáng, kỹ thuật, phong cách, xuất xứ; hoa văn nằm ở đâu và có ý nghĩa gì (chỉ ghi ý nghĩa khi có
// nguồn bảo tàng); hiện vật bảo tàng tương đồng; ảnh lấy từ đâu và được dùng tới mức nào.
// Dữ liệu: khối artifact_info trong data/heritage/metadata.json → trường `info` của API /heritage và web_ui/data/heritage.json.
import { h } from '../core/dom.js';
import { icon } from '../core/icons.js';

// Chỉ mở liên kết http(s); địa chỉ khác hiện thành chữ thường
function outLink(url, text, cls) {
    let safe = '';
    try { const u = new URL(url); if (['http:', 'https:'].includes(u.protocol)) safe = u.href; } catch { /* bỏ qua */ }
    if (!safe) return h('span', { class: cls }, text);
    return h('a', { class: cls, href: safe, target: '_blank', rel: 'noopener noreferrer' }, text, icon('external'));
}

const RIGHTS_TEXT = {
    unverified: 'Bộ dữ liệu công bố theo CC BY 4.0, nhưng quyền dùng riêng vật này chưa được xác minh: chỉ dùng phi thương mại, thử nghiệm.',
};

export function artifactInfo(item) {
    const info = item.info;
    const p = item.provenance || {};
    const refNo = new Map((info?.sources || []).map((s, k) => [s.key, k + 1]));
    const ref = (key) => (refNo.has(key) ? h('sup', { class: 'ai-ref', title: 'Xem mục Nguồn tham khảo' }, String(refNo.get(key))) : null);
    const block = (title, ...body) => h('section', { class: 'ai-block' }, h('h3', { class: 'ai-h' }, title), ...body);
    const fact = (k, v) => (v ? [h('dt', {}, k), h('dd', {}, v)] : []);
    const cmp = info?.comparison;
    return h('aside', { class: 'ai-panel', 'aria-label': `Thông tin hiện vật ${item.name}` },
        h('p', { class: 'ai-kicker' }, 'Về hiện vật'),
        info?.summary ? h('p', { class: 'ai-lead' }, info.summary) : null,
        info ? h('dl', { class: 'ai-facts' },
            ...fact('Dáng', info.form),
            ...fact('Kỹ thuật', info.technique),
            ...fact('Phong cách', info.style),
            ...fact('Xuất xứ', info.origin)) : null,
        info?.motifs?.length ? block('Hoa văn',
            h('ul', { class: 'ai-motifs' }, info.motifs.map((m) => h('li', {},
                h('p', { class: 'ai-motif' }, h('strong', {}, m.name), m.where ? h('span', {}, ` · ${m.where}`) : null),
                m.meaning ? h('p', { class: 'ai-meaning' }, m.meaning, ref(m.source)) : null)))) : null,
        info ? block('Hiện vật bảo tàng tương đồng', cmp
            ? h('a', { class: 'ai-compare', href: cmp.url, target: '_blank', rel: 'noopener noreferrer' },
                h('span', { class: 'ai-compare-holder' }, cmp.holder),
                h('span', { class: 'ai-compare-title' }, cmp.title, icon('external')),
                h('span', { class: 'ai-compare-meta' }, [cmp.dating, cmp.place].filter(Boolean).join(' · ')),
                cmp.note ? h('span', { class: 'ai-compare-note' }, cmp.note) : null)
            : h('p', { class: 'ai-muted' }, 'Chưa tìm được hiện vật bảo tàng đủ gần để đối chiếu.')) : null,
        block('Nguồn ảnh',
            h('p', {}, p.sourceTitle || p.holder || 'Chưa rõ nguồn'),
            p.sourceUrl ? h('p', {}, outLink(p.sourceUrl, 'Xem trang bộ dữ liệu', 'ai-link')) : null,
            h('p', { class: 'ai-muted' }, RIGHTS_TEXT[p.rightsStatus] || item.licenseNote || '')),
        info?.sources?.length ? h('details', { class: 'ai-sources' },
            h('summary', {}, `Nguồn tham khảo (${info.sources.length})`),
            h('ol', {}, info.sources.map((s) => h('li', {},
                h('span', { class: 'ai-src-holder' }, s.holder), ' — ', outLink(s.url, s.title, 'ai-link'))))) : null,
        info?.note ? h('p', { class: 'ai-note' }, info.note) : null);
}
