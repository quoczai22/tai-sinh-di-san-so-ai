import { fmt, h } from '../lib/dom.js';
import * as data from '../lib/data.js';
import { decisionChip, section, stateBox } from '../lib/ui.js';

const STATUS = {
    planned: ['info', 'Đã lập kế hoạch, chờ chạy GPU'],
    awaiting_ratings: ['warn', 'Đã chạy, chờ phiếu chấm mù'],
    completed: ['pass', 'Hoàn tất'],
    draft: ['neutral', 'Bản nháp'],
};
const VAR_LABEL = {
    controlnet_weight: 'Trọng số ControlNet', seed: 'Seed', polish_seed: 'Seed img2img', stage2_finish: 'Bước hoàn thiện giai đoạn 2',
    composite_mode: 'Chế độ ghép', prompt_modifier: 'Cụm điều tiết prompt', palette_mode: 'Bảng màu', layout: 'Bố cục',
    polish_strength: 'img2img strength', steps: 'Số bước', guidance: 'Guidance', pattern_seed: 'Seed hoa văn',
    pattern_source: 'Nguồn hoa văn', prompt_terms_version: 'Phiên bản mô tả hoa văn',
};
const show = (v) => (v === '' ? '(rỗng)' : Array.isArray(v) ? v.join(', ') : String(v));

function experimentPanel(e) {
    const [cls, text] = STATUS[e.status] || STATUS.draft;
    const iv = e.independent_variable;
    return h('article', { class: 'panel stack' },
        h('div', { class: 'row spread' }, h('h3', { style: { margin: 0 } }, `${e.id}. ${e.title}`), h('span', { class: `chip ${cls}` }, text)),
        h('p', { style: { margin: 0 } }, e.question),
        e.why ? h('p', { class: 'muted small', style: { margin: 0 } }, e.why) : null,
        h('div', { class: 'grid cols-3' },
            h('div', {}, h('div', { class: 'muted small' }, 'Biến độc lập (duy nhất)'), h('b', {}, VAR_LABEL[iv.name] || iv.name), h('div', { class: 'small' }, iv.levels.map(show).join(' / '))),
            h('div', {}, h('div', { class: 'muted small' }, 'Lặp lại'), e.replicates ? [h('b', {}, VAR_LABEL[e.replicates.name] || e.replicates.name), h('div', { class: 'small' }, e.replicates.levels.join(', '))] : h('b', {}, 'Không cần (tất định)')),
            h('div', {}, h('div', { class: 'muted small' }, 'Quy mô'), h('b', {}, `${e.completed_runs}/${e.planned_runs} lượt`), h('div', { class: 'small' }, e.requires_gpu ? 'Cần GPU' : 'Chạy được trên CPU'))),
        h('details', {}, h('summary', {}, 'Biến giữ cố định'),
            h('div', { class: 'table-wrap' }, h('table', { class: 'data' }, h('tbody', {},
                Object.entries(e.fixed).map(([k, v]) => h('tr', {}, h('td', {}, VAR_LABEL[k] || k), h('td', {}, show(v)))))))),
        h('div', { class: 'row' },
            e.plan_csv ? h('a', { class: 'btn small', href: e.plan_csv, download: '' }, 'Tải CSV cấu hình') : null,
            h('span', { class: 'muted small' }, `Chỉ số: ${[...(e.metrics?.automatic || []), ...(e.metrics?.human || []).map((m) => `${m} (người chấm)`)].join(', ')}`)));
}

function expCResults(e) {
    if (!e?.results?.length) return null;
    const auto = e.summary?.automatic?.pattern_preservation_vs_full || {};
    const levels = e.independent_variable.levels;
    const label = { full: 'Đủ các bước', no_displacement: 'Bỏ displacement', no_shading: 'Bỏ shading', no_grade: 'Bỏ chỉnh màu' };
    const byItem = {};
    for (const r of e.results) (byItem[r.heritage_id] ||= {})[r.iv_level] = r;
    return section('EXP-C: kết quả đã chạy',
        'Bản ghép tất định chạy trên CPU với hoa văn V2 của lần chạy 06/09. Điểm dưới đây chỉ cho biết mỗi bước làm ảnh khác bản đầy đủ bao nhiêu; bước nào làm vải trông thật hơn phải do người chấm mù.',
        h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
            h('thead', {}, h('tr', {}, h('th', {}, 'Mức'), h('th', { class: 'num' }, 'n'), h('th', { class: 'num' }, 'Tương quan với bản đầy đủ'), h('th', { class: 'num' }, 'Độ lệch chuẩn'), h('th', {}, 'Khoảng tin cậy 95%'))),
            h('tbody', {}, levels.map((lv) => {
                const d = auto[lv] || {};
                return h('tr', {}, h('td', {}, label[lv] || lv), h('td', { class: 'num' }, d.n ?? '—'),
                    h('td', { class: 'num' }, fmt.num(d.mean, 3)), h('td', { class: 'num' }, fmt.num(d.sd, 3)),
                    h('td', {}, d.ci95 ? `${fmt.num(d.ci95[0], 3)} đến ${fmt.num(d.ci95[1], 3)}` : '—'));
            })))),
        h('p', { class: 'note warn' }, `Gói chấm mù đã tạo cho ${e.raters || 0} người chấm. Phiếu đã điền: ${e.filled_ratings || 0}. Chưa có kết luận về cảm nhận thị giác cho đến khi thu đủ phiếu.`),
        h('div', { class: 'stack', style: { marginTop: '12px' } }, Object.entries(byItem).map(([hid, lv]) => h('div', {},
            h('div', { class: 'muted small', style: { marginBottom: '6px' } }, hid),
            h('div', { class: 'grid cols-4' }, levels.map((l) => lv[l] ? h('figure', { style: { margin: 0 } },
                h('img', { src: `./${lv[l].display}`, alt: `${hid}, ${label[l]}`, loading: 'lazy', style: { borderRadius: '8px', border: '1px solid var(--line)' } }),
                h('figcaption', { class: 'small muted' }, label[l])) : null))))));
}

function flatten(obj, prefix = '') {
    const out = {};
    for (const [k, v] of Object.entries(obj || {})) {
        if (v && typeof v === 'object' && !Array.isArray(v)) Object.assign(out, flatten(v, `${prefix}${k}.`));
        else out[`${prefix}${k}`] = Array.isArray(v) ? v.join(', ') : v;
    }
    return out;
}

async function comparison(passports) {
    const options = passports.map((p) => h('option', { value: p.passport_id }, `${p.passport_id} (${p.heritage_name})`));
    const sameItem = passports.filter((p) => p.heritage_id === passports[0]?.heritage_id);
    const selA = h('select', {}, options.map((o) => o.cloneNode(true)));
    const selB = h('select', {}, options.map((o) => o.cloneNode(true)));
    selA.value = sameItem[0]?.passport_id;
    selB.value = sameItem[1]?.passport_id || passports[1]?.passport_id;
    const out = h('div', { class: 'stack' });
    const KEYS = ['controlnet.conditioning_scale', 'seed', 'prompt', 'palette.mode', 'layout.name', 'layout.selected_by',
        'polish_img2img.strength', 'polish_img2img.seed', 'steps', 'guidance', 'models.sd', 'models.controlnet', 'versions.torch', 'versions.diffusers'];
    const draw = async () => {
        out.replaceChildren(h('div', { class: 'skeleton' }));
        const [a, b] = await Promise.all([data.passport(selA.value), data.passport(selB.value)]);
        data.audit('comparison_viewed', { step: 4, passport_id: a.passport_id });
        const fa = flatten(a.generation);
        const fb = flatten(b.generation);
        const changed = KEYS.filter((k) => String(fa[k]) !== String(fb[k]));
        const side = (p) => {
            const fin = p.artifacts.find((x) => x.role === 'final_img2img');
            const ref = p.artifacts.find((x) => x.role === 'reference_512');
            const q = p.quality || {};
            return h('div', { class: 'side stack' },
                h('b', {}, p.passport_id),
                h('div', { class: 'grid cols-2' },
                    h('img', { src: data.media(ref, ref?.display), alt: 'Hiện vật', style: { borderRadius: '8px', background: '#fff' } }),
                    h('img', { src: data.media(fin, fin?.display), alt: 'Thiết kế cuối', style: { borderRadius: '8px' } })),
                h('div', { class: 'row' }, decisionChip(q.G2_pattern?.decision, 'G2: '), decisionChip(q.G3_final?.decision, 'G3: ')),
                h('div', { class: 'small' }, `Giữ họa tiết ${fmt.num(q.G3_final?.metrics?.pattern_preservation?.value, 2)}, dáng áo ${fmt.num(q.G3_final?.metrics?.garment_shape_iou?.value, 3)}`),
                h('div', { class: 'small muted' }, p.reviews.length ? p.reviews.map((r) => `${r.reviewer_id}: ${r.comment || r.decision}`).join(' | ') : 'Chưa có nhận xét chuyên gia'));
        };
        out.replaceChildren(
            changed.length > 1
                ? h('p', { class: 'note warn' }, `Hai thiết kế này khác nhau ở ${changed.length} tham số cùng lúc. Không thể quy kết khác biệt về chất lượng cho riêng tham số nào. Đây đúng là hạn chế của bộ 4 biến thể cũ; dùng EXP-A hoặc EXP-B để tách biến.`)
                : h('p', { class: 'note' }, changed.length === 1 ? 'Hai thiết kế chỉ khác một tham số: so sánh này quy kết được.' : 'Hai thiết kế có cùng cấu hình.'),
            h('div', { class: 'compare' }, side(a), side(b)),
            h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
                h('thead', {}, h('tr', {}, h('th', {}, 'Tham số'), h('th', {}, 'A'), h('th', {}, 'B'))),
                h('tbody', {}, KEYS.map((k) => h('tr', { class: 'diff-row' }, h('td', {}, k),
                    h('td', { class: changed.includes(k) ? 'changed' : '' }, show(fa[k] ?? '—')),
                    h('td', { class: changed.includes(k) ? 'changed' : '' }, show(fb[k] ?? '—'))))))));
    };
    selA.addEventListener('change', draw);
    selB.addEventListener('change', draw);
    draw();
    return section('So sánh A/B', 'Chọn hai thiết kế để xem ảnh đầu vào, kết quả, cấu hình và nhận xét cạnh nhau. Ô tô vàng là tham số khác nhau.',
        h('div', { class: 'row', style: { marginBottom: '12px' } }, h('label', { class: 'field' }, 'Phiên bản A', selA), h('label', { class: 'field' }, 'Phiên bản B', selB)),
        out);
}

export async function render() {
    const [exps, passports] = await Promise.all([data.experiments(), data.passports()]);
    if (!exps.length) return stateBox('', 'Chưa có thí nghiệm', 'Thêm đặc tả vào evaluation/experiments/.');
    const expC = exps.find((e) => e.id === 'EXP-C');
    return h('div', {},
        section('Thí nghiệm có đối chứng', 'Hệ thống từ chối kế hoạch nếu ngoài biến độc lập và seed còn tham số nào khác thay đổi.',
            h('div', { class: 'stack' }, exps.map(experimentPanel))),
        expCResults(expC),
        await comparison(passports));
}
