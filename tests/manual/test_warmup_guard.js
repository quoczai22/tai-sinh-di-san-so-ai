const assert = require('node:assert/strict');
const warmup = require('../../web_ui/api/warmup');

process.env.MODAL_URL = 'https://modal.example.test';
process.env.MODAL_KEY = 'modal-test-key';
process.env.WARMUP_KEY = 'warmup-test-key';
let calls = 0;
global.fetch = async () => { calls++; return Response.json({ status: 'ok' }); };

function response() {
    return {
        status(code) { this.code = code; return this; },
        json(body) { this.body = body; return this; },
    };
}

(async () => {
    for (const [method, key, expected] of [
        ['GET', '', 405], ['POST', '', 403], ['POST', 'wrong', 403],
    ]) {
        const res = response();
        await warmup({ method, headers: { 'x-warmup-key': key } }, res);
        assert.equal(res.code, expected);
    }
    assert.equal(calls, 0);
    const res = response();
    await warmup({ method: 'POST', headers: { 'x-warmup-key': 'warmup-test-key' } }, res);
    assert.equal(res.code, 200);
    assert.equal(calls, 1);
    console.log('warmup guard: public GET and unauthenticated POST blocked');
})().catch((error) => { console.error(error); process.exitCode = 1; });
