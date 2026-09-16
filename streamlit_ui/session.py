from __future__ import annotations

import streamlit as st


def initialize(default_heritage_id: str) -> None:
    defaults = {
        "selected_heritage_id": default_heritage_id,
        "generated_variants": [],
        "generated_for": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def clear_results() -> None:
    st.session_state.generated_variants = []
    st.session_state.generated_for = None
