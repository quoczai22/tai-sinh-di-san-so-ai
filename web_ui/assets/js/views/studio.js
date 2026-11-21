// views/studio.js — TRANG STUDIO (#/studio, #/studio/<mã hiện vật>): bước 1–2 của pipeline GUI.
//  · Chưa chọn hiện vật: lưới picker-card để chọn đầu vào.
//  · Đã chọn: khung 3D + thanh điều khiển, nút "Xem ý nghĩa hoa văn" (mở sổ hai trang, components/artifact-book.js), nút Tạo thiết kế.
//    Có máy chủ GPU (data.canGenerate): bấm Tạo là sinh thật (core/generation.js), có thanh tiến độ, xong sang #/result.
//    Không có GPU: không giả lập việc sinh — bấm Tạo mở trang Kết quả với bộ thiết kế đã tạo trước đó trên GPU.
// View chỉ lấy dữ liệu và ghép component; không tự định nghĩa component.
import { h } from '../core/dom.js';
import { icon } from '../core/icons.js';
import * as data from '../core/data.js';
import { pendingGeneration, runGeneration } from '../core/generation.js';
import { section, stateBox } from '../components/layout.js';
import { pickerCard } from '../components/picker-card.js';
import { mountViewer } from '../components/viewer3d.js';
import { bookButton } from '../components/artifact-book.js';
import { viewerControls } from '../components/viewer-controls.js';

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
    const recovering = pendingGeneration()?.heritageId === heritageId;
    const can = data.canGenerate() || recovering;
    const goToResult = () => { location.hash = `#/result/${encodeURIComponent(heritageId)}`; };

    const note = h('p', { class: 'out-note', role: 'status', 'aria-live': 'polite' });
    const progressBar = h('span');
    const progress = h('div', { class: 'out-progress', hidden: true }, h('div', { class: 'progress' }, progressBar));
    const start = async () => {
        if (genBtn.disabled) return;
        if (!can) {
            // Không có GPU: mở trang Kết quả với bộ đã tạo trước
            if (!hasDesigns) { note.textContent = 'Hiện vật này chưa có thiết kế.'; return; }
            goToResult();
            return;
        }
        genBtn.disabled = true;
        progress.hidden = false;
        note.textContent = recovering ? 'Đang khôi phục lượt tạo ảnh…' : 'Đang tạo ảnh';
        try {
            await runGeneration(heritageId, null, (pct, job) => {
                progressBar.style.width = `${pct}%`;
                note.textContent = job.status === 'queued' ? 'Đang chờ tạo ảnh' : 'Đang tạo ảnh';
            });
            goToResult();
        } catch (err) {
            progress.hidden = true;
            note.textContent = `Không tạo được thiết kế: ${err.message}`;
            genBtn.disabled = false;
        }
    };
    const genBtn = h('button', { class: 'btn hero-btn primary gen-btn', onclick: start }, 'Tạo thiết kế', icon('arrow'));
    if (recovering) setTimeout(start, 0);

    // Khung hiện vật: ảnh phẳng làm sẵn; nếu có mô hình 3D thì thay bằng khung xoay 360 độ bằng chuột
    const artifactImg = h('img', { src: item.image, alt: item.name });
    const artifactBox = h('div', { class: 'io-artifact' }, artifactImg);
    const viewerPromise = mountViewer(artifactBox, heritageId);

    return h('div', { class: 'studio-io' },
        h('div', { class: 'io-input' },
            artifactBox,
            viewerControls(artifactImg, viewerPromise, artifactBox),
            h('h2', { class: 'io-name' }, item.name),
            bookButton(item),
            h('a', { class: 'io-change', href: '#/studio' }, 'Đổi hiện vật')),
        h('div', { class: 'io-action' },
            genBtn,
            progress,
            note));
}
