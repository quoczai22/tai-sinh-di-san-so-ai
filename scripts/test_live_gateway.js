const assert = require('node:assert/strict');
const handler = require('../web_ui/api/live');
const { _resetAlertCooldown } = require('../web_ui/api/_shared');

process.env.MODAL_URL = 'https://modal.mock';
process.env.MODAL_KEY = 'local-test-key';
process.env.MODAL_TIMEOUT_MS = '500';
process.env.RATE_LIMIT_PER_HOUR = '1';
process.env.ALERT_DISCORD_WEBHOOK_URL = 'https://alert.mock';

function response() {
    return {
        status(code) { this.code = code; return this; },
        json(value) { this.body = value; return this; },
        send(value) { this.body = value; return this; },
        end() { return this; },
        setHeader() {},
    };
}

let ip = 0;
async function call(route, method = 'GET', body = undefined, query = {}) {
    const req = {
        method, body, query: { route, ...query },
        headers: { 'x-forwarded-for': '192.0.2.' + (++ip) },
        socket: { remoteAddress: '127.0.0.1' },
    };
    const res = response();
    await handler(req, res);
    return res;
}

async function main() {
    let requests = [];
    let alerts = 0;
    global.fetch = async (url, options = {}) => {
        requests.push({ url, options });
        if (url === 'https://alert.mock') { alerts++; return new Response(null, { status: 204 }); }
        if (url.endsWith('/generate') && options.method === 'POST') {
            if (JSON.parse(options.body).seed === 47) {
                return Response.json({ detail: 'Hàng chờ đầy' }, { status: 429 });
            }
            return Response.json({ job_id: 'abc123', status_url: '/generate/abc123' }, { status: 202 });
        }
        if (url.endsWith('/generate/abc123')) {
            return Response.json({ status: 'completed', progress: 100, variants: [] });
        }
        if (url.endsWith('/generate/missing')) {
            return Response.json({ detail: 'Không tìm thấy job' }, { status: 404 });
        }
        if (url.endsWith('/passports')) {
            return Response.json([{
                passport_id: 'DP-HV08-20261119T161848-V1',
                final_path: 'outputs/runs/R20261119T161848-HV08/V1_aodai.png',
            }]);
        }
        throw new Error('Unexpected upstream URL: ' + url);
    };

    let result = await call('health');
    assert.equal(result.code, 200);
    assert.equal(result.body.generation_available, true);
    assert.equal(requests.length, 0, 'health must not wake Modal');

    result = await call('generate', 'POST', { heritage_id: 'LR3D_61', seed: 42 });
    assert.equal(result.code, 202);
    assert.equal(result.body.backend, 'modal');
    assert.equal(requests[0].options.headers['X-API-Key'], 'local-test-key');
    assert.equal(JSON.stringify(result.body).includes('local-test-key'), false);

    result = await call('generate/abc123', 'GET', undefined, { heritage_id: 'LR3D_61' });
    assert.equal(result.body.status, 'completed');
    result = await call('generate/missing', 'GET', undefined, { heritage_id: 'LR3D_61' });
    assert.equal(result.code, 404, 'a lost job must be retryable, not labeled demo');

    result = await call('generate', 'POST', { heritage_id: 'LR3D_61', seed: 47 });
    assert.equal(result.code, 429);
    assert.equal(result.body.backend, undefined, 'full queue must not be labeled demo');

    result = await call('passports');
    assert.equal(result.body.length, 1);
    assert.match(result.body[0].thumb, /^\/api\/live\/media\/artifact\?path=/);

    result = await call('passports/DP-HV08-20261119T161848-V1/qc', 'POST', {});
    assert.equal(result.code, 404, 'write route must not be forwarded');

    _resetAlertCooldown();
    global.fetch = async (url) => {
        if (url === 'https://alert.mock') { alerts++; return new Response(null, { status: 204 }); }
        throw new Error('mock connection failure');
    };
    result = await call('generate', 'POST', { heritage_id: 'LR3D_61', seed: 43 });
    assert.equal(result.body.backend, 'demo');
    assert.equal(result.body.demo_label, 'Kết quả đã sinh sẵn — không phải sinh trực tiếp');
    result = await call('generate', 'POST', { heritage_id: 'LR3D_61', seed: 44 });
    assert.equal(result.body.backend, 'demo');
    assert.equal(alerts, 1, 'Discord alert must respect cooldown');

    process.env.MODAL_URL = '';
    _resetAlertCooldown();
    result = await call('generate', 'POST', { heritage_id: 'LR3D_61', seed: 45 });
    assert.equal(result.body.backend, 'demo');
    assert.equal(alerts, 1, 'unconfigured Modal must not alert');

    process.env.MODAL_URL = 'https://modal.mock';
    process.env.ALERT_DISCORD_WEBHOOK_URL = '';
    global.fetch = async () => Response.json({ job_id: 'abc123' }, { status: 202 });
    const sameIp = '198.51.100.1';
    const req = { method: 'POST', body: { heritage_id: 'LR3D_61', seed: 46 },
        query: { route: 'generate' }, headers: { 'x-forwarded-for': sameIp } };
    await handler(req, response());
    result = response();
    await handler(req, result);
    assert.equal(result.body.reason, 'rate_limit_exceeded');
    console.log('live gateway: 11 contract checks passed (mock only)');
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
