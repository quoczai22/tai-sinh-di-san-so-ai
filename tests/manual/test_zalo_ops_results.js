const assert = require('node:assert/strict');
const { formatUsageReport, formatCreditReport, formatGpuStatus } = require('../../web_ui/api/bot_ops_commands');
const { tryHandleDesignCommand } = require('../../web_ui/api/bot_design_preview');
const live = require('../../web_ui/api/live');

process.env.ALERT_ZALO_BOT_TOKEN = 'test-bot';
process.env.ALERT_ZALO_WEBHOOK_SECRET = 'test-secret';
process.env.ALERT_ZALO_USER_CHAT_ID = 'owner';
process.env.ALERT_ZALO_CHAT_ID = 'group';
process.env.MODAL_URL = 'https://modal.test';
process.env.MODAL_KEY = 'key';

const calls = [];
global.fetch = async (url) => {
    calls.push(String(url));
    return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'Content-Type': 'application/json' } });
};
function response() {
    return { status(code) { this.code = code; return this; }, json(body) { this.body = body; return this; } };
}
async function post(chatId, chatType, message) {
    const res = response();
    await live({ method: 'POST', query: { route: 'zalo-webhook' },
        headers: { 'x-bot-api-secret-token': 'test-secret' },
        body: { message: { chat: { id: chatId, chat_type: chatType }, text: message } } }, res);
    return res.body;
}

(async () => {
    assert.match(formatUsageReport(null, 0), /0 lượt/);
    assert.doesNotMatch(formatUsageReport(null, 0), /3\.16|2\.21|100% miễn phí/);
    assert.match(formatCreditReport(null), /chưa kết nối API billing/);
    assert.doesNotMatch(formatCreditReport(null), /0\.00\$|95 phút/);
    assert.match(formatGpuStatus(null, 6000), /Không xác minh được/);
    assert.doesNotMatch(formatGpuStatus(null, 6000), /đang ở chế độ ngủ/);

    assert.equal((await post('group', 'GROUP', '/gpu')).ignored, 'operator_only');
    assert.equal(calls.length, 0);
    assert.equal((await post('owner', 'PRIVATE', '/gpu')).mode, 'ops_gpu');
    assert.equal(calls.filter((url) => url.endsWith('/health')).length, 1);
    assert.equal((await post('owner', 'PRIVATE', '/runs')).ignored, 'rate_limited');

    const directCalls = [];
    const fetchWithTimeout = async (url, options) => {
        directCalls.push(String(url));
        if (String(url).includes('/generate/job-abc')) {
            return new Response(JSON.stringify({ status: 'completed', heritage_id: 'LR3D_33', run_id: 'R20261124T120000-HV07' }), { status: 200 });
        }
        if (String(url).endsWith('/sendPhoto')) {
            return new Response(JSON.stringify({ ok: false, error_code: 500 }), { status: 200 });
        }
        return new Response(JSON.stringify({ ok: true }), { status: 200 });
    };
    const result = await tryHandleDesignCommand({
        text: 'xem job-abc', normalizedText: 'xem job-abc', chatId: 'owner', chatType: 'PRIVATE',
        zaloBase: 'https://zalo.test', zaloToken: 'test-bot', fetchWithTimeout,
        getBackendConfig: () => ({ modalUrl: 'https://modal.test' }), buildBackendHeaders: () => ({}),
    });
    assert.equal(result.runId, 'R20261124T120000-HV07');
    assert.equal(result.sent, 0);
    assert.ok(directCalls.some((url) => url.endsWith('/generate/job-abc')));
    assert.ok(!directCalls.some((url) => url.endsWith('/passports')));
    console.log('Zalo ops and exact-job result guards passed');
})().catch((error) => { console.error(error); process.exitCode = 1; });
