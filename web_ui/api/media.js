const fs = require('fs');
const path = require('path');
const { getBackendConfig, buildBackendHeaders, fetchReadWithRetry, alertModalIssue,
    upstreamErrorType, httpFailureType } = require('./_shared');

const SAFE_FILENAME_RE = /^[A-Za-z0-9._-]+$/;

function tryServeLocalVariant(filename, res) {
    const candidates = [
        path.join(__dirname, '..', 'assets', 'images', 'variants', filename),
        path.join(process.cwd(), 'assets', 'images', 'variants', filename),
        path.join(process.cwd(), 'web_ui', 'assets', 'images', 'variants', filename),
    ];
    for (const filePath of candidates) {
        if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
            const ext = path.extname(filename).toLowerCase();
            res.setHeader('Content-Type', ext === '.jpg' || ext === '.jpeg' ? 'image/jpeg' : 'image/png');
            res.setHeader('Cache-Control', 'public, max-age=3600');
            return res.status(200).send(fs.readFileSync(filePath));
        }
    }
    return null;
}

module.exports = async function handler(req, res) {
    if (req.method !== 'GET') {
        return res.status(405).json({ detail: 'Method Not Allowed' });
    }

    const filename = String(req.query?.file || '').trim();
    const backend = String(req.query?.backend || 'modal').trim();

    if (!filename || !SAFE_FILENAME_RE.test(filename) || filename.includes('..')) {
        return res.status(400).json({ detail: 'Tên file ảnh không hợp lệ.' });
    }

    const config = getBackendConfig();
    const baseUrl = backend === 'hf' ? config.hfSpaceUrl : config.modalUrl;
    const timeoutMs = backend === 'hf' ? config.hfTimeoutMs : config.modalTimeoutMs;

    let failure = baseUrl ? null : 'thiếu MODAL_URL';
    if (baseUrl) {
        try {
            const upstream = await fetchReadWithRetry(
                `${baseUrl}/media/variant/${encodeURIComponent(filename)}`,
                {
                    method: 'GET',
                    headers: buildBackendHeaders(backend, config),
                },
                timeoutMs
            );
            if (upstream.ok) {
                const contentType = upstream.headers.get('content-type') || 'image/png';
                const arrayBuffer = await upstream.arrayBuffer();
                res.setHeader('Content-Type', contentType);
                res.setHeader('Cache-Control', 'public, max-age=3600');
                return res.status(200).send(Buffer.from(arrayBuffer));
            }
            failure = httpFailureType(upstream.status);
        } catch (error) {
            failure = upstreamErrorType(error);
            // Fallback sang ảnh tĩnh nếu backend vừa tắt sau khi sinh xong
        }
    }

    const served = tryServeLocalVariant(filename, res);
    if (served) return served;

    if (backend === 'modal') {
        await alertModalIssue(failure || 'ảnh không có trong backend', '/api/media', null, 'lỗi');
    }

    return res.status(404).json({ detail: 'Không tìm thấy ảnh thiết kế.' });
};
