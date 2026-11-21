// views/result.js — TRANG KẾT QUẢ (#/result/<mã hiện vật>): bước cuối của pipeline GUI — xem và tải đầu ra.
// Bốn tà áo của bộ thiết kế mới nhất của hiện vật (design-card). Chỉ có ảnh: không bảng chỉ số, không ghi chú.
// Bấm một ảnh → lightbox (tải xuống / quay lại). Chế độ trình diễn luôn hiện nhãn "Kết quả đã sinh sẵn".
// View chỉ lấy dữ liệu và ghép component; không tự định nghĩa component.
import { h } from '../core/dom.js';
import { icon } from '../core/icons.js';
import * as data from '../core/data.js';
import { fullImage, latestOf } from '../core/designs.js';
import { downloadImage } from '../core/download.js';
import { demoNotice } from '../components/badges.js';
import { designCard } from '../components/design-card.js';
import { stateBox } from '../components/layout.js';

export async function render([heritageId]) {
    const { items } = await data.heritage();
    const item = items.find((i) => i.id === heritageId);
    const all = data.liveDesignsFor(heritageId) ||
        (await data.passports()).filter((p) => p.heritage_id === heritageId && p.thumb);
    const savedRun = data.isLive() ? data.liveRunFor(heritageId) : null;
    const run = savedRun && all.some((p) => p.run_id === savedRun)
        ? savedRun : [...new Set(all.map((p) => p.run_id))].sort().reverse()[0];
    const designs = all.filter((p) => p.run_id === run).sort((a, b) => a.passport_id.localeCompare(b.passport_id));
    const studio = item ? `#/studio/${encodeURIComponent(item.id)}` : '#/studio';
    if (!item || !designs.length) {
        return stateBox('', 'Chưa có thiết kế', 'Hiện vật này chưa có bộ thiết kế nào.', h('a', { class: 'btn primary', href: '#/studio' }, 'Về Studio'));
    }
    const grid = h('div', { class: 'out-grid' }, designs.map((d, k) => designCard(d, k + 1, heritageId)));
    requestAnimationFrame(() => grid.classList.add('shown'));
    const downloadAllBtn = h('button', {
        class: 'btn hero-btn ghost',
        type: 'button',
        title: 'Tải 4 file ảnh PNG gốc chất lượng cao',
        onclick: async () => {
            downloadAllBtn.disabled = true;
            downloadAllBtn.textContent = 'Đang tải…';
            for (let i = 0; i < designs.length; i++) {
                const d = designs[i];
                const src = fullImage(d, heritageId, data.media(d.latest_path || d.final_path, latestOf(d)));
                await downloadImage(src, `thiet-ke-${heritageId}-V${i + 1}`);
                if (i < designs.length - 1) await new Promise((r) => setTimeout(r, 450));
            }
            downloadAllBtn.disabled = false;
            downloadAllBtn.replaceChildren(icon('download'), ' Tải toàn bộ 4 ảnh');
        }
    }, icon('download'), ' Tải toàn bộ 4 ảnh');

    return h('div', { class: 'result' },
        h('div', { class: 'result-head' },
            h('div', { class: 'result-artifact' }, h('img', { src: item.image, alt: '' })),
            h('h2', { class: 'io-name' }, item.name)),
        grid,
        h('div', { class: 'result-actions' },
            h('a', { class: 'btn hero-btn primary', href: studio }, 'Tạo lại'),
            downloadAllBtn,
            h('a', { class: 'btn hero-btn ghost', href: '#/studio' }, 'Chọn hiện vật khác')));
}
