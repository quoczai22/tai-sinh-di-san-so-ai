"""Chọn hiện vật (bước 1) và khối thông tin hiện vật + trạng thái PyTorch + nút Tạo (bước 2)."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from generation.stable_diffusion import runtime_status

from ..state import clear_results


def heritage_select(items_by_id: dict[str, dict]) -> tuple[str, dict]:
    """Hộp chọn hiện vật + niên đại. Trả (mã hiện vật, hiện vật)."""
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
    return selected_id, item


def heritage_panel(project_root: Path, item: dict, selected_id: str) -> tuple[bool, Path]:
    """Ảnh hiện vật (trái), thông tin + trạng thái PyTorch + nút Tạo (phải). Trả (đã bấm Tạo?, đường dẫn ảnh hiện vật)."""
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
    return clicked, artifact_path
