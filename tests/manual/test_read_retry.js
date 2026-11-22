// Thử lại đúng một lần cho GET lỗi tạm thời; không bao giờ gửi lại POST sinh ảnh.
const assert = require('node:assert/strict');
const { fetchReadWithRetry } = require('../../web_ui/api/_shared');

async function scenario(first, expectedCalls, expectedStatus) {
    let calls = 0;
    global.fetch = async () => {
        calls += 1;
        if (calls === 1 && first instanceof Error) throw first;
        return { status: calls === 1 ? first : 200 };
    };
    const response = await fetchReadWithRetry('https://example.invalid/read', {}, 1000);
    assert.equal(response.status, expectedStatus);
    assert.equal(calls, expectedCalls);
}

async function main() {
    await scenario(503, 2, 200);
    await scenario(new TypeError('network error'), 2, 200);
    await scenario(401, 1, 401);
    let calls = 0;
    global.fetch = async () => { calls += 1; throw new Error('should not be called'); };
    await assert.rejects(fetchReadWithRetry('https://example.invalid/generate', { method: 'POST' }), TypeError);
    assert.equal(calls, 0);
    console.log('read retry: one retry for 503/network, none for 401 or POST');
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
