import { h, icon, toast } from '../lib/dom.js';
import * as data from '../lib/data.js';
import { section, stateBox } from '../lib/ui.js';
import { hoverSpin, mountViewer } from '../lib/viewer3d.js';

// ---------------------------------------------------------------------------------------------
// Studio cho người xem: chọn hiện vật (đầu vào) → bấm Tạo thiết kế → chuyển sang trang Kết quả (#/result).
// · Có máy chủ GPU: bấm Tạo là sinh thật, có thanh tiến độ, xong chuyển sang trang Kết quả.
// · Không có GPU: không giả lập việc sinh. Bấm Tạo mở trang Kết quả với bộ thiết kế mô hình đã tạo trước
//   đó trên GPU (trang Kết quả ghi rõ ngày tạo).
// ---------------------------------------------------------------------------------------------
// Thẻ hiện vật trong lưới chọn: rê chuột vào thì bình xoay 3D, rê ra thì đứng yên
function pickerCard(it) {
    const pic = h('div', { class: 'pic' }, h('img', { src: it.image, alt: '', loading: 'lazy' }));
    const card = h('a', { class: 'artifact', href: `#/studio/${encodeURIComponent(it.id)}`, style: { textDecoration: 'none' } },
        pic,
        h('div', { class: 'body' }, h('div', { class: 'code' }, it.dating || 'Gốm Bát Tràng'), h('div', { class: 'name' }, it.name)));
    hoverSpin(card, pic, it.id);
    return card;
}

function picker(items) {
    return section('Chọn một hiện vật', 'Hoa văn của hiện vật bạn chọn sẽ được dệt lên tà áo dài.',
        h('div', { class: 'artifact-grid' }, items.filter((i) => i.status === 'active').map((it) =>
            pickerCard(it))));
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
            if (!hasDesigns) { note.textContent = 'Hiện vật này chưa có thiết kế.'; return; }
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

    // Khung hiện vật: ảnh phẳng làm sẵn; nếu có mô hình 3D thì thay bằng khung xoay 360 độ bằng chuột
    const artifactImg = h('img', { src: item.image, alt: item.name });
    const artifactBox = h('div', { class: 'io-artifact' }, artifactImg);
    const viewerPromise = mountViewer(artifactBox, heritageId);

    // Thanh điều khiển thu phóng hiện vật + nút khoá đứng yên / chuyển động xoay
    let viewerInstance = null;
    Promise.resolve(viewerPromise).then((inst) => { viewerInstance = inst; });

    let isLocked = false;
    let zoomLevel = 1.0;

    const lockIcon = h('span', { class: 'ctrl-icon', 'aria-hidden': 'true' }, '🔄');
    const updateLockUi = (spinning) => {
        isLocked = !spinning;
        lockBtn.setAttribute('aria-pressed', String(isLocked));
        lockBtn.title = isLocked ? 'Đang đứng yên — Bấm để tiếp tục xoay 360°' : 'Đang tự xoay — Bấm để khoá đứng yên';
        lockIcon.textContent = isLocked ? '🔒' : '🔄';
    };

    const lockBtn = h('button', {
        type: 'button',
        class: 'lb-step lock-btn',
        title: 'Đang tự xoay — Bấm để khoá đứng yên',
        onclick: () => {
            if (viewerInstance?.toggleSpin) {
                const nowSpinning = viewerInstance.toggleSpin();
                updateLockUi(nowSpinning);
            } else {
                updateLockUi(isLocked);
            }
        }
    }, lockIcon);

    const zoomSlider = h('input', {
        type: 'range',
        class: 'lb-zoom',
        min: '70',
        max: '180',
        step: '2',
        value: '100',
        'aria-label': 'Thu phóng hiện vật'
    });

    const applyZoom = (val) => {
        zoomLevel = Math.max(0.7, Math.min(1.8, Math.round(val * 100) / 100));
        zoomSlider.value = String(Math.round(zoomLevel * 100));
        if (viewerInstance?.setZoom) {
            viewerInstance.setZoom(zoomLevel);
        } else {
            artifactImg.style.transform = `scale(${zoomLevel})`;
        }
    };

    zoomSlider.addEventListener('input', () => {
        applyZoom(Number(zoomSlider.value) / 100);
    });

    const stepOut = h('button', {
        type: 'button',
        class: 'lb-step',
        'aria-label': 'Thu nhỏ',
        title: 'Thu nhỏ',
        onclick: () => applyZoom(zoomLevel - 0.1)
    }, '−');

    const stepIn = h('button', {
        type: 'button',
        class: 'lb-step',
        'aria-label': 'Phóng to',
        title: 'Phóng to',
        onclick: () => applyZoom(zoomLevel + 0.1)
    }, '+');

    const viewerControls = h('div', { class: 'lb-zoomrow viewer-controls', role: 'toolbar', 'aria-label': 'Điều khiển xem hiện vật 3D' },
        lockBtn,
        stepOut,
        zoomSlider,
        stepIn
    );

    return h('div', { class: 'studio-io' },
        h('div', { class: 'io-input' },
            artifactBox,
            viewerControls,
            h('h2', { class: 'io-name' }, item.name),
            h('a', { class: 'io-change', href: '#/studio' }, 'Đổi hiện vật')),
        h('div', { class: 'io-action' },
            genBtn,
            can ? h('details', { class: 'adv' }, h('summary', {}, 'Tuỳ chọn'), h('label', { class: 'field', for: 'seed' }, 'Seed', seedInput)) : null,
            progress,
            note));
}
