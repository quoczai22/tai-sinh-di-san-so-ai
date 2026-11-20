// components/viewer-controls.js — THANH ĐIỀU KHIỂN KHUNG 3D ở Studio: nút khoá đứng yên / tự xoay, nút − +, thanh thu phóng 70–180%.
// Vào: artifactImg (ảnh phẳng dự phòng khi không có WebGL) và viewerPromise (kết quả viewer3d.mountViewer).
// Ra: phần tử thanh công cụ. Có 3D thì điều khiển khung 3D; không có thì phóng ảnh phẳng.
import { h } from '../core/dom.js';

export function viewerControls(artifactImg, viewerPromise) {
    // Thanh điều khiển thu phóng hiện vật + nút khoá đứng yên / chuyển động xoay
    let viewerInstance = null;
    Promise.resolve(viewerPromise).then((inst) => { viewerInstance = inst; });

    let isLocked = false;
    let zoomLevel = 1.0;

    const lockIcon = h('span', { class: 'ctrl-icon', 'aria-hidden': 'true' }, '🔄');
    const updateLockUi = (spinning) => {
        isLocked = !spinning;
        lockBtn.setAttribute('aria-pressed', String(isLocked));
        lockBtn.title = isLocked ? 'Đang đứng yên — Bấm để tiếp tục xoay 360°' : 'Đang tự xoay — Bấm để khoá đứng yên';
        lockIcon.textContent = isLocked ? '🔒' : '🔄';
    };

    const lockBtn = h('button', {
        type: 'button',
        class: 'lb-step lock-btn',
        title: 'Đang tự xoay — Bấm để khoá đứng yên',
        onclick: () => {
            if (viewerInstance?.toggleSpin) {
                const nowSpinning = viewerInstance.toggleSpin();
                updateLockUi(nowSpinning);
            } else {
                updateLockUi(isLocked);
            }
        }
    }, lockIcon);

    const zoomSlider = h('input', {
        type: 'range',
        class: 'lb-zoom',
        min: '70',
        max: '180',
        step: '2',
        value: '100',
        'aria-label': 'Thu phóng hiện vật'
    });

    const applyZoom = (val) => {
        zoomLevel = Math.max(0.7, Math.min(1.8, Math.round(val * 100) / 100));
        zoomSlider.value = String(Math.round(zoomLevel * 100));
        if (viewerInstance?.setZoom) {
            viewerInstance.setZoom(zoomLevel);
        } else {
            artifactImg.style.transform = `scale(${zoomLevel})`;
        }
    };

    zoomSlider.addEventListener('input', () => {
        applyZoom(Number(zoomSlider.value) / 100);
    });

    const stepOut = h('button', {
        type: 'button',
        class: 'lb-step',
        'aria-label': 'Thu nhỏ',
        title: 'Thu nhỏ',
        onclick: () => applyZoom(zoomLevel - 0.1)
    }, '−');

    const stepIn = h('button', {
        type: 'button',
        class: 'lb-step',
        'aria-label': 'Phóng to',
        title: 'Phóng to',
        onclick: () => applyZoom(zoomLevel + 0.1)
    }, '+');

    const bar = h('div', { class: 'lb-zoomrow viewer-controls', role: 'toolbar', 'aria-label': 'Điều khiển xem hiện vật 3D' },
        lockBtn,
        stepOut,
        zoomSlider,
        stepIn
    );

    return bar;
}
