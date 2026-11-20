// core/generation.js — VÒNG SINH THIẾT KẾ phía giao diện (chỉ chạy khi có máy chủ GPU, data.canGenerate()).
// Gửi POST /generate rồi hỏi trạng thái mỗi 1,2 giây tới khi xong; báo tiến độ qua onProgress(0..100).
// Vị trí trong pipeline GUI: Studio (bấm Tạo thiết kế) → generation.js → API → trang Kết quả.
import * as data from './data.js';

const MAX_WAIT_MS = 8 * 60 * 1000;

function beforeDeadline(promise, deadline) {
    const remaining = deadline - Date.now();
    if (remaining <= 0) return Promise.reject(new Error('Quá 8 phút chờ tạo thiết kế. Vui lòng thử lại.'));
    let timer;
    return Promise.race([
        promise,
        new Promise((_, reject) => {
            timer = setTimeout(() => reject(new Error('Quá 8 phút chờ tạo thiết kế. Vui lòng thử lại.')), remaining);
        }),
    ]).finally(() => clearTimeout(timer));
}

export async function runGeneration(heritageId, seed, onProgress = () => {}) {
    const deadline = Date.now() + MAX_WAIT_MS;
    data.audit('generation_requested', { step: 3, heritage_id: heritageId });
    const started = await beforeDeadline(data.startGeneration(heritageId, seed), deadline);
    if (started.backend === 'demo') return started;
    const jobId = started.job_id;
    let job;
    do {
        await beforeDeadline(new Promise((r) => setTimeout(r, 1200)), deadline);
        job = await beforeDeadline(data.jobStatus(jobId, heritageId), deadline);
        onProgress(job.progress || 0);
    } while (['queued', 'running'].includes(job.status));
    if (job.status !== 'completed') throw new Error(job.label);
    if (job.backend !== 'demo') {
        data.activateLive();
        data.invalidate('live:passports');
    }
    return job;
}
