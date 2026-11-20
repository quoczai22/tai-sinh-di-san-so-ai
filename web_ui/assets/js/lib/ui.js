import { clear, fmt, h, icon } from './dom.js';
import { media } from './data.js';
import { enhance, reduced } from './motion.js';

export const DECISION = {
    PASS: { cls: 'pass', icon: 'pass', text: 'Đạt' },
    WARN: { cls: 'warn', icon: 'warn', text: 'Cảnh báo' },
    FAIL: { cls: 'fail', icon: 'fail', text: 'Không đạt' },
    'N/A': { cls: 'neutral', icon: 'info', text: 'Chưa đo' },
};

export const APPROVAL = {
    draft: { cls: 'neutral', text: 'Đang tạo' },
    qa_failed: { cls: 'fail', text: 'Không đạt kiểm định' },
    qa_warning: { cls: 'warn', text: 'Chờ QC xem cảnh báo' },
    pending_expert_review: { cls: 'info', text: 'Chờ chuyên gia thẩm định' },
    revision_requested: { cls: 'warn', text: 'Chuyên gia yêu cầu sửa' },
    approved: { cls: 'pass', text: 'Đã phê duyệt' },
    rejected: { cls: 'fail', text: 'Bị loại' },
};

export const RIGHTS = {
    unverified: { cls: 'warn', text: 'Chưa xác minh quyền' },
    permission_requested: { cls: 'warn', text: 'Đang xin phép' },
    permission_granted: { cls: 'pass', text: 'Đã được cấp phép' },
    open_license: { cls: 'pass', text: 'Giấy phép mở' },
    public_domain: { cls: 'pass', text: 'Phạm vi công cộng' },
    own_work: { cls: 'pass', text: 'Ảnh của nhóm' },
    permission_denied: { cls: 'fail', text: 'Bị từ chối' },
};

export const ACTOR = { ai: 'AI hỗ trợ', system: 'Hệ thống tất định', human: 'Con người' };

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

/** Dòng chú thích quyền sử dụng dưới ảnh (chữ nghiêng, không dùng thẻ màu). */
export function rightsNote(status) {
    const r = RIGHTS[status] || RIGHTS.unverified;
    return h('span', { class: `rights-note ${r.cls}` }, r.text);
}

export function decisionChip(decision, prefix = '') {
    const d = DECISION[decision] || DECISION['N/A'];
    return h('span', { class: `chip ${d.cls}` }, icon(d.icon), `${prefix}${d.text}`);
}

export function approvalChip(status) {
    const a = APPROVAL[status] || { cls: 'neutral', text: status || 'Không rõ' };
    return h('span', { class: `chip ${a.cls}` }, a.text);
}

export function rightsChip(status) {
    const r = RIGHTS[status] || RIGHTS.unverified;
    return h('span', { class: `chip ${r.cls}` }, icon(r.cls === 'pass' ? 'pass' : r.cls === 'fail' ? 'fail' : 'warn'), r.text);
}

export function actorMark(type) {
    return h('span', { class: `actor ${type}`, title: ACTOR[type] || type, 'aria-label': ACTOR[type] || type });
}

export function stateBox(kind, title, text, action) {
    return h('div', { class: `state ${kind}`, role: kind === 'error' ? 'alert' : null },
        h('h3', {}, title), text ? h('p', {}, text) : null, action || null);
}

export function skeleton(n = 3, height = 160) {
    return h('div', { class: 'grid cols-3', 'aria-busy': 'true', 'aria-label': 'Đang tải dữ liệu' },
        Array.from({ length: n }, () => h('div', { class: 'skeleton', style: { minHeight: `${height}px` } })));
}

export function section(title, lede, ...body) {
    return h('section', { class: 'section' },
        h('div', { class: 'section-head' }, h('div', {}, h('h2', {}, title), lede ? h('p', {}, lede) : null)),
        ...body);
}

export function stat(value, label, foot, ratio) {
    return h('div', { class: 'stat' },
        h('div', { class: 'value' }, value),
        h('div', { class: 'label' }, label),
        ratio !== undefined && ratio !== null ? h('div', { class: 'meter', role: 'img', 'aria-label': `${Math.round(ratio * 100)}%` },
            h('span', { style: { width: `${Math.max(0, Math.min(1, ratio)) * 100}%` } })) : null,
        foot ? h('div', { class: 'foot' }, foot) : null);
}

/** Chuỗi truy vết: ảnh → ảnh, mỗi nút ghi ai làm (AI / hệ thống / người) và mã băm. */
export function chain(nodes) {
    return h('div', { class: 'chain', role: 'list', 'aria-label': 'Chuỗi truy vết từ hiện vật tới thiết kế' },
        nodes.map((n) => h('div', { class: 'chain-node', role: 'listitem' },
            h('div', { class: `frame ${n.contain ? 'contain' : ''}` },
                n.src ? h('img', { src: n.src, alt: n.title, loading: 'lazy' }) : null),
            h('div', { class: 'title' }, n.title),
            h('div', { class: 'who' }, actorMark(n.actor), ACTOR[n.actor]),
            n.sha ? h('div', { class: 'hash', title: `SHA-256 ${n.sha}` }, `SHA-256 ${fmt.hash(n.sha, 10)}`) : null,
            n.extra || null)));
}

export function artifactNodes(passport) {
    const pick = (role) => passport.artifacts.find((a) => a.role === role);
    const order = [
        ['reference_512', 'Hiện vật', 'human', true],
        ['control_canny', 'Bản đồ nét', 'system'],
        ['pattern', 'Hoa văn', 'ai'],
        ['composite_raw', 'Bản ghép', 'system'],
        ['final_img2img', 'Áo cuối (img2img)', 'ai'],
        ['repair_pattern_lock', 'Bản sửa: khoá họa tiết', 'system'],
        ['human_edit', 'Bản chỉnh sửa thủ công', 'human'],
    ];
    return order.filter(([role]) => pick(role)).map(([role, title, actor, contain]) => {
        const a = pick(role);
        return { title, actor, contain, src: media(a, a.display), sha: a.sha256 };
    });
}

export function metricLine(label, value, chip) {
    return h('div', { class: 'metric-line' }, h('span', {}, label), h('span', {}, h('b', {}, value), chip ? ' ' : null, chip || null));
}

export function kv(pairs) {
    return h('dl', { class: 'kv' }, pairs.flatMap(([k, v, missing]) => [
        h('dt', {}, k),
        h('dd', { class: missing ? 'missing' : '' }, v === null || v === undefined || v === '' ? 'Chưa có — cần bổ sung' : v),
    ]));
}

export function externalLink(url, text) {
    if (!url) return 'Chưa có';
    let safe = '';
    try { const u = new URL(url); if (['http:', 'https:'].includes(u.protocol)) safe = u.href; } catch { /* bỏ */ }
    if (!safe) return url;
    return h('a', { href: safe, target: '_blank', rel: 'noopener noreferrer' }, text || new URL(safe).hostname, ' ', icon('external'));
}
