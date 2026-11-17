import { setDynamicImage, scrollToElement } from '../core/dom.js';
import { updateStepper } from './stepper.js';

let currentPassportData = null;

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

export function openDesignPassport(item, variant) {
    const modal = document.getElementById('passport-modal');
    if (!modal) return;

    setDynamicImage(document.getElementById('passport-aodai-img'), variant.img);
    setDynamicImage(document.getElementById('passport-origin-thumb'), item.image);
    setText('passport-origin-name', item.name);

    const score = Number(variant.similarity_pattern_vs_ceramic ?? variant.similarityScore ?? 0);
    const clipDisplay =
        Number.isFinite(score) && score > 0
            ? `Điểm CLIP ${score.toFixed(2)} (tham khảo · gốc: ${score.toFixed(4)})`
            : 'Điểm CLIP — (tham khảo)';
    setText('passport-similarity-val', clipDisplay);

    const modeBadge = document.getElementById('passport-mode-badge');
    if (modeBadge) {
        if (variant.backend === 'demo') {
            modeBadge.textContent = 'Kết quả đã sinh sẵn — không phải sinh trực tiếp';
            modeBadge.className = 'passport-mode-badge is-demo';
        } else if (variant.backend === 'hf') {
            modeBadge.textContent = 'Sinh trực tiếp trên máy dự phòng (HF Space GPU)';
            modeBadge.className = 'passport-mode-badge is-backup';
        } else {
            modeBadge.textContent = 'Sinh trực tiếp trên GPU chính (Modal)';
            modeBadge.className = 'passport-mode-badge is-live';
        }
    }

    setText('passport-variant-title', variant.name || `Biến thể ${variant.variant_index || 1}`);
    setText(
        'passport-layout',
        `${variant.layout_label || variant.layout || '—'} (${variant.layout || 'auto'})`
    );
    setText(
        'passport-intensity',
        `Mức ${variant.intensity_level ?? '—'}${variant.level_name ? ` (${variant.level_name})` : ''} · ControlNet weight: ${variant.controlnet_weight ?? '—'}`
    );
    setText(
        'passport-palette',
        `${variant.palette_mode === 'original' ? 'Giữ bảng màu gốc (original)' : 'Tự do (free)'}${variant.source_palette ? ` · ${variant.source_palette}` : ''}`
    );
    setText(
        'passport-seed-polish',
        `Seed: ${variant.seed ?? 42} · Polish strength: ${variant.polish_strength ?? 0.4}`
    );
    setText(
        'passport-models',
        `SD: ${variant.sd_model_id || '—'} · ControlNet: ${variant.controlnet_id || '—'}`
    );
    setText(
        'passport-runtime',
        `PyTorch ${variant.torch_version || '—'} · Diffusers ${variant.diffusers_version || '—'} · GPU: ${variant.gpu || '—'} · Thời gian: ${variant.duration_s ?? '—'}s`
    );
    setText('passport-sha256', variant.sha256_design || '—');
    setText('passport-pos-prompt', variant.positive_prompt || '—');
    setText('passport-neg-prompt', variant.negative_prompt || '—');

    currentPassportData = {
        schema_version: '1.1-phase1',
        exported_at: new Date().toISOString(),
        mode:
            variant.backend === 'demo'
                ? 'Kết quả đã sinh sẵn — không phải sinh trực tiếp'
                : 'Sinh trực tiếp trên GPU',
        backend: variant.backend || 'demo',
        heritage_id: item.id,
        heritage_name: item.name,
        variant_index: variant.variant_index ?? 1,
        variant_name: variant.name,
        similarity_pattern_vs_ceramic: score,
        seed: variant.seed ?? 42,
        intensity_level: variant.intensity_level,
        level_name: variant.level_name,
        controlnet_weight: variant.controlnet_weight,
        palette_mode: variant.palette_mode,
        source_palette: variant.source_palette,
        layout: variant.layout,
        layout_label: variant.layout_label || variant.layout,
        polish_strength: variant.polish_strength ?? 0.4,
        positive_prompt: variant.positive_prompt,
        negative_prompt: variant.negative_prompt,
        sha256_design: variant.sha256_design,
        sd_model_id: variant.sd_model_id,
        controlnet_id: variant.controlnet_id,
        torch_version: variant.torch_version,
        diffusers_version: variant.diffusers_version,
        gpu: variant.gpu,
        duration_s: variant.duration_s,
        image_url: variant.img,
    };

    modal.classList.add('active');
}

export function initPassportModal() {
    const modal = document.getElementById('passport-modal');
    const close = () => modal?.classList.remove('active');
    document.getElementById('passport-close-btn')?.addEventListener('click', close);
    modal?.addEventListener('click', (event) => {
        if (event.target === modal) close();
    });
    document.getElementById('btn-reset-studio')?.addEventListener('click', () => {
        close();
        updateStepper(1);
        scrollToElement(document.getElementById('hien-vat'));
    });
    document.getElementById('btn-export-passport')?.addEventListener('click', () => {
        if (!currentPassportData) return;
        const jsonString = JSON.stringify(currentPassportData, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        const hid = currentPassportData.heritage_id || 'heritage';
        const vIdx = currentPassportData.variant_index || 1;
        link.href = url;
        link.download = `${hid}_V${vIdx}_passport.json`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
}
