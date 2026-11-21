import assert from 'node:assert/strict';

const entries = new Map();
const prefetched = [];
globalThis.Image = class {
    set src(value) { prefetched.push(value); }
};
globalThis.localStorage = {
    getItem: (key) => entries.get(key) ?? null,
    setItem: (key, value) => entries.set(key, String(value)),
    removeItem: (key) => entries.delete(key),
};
globalThis.window = { DH_API_BASE: '/api/live' };
globalThis.location = { hash: '#/result/LR3D_33' };
entries.set('dh:last-live-run', JSON.stringify({ heritageId: 'LR3D_33', runId: 'R-old' }));
entries.set('dh:pending-generation', JSON.stringify({
    heritageId: 'LR3D_33', jobId: 'job123', startedAt: Date.now(),
}));

let posts = 0;
let healthFails = false;
globalThis.fetch = async (url, options = {}) => {
    if (url === '/api/live/health') {
        if (healthFails) throw new Error('Health temporarily unavailable');
        return Response.json({ generation_available: true });
    }
    if (url === './data/meta.json') return Response.json({});
    if (url.startsWith('/api/live/generate/job123')) {
        return Response.json({ status: 'completed', progress: 100, run_id: 'R-new', variants:
            [1, 2, 3, 4].map((n) => ({ status: 'completed', passport_id: `DP-TEST-V${n}`,
                run_id: 'R-new', image_url: `/media/run/R-new/V${n}_aodai.png` })) });
    }
    if (options.method === 'POST') posts++;
    throw new Error('Unexpected request: ' + url);
};

const data = await import('../../web_ui/assets/js/core/data.js');
const { pendingGeneration, runGeneration } = await import('../../web_ui/assets/js/core/generation.js');

await data.init();
assert.equal(data.isLive(), true);
assert.equal(data.liveRunFor('LR3D_33'), 'R-old');

location.hash = '#/studio/LR3D_33';
await data.init();
assert.equal(data.isLive(), false);
assert.equal(pendingGeneration().jobId, 'job123', 'closing a tab must retain the pending job');

const job = await runGeneration('LR3D_33', 42);
assert.equal(job.run_id, 'R-new');
assert.equal(posts, 0, 'reload must resume instead of creating another GPU job');
assert.equal(entries.has('dh:pending-generation'), false);
assert.equal(data.liveDesignsFor('LR3D_33').length, 4);
assert.equal(prefetched.length, 4, 'all four images should start loading before result navigation');
assert.equal(data.media(data.liveDesignsFor('LR3D_33')[0].final_path),
    '/api/live/media/run/R-new/V1_aodai.png');
assert.equal(posts, 0, 'result cards should use completed job data without a new POST');

location.hash = '#/result/LR3D_33';
healthFails = true;
await data.init();
assert.equal(data.isLive(), true);
assert.equal(data.liveRunFor('LR3D_33'), 'R-new');
console.log('live session: returning browser restores the completed run without a second POST');
