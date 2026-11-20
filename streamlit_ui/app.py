"""Công cụ Streamlit nội bộ kiểm chứng pipeline PyTorch/ControlNet bằng dữ liệu hiện vật thật.

Chạy từ gốc repo: `streamlit run app.py` (app.py ở gốc chỉ gọi main() ở đây).
Luồng: theme → đọc hiện vật (provenance/heritage.py) → trạng thái phiên → thanh bên → màn hình Tạo thiết kế.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from provenance.heritage import load_heritage_metadata

from .components.sidebar import render_sidebar
from .screens.generate import render_generate
from .state import initialize
from .theme import PAGE_CONFIG, inject_styles, page_header

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    st.set_page_config(**PAGE_CONFIG)
    inject_styles()
    heritage_items = load_heritage_metadata(PROJECT_ROOT)
    initialize(heritage_items[0]["heritage_id"])
    render_sidebar(len(heritage_items))
    page_header()
    render_generate(PROJECT_ROOT, heritage_items)
