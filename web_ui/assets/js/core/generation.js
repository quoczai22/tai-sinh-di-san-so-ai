// core/generation.js — VÒNG SINH THIẾT KẾ phía giao diện (chỉ chạy khi có máy chủ GPU, data.canGenerate()).
// Gửi POST /generate rồi hỏi trạng thái mỗi 1,2 giây tới khi xong; báo tiến độ qua onProgress(0..100).
// Vị trí trong pipeline GUI: Studio (bấm Tạo thiết kế) → generation.js → API → trang Kết quả.
import * as data from './data.js';

const MAX_WAIT_MS = 8 * 60 * 1000;
const PENDING_KEY = 'dh:pending-generation';

function pendingJob(heritageId) {
    try {
        const saved = JSON.parse(sessionStorage.getItem(PENDING_KEY) || 'null');
        if (saved?.heritageId === heritageId && Date.now() - saved.startedAt < MAX_WAIT_MS) return saved.jobId;
        sessionStorage.removeItem(PENDING_KEY);
    } catch {}
    return null;
}

function rememberJob(heritageId, jobId) {
    try { sessionStorage.setItem(PENDING_KEY, JSON.stringify({ heritageId, jobId, startedAt: Date.now() })); }
    catch {}
}

function forgetJob() {
    try { sessionStorage.removeItem(PENDING_KEY); } catch {}
}

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
    let jobId = pendingJob(heritageId);
    if (jobId) {
        try { await beforeDeadline(data.jobStatus(jobId, heritageId), deadline); }
        catch (error) {
            if (error.status !== 404) throw error;
            forgetJob();
            jobId = null;
        }
    }
    if (!jobId) {
        data.audit('generation_requested', { step: 3, heritage_id: heritageId });
        const started = await beforeDeadline(data.startGeneration(heritageId, seed), deadline);
        if (started.backend === 'demo') return started;
        jobId = started.job_id;
        rememberJob(heritageId, jobId);
    }
    let misses = 0;
    while (true) {
        await beforeDeadline(new Promise((r) => setTimeout(r, 1200)), deadline);
        let job;
        try { job = await beforeDeadline(data.jobStatus(jobId, heritageId), deadline); }
        catch (error) {
            if (error.status === 404) forgetJob();
            if (error.status !== 404 && ++misses < 10) continue;
            throw error;
        }
        if (job.backend === 'demo') {
            if (++misses < 10) continue;
            return job;
        }
        misses = 0;
        onProgress(job.progress || 0);
        if (['queued', 'running'].includes(job.status)) continue;
        forgetJob();
        if (job.status !== 'completed') throw new Error(job.label);
        data.activateLive();
        data.invalidate('live:passports');
        return job;
    }
}
