const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const gateway = require('../../web_ui/api/live');

const port = 8061;
const base = 'http://127.0.0.1:' + port;
const python = process.env.PYTHON_EXECUTABLE || 'python';
const outputDir = fs.mkdtempSync(path.join(os.tmpdir(), 'dh-live-mock-'));
const child = spawn(python, ['-m', 'uvicorn', 'mock_backend:app',
    '--host', '127.0.0.1', '--port', String(port), '--log-level', 'error'], {
    cwd: path.resolve(__dirname, '..', '..'),
    env: { ...process.env, DH_API_KEY: 'local-contract-key', DH_OUTPUT_DIR: outputDir,
        DELAY: '0.1', FAIL: '0' },
    stdio: 'ignore',
    windowsHide: true,
});

process.env.MODAL_URL = base;
process.env.MODAL_KEY = 'local-contract-key';
process.env.MODAL_TIMEOUT_MS = '1500';
process.env.ALERT_DISCORD_WEBHOOK_URL = '';

let requestIndex = 0;
async function request(route, method = 'GET', body = undefined, query = {}) {
    const res = {
        status(code) { this.code = code; return this; },
        json(value) { this.body = value; return this; },
        send(value) { this.body = value; return this; },
        setHeader() {},
    };
    await gateway({
        method, body, query: { route, ...query },
        headers: { 'x-forwarded-for': '203.0.113.' + (++requestIndex) },
    }, res);
    return res;
}

async function waitReady() {
    for (let i = 0; i < 50; i++) {
        try {
            const response = await fetch(base + '/health');
            if (response.ok) return;
        } catch {}
        await new Promise((resolve) => setTimeout(resolve, 200));
    }
    throw new Error('Mock FastAPI không khởi động.');
}

async function main() {
    try {
        await waitReady();
        const health = await request('health');
        assert.equal(health.body.generation_available, true);

        const started = await request('generate', 'POST', { heritage_id: 'LR3D_61', seed: 123 });
        assert.equal(started.code, 202);
        assert.equal(started.body.backend, 'modal');
        assert.equal(started.body.seed, 123);

        let status;
        for (let i = 0; i < 40; i++) {
            status = await request('generate/' + started.body.job_id,
                'GET', undefined, { heritage_id: 'LR3D_61' });
            if (status.body.status === 'completed') break;
            await new Promise((resolve) => setTimeout(resolve, 100));
        }
        assert.equal(status.body.status, 'completed');

        const passports = await request('passports');
        assert.equal(passports.code, 200);
        const item = passports.body.find((p) => p.heritage_id === 'LR3D_61');
        assert.ok(item && item.thumb);

        const media = await request('media/artifact', 'GET', undefined,
            { path: item.final_path });
        assert.equal(media.code, 200);
        assert.ok(Buffer.isBuffer(media.body) && media.body.length > 1000);

        const blocked = await request('passports/' + item.passport_id + '/qc', 'POST', {});
        assert.equal(blocked.code, 404);

        child.kill();
        await new Promise((resolve) => child.once('exit', resolve));
        const fallback = await request('generate', 'POST',
            { heritage_id: 'LR3D_61', seed: 124 });
        assert.equal(fallback.body.backend, 'demo');
        assert.equal(fallback.body.demo_label,
            'Kết quả đã sinh sẵn — không phải sinh trực tiếp');
        console.log('live gateway + FastAPI mock: 7 checks passed');
    } finally {
        if (child.exitCode === null) child.kill();
        if (outputDir.startsWith(os.tmpdir() + path.sep)) {
            fs.rmSync(outputDir, { recursive: true, force: true });
        }
    }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
