// components/confirm-dialog.js — HỘP XÁC NHẬN nổi trên trang: tiêu đề, nội dung, tối đa hai nút. Dùng ở trang chỉnh sửa (hủy, lưu, đã lưu).
// Vào: { title, text, note, buttons: [{ label, primary, onClick(ctrl) }], onDismiss }. Esc hoặc bấm ra ngoài gọi onDismiss
// (mặc định là nút đầu tiên). Nút không tự đóng hộp: onClick gọi ctrl.close(). Giữ tiêu điểm bàn phím trong hộp.
// Ra: ctrl = { close(), setBusy(bool, nhãn), setError(chữ) } để báo đang lưu hoặc lỗi ngay trong hộp. Gắn vào #overlay-root.
import { h } from '../core/dom.js';

export function confirmDialog({ title, text, note, buttons, onDismiss }) {
    const opener = document.activeElement;
    const error = h('p', { class: 'cd-error', role: 'alert', hidden: true });
    const status = h('p', { class: 'cd-status', role: 'status', 'aria-live': 'polite', hidden: true });
    const nodes = buttons.map((b) => h('button', {
        class: `btn hero-btn ${b.primary ? 'primary' : 'ghost'}`, type: 'button', onclick: () => b.onClick(ctrl),
    }, b.label));
    const labels = buttons.map((b) => b.label);

    const close = () => {
        document.removeEventListener('keydown', onKey);
        window.removeEventListener('hashchange', close);
        box.remove();
        if (!document.querySelector('.cd, .lightbox')) document.body.classList.remove('lb-open');
        opener?.focus?.();
    };
    let busy = false;                                          // đang lưu thì Esc và bấm ra ngoài không đóng hộp
    const dismiss = () => { if (!busy) (onDismiss ? onDismiss(ctrl) : buttons[0].onClick(ctrl)); };
    const onKey = (e) => {
        if (e.key === 'Escape') { e.preventDefault(); dismiss(); return; }
        if (e.key !== 'Tab') return;
        const active = nodes.filter((n) => !n.disabled);
        if (!active.length) { e.preventDefault(); return; }       // đang lưu: các nút bị khóa, không cho Tab thoát ra trang nền
        const i = active.indexOf(document.activeElement);
        const next = e.shiftKey ? (i <= 0 ? active.length - 1 : i - 1) : (i + 1) % active.length;
        e.preventDefault();
        active[next].focus();
    };
    const ctrl = {
        close,
        setBusy(on, label = '') {
            busy = on;
            nodes.forEach((n, i) => { n.disabled = on; n.textContent = on && i === nodes.length - 1 && label ? label : labels[i]; });
            status.hidden = !on; status.textContent = on ? label : '';
            if (on) error.hidden = true;
        },
        setError(msg) { error.hidden = !msg; error.textContent = msg || ''; nodes.at(-1)?.focus(); },
    };
    const box = h('div', { class: 'cd', role: 'alertdialog', 'aria-modal': 'true', 'aria-labelledby': 'cd-title',
        onclick: (e) => { if (e.target === box) dismiss(); } },
    h('div', { class: 'cd-panel' },
        h('h2', { id: 'cd-title', class: 'cd-title' }, title),
        text ? h('p', { class: 'cd-text' }, text) : null,
        note ? h('p', { class: 'cd-note' }, note) : null,
        status, error,
        h('div', { class: 'cd-actions' }, nodes)));
    document.body.classList.add('lb-open');
    document.getElementById('overlay-root').append(box);
    document.addEventListener('keydown', onKey);
    window.addEventListener('hashchange', close);              // bấm Back hay đổi trang thì đóng hộp, không để hộp mồ côi trên trang khác
    nodes[0]?.focus();                                         // tiêu điểm đầu tiên ở nút an toàn bên trái, tránh bấm Enter nhầm vào nút hủy bỏ hay lưu
    return ctrl;
}
