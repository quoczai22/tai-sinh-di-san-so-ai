// core/data.js — LỚP DỮ LIỆU duy nhất của giao diện (mọi view/component lấy dữ liệu qua đây, không tự fetch).
// Vào: window.DH_API_BASE (config.js). Ra: heritage(), passports(), media(), startGeneration()/jobStatus(), audit().
// Vị trí trong pipeline GUI: bước 0 (init chọn chế độ) → cấp dữ liệu cho views/* và components/hero/*.
// Lớp dữ liệu hai chế độ:
//  · live — gọi API FastAPI (sinh ảnh thật trên GPU, ghi phiếu thẩm định, chỉnh sửa)
//  · demo — đọc ./data/*.json do scripts/demo/export_demo_data.py xuất từ dữ liệu THẬT
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

// Danh sách các bộ thiết kế đã tạo trên trình duyệt này (trang #/mine). Chỉ lưu mã hiện vật, mã lượt chạy và giờ tạo;
// ảnh và Passport vẫn nằm trên máy chủ. Tối đa MY_RUNS_MAX bộ, bộ mới nhất đứng đầu.
const MY_RUNS_KEY = 'dh:my-runs';
const MY_RUNS_MAX = 12;

export function myRuns() {
    try {
        const list = JSON.parse(localStorage.getItem(MY_RUNS_KEY) || '[]');
        return Array.isArray(list) ? list.filter((r) => r?.heritageId && r?.runId) : [];
    } catch { return []; }
}
function saveRuns(list) {
    try { localStorage.setItem(MY_RUNS_KEY, JSON.stringify(list.slice(0, MY_RUNS_MAX))); } catch { /* trình duyệt chặn lưu: bỏ qua */ }
}
function rememberRun(heritageId, runId) {
    saveRuns([{ heritageId, runId, createdAt: new Date().toISOString() }, ...myRuns().filter((r) => r.runId !== runId)]);
}
export function forgetRun(runId) { saveRuns(myRuns().filter((r) => r.runId !== runId)); }

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
    // Chế độ trực tiếp khi mở thẳng: trang Kết quả vừa tạo, hoặc trang cần dữ liệu máy chủ (#/mine, #/edit/..., #/result/<mã>/<lượt chạy>)
    const needsServer = /^#\/(mine|edit)(\/|$)/.test(location.hash) || /^#\/result\/[^/]+\/[^/]+/.test(location.hash);
    let resultKey = resultId || '';
    try { resultKey = decodeURIComponent(resultKey); } catch { /* địa chỉ sai định dạng: dùng nguyên văn, không làm sập trang */ }
    state.mode = needsServer || (resultId && resultKey === saved?.heritageId) ? 'live' : 'demo';
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
        rememberRun(heritageId, runId);
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
// Trang cần dữ liệu máy chủ (Thiết kế đã tạo, Chỉnh sửa, Kết quả của một lượt cũ) chuyển sang chế độ trực tiếp.
// Nếu máy chủ không trả lời, trang live báo lỗi; không thay ảnh của lượt sinh bằng ảnh mẫu.
export function enterLive() { if (API) state.mode = 'live'; }
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
        return cached('live:passports', () => getJson(`${API}/passports`));
    }
    return cached('demo:passports', () => getJson('./data/passports.json'));
}

// Danh sách thiết kế cho trang Kết quả. Chế độ trình diễn đọc bộ riêng ./data/result/passports.json (xuất bằng
// scripts/demo/export_demo_data.py --only-result); trang chủ, Thư viện và Studio vẫn dùng passports() như cũ.
export async function resultPassports() {
    if (state.mode === 'live') {
        return passports();
    }
    return cached('demo:result-passports', () => getJson('./data/result/passports.json'));
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

// Gửi bản chỉnh sửa của một thiết kế (POST /passports/<mã>/edits qua gateway). Trả về kết quả của API (mã sửa, quyết định G3, trạng thái duyệt).
// Sau khi lưu thành công, bỏ danh sách Passport đã nhớ để trang Kết quả hiện dấu "Có bản chỉnh sửa".
export async function submitEdit(passportId, payload) {
    const result = await getJson(`${API}/passports/${encodeURIComponent(passportId)}/edits`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    state.cache.delete('live:passports');
    state.latestResult = null;               // ảnh chụp bộ vừa sinh không có số bản sửa; bỏ để trang Kết quả đọc lại danh sách mới
    return result;
}

export function audit(event, extra = {}) {
    if (state.mode !== 'live') return;
    fetch(`${API}/audit`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, keepalive: true,
        body: JSON.stringify({ step: extra.step || 1, event, ...extra }),
    }).catch(() => {});
}
