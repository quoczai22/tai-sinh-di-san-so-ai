import { setPipelineProgress } from '../core/dom.js';
import { getSelectedHeritageItem } from '../core/state.js';
import { createGenerationJob, fetchDemoVariants, fetchGenerationJob, recordAudit } from '../services/heritage-api.js';
import { renderCurateSection } from './curate.js';
import { updateStepper } from './stepper.js';

// Giới hạn thời gian chờ một lần sinh (gồm cả lúc máy dự phòng thức dậy).
// Quá mức này thì dừng hỏi trạng thái và chuyển sang kết quả đã sinh sẵn.
const MAX_WAIT_MS = 8 * 60 * 1000;

function pipelineUi() {
    return {
        modal: document.getElementById('pipeline-modal'),
        progress: document.getElementById('pipeline-progress-bar'),
        percent: document.getElementById('pipeline-percentage'),
        status: document.getElementById('pipeline-status-text'),
        footer: document.getElementById('pipeline-modal-footer'),
        stages: [1, 2, 3, 4].map((number) => document.getElementById(`stage-card-${number}`)),
    };
}

function updatePipeline(ui, progress) {
    const stage = Math.min(4, Math.max(1, Math.ceil(progress / 25)));
    ui.stages.forEach((card, index) => {
        card?.classList.toggle('done', index < stage - 1);
        card?.classList.toggle('running', index === stage - 1);
    });
    setPipelineProgress(ui.progress, progress);
    if (ui.percent) ui.percent.textContent = `${progress}%`;
}

function formatStatusLabel(state, backend) {
    if (state.warming) {
        return 'Đang khởi động máy dự phòng (2–3 phút)…';
    }
    const queuePos = Number(state.queue_position || 0);
    const prefix = backend === 'hf' ? '[Máy dự phòng HF Space] ' : '';
    const gpuTag = state.gpu ? ` (${state.gpu})` : '';
    if (state.status === 'queued' && queuePos > 0) {
        return `${prefix}Đang xếp hàng chờ GPU — Vị trí trong hàng đợi: #${queuePos}${gpuTag}`;
    }
    return `${prefix}${state.label || 'Đang xử lý...'}${gpuTag}`;
}

export async function runVisualPipeline(item) {
    if (!item) return;
    updateStepper(3);
    const ui = pipelineUi();
    if (ui.footer) ui.footer.style.display = 'none';
    ui.stages.forEach((card) => card?.classList.remove('running', 'done'));
    updatePipeline(ui, 0);
    if (ui.status) ui.status.textContent = 'Đang gửi hiện vật tới cổng điều phối GPU...';
    ui.modal?.classList.add('active');

    const startTime = Date.now();
    try {
        const initial = await createGenerationJob(item.id);
        let currentJobId = initial.job_id;
        let currentBackend = initial.backend || 'modal';
        let didFailover = Boolean(initial.failover || currentBackend !== 'modal');

        // Nếu cổng trả về ngay kết quả Demo (do cả 2 backend tắt hoặc vượt rate limit)
        if (currentBackend === 'demo' || initial.status === 'completed') {
            const variants =
                Array.isArray(initial.variants) && initial.variants.length === 4
                    ? initial.variants
                    : await fetchDemoVariants(item.id);
            item.generatedVariants = variants;
            item.generationBackend = currentBackend;
            item.rateLimitMessage = initial.rate_limited ? initial.message : '';

            updatePipeline(ui, 100);
            ui.stages.forEach((card) => {
                card?.classList.remove('running');
                card?.classList.add('done');
            });
            if (ui.status) {
                ui.status.textContent =
                    currentBackend === 'demo'
                        ? (initial.rate_limited ? initial.message : (initial.message || initial.label || 'GPU đang bận hoặc tạm ngừng — hiển thị kết quả đã sinh sẵn.'))
                        : 'Thiết kế đã sẵn sàng để bạn chiêm ngưỡng.';
            }
            if (ui.footer) ui.footer.style.display = 'flex';
            recordAudit({
                step: 3,
                event: 'generation_resolved',
                heritage_id: item.id,
                backend: currentBackend,
                wait_ms: Date.now() - startTime,
                failover: didFailover,
            });
            await renderCurateSection(item, false);
            return;
        }

        if (ui.status) {
            ui.status.textContent = formatStatusLabel(initial, currentBackend);
        }

        let result = initial;
        while (!result || ['queued', 'running'].includes(result.status) || result.warming) {
            if (Date.now() - startTime > MAX_WAIT_MS) {
                throw new Error('Quá thời gian chờ GPU');
            }
            await new Promise((resolve) => setTimeout(resolve, 1200));
            result = await fetchGenerationJob(currentJobId, currentBackend, item.id);
            if (result.job_id && result.job_id !== currentJobId) {
                currentJobId = result.job_id;
            }
            if (result.backend && result.backend !== currentBackend) {
                currentBackend = result.backend;
                didFailover = true;
            }
            updatePipeline(ui, Number(result.progress || (result.warming ? 5 : 0)));
            if (ui.status) {
                ui.status.textContent = formatStatusLabel(result, currentBackend);
            }
            if (result.backend === 'demo' || result.status === 'completed' || result.status === 'failed') {
                break;
            }
        }

        if (result.status !== 'completed') {
            throw new Error(result.label || 'Pipeline thất bại');
        }

        ui.stages.forEach((card) => {
            card?.classList.remove('running');
            card?.classList.add('done');
        });
        item.generatedVariants =
            Array.isArray(result.variants) && result.variants.length === 4
                ? result.variants
                : await fetchDemoVariants(item.id);
        item.generationBackend = result.backend || currentBackend;
        item.rateLimitMessage = '';

        const gpuInfo = result.gpu || item.generatedVariants?.[0]?.gpu;
        if (ui.status) {
            if (item.generationBackend === 'demo') {
                ui.status.textContent = result.message || result.label || 'GPU đang bận hoặc tạm ngừng — hiển thị kết quả đã sinh sẵn.';
            } else if (item.generationBackend === 'hf') {
                ui.status.textContent = `Đã tạo xong trên máy dự phòng${gpuInfo ? ` (${gpuInfo})` : ''}.`;
            } else {
                ui.status.textContent = `Thiết kế đã sẵn sàng${gpuInfo ? ` (${gpuInfo})` : ''}.`;
            }
        }
        if (ui.footer) ui.footer.style.display = 'flex';
        recordAudit({
            step: 3,
            event: 'generation_resolved',
            heritage_id: item.id,
            backend: item.generationBackend,
            wait_ms: Date.now() - startTime,
            failover: didFailover,
        });
        await renderCurateSection(item, false);
    } catch (error) {
        // Fallback an toàn cuối cùng sang Demo mode nếu mất mạng giữa chừng
        try {
            const demoVariants = await fetchDemoVariants(item.id);
            item.generatedVariants = demoVariants;
            item.generationBackend = 'demo';
            updatePipeline(ui, 100);
            ui.stages.forEach((card) => {
                card?.classList.remove('running');
                card?.classList.add('done');
            });
            if (ui.status) {
                ui.status.textContent = 'GPU đang bận hoặc tạm ngừng — hiển thị kết quả đã sinh sẵn.';
            }
            if (ui.footer) ui.footer.style.display = 'flex';
            recordAudit({
                step: 3,
                event: 'generation_fallback_demo',
                heritage_id: item.id,
                backend: 'demo',
                wait_ms: Date.now() - startTime,
                failover: true,
            });
            await renderCurateSection(item, false);
        } catch (fallbackErr) {
            if (ui.status) ui.status.textContent = `Không thể tạo thiết kế: ${error.message}`;
            console.error('Pipeline API error:', error, fallbackErr);
        }
    }
}

export function initPipelineControls() {
    const modal = document.getElementById('pipeline-modal');
    document.getElementById('pipeline-close-btn')?.addEventListener('click', () => modal?.classList.remove('active'));
    document.getElementById('btn-stay-inspector')?.addEventListener('click', () => modal?.classList.remove('active'));
    document.getElementById('btn-modal-goto-curate')?.addEventListener('click', () => {
        modal?.classList.remove('active');
        const item = getSelectedHeritageItem();
        if (item) void renderCurateSection(item, true);
    });
}
