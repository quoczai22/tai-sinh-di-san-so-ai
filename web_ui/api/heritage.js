const fs = require('fs');
const path = require('path');

module.exports = async function handler(req, res) {
    if (req.method !== 'GET') {
        return res.status(405).json({ detail: 'Method Not Allowed' });
    }
    const candidates = [
        path.join(__dirname, '..', 'assets', 'data', 'heritage_items.json'),
        path.join(process.cwd(), 'assets', 'data', 'heritage_items.json'),
        path.join(process.cwd(), 'web_ui', 'assets', 'data', 'heritage_items.json'),
    ];
    for (const filePath of candidates) {
        if (fs.existsSync(filePath)) {
            const items = JSON.parse(fs.readFileSync(filePath, 'utf8'));
            res.setHeader('Cache-Control', 'public, max-age=300');
            return res.status(200).json(items);
        }
    }
    return res.status(404).json({ detail: 'Không tìm thấy dữ liệu hiện vật.' });
};
