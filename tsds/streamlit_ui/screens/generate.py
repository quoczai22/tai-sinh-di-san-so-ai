"""Màn hình duy nhất: chọn hiện vật → bấm Tạo (chạy pipeline thật qua tsds/pipeline/run.py) → xem 4 thiết kế.

Chưa bấm Tạo cho hiện vật đang chọn thì hiện bộ ảnh đã sinh trước đó trên ổ đĩa (nếu có), không giả lập.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from tsds.pipeline.run import generate_design_set

from ..components.heritage_picker import heritage_panel, heritage_select
from ..components.variant_results import variant_results
from ..variants import saved_variants


def render_generate(project_root: Path, heritage_items: list[dict]) -> None:
    items_by_id = {item["heritage_id"]: item for item in heritage_items}
    selected_id, item = heritage_select(items_by_id)
    clicked, artifact_path = heritage_panel(project_root, item, selected_id)

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
        variant_results(project_root, variants, selected_id, artifact_path)
