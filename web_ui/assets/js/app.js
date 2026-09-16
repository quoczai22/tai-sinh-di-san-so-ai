import { setHeritageItems } from './core/state.js';
import { fetchHeritageItems } from './services/heritage-api.js';
import { initDetailModal, renderHeritageCards } from './ui/catalog.js';
import { initFooterLinks } from './ui/footer.js';
import { initNavigation } from './ui/navigation.js';
import { initPassportModal } from './ui/passport.js';
import { initPipelineControls } from './ui/pipeline.js';

let initialized = false;

async function initializeStudio() {
    if (initialized) return;
    initialized = true;
    try {
        const items = await fetchHeritageItems();
        setHeritageItems(items);
        renderHeritageCards(items);
    } catch (error) {
        console.warn('Không thể nạp metadata hiện vật từ API.', error);
    }
    initDetailModal();
    initNavigation();
    initPipelineControls();
    initPassportModal();
    initFooterLinks();
    document.addEventListener('visibilitychange', () => {
        document.documentElement.classList.toggle('is-page-hidden', document.hidden);
    });
}

if (window.componentsReady) {
    window.componentsReady.then(initializeStudio).catch((error) => console.error('Không thể khởi tạo giao diện:', error));
} else if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeStudio, { once: true });
} else {
    initializeStudio();
}
