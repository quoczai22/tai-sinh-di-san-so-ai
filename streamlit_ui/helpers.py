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


def render_html(html: str) -> None:
    """Render HTML an toàn trong Streamlit, loại bỏ thụt lề đầu dòng

    để parser CommonMark không bao giờ hiểu nhầm là khối code (<pre><code>).
    """
    clean_html = "\n".join(line.lstrip() for line in html.splitlines())
    st.markdown(clean_html, unsafe_allow_html=True)


WEB_UI_CSS_ORDER = (
    "assets/css/base.css",
    "assets/css/layout.css",
    "assets/css/sections/hero.css",
    "assets/css/sections/catalog.css",
    "assets/css/overlays/detail-modal.css",
    "assets/css/overlays/pipeline.css",
    "assets/css/sections/curate-layout.css",
    "assets/css/sections/curate-motion.css",
    "assets/css/sections/variants.css",
    "assets/css/overlays/passport.css",
    "assets/css/overlays/stage-lightbox.css",
    "assets/css/responsive.css",
    "assets/css/effects/heritage-motion.css",
    "assets/css/footer.css",
    "assets/css/effects/loading-states.css",
)


def inject_web_ui_styles(root: Path) -> None:
    """Nạp trực tiếp toàn bộ hệ thống CSS từ thư mục web_ui kèm override Streamlit."""
    css_chunks: list[str] = []
    web_dir = root / "web_ui"
    for rel_path in WEB_UI_CSS_ORDER:
        file_path = web_dir / rel_path
        if file_path.exists():
            css_chunks.append(file_path.read_text(encoding="utf-8"))

    override_path = root / "streamlit_ui" / "streamlit_overrides.css"
    if override_path.exists():
        css_chunks.append(override_path.read_text(encoding="utf-8"))

    render_html(f"<style>{''.join(css_chunks)}</style>")


inject_webtestdesign_styles = inject_web_ui_styles
