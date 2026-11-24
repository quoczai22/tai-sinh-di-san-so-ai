// core/edit-rules.js — QUY TẮC KIỂM TRA biểu mẫu tải bản chỉnh sửa. Khớp EditRequest của API (tsds/api/main.py) và hàm gateway api/edit.js.
// Hàm thuần, không đụng DOM nên kiểm thử được bằng Node (tests/test_web_edit.py).
// Ra: EDIT_LIMITS, ROLES, validateField(tên, giá trị), validateFile({ type, size }), validateAll(giá trị).

export const EDIT_LIMITS = Object.freeze({
    idPrefix: 'TSDS', idMin: 5, idMax: 24,      // ID tài khoản: bắt đầu bằng TSDS và có thêm ít nhất 1 ký tự (API cho phép 2 đến 24, gateway siết hơn)
    descMin: 5, descMax: 500, toolMin: 2, toolMax: 80,
    maxBytes: 3 * 1024 * 1024,   // 3 MB: ảnh gửi dạng base64 lớn thêm khoảng 33%, hàm Vercel nhận thân yêu cầu tối đa 4,5 MB
    maxSide: 4096,               // cạnh dài tối đa (px), chặn ảnh khổ cực lớn làm cạn bộ nhớ máy chủ
});

export const ROLES = Object.freeze([
    { value: 'designer', label: 'Nhà thiết kế' },
    { value: 'qc_officer', label: 'Người kiểm soát chất lượng (QC)' },
]);

const ID = /^[A-Za-z0-9_-]+$/;
// Đếm theo điểm mã (như Pydantic của API), không đếm đơn vị UTF-16: một biểu tượng cảm xúc tính là 1 ký tự, không phải 2
const between = (text, min, max) => { const n = [...text].length; return n >= min && n <= max; };

// Trả về câu báo lỗi (tiếng Việt) hoặc chuỗi rỗng nếu hợp lệ. name: editor_id | editor_role | description | tool.
export function validateField(name, raw) {
    const v = String(raw ?? '').trim();
    const { idPrefix, idMin, idMax, descMin, descMax, toolMin, toolMax } = EDIT_LIMITS;
    if (name === 'editor_id') {
        if (v && !ID.test(v)) return 'Chỉ dùng chữ không dấu, số, dấu gạch dưới và gạch nối.';
        if (!v.startsWith(idPrefix)) return `ID phải bắt đầu bằng ${idPrefix}.`;
        if (!between(v, idMin, idMax)) return `ID gồm ${idMin} đến ${idMax} ký tự.`;
        return '';
    }
    if (name === 'editor_role') return ROLES.some((r) => r.value === v) ? '' : 'Hãy chọn vai trò của bạn.';
    if (name === 'description') return between(v, descMin, descMax) ? '' : `Mô tả gồm ${descMin} đến ${descMax} ký tự.`;
    if (name === 'tool') return between(v, toolMin, toolMax) ? '' : `Tên công cụ gồm ${toolMin} đến ${toolMax} ký tự.`;
    return 'Trường không hợp lệ.';
}

// file: { type, size } (đối tượng File của trình duyệt cũng dùng được). Chỉ nhận PNG, không rỗng, tối đa EDIT_LIMITS.maxBytes.
export function validateFile(file) {
    if (!file) return 'Hãy chọn một ảnh PNG đã chỉnh sửa.';
    // Một số hệ điều hành không điền loại tệp: khi đó dựa vào đuôi .png (gateway vẫn kiểm chữ ký PNG thật)
    const type = file.type || (/\.png$/i.test(file.name || '') ? 'image/png' : '');
    if (type !== 'image/png') return 'Chỉ nhận ảnh PNG.';
    if (!(file.size > 0)) return 'Tệp rỗng.';
    if (file.size > EDIT_LIMITS.maxBytes) return `Ảnh vượt ${EDIT_LIMITS.maxBytes / 1024 / 1024} MB.`;
    return '';
}

// values: { editor_id, editor_role, description, tool }. Trả về { lỗi theo trường } (rỗng nếu tất cả hợp lệ).
export function validateAll(values) {
    const errors = {};
    for (const name of ['editor_id', 'editor_role', 'description', 'tool']) {
        const msg = validateField(name, values?.[name]);
        if (msg) errors[name] = msg;
    }
    return errors;
}
