// Xác nhận hai health endpoint chỉ trả lời tại Vercel, không gọi Modal.
const assert = require('node:assert/strict');
const health = require('../../web_ui/api/health');
const live = require('../../web_ui/api/live');

process.env.MODAL_URL = 'https://modal.invalid';
process.env.MODAL_KEY = 'test-only-key';
let calls = 0;
global.fetch = async () => { calls += 1; throw new Error('health must not fetch'); };

function response() {
    return {
        status(code) { this.code = code; return this; },
        json(body) { this.body = body; return this; },
    };
}

async function main() {
    const plain = response();
    await health({ method: 'GET' }, plain);
    assert.equal(plain.code, 200);
    assert.equal(plain.body.runtime, 'vercel-cpu');

    const gateway = response();
    await live({ method: 'GET', query: { route: 'health' } }, gateway);
    assert.equal(gateway.code, 200);
    assert.equal(gateway.body.runtime, 'vercel-cpu');
    assert.equal(gateway.body.generation_available, true);
    assert.equal(calls, 0, 'health endpoints must never wake Modal');
    console.log('health endpoints: 2 responses, 0 Modal fetches');
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
