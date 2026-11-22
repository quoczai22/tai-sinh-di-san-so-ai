const fs = require('fs');
const path = require('path');

/**
 * Bộ đếm Rate Limit theo IP (in-memory trên từng instance Vercel Function).
 * Giới hạn mặc định: RATE_LIMIT_PER_HOUR = 10 lượt / IP / giờ.
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
    const limit = Math.max(1, parseInt(process.env.RATE_LIMIT_PER_HOUR || '10', 10));
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
    const hfApiKey = (process.env.HF_API_KEY || '').trim();
    // Mặc định 25 giây: đủ cho Modal khởi động container nguội trước khi bị coi là sập.
    const modalTimeoutMs = Math.max(500, parseInt(process.env.MODAL_TIMEOUT_MS || '25000', 10));
    const hfTimeoutMs = Math.max(500, parseInt(process.env.HF_TIMEOUT_MS || '6000', 10));
    return { modalUrl, modalKey, hfSpaceUrl, hfToken, hfApiKey, modalTimeoutMs, hfTimeoutMs };
}

function buildBackendHeaders(backend, config = getBackendConfig()) {
    const headers = { Accept: 'application/json' };
    if (backend === 'modal') {
        if (config.modalKey) headers['X-API-Key'] = config.modalKey;
    } else if (backend === 'hf') {
        // Authorization: Bearer HF_TOKEN -> để Hugging Face cho phép vào Space riêng tư.
        // X-API-Key -> khoá ứng dụng, phải khớp DH_API_KEY đặt trong secret của Space.
        // Dùng HF_API_KEY nếu có, không thì dùng chung MODAL_KEY. Không gửi HF_TOKEN vào X-API-Key.
        if (config.hfToken) headers['Authorization'] = `Bearer ${config.hfToken}`;
        const appKey = config.hfApiKey || config.modalKey;
        if (appKey) headers['X-API-Key'] = appKey;
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

async function fetchReadWithRetry(url, options = {}, timeoutMs = 8000) {
    if ((options.method || 'GET').toUpperCase() !== 'GET') {
        throw new TypeError('Chỉ thử lại yêu cầu đọc GET.');
    }
    for (let attempt = 0; attempt < 2; attempt++) {
        try {
            const response = await fetchWithTimeout(url, options, timeoutMs);
            if (attempt === 0 && [502, 503, 504].includes(response.status)) {
                await new Promise((resolve) => setTimeout(resolve, 200));
                continue;
            }
            return response;
        } catch (error) {
            if (attempt === 1 || upstreamErrorType(error) === 'timeout') throw error;
            await new Promise((resolve) => setTimeout(resolve, 200));
        }
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

let lastAlertTimestamp = 0;

function _resetAlertCooldown() {
    lastAlertTimestamp = 0;
}

/**
 * Gửi cảnh báo sự cố tới Discord Webhook và/hoặc Zalo Bot Manager khi Modal gặp lỗi/timeout.
 * - Cooldown chống spam: mặc định 30 phút (ALERT_COOLDOWN_MIN) lưu trong RAM instance.
 * - Timeout 3s, bọc try/catch, không bao giờ làm hỏng request của người dùng.
 * - Tuyệt đối không gửi token, key hay IP người dùng.
 */
let lastPersonalChatId = '';

async function notifyAlert(message) {
    const webhookUrl = (process.env.ALERT_DISCORD_WEBHOOK_URL || '').trim();
    const zaloToken = (process.env.ALERT_ZALO_BOT_TOKEN || '').trim();
    const allowGroup = (process.env.ALERT_ZALO_ALLOW_GROUP || '0').trim() === '1';
    const userChatId = (process.env.ALERT_ZALO_USER_CHAT_ID || lastPersonalChatId || '').trim();
    const groupChatId = (process.env.ALERT_ZALO_CHAT_ID || '').trim();
    const zaloChatId = userChatId || (allowGroup ? groupChatId : '');
    const zaloBase = (process.env.ALERT_ZALO_API_BASE || 'https://bot-api.zapps.me').trim().replace(/\/$/, '');
    const hasZalo = Boolean(zaloToken && zaloChatId);
    if (!webhookUrl && !hasZalo) return;

    const cooldownMin = Math.max(1, parseInt(process.env.ALERT_COOLDOWN_MIN || '30', 10));
    const cooldownMs = cooldownMin * 60 * 1000;
    const now = Date.now();
    if (now - lastAlertTimestamp < cooldownMs) {
        return;
    }
    lastAlertTimestamp = now;

    const text = String(message || '');
    const tasks = [];
    if (webhookUrl) {
        tasks.push(
            fetchWithTimeout(
                webhookUrl,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: text }),
                },
                3000
            ).catch(() => {
                console.warn('[ALERT] Không thể gửi cảnh báo Discord.');
            })
        );
    }
    if (hasZalo) {
        tasks.push(
            fetchWithTimeout(
                `${zaloBase}/bot${zaloToken}/sendMessage`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ chat_id: zaloChatId, text }),
                },
                3000
            ).catch(() => {
                console.warn('[ALERT] Không thể gửi cảnh báo Zalo Bot.');
            })
        );
    }
    await Promise.all(tasks);
}

let lastModalIssue = null;

function alertModalIssue(type, endpoint, heritageId, viewerState) {
    const safeId = /^[A-Za-z0-9_-]{1,80}$/.test(String(heritageId || ''))
        ? String(heritageId) : 'không có';
    const time = new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
    const action = recommendedAction(type);
    lastModalIssue = { type, endpoint, heritageId: safeId, viewerState, action, time };
    return notifyAlert(`⚠️ Modal lỗi: ${type} | Endpoint: ${endpoint} | Hiện vật: ${safeId} | ` +
        `${time} (giờ VN) | giám khảo đang thấy ${viewerState}. | Gợi ý: ${action}`);
}

async function callChatModel(provider, systemPrompt, userPrompt, timeoutMs = 8000) {
    const isGroq = provider === 'groq';
    const apiKey = (isGroq ? process.env.GROQ_API_KEY : process.env.OPENROUTER_API_KEY || '').trim();
    if (!apiKey) throw new Error(`Missing ${provider} API key`);
    const model = (isGroq
        ? (process.env.GROQ_MODEL || 'openai/gpt-oss-20b')
        : (process.env.OPENROUTER_MODEL || 'google/gemini-2.5-flash')).trim();
    const url = isGroq
        ? 'https://api.groq.com/openai/v1/chat/completions'
        : 'https://openrouter.ai/api/v1/chat/completions';
    const bodyPayload = {
        model,
        messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: userPrompt },
        ],
        max_tokens: isGroq ? 1024 : 350,
        temperature: 0.2,
    };
    const res = await fetchWithTimeout(url, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(bodyPayload),
    }, timeoutMs);
    if (!res.ok) throw new Error(`${provider} HTTP ${res.status}`);
    const data = await res.json();
    const reply = data?.choices?.[0]?.message?.content?.trim();
    if (!reply) throw new Error(`${provider} empty reply`);
    return { model, reply };
}

async function probeAndRemedateModal(isFixMode) {
    const config = getBackendConfig();
    if (!config.modalUrl || !config.modalKey) {
        return { configured: false, ok: false, summary: 'Thiếu biến MODAL_URL hoặc MODAL_KEY trên Vercel.' };
    }
    if (!isFixMode) {
        return {
            configured: true,
            ok: !lastModalIssue,
            summary: lastModalIssue
                ? `Cấu hình Vercel đầy đủ; đang có ghi nhận sự cố gần nhất cần lưu ý.`
                : 'Hệ thống Vercel và Modal đã cấu hình đầy đủ, hoạt động bình thường. GPU T4 trên Modal đang ở chế độ chờ tiết kiệm credit (tự động thức dậy khi có người bấm Tạo thiết kế hoặc khi bạn nhắn "đánh thức GPU").',
        };
    }
    _resetAlertCooldown();
    const t0 = Date.now();
    try {
        const timeout = Math.max(20000, config.modalTimeoutMs);
        const healthRes = await fetchWithTimeout(`${config.modalUrl}/health`, {
            headers: buildBackendHeaders('modal', config),
        }, timeout);
        const elapsedMs = Date.now() - t0;
        if (!healthRes.ok) {
            return {
                configured: true,
                ok: false,
                httpStatus: healthRes.status,
                elapsedMs,
                summary: `Modal /health trả HTTP ${healthRes.status} sau ${elapsedMs}ms (${httpFailureType(healthRes.status)}).`,
            };
        }
        const health = await healthRes.json().catch(() => ({}));
        lastModalIssue = null;
        return {
            configured: true,
            ok: true,
            httpStatus: 200,
            elapsedMs,
            cuda: health.cuda,
            device: health.device,
            summary: `Đã đánh thức và kiểm tra Modal GPU thành công: phản hồi 200 OK sau ${elapsedMs}ms (CUDA=${health.cuda}, GPU=${health.device || 'T4'}).`,
        };
    } catch (error) {
        const elapsedMs = Date.now() - t0;
        return {
            configured: true,
            ok: false,
            elapsedMs,
            summary: `Không kết nối được Modal sau ${elapsedMs}ms (${upstreamErrorType(error)}).`,
        };
    }
}

async function handleZaloBotWebhook(body) {
    const zaloToken = (process.env.ALERT_ZALO_BOT_TOKEN || '').trim();
    const allowedChatIds = [
        (process.env.ALERT_ZALO_CHAT_ID || '').trim(),
        (process.env.ALERT_ZALO_USER_CHAT_ID || '').trim(),
    ].filter(Boolean);
    const allowGroup = (process.env.ALERT_ZALO_ALLOW_GROUP || '0').trim() === '1';
    const zaloBase = (process.env.ALERT_ZALO_API_BASE || 'https://bot-api.zapps.me').trim().replace(/\/$/, '');
    const msg = body?.message || body?.result?.message || null;
    const chatId = msg?.chat?.id ? String(msg.chat.id) : '';
    const chatType = String(msg?.chat?.chat_type || '').toUpperCase();
    const text = String(msg?.text || '').trim();
    if (!zaloToken || !chatId || !text) {
        return { ok: true, ignored: true };
    }
    if (chatType === 'GROUP' && !allowGroup) {
        return { ok: true, ignored: 'group_disabled' };
    }
    if (chatType === 'GROUP' && allowedChatIds.length && !allowedChatIds.includes(chatId)) {
        return { ok: true, ignored: true };
    }
    if (chatType !== 'GROUP') {
        lastPersonalChatId = chatId;
    }

    const isFixMode = /\b(sửa|sua|fix|khắc phục|khac phuc|giải quyết|giai quyet|đánh thức|danh thuc|warmup|wake|khởi động|khoi dong|thử lại|thu lai|retry|cứu|cuu)\b/i.test(text);
    const probe = await probeAndRemedateModal(isFixMode);
    const issueContext = lastModalIssue
        ? `Sự cố gần nhất: ${lastModalIssue.type} tại ${lastModalIssue.endpoint} (hiện vật ${lastModalIssue.heritageId}) lúc ${lastModalIssue.time}. Gợi ý gốc: ${lastModalIssue.action}`
        : 'Chưa ghi nhận sự cố Modal nào trong phiên hiện tại.';

    const primary = isFixMode ? 'openrouter' : 'groq';
    const secondary = isFixMode ? 'groq' : 'openrouter';
    const sysPrompt = isFixMode
        ? 'Bạn là Kỹ sư Trực chiến AI của dự án Tái Sinh Di Sản Số (Vercel + Modal GPU T4). Nhiệm vụ: dựa trên kết quả kiểm tra/đánh thức GPU vừa chạy và sự cố gần nhất, báo cáo ngắn gọn (dưới 110 từ, tiếng Việt rõ ràng) việc hệ thống vừa tự động thực hiện (đánh thức GPU, kiểm tra khóa, xóa cooldown) và hướng giải quyết cụ thể. Tuyệt đối không bịa đặt số liệu hay tiết lộ khóa.'
        : 'Bạn là Trợ lý Tóm tắt Vận hành của dự án Tái Sinh Di Sản Số. Nhiệm vụ: giải thích tình trạng hệ thống hoặc tóm tắt lỗi gần nhất bằng ngôn ngữ đời thường, tự nhiên, dễ hiểu cho cả nhóm (dưới 90 từ, tiếng Việt). Cuối tin nhắc nhẹ: nếu cần đánh thức GPU hoặc xử lý lỗi, nhắn "sửa lỗi" hoặc "đánh thức GPU".';
    const userPrompt = `Tin nhắn từ nhóm: "${text}"\nTrạng thái kiểm tra Modal vừa chạy: ${probe.summary}\n${issueContext}`;

    let replyText = '';
    try {
        const { model, reply } = await callChatModel(primary, sysPrompt, userPrompt, 9000);
        const badge = isFixMode ? `🛠️ [Giải quyết · ${model}]` : `📌 [Tóm tắt · ${model}]`;
        replyText = `${badge}\n${reply}`;
    } catch (_) {
        try {
            const { model, reply } = await callChatModel(secondary, sysPrompt, userPrompt, 9000);
            const badge = isFixMode ? `🛠️ [Giải quyết · ${model}]` : `📌 [Tóm tắt · ${model}]`;
            replyText = `${badge}\n${reply}`;
        } catch (__) {
            replyText = `${isFixMode ? '🛠️ [Tự động kiểm tra & đánh thức GPU]' : '📌 [Trạng thái hệ thống]'}\n• ${probe.summary}\n• ${issueContext}`;
        }
    }

    await fetchWithTimeout(`${zaloBase}/bot${zaloToken}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: chatId, text: replyText }),
    }, 5000).catch(() => {});

    return { ok: true, mode: isFixMode ? 'fix' : 'summary', probeOk: probe.ok };
}

function recommendedAction(type) {
    if (/sai khóa|HTTP 40[13]/i.test(type)) return 'Đối chiếu MODAL_KEY trên Vercel với DH_API_KEY trong Modal secret.';
    if (/thiếu.*(MODAL|backend)|chưa cấu hình/i.test(type)) return 'Kiểm tra biến môi trường Vercel rồi redeploy phần cấu hình bị đổi.';
    if (/hàng chờ đầy|HTTP 429|HTTP 409/i.test(type)) return 'Kiểm tra hàng đợi và job đang chạy; chờ rồi thử lại.';
    if (/job.*failed|job không còn/i.test(type)) return 'Xem log job trong Modal và trạng thái ảnh/Volume trước khi tạo lại.';
    if (/timeout|lỗi mạng|HTTP 50[234]/i.test(type)) return 'Kiểm tra Modal Logs, trạng thái GPU và credit; giữ bản demo cho người xem.';
    return 'Đối chiếu Vercel Runtime Logs và Modal Logs theo thời gian, endpoint.';
}

function upstreamErrorType(error) {
    return error?.name === 'AbortError' || /timeout/i.test(String(error?.message || ''))
        ? 'timeout' : 'lỗi mạng';
}

function httpFailureType(status) {
    return status === 401 || status === 403
        ? `sai khóa (HTTP ${status})` : `HTTP ${status}`;
}

module.exports = {
    checkRateLimit,
    getBackendConfig,
    buildBackendHeaders,
    fetchWithTimeout,
    fetchReadWithRetry,
    loadDemoData,
    getDemoVariants,
    logGatewayAudit,
    notifyAlert,
    alertModalIssue,
    handleZaloBotWebhook,
    upstreamErrorType,
    httpFailureType,
    _resetAlertCooldown,
};
