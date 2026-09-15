from __future__ import annotations

from html import escape
from pathlib import Path
import re

import streamlit as st

from .helpers import get_image_base64

PALETTES = (
    ("#3b4856", "#87929e", "#d8dfd5", "#a47e5b"),
    ("#1d4ed8", "#3b82f6", "#d97706", "#f1f5f9"),
    ("#475569", "#94a3b8", "#e2e8f0", "#b45309"),
    ("#785d38", "#b4976a", "#e8dfcc", "#1e293b"),
    ("#2d4059", "#4a7c59", "#de9b72", "#eae3d2"),
    ("#334155", "#64748b", "#c2410c", "#f8fafc"),
)


def render_static_nav(step: int) -> None:
    labels = ("1. Chọn hiện vật", "2. Xem hiện vật", "3. Đang tạo", "4. Chọn thiết kế")
    items = "".join(
        f'<a class="stepper-item {"active" if index + 1 == step else ""}" href="?go={index + 1}"><span>{label}</span></a>'
        for index, label in enumerate(labels)
    )
    st.markdown(
        f'''<div class="framer-nav-wrapper"><header class="framer-navbar"><a href="?go=1" class="nav-logo"><div class="nav-logo-icon"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg></div><span>DIGITAL HERITAGE</span></a><nav><div class="nav-links">{items}</div></nav></header></div>''',
        unsafe_allow_html=True,
    )


def render_static_catalog(heritage_dir: Path, items: list[dict]) -> None:
    cards = []
    for index, item in enumerate(items):
        dots = "".join(f'<span class="glaze-dot" style="background-color:{color}"></span>' for color in PALETTES[index])
        image = get_image_base64(heritage_dir / item["image_file"])
        cards.append(
            f'''<article class="heritage-card"><div class="card-img-wrap"><span class="badge-glaze">Gốm Bát Tràng</span><img src="{image}" alt="{escape(item["name"])}" loading="lazy"></div><div class="heritage-card-content"><div><div class="heritage-dynasty">{escape(item["era"])}</div><h3 class="heritage-title">{escape(item["name"])}</h3><p class="heritage-desc">{escape(item["category"])}</p></div><div><div class="glaze-palette-box"><span class="glaze-label">Màu men trích xuất</span><div class="glaze-dots">{dots}</div></div><a class="card-action-btn" href="?select={escape(item["id"])}"><span>Chiêm ngưỡng &amp; Tạo thiết kế</span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg></a></div></div></article>'''
        )
    st.markdown(
        f'''<main class="main-content-flow"><section class="hero-section container"><div class="hero-editorial-grid"><div class="hero-left-col"><h1 class="hero-title-editorial">Tái sinh Hoa văn Gốm Bát Tràng<br>trên <span class="highlight">Tà Áo Dài Đương đại</span></h1><p class="hero-desc-editorial">Hành trình sáng tạo từ hiện vật gốm Bát Tràng đến những thiết kế áo dài được kiến tạo riêng từ linh hồn di sản.</p></div></div></section><section class="showcase-section container" id="hien-vat"><div class="showcase-header-bar"><div class="showcase-title-group"><h2>Kho báu Men sắc &amp; Họa phẩm</h2><p><span>Sáu hiện vật tiêu biểu đợt tuyển chọn</span><span>•</span><span class="museum-badge">● Nguyên bản viện bảo tàng &amp; tư liệu di sản</span></p></div></div><div class="filter-chips-container"><span class="filter-chip active">Tất cả (6)</span><span class="filter-chip">Men rạn cổ</span><span class="filter-chip">Men lam</span><span class="filter-chip">Đồ thờ &amp; Phật giáo</span><span class="filter-chip">Đề tài Trang trí</span></div><div class="cards-grid-6">{"".join(cards)}</div></section></main>''',
        unsafe_allow_html=True,
    )


def render_static_detail(heritage_dir: Path, item: dict) -> None:
    image = get_image_base64(heritage_dir / item["image_file"])
    st.markdown(
        f'''<div class="detail-modal-overlay active"><div class="detail-modal-card"><a class="modal-close-btn" href="?go=1" aria-label="Quay lại">←</a><div class="modal-grid"><div class="modal-img-col"><img alt="{escape(item["name"])}" src="{image}"></div><div class="modal-info-col"><div><span class="modal-step-badge">Bước 2 — Chiêm ngưỡng hiện vật</span><h3 class="modal-title">{escape(item["name"])}</h3><div class="modal-meta">{escape(item["subtitle"])}</div><div class="glaze-palette-box"><span class="glaze-label">Bảng màu men trích xuất</span><div class="glaze-dots">{"".join(f'<span class="glaze-dot" style="background-color:{color}"></span>' for color in PALETTES[0])}</div></div></div><a class="modal-cta-btn" href="?go=3"><span>TẠO BỘ 4 THIẾT KẾ ÁO DÀI</span></a></div></div></div></div>''',
        unsafe_allow_html=True,
    )


def render_static_curate(root: Path, item: dict, variants: list[dict]) -> None:
    template = (root / "webtestdesign" / "components" / "sections" / "curate.html").read_text(encoding="utf-8")
    cards = []
    for index, variant in enumerate(variants[:4]):
        image = get_image_base64(root / variant.get("design_path", ""))
        similarity = f'{float(variant.get("similarity_pattern_vs_ceramic", 0)) * 100:.1f}%'
        label = escape(variant.get("layout_label", f"Biến thể {index + 1}"))
        cards.append(
            f'''<article class="variant-card"><div class="variant-img-wrap"><img class="variant-img" src="{image}" alt="{label}"><span class="similarity-badge">★ {similarity}</span></div><div class="variant-layer"></div><div class="variant-info"><span class="variant-tagline">ĐỘ TƯƠNG ĐỒNG THAM KHẢO · {similarity}</span><h4 class="variant-name">Biến thể {index + 1}</h4><a class="variant-btn-select" href="?choose={index + 1}"><span>Xem hộ chiếu thiết kế →</span></a></div></article>'''
        )
    template = template.replace(' style="display: none;"', '')
    template = re.sub(r'<h2 class="curate-title"[^>]*>.*?</h2>', f'<h2 class="curate-title">Bộ Sưu Tập Áo Dài: {escape(item["name"])}</h2>', template, flags=re.S)
    template = re.sub(r'<p class="curate-subtitle"[^>]*>.*?</p>', '<p class="curate-subtitle">Bốn thiết kế được kiến tạo từ hoa văn hiện vật bạn đã chọn.</p>', template, flags=re.S)
    template = re.sub(r'(<div class="variants-grid"[^>]*>).*?(</div>)', rf'\1{"".join(cards)}\2', template, count=1, flags=re.S)
    st.markdown(template, unsafe_allow_html=True)


def render_static_footer(root: Path) -> None:
    template = (root / "webtestdesign" / "components" / "layout" / "footer.html").read_text(encoding="utf-8")
    st.markdown(template, unsafe_allow_html=True)


def render_app(root: Path, heritage_dir: Path, heritage_items: list[dict], heritage_map: dict[str, dict]) -> None:
    ROOT = root
    HERITAGE_DIR = heritage_dir
    HERITAGE_ITEMS = heritage_items
    HERITAGE_MAP = heritage_map
    selected = st.query_params.get("select")
    requested_step = st.query_params.get("go")
    chosen = st.query_params.get("choose")
    if selected in HERITAGE_MAP:
        st.session_state.selected_id = selected
        st.session_state.step = 2
        st.session_state.chosen_variant = None
        st.session_state.show_passport = False
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


    # ==============================================================================
    # TOP NAVBAR
    # ==============================================================================
    step = st.session_state.step
    render_static_nav(step)


    # ==============================================================================
    # VIEW 1 — CHỌN HIỆN VẬT
    # ==============================================================================
    if st.session_state.step == 1:
        render_static_catalog(HERITAGE_DIR, HERITAGE_ITEMS)


    # ==============================================================================
    # VIEW 2 — XEM HIỆN VẬT
    # ==============================================================================
    elif st.session_state.step == 2:
        render_static_detail(HERITAGE_DIR, current_heritage)


    # ==============================================================================
    # VIEW 3 — ĐANG TẠO THIẾT KẾ
    # Bỏ hoàn toàn hiển thị thông số kỹ thuật và weight (0.85, 0.65, ...)
    # ==============================================================================
    elif st.session_state.step == 3:
        img_path = HERITAGE_DIR / current_heritage["image_file"]
        img_b64 = get_image_base64(img_path)

        st.markdown(
            f"""
            <div class="generating-container">
                <img class="thumb-avatar" src="{img_b64}" alt="{current_heritage['name']}"/>
                <div class="view-step-label">BƯỚC 3 — ĐANG TẠO THIẾT KẾ</div>
                <div class="view-main-title" style="font-size: 1.9rem;">{current_heritage['name']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        from generation.stable_diffusion import runtime_status

        ready, _ = runtime_status()
        if not ready:
            st.error("Chưa thể chạy mô hình trên máy này. Hãy hoàn tất cấu hình GPU rồi thử lại.")
            if st.button("← Quay lại hiện vật", key="btn_generation_back"):
                st.session_state.step = 2
                st.rerun()
        else:
            progress_bar = st.progress(0)
            progress_text = st.empty()

            def update_progress(value: int, label: str) -> None:
                progress_bar.progress(value)
                progress_text.markdown(f"<div class='btn-sub-note'>{label}</div>", unsafe_allow_html=True)

            try:
                from generation.streamlit_runner import generate_design_set

                st.session_state.generated_variants = generate_design_set(
                    st.session_state.selected_id, update_progress
                )
                st.session_state.step = 4
                st.rerun()
            except Exception:
                st.error("Quá trình tạo thiết kế chưa hoàn tất. Hãy kiểm tra mô hình và GPU rồi thử lại.")
                if st.button("← Quay lại hiện vật", key="btn_generation_failed_back"):
                    st.session_state.step = 2
                    st.rerun()


    # ==============================================================================
    # VIEW 4 — CHỌN THIẾT KẾ & DESIGN PASSPORT
    # UI Rules:
    # - Gallery chỉ hiển thị ảnh áo dài được sinh (không overlay bình gốc).
    # - Passport hiển thị lớn ảnh đã chọn, thông tin nguồn ngắn và similarity dạng tham khảo.
    # - Ẩn mã BT00x khỏi chữ hiển thị.
    # - Không ghi và không hiển thị audit log.
    # ==============================================================================
    elif st.session_state.step == 4:
        variants = st.session_state.generated_variants
        if not variants:
            st.warning("Chưa có thiết kế nào được tạo trong phiên này. Hãy quay lại hiện vật để bắt đầu.")
        else:
            render_static_curate(ROOT, current_heritage, variants)
        # DESIGN PASSPORT DRAWER
        if st.session_state.show_passport and st.session_state.chosen_variant is not None:
            c_var = st.session_state.chosen_variant
            var_idx = int(c_var.get("variant_index", 1))
            layout_name = c_var.get("layout_label", "Bố cục mẫu")
            sim_val = float(c_var.get("similarity_pattern_vs_ceramic", 0.75))
            sim_pct = int(round(sim_val * 100))
            palette_hexes = [c for c in c_var.get("source_palette", "").split(";") if c.startswith("#")]
            aodai_b64 = get_image_base64(ROOT / c_var.get("design_path", ""))

            st.markdown("---")
            st.markdown(
                f"""
                <div class="passport-overlay">
                    <div class="passport-header-bar">
                        <div>
                            <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.06em;">THIẾT KẾ CỦA BẠN</div>
                            <div class="passport-modal-title">{current_heritage['name']}</div>
                        </div>
                        <div style="font-size: 0.82rem; color: #CBD5E1;">
                            Biến thể {var_idx} / 4 · {layout_name}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            p_left, p_right = st.columns([1, 1], gap="large")

            with p_left:
                st.markdown(
                    f"""
                    <div style="border-radius: 16px; overflow: hidden; border: 1px solid #E2E8F0; box-shadow: 0 4px 16px rgba(0,0,0,0.06);">
                        <img src="{aodai_b64}" style="width:100%; max-height: 520px; object-fit: contain; background: #FAF9F6;"/>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with p_right:
                swatch_html = "".join([f'<span class="color-swatch" style="background: {c};" title="{c}"></span>' for c in palette_hexes])
                st.markdown(
                    f"""
                    <div class="view-main-title" style="font-size: 1.8rem; margin-bottom: 0.4rem;">{current_heritage['name']}</div>
                    <div style="font-size: 0.88rem; color: #64748B; margin-bottom: 1rem;">{current_heritage['subtitle']}</div>

                    <div style="font-size: 0.9rem; color: #334155; line-height: 1.6; margin-bottom: 14px;">
                        Thiết kế áo dài đương đại được kiến tạo từ hoa văn gốm Bát Tràng theo bố cục <strong>{layout_name}</strong>.
                        Kỹ thuật ghép tất định đảm bảo dáng áo chuẩn mực và hoa văn ôm nếp vải tự nhiên.
                    </div>

                    <div class="metric-score-box">
                        <div class="metric-title">MỨC ĐỘ GỢI NHỚ HOA VĂN GỐC</div>
                        <div class="metric-value-huge">{sim_pct}%</div>
                        <div style="width: 100%; background: #DBEAFE; height: 8px; border-radius: 999px; overflow: hidden; margin-bottom: 8px;">
                            <div style="width: {sim_pct}%; background: #2563EB; height: 100%;"></div>
                        </div>
                        <div class="metric-subnote">
                            *Chỉ mang tính tham khảo, không phải điểm đạt hoặc không đạt.
                            Đo bằng tương đồng thị giác CLIP giữa hoa văn sinh ra và hoa văn hiện vật gốc.*
                        </div>
                    </div>

                    <div style="margin-bottom: 14px;">
                        <div style="font-size: 0.8rem; font-weight: 600; color: #475569; text-transform: uppercase;">Bảng màu hiện vật</div>
                        <div class="color-swatch-bar">{swatch_html}</div>
                    </div>

                    <div style="font-size: 0.78rem; color: #64748B; margin-bottom: 20px;">
                        Nguồn tư liệu: <em>{current_heritage['source_short']}</em>.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                b_col1, b_col2 = st.columns(2)
                with b_col1:
                    if st.button("Tạo thiết kế khác ↺", key="btn_reloop", use_container_width=True, type="primary"):
                        st.session_state.step = 1
                        st.session_state.chosen_variant = None
                        st.session_state.show_passport = False
                        st.rerun()
                with b_col2:
                    if st.button("Đóng Passport ✕", key="btn_close_passport", use_container_width=True):
                        st.session_state.show_passport = False
                        st.rerun()

    render_static_footer(ROOT)
