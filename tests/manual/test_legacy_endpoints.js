const assert = require('node:assert/strict');
const generate = require('../../web_ui/api/generate');
const status = require('../../web_ui/api/status');

function response() {
    return {
        headers: {},
        setHeader(name, value) { this.headers[name] = value; },
        status(code) { this.code = code; return this; },
        json(body) { this.body = body; return this; },
    };
}

async function main() {
    for (const [handler, method] of [[generate, 'POST'], [status, 'GET']]) {
        const res = response();
        await handler({ method, body: { heritage_id: 'LR3D_61' }, query: { job_id: 'old-job', heritage_id: 'LR3D_61' } }, res);
        assert.equal(res.code, 410);
        assert.equal(res.headers['Cache-Control'], 'no-store');
        assert.equal(res.body.backend, undefined);
        assert.equal(res.body.variants, undefined);
        assert.match(res.body.detail, /\/api\/live\/generate/);
    }
    console.log('legacy generation endpoints: 410, no demo result');
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
