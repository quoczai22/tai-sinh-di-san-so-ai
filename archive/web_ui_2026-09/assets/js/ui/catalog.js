import { setDynamicImage } from '../core/dom.js';
import { getSelectedHeritageItem, setSelectedHeritageItem } from '../core/state.js';
import { runVisualPipeline } from './pipeline.js';
import { recordAudit } from '../services/heritage-api.js';
import { updateStepper } from './stepper.js';

export function renderHeritageCards(items) {
    const grid = document.getElementById('heritage-cards-grid');
    if (!grid) return;
    grid.innerHTML = '';
    items.forEach((item) => {
        const card = document.createElement('article');
        card.className = `heritage-card ${getSelectedHeritageItem()?.id === item.id ? 'selected' : ''}`;
        card.dataset.id = item.id;
        card.innerHTML = `
            <div class="card-img-wrap"><img src="${item.image}" alt="${item.name}" loading="lazy" decoding="async"></div>
            <div class="heritage-card-content">
                <div><div class="heritage-dynasty">${item.dynasty}</div><h3 class="heritage-title">${item.name}</h3></div>
                <button class="card-action-btn" type="button">
                    <span>Chiêm ngưỡng & Tạo thiết kế</span>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                        <polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                </button>
            </div>`;
        card.addEventListener('click', () => selectHeritageItem(item));
        grid.appendChild(card);
    });
}

export function selectHeritageItem(item) {
    setSelectedHeritageItem(item);
    recordAudit({ step: 1, event: 'heritage_selected', heritage_id: item.id });
    document.querySelectorAll('.heritage-card').forEach((card) => card.classList.toggle('selected', card.dataset.id === item.id));
    updateStepper(2);
    const modal = document.getElementById('detail-modal');
    const image = document.getElementById('modal-img');
    const title = document.getElementById('modal-title');
    const meta = document.getElementById('modal-meta');
    const description = document.getElementById('modal-desc');
    if (!modal || !image || !title || !meta) return;
    setDynamicImage(image, item.image);
    title.textContent = item.name;
    meta.textContent = item.dynasty;
    if (description) {
        description.textContent = item.description || '';
        description.hidden = !item.description;
    }
    recordAudit({ step: 2, event: 'artifact_viewed', heritage_id: item.id });
    modal.classList.add('active');
}

export function initDetailModal() {
    const modal = document.getElementById('detail-modal');
    const close = () => {
        modal?.classList.remove('active');
        updateStepper(1);
    };
    document.getElementById('modal-close-btn')?.addEventListener('click', close);
    modal?.addEventListener('click', (event) => { if (event.target === modal) close(); });
    document.getElementById('generate-btn')?.addEventListener('click', () => {
        const item = getSelectedHeritageItem();
        if (!item) return;
        modal?.classList.remove('active');
        runVisualPipeline(item);
    });
}
