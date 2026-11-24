// components/edit-panel.js — TRANG TẢI BẢN CHỈNH SỬA (#/edit/<mã Passport>): ô tải tệp bên trái, biểu mẫu thông tin Passport bên phải,
// hai nút Hủy và Lưu bản chỉnh sửa, cùng các hộp xác nhận theo luồng đã chốt:
//   Hủy → "Thiết kế của bạn sẽ không được lưu. Bạn có muốn hủy?"  [Quay lại | Đồng ý → về trang 4 thiết kế]
//   Lưu → "Xác nhận lưu bản chỉnh sửa"                            [Hủy | Xác nhận → gửi API → "✓ Đã cập nhật bản chỉnh sửa"]
// Vào: { design (Passport tóm tắt), n (số thứ tự thiết kế), heritageName, imageSrc (ảnh đang hiển thị), resultHref }.
// Không thu email hay họ tên: người dùng nhập ID tài khoản (bắt đầu bằng TSDS, xem core/edit-rules.js), dòng nhắc ngay trên biểu mẫu.
import { h } from '../core/dom.js';
import { icon } from '../core/icons.js';
import * as data from '../core/data.js';
import { EDIT_LIMITS, ROLES, validateAll, validateField } from '../core/edit-rules.js';
import { fileToBase64 } from '../core/upload.js';
import { aiMark } from './badges.js';
import { confirmDialog } from './confirm-dialog.js';
import { dropzone } from './dropzone.js';

const FIELDS = [
    { name: 'editor_id', label: 'ID tài khoản', tag: 'input',
      attrs: { maxlength: EDIT_LIMITS.idMax, autocomplete: 'off', spellcheck: 'false', placeholder: `${EDIT_LIMITS.idPrefix}01` },
      hint: `ID bắt đầu bằng ${EDIT_LIMITS.idPrefix}, ví dụ ${EDIT_LIMITS.idPrefix}01 (${EDIT_LIMITS.idMin} đến ${EDIT_LIMITS.idMax} ký tự, chỉ chữ không dấu, số, _ và -).` },
    { name: 'editor_role', label: 'Vai trò', tag: 'select', attrs: {}, hint: '' },
    { name: 'description', label: 'Đã sửa gì', tag: 'textarea', attrs: { maxlength: EDIT_LIMITS.descMax, rows: 4 },
      hint: `Mô tả ngắn các thay đổi (${EDIT_LIMITS.descMin} đến ${EDIT_LIMITS.descMax} ký tự).` },
    { name: 'tool', label: 'Công cụ đã dùng', tag: 'input', attrs: { maxlength: EDIT_LIMITS.toolMax, autocomplete: 'off' }, hint: 'Ví dụ GIMP, Photoshop, Canva.' },
];

// Câu báo lỗi dễ hiểu theo mã trạng thái máy chủ trả về
// Mã 502 có thể là máy chủ đã ghi xong nhưng trả lời chậm quá hạn: bản sửa ghi vào Passport không xóa được, nên nhắc kiểm tra trước khi gửi lại.
function explain(err) {
    const by = { 404: 'Không tìm thấy hồ sơ thiết kế này trên máy chủ. Có thể bộ thiết kế đã bị dọn.', 413: 'Ảnh quá lớn so với giới hạn của máy chủ.',
        429: 'Bạn gửi quá nhiều lần. Hãy thử lại sau.', 503: 'Máy chủ chưa sẵn sàng. Hãy thử lại sau ít phút.',
        502: 'Máy chủ chưa phản hồi. Bản chỉnh sửa có thể đã được lưu: hãy mở lại trang Kết quả, xem thiết kế đã có nhãn "Đã chỉnh sửa" chưa rồi hãy gửi lại.' };
    if (err instanceof TypeError) return 'Không kết nối được máy chủ. Hãy kiểm tra mạng rồi thử lại.';   // lỗi mạng của fetch
    return by[err?.status] || err?.message || 'Không lưu được bản chỉnh sửa.';
}

export function editPanel({ design, n, heritageName, imageSrc, resultHref }) {
    const controls = {};
    const touched = {};
    const errs = {};
    const dz = dropzone({ onChange: () => refresh() });

    const read = () => Object.fromEntries(FIELDS.map((f) => [f.name, controls[f.name].value]));
    const complete = () => Boolean(dz.getFile()) && Object.keys(validateAll(read())).length === 0;
    const showError = (name) => {
        const msg = touched[name] ? validateField(name, controls[name].value) : '';
        errs[name].textContent = msg; errs[name].hidden = !msg;
        controls[name].setAttribute('aria-invalid', msg ? 'true' : 'false');
    };
    function refresh() { saveBtn.disabled = !complete(); }

    const fieldEls = FIELDS.map((f) => {
        const id = `ep-${f.name}`;
        const control = f.tag === 'select'
            ? h('select', { id, name: f.name }, h('option', { value: '' }, 'Chọn vai trò…'), ROLES.map((r) => h('option', { value: r.value }, r.label)))
            : h(f.tag, { id, name: f.name, ...f.attrs });
        controls[f.name] = control;
        errs[f.name] = h('span', { class: 'ep-err', id: `${id}-err`, role: 'alert', hidden: true });
        control.setAttribute('aria-describedby', `${id}-err`);
        control.addEventListener('input', () => { showError(f.name); refresh(); });
        control.addEventListener('change', () => { touched[f.name] = true; showError(f.name); refresh(); });
        control.addEventListener('blur', () => { touched[f.name] = true; showError(f.name); });
        return h('label', { class: 'field ep-field', for: id }, h('span', {}, f.label), control,
            f.hint ? h('small', { class: 'ep-hint' }, f.hint) : null, errs[f.name]);
    });

    // Thông báo thành công chỉ có một dòng kèm dấu tích xanh, không hiện trạng thái hồ sơ hay quyết định cổng chất lượng.
    function done() {
        confirmDialog({
            title: [icon('pass', 'cd-tick'), 'Đã cập nhật bản chỉnh sửa'],
            buttons: [{ label: 'Quay lại', primary: true, onClick: (c) => { c.close(); location.hash = resultHref; } }],   // về trang 4 thiết kế
        });
    }
    async function submit(ctrl) {
        const v = read();
        if (!complete()) return ctrl.setError('Hãy chọn ảnh và điền đủ thông tin hợp lệ.');
        ctrl.setBusy(true, 'Đang lưu…');
        try {
            const image = await fileToBase64(dz.getFile());
            await data.submitEdit(design.passport_id, {
                editor_id: v.editor_id.trim(), editor_role: v.editor_role, description: v.description.trim(),
                tool: v.tool.trim(), image_png_base64: image,
            });
            ctrl.close();
            done();
        } catch (err) {
            ctrl.setBusy(false);
            ctrl.setError(explain(err));
        }
    }
    const askSave = () => confirmDialog({
        title: 'Xác nhận lưu bản chỉnh sửa',
        buttons: [{ label: 'Hủy', onClick: (c) => c.close() }, { label: 'Xác nhận', primary: true, onClick: submit }],
    });
    const askCancel = () => confirmDialog({
        title: 'Thiết kế của bạn sẽ không được lưu. Bạn có muốn hủy?',
        buttons: [{ label: 'Quay lại', onClick: (c) => c.close() },
            { label: 'Đồng ý', primary: true, onClick: (c) => { c.close(); location.hash = resultHref; } }],
    });

    const saveBtn = h('button', { class: 'btn hero-btn primary', type: 'button', disabled: true, onclick: askSave }, 'Lưu bản chỉnh sửa');
    const cancelBtn = h('button', { class: 'btn hero-btn ghost', type: 'button', onclick: askCancel }, 'Hủy');

    return h('div', { class: 'ep' },
        h('div', { class: 'ep-head' },
            h('div', { class: 'ep-thumb' }, h('img', { src: imageSrc, alt: `Thiết kế ${n}` }), aiMark()),
            h('div', {}, h('h2', { class: 'io-name' }, `Chỉnh sửa thiết kế ${n}`), h('p', { class: 'ep-sub' }, heritageName),
                h('p', { class: 'ep-sub' }, 'Chỉnh sửa ảnh thiết kế bằng công cụ của bạn, rồi tải ảnh PNG đã sửa lên.'))),
        h('div', { class: 'ep-body' },
            h('div', { class: 'ep-drop' }, dz.el),
            h('form', { class: 'ep-form', novalidate: true, onsubmit: (e) => e.preventDefault() },
                h('p', { class: 'ep-notice' }, 'Hãy nhập ID tài khoản của bạn, không nhập họ tên hay thông tin cá nhân khác.'),
                fieldEls,
                h('div', { class: 'ep-actions' }, cancelBtn, saveBtn))));
}
