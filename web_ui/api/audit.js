const { logGatewayAudit, readJsonBody } = require('./_shared');

module.exports = async function handler(req, res) {
    if (req.method === 'OPTIONS') {
        return res.status(204).end();
    }
    if (req.method !== 'POST') {
        return res.status(405).json({ detail: 'Method Not Allowed' });
    }
    const body = readJsonBody(req);
    if (!body) return res.status(400).json({ detail: 'Yêu cầu không hợp lệ.' });
    logGatewayAudit({
        ...body,
        source: 'web_ui',
    });
    return res.status(202).json({ status: 'recorded' });
};
