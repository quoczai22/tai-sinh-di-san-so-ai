const {
    checkRateLimit,
    getBackendConfig,
    buildBackendHeaders,
    fetchWithTimeout,
    getDemoVariants,
    logGatewayAudit,
    notifyAlert,
} = require('./_shared');

function buildDemoResponse(heritageId, reason, waitMs, extra = {}) {
    const variants = getDemoVariants(heritageId);
    logGatewayAudit({
        step: 3,
        event: 'gateway_generate',
        heritage_id: heritageId,
        backend: 'demo',
        failover: true,
        reason,
        wait_ms: waitMs,
    });
    return {
        job_id: `demo_${heritageId}_${Date.now()}`,
        heritage_id: heritageId,
        backend: 'demo',
        reason,
        status: 'completed',
        progress: 100,
        queue_position: 0,
        failover: true,
        demo_label: 'Kết quả đã sinh sẵn — không phải sinh trực tiếp',
        label: extra.message || 'GPU đang bận hoặc tạm ngừng — hiển thị kết quả đã sinh sẵn',
        variants,
        ...extra,
    };
}

module.exports = async function handler(req, res) {
    if (req.method === 'OPTIONS') {
        return res.status(204).end();
    }
    if (req.method !== 'POST') {
        return res.status(405).json({ detail: 'Method Not Allowed' });
    }

    const t0 = Date.now();
    const body = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {});
    const heritageId = (body.heritage_id || '').trim();
    if (!heritageId) {
        return res.status(400).json({ detail: 'Thiếu trường heritage_id.' });
    }

    // Bước 3: Kiểm tra rate limit theo IP
    const rate = checkRateLimit(req);
    res.setHeader('X-RateLimit-Limit', String(rate.limit));
    res.setHeader('X-RateLimit-Remaining', String(rate.remaining));
    if (!rate.allowed) {
        return res.status(200).json(
            buildDemoResponse(heritageId, 'rate_limit_exceeded', Date.now() - t0, {
                rate_limited: true,
                message: `Đã vượt giới hạn ${rate.limit} lượt sinh trực tiếp/giờ cho IP của bạn. Hiển thị kết quả thực nghiệm đã sinh sẵn.`,
            })
        );
    }

    const config = getBackendConfig();
    let modalFailureReason = null;

    // Bước 4: Thử gọi Modal GPU (backend chính)
    if (config.modalUrl) {
        try {
            const modalRes = await fetchWithTimeout(
                `${config.modalUrl}/generate`,
                {
                    method: 'POST',
                    headers: {
                        ...buildBackendHeaders('modal', config),
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ heritage_id: heritageId }),
                },
                config.modalTimeoutMs
            );
            if (modalRes.ok) {
                const data = await modalRes.json();
                const waitMs = Date.now() - t0;
                logGatewayAudit({
                    step: 3,
                    event: 'gateway_generate',
                    heritage_id: heritageId,
                    job_id: data.job_id,
                    backend: 'modal',
                    failover: false,
                    wait_ms: waitMs,
                });
                return res.status(202).json({
                    job_id: data.job_id,
                    heritage_id: heritageId,
                    backend: 'modal',
                    warming: false,
                    failover: false,
                    queue_position: data.queue_position ?? 0,
                    status_url: `/api/status?job_id=${encodeURIComponent(data.job_id)}&backend=modal&heritage_id=${encodeURIComponent(heritageId)}`,
                });
            } else {
                modalFailureReason = `HTTP ${modalRes.status}`;
            }
        } catch (err) {
            const isTimeout = (err && (err.name === 'AbortError' || /timeout/i.test(err.message)));
            modalFailureReason = isTimeout ? `timeout ${Math.round(config.modalTimeoutMs / 1000)}s` : 'lỗi kết nối';
        }
    } else {
        modalFailureReason = 'chưa cấu hình URL';
    }

    // Bước 5: Modal lỗi/timeout -> gọi HF Space dự phòng
    if (config.hfSpaceUrl) {
        try {
            const hfHeaders = buildBackendHeaders('hf', config);
            let healthRes = await fetchWithTimeout(
                `${config.hfSpaceUrl}/health`,
                { method: 'GET', headers: hfHeaders },
                config.hfTimeoutMs
            );

            // HF Space đang ngủ / khởi động (502/503): KHÔNG chờ trong function này
            // (giữ tổng thời gian chạy của function ngắn). Trả ngay job "warming"
            // để frontend poll tiếp qua /api/status.
            let wasWarming = false;
            if (healthRes.status === 503 || healthRes.status === 502) {
                const errText = await healthRes.text().catch(() => '');
                const isExplicitFail = errText.includes('FAIL=1');
                if (!isExplicitFail) {
                    wasWarming = true;
                    if (!healthRes.ok) {
                        const warmingJobId = `warming_${encodeURIComponent(heritageId)}_${Date.now()}`;
                        const waitMs = Date.now() - t0;
                        logGatewayAudit({
                            step: 3,
                            event: 'gateway_generate_warming',
                            heritage_id: heritageId,
                            job_id: warmingJobId,
                            backend: 'hf',
                            warming: true,
                            failover: true,
                            wait_ms: waitMs,
                        });
                        return res.status(202).json({
                            job_id: warmingJobId,
                            heritage_id: heritageId,
                            backend: 'hf',
                            warming: true,
                            failover: true,
                            queue_position: 1,
                            label: 'Đang khởi động máy dự phòng (2–3 phút)…',
                            status_url: `/api/status?job_id=${encodeURIComponent(warmingJobId)}&backend=hf&heritage_id=${encodeURIComponent(heritageId)}`,
                        });
                    }
                }
            }

            if (healthRes.ok) {
                const hfGenRes = await fetchWithTimeout(
                    `${config.hfSpaceUrl}/generate`,
                    {
                        method: 'POST',
                        headers: {
                            ...hfHeaders,
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ heritage_id: heritageId }),
                    },
                    config.hfTimeoutMs
                );
                if (hfGenRes.ok) {
                    const data = await hfGenRes.json();
                    const waitMs = Date.now() - t0;
                    logGatewayAudit({
                        step: 3,
                        event: 'gateway_generate',
                        heritage_id: heritageId,
                        job_id: data.job_id,
                        backend: 'hf',
                        warming: wasWarming,
                        failover: true,
                        wait_ms: waitMs,
                    });
                    return res.status(202).json({
                        job_id: data.job_id,
                        heritage_id: heritageId,
                        backend: 'hf',
                        warming: wasWarming,
                        failover: true,
                        queue_position: data.queue_position ?? 0,
                        status_url: `/api/status?job_id=${encodeURIComponent(data.job_id)}&backend=hf&heritage_id=${encodeURIComponent(heritageId)}`,
                    });
                }
            }
        } catch (_) {
            // HF Space cũng lỗi hoặc timeout -> chuyển sang Bước 6 (Demo mode)
        }
    }

    // Bước 6: Cả hai backend đều lỗi -> gửi cảnh báo Discord (nếu cấu hình) và trả Demo mode
    const vnTime = new Date().toLocaleTimeString('vi-VN', {
        timeZone: 'Asia/Ho_Chi_Minh',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
    });
    const alertMsg = `⚠️ Modal lỗi (${modalFailureReason || 'không khả dụng'}) lúc ${vnTime} (giờ VN) — giám khảo đang thấy bản demo. Hiện vật: ${heritageId}`;
    await notifyAlert(alertMsg).catch(() => {});

    return res.status(200).json(buildDemoResponse(heritageId, 'all_backends_unavailable', Date.now() - t0));
};
