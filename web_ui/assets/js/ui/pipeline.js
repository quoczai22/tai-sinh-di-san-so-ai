import { setPipelineProgress } from '../core/dom.js';
import { getSelectedHeritageItem } from '../core/state.js';
import { createGenerationJob, fetchGenerationJob } from '../services/heritage-api.js';
import { renderCurateSection } from './curate.js';
import { updateStepper } from './stepper.js';

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

export async function runVisualPipeline(item) {
    if (!item) return;
    updateStepper(3);
    const ui = pipelineUi();
    if (ui.footer) ui.footer.style.display = 'none';
    ui.stages.forEach((card) => card?.classList.remove('running', 'done'));
    updatePipeline(ui, 0);
    if (ui.status) ui.status.textContent = 'Đang gửi hiện vật tới pipeline RTX 4050...';
    ui.modal?.classList.add('active');
    try {
        const { job_id: jobId } = await createGenerationJob(item.id);
        let result;
        while (!result || ['queued', 'running'].includes(result.status)) {
            await new Promise((resolve) => setTimeout(resolve, 1000));
            result = await fetchGenerationJob(jobId);
            updatePipeline(ui, Number(result.progress || 0));
            if (ui.status) ui.status.textContent = result.label || 'Đang xử lý...';
        }
        if (result.status !== 'completed') throw new Error(result.label || 'Pipeline thất bại');
        ui.stages.forEach((card) => {
            card?.classList.remove('running');
            card?.classList.add('done');
        });
        item.generatedVariants = result.variants;
        if (ui.status) ui.status.textContent = 'Thiết kế đã sẵn sàng để bạn chiêm ngưỡng.';
        if (ui.footer) ui.footer.style.display = 'flex';
        renderCurateSection(item, false);
    } catch (error) {
        if (ui.status) ui.status.textContent = `Không thể tạo thiết kế: ${error.message}`;
        console.error('Pipeline API error:', error);
    }
}

export function initPipelineControls() {
    const modal = document.getElementById('pipeline-modal');
    document.getElementById('pipeline-close-btn')?.addEventListener('click', () => modal?.classList.remove('active'));
    document.getElementById('btn-stay-inspector')?.addEventListener('click', () => modal?.classList.remove('active'));
    document.getElementById('btn-modal-goto-curate')?.addEventListener('click', () => {
        modal?.classList.remove('active');
        const item = getSelectedHeritageItem();
        if (item) renderCurateSection(item, true);
    });
}
