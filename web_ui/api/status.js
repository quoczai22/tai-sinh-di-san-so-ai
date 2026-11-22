const path = require('path');
const {
    getBackendConfig,
    buildBackendHeaders,
    fetchWithTimeout,
    getDemoVariants,
    logGatewayAudit,
    alertModalIssue,
} = require('./_shared');

function rewriteVariantsMedia(variants, backend) {
    if (!Array.isArray(variants)) return [];
    return variants.map((variant) => {
        const rawPath = variant.image_url || variant.design_path || '';
        const filename = path.posix.basename(String(rawPath).replace(/\\/g, '/'));
        return {
            ...variant,
            image_url: filename
                ? `/api/media?backend=${encodeURIComponent(backend)}&file=${encodeURIComponent(filename)}`
                : rawPath,
        };
    });
}

module.exports = async function handler(req, res) {
    if (req.method === 'OPTIONS') {
        return res.status(204).end();
    }
    if (req.method !== 'GET') {
        return res.status(405).json({ detail: 'Method Not Allowed' });
    }

    const jobId = String(req.query?.job_id || '').trim();
    const backend = String(req.query?.backend || 'modal').trim();
    const heritageId = String(req.query?.heritage_id || '').trim();

    if (!jobId) {
        return res.status(400).json({ detail: 'Thiếu tham số job_id.' });
    }

    if (backend === 'demo' || jobId.startsWith('demo_')) {
        const resolvedHeritageId = heritageId || jobId.replace(/^demo_/, '').replace(/_\d+$/, '');
        return res.status(200).json({
            job_id: jobId,
            heritage_id: resolvedHeritageId,
            backend: 'demo',
            status: 'completed',
            progress: 100,
            queue_position: 0,
            failover: true,
            demo_label: 'Kết quả đã sinh sẵn — không phải sinh trực tiếp',
            label: 'GPU đang bận hoặc tạm ngừng — hiển thị kết quả đã sinh sẵn',
            variants: getDemoVariants(resolvedHeritageId),
        });
    }

    const config = getBackendConfig();

    // Trường hợp HF Space đang thức dậy (job_id = warming_<heritageId>_<timestamp>)
    if (backend === 'hf' && jobId.startsWith('warming_')) {
        const parts = jobId.split('_');
        const ts = parseInt(parts[parts.length - 1], 10) || Date.now();
        const resolvedHeritageId =
            heritageId || decodeURIComponent(parts.slice(1, -1).join('_'));
        const maxWarmupMs = parseInt(process.env.HF_WARMUP_MAX_MS || '180000', 10);

        if (!config.hfSpaceUrl || Date.now() - ts > maxWarmupMs) {
            await alertModalIssue('máy dự phòng không khả dụng', '/api/status', resolvedHeritageId, 'bản demo');
            return res.status(200).json({
                job_id: jobId,
                heritage_id: resolvedHeritageId,
                backend: 'demo',
                status: 'completed',
                progress: 100,
                queue_position: 0,
                failover: true,
                demo_label: 'Kết quả đã sinh sẵn — không phải sinh trực tiếp',
                label: 'GPU đang bận hoặc tạm ngừng — hiển thị kết quả đã sinh sẵn',
                variants: getDemoVariants(resolvedHeritageId),
            });
        }

        try {
            const hfHeaders = buildBackendHeaders('hf', config);
            const healthRes = await fetchWithTimeout(
                `${config.hfSpaceUrl}/health`,
                { method: 'GET', headers: hfHeaders },
                config.hfTimeoutMs
            );
            if (!healthRes.ok) {
                return res.status(200).json({
                    job_id: jobId,
                    heritage_id: resolvedHeritageId,
                    backend: 'hf',
                    warming: true,
                    status: 'queued',
                    progress: 5,
                    queue_position: 1,
                    label: 'Đang khởi động máy dự phòng (2–3 phút)…',
                });
            }

            // HF Space đã thức dậy -> gửi POST /generate để lấy job_id thật
            const genRes = await fetchWithTimeout(
                `${config.hfSpaceUrl}/generate`,
                {
                    method: 'POST',
                    headers: {
                        ...hfHeaders,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ heritage_id: resolvedHeritageId }),
                },
                config.hfTimeoutMs
            );
            if (genRes.ok) {
                const genData = await genRes.json();
                logGatewayAudit({
                    step: 3,
                    event: 'hf_warmup_ready',
                    heritage_id: resolvedHeritageId,
                    job_id: genData.job_id,
                    backend: 'hf',
                    wait_ms: Date.now() - ts,
                    failover: true,
                });
                return res.status(200).json({
                    job_id: genData.job_id,
                    heritage_id: resolvedHeritageId,
                    backend: 'hf',
                    warming: false,
                    status: 'queued',
                    progress: 8,
                    queue_position: genData.queue_position ?? 0,
                    label: 'Máy dự phòng đã sẵn sàng. Đang tạo thiết kế...',
                });
            }
            await alertModalIssue(`máy dự phòng HTTP ${genRes.status}`, '/api/status',
                resolvedHeritageId, 'bản demo');
        } catch (_) {
            // Nếu lỗi mạng tạm thời trong lúc Space đang thức
            return res.status(200).json({
                job_id: jobId,
                heritage_id: resolvedHeritageId,
                backend: 'hf',
                warming: true,
                status: 'queued',
                progress: 5,
                queue_position: 1,
                label: 'Đang khởi động máy dự phòng (2–3 phút)…',
            });
        }
    }

    const baseUrl = backend === 'hf' ? config.hfSpaceUrl : config.modalUrl;
    const timeoutMs = backend === 'hf' ? config.hfTimeoutMs : config.modalTimeoutMs;

    if (!baseUrl) {
        await alertModalIssue('thiếu cấu hình backend', '/api/status', heritageId, heritageId ? 'bản demo' : 'lỗi');
        if (heritageId) {
            return res.status(200).json({
                job_id: jobId,
                heritage_id: heritageId,
                backend: 'demo',
                status: 'completed',
                progress: 100,
                queue_position: 0,
                failover: true,
                demo_label: 'Kết quả đã sinh sẵn — không phải sinh trực tiếp',
                label: 'Kết quả đã sinh sẵn — không phải sinh trực tiếp',
                variants: getDemoVariants(heritageId),
            });
        }
        return res.status(503).json({ detail: `Backend ${backend} chưa được cấu hình.` });
    }

    async function alertModalFailure(reason) {
        if (jobId.startsWith('warming_')) return;
        const source = backend === 'modal' ? 'giữa chừng' : 'máy dự phòng';
        await alertModalIssue(source + ' (' + reason + ')', '/api/status', heritageId,
            heritageId ? 'bản demo' : 'lỗi');
    }

    try {
        const upstream = await fetchWithTimeout(
            `${baseUrl}/generate/${encodeURIComponent(jobId)}`,
            {
                method: 'GET',
                headers: buildBackendHeaders(backend, config),
            },
            timeoutMs
        );
        if (!upstream.ok) {
            if (heritageId) {
                await alertModalFailure(`HTTP ${upstream.status}`);
                return res.status(200).json({
                    job_id: jobId,
                    heritage_id: heritageId,
                    backend: 'demo',
                    status: 'completed',
                    progress: 100,
                    queue_position: 0,
                    failover: true,
                    demo_label: 'Kết quả đã sinh sẵn — không phải sinh trực tiếp',
                    label: 'Kết quả đã sinh sẵn — không phải sinh trực tiếp',
                    variants: getDemoVariants(heritageId),
                });
            }
            await alertModalFailure(`HTTP ${upstream.status}`);
            return res.status(upstream.status).json({ detail: `Upstream status ${upstream.status}` });
        }

        const data = await upstream.json();
        if (data.status === 'failed') {
            await alertModalIssue(backend === 'modal' ? 'job failed' : 'job dự phòng failed',
                '/api/status', heritageId, 'lỗi');
        }
        return res.status(200).json({
            ...data,
            job_id: jobId,
            backend,
            queue_position: data.queue_position ?? 0,
            variants: data.variants ? rewriteVariantsMedia(data.variants, backend) : undefined,
        });
    } catch (error) {
        if (heritageId) {
            const isTimeout = error && (error.name === 'AbortError' || /timeout/i.test(error.message));
            await alertModalFailure(isTimeout ? `timeout ${Math.round(timeoutMs / 1000)}s` : 'lỗi kết nối');
            return res.status(200).json({
                job_id: jobId,
                heritage_id: heritageId,
                backend: 'demo',
                status: 'completed',
                progress: 100,
                queue_position: 0,
                failover: true,
                demo_label: 'Kết quả đã sinh sẵn — không phải sinh trực tiếp',
                label: 'Kết quả đã sinh sẵn — không phải sinh trực tiếp',
                variants: getDemoVariants(heritageId),
            });
        }
        await alertModalFailure('timeout hoặc lỗi mạng');
        return res.status(504).json({ detail: 'Máy sinh thiết kế không phản hồi.' });
    }
};
