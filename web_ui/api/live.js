const {
    checkRateLimit,
    getBackendConfig,
    buildBackendHeaders,
    fetchWithTimeout,
    notifyAlert,
    logGatewayAudit,
} = require('./_shared');

const DEMO_LABEL = 'Kết quả đã sinh sẵn — không phải sinh trực tiếp';
const ID = /^[A-Za-z0-9_-]{1,80}$/;
const JOB_ID = /^[A-Za-z0-9_-]{1,100}$/;
const RUN_ID = /^R[0-9]{8}T[0-9]{6}-[A-Z0-9]{2,8}$/;
const FILE = /^[A-Za-z0-9_.-]{1,80}\.png$/;
const PASSPORT_ID = /^DP-[A-Z0-9]{2,8}-[0-9T]{8,15}-V[0-9]{1,2}$/;

function demo(jobId, heritageId, reason) {
    return {
        job_id: jobId || 'demo_' + Date.now(),
        heritage_id: heritageId,
        backend: 'demo',
        status: 'completed',
        progress: 100,
        failover: true,
        demo_label: DEMO_LABEL,
        label: DEMO_LABEL,
        reason,
    };
}

async function alertFailure(heritageId, reason) {
    const time = new Date().toLocaleTimeString('vi-VN', {
        timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit', hour12: false,
    });
    await notifyAlert('⚠️ Modal lỗi (' + reason + ') lúc ' + time +
        ' (giờ VN) — giám khảo đang thấy bản demo. Hiện vật: ' + heritageId);
}

async function forward(req, res, upstreamPath, options = {}) {
    const config = getBackendConfig();
    if (!config.modalUrl || !config.modalKey) {
        return res.status(503).json({ detail: 'Máy sinh thiết kế chưa được cấu hình.' });
    }
    const headers = buildBackendHeaders('modal', config);
    if (options.body) headers['Content-Type'] = 'application/json';
    const upstream = await fetchWithTimeout(config.modalUrl + upstreamPath, {
        method: req.method,
        headers,
        ...(options.body ? { body: JSON.stringify(options.body) } : {}),
    }, config.modalTimeoutMs);
    if (!upstream.ok) {
        return res.status(upstream.status).json({ detail: 'Máy sinh thiết kế trả mã ' + upstream.status });
    }
    if (options.binary) {
        const bytes = Buffer.from(await upstream.arrayBuffer());
        res.setHeader('Content-Type', upstream.headers.get('content-type') || 'image/png');
        res.setHeader('Cache-Control', 'private, max-age=60');
        return res.status(200).send(bytes);
    }
    const payload = await upstream.json();
    return res.status(upstream.status).json(options.transform ? options.transform(payload) : payload);
}

module.exports = async function handler(req, res) {
    const routeParam = req.query?.route || '';
    const route = (Array.isArray(routeParam) ? routeParam.join('/') : String(routeParam))
        .replace(/^\/+|\/+$/g, '');
    const config = getBackendConfig();

    if (route === 'health' && req.method === 'GET') {
        return res.status(200).json({
            status: 'ok',
            runtime: 'vercel-cpu',
            generation_available: Boolean(config.modalUrl && config.modalKey),
        });
    }
    if (route === 'generate' && req.method === 'POST') {
        const body = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {});
        const heritageId = String(body.heritage_id || '');
        if (!ID.test(heritageId) || !Number.isInteger(body.seed) ||
            body.seed < 0 || body.seed > 2147483647) {
            return res.status(400).json({ detail: 'Hiện vật hoặc seed không hợp lệ.' });
        }
        if (!config.modalUrl || !config.modalKey) {
            return res.status(200).json(demo(null, heritageId, 'modal_not_configured'));
        }
        const rate = checkRateLimit(req);
        res.setHeader('X-RateLimit-Limit', String(rate.limit));
        res.setHeader('X-RateLimit-Remaining', String(rate.remaining));
        if (!rate.allowed) {
            return res.status(200).json(demo(null, heritageId, 'rate_limit_exceeded'));
        }
        try {
            const upstream = await fetchWithTimeout(config.modalUrl + '/generate', {
                method: 'POST',
                headers: { ...buildBackendHeaders('modal', config), 'Content-Type': 'application/json' },
                body: JSON.stringify({ heritage_id: heritageId, seed: body.seed }),
            }, config.modalTimeoutMs);
            if (upstream.status === 409) {
                return res.status(409).json({
                    detail: 'Một lượt sinh đang chạy trên GPU. Hãy chờ lượt đó hoàn tất rồi thử lại.',
                });
            }
            if (upstream.status === 429) {
                return res.status(429).json({
                    detail: 'Hàng chờ tạo thiết kế đã đầy. Vui lòng thử lại sau.',
                });
            }
            if (!upstream.ok) throw new Error('HTTP ' + upstream.status);
            const job = await upstream.json();
            logGatewayAudit({ step: 3, event: 'gateway_generate', heritage_id: heritageId,
                job_id: job.job_id, backend: 'modal', failover: false });
            return res.status(202).json({ ...job, backend: 'modal' });
        } catch (error) {
            await alertFailure(heritageId, error.name === 'AbortError' ? 'timeout' : 'lỗi kết nối');
            return res.status(200).json(demo(null, heritageId, 'modal_unavailable'));
        }
    }
    const job = route.match(/^generate\/([^/]+)$/);
    if (job && req.method === 'GET' && JOB_ID.test(job[1])) {
        const heritageId = String(req.query?.heritage_id || '');
        if (!ID.test(heritageId)) return res.status(400).json({ detail: 'Thiếu mã hiện vật.' });
        if (!config.modalUrl || !config.modalKey) {
            return res.status(200).json(demo(job[1], heritageId, 'modal_not_configured'));
        }
        try {
            const upstream = await fetchWithTimeout(
                config.modalUrl + '/generate/' + encodeURIComponent(job[1]),
                { headers: buildBackendHeaders('modal', config) }, config.modalTimeoutMs);
            if (upstream.status === 404) {
                return res.status(404).json({ detail: 'Lượt sinh không còn trên máy chủ. Vui lòng tạo lại.' });
            }
            if (!upstream.ok) throw new Error('HTTP ' + upstream.status);
            return res.status(200).json(await upstream.json());
        } catch (error) {
            await alertFailure(heritageId, error.name === 'AbortError' ? 'timeout' : 'lỗi kết nối');
            return res.status(200).json(demo(job[1], heritageId, 'modal_unavailable'));
        }
    }
    if (route === 'heritage' && req.method === 'GET') {
        return forward(req, res, '/heritage?include_retired=true');
    }
    if (route === 'passports' && req.method === 'GET') {
        return forward(req, res, '/passports', { transform: (items) => items.map((item) => ({
            ...item,
            thumb: item.final_path
                ? '/api/live/media/artifact?path=' + encodeURIComponent(item.final_path) : null,
            repair_thumb: item.repair_path
                ? '/api/live/media/artifact?path=' + encodeURIComponent(item.repair_path) : null,
            pattern_thumb: item.final_path
                ? '/api/live/media/artifact?path=' +
                    encodeURIComponent(item.final_path.replace(/_aodai\.png$/, '_pattern.png')) : null,
        })) });
    }
    if (route === 'experiments' && req.method === 'GET') {
        return forward(req, res, '/experiments');
    }
    if (route === 'audit' && req.method === 'POST') {
        const body = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {});
        if (!Number.isInteger(body.step) || typeof body.event !== 'string' ||
            body.event.length > 80) return res.status(400).json({ detail: 'Audit không hợp lệ.' });
        try { return await forward(req, res, '/audit', { body }); }
        catch { return res.status(202).json({ recorded: false }); }
    }
    if (req.method === 'GET' && route === 'media/artifact') {
        const artifact = String(req.query?.path || '');
        if (!/^outputs\/runs\/[A-Za-z0-9_./-]{1,180}\.png$/.test(artifact) ||
            artifact.includes('..')) return res.status(400).json({ detail: 'Đường ảnh không hợp lệ.' });
        return forward(req, res, '/media/artifact?path=' + encodeURIComponent(artifact), { binary: true });
    }
    const heritageImage = route.match(/^media\/heritage\/([^/]+)$/);
    if (req.method === 'GET' && heritageImage && ID.test(heritageImage[1])) {
        return forward(req, res, '/media/heritage/' + encodeURIComponent(heritageImage[1]), { binary: true });
    }
    const runImage = route.match(/^media\/run\/([^/]+)\/([^/]+)$/);
    if (req.method === 'GET' && runImage && RUN_ID.test(runImage[1]) && FILE.test(runImage[2])) {
        return forward(req, res, '/media/run/' + runImage[1] + '/' + runImage[2], { binary: true });
    }
    const passport = route.match(/^passports\/([^/]+)$/);
    if (req.method === 'GET' && passport && PASSPORT_ID.test(passport[1])) {
        return forward(req, res, '/passports/' + encodeURIComponent(passport[1]));
    }
    return res.status(404).json({ detail: 'Route không tồn tại.' });
};
