// components/badges.js — NHÃN BẮT BUỘC trên ảnh: nhãn "AI" cho mọi ảnh có AI hỗ trợ tạo (YC3 — minh bạch AI)
// và dòng "Kết quả đã sinh sẵn" khi chạy chế độ trình diễn (không có GPU trực tuyến).
// Dùng ở: ảnh bìa (hero/fan), trang chủ (journey-card, gallery-item), design-card, lightbox, trang Kết quả.
import { h } from '../core/dom.js';

/** Nhãn bắt buộc trên mọi ảnh có AI hỗ trợ tạo — gọn, nhưng trình đọc màn hình vẫn đọc đủ câu. */
export function aiMark() {
    return h('span', { class: 'ai-tag', title: 'Thiết kế có AI hỗ trợ tạo', 'aria-label': 'Thiết kế có AI hỗ trợ tạo' }, 'AI');
}

/** Nhãn bắt buộc khi chạy chế độ trình diễn (không có GPU trực tuyến): ảnh là kết quả thật đã sinh sẵn. */
export const DEMO_LABEL = 'Kết quả đã sinh sẵn — không phải sinh trực tiếp';
export function demoNotice() {
    return h('p', { class: 'demo-notice', role: 'note' },
        h('strong', {}, DEMO_LABEL));
}
