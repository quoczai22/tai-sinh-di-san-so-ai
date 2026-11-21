// core/data.js — LỚP DỮ LIỆU duy nhất của giao diện (mọi view/component lấy dữ liệu qua đây, không tự fetch).
// Vào: window.DH_API_BASE (config.js). Ra: heritage(), passports(), media(), startGeneration()/jobStatus(), audit().
// Vị trí trong pipeline GUI: bước 0 (init chọn chế độ) → cấp dữ liệu cho views/* và components/hero/*.
// Lớp dữ liệu hai chế độ:
//  · live — gọi API FastAPI (sinh ảnh thật trên GPU, ghi phiếu thẩm định, chỉnh sửa)
//  · demo — đọc ./data/*.json do scripts/11_export_demo_data.py xuất từ dữ liệu THẬT
// Chế độ được xác định một lần khi mở trang bằng /health (chờ tối đa 2,5 giây).

const API = (window.DH_API_BASE || '').replace(/\/$/, '');
const state = { mode: 'demo', health: null, meta: null, cache: new Map(), latestResult: null, preloads: [] };
const LIVE_RUN_KEY = 'dh:last-live-run';

function savedLiveRun() {
    try {
        const saved = JSON.parse(localStorage.getItem(LIVE_RUN_KEY) || 'null');
        return saved?.heritageId && saved?.runId ? saved : null;
    } catch { return null; }
}

async function getJson(url, opts = {}) {
    const res = await fetch(url, { cache: 'no-store', ...opts });
    if (!res.ok) {
        let detail = `Máy chủ trả mã ${res.status}`;
        try { detail = (await res.json()).detail || detail; } catch { /* không phải JSON */ }
        const err = new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
        err.status = res.status;
        throw err;
    }
    return res.json();
}

async function cached(key, loader) {
    if (!state.cache.has(key)) state.cache.set(key, loader().catch((e) => { state.cache.delete(key); throw e; }));
    return state.cache.get(key);
}

export async function init() {
    const resultId = location.hash.match(/^#\/result\/([^/]+)$/)?.[1];
    const saved = savedLiveRun();
    state.mode = resultId && decodeURIComponent(resultId) === saved?.heritageId ? 'live' : 'demo';
    if (API) {
        try {
            const ctrl = new AbortController();
            const t = setTimeout(() => ctrl.abort(), 2500);
            state.health = await getJson(`${API}/health`, { signal: ctrl.signal });
            clearTimeout(t);
        } catch { state.health = null; }
    }
    try { state.meta = await getJson('./data/meta.json'); } catch { state.meta = null; }
    return { mode: state.mode, health: state.health, meta: state.meta };
}

export const isLive = () => state.mode === 'live';
export const canGenerate = () => Boolean(state.health?.generation_available);
export function liveRunFor(heritageId) {
    const saved = savedLiveRun();
    return saved?.heritageId === heritageId ? saved.runId : null;
}
export function activateLive(heritageId, runId, variants = []) {
    state.mode = 'live';
    if (heritageId && runId) {
        try { localStorage.setItem(LIVE_RUN_KEY, JSON.stringify({ heritageId, runId })); } catch {}
    }
    state.cache.delete('live:passports');
    const designs = variants.filter((variant) => variant.status === 'completed' && variant.image_url)
        .map((variant) => ({
            passport_id: variant.passport_id,
            run_id: variant.run_id,
            heritage_id: heritageId,
            thumb: variant.image_url,
            final_path: variant.image_url,
            latest_path: variant.image_url,
        }));
    state.latestResult = designs.length ? { heritageId, runId, designs } : null;
    state.preloads = typeof Image === 'undefined' ? [] : designs.map((design) => {
        const image = new Image();
        image.src = `${API}${design.thumb}`;
        return image;
    });
}
export function liveDesignsFor(heritageId) {
    return state.latestResult?.heritageId === heritageId &&
        state.latestResult.runId === liveRunFor(heritageId) ? state.latestResult.designs : null;
}
export function invalidate(prefix = '') { for (const k of [...state.cache.keys()]) if (k.startsWith(prefix)) state.cache.delete(k); }

// Ảnh: demo dùng bản WebP đã xuất; live lấy tệp gốc qua API (đã kiểm đường dẫn)
export function media(artifactOrPath, display) {
    if (state.mode === 'live' && artifactOrPath) {
        const path = typeof artifactOrPath === 'string' ? artifactOrPath : artifactOrPath.path;
        if (typeof path === 'string' && path.startsWith('/media/run/')) return `${API}${path}`;
        return `${API}/media/artifact?path=${encodeURIComponent(path)}`;
    }
    if (display) return `./${display}`;
    if (artifactOrPath && typeof artifactOrPath === 'object' && artifactOrPath.display) return `./${artifactOrPath.display}`;
    return '';
}

// Tên hiện vật hiển thị cho người xem: bỏ mã bộ dữ liệu ở cuối (" (LR3D-CULT2 #61)") và tiền tố lặp lại
// "Hiện vật men lam: ", rồi viết hoa chữ đầu. Ví dụ "Hiện vật men lam: rồng và mây (LR3D-CULT2 #61)" thành "Rồng và mây".
const plainName = (name) => {
    const n = (name || '').replace(/\s*\(LR3D-CULT2 #\d+\)\s*$/, '').replace(/^Hiện vật men lam:\s*/i, '');
    return n.charAt(0).toUpperCase() + n.slice(1);
};
const plain = (h) => ({ ...h, items: h.items.map((it) => ({ ...it, name: plainName(it.name) })) });

export async function heritage() {
    const demo = await cached('demo:heritage', () => getJson('./data/heritage.json'));
    if (state.mode !== 'live') return plain(demo);
    try { return plain(await cached('live:heritage', async () => {
        const items = await getJson(`${API}/heritage?include_retired=true`);
        const byId = Object.fromEntries(demo.items.map((x) => [x.id, x]));
        return {
            selection_criteria: demo.selection_criteria,
            items: items.map((it) => ({ ...byId[it.id], ...it, image: `${API}${it.image}`,
                selection: byId[it.id]?.selection, rights: byId[it.id]?.rights })),
        };
    })); } catch { return plain(demo); }
}

export async function passports() {
    if (state.mode === 'live') {
        try { return await cached('live:passports', () => getJson(`${API}/passports`)); }
        catch { state.mode = 'demo'; }
    }
    return cached('demo:passports', () => getJson('./data/passports.json'));
}

export async function startGeneration(heritageId, seed) {
    const payload = seed == null ? { heritage_id: heritageId } : { heritage_id: heritageId, seed };
    return getJson(`${API}/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
}
export const jobStatus = (jobId, heritageId) =>
    getJson(`${API}/generate/${encodeURIComponent(jobId)}?heritage_id=${encodeURIComponent(heritageId)}`);

export function audit(event, extra = {}) {
    if (state.mode !== 'live') return;
    fetch(`${API}/audit`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, keepalive: true,
        body: JSON.stringify({ step: extra.step || 1, event, ...extra }),
    }).catch(() => {});
}
