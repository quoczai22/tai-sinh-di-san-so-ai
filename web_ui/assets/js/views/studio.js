import { clear, fmt, h, icon, toast } from '../lib/dom.js';
import * as data from '../lib/data.js';
import { aiMark, approvalChip, artifactNodes, chain, decisionChip, drawer, metricLine, section, stateBox } from '../lib/ui.js';

export function gateTable(gate, title) {
    if (!gate) return null;
    return h('div', {},
        h('div', { class: 'row spread' }, h('h3', {}, title), decisionChip(gate.decision)),
        h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
            h('thead', {}, h('tr', {}, h('th', {}, 'Chỉ số'), h('th', { class: 'num' }, 'Giá trị'),
                h('th', { class: 'num' }, 'Cảnh báo'), h('th', { class: 'num' }, 'Không đạt'), h('th', {}, 'Kết quả'))),
            h('tbody', {}, Object.entries(gate.metrics).map(([, m]) => h('tr', {},
                h('td', {}, m.label), h('td', { class: 'num' }, fmt.num(m.value, 3)),
                h('td', { class: 'num' }, fmt.num(m.warn, 2)), h('td', { class: 'num' }, fmt.num(m.fail, 2)),
                h('td', {}, decisionChip(m.status))))))));
}

export async function openDesign(pid) {
    data.audit('design_viewed', { step: 4, passport_id: pid });
    const p = await data.passport(pid);
    const q = p.quality || {};
    const g = p.generation || {};
    const body = h('div', { class: 'stack' },
        h('div', { class: 'row' }, approvalChip(p.approval.status), h('span', { class: 'muted small' }, p.approval.reason || '')),
        section('Chuỗi truy vết', 'Mỗi bước ghi rõ do AI, hệ thống tất định hay con người thực hiện, kèm mã băm tệp đầu ra.', chain(artifactNodes(p))),
        h('div', { class: 'grid cols-2' },
            h('div', { class: 'panel' }, h('h3', {}, 'Cấu hình sinh'),
                metricLine('Trọng số ControlNet', fmt.num(g.controlnet?.conditioning_scale, 2)),
                metricLine('Seed', g.seed),
                metricLine('Bảng màu', g.palette?.mode === 'original' ? 'Giữ màu hiện vật' : 'Tự do'),
                metricLine('Bố cục', g.layout?.label),
                metricLine('img2img strength', fmt.num(g.polish_img2img?.strength, 2)),
                metricLine('CLIP hoa văn so với hiện vật (tham khảo)', fmt.num(g.reference_metrics?.clip_similarity_pattern_vs_ceramic, 3))),
            h('div', { class: 'panel' }, h('h3', {}, 'Quyết định của cổng'),
                h('p', {}, decisionChip(q.overall?.decision)), h('p', { class: 'small' }, q.overall?.message || ''),
                q.repair ? h('p', { class: 'note' }, `Bản sửa khoá họa tiết: ${(({ PASS: 'Đạt', WARN: 'Cảnh báo', FAIL: 'Không đạt' })[q.repair.overall.decision])}. `,
                    'Điểm giữ họa tiết của bản sửa cao do cấu tạo (chép lại nét bản ghép), nên chuyên gia phải so mù hai bản trước khi chọn.') : null)),
        gateTable(q.G2_pattern, 'Cổng G2: hoa văn'),
        gateTable(q.G3_final, 'Cổng G3: thiết kế cuối (img2img)'),
        q.repair ? gateTable(q.repair.G3_final, 'Cổng G3 sau khi khoá họa tiết') : null,
        h('a', { class: 'btn primary', href: `#/passport/${p.passport_id}` }, icon('passport'), 'Mở Design Passport'));
    drawer(`${p.passport_id}`, body);
}

// Thẻ cho người xem: ảnh, tên, cách đặt hoa văn, tình trạng bằng lời. Chỉ số kỹ thuật nằm trong "Xem chi tiết".
const PLAIN = {
    pending_expert_review: ['Chờ chuyên gia', true], approved: ['Đã duyệt', true], qa_warning: ['Đang xem lại', false],
    revision_requested: ['Đang chỉnh sửa', false], qa_failed: ['Chưa đạt', false], rejected: ['Không dùng', false], draft: ['Đang tạo', false],
};
function designCard(d, n) {
    const thumb = data.media(d.final_path, d.thumb);
    const [status, ok] = PLAIN[d.approval.status] || [d.approval.label || '', false];
    const open = () => openDesign(d.passport_id);
    return h('article', { class: 'design', tabindex: '0', role: 'button', 'aria-label': `Thiết kế ${n}, ${d.layout || ''} — xem chi tiết`,
        onclick: open, onkeydown: (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } } },
        h('div', { class: 'pic' }, h('img', { src: thumb, alt: `Thiết kế ${n}`, loading: 'lazy' }), aiMark()),
        h('div', { class: 'body' },
            h('span', { class: `status ${ok ? 'ok' : ''}` }, status),
            h('span', { class: 'title' }, `Thiết kế ${n}`),
            d.layout ? h('span', { class: 'layout' }, d.layout) : null,
            h('span', { class: 'more' }, 'Xem chi tiết', h('i', { class: 'arr', 'aria-hidden': 'true' }))));
}

function picker(items) {
    return section('Chọn hiện vật', null,
        h('div', { class: 'artifact-grid' }, items.filter((i) => i.status === 'active').map((it) =>
            h('a', { class: 'artifact', href: `#/studio/${encodeURIComponent(it.id)}`, style: { textDecoration: 'none' } },
                h('div', { class: 'pic' }, h('img', { src: it.image, alt: '', loading: 'lazy' })),
                h('div', { class: 'body' }, h('div', { class: 'code' }, it.dating || 'Gốm Bát Tràng'), h('div', { class: 'name' }, it.name))))));
}

export async function render([heritageId]) {
    const { items } = await data.heritage();
    if (!heritageId) return picker(items);
    const item = items.find((i) => i.id === heritageId);
    if (!item) return stateBox('error', 'Không tìm thấy hiện vật', 'Mã hiện vật không có trong Thư viện.', h('a', { class: 'btn', href: '#/studio' }, 'Chọn hiện vật khác'));
    data.audit('heritage_selected', { step: 1, heritage_id: heritageId });
    const all = (await data.passports()).filter((p) => p.heritage_id === heritageId);
    const runs = [...new Set(all.map((p) => p.run_id))].sort().reverse();
    let currentRun = runs[0];
    const grid = h('div', { class: 'design-grid' });
    const drawRun = () => {
        const list = all.filter((p) => p.run_id === currentRun).sort((a, b) => a.passport_id.localeCompare(b.passport_id));
        grid.replaceChildren(...(list.length ? list.map((d, k) => designCard(d, k + 1))
            : [stateBox('', 'Chưa có thiết kế nào cho hiện vật này', data.canGenerate()
                ? 'Bấm "Sinh 4 thiết kế" để tạo bộ đầu tiên.'
                : 'Hiện vật mới đã đạt tiêu chí tuyển ảnh nhưng chưa được chạy trên GPU. Kết nối máy chủ GPU để sinh bộ đầu tiên.')]));
    };
    drawRun();

    const reviewedSteps = all.some((p) => p.reviews > 0);
    const steps = [['Hiện vật', true], ['Hoa văn', all.length > 0], ['Áo dài', all.length > 0], ['Kiểm định', all.length > 0],
        ['Thẩm định', reviewedSteps], ['Passport', all.length > 0]];
    const firstOpen = steps.findIndex(([, done]) => !done);
    const reached = firstOpen === -1 ? steps.length - 1 : firstOpen;
    const stepper = h('ol', { class: 'stepper timeline-steps', 'aria-label': 'Tiến trình thiết kế',
        style: { '--p': String(reached / (steps.length - 1)) } }, steps.map(([label, done], i) =>
        h('li', { class: done ? 'done' : i === firstOpen ? 'current' : '' }, label)));

    const seedInput = h('input', { type: 'number', min: 0, max: 2147483647, value: 42, id: 'seed', inputmode: 'numeric' });
    const progressBar = h('span');
    const progressText = h('div', { class: 'small muted', role: 'status', 'aria-live': 'polite' });
    const progress = h('div', { class: 'stack', hidden: true }, h('div', { class: 'progress' }, progressBar), progressText);
    const can = data.canGenerate();
    const genBtn = h('button', { class: 'btn primary', disabled: !can, onclick: async () => {
        const seed = Number(seedInput.value);
        if (!Number.isInteger(seed) || seed < 0) { toast('Seed phải là số nguyên không âm.'); return; }
        genBtn.disabled = true;
        progress.hidden = false;
        try {
            data.audit('generation_requested', { step: 3, heritage_id: heritageId });
            const { job_id: jobId } = await data.startGeneration(heritageId, seed);
            let job;
            do {
                await new Promise((r) => setTimeout(r, 1200));
                job = await data.jobStatus(jobId);
                progressBar.style.width = `${job.progress || 0}%`;
                progressText.textContent = job.label || 'Đang xử lý';
            } while (['queued', 'running'].includes(job.status));
            if (job.status !== 'completed') throw new Error(job.label);
            data.invalidate('live:passports');
            toast(job.label);
            location.hash = `#/studio/${encodeURIComponent(heritageId)}`;
            window.dispatchEvent(new HashChangeEvent('hashchange'));
        } catch (err) {
            progressText.textContent = `Không sinh được thiết kế: ${err.message}`;
            genBtn.disabled = false;
        }
    } }, 'Sinh 4 thiết kế');

    const runLabel = (r) => { const m = /^R(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/.exec(r || ''); return m ? `${m[3]}/${m[2]}/${m[1]}, ${m[4]}:${m[5]}` : r; };
    const runSelect = runs.length > 1 ? h('label', { class: 'field' }, 'Bộ thiết kế',
        h('select', { onchange: (e) => { currentRun = e.target.value; drawRun(); } }, runs.map((r) => h('option', { value: r }, runLabel(r))))) : null;

    return h('div', {},
        h('div', { class: 'studio-head v2' },
            h('div', { class: 'stack' },
                h('span', { class: 'kicker-sm' }, item.dating || 'Gốm Bát Tràng'),
                h('h2', { class: 'display studio-name' }, item.name),
                h('p', { class: 'studio-summary' }, item.visualSummary || ''),
                stepper),
            h('div', { class: 'stack' },
                h('div', { class: 'panel stack gen-panel' },
                    h('h3', {}, 'Sinh bộ thiết kế mới'),
                    h('div', { class: 'row' }, genBtn, runSelect),
                    h('details', { class: 'adv' }, h('summary', {}, 'Tuỳ chọn nâng cao'),
                        h('label', { class: 'field', for: 'seed' }, 'Seed (cùng seed cho cùng kết quả)', seedInput)),
                    can ? null : h('p', { class: 'gen-off' }, 'Cần máy chủ có GPU để tạo bộ mới. Bên dưới là bộ thiết kế gần nhất.'),
                    progress))),
        section('Bộ thiết kế', currentRun ? `Tạo ngày ${runLabel(currentRun)}` : null, grid));
}
