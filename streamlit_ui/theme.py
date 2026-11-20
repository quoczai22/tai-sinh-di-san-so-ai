"""Kiểu dáng của công cụ Streamlit: bảng màu gốm Bát Tràng, tiêu đề, thẻ số liệu, nút."""
from __future__ import annotations

import streamlit as st

PAGE_CONFIG = {
    "page_title": "Tái Sinh Di Sản Số — Kiểm chứng Pipeline AI",
    "page_icon": "🏺",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

STYLES = """
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
"""


def inject_styles() -> None:
    # Chuỗi CSS hằng trong file này, không chứa dữ liệu người dùng
    st.markdown(STYLES, unsafe_allow_html=True)


def page_header() -> None:
    st.markdown('<div class="main-title">🏺 Tái Sinh Di Sản Số</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Công cụ kiểm chứng pipeline AI sinh thiết kế áo dài từ hoa văn gốm sứ Bát Tràng (PyTorch + ControlNet)</div>', unsafe_allow_html=True)
