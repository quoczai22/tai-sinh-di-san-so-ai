/**
 * Cổng GHI bản chỉnh sửa: POST /api/live/passports/<mã>/edits  →  Modal POST /passports/<mã>/edits (rewrite trong vercel.json).
 *
 * Tách khỏi live.js để một lỗi ở đây không làm hỏng route sinh ảnh và đọc Passport đang chạy.
 * - Kiểm tra lại mọi trường như EditRequest của API (tsds/api/main.py) và biểu mẫu (assets/js/core/edit-rules.js).
 * - Chỉ nhận ảnh PNG thật (đúng chữ ký tệp), tối đa 3 MB và cạnh dài tối đa 4096 px (đọc từ phần IHDR, không giải mã ảnh).
 * - Khóa ghi do máy chủ giữ: biến MODAL_WRITE_KEY (cùng giá trị TSDS_WRITE_KEY của Modal); thiếu thì dùng MODAL_KEY.
 * - Tối đa EDIT_RATE_LIMIT_PER_HOUR (mặc định 5) lượt mỗi IP mỗi giờ, đếm trong bộ nhớ của từng instance.
 * - Không ghi nội dung biểu mẫu hay ảnh vào nhật ký; nhật ký chỉ có mã Passport. Chỉ trả về mã sửa, quyết định G3, trạng thái duyệt.
 */
const { getBackendConfig, fetchWithTimeout, getClientIp, logGatewayAudit } = require('./_shared');

const PASSPORT_ID = /^DP-[A-Z0-9]{2,8}-[0-9T]{8,15}-V[0-9]{1,2}$/;
const EDITOR_ID = /^TSDS[A-Za-z0-9_-]{1,20}$/;      // ID tài khoản: bắt đầu bằng TSDS, tối đa 24 ký tự (API cho phép rộng hơn: [A-Za-z0-9_-]{2,24})
const ROLES = ['designer', 'qc_officer'];
const MAX_BYTES = 3 * 1024 * 1024;
const MAX_SIDE = 4096;
const EDIT_TIMEOUT_MS = 55000;            // hàm chạy tối đa 60 giây (vercel.json); Modal có thể phải khởi động lại container
const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const buckets = new Map();

// Chiều rộng, cao của ảnh PNG đọc từ khối IHDR (byte 16 đến 23); trả null nếu không phải PNG hợp lệ.
function pngSize(buf) {
    if (buf.length < 24 || !buf.subarray(0, 8).equals(PNG_SIGNATURE) || buf.toString('ascii', 12, 16) !== 'IHDR') return null;
    return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

// Trả { payload } (đã làm sạch, sẵn sàng chuyển tiếp) hoặc { error, status }.
function validateBody(body) {
    const bad = (error, status = 400) => ({ error, status });
    if (!body || typeof body !== 'object') return bad('Yêu cầu không hợp lệ.');
    const text = (v) => (typeof v === 'string' ? v.trim() : '');
    const editorId = text(body.editor_id), description = text(body.description), tool = text(body.tool);
    if (!EDITOR_ID.test(editorId)) return bad('ID tài khoản không hợp lệ: phải bắt đầu bằng TSDS, tối đa 24 ký tự.');
    if (!ROLES.includes(body.editor_role)) return bad('Vai trò không hợp lệ.');
    // Đếm theo điểm mã như Pydantic của API (một biểu tượng cảm xúc là 1 ký tự, không phải 2 đơn vị UTF-16)
    const lenOf = (s) => Array.from(s).length;
    if (lenOf(description) < 5 || lenOf(description) > 500) return bad('Mô tả phải từ 5 đến 500 ký tự.');
    if (lenOf(tool) < 2 || lenOf(tool) > 80) return bad('Tên công cụ phải từ 2 đến 80 ký tự.');
    if (typeof body.image_png_base64 !== 'string') return bad('Thiếu ảnh.');
    const b64 = body.image_png_base64.split(',').pop();
    if (b64.length > Math.ceil(MAX_BYTES / 3) * 4 + 4) return bad('Ảnh vượt 3 MB.', 413);
    const bytes = Buffer.from(b64, 'base64');
    if (bytes.toString('base64') !== b64) return bad('Ảnh không phải base64 hợp lệ.');
    if (bytes.length === 0) return bad('Ảnh rỗng.');
    if (bytes.length > MAX_BYTES) return bad('Ảnh vượt 3 MB.', 413);
    const size = pngSize(bytes);
    if (!size) return bad('Chỉ nhận ảnh PNG hợp lệ.');
    if (size.width < 1 || size.height < 1 || Math.max(size.width, size.height) > MAX_SIDE) return bad(`Cạnh dài của ảnh tối đa ${MAX_SIDE} px.`);
    return { payload: { editor_id: editorId, editor_role: body.editor_role, description, tool, image_png_base64: b64 } };
}

function checkEditLimit(req) {
    const limit = Math.max(1, parseInt(process.env.EDIT_RATE_LIMIT_PER_HOUR || '5', 10));
    const now = Date.now();
    const ip = getClientIp(req);
    if (buckets.size > 1000) {               // dọn IP đã hết hạn để bộ nhớ của instance sống lâu không phình mãi
        for (const [key, times] of buckets) if (!times.some((t) => now - t < 60 * 60 * 1000)) buckets.delete(key);
    }
    const recent = (buckets.get(ip) || []).filter((t) => now - t < 60 * 60 * 1000);
    if (recent.length >= limit) { buckets.set(ip, recent); return { allowed: false }; }
    recent.push(now);
    buckets.set(ip, recent);
    return { allowed: true };
}

async function handler(req, res) {
    res.setHeader('Cache-Control', 'no-store');
    if (req.method !== 'POST') {
        res.setHeader('Allow', 'POST');
        return res.status(405).json({ detail: 'Chỉ nhận POST.' });
    }
    const id = String(req.query?.id || '');
    if (!PASSPORT_ID.test(id)) return res.status(400).json({ detail: 'Mã hồ sơ thiết kế không hợp lệ.' });
    const config = getBackendConfig();
    if (!config.modalUrl || !config.modalKey) return res.status(503).json({ detail: 'Máy chủ chưa được cấu hình.' });

    let body;
    try { body = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {}); }
    catch { return res.status(400).json({ detail: 'Yêu cầu không hợp lệ.' }); }
    const checked = validateBody(body);
    if (checked.error) return res.status(checked.status).json({ detail: checked.error });
    if (!checkEditLimit(req).allowed) return res.status(429).json({ detail: 'Bạn gửi quá nhiều lần. Hãy thử lại sau.' });

    const key = (process.env.MODAL_WRITE_KEY || '').trim() || config.modalKey;
    try {
        const upstream = await fetchWithTimeout(config.modalUrl + '/passports/' + encodeURIComponent(id) + '/edits', {
            method: 'POST',
            headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-API-Key': key },
            body: JSON.stringify(checked.payload),
        }, Math.max(config.modalTimeoutMs, EDIT_TIMEOUT_MS));
        if (upstream.status === 404) return res.status(404).json({ detail: 'Không tìm thấy hồ sơ thiết kế này trên máy chủ.' });
        if (upstream.status === 401 || upstream.status === 403) {
            return res.status(503).json({ detail: 'Máy chủ chưa xác thực được. Vui lòng báo nhóm vận hành.' });
        }
        if (upstream.status === 413 || upstream.status === 422) return res.status(upstream.status).json({ detail: 'Máy chủ từ chối ảnh hoặc thông tin này.' });
        if (!upstream.ok) return res.status(502).json({ detail: 'Máy chủ chưa phản hồi. Hãy thử lại sau ít phút.' });
        const result = await upstream.json();
        logGatewayAudit({ step: 5, event: 'gateway_edit', passport_id: id });
        return res.status(200).json({
            edit_id: result.edit_id ?? null, approval_status: result.approval_status ?? null, quality_decision: result.quality_decision ?? null,
        });
    } catch {
        return res.status(502).json({ detail: 'Máy chủ chưa phản hồi. Hãy thử lại sau ít phút.' });
    }
}

module.exports = handler;
module.exports.validateBody = validateBody;
module.exports.pngSize = pngSize;
