export function setDynamicImage(image, source) {
    if (!image) return;
    const host = image.closest('.modal-img-col, .passport-visual-col');
    image.hidden = true;
    host?.classList.add('is-loading');
    const settle = (loaded) => {
        image.hidden = !loaded;
        host?.classList.remove('is-loading');
    };
    image.addEventListener('load', () => settle(true), { once: true });
    image.addEventListener('error', () => settle(false), { once: true });
    image.src = source;
}

export function setPipelineProgress(progressBar, percentage) {
    progressBar?.style.setProperty('--progress', String(percentage / 100));
}

export function scrollToElement(element) {
    element?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
