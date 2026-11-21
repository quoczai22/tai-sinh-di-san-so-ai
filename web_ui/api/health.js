module.exports = async function handler(req, res) {
    // Endpoint /health trên CPU: không chạm tới GPU hay gọi backend GPU,
    // để UptimeRobot ping định kỳ mà không đánh thức Modal / HF Space.
    return res.status(200).json({ status: 'ok', runtime: 'vercel-cpu' });
};
