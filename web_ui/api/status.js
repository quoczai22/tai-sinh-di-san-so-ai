// Endpoint cũ đã ngừng dùng. Trạng thái job hiện hành đi qua /api/live/generate/:job_id.
module.exports = async function handler(req, res) {
    res.setHeader('Cache-Control', 'no-store');
    return res.status(410).json({ detail: 'API này đã ngừng dùng. Hãy sử dụng /api/live/generate/:job_id.' });
};
