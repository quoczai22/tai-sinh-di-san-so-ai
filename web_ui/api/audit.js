const { logGatewayAudit } = require('./_shared');

module.exports = async function handler(req, res) {
    if (req.method === 'OPTIONS') {
        return res.status(204).end();
    }
    if (req.method !== 'POST') {
        return res.status(405).json({ detail: 'Method Not Allowed' });
    }
    const body = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {});
    logGatewayAudit({
        ...body,
        source: 'web_ui',
    });
    return res.status(202).json({ status: 'recorded' });
};
