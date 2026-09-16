from __future__ import annotations

from html import escape
from pathlib import Path
import re

import streamlit as st

from .helpers import get_image_base64, render_html


DEFAULT_PALETTES: dict[str, list[str]] = {
    "BT_Hac_XP": ["#99a1a8", "#ccd5d8", "#6b7177", "#3f4551", "#1d1d29"],
    "HSBT_XP-300x300": ["#d3e0e3", "#afb8b1", "#434f49", "#788480", "#19211c"],
    "BHV_UU_XP1-600x600": ["#392a17", "#886a41", "#d8bd54", "#cac6c4", "#30598a"],
    "MB_2C_XP_31": ["#2d2927", "#d6d7d5", "#70808c", "#e1cb53", "#8a6e2f"],
    "BT010_2": ["#dee0e4", "#646d90", "#8c94ad", "#bcbfca", "#414768"],
    "binh-hoa-su-trang-ap-noi-hoa-sen-dat-vang-24k-bat-trang-cao-cap-anh-dai-dien": [
        "#f7f4ed",
        "#d4af37",
        "#997b2f",
        "#404040",
    ],
}


def get_palette_for_item(item: dict) -> list[str]:
    return DEFAULT_PALETTES.get(
        item.get("id", ""),
        ["#3b4856", "#87929e", "#d8dfd5", "#a47e5b"],
    )


# ==============================================================================
# 1. HEADER (web_ui/components/layout/header.html)
# ==============================================================================
def render_static_nav(root: Path, current_step: int) -> None:
    header_file = root / "web_ui" / "components" / "layout" / "header.html"
    html = header_file.read_text(encoding="utf-8")

    # Đổi logo link về Bước 1
    html = re.sub(r'href="\./index\.html"', 'href="?go=1"', html)

    # Đổi các bước trong nav-links thành thẻ <a> với query param ?go=X và cập nhật active/completed
    step_labels = [
        (1, "1. Chọn hiện vật"),
        (2, "2. Xem mô tả"),
        (3, "3. Đang tạo"),
        (4, "4. Chọn thiết kế"),
    ]

    new_nav_links: list[str] = []
    for step_num, label in step_labels:
        classes = ["stepper-item"]
        if step_num == current_step:
            classes.append("active")
        elif step_num < current_step:
            classes.append("completed")
        class_str = " ".join(classes)
        new_nav_links.append(
            f'<a class="{class_str}" id="step-{step_num}-btn" href="?go={step_num}"><span>{label}</span></a>'
        )

    stepper_html = '<span class="stepper-arrow">→</span>'.join(new_nav_links)
    html = re.sub(
        r'<ul class="nav-links">.*?</ul>',
        f'<div class="nav-links">{stepper_html}</div>',
        html,
        flags=re.S,
    )

    render_html(html)


# ==============================================================================
# 2. CATALOG / HERO (web_ui/components/sections/experience.html)
# ==============================================================================
HERITAGE_FILTERS: dict[str, list[str]] = {
    "BT_Hac_XP": ["all", "men-lam", "phat-giao"],
    "HSBT_XP-300x300": ["all", "men-ran", "phat-giao"],
    "BHV_UU_XP1-600x600": ["all", "men-lam", "phat-giao"],
    "MB_2C_XP_31": ["all", "trang-tri"],
    "BT010_2": ["all", "men-lam", "trang-tri"],
    "binh-hoa-su-trang-ap-noi-hoa-sen-dat-vang-24k-bat-trang-cao-cap-anh-dai-dien": ["all", "trang-tri"],
}

FILTER_CHIPS = (
    ("all", "Tất cả (6)"),
    ("men-ran", "Men rạn cổ"),
    ("men-lam", "Men lam"),
    ("phat-giao", "Đồ thờ & Phật giáo"),
    ("trang-tri", "Đề tài Trang trí"),
)


def render_static_catalog(
    root: Path,
    heritage_dir: Path,
    items: list[dict],
    selected_id: str,
    active_filter: str = "all",
) -> None:
    exp_file = root / "web_ui" / "components" / "sections" / "experience.html"
    html = exp_file.read_text(encoding="utf-8")

    # Cập nhật các nút filter chip thành link điều hướng ?filter=...
    chips_html = []
    for filter_key, label in FILTER_CHIPS:
        is_active = "active" if filter_key == active_filter else ""
        chips_html.append(
            f'<a class="filter-chip {is_active}" href="?filter={filter_key}"><span>{label}</span></a>'
        )
    html = re.sub(
        r'(<div class="filter-chips-container">)(.*?)(</div>)',
        rf'\1{"".join(chips_html)}\3',
        html,
        flags=re.S,
    )

    # Lọc danh sách hiện vật hiển thị
    filtered_items = [
        item for item in items
        if active_filter in HERITAGE_FILTERS.get(item["id"], ["all"])
    ]

    cards_html: list[str] = []
    for item in filtered_items:
        item_id = item["id"]
        is_selected = "selected" if item_id == selected_id else ""
        palette = get_palette_for_item(item)
        dots_html = "".join(
            f'<span class="glaze-dot" style="background-color: {color};" title="{color}"></span>'
            for color in palette
        )
        img_b64 = get_image_base64(heritage_dir / item["image_file"])

        card = f"""
        <article class="heritage-card {is_selected}" data-id="{escape(item_id)}">
            <div class="card-img-wrap">
                <span class="badge-glaze">Gốm Bát Tràng</span>
                <img src="{img_b64}" alt="{escape(item['name'])}" loading="lazy">
            </div>
            <div class="heritage-card-content">
                <div>
                    <div class="heritage-dynasty">{escape(item.get('era', 'Cổ truyền'))}</div>
                    <h3 class="heritage-title">{escape(item['name'])}</h3>
                    <p class="heritage-desc">{escape(item.get('category', 'Di sản văn hóa Bát Tràng'))}</p>
                </div>
                <div>
                    <div class="glaze-palette-box">
                        <span class="glaze-label">Màu men trích xuất</span>
                        <div class="glaze-dots">{dots_html}</div>
                    </div>
                    <a class="card-action-btn" href="?select={escape(item_id)}">
                        <span>Chiêm ngưỡng &amp; Tạo thiết kế</span>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                            <polyline points="12 5 19 12 12 19"></polyline>
                        </svg>
                    </a>
                </div>
            </div>
        </article>
        """
        cards_html.append(card)

    cards_grid_content = "\n".join(cards_html)
    html = re.sub(
        r'(<div class="cards-grid-6" id="heritage-cards-grid">)(.*?)(</div>)',
        rf'\1{cards_grid_content}\3',
        html,
        flags=re.S,
    )

    render_html(html)


# ==============================================================================
# 3. MODAL CHI TIẾT (web_ui/components/overlays/modals.html - #detail-modal)
# ==============================================================================
def render_static_detail(root: Path, heritage_dir: Path, item: dict) -> None:
    modals_file = root / "web_ui" / "components" / "overlays" / "modals.html"
    modals_html = modals_file.read_text(encoding="utf-8")

    # Trích xuất riêng khối #detail-modal
    match = re.search(
        r'(<div class="detail-modal-overlay"[^>]*id="detail-modal"[^>]*>.*?</div>\s*</div>\s*</div>)',
        modals_html,
        flags=re.S,
    )
    if not match:
        # Fallback tìm div bao quanh
        match = re.search(r'(<div class="detail-modal-overlay".*?</div>\s*</div>)', modals_html, flags=re.S)

    modal_chunk = match.group(0) if match else ""

    # Kích hoạt trạng thái active
    modal_chunk = modal_chunk.replace('class="detail-modal-overlay"', 'class="detail-modal-overlay active"')

    # Đổi nút close thành thẻ a về ?go=1
    modal_chunk = re.sub(
        r'<button class="modal-close-btn"[^>]*id="modal-close-btn"[^>]*>.*?</button>',
        '<a class="modal-close-btn" id="modal-close-btn" href="?go=1" aria-label="Quay lại">←</a>',
        modal_chunk,
        flags=re.S,
    )

    # Đổi nút generate CTA thành thẻ a về ?go=3
    modal_chunk = re.sub(
        r'<button class="modal-cta-btn"[^>]*id="generate-btn"[^>]*>(.*?)</button>',
        r'<a class="modal-cta-btn" id="generate-btn" href="?go=3">\1</a>',
        modal_chunk,
        flags=re.S,
    )

    # Inject dữ liệu hiện vật
    img_b64 = get_image_base64(heritage_dir / item["image_file"])
    palette = get_palette_for_item(item)
    dots_html = "".join(
        f'<span class="glaze-dot" style="background-color: {c}; width: 22px; height: 22px;" title="{c}"></span>'
        for c in palette
    )

    modal_chunk = re.sub(
        r'<img id="modal-img"[^>]*>',
        f'<img id="modal-img" alt="{escape(item["name"])}" src="{img_b64}">',
        modal_chunk,
    )
    modal_chunk = re.sub(
        r'<h3 class="modal-title"[^>]*id="modal-title">.*?</h3>',
        f'<h3 class="modal-title" id="modal-title">{escape(item["name"])}</h3>',
        modal_chunk,
    )
    modal_chunk = re.sub(
        r'<div class="modal-meta"[^>]*id="modal-meta">.*?</div>',
        f'<div class="modal-meta" id="modal-meta">{escape(item.get("subtitle", item.get("era", "")))}</div>',
        modal_chunk,
    )
    desc_text = item.get("category", "")
    if item.get("source_short"):
        desc_text += f" · {item['source_short']}"
    modal_chunk = re.sub(
        r'<div class="modal-cultural-desc"[^>]*id="modal-desc">.*?</div>',
        f'<div class="modal-cultural-desc" id="modal-desc">{escape(desc_text)}</div>',
        modal_chunk,
    )
    modal_chunk = re.sub(
        r'<div class="glaze-dots"[^>]*id="modal-glaze-dots">.*?</div>',
        f'<div class="glaze-dots" id="modal-glaze-dots">{dots_html}</div>',
        modal_chunk,
    )

    render_html(modal_chunk)


# ==============================================================================
# 4. CURATE SECTION & PASSPORT MODAL (curate.html & modals.html - #passport-modal)
# ==============================================================================
def render_static_curate(root: Path, item: dict, variants: list[dict]) -> None:
    template = (root / "web_ui" / "components" / "sections" / "curate.html").read_text(
        encoding="utf-8"
    )

    cards: list[str] = []
    for index, variant in enumerate(variants[:4]):
        var_idx = index + 1
        img_rel = variant.get("design_path", "")
        img_path = root / img_rel if img_rel else Path("")
        image_b64 = get_image_base64(img_path)
        similarity = f'{float(variant.get("similarity_pattern_vs_ceramic", 0)) * 100:.1f}%'
        layout_name = escape(variant.get("layout_label", f"Bố cục {var_idx}"))

        cards.append(
            f"""
            <article class="variant-card" tabindex="0" role="button">
                <div class="variant-img-wrap">
                    <img class="variant-img" src="{image_b64}" alt="Biến thể {var_idx} - {layout_name}">
                    <span class="similarity-badge">★ {similarity}</span>
                </div>
                <div class="variant-layer" aria-hidden="true"></div>
                <div class="variant-info">
                    <span class="variant-tagline">ĐỘ TƯƠNG ĐỒNG THAM KHẢO · {similarity}</span>
                    <h4 class="variant-name">Biến thể {var_idx}</h4>
                    <a class="variant-btn-select" href="?choose={var_idx}">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                            <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                            <polyline points="2 17 12 22 22 17"></polyline>
                            <polyline points="2 12 12 17 22 12"></polyline>
                        </svg>
                        <span>Xem hộ chiếu thiết kế →</span>
                    </a>
                </div>
            </article>
            """
        )

    template = template.replace(' style="display: none;"', "")
    template = re.sub(
        r'<h2 class="curate-title"[^>]*>.*?</h2>',
        f'<h2 class="curate-title">Bộ Sưu Tập Áo Dài: {escape(item["name"])}</h2>',
        template,
        flags=re.S,
    )
    template = re.sub(
        r'<p class="curate-subtitle"[^>]*>.*?</p>',
        '<p class="curate-subtitle">Bốn thiết kế được kiến tạo từ hoa văn hiện vật bạn đã chọn.</p>',
        template,
        flags=re.S,
    )
    template = re.sub(
        r'(<div class="variants-grid"[^>]*>).*?(</div>)',
        rf'\1{"".join(cards)}\2',
        template,
        count=1,
        flags=re.S,
    )

    render_html(template)


def render_static_passport(
    root: Path, heritage_dir: Path, item: dict, variant: dict
) -> None:
    modals_file = root / "web_ui" / "components" / "overlays" / "modals.html"
    modals_html = modals_file.read_text(encoding="utf-8")

    match = re.search(
        r'(<div class="passport-modal-overlay"[^>]*id="passport-modal"[^>]*>.*?</div>\s*</div>\s*</div>)',
        modals_html,
        flags=re.S,
    )
    if not match:
        return

    passport_chunk = match.group(0)
    passport_chunk = passport_chunk.replace(
        'class="passport-modal-overlay"', 'class="passport-modal-overlay active"'
    )

    # Close button -> thẻ a
    passport_chunk = re.sub(
        r'<button class="modal-close-btn"[^>]*id="passport-close-btn"[^>]*>.*?</button>',
        '<a class="modal-close-btn" id="passport-close-btn" href="?go=4" style="position: static; background: rgba(255,255,255,0.15); color: #fff; text-decoration: none; display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%;" aria-label="Đóng">✕</a>',
        passport_chunk,
        flags=re.S,
    )

    # Reset button -> thẻ a về ?go=1
    passport_chunk = re.sub(
        r'<button class="btn-reset-studio"[^>]*id="btn-reset-studio"[^>]*>(.*?)</button>',
        r'<a class="btn-reset-studio" id="btn-reset-studio" href="?go=1" style="text-decoration: none; display: inline-flex; align-items: center; justify-content: center;">\1</a>',
        passport_chunk,
        flags=re.S,
    )

    # Đổ ảnh và thông số
    aodai_b64 = get_image_base64(root / variant.get("design_path", ""))
    origin_b64 = get_image_base64(heritage_dir / item["image_file"])
    sim_val = float(variant.get("similarity_pattern_vs_ceramic", 0.75))
    sim_pct = f"{sim_val * 100:.1f}%"
    layout_name = escape(variant.get("layout_label", "Bố cục mẫu"))
    var_num = variant.get("variant_index", 1)

    palette_hexes = [
        c for c in variant.get("source_palette", "").split(";") if c.startswith("#")
    ]
    if not palette_hexes:
        palette_hexes = get_palette_for_item(item)
    dots_html = "".join(
        f'<span class="glaze-dot" style="background-color: {c}; width: 22px; height: 22px;" title="{c}"></span>'
        for c in palette_hexes
    )

    passport_chunk = re.sub(
        r'<img class="passport-aodai-img"[^>]*>',
        f'<img class="passport-aodai-img" id="passport-aodai-img" alt="Thiết kế đã chọn" src="{aodai_b64}">',
        passport_chunk,
    )
    passport_chunk = re.sub(
        r'<img class="passport-compare-thumb"[^>]*>',
        f'<img class="passport-compare-thumb" id="passport-origin-thumb" alt="Hiện vật gốc" src="{origin_b64}">',
        passport_chunk,
    )
    passport_chunk = re.sub(
        r'<div id="passport-origin-name"[^>]*>.*?</div>',
        f'<div id="passport-origin-name" style="font-size: 12px; color: var(--text-muted);">{escape(item["name"])}</div>',
        passport_chunk,
    )
    passport_chunk = re.sub(
        r'<div [^>]*id="passport-similarity-val"[^>]*>.*?</div>',
        f'<div style="font-size: 24px; font-weight: 800; color: #15803d;" id="passport-similarity-val">{sim_pct} (Tham khảo)</div>',
        passport_chunk,
    )
    passport_chunk = re.sub(
        r'<div class="passport-field-value"[^>]*id="passport-variant-title">.*?</div>',
        f'<div class="passport-field-value" id="passport-variant-title">Biến thể {var_num} — {layout_name}</div>',
        passport_chunk,
    )
    passport_chunk = re.sub(
        r'<div class="passport-field-value"[^>]*id="passport-layout">.*?</div>',
        f'<div class="passport-field-value" id="passport-layout">{layout_name}</div>',
        passport_chunk,
    )
    passport_chunk = re.sub(
        r'<div class="passport-field-value"[^>]*id="passport-palette-mode">.*?</div>',
        f'<div class="passport-field-value" id="passport-palette-mode">Màu men gốc</div>',
        passport_chunk,
    )
    passport_chunk = re.sub(
        r'<div class="glaze-dots"[^>]*id="passport-palette-dots"[^>]*>.*?</div>',
        f'<div class="glaze-dots" id="passport-palette-dots" style="margin-top: 6px;">{dots_html}</div>',
        passport_chunk,
    )

    render_html(passport_chunk)


# ==============================================================================
# 5. FOOTER (web_ui/components/layout/footer.html)
# ==============================================================================
def render_static_footer(root: Path) -> None:
    footer_file = root / "web_ui" / "components" / "layout" / "footer.html"
    html = footer_file.read_text(encoding="utf-8")
    html = re.sub(r'<a\s+[^>]*id="footer-link-step1"[^>]*>', '<a href="?go=1" id="footer-link-step1">', html)
    html = re.sub(r'<a\s+[^>]*id="footer-link-step4"[^>]*>', '<a href="?go=4" id="footer-link-step4">', html)
    render_html(html)


# ==============================================================================
# 3.5. VISUAL PIPELINE RUNNER MODAL (modals.html - #pipeline-modal)
# ==============================================================================
def render_static_pipeline(root: Path, current_heritage: dict, progress: int = 100) -> None:
    modals_file = root / "web_ui" / "components" / "overlays" / "modals.html"
    modals_html = modals_file.read_text(encoding="utf-8")

    match = re.search(
        r'(<div class="pipeline-modal-overlay"[^>]*id="pipeline-modal"[^>]*>.*?</div>\s*</div>\s*</div>)',
        modals_html,
        flags=re.S,
    )
    if not match:
        return

    pipe_chunk = match.group(0)
    pipe_chunk = pipe_chunk.replace('class="pipeline-modal-overlay"', 'class="pipeline-modal-overlay active"')

    # Đổi close button thành link quay lại Bước 2
    pipe_chunk = re.sub(
        r'<button(\s+[^>]*id="pipeline-close-btn"[^>]*)>(.*?)</button>',
        r'<a\1 href="?go=2">\2</a>',
        pipe_chunk,
        flags=re.S,
    )

    # Đổ ảnh 4 stage từ outputs/variants/ tương ứng với hiện vật
    hid = current_heritage["id"]
    variants_dir = root / "outputs" / "variants"

    canny_path = variants_dir / f"{hid}_01_canny.png"
    pattern_path = variants_dir / f"{hid}_V1_pattern.png"
    comp_path = variants_dir / f"{hid}_V1_aodai_raw.png"
    final_path = variants_dir / f"{hid}_V1_aodai.png"

    canny_b64 = get_image_base64(canny_path)
    pattern_b64 = get_image_base64(pattern_path)
    comp_b64 = get_image_base64(comp_path)
    final_b64 = get_image_base64(final_path)

    pipe_chunk = re.sub(r'<img id="stage-img-1"[^>]*>', f'<img id="stage-img-1" alt="Canny Lineart" src="{canny_b64}">', pipe_chunk)
    pipe_chunk = re.sub(r'<img id="stage-img-2"[^>]*>', f'<img id="stage-img-2" alt="Pattern Tile" src="{pattern_b64}">', pipe_chunk)
    pipe_chunk = re.sub(r'<img id="stage-img-3"[^>]*>', f'<img id="stage-img-3" alt="Garment Composite" src="{comp_b64}">', pipe_chunk)
    pipe_chunk = re.sub(r'<img id="stage-img-4"[^>]*>', f'<img id="stage-img-4" alt="Final Design" src="{final_b64}">', pipe_chunk)

    # Đánh dấu stage card done và update progress bar
    pipe_chunk = pipe_chunk.replace('id="stage-card-1"', 'id="stage-card-1" class="pipeline-stage-card done"')
    pipe_chunk = pipe_chunk.replace('id="stage-card-2"', 'id="stage-card-2" class="pipeline-stage-card done"')
    pipe_chunk = pipe_chunk.replace('id="stage-card-3"', 'id="stage-card-3" class="pipeline-stage-card done"')
    pipe_chunk = pipe_chunk.replace('id="stage-card-4"', 'id="stage-card-4" class="pipeline-stage-card done"')
    pipe_chunk = re.sub(r'id="pipeline-percentage">.*?</div>', f'id="pipeline-percentage">{progress}%</div>', pipe_chunk)
    pipe_chunk = re.sub(
        r'id="pipeline-progress-bar"[^>]*>',
        f'id="pipeline-progress-bar" style="--progress: {progress/100}; width: {progress}%;">',
        pipe_chunk,
    )
    pipe_chunk = re.sub(
        r'id="pipeline-status-text">.*?</p>',
        'id="pipeline-status-text">Thiết kế áo dài đã sẵn sàng để bạn chiêm ngưỡng và chọn lựa.</p>',
        pipe_chunk,
    )

    # Hiển thị footer buttons với link chuyển bước
    pipe_chunk = re.sub(
        r'<button(\s+[^>]*id="btn-stay-inspector"[^>]*)>(.*?)</button>',
        r'<a\1 href="?go=2" style="text-decoration: none; display: inline-flex; align-items: center; justify-content: center;">\2</a>',
        pipe_chunk,
        flags=re.S,
    )
    pipe_chunk = re.sub(
        r'<button(\s+[^>]*id="btn-modal-goto-curate"[^>]*)>(.*?)</button>',
        r'<a\1 href="?go=4" style="text-decoration: none; display: inline-flex; align-items: center; justify-content: center;">\2</a>',
        pipe_chunk,
        flags=re.S,
    )
    pipe_chunk = pipe_chunk.replace(
        'id="pipeline-modal-footer" style="display: none;"',
        'id="pipeline-modal-footer" style="display: flex;"',
    )

    render_html(pipe_chunk)


# ==============================================================================
# MAIN APP CONTROLLER
# ==============================================================================
def render_app(
    root: Path,
    heritage_dir: Path,
    heritage_items: list[dict],
    heritage_map: dict[str, dict],
) -> None:
    ROOT = root
    HERITAGE_DIR = heritage_dir
    HERITAGE_ITEMS = heritage_items
    HERITAGE_MAP = heritage_map

    # Bắt query parameters từ URL
    selected = st.query_params.get("select")
    requested_step = st.query_params.get("go")
    chosen = st.query_params.get("choose")
    filter_param = st.query_params.get("filter")

    if filter_param:
        st.session_state.active_filter = filter_param

    if selected in HERITAGE_MAP:
        st.session_state.selected_id = selected
        st.session_state.step = 2
        st.session_state.chosen_variant = None
        st.session_state.show_passport = False
        st.session_state.generated_variants = []
        st.query_params.clear()
    elif requested_step in {"1", "2", "3", "4"}:
        st.session_state.step = int(requested_step)
        st.query_params.clear()
    elif chosen and chosen.isdigit():
        index = int(chosen) - 1
        variants = st.session_state.generated_variants
        if 0 <= index < len(variants):
            st.session_state.chosen_variant = variants[index]
            st.session_state.show_passport = True
            st.session_state.step = 4
        st.query_params.clear()

    current_heritage = HERITAGE_MAP.get(st.session_state.selected_id, HERITAGE_ITEMS[0])
    step = st.session_state.step
    current_filter = st.session_state.get("active_filter", "all")

    # 1. Luôn hiển thị Navbar
    render_static_nav(ROOT, step)

    # 2. View theo từng bước
    if step == 1:
        render_static_catalog(
            ROOT, HERITAGE_DIR, HERITAGE_ITEMS, st.session_state.selected_id, current_filter
        )

    elif step == 2:
        # Render nền catalog mờ phía sau modal để giữ hiệu ứng overlay chân thực
        render_static_catalog(
            ROOT, HERITAGE_DIR, HERITAGE_ITEMS, st.session_state.selected_id, current_filter
        )
        render_static_detail(ROOT, HERITAGE_DIR, current_heritage)

    elif step == 3:
        # Nền catalog mờ phía sau pipeline modal
        render_static_catalog(
            ROOT, HERITAGE_DIR, HERITAGE_ITEMS, st.session_state.selected_id, current_filter
        )
        from generation.stable_diffusion import runtime_status

        ready, detail = runtime_status()
        if not ready:
            st.error(f"Chưa thể chạy mô hình trên máy này. {detail}")
            return

        progress_bar = st.progress(0)
        progress_label = st.empty()

        def update_progress(value: int, label: str) -> None:
            progress_bar.progress(value)
            progress_label.caption(label)

        try:
            from generation.streamlit_runner import generate_design_set

            st.session_state.generated_variants = generate_design_set(
                current_heritage["id"], update_progress
            )
            st.session_state.step = 4
            st.rerun()
        except Exception as exc:
            st.error("Quá trình tạo thiết kế chưa hoàn tất. Hãy kiểm tra mô hình và GPU rồi thử lại.")
            st.exception(exc)

    elif step == 4:
        variants = st.session_state.generated_variants
        if not variants:
            st.warning("Chưa có thiết kế nào được tạo trong phiên này. Hãy quay lại hiện vật để bắt đầu.")
        else:
            render_static_curate(ROOT, current_heritage, variants)

        # Hiển thị Design Passport Modal nếu đang chọn xem biến thể
        if st.session_state.show_passport and st.session_state.chosen_variant is not None:
            render_static_passport(ROOT, HERITAGE_DIR, current_heritage, st.session_state.chosen_variant)

    # 3. Luôn hiển thị Footer
    render_static_footer(ROOT)
