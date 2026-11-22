"""Kết quả (bước cuối): 3 thẻ — bộ 4 thiết kế có nút tải PNG, đối chiếu hiện vật ↔ tà áo, bảng số liệu."""
from __future__ import annotations

from pathlib import Path

import streamlit as st


def _grid(project_root: Path, variants: list[dict], selected_id: str) -> None:
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


def _compare(project_root: Path, variants: list[dict], artifact_path: Path) -> None:
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


def _metrics(variants: list[dict]) -> None:
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


def variant_results(project_root: Path, variants: list[dict], selected_id: str, artifact_path: Path) -> None:
    st.divider()
    st.subheader("🎨 Kết quả thiết kế áo dài (Giai đoạn 1 & 2)")

    tab_grid, tab_compare, tab_metrics = st.tabs([
        "🌟 Bộ 4 Thiết Kế Hoàn Thiện",
        "🔍 Đối Chiếu Hiện Vật & Tà Áo",
        "📊 Chỉ Số Kiểm Định & Dữ Liệu",
    ])
    with tab_grid:
        _grid(project_root, variants, selected_id)
    with tab_compare:
        _compare(project_root, variants, artifact_path)
    with tab_metrics:
        _metrics(variants)
