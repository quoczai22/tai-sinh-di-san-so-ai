"""Ứng dụng kiểm chứng pipeline PyTorch/ControlNet bằng dữ liệu hiện vật thật."""
from pathlib import Path

import streamlit as st

from streamlit_ui.heritage_data import load_heritage_metadata
from streamlit_ui.session import initialize
from streamlit_ui.views import render_app


st.set_page_config(page_title="Kiểm chứng Tái sinh Di sản", page_icon="🏺", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent
HERITAGE_ITEMS = load_heritage_metadata(PROJECT_ROOT)

initialize(HERITAGE_ITEMS[0]["heritage_id"])

st.title("Tái sinh Di sản Số")
st.caption("Kiểm chứng dữ liệu hiện vật và pipeline sinh ảnh bằng PyTorch + ControlNet.")
render_app(PROJECT_ROOT, HERITAGE_ITEMS)
