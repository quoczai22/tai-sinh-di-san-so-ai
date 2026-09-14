/**
 * MAIN.JS - Xử lý tương tác Studio Tái Sinh Di Sản Số AI
 * Kết hợp phong cách Stitch by Google & Figma Make (MVP v6.1)
 */

// Dữ liệu 6 hiện vật gốm Bát Tràng chuẩn hóa theo MVP spec v6.1 & rule_base.json
const HERITAGE_ITEMS = [
    {
        id: "BT001",
        name: "Hoa sen trên gốm thờ Bát Tràng",
        dynasty: "Niên hiệu Vĩnh Thịnh (1705 - 1719)",
        glaze: "Men rạn",
        category: ["men-ran", "phat-giao"],
        categoryLabel: "Biểu trưng Phật giáo · Lư hương men rạn",
        image: "./assets/images/heritage/bt001.png",
        colors: ["#3b4856", "#87929e", "#d8dfd5", "#a47e5b"],
        colorNames: ["Xanh chàm men", "Xám rạn đá", "Trắng ngà cốt gốm", "Nâu hoàng thổ"],
        desc: "Thành lư hương tạo hình bông sen nở với 3 lớp cánh nổi tinh xảo. Đế lư tạo hình chiếc lá sen úp trang nhã, biểu trưng cho sự thanh khiết trong Phật giáo Đại thừa."
    },
    {
        id: "BT002",
        name: "Rồng trên đồ thờ Bát Tràng",
        dynasty: "Niên hiệu Hưng Trị (1590)",
        glaze: "Men lam",
        category: ["men-lam", "cung-dinh"],
        categoryLabel: "Bảo vật Quốc gia · Đồ cung tiến chùa",
        image: "./assets/images/heritage/bt002.png",
        colors: ["#1d4ed8", "#3b82f6", "#d97706", "#f1f5f9"],
        colorNames: ["Xanh lam gốm đậm", "Lam tràm hoa văn", "Vàng men rạn", "Men sứ trắng"],
        desc: "Bộ chân đèn và lư hương do tượng nhân Đỗ Xuân Vy tạo tác, trang trí hình rồng yên ngựa và mây uốn lượn uy nghi. Đã được Thủ tướng Chính phủ công nhận Bảo vật Quốc gia."
    },
    {
        id: "BT005",
        name: "Chữ Thọ trong ô hình lá đề",
        dynasty: "Thế kỷ XVII (1637)",
        glaze: "Men rạn",
        category: ["men-ran", "phat-giao"],
        categoryLabel: "Chỉ dấu niên đại · Đồ thờ thế kỷ XVII",
        image: "./assets/images/heritage/bt005.png",
        colors: ["#475569", "#94a3b8", "#e2e8f0", "#b45309"],
        colorNames: ["Xám tro cổ", "Men rạn hạt mè", "Trắng sương", "Nâu đất nung"],
        desc: "Chữ Thọ thể hiện nổi để mộc tinh xảo trong ô lá đề Phật giáo trên chân đèn đế nghê quỳ, cung tiến vào chùa Thánh Ân năm Đinh Sửu (1637)."
    },
    {
        id: "BT007",
        name: "Bát bảo (kiếm, bút, cuốn thư, túi gấm...)",
        dynasty: "Niên hiệu Gia Long (1802 - 1820)",
        glaze: "Men rạn",
        category: ["men-ran", "trang-tri"],
        categoryLabel: "Bát bảo Đạo giáo · Nậm rượu men rạn ngà",
        image: "./assets/images/heritage/bt007.png",
        colors: ["#785d38", "#b4976a", "#e8dfcc", "#1e293b"],
        colorNames: ["Vàng hổ phách", "Men ngà cổ", "Trắng hoàng gia", "Đen than mun"],
        desc: "Đề tài Bát bảo Đạo giáo kết hợp triết lý Nho gia trên nậm rượu dáng hồ lô men rạn ngà, biểu trưng cho sự chúc phúc, trường thọ và văn hóa hiền tài đất Thăng Long."
    },
    {
        id: "BT008",
        name: "Tứ quý (tùng – cúc – trúc – mai)",
        dynasty: "Niên hiệu Cảnh Hưng (1740 - 1786)",
        glaze: "Men rạn",
        category: ["men-ran", "trang-tri"],
        categoryLabel: "Đề tài trang trí thuần túy · Bình men rạn",
        image: "./assets/images/heritage/bt008.png",
        colors: ["#2d4059", "#4a7c59", "#de9b72", "#eae3d2"],
        colorNames: ["Lam đậm cổ vật", "Xanh tùng bách", "Vàng hoàng kim", "Trắng ngà men rạn"],
        desc: "Bốn loài cây tượng trưng cho bốn mùa xuân - hạ - thu - đông tuần hoàn và khí chất người quân tử. Hoa văn chạm khắc tỉ mỉ dọc thân bình tứ giác độc bản."
    },
    {
        id: "BT011",
        name: "Hoa dây lá lật (băng hoa văn đường dềm)",
        dynasty: "Thế kỷ XVIII (1735 - 1740)",
        glaze: "Men rạn",
        category: ["men-ran", "trang-tri"],
        categoryLabel: "Chỉ dấu niên đại thế kỷ XVIII · Đỉnh thờ",
        image: "./assets/images/heritage/bt011.png",
        colors: ["#334155", "#64748b", "#c2410c", "#f8fafc"],
        colorNames: ["Xám men gốm", "Xám tro nung", "Đỏ son gạch", "Trắng sứ mịn"],
        desc: "Băng hoa văn hoa dây lá lật uốn lượn liên hoàn quanh cổ đỉnh thờ, tạo nhịp điệu chuyển động mềm mại, là nguồn cảm hứng lý tưởng để ứng dụng trên tà áo dài lụa."
    }
];

let currentSelectedItem = null;
let currentActiveFilter = "all";

/** Nạp ảnh động an toàn: modal chỉ hiện ảnh khi tệp đã sẵn sàng. */
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

    // 1. Render danh sách 6 hiện vật
    renderHeritageCards(HERITAGE_ITEMS);

    // 2. Khởi tạo Filter Chips
    initFilterChips();

    // 3. Khởi tạo Modal chi tiết & Stepper
    initDetailModal();

    // 4. Framer Editor Bar toggle
    initEditorBar();

    // 5. Khởi tạo Bát Tràng Gooey Liquid Footer
    initGlazeLiquidFooter();
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

/**
 * Render 6 thẻ hiện vật vào lưới
 */
function renderHeritageCards(items) {
    const gridContainer = document.getElementById('heritage-cards-grid');
    if (!gridContainer) return;

    gridContainer.innerHTML = '';

    items.forEach(item => {
        const card = document.createElement('article');
        card.className = `heritage-card ${currentSelectedItem?.id === item.id ? 'selected' : ''}`;
        card.setAttribute('data-id', item.id);

        // Tạo dải chấm màu men (glaze dots)
        const glazeDotsHtml = item.colors.map((color, index) => 
            `<span class="glaze-dot" style="background-color: ${color};" title="${item.colorNames[index]} (${color})"></span>`
        ).join('');

        card.innerHTML = `
            <div class="card-img-wrap">
                <span class="badge-code">${item.id}</span>
                <span class="badge-glaze">${item.glaze}</span>
                <img src="${item.image}" alt="${item.name}" loading="lazy">
            </div>
            <div class="heritage-card-content">
                <div>
                    <div class="heritage-dynasty">${item.dynasty}</div>
                    <h3 class="heritage-title">${item.name}</h3>
                    <p class="heritage-desc">${item.categoryLabel}</p>
                </div>
                <div>
                    <div class="glaze-palette-box">
                        <span class="glaze-label">Màu men trích xuất</span>
                        <div class="glaze-dots">${glazeDotsHtml}</div>
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

        // Click để chọn hiện vật và mở Bước 2 (Modal / Drawer)
        card.addEventListener('click', () => {
            selectHeritageItem(item);
        });

        gridContainer.appendChild(card);
    });
}

/**
 * Xử lý bộ lọc Filter Chips
 */
function initFilterChips() {
    const chipBtns = document.querySelectorAll('.filter-chip');
    chipBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            chipBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const filterValue = btn.getAttribute('data-filter');
            currentActiveFilter = filterValue;

            if (filterValue === 'all') {
                renderHeritageCards(HERITAGE_ITEMS);
            } else {
                const filtered = HERITAGE_ITEMS.filter(item => item.category.includes(filterValue));
                renderHeritageCards(filtered);
            }
        });
    });
}

/**
 * Chọn hiện vật và hiển thị modal chi tiết (Bước 2)
 */
function selectHeritageItem(item) {
    currentSelectedItem = item;

    // Cập nhật class selected cho card
    document.querySelectorAll('.heritage-card').forEach(card => {
        if (card.getAttribute('data-id') === item.id) {
            card.classList.add('selected');
        } else {
            card.classList.remove('selected');
        }
    });

    // Cập nhật Stepper sang Bước 2
    updateStepper(2);

    // Điền dữ liệu vào Modal
    const modal = document.getElementById('detail-modal');
    const modalImg = document.getElementById('modal-img');
    const modalTitle = document.getElementById('modal-title');
    const modalMeta = document.getElementById('modal-meta');
    const modalDesc = document.getElementById('modal-desc');
    const modalDots = document.getElementById('modal-glaze-dots');

    if (modal && modalImg && modalTitle && modalMeta && modalDesc && modalDots) {
        setDynamicImage(modalImg, item.image);
        modalTitle.innerHTML = `<span class="modal-artifact-code">${item.id}</span><span class="modal-artifact-name">${item.name}</span>`;
        modalMeta.textContent = `${item.dynasty} · ${item.glaze} Bát Tràng`;
        modalDesc.textContent = item.desc;

        modalDots.innerHTML = item.colors.map((color, index) => 
            `<span class="glaze-dot" style="background-color: ${color}; width: 22px; height: 22px;" title="${item.colorNames[index]} (${color})"></span>`
        ).join('');

        modal.classList.add('active');
    }
}

/**
 * Khởi tạo modal chi tiết và hành động Tạo thiết kế
 */
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

            // Đóng modal bước 2 và chạy trực quan Bước 3
            modal.classList.remove('active');
            runVisualPipeline(currentSelectedItem);
        });
    }

    // Các nút stepper trên Header
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
            updateStepper(3);
            openPipelineModal(currentSelectedItem);
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

    // Khởi tạo nút đóng Passport Modal
    initPassportModal();

    // Khởi tạo các tương tác cho Pipeline & Lightbox
    initPipelineControls();
    initStageLightbox();
}

/**
 * Thông tin chi tiết 4 pha phục vụ soi kỹ thuật (Lightbox & Inspector)
 */
let currentLightboxStage = 1;

const STAGE_DETAILS = {
    1: {
        badge: "Pha 01 / 04 · Khảo Cứu Hình Thái",
        title: "Tách Nền & Trích Xuất Canny Lineart",
        desc: "Bộ lọc Canny loại bỏ hoàn toàn viền bao thân bình gốm, chỉ giữ lại mạng lưới đường nét hoa văn nguyên bản phục vụ quá trình tái tạo toán học phẳng.",
        model: "ControlNet Canny v1.1",
        res: "1024 × 1024 px",
        params: "Threshold Low: 100, High: 200",
        purpose: "Bảo lưu 100% tỷ lệ và hình thái di sản Bát Tràng",
        getImage: (id) => `./assets/images/pipeline_steps/${id}_canny.png`,
        caption: "Bản vẽ phân đoạn đường nét Canny Edge trích xuất từ hiện vật"
    },
    2: {
        badge: "Pha 02 / 04 · Biến Đổi Không Gian",
        title: "Sinh Hoa Văn Phẳng Liền Mạch (Seamless Pattern)",
        desc: "Mô hình SD1.5 kết hợp thuật toán Circular Convolution Tiling giúp hoa văn lặp lại vô tận (seamless) trên cả trục ngang và trục dọc mà không để lại vết nối.",
        model: "SD1.5 + Circular Tiling Mode",
        res: "1024 × 1024 px (Repeat 2x2)",
        params: "ControlNet Weight: 0.85, CFG: 7.5",
        purpose: "Tạo tư liệu vải dệt và in hoa văn khổ lớn",
        getImage: (id) => `./assets/images/pipeline_steps/${id}_pattern.png`,
        caption: "Hoa văn phẳng lặp vô tận (Circular Tile) sẵn sàng may trang phục"
    },
    3: {
        badge: "Pha 03 / 04 · Uốn Lượn Hình Học",
        title: "Displacement Map & Shading Map Nếp Vải",
        desc: "Ma trận bản đồ độ sâu (Displacement Map 16-bit) uốn cong hoa văn theo chuyển động thực tế của cơ thể, hòa trộn với Shading Map qua chế độ Multiply.",
        model: "Photometric Stereo & Displacement",
        res: "1024 × 1536 px",
        params: "Depth Scale: 1.25, Shading: Multiply 80%",
        purpose: "Tái hiện chính xác nếp gấp tà áo dài khi cử động",
        getImage: (id) => `./assets/images/pipeline_steps/${id}_composite.png`,
        caption: "Ma trận nếp gấp lụa áo dài tích hợp hoa văn uốn theo nếp vải"
    },
    4: {
        badge: "Pha 04 / 04 · Hoàn Thiện Tác Phẩm",
        title: "img2img Denoise 0.40 & Chất Liệu Tơ Tằm",
        desc: "Lượt sinh ảnh cuối cùng bổ sung ánh sáng sợi tơ tằm, làm mềm các mép uốn và đồng bộ sắc men cổ truyền Bát Tràng vào cấu trúc sợi vải mềm mại sang trọng.",
        model: "SD1.5 + Euler a Refiner",
        res: "1024 × 1536 px",
        params: "Denoise Strength: 0.40, Steps: 28",
        purpose: "Xuất bản thiết kế Áo Dài truyền thống chuẩn thị giác cao cấp",
        getImage: (id) => `./assets/images/curate/${id}_V1.png`,
        caption: "Tác phẩm Áo Dài hoàn thiện với sắc thái men gốm và chất liệu lụa tơ tằm"
    }
};

/**
 * Mở Modal Tiến trình 4 pha (như modal xem mô tả ở Bước 2)
 */
function openPipelineModal(item) {
    const pipelineModal = document.getElementById('pipeline-modal');
    const progressBar = document.getElementById('pipeline-progress-bar');
    const percentText = document.getElementById('pipeline-percentage');
    const statusText = document.getElementById('pipeline-status-text');
    const modalFooter = document.getElementById('pipeline-modal-footer');

    // Nạp ảnh thực tế cho 4 pha của hiện vật
    setDynamicImage(document.getElementById('stage-img-1'), `./assets/images/pipeline_steps/${item.id}_canny.png`);
    setDynamicImage(document.getElementById('stage-img-2'), `./assets/images/pipeline_steps/${item.id}_pattern.png`);
    setDynamicImage(document.getElementById('stage-img-3'), `./assets/images/pipeline_steps/${item.id}_composite.png`);
    setDynamicImage(document.getElementById('stage-img-4'), `./assets/images/curate/${item.id}_V1.png`);

    const stageCards = [
        document.getElementById('stage-card-1'),
        document.getElementById('stage-card-2'),
        document.getElementById('stage-card-3'),
        document.getElementById('stage-card-4')
    ];

    stageCards.forEach(c => {
        if (c) {
            c.classList.remove('running');
            c.classList.add('done');
        }
    });

    setPipelineProgress(progressBar, 100);
    if (percentText) percentText.textContent = '100%';
    if (statusText) statusText.textContent = `✨ Quy trình 4 pha kỹ thuật: ${item.name} (${item.id}). Bấm vào từng pha để soi chi tiết.`;
    if (modalFooter) modalFooter.style.display = 'flex';

    if (pipelineModal) pipelineModal.classList.add('active');
}

/**
 * BƯỚC 3: Chạy trực quan Pipeline 4 pha kỹ thuật với tiến độ và ảnh preview thực tế
 */
function runVisualPipeline(item) {
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

    // Nạp ảnh thực tế cho 4 pha của hiện vật
    setDynamicImage(document.getElementById('stage-img-1'), `./assets/images/pipeline_steps/${item.id}_canny.png`);
    setDynamicImage(document.getElementById('stage-img-2'), `./assets/images/pipeline_steps/${item.id}_pattern.png`);
    setDynamicImage(document.getElementById('stage-img-3'), `./assets/images/pipeline_steps/${item.id}_composite.png`);
    setDynamicImage(document.getElementById('stage-img-4'), `./assets/images/curate/${item.id}_V1.png`);

    // Reset trạng thái các card và footer
    if (modalFooter) modalFooter.style.display = 'none';
    stageCards.forEach(c => {
        if (c) {
            c.classList.remove('running', 'done');
        }
    });

    setPipelineProgress(progressBar, 0);
    if (percentText) percentText.textContent = '0%';
    if (pipelineModal) pipelineModal.classList.add('active');

    // Pha 1: 0% -> 25% (0.7s)
    statusText.textContent = "Pha 1/4: Tách nền & Canny trích xuất hoa văn phẳng từ hiện vật...";
    stageCards[0]?.classList.add('running');
    setPipelineProgress(progressBar, 25);
    if (percentText) percentText.textContent = '25%';

    setTimeout(() => {
        stageCards[0]?.classList.remove('running');
        stageCards[0]?.classList.add('done');

        // Pha 2: 25% -> 50% (1.5s)
        statusText.textContent = "Pha 2/4: SD1.5 + ControlNet sinh hoa văn tuần hoàn liền mạch (Circular Tile)...";
        stageCards[1]?.classList.add('running');
        setPipelineProgress(progressBar, 50);
        if (percentText) percentText.textContent = '50%';

        setTimeout(() => {
            stageCards[1]?.classList.remove('running');
            stageCards[1]?.classList.add('done');

            // Pha 3: 50% -> 75% (2.3s)
            statusText.textContent = "Pha 3/4: Displacement Map & Shading Map uốn hoa văn theo nếp vải áo dài...";
            stageCards[2]?.classList.add('running');
            setPipelineProgress(progressBar, 75);
            if (percentText) percentText.textContent = '75%';

            setTimeout(() => {
                stageCards[2]?.classList.remove('running');
                stageCards[2]?.classList.add('done');

                // Pha 4: 75% -> 100% (3.0s)
                statusText.textContent = "Pha 4/4: img2img Denoise 0.40 tạo độ rủ tơ tằm tự nhiên cho bộ sưu tập...";
                stageCards[3]?.classList.add('running');
                setPipelineProgress(progressBar, 100);
                if (percentText) percentText.textContent = '100%';

                setTimeout(() => {
                    stageCards[3]?.classList.remove('running');
                    stageCards[3]?.classList.add('done');
                    statusText.textContent = "✨ Hoàn thành xuất sắc 4 pha kỹ thuật! Nhấn vào thẻ để soi chi tiết hoặc chuyển sang Bước 4.";

                    // Hiển thị Footer điều khiển thay vì tự động tắt làm người dùng mất xem!
                    if (modalFooter) modalFooter.style.display = 'flex';

                    // Sẵn sàng nội dung Bước 4 ở bên dưới
                    renderCurateSection(item, false);

                }, 700);

            }, 700);

        }, 700);

    }, 700);
}

/**
 * Khởi tạo các nút điều khiển của Pipeline Modal và Section
 */
function initPipelineControls() {
    const pipelineModal = document.getElementById('pipeline-modal');
    const closeBtn = document.getElementById('pipeline-close-btn');
    const stayBtn = document.getElementById('btn-stay-inspector');
    const modalGotoCurateBtn = document.getElementById('btn-modal-goto-curate');
    const rerunBtn = document.getElementById('btn-rerun-pipeline');
    const gotoStep4Btn = document.getElementById('btn-goto-step4');

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

    if (rerunBtn) {
        rerunBtn.addEventListener('click', () => {
            if (currentSelectedItem) {
                runVisualPipeline(currentSelectedItem);
            } else {
                runVisualPipeline(HERITAGE_ITEMS[0]);
            }
        });
    }

    // Gắn sự kiện click vào các thẻ stage card trong Modal để soi Lightbox
    document.querySelectorAll('.pipeline-stage-card').forEach(card => {
        card.addEventListener('click', () => {
            const stage = parseInt(card.getAttribute('data-stage') || '1', 10);
            openStageLightbox(stage);
        });
    });
}

/**
 * Mở Lightbox soi chi tiết từng pha kỹ thuật
 */
function openStageLightbox(stageNumber) {
    currentLightboxStage = stageNumber;
    const item = currentSelectedItem || HERITAGE_ITEMS[0];
    const details = STAGE_DETAILS[stageNumber];
    if (!details) return;

    const modal = document.getElementById('stage-lightbox-modal');
    if (!modal) return;

    setDynamicImage(document.getElementById('lightbox-main-img'), details.getImage(item.id));
    document.getElementById('lightbox-caption').textContent = `${details.caption} (${item.id})`;
    document.getElementById('lightbox-phase-badge').textContent = details.badge;
    document.getElementById('lightbox-title').textContent = details.title;
    document.getElementById('lightbox-desc').textContent = details.desc;

    document.getElementById('lightbox-spec-model').textContent = details.model;
    document.getElementById('lightbox-spec-res').textContent = details.res;
    document.getElementById('lightbox-spec-params').textContent = details.params;
    document.getElementById('lightbox-spec-purpose').textContent = details.purpose;

    modal.classList.add('active');
}

/**
 * Khởi tạo Modal Lightbox (đóng, chuyển pha tới / lui)
 */
function initStageLightbox() {
    const modal = document.getElementById('stage-lightbox-modal');
    const closeBtn = document.getElementById('lightbox-close-btn');
    const prevBtn = document.getElementById('lightbox-prev-btn');
    const nextBtn = document.getElementById('lightbox-next-btn');

    if (closeBtn && modal) {
        closeBtn.addEventListener('click', () => {
            modal.classList.remove('active');
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            let nextStage = currentLightboxStage - 1;
            if (nextStage < 1) nextStage = 4;
            openStageLightbox(nextStage);
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            let nextStage = currentLightboxStage + 1;
            if (nextStage > 4) nextStage = 1;
            openStageLightbox(nextStage);
        });
    }
}

/**
 * BƯỚC 4: Hiển thị 4 thiết kế áo dài phái sinh thực tế
 */
function renderCurateSection(item, shouldScroll = true) {
    if (shouldScroll) {
        updateStepper(4);
    }

    const curateSection = document.getElementById('curate-section');
    const curateTitle = document.getElementById('curate-title');
    const variantsGrid = document.getElementById('variants-grid');

    if (!curateSection || !variantsGrid) return;

    curateTitle.textContent = `Bộ Sưu Tập Áo Dài: ${item.name} (${item.id})`;

    const VARIANTS = [
        {
            vNumber: 1,
            name: "Biến thể 1 — Tôn trọng nguyên bản",
            rule: "ControlNet w=0.85 · Bảng màu men gốc · Bố cục toàn thân điểm cao nhất",
            similarity: "88.4%",
            img: `./assets/images/curate/${item.id}_V1.png`
        },
        {
            vNumber: 2,
            name: "Biến thể 2 — Cân bằng di sản",
            rule: "ControlNet w=0.65 · Bảng màu lam & ngọc · Bố cục dải hoa văn thân trước",
            similarity: "76.2%",
            img: `./assets/images/curate/${item.id}_V2.png`
        },
        {
            vNumber: 3,
            name: "Biến thể 3 — Cách tân hiện đại",
            rule: "ControlNet w=0.45 · Sắc thu trang nhã · Bố cục nhấn tà áo & tay áo",
            similarity: "68.5%",
            img: `./assets/images/curate/${item.id}_V3.png`
        },
        {
            vNumber: 4,
            name: "Biến thể 4 — Đột phá nghệ thuật",
            rule: "ControlNet w=0.25 · Đương đại tự do · Bố cục mảng lớn phóng khoáng",
            similarity: "54.1%",
            img: `./assets/images/curate/${item.id}_V4.png`
        }
    ];

    variantsGrid.innerHTML = '';

    VARIANTS.forEach(v => {
        const card = document.createElement('article');
        card.className = 'variant-card';
        card.tabIndex = 0;
        card.setAttribute('role', 'button');
        card.setAttribute('aria-label', `${v.name} - ${v.similarity} tương đồng`);
        card.innerHTML = `
            <div class="variant-img-wrap">
                <img class="variant-img" src="${v.img}" alt="${v.name}" loading="lazy">
                <span class="similarity-badge">★ ${v.similarity}</span>
                <span class="variant-code-badge">V${v.vNumber}</span>
            </div>
            <div class="variant-layer" aria-hidden="true"></div>
            <div class="variant-info">
                <span class="variant-tagline">TÁI SINH DI SẢN · ${v.similarity} TƯƠNG ĐỒNG</span>
                <h4 class="variant-name">${v.name}</h4>
                <p class="variant-rule-desc">${v.rule}</p>
                <button class="variant-btn-select" type="button" aria-label="Xem hộ chiếu ${v.name}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                        <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                        <polyline points="2 17 12 22 22 17"></polyline>
                        <polyline points="2 12 12 17 22 12"></polyline>
                    </svg>
                    <span>XEM HỘ CHIẾU PASSPORT →</span>
                </button>
            </div>
        `;

        // Click vào card hoặc bấm nút đều chọn và mở Hộ Chiếu Thiết Kế chi tiết
        card.addEventListener('click', () => {
            document.querySelectorAll('.variant-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            openDesignPassport(item, v);
        });

        // Hỗ trợ phím Enter / Space cho bàn phím
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

    curateSection.style.display = 'block';
    if (shouldScroll) {
        curateSection.scrollIntoView({ behavior: 'smooth' });
    }
}

/**
 * Mở Hộ Chiếu Thiết Kế (Design Passport)
 */
function openDesignPassport(item, variant) {
    const passportModal = document.getElementById('passport-modal');
    if (!passportModal) return;

    setDynamicImage(document.getElementById('passport-aodai-img'), variant.img);
    setDynamicImage(document.getElementById('passport-origin-thumb'), item.image);
    document.getElementById('passport-origin-name').textContent = `${item.id} — ${item.name}`;

    document.getElementById('passport-similarity-val').textContent = `${variant.similarity} (Tham khảo)`;
    document.getElementById('passport-variant-title').textContent = variant.name;
    document.getElementById('passport-heritage-id').textContent = `${item.id} · ${item.dynasty} · ${item.glaze}`;
    document.getElementById('passport-seed').textContent = `#SEED_42_V${variant.vNumber}_${variant.similarity.replace('%','')}_AUDIT_LOG_OK`;

    const dotsContainer = document.getElementById('passport-palette-dots');
    if (dotsContainer) {
        dotsContainer.innerHTML = item.colors.map((c, i) => 
            `<span class="glaze-dot" style="background-color: ${c}; width: 22px; height: 22px;" title="${item.colorNames[i]} (${c})"></span>`
        ).join('');
    }

    passportModal.classList.add('active');
}

/**
 * Khởi tạo sự kiện đóng & reset của Passport Modal
 */
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

/**
 * Cập nhật trạng thái thanh Stepper 4 bước
 */
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

/**
 * Widget Framer Editor Bar
 */
function initEditorBar() {
    const editorBarBtn = document.getElementById('__framer-editorbar-button');
    const editorBarLabel = document.getElementById('__framer-editorbar-label');

    if (editorBarBtn && editorBarLabel) {
        editorBarBtn.addEventListener('click', () => {
            editorBarLabel.classList.toggle('__framer-editorbar-button-tooltip-visible');
        });
    }
}

/**
 * Khởi tạo Bát Tràng Gooey Liquid Footer (Dòng men lỏng Bát Tràng)
 * Tạo các hạt men nổi dâng trào và điều hướng thông minh Bước 1 - Bước 4
 */
function initGlazeLiquidFooter() {
    const container = document.getElementById("glaze-particle-container");
    if (container) {
        container.innerHTML = '';
        const fragment = document.createDocumentFragment();

        // 1. Tạo chuỗi bong bóng chân sóng liên tục (Base Meniscus) để mép trên lượn sóng tự nhiên, KHÔNG có đường thẳng
        const baseBubbleCount = window.innerWidth < 640 ? 18 : 34;
        const step = 100 / (baseBubbleCount - 1);
        for (let b = 0; b < baseBubbleCount; b++) {
            const baseSpan = document.createElement("span");
            baseSpan.classList.add("glaze-base-bubble");
            baseSpan.style.setProperty("--dim", `${3.5 + Math.random() * 2.5}rem`);
            baseSpan.style.setProperty("--pos-x", `${b * step - 2 + (Math.random() * 2 - 1)}%`);
            baseSpan.style.setProperty("--dur", `${2.5 + Math.random() * 2}s`);
            baseSpan.style.setProperty("--delay", `${-1 * (Math.random() * 5)}s`);
            fragment.appendChild(baseSpan);
        }

        // 2. Tạo các giọt men gốm lỏng dâng trào và tách bọt (Rising Particles)
        const particleCount = window.innerWidth < 640 ? 25 : 55;
        for (let i = 0; i < particleCount; i++) {
            const span = document.createElement("span");
            span.classList.add("glaze-particle");
            span.style.setProperty("--dim", `${2.2 + Math.random() * 4}rem`);
            span.style.setProperty("--uplift", `${5 + Math.random() * 7.5}rem`);
            span.style.setProperty("--pos-x", `${Math.random() * 100}%`);
            span.style.setProperty("--dur", `${2.6 + Math.random() * 2.8}s`);
            span.style.setProperty("--delay", `${-1 * (Math.random() * 10)}s`);
            fragment.appendChild(span);
        }

        container.appendChild(fragment);
    }

    // Điều hướng về Bước 1 (Khảo cứu Hiện vật Gốm)
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

    // Điều hướng đến Bước 4 (Bộ Sưu Tập Áo Dài)
    const linkStep4 = document.getElementById('footer-link-step4');
    if (linkStep4) {
        linkStep4.addEventListener('click', (e) => {
            e.preventDefault();
            const curateSection = document.getElementById('curate-section');
            if (curateSection) {
                const variantsGrid = document.getElementById('variants-grid');
                if (!variantsGrid || !variantsGrid.children.length) {
                    renderAodaiVariants(HERITAGE_ITEMS[0]);
                }
                curateSection.style.display = 'block';
                updateStepper(4);
                curateSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    }
}
