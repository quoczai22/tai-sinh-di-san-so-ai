
const COMPONENT_VERSION = 'logic-cleanup-3';

window.componentsReady = (async () => {
    const slots = [...document.querySelectorAll('[data-component]')];

    await Promise.all(slots.map(async (slot) => {
        const name = slot.dataset.component;
        const response = await fetch(`./components/${name}.html?v=${COMPONENT_VERSION}`, {
            cache: 'no-store',
        });

        if (!response.ok) {
            throw new Error(`Không thể nạp component: ${name}`);
        }

        slot.outerHTML = await response.text();
    }));
})();
