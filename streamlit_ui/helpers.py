from __future__ import annotations

import base64
import json
from pathlib import Path

import streamlit as st


def load_heritage_items(data_dir: Path) -> list[dict]:
    """Đọc danh mục hiện vật MVP từ dữ liệu tĩnh."""
    item_path = data_dir / "heritage" / "items.json"
    items = json.loads(item_path.read_text(encoding="utf-8"))
    if not isinstance(items, list) or not items:
        raise ValueError("Danh mục hiện vật phải là một danh sách không rỗng.")
    return items


def get_image_base64(path: Path) -> str:
    if not path.exists():
        return ""
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('utf-8')}"


def init_session(default_id: str) -> None:
    defaults = {
        "step": 1,
        "selected_id": default_id,
        "chosen_variant": None,
        "show_passport": False,
        "generated_variants": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def inject_styles(path: Path) -> None:
    st.markdown(f"<style>{path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
