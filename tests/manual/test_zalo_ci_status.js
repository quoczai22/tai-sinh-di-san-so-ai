const assert = require('node:assert/strict');
const live = require('../../web_ui/api/live');

process.env.ALERT_ZALO_BOT_TOKEN = 'test-bot-token';
process.env.ALERT_ZALO_WEBHOOK_SECRET = 'test-webhook-secret';
process.env.ALERT_ZALO_USER_CHAT_ID = 'owner';
process.env.ALERT_ZALO_CHAT_ID = 'group';

function response() {
    return {
        status(code) { this.code = code; return this; },
        json(body) { this.body = body; return this; },
    };
}

async function post(chatId, text) {
    const res = response();
    await live({
        method: 'POST', query: { route: 'zalo-webhook' },
        headers: { 'x-bot-api-secret-token': 'test-webhook-secret' },
        body: { message: { chat: { id: chatId, chat_type: chatId === 'group' ? 'GROUP' : 'PRIVATE' }, text } },
    }, res);
    return res;
}

(async () => {
    const requests = [];
    let sent = '';
    global.fetch = async (url, options = {}) => {
        requests.push(String(url));
        if (String(url).startsWith('https://api.github.com/')) {
            return Response.json({ workflow_runs: [{
                id: 12345, status: 'completed', conclusion: 'success', head_branch: 'main',
                head_sha: 'c7412944b4e2e3a3f9ddfd23021dffe1a042a543',
            }] });
        }
        if (String(url).endsWith('/sendMessage')) {
            sent = JSON.parse(options.body).text;
            return Response.json({ ok: true });
        }
        throw new Error(`Unexpected external request: ${url}`);
    };

    assert.equal((await post('unknown', 'ci')).body.ignored, true);
    assert.equal(requests.length, 0);
    assert.equal((await post('group', 'ci')).body.mode, 'ci_status');
    assert.match(sent, /CI main: đạt · commit c741294/);
    assert.match(sent, /CodeBuild/);
    assert.match(sent, /Bot không tự deploy/);
    assert.equal(requests.filter((url) => url.startsWith('https://api.github.com/')).length, 1);
    assert.ok(requests.every((url) => !url.includes('modal.run') && !url.includes('codebuild.amazonaws.com')));

    global.fetch = async (url, options = {}) => {
        if (String(url).startsWith('https://api.github.com/')) return Response.json({}, { status: 503 });
        if (String(url).endsWith('/sendMessage')) {
            sent = JSON.parse(options.body).text;
            return Response.json({ ok: true });
        }
        throw new Error(`Unexpected external request: ${url}`);
    };
    assert.equal((await post('owner', 'trạng thái phát hành')).body.mode, 'ci_status');
    assert.match(sent, /Chưa đọc được trạng thái CI/);
    assert.doesNotMatch(sent, /CI main: đạt/);
    console.log('Zalo CI/CD status: allowlist, exact run, read-only and honest fallback passed');
})().catch((error) => { console.error(error); process.exitCode = 1; });
