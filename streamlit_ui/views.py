from __future__ import annotations

from pathlib import Path

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
    selected_id = st.selectbox(
        "Chọn hiện vật",
        options=list(items_by_id),
        format_func=lambda heritage_id: items_by_id[heritage_id]["name"],
        key="selected_heritage_id",
    )
    item = items_by_id[selected_id]

    left, right = st.columns((1, 1), gap="large")
    with left:
        st.image(project_root / item["image_path"], caption=item["name"], width="stretch")
    with right:
        st.subheader(item["name"])
        st.caption(f"Bản quyền ảnh: {item['license_note']}")
        st.write(f"Conditioning mode: `{item['conditioning_mode']}`")

    if st.session_state.generated_for not in {None, selected_id}:
        clear_results()

    ready, detail = runtime_status()
    if ready:
        st.success(f"PyTorch đã sẵn sàng trên {detail}.")
    else:
        st.error(f"PyTorch chưa thể chạy pipeline: {detail}")

    if st.button("Tạo 4 thiết kế áo dài", type="primary", disabled=not ready):
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
        st.subheader("Kết quả vừa sinh")
        columns = st.columns(len(variants))
        for column, variant in zip(columns, variants, strict=True):
            with column:
                image_path = project_root / variant["design_path"]
                st.image(image_path, width="stretch")
                st.caption(f"Biến thể {variant['variant_index']} · {variant['layout_label']}")
                if "similarity_pattern_vs_ceramic" in variant:
                    similarity = float(variant["similarity_pattern_vs_ceramic"])
                    st.caption(f"Độ tương đồng tham khảo: {similarity:.1%}")
