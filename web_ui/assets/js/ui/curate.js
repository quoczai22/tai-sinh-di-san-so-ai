import { publicVariantUrl, recordAudit } from '../services/heritage-api.js';
import { openDesignPassport } from './passport.js';
import { updateStepper } from './stepper.js';

function variantsFor(item) {
    const base = item.variantImageBase || `./assets/images/variants/${item.id}_V`;
    const specs = [
        ['Biến thể 1', 'Thân trước', '88.4%'],
        ['Biến thể 2', 'Phủ toàn thân', '76.2%'],
        ['Biến thể 3', 'Băng gấu tà', '68.5%'],
        ['Biến thể 4', 'Vai và ngực', '54.1%'],
    ];
    const variants = specs.map(([name, layout, similarity], index) => ({
        name, layout, similarity, img: `${base}${index + 1}_aodai.png`,
    }));
    if (item.generatedVariants?.length === 4) {
        item.generatedVariants.forEach((generated, index) => {
            variants[index].img = publicVariantUrl(generated.image_url);
            variants[index].similarity = `${(Number(generated.similarity_pattern_vs_ceramic || 0) * 100).toFixed(1)}%`;
            variants[index].layout = generated.layout_label || variants[index].layout;
        });
    }
    return variants;
}

function createVariantCard(item, variant) {
    const card = document.createElement('article');
    card.className = 'variant-card';
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', `${variant.name} - ${variant.similarity} tương đồng`);
    card.innerHTML = `
        <div class="variant-img-wrap">
            <img class="variant-img" src="${variant.img}" alt="${variant.name}" loading="lazy" decoding="async">
            <span class="similarity-badge">★ ${variant.similarity}</span>
        </div>
        <div class="variant-layer" aria-hidden="true"></div>
        <div class="variant-info">
            <span class="variant-tagline">ĐỘ TƯƠNG ĐỒNG THAM KHẢO · ${variant.similarity}</span>
            <h4 class="variant-name">${variant.name}</h4>
            <button class="variant-btn-select" type="button" aria-label="Xem thiết kế ${variant.name}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                    <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                    <polyline points="2 17 12 22 22 17"></polyline>
                    <polyline points="2 12 12 17 22 12"></polyline>
                </svg>
                <span>Xem thiết kế →</span>
            </button>
        </div>`;
    const select = () => {
        document.querySelectorAll('.variant-card').forEach((element) => element.classList.remove('selected'));
        card.classList.add('selected');
        openDesignPassport(item, variant);
        recordAudit({ step: 4, event: 'design_viewed', heritage_id: item.id, variant_name: variant.name });
    };
    card.addEventListener('click', select);
    card.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(); }
    });
    return card;
}

export function renderCurateSection(item, shouldScroll = true) {
    if (!item) return;
    if (shouldScroll) updateStepper(4);
    const section = document.getElementById('curate-section');
    const title = document.getElementById('curate-title');
    const grid = document.getElementById('variants-grid');
    if (!section || !title || !grid) return;
    title.textContent = `Bộ sưu tập áo dài: ${item.name}`;
    grid.replaceChildren(...variantsFor(item).map((variant) => createVariantCard(item, variant)));
    document.getElementById('dragon-wave-bridge')?.style.setProperty('display', 'block');
    const footerBridge = document.getElementById('curate-to-footer-bridge');
    footerBridge?.classList.add('is-visible');
    if (footerBridge) footerBridge.style.display = 'block';
    section.style.display = 'block';
    if (shouldScroll) section.scrollIntoView({ behavior: 'smooth' });
}
