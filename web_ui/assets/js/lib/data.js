// Lớp dữ liệu hai chế độ:
//  · live — gọi API FastAPI (sinh ảnh thật trên GPU, ghi phiếu thẩm định, chỉnh sửa)
//  · demo — đọc ./data/*.json do scripts/11_export_demo_data.py xuất từ dữ liệu THẬT
// Chế độ được xác định một lần khi mở trang bằng /health (chờ tối đa 2,5 giây).

const API = (window.DH_API_BASE || '').replace(/\/$/, '');
const state = { mode: 'demo', health: null, meta: null, cache: new Map() };

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
    if (API) {
        try {
            const ctrl = new AbortController();
            const t = setTimeout(() => ctrl.abort(), 2500);
            state.health = await getJson(`${API}/health`, { signal: ctrl.signal });
            clearTimeout(t);
            state.mode = 'live';
        } catch { state.mode = 'demo'; }
    }
    try { state.meta = await getJson('./data/meta.json'); } catch { state.meta = null; }
    return { mode: state.mode, health: state.health, meta: state.meta };
}

export const mode = () => state.mode;
export const isLive = () => state.mode === 'live';
export const canGenerate = () => state.mode === 'live' && Boolean(state.health?.generation_available);
export const meta = () => state.meta;
export function invalidate(prefix = '') { for (const k of [...state.cache.keys()]) if (k.startsWith(prefix)) state.cache.delete(k); }

// Ảnh: demo dùng bản WebP đã xuất; live lấy tệp gốc qua API (đã kiểm đường dẫn)
export function media(artifactOrPath, display) {
    if (state.mode === 'live' && artifactOrPath) {
        const path = typeof artifactOrPath === 'string' ? artifactOrPath : artifactOrPath.path;
        return `${API}/media/artifact?path=${encodeURIComponent(path)}`;
    }
    if (display) return `./${display}`;
    if (artifactOrPath && typeof artifactOrPath === 'object' && artifactOrPath.display) return `./${artifactOrPath.display}`;
    return '';
}

// Số liệu tĩnh tại thời điểm xuất dữ liệu (toàn vẹn Passport, thời gian sinh ghi trong variants.csv)
export const dashboardSnapshot = () => cached('demo:dashboard', () => getJson('./data/dashboard.json'));

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
    return plain(await cached('live:heritage', async () => {
        const items = await getJson(`${API}/heritage?include_retired=true`);
        const byId = Object.fromEntries(demo.items.map((x) => [x.id, x]));
        return {
            selection_criteria: demo.selection_criteria,
            items: items.map((it) => ({ ...byId[it.id], ...it, image: `${API}${it.image}`,
                selection: byId[it.id]?.selection, rights: byId[it.id]?.rights })),
        };
    }));
}

export async function passports() {
    if (state.mode === 'live') return cached('live:passports', () => getJson(`${API}/passports`));
    return cached('demo:passports', () => getJson('./data/passports.json'));
}

// Danh sách thiết kế cho trang Kết quả. Chế độ trình diễn đọc bộ riêng ./data/result/passports.json (xuất bằng
// scripts/11_export_demo_data.py --only-result); trang chủ, Thư viện và Studio vẫn dùng passports() như cũ.
export async function resultPassports() {
    if (state.mode === 'live') return passports();
    return cached('demo:result-passports', () => getJson('./data/result/passports.json'));
}

export async function passport(id) {
    if (!/^DP-[A-Z0-9]{2,8}-[0-9T]{8,15}-V[0-9]{1,2}$/.test(id)) throw new Error('Mã Passport không hợp lệ.');
    if (state.mode === 'live') return getJson(`${API}/passports/${id}`);
    return cached(`demo:passport:${id}`, () => getJson(`./data/passports/${id}.json`));
}

export const quality = () => cached('demo:quality', () => getJson('./data/quality.json'));
export const experiments = () => (state.mode === 'live'
    ? cached('live:exp', async () => {
        const [live, demo] = await Promise.all([getJson(`${API}/experiments`), getJson('./data/experiments.json')]);
        const byId = Object.fromEntries(demo.map((e) => [e.id, e]));
        return live.map((e) => ({ ...byId[e.id], ...e }));
    })
    : cached('demo:exp', () => getJson('./data/experiments.json')));

export async function startGeneration(heritageId, seed) {
    return getJson(`${API}/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ heritage_id: heritageId, seed }),
    });
}
export const jobStatus = (jobId) => getJson(`${API}/generate/${jobId}`);

function writeHeaders() {
    const h = { 'Content-Type': 'application/json' };
    const key = sessionStorageSafe('tsds-write-key');
    if (key) h['X-API-Key'] = key;
    return h;
}
function sessionStorageSafe(k) { try { return sessionStorage.getItem(k); } catch { return null; } }

export async function submitReview(pid, review) {
    const out = await getJson(`${API}/passports/${pid}/reviews`, { method: 'POST', headers: writeHeaders(), body: JSON.stringify(review) });
    invalidate('live:passports');
    return out;
}
export async function submitQc(pid, body) {
    const out = await getJson(`${API}/passports/${pid}/qc`, { method: 'POST', headers: writeHeaders(), body: JSON.stringify(body) });
    invalidate('live:passports');
    return out;
}
export async function submitEdit(pid, body) {
    const out = await getJson(`${API}/passports/${pid}/edits`, { method: 'POST', headers: writeHeaders(), body: JSON.stringify(body) });
    invalidate('live:passports');
    return out;
}
export const exportUrl = (pid) => `${API}/passports/${pid}/export`;

export function audit(event, extra = {}) {
    if (state.mode !== 'live') return;
    fetch(`${API}/audit`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, keepalive: true,
        body: JSON.stringify({ step: extra.step || 1, event, ...extra }),
    }).catch(() => {});
}
