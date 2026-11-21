const { getBackendConfig, buildBackendHeaders } = require('./_shared');

module.exports = async function handler(req, res) {
    if (req.method === 'OPTIONS') {
        return res.status(204).end();
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
