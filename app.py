# -*- coding: utf-8 -*-
"""TÁI SINH DI SẢN SỐ — STREAMLIT PROTOTYPE (MVP v6.1)
Bám sát mockup Figma đã chốt: https://marvel-ascii-36457406.figma.site/

Luồng người dùng 4 bước:
  1. Chọn hiện vật (6 mẫu Bát Tràng)
  2. Xem mô tả (ảnh hiện vật, tên, nguồn ngắn, nút TẠO THIẾT KẾ)
  3. Đang tạo (tiến độ sinh 4 biến thể trực quan)
  4. Chọn thiết kế / Design Passport (bộ 4 áo dài, độ tương đồng CLIP tham khảo)
"""
from __future__ import annotations

import base64
import csv
import time
from pathlib import Path
import streamlit as st

# Cấu hình trang
st.set_page_config(
    page_title="Tái Sinh Di Sản Số · Áo Dài Bát Tràng",
    page_icon="🏺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
HERITAGE_DIR = DATA_DIR / "heritage"
OUTPUTS_DIR = ROOT / "outputs" / "variants"
VARIANTS_CSV = ROOT / "evaluation" / "variants.csv"

# 6 Hiện vật thuộc phạm vi MVP v6.1 (Ẩn mã BT00x khỏi hiển thị UI)
HERITAGE_ITEMS = [
    {
        "id": "BT_Hac_XP",
        "name": "Bình gốm hoa lam công và sen",
        "era": "Niên hiệu Chính Hòa",
        "subtitle": "Niên hiệu Chính Hòa · Đồ thờ men lam",
        "category": "Đồ thờ men lam Bát Tràng",
        "image_file": "BT_Hac_XP.png",
        "source_short": "Bảo tàng Lịch sử Quốc gia · Bộ sưu tập gốm men lam thế kỷ XVII–XVIII",
    },
    {
        "id": "HSBT_XP-300x300",
        "name": "Hoa sen trên gốm thờ Bát Tràng",
        "era": "Niên hiệu Vĩnh Thịnh",
        "subtitle": "Niên hiệu Vĩnh Thịnh (1705–1719)",
        "category": "Biểu trưng Phật giáo · Lư hương men rạn",
        "image_file": "HSBT_XP-300x300.png",
        "source_short": "Lư hương men rạn niên hiệu Vĩnh Thịnh · Sưu tập đồ gốm men rạn có minh văn",
    },
    {
        "id": "BHV_UU_XP1-600x600",
        "name": "Bình hoa văn chim công hoa mẫu đơn",
        "era": "Thế kỷ XVIII",
        "subtitle": "Thế kỷ XVIII · Men hoàng lưu ly",
        "category": "Đồ thờ gốm hoa lam · Men hoàng lưu ly",
        "image_file": "BHV_UU_XP1-600x600.png",
        "source_short": "Đồ gốm trang trí cung đình Bát Tràng thế kỷ XVIII",
    },
    {
        "id": "MB_2C_XP_31",
        "name": "Thuyền buồm và sóng nước",
        "era": "Thế kỷ XIX",
        "subtitle": "Thế kỷ XIX · Họa tiết hàng hải",
        "category": "Đồ gốm xuất khẩu · Dấu ấn giao thương",
        "image_file": "MB_2C_XP_31.png",
        "source_short": "Sưu tập gốm Bát Tràng xuất khẩu thế kỷ XIX",
    },
    {
        "id": "BT010_2",
        "name": "Hoa cúc dây hoa lam",
        "era": "Niên hiệu Cảnh Hưng",
        "subtitle": "Niên hiệu Cảnh Hưng (1740–1786)",
        "category": "Đề tài trang trí truyền thống · Men lam ngà",
        "image_file": "BT010_2.jpg",
        "source_short": "Chân đèn gốm men rạn Bát Tràng có minh văn thời Lê - Trịnh",
    },
    {
        "id": "binh-hoa-su-trang-ap-noi-hoa-sen-dat-vang-24k-bat-trang-cao-cap-anh-dai-dien",
        "name": "Bình hoa sen dát vàng 24k",
        "era": "Nghệ thuật đương đại",
        "subtitle": "Nghệ thuật đương đại · Sứ trắng dát vàng",
        "category": "Sứ trắng áp nổi · Dát vàng 24k",
        "image_file": "binh-hoa-su-trang-ap-noi-hoa-sen-dat-vang-24k-bat-trang-cao-cap-anh-dai-dien.jpg",
        "source_short": "Tác phẩm nghệ nhân làng gốm Bát Tràng thế kỷ XXI",
    },
]

HERITAGE_MAP = {h["id"]: h for h in HERITAGE_ITEMS}


def get_image_base64(path: Path) -> str:
    """Đọc ảnh sang chuỗi base64 data URI để hiển thị mượt mà trong HTML CSS."""
    if not path.exists():
        return ""
    suffix = path.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{data}"


@st.cache_data
def load_variants_data() -> dict[str, list[dict]]:
    """Nạp dữ liệu 24 biến thể từ evaluation/variants.csv."""
    res: dict[str, list[dict]] = {}
    if not VARIANTS_CSV.exists():
        return res
    with open(VARIANTS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            hid = r["heritage_id"]
            res.setdefault(hid, []).append(r)
    return res


# Khởi tạo Session State
if "step" not in st.session_state:
    st.session_state.step = 1  # 1: Chọn, 2: Mô tả, 3: Đang tạo, 4: Chọn thiết kế
if "selected_id" not in st.session_state:
    st.session_state.selected_id = HERITAGE_ITEMS[0]["id"]
if "chosen_variant" not in st.session_state:
    st.session_state.chosen_variant = None
if "show_passport" not in st.session_state:
    st.session_state.show_passport = False


# Custom CSS khớp chuẩn Figma và design aesthetics
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;0,700;1,400&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    /* Reset & Base */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #1A202C;
    }

    .stApp {
        background-color: #F7F5F0;
    }

    /* Ẩn Streamlit chrome mặc định */
    #MainMenu, header, footer {visibility: hidden;}
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 3rem !important;
        max-width: 1240px;
    }

    /* TOP NAVBAR KHỚP FIGMA */
    .top-navbar {
        background: #0D1E3A;
        padding: 14px 28px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 18px rgba(10, 25, 47, 0.15);
        margin-left: -4rem;
        margin-right: -4rem;
        margin-bottom: 2.2rem;
    }

    .brand-logo {
        display: flex;
        align-items: center;
        gap: 12px;
        text-decoration: none;
    }

    .brand-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        color: #FFFFFF;
        line-height: 1.2;
    }

    .brand-subtitle {
        font-size: 0.72rem;
        color: #94A3B8;
        letter-spacing: 0.02em;
    }

    /* STEPS BREADCRUMB */
    .steps-nav {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .step-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.8rem;
        font-weight: 500;
        padding: 5px 14px;
        border-radius: 9999px;
        color: #94A3B8;
        background: transparent;
        transition: all 0.2s ease;
    }

    .step-pill.active {
        background: #FFFFFF;
        color: #0D1E3A;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    }

    .step-pill.completed {
        color: #E2E8F0;
    }

    .step-divider {
        color: #334155;
        font-size: 0.8rem;
    }

    .badge-mvp {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: #CBD5E1;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 6px;
        letter-spacing: 0.04em;
    }

    /* TYPOGRAPHY */
    .view-step-label {
        color: #2B6CB0;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }

    .view-main-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.25rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.5rem;
        line-height: 1.25;
    }

    .view-description {
        font-size: 0.96rem;
        color: #4B5563;
        margin-bottom: 2rem;
        line-height: 1.5;
    }

    /* CARDS TRONG VIEW 1 */
    .heritage-card {
        background: #FFFFFF;
        border: 1px solid #E8E5DF;
        border-radius: 16px;
        overflow: hidden;
        transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        height: 100%;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    }

    .heritage-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 28px rgba(15, 30, 60, 0.09);
        border-color: #CBD5E1;
    }

    .card-img-wrap {
        width: 100%;
        height: 250px;
        background: #F1EFEA;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }

    .card-img-wrap img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.3s ease;
    }

    .heritage-card:hover .card-img-wrap img {
        transform: scale(1.03);
    }

    .card-body {
        padding: 16px 18px 20px 18px;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }

    .era-tag {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 600;
        color: #2B6CB0;
        background: #EBF4FF;
        padding: 3px 9px;
        border-radius: 6px;
        margin-bottom: 8px;
        align-self: flex-start;
    }

    .card-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.12rem;
        font-weight: 700;
        color: #1A202C;
        margin-bottom: 6px;
        line-height: 1.35;
    }

    .card-desc {
        font-size: 0.82rem;
        color: #64748B;
        line-height: 1.45;
        flex-grow: 1;
    }

    /* VIEW 2 — XEM MÔ TẢ (CHỈ GIỮ ẢNH, TÊN, NGUỒN NGẮN VÀ NÚT TẠO THIẾT KẾ) */
    .detail-img-container {
        border-radius: 18px;
        overflow: hidden;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.06);
        background: #FFFFFF;
    }

    .detail-img-container img {
        width: 100%;
        max-height: 460px;
        object-fit: contain;
        background: #F8F7F4;
    }

    .detail-tag-bar {
        display: flex;
        gap: 8px;
        margin-top: 12px;
        flex-wrap: wrap;
    }

    .pill-tag {
        font-size: 0.76rem;
        font-weight: 500;
        padding: 4px 12px;
        border-radius: 9999px;
        background: #EAE6DF;
        color: #334155;
    }

    .pill-tag.accent {
        background: #FEEBC8;
        color: #7B341E;
        font-weight: 600;
    }

    .btn-sub-note {
        text-align: center;
        font-size: 0.82rem;
        color: #64748B;
        margin-top: 10px;
    }

    /* VIEW 3 — ĐANG TẠO THIẾT KẾ (TIẾN ĐỘ TRỰC QUAN, KHÔNG CHỨA THÔNG SỐ WEIGHT) */
    .generating-container {
        max-width: 600px;
        margin: 0 auto;
        text-align: center;
        padding-top: 1.2rem;
    }

    .thumb-avatar {
        width: 76px;
        height: 76px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #FFFFFF;
        box-shadow: 0 4px 14px rgba(0,0,0,0.12);
        margin: 0 auto 16px auto;
    }

    .gen-progress-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 4px 16px rgba(0,0,0,0.04);
        margin-top: 24px;
        text-align: left;
    }

    .gen-step-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 13px 20px;
        border-bottom: 1px solid #F1F5F9;
        font-size: 0.88rem;
    }

    .gen-step-item:last-child {
        border-bottom: none;
    }

    .gen-step-item.active {
        background: #EFF6FF;
        color: #1E40AF;
        font-weight: 600;
    }

    .gen-step-left {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .step-circle {
        width: 22px;
        height: 22px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.72rem;
        font-weight: 700;
    }

    .step-circle.done {
        background: #10B981;
        color: #FFFFFF;
    }

    .step-circle.running {
        background: #2563EB;
        color: #FFFFFF;
    }

    .step-circle.pending {
        background: #E2E8F0;
        color: #64748B;
    }

    .step-status-tag {
        font-size: 0.78rem;
        font-weight: 500;
    }

    /* VIEW 4 — CHỌN THIẾT KẾ (GALLERY CHỈ HIỂN THỊ ÁO DÀI, KHÔNG OVERLAY BÌNH GỐC) */
    .aodai-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        display: flex;
        flex-direction: column;
        height: 100%;
        position: relative;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .aodai-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 28px rgba(0,0,0,0.08);
    }

    .aodai-img-wrap {
        position: relative;
        width: 100%;
        height: 380px;
        background: #E2E8F0;
    }

    .aodai-img-wrap img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .variant-index-badge {
        position: absolute;
        top: 12px;
        right: 12px;
        background: rgba(15, 23, 42, 0.75);
        color: #FFFFFF;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 3px 9px;
        border-radius: 9999px;
        backdrop-filter: blur(4px);
    }

    .aodai-card-body {
        padding: 16px 18px 20px 18px;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }

    .layout-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.15rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 4px;
    }

    .heritage-ref-text {
        font-size: 0.8rem;
        color: #64748B;
        margin-bottom: 16px;
    }

    /* DESIGN PASSPORT */
    .passport-overlay {
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 20px;
        box-shadow: 0 16px 40px rgba(15, 23, 42, 0.18);
        overflow: hidden;
        margin-top: 1.5rem;
        margin-bottom: 2rem;
    }

    .passport-header-bar {
        background: #0D1E3A;
        padding: 16px 24px;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .passport-modal-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.25rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }

    .metric-score-box {
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-radius: 14px;
        padding: 18px 20px;
        margin: 20px 0;
    }

    .metric-title {
        font-size: 0.82rem;
        font-weight: 700;
        color: #1E3A8A;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }

    .metric-value-huge {
        font-size: 2.5rem;
        font-weight: 800;
        color: #1E40AF;
        line-height: 1;
        margin-bottom: 8px;
    }

    .metric-subnote {
        font-size: 0.78rem;
        color: #475569;
        line-height: 1.45;
    }

    .color-swatch-bar {
        display: flex;
        gap: 6px;
        margin-top: 8px;
    }

    .color-swatch {
        width: 24px;
        height: 24px;
        border-radius: 4px;
        border: 1px solid rgba(0,0,0,0.15);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Nạp dữ liệu biến thể
variants_db = load_variants_data()
current_heritage = HERITAGE_MAP.get(st.session_state.selected_id, HERITAGE_ITEMS[0])


# ==============================================================================
# TOP NAVBAR
# ==============================================================================
step = st.session_state.step
p1_cls = "active" if step == 1 else ("completed" if step > 1 else "")
p2_cls = "active" if step == 2 else ("completed" if step > 2 else "")
p3_cls = "active" if step == 3 else ("completed" if step > 3 else "")
p4_cls = "active" if step == 4 else ""

st.markdown(
    f"""
    <div class="top-navbar">
        <div class="brand-logo">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M8 2h8l2 5-3 6v7a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2v-7l-3-6 2-5z"/>
                <line x1="8" y1="2" x2="16" y2="2"/>
                <line x1="12" y1="13" x2="12" y2="20"/>
            </svg>
            <div>
                <div class="brand-title">DIGITAL HERITAGE</div>
                <div class="brand-subtitle">Di Sản Số · Gốm Bát Tràng</div>
            </div>
        </div>
        <div class="steps-nav">
            <span class="step-pill {p1_cls}">{'✓ ' if step > 1 else '1 '}Chọn hiện vật</span>
            <span class="step-divider">—</span>
            <span class="step-pill {p2_cls}">{'✓ ' if step > 2 else '2 '}Xem mô tả</span>
            <span class="step-divider">—</span>
            <span class="step-pill {p3_cls}">{'✓ ' if step > 3 else '3 '}Đang tạo</span>
            <span class="step-divider">—</span>
            <span class="step-pill {p4_cls}">4 Chọn thiết kế</span>
        </div>
        <div>
            <span class="badge-mvp">MVP v6.1</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# VIEW 1 — CHỌN HIỆN VẬT
# ==============================================================================
if st.session_state.step == 1:
    st.markdown('<div class="view-step-label">BƯỚC 1 — CHỌN HIỆN VẬT</div>', unsafe_allow_html=True)
    st.markdown('<div class="view-main-title">Tái Sinh Di Sản Số</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="view-description">'
        'Chọn một hiện vật gốm Bát Tràng để bắt đầu hành trình tái sinh hoa văn thành thiết kế áo dài đương đại.'
        '</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    for idx, item in enumerate(HERITAGE_ITEMS):
        col = cols[idx % 3]
        with col:
            img_path = HERITAGE_DIR / item["image_file"]
            img_b64 = get_image_base64(img_path)

            st.markdown(
                f"""
                <div class="heritage-card">
                    <div class="card-img-wrap">
                        <img src="{img_b64}" alt="{item['name']}"/>
                    </div>
                    <div class="card-body">
                        <span class="era-tag">{item['era']}</span>
                        <div class="card-title">{item['name']}</div>
                        <div class="card-desc">{item['category']}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Khám phá hiện vật", key=f"btn_select_{item['id']}", use_container_width=True):
                st.session_state.selected_id = item["id"]
                st.session_state.step = 2
                st.session_state.chosen_variant = None
                st.session_state.show_passport = False
                st.rerun()
            st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)


# ==============================================================================
# VIEW 2 — XEM MÔ TẢ
# UI Rules bắt buộc: Chỉ giữ ảnh hiện vật, tên, nguồn ngắn và nút TẠO THIẾT KẾ;
# Bỏ khung 4 biến thể, thông số kỹ thuật, weight, GPU/thời gian, evaluation và audit log.
# Ẩn mã BT00x khỏi chữ hiển thị. Không hiển thị khối mô tả dài.
# ==============================================================================
elif st.session_state.step == 2:
    if st.button("← Quay lại danh sách", key="btn_back_to_list"):
        st.session_state.step = 1
        st.rerun()

    st.markdown('<div class="view-step-label">BƯỚC 2 — XEM MÔ TẢ</div>', unsafe_allow_html=True)

    c_left, c_right = st.columns([1.1, 1.3], gap="large")

    with c_left:
        img_path = HERITAGE_DIR / current_heritage["image_file"]
        img_b64 = get_image_base64(img_path)
        st.markdown(
            f"""
            <div class="detail-img-container">
                <img src="{img_b64}" alt="{current_heritage['name']}"/>
            </div>
            <div class="detail-tag-bar">
                <span class="pill-tag accent">{current_heritage['era']}</span>
                <span class="pill-tag">Bát Tràng</span>
                <span class="pill-tag">Gốm truyền thống</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_right:
        st.markdown(
            f"""
            <div class="view-main-title" style="font-size: 2.1rem; margin-bottom: 0.3rem;">{current_heritage['name']}</div>
            <div style="font-size: 0.95rem; color: #64748B; margin-bottom: 1.8rem;">{current_heritage['category']}</div>

            <div style="background: #FFFFFF; border: 1px solid #E5E0D8; border-radius: 16px; padding: 20px 24px; margin-bottom: 28px; box-shadow: 0 2px 10px rgba(0,0,0,0.03);">
                <div style="font-size: 0.8rem; font-weight: 700; color: #1A365D; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">
                    NGUỒN TƯ LIỆU
                </div>
                <div style="font-size: 0.92rem; color: #334155; line-height: 1.5;">
                    <em>{current_heritage['source_short']}</em>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("TẠO THIẾT KẾ →", key="btn_start_generate", use_container_width=True, type="primary"):
            st.session_state.step = 3
            st.rerun()

        st.markdown(
            '<div class="btn-sub-note">Hệ thống sẽ tạo một số phương án để bạn chọn.</div>',
            unsafe_allow_html=True,
        )


# ==============================================================================
# VIEW 3 — ĐANG TẠO THIẾT KẾ
# Bỏ hoàn toàn hiển thị thông số kỹ thuật và weight (0.85, 0.65, ...)
# ==============================================================================
elif st.session_state.step == 3:
    img_path = HERITAGE_DIR / current_heritage["image_file"]
    img_b64 = get_image_base64(img_path)

    st.markdown(
        f"""
        <div class="generating-container">
            <img class="thumb-avatar" src="{img_b64}" alt="{current_heritage['name']}"/>
            <div class="view-step-label">BƯỚC 3 — ĐANG TẠO THIẾT KẾ</div>
            <div class="view-main-title" style="font-size: 1.9rem;">{current_heritage['name']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    gen_box = st.empty()
    pbar = st.progress(0)

    steps_definition = [
        "Tách nền & chuẩn bị bản đồ cạnh",
        "Biến thể 1 / 4 đang sinh",
        "Biến thể 2 / 4 đang sinh",
        "Biến thể 3 / 4 đang sinh",
        "Biến thể 4 / 4 đang sinh",
        "Đưa lên áo dài & hoàn thiện",
    ]

    for i in range(len(steps_definition)):
        pbar.progress((i + 1) / len(steps_definition))

        # Render HTML tiến độ trực quan, không lộ tham số weight
        html_steps = '<div class="gen-progress-card">'
        for s_idx, s_title in enumerate(steps_definition):
            if s_idx < i:
                circle = '<span class="step-circle done">✓</span>'
                status = '<span style="color: #10B981; font-weight:600;">xong</span>'
                cls = ""
            elif s_idx == i:
                circle = f'<span class="step-circle running">{s_idx + 1}</span>'
                status = '<span style="color: #2563EB; font-weight:600;">đang chạy...</span>'
                cls = "active"
            else:
                circle = f'<span class="step-circle pending">{s_idx + 1}</span>'
                status = '<span style="color: #94A3B8;">chờ</span>'
                cls = ""

            html_steps += f"""
            <div class="gen-step-item {cls}">
                <div class="gen-step-left">
                    {circle}
                    <div style="font-weight: 500;">{s_title}</div>
                </div>
                <div class="step-status-tag">{status}</div>
            </div>
            """
        html_steps += "</div>"
        gen_box.markdown(html_steps, unsafe_allow_html=True)
        time.sleep(0.35)

    st.session_state.step = 4
    st.rerun()


# ==============================================================================
# VIEW 4 — CHỌN THIẾT KẾ & DESIGN PASSPORT
# UI Rules:
# - Gallery chỉ hiển thị ảnh áo dài được sinh (không overlay bình gốc).
# - Passport hiển thị lớn ảnh đã chọn, thông tin nguồn ngắn và similarity dạng tham khảo.
# - Ẩn mã BT00x khỏi chữ hiển thị.
# - Không ghi và không hiển thị audit log.
# ==============================================================================
elif st.session_state.step == 4:
    st.markdown('<div class="view-step-label">BƯỚC 4 — CHỌN THIẾT KẾ</div>', unsafe_allow_html=True)
    st.markdown('<div class="view-main-title">4 Thiết Kế Áo Dài</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="view-description">Từ hoa văn: <strong>{current_heritage["name"]}</strong>. '
        'Bấm "Chọn thiết kế này" để xem chi tiết Design Passport và đối chiếu độ tương đồng.</div>',
        unsafe_allow_html=True,
    )

    variants = variants_db.get(st.session_state.selected_id, [])

    if not variants:
        st.warning("Chưa tìm thấy dữ liệu biến thể cho hiện vật này trong outputs/variants.")
    else:
        v_cols = st.columns(4)
        for idx, var in enumerate(variants[:4]):
            col = v_cols[idx]
            with col:
                design_rel_path = var.get("design_path", "")
                design_file = ROOT / design_rel_path
                design_b64 = get_image_base64(design_file)
                layout_label = var.get("layout_label", f"Bố cục {idx + 1}")

                st.markdown(
                    f"""
                    <div class="aodai-card">
                        <div class="aodai-img-wrap">
                            <img src="{design_b64}" alt="{layout_label}"/>
                            <span class="variant-index-badge">{idx + 1} / 4</span>
                        </div>
                        <div class="aodai-card-body">
                            <div class="layout-title">{layout_label}</div>
                            <div class="heritage-ref-text">{current_heritage['name']}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button(f"Chọn thiết kế này →", key=f"btn_choose_v_{idx + 1}", use_container_width=True):
                    st.session_state.chosen_variant = var
                    st.session_state.show_passport = True
                    st.rerun()

                st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    # DESIGN PASSPORT DRAWER
    if st.session_state.show_passport and st.session_state.chosen_variant is not None:
        c_var = st.session_state.chosen_variant
        var_idx = int(c_var.get("variant_index", 1))
        layout_name = c_var.get("layout_label", "Bố cục mẫu")
        sim_val = float(c_var.get("similarity_pattern_vs_ceramic", 0.75))
        sim_pct = int(round(sim_val * 100))
        palette_hexes = [c for c in c_var.get("source_palette", "").split(";") if c.startswith("#")]
        aodai_b64 = get_image_base64(ROOT / c_var.get("design_path", ""))

        st.markdown("---")
        st.markdown(
            f"""
            <div class="passport-overlay">
                <div class="passport-header-bar">
                    <div>
                        <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.06em;">THIẾT KẾ CỦA BẠN</div>
                        <div class="passport-modal-title">{current_heritage['name']}</div>
                    </div>
                    <div style="font-size: 0.82rem; color: #CBD5E1;">
                        Biến thể {var_idx} / 4 · {layout_name}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        p_left, p_right = st.columns([1, 1], gap="large")

        with p_left:
            st.markdown(
                f"""
                <div style="border-radius: 16px; overflow: hidden; border: 1px solid #E2E8F0; box-shadow: 0 4px 16px rgba(0,0,0,0.06);">
                    <img src="{aodai_b64}" style="width:100%; max-height: 520px; object-fit: contain; background: #FAF9F6;"/>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with p_right:
            swatch_html = "".join([f'<span class="color-swatch" style="background: {c};" title="{c}"></span>' for c in palette_hexes])
            st.markdown(
                f"""
                <div class="view-main-title" style="font-size: 1.8rem; margin-bottom: 0.4rem;">{current_heritage['name']}</div>
                <div style="font-size: 0.88rem; color: #64748B; margin-bottom: 1rem;">{current_heritage['subtitle']}</div>

                <div style="font-size: 0.9rem; color: #334155; line-height: 1.6; margin-bottom: 14px;">
                    Thiết kế áo dài đương đại được kiến tạo từ hoa văn gốm Bát Tràng theo bố cục <strong>{layout_name}</strong>.
                    Kỹ thuật ghép tất định đảm bảo dáng áo chuẩn mực và hoa văn ôm nếp vải tự nhiên.
                </div>

                <div class="metric-score-box">
                    <div class="metric-title">MỨC ĐỘ GỢI NHỚ HOA VĂN GỐC</div>
                    <div class="metric-value-huge">{sim_pct}%</div>
                    <div style="width: 100%; background: #DBEAFE; height: 8px; border-radius: 999px; overflow: hidden; margin-bottom: 8px;">
                        <div style="width: {sim_pct}%; background: #2563EB; height: 100%;"></div>
                    </div>
                    <div class="metric-subnote">
                        *Chỉ mang tính tham khảo, không phải điểm đạt hoặc không đạt.
                        Đo bằng tương đồng thị giác CLIP giữa hoa văn sinh ra và hoa văn hiện vật gốc.*
                    </div>
                </div>

                <div style="margin-bottom: 14px;">
                    <div style="font-size: 0.8rem; font-weight: 600; color: #475569; text-transform: uppercase;">Bảng màu hiện vật</div>
                    <div class="color-swatch-bar">{swatch_html}</div>
                </div>

                <div style="font-size: 0.78rem; color: #64748B; margin-bottom: 20px;">
                    Nguồn tư liệu: <em>{current_heritage['source_short']}</em>.
                </div>
                """,
                unsafe_allow_html=True,
            )

            b_col1, b_col2 = st.columns(2)
            with b_col1:
                if st.button("Tạo thiết kế khác ↺", key="btn_reloop", use_container_width=True, type="primary"):
                    st.session_state.step = 1
                    st.session_state.chosen_variant = None
                    st.session_state.show_passport = False
                    st.rerun()
            with b_col2:
                if st.button("Đóng Passport ✕", key="btn_close_passport", use_container_width=True):
                    st.session_state.show_passport = False
                    st.rerun()
