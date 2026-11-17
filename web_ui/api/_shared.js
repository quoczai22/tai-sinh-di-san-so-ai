const fs = require('fs');
const path = require('path');

/**
 * Bộ đếm Rate Limit theo IP (in-memory trên từng instance Vercel Function).
 * Giới hạn mặc định: RATE_LIMIT_PER_HOUR = 5 lượt / IP / giờ.
 * Lưu ý: Vì Vercel Serverless có thể khởi tạo lại container khi scale hoặc sau thời gian rảnh,
 * bộ đếm in-memory áp dụng trong vòng đời warm instance — phù hợp quy mô cuộc thi.
 */
const ipBuckets = new Map();

function getClientIp(req) {
    const xff = req.headers['x-forwarded-for'];
    if (typeof xff === 'string' && xff.trim()) {
        return xff.split(',')[0].trim();
    }
    return req.headers['x-real-ip'] || req.socket?.remoteAddress || 'unknown';
}

function checkRateLimit(req) {
    const limit = Math.max(1, parseInt(process.env.RATE_LIMIT_PER_HOUR || '5', 10));
    const windowMs = 60 * 60 * 1000;
    const now = Date.now();
    const ip = getClientIp(req);

    const timestamps = (ipBuckets.get(ip) || []).filter((ts) => now - ts < windowMs);
    if (timestamps.length >= limit) {
        ipBuckets.set(ip, timestamps);
        return { allowed: false, limit, remaining: 0, ip };
    }
    timestamps.push(now);
    ipBuckets.set(ip, timestamps);
    return { allowed: true, limit, remaining: limit - timestamps.length, ip };
}

function getBackendConfig() {
    const modalUrl = (process.env.MODAL_URL || '').trim().replace(/\/$/, '');
    const modalKey = (process.env.MODAL_KEY || '').trim();
    const hfSpaceUrl = (process.env.HF_SPACE_URL || '').trim().replace(/\/$/, '');
    const hfToken = (process.env.HF_TOKEN || '').trim();
    const modalTimeoutMs = Math.max(500, parseInt(process.env.MODAL_TIMEOUT_MS || '8000', 10));
    const hfTimeoutMs = Math.max(500, parseInt(process.env.HF_TIMEOUT_MS || '8000', 10));
    return { modalUrl, modalKey, hfSpaceUrl, hfToken, modalTimeoutMs, hfTimeoutMs };
}

function buildBackendHeaders(backend, config = getBackendConfig()) {
    const headers = { Accept: 'application/json' };
    if (backend === 'modal') {
        if (config.modalKey) headers['X-API-Key'] = config.modalKey;
    } else if (backend === 'hf') {
        if (config.hfToken) {
            headers['Authorization'] = `Bearer ${config.hfToken}`;
            headers['X-API-Key'] = config.hfToken;
        }
        if (config.modalKey && !headers['X-API-Key']) {
            headers['X-API-Key'] = config.modalKey;
        }
    }
    return headers;
}

async function fetchWithTimeout(url, options = {}, timeoutMs = 8000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(new Error(`Timeout after ${timeoutMs}ms`)), timeoutMs);
    try {
        return await fetch(url, { ...options, signal: controller.signal });
    } finally {
        clearTimeout(timer);
    }
}

let cachedDemoData = null;
function loadDemoData() {
    if (cachedDemoData) return cachedDemoData;
    const candidates = [
        path.join(__dirname, '..', 'assets', 'data', 'demo_variants.json'),
        path.join(process.cwd(), 'assets', 'data', 'demo_variants.json'),
        path.join(process.cwd(), 'web_ui', 'assets', 'data', 'demo_variants.json'),
    ];
    for (const filePath of candidates) {
        if (fs.existsSync(filePath)) {
            cachedDemoData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
            return cachedDemoData;
        }
    }
    return { items: {} };
}

function getDemoVariants(heritageId) {
    const data = loadDemoData();
    const list = data?.items?.[heritageId] || [];
    return list.map((variant) => ({
        ...variant,
        image_url: variant.image_url || `./assets/images/variants/${heritageId}_V${variant.variant_index}_aodai.png`,
    }));
}

function logGatewayAudit(entry) {
    const payload = {
        timestamp: new Date().toISOString(),
        ...entry,
    };
    console.log('[AUDIT]', JSON.stringify(payload));
    try {
        const outDir = process.env.DH_OUTPUT_DIR
            ? path.resolve(process.env.DH_OUTPUT_DIR)
            : path.resolve(__dirname, '..', '..', 'outputs');
        const auditDir = path.join(outDir, 'audit');
        if (fs.existsSync(path.dirname(outDir))) {
            fs.mkdirSync(auditDir, { recursive: true });
            fs.appendFileSync(path.join(auditDir, 'audit.jsonl'), `${JSON.stringify(payload)}\n`, 'utf8');
        }
    } catch (_) {
        // Trên Vercel serverless filesystem là read-only; stdout log đã lưu vào Vercel Runtime Logs.
    }
}

module.exports = {
    checkRateLimit,
    getBackendConfig,
    buildBackendHeaders,
    fetchWithTimeout,
    loadDemoData,
    getDemoVariants,
    logGatewayAudit,
};
