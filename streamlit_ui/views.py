from __future__ import annotations

from pathlib import Path

import streamlit as st

from .helpers import get_image_base64


def render_app(root: Path, heritage_dir: Path, heritage_items: list[dict], heritage_map: dict[str, dict]) -> None:
    ROOT = root
    HERITAGE_DIR = heritage_dir
    HERITAGE_ITEMS = heritage_items
    HERITAGE_MAP = heritage_map
    current_heritage = HERITAGE_MAP.get(st.session_state.selected_id, HERITAGE_ITEMS[0])


    # ==============================================================================
    # TOP NAVBAR
    # ==============================================================================
    step = st.session_state.step
    p1_cls = "active" if step == 1 else ("completed" if step > 1 else "")
    p2_cls = "active" if step == 2 else ("completed" if step > 2 else "")
    p3_cls = "active" if step == 3 else ("completed" if step > 3 else "")
    p4_cls = "active" if step == 4 else ""

    st.markdown(
        f"""
        <div class="top-navbar">
            <div class="brand-logo">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M8 2h8l2 5-3 6v7a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2v-7l-3-6 2-5z"/>
                    <line x1="8" y1="2" x2="16" y2="2"/>
                    <line x1="12" y1="13" x2="12" y2="20"/>
                </svg>
                <div>
                    <div class="brand-title">DIGITAL HERITAGE</div>
                    <div class="brand-subtitle">Di Sản Số · Gốm Bát Tràng</div>
                </div>
            </div>
            <div class="steps-nav">
                <span class="step-pill {p1_cls}">{'✓ ' if step > 1 else '1 '}Chọn hiện vật</span>
                <span class="step-divider">—</span>
                <span class="step-pill {p2_cls}">{'✓ ' if step > 2 else '2 '}Xem hiện vật</span>
                <span class="step-divider">—</span>
                <span class="step-pill {p3_cls}">{'✓ ' if step > 3 else '3 '}Đang tạo</span>
                <span class="step-divider">—</span>
                <span class="step-pill {p4_cls}">4 Chọn thiết kế</span>
            </div>
            <div>
                <span class="badge-mvp">MVP v6.1</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


    # ==============================================================================
    # VIEW 1 — CHỌN HIỆN VẬT
    # ==============================================================================
    if st.session_state.step == 1:
        st.markdown('<div class="view-step-label">BƯỚC 1 — CHỌN HIỆN VẬT</div>', unsafe_allow_html=True)
        st.markdown('<div class="view-main-title">Tái Sinh Di Sản Số</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="view-description">'
            'Chọn một hiện vật gốm Bát Tràng để bắt đầu hành trình tái sinh hoa văn thành thiết kế áo dài đương đại.'
            '</div>',
            unsafe_allow_html=True,
        )

        cols = st.columns(3)
        for idx, item in enumerate(HERITAGE_ITEMS):
            col = cols[idx % 3]
            with col:
                img_path = HERITAGE_DIR / item["image_file"]
                img_b64 = get_image_base64(img_path)

                st.markdown(
                    f"""
                    <div class="heritage-card">
                        <div class="card-img-wrap">
                            <img src="{img_b64}" alt="{item['name']}"/>
                        </div>
                        <div class="card-body">
                            <span class="era-tag">{item['era']}</span>
                            <div class="card-title">{item['name']}</div>
                            <div class="card-desc">{item['category']}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Khám phá hiện vật", key=f"btn_select_{item['id']}", use_container_width=True):
                    st.session_state.selected_id = item["id"]
                    st.session_state.step = 2
                    st.session_state.chosen_variant = None
                    st.session_state.show_passport = False
                    st.rerun()
                st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)


    # ==============================================================================
    # VIEW 2 — XEM HIỆN VẬT
    # ==============================================================================
    elif st.session_state.step == 2:
        if st.button("← Quay lại danh sách", key="btn_back_to_list"):
            st.session_state.step = 1
            st.rerun()

        st.markdown('<div class="view-step-label">BƯỚC 2 — XEM HIỆN VẬT</div>', unsafe_allow_html=True)

        c_left, c_right = st.columns([1.1, 1.3], gap="large")

        with c_left:
            img_path = HERITAGE_DIR / current_heritage["image_file"]
            img_b64 = get_image_base64(img_path)
            st.markdown(
                f"""
                <div class="detail-img-container">
                    <img src="{img_b64}" alt="{current_heritage['name']}"/>
                </div>
                <div class="detail-tag-bar">
                    <span class="pill-tag accent">{current_heritage['era']}</span>
                    <span class="pill-tag">Bát Tràng</span>
                    <span class="pill-tag">Gốm truyền thống</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c_right:
            st.markdown(
                f"""
                <div class="view-main-title" style="font-size: 2.1rem; margin-bottom: 0.3rem;">{current_heritage['name']}</div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("TẠO THIẾT KẾ →", key="btn_start_generate", use_container_width=True, type="primary"):
                st.session_state.generated_variants = []
                st.session_state.step = 3
                st.rerun()

            st.markdown(
                '<div class="btn-sub-note">Hệ thống sẽ tạo một số phương án để bạn chọn.</div>',
                unsafe_allow_html=True,
            )


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
        st.markdown('<div class="view-step-label">BƯỚC 4 — CHỌN THIẾT KẾ</div>', unsafe_allow_html=True)
        st.markdown('<div class="view-main-title">4 Thiết Kế Áo Dài</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="view-description">Từ hoa văn: <strong>{current_heritage["name"]}</strong>. '
            'Bấm "Chọn thiết kế này" để xem chi tiết Design Passport và đối chiếu độ tương đồng.</div>',
            unsafe_allow_html=True,
        )

        variants = st.session_state.generated_variants

        if not variants:
            st.warning("Chưa có thiết kế nào được tạo trong phiên này. Hãy quay lại hiện vật để bắt đầu.")
        else:
            v_cols = st.columns(4)
            for idx, var in enumerate(variants[:4]):
                col = v_cols[idx]
                with col:
                    design_rel_path = var.get("design_path", "")
                    design_file = ROOT / design_rel_path
                    design_b64 = get_image_base64(design_file)
                    layout_label = var.get("layout_label", f"Bố cục {idx + 1}")

                    st.markdown(
                        f"""
                        <div class="aodai-card">
                            <div class="aodai-img-wrap">
                                <img src="{design_b64}" alt="{layout_label}"/>
                                <span class="variant-index-badge">{idx + 1} / 4</span>
                            </div>
                            <div class="aodai-card-body">
                                <div class="layout-title">{layout_label}</div>
                                <div class="heritage-ref-text">{current_heritage['name']}</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if st.button(f"Chọn thiết kế này →", key=f"btn_choose_v_{idx + 1}", use_container_width=True):
                        st.session_state.chosen_variant = var
                        st.session_state.show_passport = True
                        st.rerun()

                    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

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
