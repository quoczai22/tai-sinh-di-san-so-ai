// components/badges.js — NHÃN BẮT BUỘC trên ảnh: nhãn "AI" cho mọi ảnh có AI hỗ trợ tạo (YC3 — minh bạch AI)
// và dòng "Kết quả đã sinh sẵn" khi chạy chế độ trình diễn (không có GPU trực tuyến).
// Dùng ở: ảnh bìa (hero/fan), trang chủ (journey-card, gallery-item), design-card, lightbox, trang Kết quả.
import { h } from '../core/dom.js';
import { AI_LABEL } from '../core/download.js';

/** Nhãn bắt buộc trên mọi ảnh có AI hỗ trợ tạo: chữ "Hỗ trợ bởi AI" (cùng chữ được in lên file tải về). */
export function aiMark() {
    return h('span', { class: 'ai-tag', title: 'Thiết kế có AI hỗ trợ tạo' }, AI_LABEL);
}

/** Nhãn bắt buộc khi chạy chế độ trình diễn (không có GPU trực tuyến): ảnh là kết quả thật đã sinh sẵn. */
