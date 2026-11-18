import { setDynamicImage, scrollToElement } from '../core/dom.js';
import { updateStepper } from './stepper.js';

export function openDesignPassport(item, variant) {
    const modal = document.getElementById('passport-modal');
    if (!modal) return;
    setDynamicImage(document.getElementById('passport-aodai-img'), variant.img);
    setDynamicImage(document.getElementById('passport-origin-thumb'), item.image);
    document.getElementById('passport-origin-name').textContent = item.name;
    document.getElementById('passport-similarity-val').textContent = `${variant.similarity} (Tham khảo)`;
    document.getElementById('passport-variant-title').textContent = variant.name;
    document.getElementById('passport-layout').textContent = variant.layout;
    modal.classList.add('active');
}

export function initPassportModal() {
    const modal = document.getElementById('passport-modal');
    const close = () => modal?.classList.remove('active');
    document.getElementById('passport-close-btn')?.addEventListener('click', close);
    modal?.addEventListener('click', (event) => { if (event.target === modal) close(); });
    document.getElementById('btn-reset-studio')?.addEventListener('click', () => {
        close();
        updateStepper(1);
        scrollToElement(document.getElementById('hien-vat'));
    });
    document.getElementById('btn-export-passport')?.addEventListener('click', () => {
        const imageUrl = document.getElementById('passport-aodai-img')?.src;
        if (imageUrl) window.open(imageUrl, '_blank', 'noopener');
    });
}
