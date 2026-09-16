const API_BASE_URL = (window.DH_API_BASE || 'http://127.0.0.1:8000').replace(/\/$/, '');
let HERITAGE_ITEMS = [];

let currentSelectedItem = null;

function setDynamicImage(image, source) {
    if (!image) return;

    const host = image.closest('.stage-img-preview, .modal-img-col, .passport-visual-col, .lightbox-img-wrapper');
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

function setPipelineProgress(progressBar, percentage) {
    if (progressBar) progressBar.style.setProperty('--progress', String(percentage / 100));
}

let studioInitialized = false;

function initStudio() {
    if (studioInitialized) return;
    studioInitialized = true;

    console.log('Studio Tái Sinh Di Sản Số AI - Khởi tạo thành công.');
    loadLiveHeritageItems();
}

async function loadLiveHeritageItems() {
    try {
        const response = await fetch(`${API_BASE_URL}/heritage`);
        if (!response.ok) throw new Error(`API ${response.status}`);
        HERITAGE_ITEMS = (await response.json()).map(item => ({
            ...item,
            image: item.image.startsWith('/') ? `${API_BASE_URL}${item.image}` : item.image,
        }));
    } catch (error) {
        console.warn('Không thể nạp metadata thật, dùng dữ liệu giao diện dự phòng.', error);
    }
    renderHeritageCards(HERITAGE_ITEMS);
    initDetailModal();
    initFooterLinks();
    document.addEventListener('visibilitychange', () => {
        document.documentElement.classList.toggle('is-page-hidden', document.hidden);
    });
}
function startStudioWhenReady() {
    if (window.componentsReady) {
        window.componentsReady
            .then(initStudio)
            .catch((error) => console.error('Không thể khởi tạo giao diện:', error));
        return;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initStudio, { once: true });
    } else {
        initStudio();
    }
}

startStudioWhenReady();

function renderHeritageCards(items) {
    const gridContainer = document.getElementById('heritage-cards-grid');
    if (!gridContainer) return;

    gridContainer.innerHTML = '';

    items.forEach(item => {
        const card = document.createElement('article');
        card.className = `heritage-card ${currentSelectedItem?.id === item.id ? 'selected' : ''}`;
        card.setAttribute('data-id', item.id);
        card.innerHTML = `
            <div class="card-img-wrap">
                <span class="badge-glaze">${item.conditioningMode || 'whole_object'}</span>
                <img src="${item.image}" alt="${item.name}" loading="lazy" decoding="async">
            </div>
            <div class="heritage-card-content">
                <div>
                    <div class="heritage-dynasty">${item.dynasty}</div>
                    <h3 class="heritage-title">${item.name}</h3>
                    <p class="heritage-desc">Conditioning mode: ${item.conditioningMode || 'whole_object'}</p>
                </div>
                <div>
                    <div class="glaze-palette-box">
                        <span class="glaze-label">Hiện vật dùng toàn thể hình ảnh</span>
                    </div>
                    <button class="card-action-btn" type="button">
                        <span>Chiêm ngưỡng & Tạo thiết kế</span>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                            <polyline points="12 5 19 12 12 19"></polyline>
                        </svg>
                    </button>
                </div>
            </div>
        `;
        card.addEventListener('click', () => {
            selectHeritageItem(item);
        });

        gridContainer.appendChild(card);
    });
}

function selectHeritageItem(item) {
    currentSelectedItem = item;
    document.querySelectorAll('.heritage-card').forEach(card => {
        if (card.getAttribute('data-id') === item.id) {
            card.classList.add('selected');
        } else {
            card.classList.remove('selected');
        }
    });
    updateStepper(2);
    const modal = document.getElementById('detail-modal');
    const modalImg = document.getElementById('modal-img');
    const modalTitle = document.getElementById('modal-title');
    const modalMeta = document.getElementById('modal-meta');
    const modalDesc = document.getElementById('modal-desc');

    if (modal && modalImg && modalTitle && modalMeta) {
        setDynamicImage(modalImg, item.image);
        modalTitle.textContent = item.name;
        modalMeta.textContent = `${item.dynasty} · Conditioning mode: ${item.conditioningMode || 'whole_object'}`;
        if (modalDesc) modalDesc.hidden = true;

        modal.classList.add('active');
    }
}

function initDetailModal() {
    const modal = document.getElementById('detail-modal');
    const closeBtn = document.getElementById('modal-close-btn');
    const generateBtn = document.getElementById('generate-btn');

    if (closeBtn && modal) {
        closeBtn.addEventListener('click', () => {
            modal.classList.remove('active');
            updateStepper(1);
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
                updateStepper(1);
            }
        });
    }

    if (generateBtn) {
        generateBtn.addEventListener('click', () => {
            if (!currentSelectedItem) return;
            modal.classList.remove('active');
            runVisualPipeline(currentSelectedItem);
        });
    }
    const step1Btn = document.getElementById('step-1-btn');
    const step2Btn = document.getElementById('step-2-btn');
    const step3Btn = document.getElementById('step-3-btn');
    const step4Btn = document.getElementById('step-4-btn');

    if (step1Btn) {
        step1Btn.addEventListener('click', () => {
            updateStepper(1);
            if (modal) modal.classList.remove('active');
            const catalog = document.getElementById('hien-vat');
            if (catalog) catalog.scrollIntoView({ behavior: 'smooth' });
        });
    }
    if (step2Btn) {
        step2Btn.addEventListener('click', () => {
            if (currentSelectedItem) {
                selectHeritageItem(currentSelectedItem);
            } else {
                selectHeritageItem(HERITAGE_ITEMS[0]);
            }
        });
    }
    if (step3Btn) {
        step3Btn.addEventListener('click', () => {
            if (!currentSelectedItem) {
                currentSelectedItem = HERITAGE_ITEMS[0];
            }
            runVisualPipeline(currentSelectedItem);
        });
    }
    if (step4Btn) {
        step4Btn.addEventListener('click', () => {
            if (!currentSelectedItem) {
                currentSelectedItem = HERITAGE_ITEMS[0];
            }
            renderCurateSection(currentSelectedItem);
            updateStepper(4);
            const curateSection = document.getElementById('curate-section');
            if (curateSection) curateSection.scrollIntoView({ behavior: 'smooth' });
        });
    }
    initPassportModal();
    initPipelineControls();
}

async function runVisualPipeline(item) {
    updateStepper(3);

    const pipelineModal = document.getElementById('pipeline-modal');
    const progressBar = document.getElementById('pipeline-progress-bar');
    const percentText = document.getElementById('pipeline-percentage');
    const statusText = document.getElementById('pipeline-status-text');
    const modalFooter = document.getElementById('pipeline-modal-footer');

    const stageCards = [
        document.getElementById('stage-card-1'),
        document.getElementById('stage-card-2'),
        document.getElementById('stage-card-3'),
        document.getElementById('stage-card-4')
    ];
    if (modalFooter) modalFooter.style.display = 'none';
    stageCards.forEach(c => {
        if (c) {
            c.classList.remove('running', 'done');
        }
    });

    setPipelineProgress(progressBar, 0);
    if (percentText) percentText.textContent = '0%';
    if (pipelineModal) pipelineModal.classList.add('active');
    statusText.textContent = "Đang gửi hiện vật tới pipeline RTX 4050...";
    try {
        const created = await fetch(`${API_BASE_URL}/generate`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ heritage_id: item.id })
        });
        if (!created.ok) throw new Error(`API ${created.status}`);
        const { job_id: jobId } = await created.json();
        let result;
        while (!result || ['queued', 'running'].includes(result.status)) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            const response = await fetch(`${API_BASE_URL}/generate/${jobId}`);
            if (!response.ok) throw new Error(`Job API ${response.status}`);
            result = await response.json();
            const progress = Number(result.progress || 0);
            const stage = Math.min(4, Math.max(1, Math.ceil(progress / 25)));
            stageCards.forEach((card, index) => card?.classList.toggle('done', index < stage - 1));
            stageCards.forEach((card, index) => card?.classList.toggle('running', index === stage - 1));
            setPipelineProgress(progressBar, progress);
            if (percentText) percentText.textContent = `${progress}%`;
            if (statusText) statusText.textContent = result.label || 'Đang xử lý...';
        }
        if (result.status !== 'completed') throw new Error(result.label || 'Pipeline thất bại');
        stageCards.forEach(card => { card?.classList.remove('running'); card?.classList.add('done'); });
        item.generatedVariants = result.variants;
        statusText.textContent = "Thiết kế đã sẵn sàng để bạn chiêm ngưỡng.";
        if (modalFooter) modalFooter.style.display = 'flex';
        renderCurateSection(item, false);
    } catch (error) {
        statusText.textContent = `Không thể tạo thiết kế: ${error.message}`;
        console.error('Pipeline API error:', error);
    }
}

function initPipelineControls() {
    const pipelineModal = document.getElementById('pipeline-modal');
    const closeBtn = document.getElementById('pipeline-close-btn');
    const stayBtn = document.getElementById('btn-stay-inspector');
    const modalGotoCurateBtn = document.getElementById('btn-modal-goto-curate');

    if (closeBtn && pipelineModal) {
        closeBtn.addEventListener('click', () => {
            pipelineModal.classList.remove('active');
        });
    }

    if (stayBtn && pipelineModal) {
        stayBtn.addEventListener('click', () => {
            pipelineModal.classList.remove('active');
        });
    }

    if (modalGotoCurateBtn && pipelineModal) {
        modalGotoCurateBtn.addEventListener('click', () => {
            pipelineModal.classList.remove('active');
            if (currentSelectedItem) {
                renderCurateSection(currentSelectedItem, true);
            }
        });
    }

}

function renderCurateSection(item, shouldScroll = true) {
    if (shouldScroll) {
        updateStepper(4);
    }

    const curateSection = document.getElementById('curate-section');
    const curateTitle = document.getElementById('curate-title');
    const variantsGrid = document.getElementById('variants-grid');

    if (!curateSection || !variantsGrid) return;

    curateTitle.textContent = `Bộ sưu tập áo dài: ${item.name}`;

    const VARIANTS = [
        {
            vNumber: 1,
            name: "Biến thể 1",
            layout: "Thân trước",
            palette: "Màu men gốc",
            similarity: "88.4%",
            img: `${item.variantImageBase || `./assets/images/curate/${item.id}_V`}1_aodai.png`
        },
        {
            vNumber: 2,
            name: "Biến thể 2",
            layout: "Phủ toàn thân",
            palette: "Tự do",
            similarity: "76.2%",
            img: `${item.variantImageBase || `./assets/images/curate/${item.id}_V`}2_aodai.png`
        },
        {
            vNumber: 3,
            name: "Biến thể 3",
            layout: "Băng gấu tà",
            palette: "Tự do",
            similarity: "68.5%",
            img: `${item.variantImageBase || `./assets/images/curate/${item.id}_V`}3_aodai.png`
        },
        {
            vNumber: 4,
            name: "Biến thể 4",
            layout: "Vai và ngực",
            palette: "Tự do",
            similarity: "54.1%",
            img: `${item.variantImageBase || `./assets/images/curate/${item.id}_V`}4_aodai.png`
        }
    ];
    if (Array.isArray(item.generatedVariants) && item.generatedVariants.length === 4) {
        item.generatedVariants.forEach((generated, index) => {
            const variant = VARIANTS[index];
            variant.img = generated.image_url.startsWith('/')
                ? `${API_BASE_URL}${generated.image_url}`
                : generated.image_url;
            variant.similarity = `${(Number(generated.similarity_pattern_vs_ceramic || 0) * 100).toFixed(1)}%`;
            variant.layout = generated.layout_label || variant.layout;
        });
    }

    variantsGrid.innerHTML = '';

    VARIANTS.forEach(v => {
        const card = document.createElement('article');
        card.className = 'variant-card';
        card.tabIndex = 0;
        card.setAttribute('role', 'button');
        card.setAttribute('aria-label', `${v.name} - ${v.similarity} tương đồng`);
        card.innerHTML = `
            <div class="variant-img-wrap">
                <img class="variant-img" src="${v.img}" alt="${v.name}" loading="lazy" decoding="async">
                <span class="similarity-badge">★ ${v.similarity}</span>
            </div>
            <div class="variant-layer" aria-hidden="true"></div>
            <div class="variant-info">
                <span class="variant-tagline">ĐỘ TƯƠNG ĐỒNG THAM KHẢO · ${v.similarity}</span>
                <h4 class="variant-name">${v.name}</h4>
                <button class="variant-btn-select" type="button" aria-label="Xem hộ chiếu ${v.name}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                        <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                        <polyline points="2 17 12 22 22 17"></polyline>
                        <polyline points="2 12 12 17 22 12"></polyline>
                    </svg>
                    <span>Xem hộ chiếu thiết kế →</span>
                </button>
            </div>
        `;
        card.addEventListener('click', () => {
            document.querySelectorAll('.variant-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            openDesignPassport(item, v);
        });
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                card.click();
            }
        });

        variantsGrid.appendChild(card);
    });

    const waveBridge = document.getElementById('dragon-wave-bridge');
    if (waveBridge) waveBridge.style.display = 'block';

    const footerBridge = document.getElementById('curate-to-footer-bridge');
    if (footerBridge) {
        footerBridge.classList.add('is-visible');
        footerBridge.style.display = 'block';
    }

    curateSection.style.display = 'block';
    if (shouldScroll) {
        curateSection.scrollIntoView({ behavior: 'smooth' });
    }
}

function openDesignPassport(item, variant) {
    const passportModal = document.getElementById('passport-modal');
    if (!passportModal) return;

    setDynamicImage(document.getElementById('passport-aodai-img'), variant.img);
    setDynamicImage(document.getElementById('passport-origin-thumb'), item.image);
    document.getElementById('passport-origin-name').textContent = item.name;

    document.getElementById('passport-similarity-val').textContent = `${variant.similarity} (Tham khảo)`;
    document.getElementById('passport-variant-title').textContent = variant.name;
    document.getElementById('passport-layout').textContent = variant.layout;
    document.getElementById('passport-palette-mode').textContent = variant.palette;

    const dotsContainer = document.getElementById('passport-palette-dots');
    if (dotsContainer) {
        dotsContainer.innerHTML = item.colors.map((c, i) =>
            `<span class="glaze-dot" style="background-color: ${c}; width: 22px; height: 22px;" title="${item.colorNames[i]} (${c})"></span>`
        ).join('');
    }

    passportModal.classList.add('active');
}

function initPassportModal() {
    const passportModal = document.getElementById('passport-modal');
    const closeBtn = document.getElementById('passport-close-btn');
    const resetBtn = document.getElementById('btn-reset-studio');
    const exportBtn = document.getElementById('btn-export-passport');

    if (closeBtn && passportModal) {
        closeBtn.addEventListener('click', () => {
            passportModal.classList.remove('active');
        });

        passportModal.addEventListener('click', (e) => {
            if (e.target === passportModal) {
                passportModal.classList.remove('active');
            }
        });
    }

    if (resetBtn && passportModal) {
        resetBtn.addEventListener('click', () => {
            passportModal.classList.remove('active');
            updateStepper(1);
            const catalog = document.getElementById('hien-vat');
            if (catalog) catalog.scrollIntoView({ behavior: 'smooth' });
        });
    }

    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            alert('🎉 Hộ chiếu di sản số và bản vẽ kỹ thuật đã được xuất thành công!');
        });
    }
}

function updateStepper(stepNumber) {
    const steps = [
        document.getElementById('step-1-btn'),
        document.getElementById('step-2-btn'),
        document.getElementById('step-3-btn'),
        document.getElementById('step-4-btn')
    ];

    steps.forEach((stepEl, index) => {
        if (!stepEl) return;
        const currentStep = index + 1;
        stepEl.classList.remove('active', 'completed');

        if (currentStep === stepNumber) {
            stepEl.classList.add('active');
        } else if (currentStep < stepNumber) {
            stepEl.classList.add('completed');
        }
    });
}

function initFooterLinks() {
    const linkStep1 = document.getElementById('footer-link-step1');
    if (linkStep1) {
        linkStep1.addEventListener('click', (e) => {
            e.preventDefault();
            updateStepper(1);
            const catalog = document.getElementById('heritage-cards-section') || document.getElementById('hien-vat');
            if (catalog) {
                catalog.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    }

    const linkStep4 = document.getElementById('footer-link-step4');
    if (linkStep4) {
        linkStep4.addEventListener('click', (e) => {
            e.preventDefault();
            const curateSection = document.getElementById('curate-section');
            if (curateSection) {
                const variantsGrid = document.getElementById('variants-grid');
                const item = currentSelectedItem || HERITAGE_ITEMS[0];
                if (!variantsGrid || !variantsGrid.children.length) renderCurateSection(item, false);
                updateStepper(4);
                curateSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    }
}
