const assert = require('node:assert/strict');
const live = require('../../web_ui/api/live');

process.env.ALERT_ZALO_BOT_TOKEN = 'test-bot-token';
process.env.ALERT_ZALO_WEBHOOK_SECRET = 'test-webhook-secret';
process.env.ALERT_ZALO_USER_CHAT_ID = 'owner-123';
process.env.ALERT_ZALO_CHAT_ID = 'group-456';
process.env.MODAL_URL = 'https://modal.example.test';
process.env.MODAL_KEY = 'test-modal-key';

const calls = [];
global.fetch = async (url) => {
    calls.push(String(url));
    return new Response(JSON.stringify({ status: 'ok', cuda: true, device: 'T4' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
    });
};

function response() {
    return {
        status(code) { this.code = code; return this; },
        json(body) { this.body = body; return this; },
    };
}

async function post(chatId, text, secret) {
    const res = response();
    await live({
        method: 'POST',
        query: { route: 'zalo-webhook' },
        headers: { 'x-bot-api-secret-token': secret || '' },
        body: { message: { chat: { id: chatId, chat_type: chatId.startsWith('group') ? 'GROUP' : 'PRIVATE' }, text } },
    }, res);
    return res;
}

(async () => {
    assert.equal((await post('owner-123', 'đánh thức GPU')).code, 403);
    assert.equal((await post('owner-123', 'đánh thức GPU', 'wrong')).code, 403);
    assert.equal(calls.length, 0);
    assert.equal((await post('new-owner', '/id', 'test-webhook-secret')).body.mode, 'chat_id');
    assert.equal(calls.length, 1);
    assert.ok(calls[0].endsWith('/sendMessage'));
    calls.length = 0;
    assert.equal((await post('stranger', 'đánh thức GPU', 'test-webhook-secret')).body.ignored, true);
    assert.equal((await post('group-456', 'đánh thức GPU', 'test-webhook-secret')).body.ignored, 'operator_only');
    assert.equal((await post('group-456', 'số dư', 'test-webhook-secret')).body.ignored, 'operator_only');
    assert.equal(calls.length, 0);
    const owner = await post('owner-123', 'đánh thức GPU', 'test-webhook-secret');
    assert.equal(owner.body.mode, 'fix');
    assert.ok(calls.some((url) => url.endsWith('/health')));
    const count = calls.length;
    assert.equal((await post('owner-123', 'đánh thức GPU', 'test-webhook-secret')).body.ignored, 'rate_limited');
    assert.equal(calls.length, count);
    console.log('Zalo webhook guard: secret, allowlist, operator-only wake, and cooldown passed');
})().catch((error) => { console.error(error); process.exitCode = 1; });
