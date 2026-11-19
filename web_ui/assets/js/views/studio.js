import { h, icon, toast } from '../lib/dom.js';
import * as data from '../lib/data.js';
import { section, stateBox } from '../lib/ui.js';

// ---------------------------------------------------------------------------------------------
// Studio cho người xem: chọn hiện vật (đầu vào) → bấm Tạo thiết kế → chuyển sang trang Kết quả (#/result).
// · Có máy chủ GPU: bấm Tạo là sinh thật, có thanh tiến độ, xong chuyển sang trang Kết quả.
// · Không có GPU: không giả lập việc sinh. Bấm Tạo mở trang Kết quả với bộ thiết kế mô hình đã tạo trước
//   đó trên GPU (trang Kết quả ghi rõ ngày tạo).
// ---------------------------------------------------------------------------------------------
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

    const hasDesigns = (await data.passports()).some((p) => p.heritage_id === heritageId);
    const can = data.canGenerate();
    const goToResult = () => { location.hash = `#/result/${encodeURIComponent(heritageId)}`; };

    const note = h('p', { class: 'out-note', role: 'status', 'aria-live': 'polite' });
    const progressBar = h('span');
    const progress = h('div', { class: 'out-progress', hidden: true }, h('div', { class: 'progress' }, progressBar));
    const seedInput = h('input', { type: 'number', min: 0, max: 2147483647, value: 42, id: 'seed', inputmode: 'numeric' });
    const genBtn = h('button', { class: 'btn hero-btn primary gen-btn', onclick: async () => {
        if (!can) {
            // Không có GPU: mở trang Kết quả với bộ đã tạo trước
            if (!hasDesigns) { note.textContent = 'Hiện vật này chưa được chạy trên máy GPU nên chưa có thiết kế.'; return; }
            goToResult();
            return;
        }
        const seed = Number(seedInput.value);
        if (!Number.isInteger(seed) || seed < 0) { toast('Seed phải là số nguyên không âm.'); return; }
        genBtn.disabled = true;
        progress.hidden = false;
        note.textContent = 'Đang tạo thiết kế…';
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
            goToResult();
        } catch (err) {
            progress.hidden = true;
            note.textContent = `Không tạo được thiết kế: ${err.message}`;
            genBtn.disabled = false;
        }
    } }, 'Tạo thiết kế', icon('arrow'));

    return h('div', { class: 'studio-io' },
        h('div', { class: 'io-input' },
            h('div', { class: 'io-artifact' }, h('img', { src: item.image, alt: item.name })),
            h('h2', { class: 'io-name' }, item.name),
            h('a', { class: 'io-change', href: '#/studio' }, 'Đổi hiện vật')),
        h('div', { class: 'io-action' },
            genBtn,
            can ? h('details', { class: 'adv' }, h('summary', {}, 'Tuỳ chọn'), h('label', { class: 'field', for: 'seed' }, 'Seed', seedInput)) : null,
            progress,
            note));
}
