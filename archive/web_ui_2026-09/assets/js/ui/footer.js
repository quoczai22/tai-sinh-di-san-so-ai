import { scrollToElement } from '../core/dom.js';
import { getHeritageItems, getSelectedHeritageItem } from '../core/state.js';
import { renderCurateSection } from './curate.js';
import { updateStepper } from './stepper.js';

export function initFooterLinks() {
    document.getElementById('footer-link-step1')?.addEventListener('click', (event) => {
        event.preventDefault();
        updateStepper(1);
        scrollToElement(document.getElementById('hien-vat'));
    });
    document.getElementById('footer-link-step4')?.addEventListener('click', (event) => {
        event.preventDefault();
        const item = getSelectedHeritageItem() || getHeritageItems()[0];
        const section = document.getElementById('curate-section');
        if (!item?.generatedVariants?.length || !section) return;
        if (!document.getElementById('variants-grid')?.children.length) renderCurateSection(item, false);
        updateStepper(4);
        scrollToElement(section);
    });
}
