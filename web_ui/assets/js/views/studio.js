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

// ---------------------------------------------------------------------------------------------
// Studio cho người xem: ĐẦU VÀO (hiện vật) → nút Tạo thiết kế → ĐẦU RA (4 tà áo).
// Không hiện các bước trung gian (hoa văn, cổng kiểm định, Passport) — xem trong "Xem chi tiết".
// · Có máy chủ GPU: bấm Tạo là sinh thật, có thanh tiến độ, xong hiện bộ mới.
// · Không có GPU: không giả lập việc sinh. Bấm Tạo sẽ mở bộ thiết kế mô hình đã tạo trước đó trên GPU,
//   ghi rõ ngày tạo. Trước khi bấm, khung đầu ra để trống.
// ---------------------------------------------------------------------------------------------
const latestOf = (d) => (d.latest_version_kind === 'system_repair' && d.repair_thumb ? d.repair_thumb : d.thumb);
const runDate = (r) => { const m = /^R(\d{4})(\d{2})(\d{2})/.exec(r || ''); return m ? `${m[3]}/${m[2]}/${m[1]}` : ''; };

function designCard(d, n) {
    const open = () => openDesign(d.passport_id);
    return h('article', { class: 'design out-card', tabindex: '0', role: 'button', 'aria-label': `Thiết kế ${n}, ${d.layout || ''} — xem chi tiết`,
        style: { '--k': String(n - 1) },
        onclick: open, onkeydown: (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } } },
    h('div', { class: 'pic' }, h('img', { src: data.media(d.final_path, latestOf(d)), alt: `Thiết kế ${n}`, loading: 'lazy' }), aiMark()),
    h('div', { class: 'body' },
        h('span', { class: 'title' }, `Thiết kế ${n}`),
        d.layout ? h('span', { class: 'layout' }, d.layout) : null,
        h('span', { class: 'more' }, 'Xem chi tiết', h('i', { class: 'arr', 'aria-hidden': 'true' }))));
}

function picker(items) {
    return section('Chọn một hiện vật', 'Hoa văn của hiện vật bạn chọn sẽ được dệt lên tà áo dài.',
        h('div', { class: 'artifact-grid' }, items.filter((i) => i.status === 'active').map((it) =>
            h('a', { class: 'artifact', href: `#/studio/${encodeURIComponent(it.id)}`, style: { textDecoration: 'none' } },
                h('div', { class: 'pic' }, h('img', { src: it.image, alt: '', loading: 'lazy' })),
                h('div', { class: 'body' }, h('div', { class: 'code' }, it.dating || 'Gốm Bát Tràng'), h('div', { class: 'name' }, it.name))))));
}

export async function render([heritageId]) {
    const { items } = await data.heritage();
    if (!heritageId) return picker(items);
    const item = items.find((i) => i.id === heritageId);
    if (!item) return stateBox('error', 'Không tìm thấy hiện vật', 'Hiện vật này không có trong Thư viện.', h('a', { class: 'btn', href: '#/studio' }, 'Chọn hiện vật khác'));
    data.audit('heritage_selected', { step: 1, heritage_id: heritageId });

    const all = (await data.passports()).filter((p) => p.heritage_id === heritageId);
    const latestRun = [...new Set(all.map((p) => p.run_id))].sort().reverse()[0];
    const latest = all.filter((p) => p.run_id === latestRun).sort((a, b) => a.passport_id.localeCompare(b.passport_id));
    const can = data.canGenerate();

    const outGrid = h('div', { class: 'out-grid' });
    const outNote = h('p', { class: 'out-note', role: 'status', 'aria-live': 'polite' });
    const progressBar = h('span');
    const progress = h('div', { class: 'out-progress', hidden: true }, h('div', { class: 'progress' }, progressBar));
    const empty = h('div', { class: 'out-empty' }, h('p', {}, 'Bốn thiết kế áo dài sẽ hiện ở đây.'));
    outGrid.append(empty);

    const show = (list, note) => {
        outGrid.replaceChildren(...list.map((d, k) => designCard(d, k + 1)));
        outNote.textContent = note;
        requestAnimationFrame(() => outGrid.classList.add('shown'));
        // Màn hình hẹp: phần Đầu ra nằm dưới, tự cuộn tới để người xem thấy kết quả
        const r = outGrid.getBoundingClientRect();
        if (r.top > window.innerHeight * 0.6) outGrid.scrollIntoView({ behavior: 'smooth', block: 'center' });
    };

    const seedInput = h('input', { type: 'number', min: 0, max: 2147483647, value: 42, id: 'seed', inputmode: 'numeric' });
    const genBtn = h('button', { class: 'btn hero-btn primary gen-btn', onclick: async () => {
        if (!can) {
            // Không có GPU: mở bộ đã tạo trước, nói rõ là kết quả có sẵn
            if (!latest.length) { outNote.textContent = 'Hiện vật này chưa được chạy trên máy GPU nên chưa có thiết kế.'; return; }
            genBtn.disabled = true;
            show(latest, `Chưa kết nối máy GPU nên chưa tạo mới được. Đây là bộ thiết kế mô hình đã tạo từ hiện vật này ngày ${runDate(latestRun)}.`);
            return;
        }
        const seed = Number(seedInput.value);
        if (!Number.isInteger(seed) || seed < 0) { toast('Seed phải là số nguyên không âm.'); return; }
        genBtn.disabled = true;
        progress.hidden = false;
        outNote.textContent = 'Đang tạo thiết kế…';
        try {
            data.audit('generation_requested', { step: 3, heritage_id: heritageId });
            const { job_id: jobId } = await data.startGeneration(heritageId, seed);
            let job;
            do {
                await new Promise((r) => setTimeout(r, 1200));
                job = await data.jobStatus(jobId);
                progressBar.style.width = `${job.progress || 0}%`;
            } while (['queued', 'running'].includes(job.status));
            if (job.status !== 'completed') throw new Error(job.label);
            data.invalidate('live:passports');
            const fresh = (await data.passports()).filter((p) => p.heritage_id === heritageId);
            const run = [...new Set(fresh.map((p) => p.run_id))].sort().reverse()[0];
            progress.hidden = true;
            show(fresh.filter((p) => p.run_id === run).sort((a, b) => a.passport_id.localeCompare(b.passport_id)), 'Đã tạo xong bộ thiết kế mới.');
        } catch (err) {
            progress.hidden = true;
            outNote.textContent = `Không tạo được thiết kế: ${err.message}`;
            genBtn.disabled = false;
        }
    } }, 'Tạo thiết kế', icon('arrow'));

    return h('div', { class: 'studio-io' },
        h('div', { class: 'io-input' },
            h('p', { class: 'kicker' }, 'Đầu vào'),
            h('div', { class: 'io-artifact' }, h('img', { src: item.image, alt: item.name })),
            h('h2', { class: 'io-name' }, item.name),
            item.visualSummary ? h('p', { class: 'io-summary' }, item.visualSummary) : null,
            h('a', { class: 'io-change', href: '#/studio' }, 'Đổi hiện vật')),
        h('div', { class: 'io-action' },
            genBtn,
            can ? h('details', { class: 'adv' }, h('summary', {}, 'Tuỳ chọn'), h('label', { class: 'field', for: 'seed' }, 'Seed', seedInput)) : null,
            progress),
        h('div', { class: 'io-output' },
            h('p', { class: 'kicker' }, 'Đầu ra'),
            outGrid,
            outNote));
}
