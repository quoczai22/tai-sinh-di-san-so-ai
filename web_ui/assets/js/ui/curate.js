import { fetchDemoVariants, publicVariantUrl, recordAudit } from '../services/heritage-api.js';
import { openDesignPassport } from './passport.js';
import { updateStepper } from './stepper.js';

function formatClipScore(rawScore) {
    const num = Number(rawScore);
    if (!Number.isFinite(num) || num <= 0) {
        return 'Điểm CLIP — (tham khảo)';
    }
    return `Điểm CLIP ${num.toFixed(2)} (tham khảo)`;
}

function formatClipBadge(rawScore) {
    const num = Number(rawScore);
    if (!Number.isFinite(num) || num <= 0) {
        return '★ CLIP —';
    }
    return `★ CLIP ${num.toFixed(2)}`;
}

async function resolveVariantsFor(item) {
    let sourceVariants = item.generatedVariants;
    if (!Array.isArray(sourceVariants) || sourceVariants.length === 0) {
        sourceVariants = await fetchDemoVariants(item.id);
        item.generationBackend = 'demo';
    }

    const base = item.variantImageBase || `./assets/images/variants/${item.id}_V`;
    return sourceVariants.map((raw, index) => {
        const vIndex = raw.variant_index || index + 1;
        const levelName = raw.level_name ? ` — ${raw.level_name}` : '';
        const score = Number(raw.similarity_pattern_vs_ceramic || 0);
        const imageUrl =
            item.generationBackend === 'demo'
                ? `./assets/images/variants/${item.id}_V${vIndex}_aodai.png`
                : publicVariantUrl(raw.image_url || `${base}${vIndex}_aodai.png`);

        return {
            ...raw,
            variant_index: vIndex,
            name: `Biến thể ${vIndex}${levelName}`,
            layout: raw.layout_label || raw.layout || 'Tự động theo CLIP',
            similarityScore: score,
            similarityText: formatClipScore(score),
            similarityBadge: formatClipBadge(score),
            img: imageUrl,
            backend: item.generationBackend || raw.backend || 'demo',
        };
    });
}

function updateBackendBanner(item) {
    const banner = document.getElementById('curate-mode-banner');
    if (!banner) return;
    const backend = item.generationBackend || 'demo';
    if (backend === 'demo') {
        banner.style.display = 'inline-flex';
        banner.className = 'curate-mode-banner is-demo';
        const extraMsg = item.rateLimitMessage ? ` (${item.rateLimitMessage})` : '';
        banner.textContent = `⚠ Kết quả đã sinh sẵn — không phải sinh trực tiếp${extraMsg}`;
    } else if (backend === 'hf') {
        banner.style.display = 'inline-flex';
        banner.className = 'curate-mode-banner is-backup';
        banner.textContent = '✦ Sinh trực tiếp từ máy dự phòng (Hugging Face Space GPU)';
    } else {
        banner.style.display = 'inline-flex';
        banner.className = 'curate-mode-banner is-live';
        banner.textContent = '✦ Sinh trực tiếp trên GPU chính (Modal)';
    }
}

function createVariantCard(item, variant) {
    const card = document.createElement('article');
    card.className = 'variant-card';
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', `${variant.name} - ${variant.similarityText}`);
    card.dataset.clipExact = Number(variant.similarityScore || 0).toFixed(4);
    card.innerHTML = `
        <div class="variant-img-wrap">
            <img class="variant-img" src="${variant.img}" alt="${variant.name}" loading="lazy" decoding="async">
            <span class="similarity-badge" title="Cosine CLIP chính xác: ${Number(variant.similarityScore || 0).toFixed(4)}">${variant.similarityBadge}</span>
        </div>
        <div class="variant-layer" aria-hidden="true"></div>
        <div class="variant-info">
            <span class="variant-tagline">${variant.similarityText} · ${variant.layout}</span>
            <h4 class="variant-name">${variant.name}</h4>
            <button class="variant-btn-select" type="button" aria-label="Xem thiết kế ${variant.name}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                    <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                    <polyline points="2 17 12 22 22 17"></polyline>
                    <polyline points="2 12 12 17 22 12"></polyline>
                </svg>
                <span>Xem thiết kế & Passport →</span>
            </button>
        </div>`;
    const select = () => {
        document.querySelectorAll('.variant-card').forEach((element) => element.classList.remove('selected'));
        card.classList.add('selected');
        openDesignPassport(item, variant);
        recordAudit({
            step: 4,
            event: 'design_viewed',
            heritage_id: item.id,
            variant_name: variant.name,
            backend: variant.backend,
        });
    };
    card.addEventListener('click', select);
    card.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            select();
        }
    });
    return card;
}

export async function renderCurateSection(item, shouldScroll = true) {
    if (!item) return;
    if (shouldScroll) updateStepper(4);
    const section = document.getElementById('curate-section');
    const title = document.getElementById('curate-title');
    const grid = document.getElementById('variants-grid');
    if (!section || !title || !grid) return;

    title.textContent = `Bộ sưu tập áo dài: ${item.name}`;
    updateBackendBanner(item);

    const variants = await resolveVariantsFor(item);
    grid.replaceChildren(...variants.map((variant) => createVariantCard(item, variant)));

    document.getElementById('dragon-wave-bridge')?.style.setProperty('display', 'block');
    const footerBridge = document.getElementById('curate-to-footer-bridge');
    footerBridge?.classList.add('is-visible');
    if (footerBridge) footerBridge.style.display = 'block';
    section.style.display = 'block';
    if (shouldScroll) section.scrollIntoView({ behavior: 'smooth' });
}
