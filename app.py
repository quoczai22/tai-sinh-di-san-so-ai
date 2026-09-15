"""Điểm khởi động của ứng dụng Streamlit Tái sinh Di sản Số."""
from pathlib import Path

import streamlit as st

from streamlit_ui.helpers import init_session, inject_styles, load_heritage_items
from streamlit_ui.views import render_app


st.set_page_config(
    page_title="Tái Sinh Di Sản Số · Áo Dài Bát Tràng",
    page_icon="🏺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
HERITAGE_DIR = DATA_DIR / "heritage"
HERITAGE_ITEMS = load_heritage_items(DATA_DIR)
HERITAGE_MAP = {item["id"]: item for item in HERITAGE_ITEMS}

init_session(HERITAGE_ITEMS[0]["id"])
inject_styles(ROOT / "streamlit_ui" / "styles.css")
inject_styles(ROOT / "streamlit_ui" / "static_design.css")
render_app(ROOT, HERITAGE_DIR, HERITAGE_ITEMS, HERITAGE_MAP)
