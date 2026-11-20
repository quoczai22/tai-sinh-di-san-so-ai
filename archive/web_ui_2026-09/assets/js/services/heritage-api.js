import { API_BASE_URL } from '../core/config.js';

const isVercelGateway = API_BASE_URL === '/api' || API_BASE_URL.endsWith('/api');

const publicUrl = (url) => {
    if (!url) return url;
    if (url.startsWith('/api/') || url.startsWith('./') || url.startsWith('http://') || url.startsWith('https://')) {
        return url;
    }
    if (url.startsWith('/')) {
        return `${API_BASE_URL}${url}`;
    }
    return url;
};

let demoDataPromise = null;
export async function loadDemoDataJson() {
    if (!demoDataPromise) {
        demoDataPromise = fetch('./assets/data/demo_variants.json')
            .then((res) => {
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                return res.json();
            })
            .catch((err) => {
                demoDataPromise = null;
                throw err;
            });
    }
    return demoDataPromise;
}

export async function fetchDemoVariants(heritageId) {
    const data = await loadDemoDataJson();
    return data?.items?.[heritageId] || [];
}

export function warmupBackend() {
    const url = isVercelGateway ? `${API_BASE_URL}/warmup` : `${API_BASE_URL}/health`;
    void fetch(url, { method: 'GET' }).catch(() => {});
}

export async function fetchHeritageItems() {
    try {
        const response = await fetch(`${API_BASE_URL}/heritage`);
        if (response.ok) {
            return (await response.json()).map((item) => ({ ...item, image: publicUrl(item.image) }));
        }
    } catch (_) {
        // Fallback sang dữ liệu tĩnh khi cổng hoặc backend local không bật
    }
    const fallbackRes = await fetch('./assets/data/heritage_items.json');
    if (!fallbackRes.ok) throw new Error(`Heritage catalog ${fallbackRes.status}`);
    return fallbackRes.json();
}

export async function createGenerationJob(heritageId) {
    try {
        const response = await fetch(`${API_BASE_URL}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ heritage_id: heritageId }),
        });
        if (response.ok) {
            return await response.json();
        }
    } catch (_) {
        // Chuyển sang chế độ Demo khi không kết nối được cổng API
    }
    const variants = await fetchDemoVariants(heritageId);
    return {
        job_id: `demo_${heritageId}_${Date.now()}`,
        heritage_id: heritageId,
        backend: 'demo',
        status: 'completed',
        progress: 100,
        queue_position: 0,
        failover: true,
        demo_label: 'Kết quả đã sinh sẵn — không phải sinh trực tiếp',
        label: 'Kết quả đã sinh sẵn — không phải sinh trực tiếp',
        variants,
    };
}

export async function fetchGenerationJob(jobId, backend = 'modal', heritageId = '') {
    const url = isVercelGateway
        ? `${API_BASE_URL}/status?job_id=${encodeURIComponent(jobId)}&backend=${encodeURIComponent(backend)}&heritage_id=${encodeURIComponent(heritageId)}`
        : `${API_BASE_URL}/generate/${encodeURIComponent(jobId)}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Job API ${response.status}`);
    return response.json();
}

export function recordAudit(event) {
    void fetch(`${API_BASE_URL}/audit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(event),
        keepalive: true,
    }).catch(() => {});
}

export const publicVariantUrl = publicUrl;
