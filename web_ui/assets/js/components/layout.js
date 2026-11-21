// components/layout.js — KHỐI BỐ CỤC dùng chung: section (tiêu đề + mô tả + nội dung) và stateBox
// (hộp trạng thái: lỗi, trống, chưa có dữ liệu). Dùng ở: router (lỗi tải trang), Studio, trang Kết quả.
import { h } from '../core/dom.js';

export function stateBox(kind, title, text, action) {
    return h('div', { class: `state ${kind}`, role: kind === 'error' ? 'alert' : null },
        h('h3', {}, title), text ? h('p', {}, text) : null, action || null);
}

export function section(title, lede, ...body) {
    return h('section', { class: 'section' },
        h('div', { class: 'section-head' }, h('div', {}, h('h2', {}, title), lede ? h('p', {}, lede) : null)),
        ...body);
}
