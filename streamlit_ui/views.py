from __future__ import annotations

import io
from pathlib import Path

from PIL import Image
import streamlit as st

from generation.stable_diffusion import runtime_status
from generation.streamlit_runner import generate_design_set

from .session import clear_results


def saved_variants(project_root: Path, heritage_id: str) -> list[dict]:
    """Trả về bốn ảnh thiết kế thật đã được pipeline ghi ra ổ đĩa."""
    variants = []
    for index in range(1, 5):
        image_path = project_root / "outputs" / "variants" / f"{heritage_id}_V{index}_aodai.png"
        if not image_path.is_file():
            return []
        variants.append({
            "variant_index": index,
            "layout_label": f"Thiết kế {index}",
            "design_path": image_path.relative_to(project_root).as_posix(),
        })
    return variants


def render_app(project_root: Path, heritage_items: list[dict]) -> None:
    items_by_id = {item["heritage_id"]: item for item in heritage_items}
    
    col_sel, col_mode = st.columns([3, 1])
    with col_sel:
        selected_id = st.selectbox(
            "Chọn hiện vật gốm Bát Tràng",
            options=list(items_by_id),
            format_func=lambda heritage_id: f"{items_by_id[heritage_id]['name']} ({heritage_id})",
            key="selected_heritage_id",
        )
    with col_mode:
        item = items_by_id[selected_id]
        st.metric("Niên đại / Men", item.get("dating", "Gốm Bát Tràng"))

    left, right = st.columns((1, 1.2), gap="large")
    with left:
        artifact_path = project_root / item["image_path"]
        st.image(artifact_path, caption=f"Hiện vật: {item['name']}", use_container_width=True)
    with right:
        st.subheader(item["name"])
        st.markdown(f"""
        - **Mã hiện vật:** `{item['heritage_id']}`
        - **Chế độ tiền xử lý (Conditioning):** `{item.get('conditioning_mode', 'canny_edge')}`
        - **Bản quyền ảnh:** *{item.get('license_note', 'Tài liệu di sản')}*
        - **Giấy phép:** `{item.get('license', 'CC BY-NC 4.0')}`
        """)

        if st.session_state.generated_for not in {None, selected_id}:
            clear_results()

        ready, detail = runtime_status()
        if ready:
            st.success(f"✅ PyTorch sẵn sàng trên **{detail}**")
        else:
            st.error(f"⚠️ PyTorch chưa thể chạy pipeline: {detail}")

        btn_cols = st.columns([2, 1])
        with btn_cols[0]:
            clicked = st.button("🚀 Tạo 4 thiết kế áo dài mới", type="primary", disabled=not ready, use_container_width=True)

    if clicked:
        progress_bar = st.progress(0)
        progress_label = st.empty()

        def update_progress(value: int, label: str) -> None:
            progress_bar.progress(value)
            progress_label.write(label)

        try:
            variants = generate_design_set(selected_id, update_progress)
        except Exception as exc:
            st.error("Pipeline chưa hoàn tất. Xem chi tiết lỗi bên dưới.")
            st.exception(exc)
        else:
            st.session_state.generated_variants = variants
            st.session_state.generated_for = selected_id
            progress_bar.empty()
            progress_label.empty()
            st.rerun()

    variants = st.session_state.generated_variants
    if st.session_state.generated_for != selected_id:
        variants = saved_variants(project_root, selected_id)

    if variants:
        st.divider()
        st.subheader("🎨 Kết quả thiết kế áo dài (Giai đoạn 1 & 2)")

        tab_grid, tab_compare, tab_metrics = st.tabs([
            "🌟 Bộ 4 Thiết Kế Hoàn Thiện",
            "🔍 Đối Chiếu Hiện Vật & Tà Áo",
            "📊 Chỉ Số Kiểm Định & Dữ Liệu",
        ])

        with tab_grid:
            cols = st.columns(len(variants))
            for col, variant in zip(cols, variants, strict=True):
                with col:
                    img_path = project_root / variant["design_path"]
                    st.image(img_path, use_container_width=True)
                    st.markdown(f"**Biến thể {variant['variant_index']}**")
                    st.caption(variant.get("layout_label", f"Thiết kế {variant['variant_index']}"))
                    
                    if img_path.is_file():
                        with open(img_path, "rb") as f:
                            st.download_button(
                                label="⬇️ Tải PNG",
                                data=f.read(),
                                file_name=f"{selected_id}_V{variant['variant_index']}.png",
                                mime="image/png",
                                key=f"dl_grid_{variant['variant_index']}",
                                use_container_width=True,
                            )

        with tab_compare:
            st.caption("So sánh đối chiếu giữa hoa văn trên bình gốm gốc và 4 phương án bố cục áo dài:")
            cmp_left, cmp_right = st.columns([1, 2], gap="medium")
            with cmp_left:
                st.markdown("**🏺 Hiện vật gốc**")
                st.image(artifact_path, use_container_width=True)
            with cmp_right:
                st.markdown("**👗 4 Phương án tà áo dài**")
                sub_cols = st.columns(4)
                for sc, v in zip(sub_cols, variants, strict=True):
                    with sc:
                        v_img = project_root / v["design_path"]
                        st.image(v_img, caption=f"V{v['variant_index']}", use_container_width=True)

        with tab_metrics:
            st.markdown("##### Bảng dữ liệu thực nghiệm & Truy xuất nguồn gốc")
            table_rows = []
            for v in variants:
                table_rows.append({
                    "Biến thể": f"V{v['variant_index']}",
                    "Bố cục": v.get("layout_label", "Tất định"),
                    "Độ tương đồng (CLIP)": f"{float(v.get('similarity_pattern_vs_ceramic', 0)):.1%}" if "similarity_pattern_vs_ceramic" in v else "N/A",
                    "Đường dẫn file": v["design_path"],
                })
            st.dataframe(table_rows, use_container_width=True)
