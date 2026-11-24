// Endpoint cũ đã ngừng dùng. Luồng sinh ảnh hiện hành đi qua /api/live/generate.
module.exports = async function handler(req, res) {
    res.setHeader('Cache-Control', 'no-store');
    return res.status(410).json({ detail: 'API này đã ngừng dùng. Hãy sử dụng /api/live/generate.' });
};
