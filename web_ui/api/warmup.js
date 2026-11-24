const { getBackendConfig, buildBackendHeaders } = require('./_shared');
const { timingSafeEqual } = require('node:crypto');

module.exports = async function handler(req, res) {
    if (req.method !== 'POST') return res.status(405).json({ detail: 'Method Not Allowed' });
    const expected = (process.env.WARMUP_KEY || '').trim();
    const supplied = String(req.headers?.['x-warmup-key'] || '');
    if (!expected || !supplied || Buffer.byteLength(expected) !== Buffer.byteLength(supplied) ||
        !timingSafeEqual(Buffer.from(expected), Buffer.from(supplied))) {
        return res.status(403).json({ detail: 'Forbidden' });
    }
    const config = getBackendConfig();
    if (config.modalUrl) {
        // Gọi ngầm /health của Modal để đánh thức container (không chờ kết quả)
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 1500);
        fetch(`${config.modalUrl}/health`, {
            method: 'GET',
            headers: buildBackendHeaders('modal', config),
            signal: controller.signal,
        })
            .catch(() => {})
            .finally(() => clearTimeout(timer));
    }
    return res.status(200).json({
        status: 'ok',
        warming_triggered: Boolean(config.modalUrl),
    });
};
