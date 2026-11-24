// components/run-card.js — THẺ MỘT BỘ THIẾT KẾ ĐÃ TẠO (trang #/mine): tên hiện vật, giờ tạo, bốn ảnh nhỏ có nhãn AI, nút Xem lại.
// Vào: { run: { heritageId, runId, createdAt }, item (hiện vật, có thể thiếu), designs (Passport của bộ này; rỗng nếu máy chủ không còn) }.
// Bộ không còn trên máy chủ thì hiện chữ báo và nút Xóa khỏi danh sách (chỉ xóa tên trong trình duyệt, không đụng dữ liệu máy chủ).
import { h } from '../core/dom.js';
import { icon } from '../core/icons.js';
import * as data from '../core/data.js';
import { latestOf, shownPath } from '../core/designs.js';
import { aiMark, editedMark } from './badges.js';

export function runCard({ run, item, designs }) {
    const when = new Date(run.createdAt);
    const time = Number.isNaN(when.getTime()) ? '' : when.toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' });
    const head = h('div', { class: 'rc-head' }, h('h3', { class: 'rc-name' }, item?.name || run.heritageId), time ? h('p', { class: 'rc-time' }, `Tạo lúc ${time}`) : null);
    const card = h('article', { class: 'run-card' }, head);
    if (!designs.length) {
        card.append(h('p', { class: 'rc-gone' }, 'Bộ thiết kế này không còn trên máy chủ.'),
            h('div', { class: 'rc-actions' }, h('button', { class: 'btn hero-btn ghost', type: 'button',
                // Dựng lại trang để danh sách, trạng thái "chưa tạo" và mục trên thanh trên cập nhật theo
                onclick: () => { data.forgetRun(run.runId); window.dispatchEvent(new HashChangeEvent('hashchange')); } }, 'Xóa khỏi danh sách')));
        return card;
    }
    const pics = designs.map((d, i) => h('div', { class: 'rc-pic' },
        h('img', { src: data.media(shownPath(d), latestOf(d)), alt: `Thiết kế ${i + 1}`, loading: 'lazy', decoding: 'async' }), aiMark(),
        d.edits > 0 ? editedMark() : null));
    card.append(h('div', { class: 'rc-grid' }, pics),
        h('div', { class: 'rc-actions' },
            h('a', { class: 'btn hero-btn primary', href: `#/result/${encodeURIComponent(run.heritageId)}/${encodeURIComponent(run.runId)}` }, 'Xem lại', icon('arrow'))));
    return card;
}
