"""Thanh bên: phần cứng đang chạy (GPU/CPU, PyTorch, Python) và thống kê dữ liệu hiện vật."""
from __future__ import annotations

import sys

import streamlit as st


def render_sidebar(heritage_count: int) -> None:
    with st.sidebar:
        st.markdown("### 🏺 Tái Sinh Di Sản Số")
        st.caption("Chung kết Cuộc thi Sáng tạo trẻ 2026")
        st.divider()

        st.markdown("#### ⚡ Phần cứng & Môi trường")
        try:
            import torch
            if torch.cuda.is_available():
                dev_name = torch.cuda.get_device_name(0)
                mem_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                st.success(f"**GPU:** {dev_name}")
                st.caption(f"VRAM: {mem_gb:.1f} GB · CUDA {torch.version.cuda}")
            else:
                st.warning("**Thiết bị:** CPU (Không có GPU CUDA)")
            st.caption(f"PyTorch: `{torch.__version__}`")
        except Exception:
            st.info("Trạng thái: Python runtime")

        st.caption(f"Python: `{sys.version.split()[0]}`")
        st.divider()

        st.markdown("#### 📋 Thống kê Dữ liệu")
        st.write(f"• Số hiện vật kiểm định: **{heritage_count}**")
        st.write("• Mô hình: **SD 1.5 + ControlNet Canny + CLIP ViT-B/32**")
        st.write("• Tiêu chuẩn kiểm định: **G2 (Hoa văn) & G3 (Tà áo)**")
