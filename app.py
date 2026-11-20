"""Ứng dụng kiểm chứng pipeline PyTorch/ControlNet bằng dữ liệu hiện vật thật."""
from pathlib import Path
import sys

import streamlit as st

from streamlit_ui.heritage_data import load_heritage_metadata
from streamlit_ui.session import initialize
from streamlit_ui.views import render_app


st.set_page_config(
    page_title="Tái Sinh Di Sản Số — Kiểm chứng Pipeline AI",
    page_icon="🏺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS cho phong thái triển lãm di sản cao cấp
st.markdown("""
<style>
    /* Bảng màu nhận diện gốm Bát Tràng */
    :root {
        --primary-cobalt: #0E2240;
        --accent-gold: #D4B47A;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0E2240;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #4A5866;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #F8F5EE;
        border: 1px solid #E1D9C8;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

PROJECT_ROOT = Path(__file__).resolve().parent
HERITAGE_ITEMS = load_heritage_metadata(PROJECT_ROOT)

initialize(HERITAGE_ITEMS[0]["heritage_id"])

# Sidebar thông số hệ thống và phần cứng
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
    st.write(f"• Số hiện vật kiểm định: **{len(HERITAGE_ITEMS)}**")
    st.write("• Mô hình: **SD 1.5 + ControlNet Canny + CLIP ViT-B/32**")
    st.write("• Tiêu chuẩn kiểm định: **G2 (Hoa văn) & G3 (Tà áo)**")

st.markdown('<div class="main-title">🏺 Tái Sinh Di Sản Số</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Công cụ kiểm chứng pipeline AI sinh thiết kế áo dài từ hoa văn gốm sứ Bát Tràng (PyTorch + ControlNet)</div>', unsafe_allow_html=True)

render_app(PROJECT_ROOT, HERITAGE_ITEMS)
