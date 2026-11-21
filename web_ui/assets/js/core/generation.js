// core/generation.js — VÒNG SINH THIẾT KẾ phía giao diện (chỉ chạy khi có máy chủ GPU, data.canGenerate()).
// Gửi POST /generate rồi hỏi trạng thái mỗi 1,2 giây tới khi xong; báo tiến độ qua onProgress(0..100).
// Vị trí trong pipeline GUI: Studio (bấm Tạo thiết kế) → generation.js → API → trang Kết quả.
import * as data from './data.js';

export async function runGeneration(heritageId, seed, onProgress = () => {}) {
    data.audit('generation_requested', { step: 3, heritage_id: heritageId });
    const { job_id: jobId } = await data.startGeneration(heritageId, seed);
    let job;
    do {
        await new Promise((r) => setTimeout(r, 1200));
        job = await data.jobStatus(jobId);
        onProgress(job.progress || 0);
    } while (['queued', 'running'].includes(job.status));
    if (job.status !== 'completed') throw new Error(job.label);
    data.invalidate('live:passports');
    return job;
}
