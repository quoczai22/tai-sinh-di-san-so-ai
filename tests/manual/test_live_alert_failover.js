// Kiểm tra cổng live với Modal và Discord giả lập, không dùng GPU hay webhook thật.
const assert = require('node:assert/strict');
const http = require('node:http');
const live = require('../../web_ui/api/live');
const { _resetAlertCooldown } = require('../../web_ui/api/_shared');

const messages = [];
const listen = (server) => new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const close = (server) => new Promise((resolve) => server.close(resolve));
const reply = () => ({
    setHeader() {},
    status(code) { this.code = code; return this; },
    json(body) { this.body = body; return this; },
});

async function main() {
    let mode = '503';
    const modal = http.createServer((req, res) => {
        if (mode === '503') { res.writeHead(503); res.end('unavailable'); }
        if (mode === '401') { res.writeHead(401); res.end('unauthorized'); }
        if (mode === '429') { res.writeHead(429); res.end('queue full'); }
        if (mode === 'failed' && req.url.startsWith('/generate/')) {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ status: 'failed', progress: 20 }));
        }
    });
    const webhook = http.createServer(async (req, res) => {
        let body = '';
        for await (const chunk of req) body += chunk;
        messages.push(JSON.parse(body).content);
        res.writeHead(204); res.end();
    });
    await Promise.all([listen(modal), listen(webhook)]);
    process.env.MODAL_URL = `http://127.0.0.1:${modal.address().port}`;
    process.env.MODAL_KEY = 'test-only-key';
    process.env.MODAL_TIMEOUT_MS = '500';
    process.env.ALERT_DISCORD_WEBHOOK_URL = `http://127.0.0.1:${webhook.address().port}`;
    process.env.ALERT_COOLDOWN_MIN = '30';
    delete process.env.HF_SPACE_URL;

    const generate = async () => {
        const res = reply();
        await live({ method: 'POST', query: { route: 'generate' },
            body: { heritage_id: 'LR3D_33' }, headers: { 'x-forwarded-for': '203.0.113.20' } }, res);
        assert.equal(res.code, 200);
        assert.equal(res.body.backend, 'demo');
        return res;
    };
    try {
        for (const failure of ['503', 'timeout']) {
            mode = failure;
            messages.length = 0;
            _resetAlertCooldown();
            await generate();
            await generate();
            assert.equal(messages.length, 1, `${failure}: one alert during cooldown`);
            const message = messages[0];
            for (const value of ['/api/live/generate', 'LR3D_33', 'giờ VN',
                'đang thấy bản demo', failure]) assert.ok(message.includes(value), message);
            for (const secret of ['test-only-key', process.env.MODAL_URL,
                process.env.ALERT_DISCORD_WEBHOOK_URL, '203.0.113.20']) {
                assert.equal(message.includes(secret), false);
            }
        }
        for (const [failure, expectedCode] of [['401', 503], ['429', 429]]) {
            mode = failure;
            messages.length = 0;
            _resetAlertCooldown();
            const res = reply();
            await live({ method: 'POST', query: { route: 'generate' },
                body: { heritage_id: 'LR3D_61' }, headers: { 'x-forwarded-for': '203.0.113.21' } }, res);
            assert.equal(res.code, expectedCode);
            assert.equal(messages.length, 1);
            assert.ok(messages[0].includes('/api/live/generate'));
            assert.ok(messages[0].includes(failure));
            assert.ok(messages[0].includes('đang thấy lỗi'));
        }
        mode = 'failed';
        messages.length = 0;
        _resetAlertCooldown();
        const failed = reply();
        await live({ method: 'GET', query: { route: 'generate/job123', heritage_id: 'LR3D_61' } }, failed);
        assert.equal(failed.body.status, 'failed');
        assert.equal(messages.length, 1);
        assert.ok(messages[0].includes('job failed'));

        messages.length = 0;
        _resetAlertCooldown();
        delete process.env.MODAL_URL;
        const missing = reply();
        await live({ method: 'POST', query: { route: 'generate' },
            body: { heritage_id: 'LR3D_61' }, headers: { 'x-forwarded-for': '203.0.113.22' } }, missing);
        assert.equal(missing.body.backend, 'demo');
        assert.equal(messages.length, 1);
        assert.ok(messages[0].includes('thiếu MODAL_URL'));

        process.env.MODAL_URL = `http://127.0.0.1:${modal.address().port}`;
        process.env.RATE_LIMIT_PER_HOUR = '1';
        mode = '503';
        const limitedRequest = () => live({ method: 'POST', query: { route: 'generate' },
            body: { heritage_id: 'LR3D_61' }, headers: { 'x-forwarded-for': '203.0.113.23' } }, reply());
        await limitedRequest();
        messages.length = 0;
        _resetAlertCooldown();
        await limitedRequest();
        assert.equal(messages.length, 0, 'per-IP rate limit is not an operational failure');
        console.log('live alerts: 503, timeout, 401, queue 429, failed job, missing config; IP limit stays quiet');
    } finally {
        await Promise.all([close(modal), close(webhook)]);
    }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
