import { API_BASE_URL } from '../core/config.js';

const publicUrl = (url) => url?.startsWith('/') ? `${API_BASE_URL}${url}` : url;

export async function fetchHeritageItems() {
    const response = await fetch(`${API_BASE_URL}/heritage`);
    if (!response.ok) throw new Error(`API ${response.status}`);
    return (await response.json()).map((item) => ({ ...item, image: publicUrl(item.image) }));
}

export async function createGenerationJob(heritageId) {
    const response = await fetch(`${API_BASE_URL}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ heritage_id: heritageId }),
    });
    if (!response.ok) throw new Error(`API ${response.status}`);
    return response.json();
}

export async function fetchGenerationJob(jobId) {
    const response = await fetch(`${API_BASE_URL}/generate/${jobId}`);
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
