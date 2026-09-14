
window.componentsReady = (async () => {
    const slots = [...document.querySelectorAll('[data-component]')];

    await Promise.all(slots.map(async (slot) => {
        const name = slot.dataset.component;
        const response = await fetch(`./components/${name}.html`);

        if (!response.ok) {
            throw new Error(`Không thể nạp component: ${name}`);
        }

        slot.outerHTML = await response.text();
    }));
})();
