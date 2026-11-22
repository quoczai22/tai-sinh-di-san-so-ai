// Kiểm tra script gửi thử bằng webhook localhost, không gửi Discord thật.
const assert = require('node:assert/strict');
const http = require('node:http');
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const script = path.resolve(__dirname, '../../scripts/deploy/test_alert.js');
const noUrl = { ...process.env };
delete noUrl.ALERT_DISCORD_WEBHOOK_URL;
const missing = spawnSync(process.execPath, [script], { env: noUrl, encoding: 'utf8' });
assert.equal(missing.status, 1);
assert.match(missing.stderr, /Thiếu ALERT_DISCORD_WEBHOOK_URL/);

let count = 0;
const server = http.createServer(async (req, res) => {
    let body = '';
    for await (const chunk of req) body += chunk;
    const message = JSON.parse(body).content;
    assert.ok(message.includes('Thử cảnh báo Tái Sinh Di Sản Số'));
    assert.ok(message.includes('giờ VN'));
    count += 1;
    res.writeHead(204); res.end();
});
server.listen(0, '127.0.0.1', async () => {
    const url = `http://127.0.0.1:${server.address().port}`;
    const child = require('node:child_process').spawn(process.execPath, [script], {
        env: { ...process.env, ALERT_DISCORD_WEBHOOK_URL: url },
        stdio: ['ignore', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk; });
    child.stderr.on('data', (chunk) => { stderr += chunk; });
    child.on('exit', (code) => {
        try {
            assert.equal(code, 0, stderr);
            assert.match(stdout, /Đã gửi/);
            assert.equal(count, 1);
            assert.equal((stdout + stderr).includes(url), false);
            console.log('alert script: missing variable and one local delivery passed');
        } catch (error) {
            console.error(error);
            process.exitCode = 1;
        } finally { server.close(); }
    });
});
