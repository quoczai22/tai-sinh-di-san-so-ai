// components/dropzone.js — Ô TẢI TỆP của trang chỉnh sửa: bấm để chọn hoặc kéo thả một ảnh PNG; hiện ảnh xem trước, tên tệp, dung lượng, lỗi.
// Vào: { onChange(file | null) }. Ra: { el, getFile(), reset() }. Kiểm tra bằng core/edit-rules (PNG, tối đa 3 MB) và cạnh dài tối đa 4096 px.
// Dùng bàn phím được (Enter hoặc Space mở hộp chọn tệp). Mọi chữ đưa vào DOM bằng h(), không dùng innerHTML.
import { h } from '../core/dom.js';
import { icon } from '../core/icons.js';
import { EDIT_LIMITS, validateFile } from '../core/edit-rules.js';

export function dropzone({ onChange = () => {} } = {}) {
    let file = null;
    let url = null;
    const input = h('input', { class: 'dz-input', type: 'file', accept: 'image/png', tabindex: '-1', 'aria-hidden': 'true' });
    const preview = h('img', { class: 'dz-preview', alt: 'Ảnh bạn đã chọn', hidden: true });
    const name = h('p', { class: 'dz-name', hidden: true });
    const error = h('p', { class: 'dz-error', role: 'alert', hidden: true });
    const prompt = h('div', { class: 'dz-prompt' },
        icon('download', 'dz-ico'),
        h('p', { class: 'dz-title' }, 'Bấm để chọn ảnh hoặc kéo thả ảnh vào đây'),
        h('p', { class: 'dz-hint' }, `Chỉ ảnh PNG, tối đa ${EDIT_LIMITS.maxBytes / 1024 / 1024} MB, cạnh dài tối đa ${EDIT_LIMITS.maxSide} px.`));
    const el = h('div', { class: 'dropzone', role: 'button', tabindex: '0', 'aria-label': 'Tải ảnh đã chỉnh sửa lên. Bấm để chọn tệp hoặc kéo thả tệp vào đây' },
        input, prompt, preview, name, error);

    const reset = () => {
        if (url) URL.revokeObjectURL(url);
        url = null; file = null; input.value = '';
        preview.hidden = true; name.hidden = true; prompt.hidden = false;
        el.classList.remove('has-file');
    };
    const fail = (msg) => { reset(); error.textContent = msg; error.hidden = false; onChange(null); };
    let latest = 0;                                              // chọn hai ảnh liên tiếp: chỉ ảnh chọn sau cùng được nhận
    const accept = (f) => {
        const mine = ++latest;
        error.hidden = true;
        const problem = validateFile(f);
        if (problem) return fail(problem);
        const next = URL.createObjectURL(f);
        const probe = new Image();
        probe.onload = () => {
            if (mine !== latest) { URL.revokeObjectURL(next); return; }
            if (Math.max(probe.naturalWidth, probe.naturalHeight) > EDIT_LIMITS.maxSide) {
                URL.revokeObjectURL(next);
                return fail(`Ảnh quá lớn: cạnh dài tối đa ${EDIT_LIMITS.maxSide} px.`);
            }
            reset();
            file = f; url = next;
            preview.src = next; preview.hidden = false;
            name.textContent = `${f.name} (${(f.size / 1024).toFixed(0)} KB)`; name.hidden = false;
            prompt.hidden = true; el.classList.add('has-file');
            onChange(f);
        };
        probe.onerror = () => { URL.revokeObjectURL(next); fail('Không đọc được ảnh. Hãy chọn tệp PNG hợp lệ.'); };
        probe.src = next;
    };

    el.addEventListener('click', () => input.click());
    el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });
    input.addEventListener('click', (e) => e.stopPropagation());
    input.addEventListener('change', () => { if (input.files[0]) accept(input.files[0]); });
    el.addEventListener('dragover', (e) => { e.preventDefault(); el.classList.add('over'); });
    el.addEventListener('dragleave', () => el.classList.remove('over'));
    el.addEventListener('drop', (e) => {
        e.preventDefault();
        el.classList.remove('over');
        if (e.dataTransfer?.files?.[0]) accept(e.dataTransfer.files[0]);
    });
    return { el, getFile: () => file, reset };
}
