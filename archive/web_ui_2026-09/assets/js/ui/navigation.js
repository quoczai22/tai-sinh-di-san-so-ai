import { scrollToElement } from '../core/dom.js';
import { getHeritageItems, getSelectedHeritageItem, setSelectedHeritageItem } from '../core/state.js';
import { selectHeritageItem } from './catalog.js';
import { renderCurateSection } from './curate.js';
import { runVisualPipeline } from './pipeline.js';
import { updateStepper } from './stepper.js';

function selectedOrFirst() {
    const item = getSelectedHeritageItem() || getHeritageItems()[0];
    if (item && !getSelectedHeritageItem()) setSelectedHeritageItem(item);
    return item;
}

export function initNavigation() {
    document.getElementById('step-1-btn')?.addEventListener('click', () => {
        updateStepper(1);
        document.getElementById('detail-modal')?.classList.remove('active');
        scrollToElement(document.getElementById('hien-vat'));
    });
}
