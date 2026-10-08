from __future__ import annotations

import streamlit as st
from html import escape

from pathlib import Path
from base64 import b64encode

ROOT_DIR = Path(__file__).resolve().parent
B777_HERO_PATH = ROOT_DIR / "garuda_aircraft_hero_777.png"
PLANE_URI = "data:image/png;base64," + b64encode(B777_HERO_PATH.read_bytes()).decode("ascii")
LOGO_URI = ""

st.markdown(
    r"""
    <style>
    .stApp {
        background:
            radial-gradient(circle at 8% 2%, rgba(40,123,196,.08), transparent 28%),
            radial-gradient(circle at 92% 8%, rgba(41,151,151,.07), transparent 26%),
            #F4F7FB !important;
    }
    .block-container {
        max-width:1500px !important;
        padding-top:.8rem !important;
        padding-bottom:2rem !important;
        padding-left:1.55rem !important;
        padding-right:1.55rem !important;
    }

    /* HERO */
    .home-hero {
        position:relative;
        min-height:390px;
        overflow:hidden;
        border-radius:26px;
        margin:0 0 24px 0;
        background-image:url("__PLANE_URI__");
        background-size:cover;
        background-position:center center;
        background-repeat:no-repeat;
        border:1px solid rgba(255,255,255,.12);
        box-shadow:0 18px 40px rgba(10,31,57,.15);
    }
    .home-hero::after {
        content:"";
        position:absolute;
        inset:auto 0 0 0;
        height:74px;
        background:linear-gradient(180deg,rgba(5,24,48,0),rgba(5,24,48,.16));
        pointer-events:none;
    }
    .hero-copy {
        position:relative;
        z-index:2;
        width:49%;
        min-height:390px;
        padding:40px 38px 34px 40px;
        display:flex;
        flex-direction:column;
        justify-content:center;
    }
    .hero-eyebrow {
        color:#8FC6FF;
        font-size:12px;
        font-weight:820;
        letter-spacing:.13em;
        text-transform:uppercase;
        margin-bottom:16px;
    }
    .hero-title {
        color:#FFFFFF;
        font-size:37px;
        line-height:1.08;
        font-weight:850;
        letter-spacing:-.032em;
        max-width:650px;
        text-shadow:0 3px 12px rgba(0,0,0,.18);
    }
    .hero-subtitle {
        margin-top:17px;
        color:#DCE8F5;
        font-size:14px;
        line-height:1.45;
        font-weight:650;
    }
    .hero-subtitle span {
        display:inline-block; width:5px; height:5px; border-radius:50%;
        background:#69CFD7; margin:0 10px 2px 10px;
    }
    .hero-divider {
        width:48px;
        height:3px;
        border-radius:999px;
        background:linear-gradient(90deg,#48BDD0,#7AB8FF);
        margin:20px 0 15px 0;
    }
    .hero-rooms {
        display:flex;
        align-items:center;
        gap:13px;
        flex-wrap:wrap;
        color:#FFFFFF;
        font-size:12.5px;
        font-weight:700;
    }
    .hero-rooms .dot {
        width:5px;
        height:5px;
        border-radius:50%;
        background:#69CFD7;
    }

    /* logo moved back to top-right; reduced and isolated from aircraft */
    .hero-logo {
        position:absolute;
        z-index:4;
        top:25px;
        right:28px;
        width:185px;
        max-width:20%;
        height:auto;
        object-fit:contain;
        filter:drop-shadow(0 2px 7px rgba(0,0,0,.20));
    }
    .hero-footer {
        position:absolute;
        z-index:3;
        left:40px;
        bottom:23px;
        color:rgba(255,255,255,.72);
        font-size:10px;
        font-weight:700;
        letter-spacing:.06em;
        text-transform:uppercase;
    }

    /* WORKSPACE HEADING */
    .workspace-head {
        display:flex;
        align-items:flex-end;
        justify-content:space-between;
        gap:16px;
        margin:4px 2px 14px 2px;
    }
    .cc-greeting {
        flex:0 0 auto;
        display:inline-flex;
        align-items:center;
        min-height:36px;
        padding:0 14px;
        border-radius:999px;
        background:#FFFFFF;
        border:1px solid #DCE5EE;
        color:#234461;
        font-size:13px;
        font-weight:750;
        box-shadow:0 5px 14px rgba(17,45,78,.06);
        white-space:nowrap;
    }
    .workspace-title {
        color:#0C2138;
        font-size:23px;
        line-height:1.15;
        font-weight:830;
        letter-spacing:-.022em;
    }
    .workspace-note {
        color:#75859A;
        font-size:11.5px;
        margin-top:5px;
    }


    /* PREMIUM ROOM CARDS */
    .room-card {
        position:relative;
        min-height:238px;
        padding:24px 24px 22px 26px;
        overflow:hidden;
        background:linear-gradient(145deg,#FFFFFF 0%,#F7FAFE 56%,#EEF4FB 100%);
        border:1px solid #D7E1ED;
        border-radius:22px;
        box-shadow:0 16px 38px rgba(16,42,76,.10), inset 0 1px 0 rgba(255,255,255,.90);
        transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease;
    }
    .room-card.shop {
        background:linear-gradient(145deg,#FFFFFF 0%,#F6FBFB 56%,#EAF5F4 100%);
        border-color:#D5E6E5;
    }
    .room-card:hover {
        transform:translateY(-3px);
        border-color:#C6D5E6;
        box-shadow:0 20px 42px rgba(16,42,76,.13), inset 0 1px 0 rgba(255,255,255,.95);
    }
    .room-card::before {
        content:"";
        position:absolute;
        left:0; top:0; right:0;
        height:4px;
        background:linear-gradient(90deg,#0D4D93,#3C8AE0 58%,#73B5FF);
    }
    .room-card.shop::before {
        background:linear-gradient(90deg,#0C666B,#2E9999 58%,#71C8BD);
    }
    .room-card::after {
        content:"";
        position:absolute;
        right:-80px;
        top:-90px;
        width:220px;
        height:220px;
        border-radius:50%;
        background:radial-gradient(circle,rgba(31,110,210,.07) 0%,rgba(31,110,210,0) 68%);
        pointer-events:none;
    }
    .room-card.shop::after {
        background:radial-gradient(circle,rgba(32,154,155,.075) 0%,rgba(32,154,155,0) 68%);
    }

    .room-topline {
        position:relative;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:14px;
        margin:-20px -20px 18px -22px;
        padding:22px 22px 20px 22px;
        border-radius:18px;
        background:linear-gradient(118deg,#0B2443 0%,#123B68 58%,#1D5A9D 100%);
        box-shadow:0 12px 24px rgba(11,36,67,.13);
        overflow:hidden;
    }
    .room-card.shop .room-topline {
        background:linear-gradient(118deg,#0C3840 0%,#145C63 58%,#27898A 100%);
        box-shadow:0 12px 24px rgba(12,56,64,.13);
    }
    .room-topline::after {
        content:"";
        position:absolute;
        width:170px;
        height:170px;
        right:-70px;
        top:-95px;
        border-radius:50%;
        background:radial-gradient(circle,rgba(255,255,255,.17),rgba(255,255,255,0) 68%);
        pointer-events:none;
    }
    .room-head {
        display:flex;
        align-items:center;
        gap:13px;
        min-width:0;
    }
    .room-icon {
        width:47px;
        height:47px;
        flex:0 0 47px;
        border-radius:14px;
        display:flex;
        align-items:center;
        justify-content:center;
        background:rgba(255,255,255,.12);
        border:1px solid rgba(255,255,255,.16);
        color:#FFFFFF;
        font-size:21px;
        font-weight:850;
        box-shadow:inset 0 1px 0 rgba(255,255,255,.08);
        backdrop-filter:blur(4px);
    }
    .room-card.shop .room-icon {
        background:rgba(255,255,255,.12);
        box-shadow:inset 0 1px 0 rgba(255,255,255,.08);
    }
    .room-code {
        color:rgba(225,238,252,.78);
        font-size:9px;
        font-weight:850;
        letter-spacing:.12em;
        text-transform:uppercase;
        margin-bottom:5px;
    }
    .room-title {
        color:#FFFFFF;
        font-size:21px;
        line-height:1.15;
        font-weight:835;
        letter-spacing:-.02em;
    }
    .room-number {
        position:relative;
        z-index:2;
        flex:0 0 auto;
        color:rgba(255,255,255,.24);
        font-size:34px;
        line-height:1;
        font-weight:860;
        letter-spacing:-.04em;
        padding-top:2px;
    }
    .room-grid {
        display:grid;
        grid-template-columns:repeat(3,minmax(0,1fr));
        gap:10px;
        margin-top:2px;
    }
    .room-item {
        position:relative;
        min-height:96px;
        padding:14px 15px 15px 15px;
        border-radius:14px;
        background:linear-gradient(180deg,rgba(255,255,255,.96),rgba(247,250,254,.90));
        border:1px solid rgba(202,216,233,.96);
        box-shadow:0 5px 14px rgba(30,55,88,.045), inset 0 1px 0 rgba(255,255,255,.96);
        display:flex;
        flex-direction:column;
        align-items:flex-start;
        justify-content:flex-start;
    }
    .room-card.shop .room-item {
        border-color:rgba(205,226,224,.95);
        background:rgba(255,255,255,.74);
    }
    .room-item::before {
        content:"";
        display:block;
        width:22px;
        height:2px;
        border-radius:999px;
        background:#4E8DD6;
        margin-bottom:8px;
        opacity:.75;
    }
    .room-card.shop .room-item::before {
        background:#4CA3A1;
    }
    .item-label {
        color:#71839A;
        font-size:8.4px;
        line-height:1.15;
        font-weight:850;
        letter-spacing:.085em;
        text-transform:uppercase;
        min-height:19px;
        display:flex;
        align-items:center;
        white-space:nowrap;
    }
    .item-value {
        color:#102238;
        font-size:14.5px;
        line-height:1.22;
        font-weight:810;
        margin-top:7px;
        letter-spacing:-.012em;
        max-width:100%;
    }

    /* buttons feel like integrated module launchers */
    .stButton > button {
        min-height:50px !important;
        margin-top:10px !important;
        border-radius:14px !important;
        border:1px solid rgba(255,255,255,.08) !important;
        background:linear-gradient(115deg,#0A2442 0%,#123D6A 55%,#1C5B9D 100%) !important;
        color:#FFFFFF !important;
        font-size:13px !important;
        font-weight:800 !important;
        letter-spacing:.01em !important;
        box-shadow:0 11px 24px rgba(11,36,67,.16) !important;
        transition:all .16s ease !important;
    }
    .stButton > button:hover {
        transform:translateY(-1px) !important;
        border-color:rgba(255,255,255,.12) !important;
        background:linear-gradient(115deg,#0C2A4D 0%,#174B7F 55%,#2571B8 100%) !important;
        box-shadow:0 15px 28px rgba(11,36,67,.22) !important;
    }
    .open-rel .stButton > button,
    .open-shop .stButton > button {
        color:#FFFFFF !important;
    }

    .home-footer {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:12px;
        margin-top:23px;
        padding:11px 14px;
        border:1px solid #E2E8F0;
        border-radius:13px;
        background:#F9FBFD;
        color:#7B8797;
        font-size:10.5px;
    }
    .ready-dot {
        display:inline-block;
        width:7px;
        height:7px;
        margin-right:7px;
        border-radius:50%;
        background:#45A56A;
    }
    .home-footer strong {
        color:#405065;
        font-weight:780;
    }

    @media(max-width:1080px) {
        .hero-copy { width:58%; }
        .hero-title { font-size:34px; }
        .hero-logo { width:165px; }
    }
    @media(max-width:780px) {
        .home-hero {
            min-height:0;
            aspect-ratio:2058 / 548;
            background-size:contain;
            background-position:center center;
            background-color:#0A2443;
        }
        .hero-copy {
            width:auto;
            min-height:350px;
            padding:28px 24px;
            background:linear-gradient(90deg,rgba(5,24,48,.92),rgba(5,24,48,.58));
        }
        .hero-title { font-size:29px; }
        .hero-logo { width:125px; right:18px; top:18px; }
        .hero-footer { left:24px; bottom:18px; }
        .workspace-head { align-items:flex-start; flex-direction:column; gap:8px; }
        .cc-greeting { min-height:32px; padding:0 12px; font-size:12px; }
        .room-grid { grid-template-columns:1fr; }
        .home-footer { align-items:flex-start; flex-direction:column; gap:5px; }
    }
    </style>
    """.replace("__PLANE_URI__", PLANE_URI),
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="home-hero" role="img" aria-label="Garuda Indonesia Boeing 777 Powerplant Engineering Control Center"></div>
    """,
    unsafe_allow_html=True,
)

display_name = escape(str(st.session_state.get("cc_user", "User")).strip() or "User")
st.markdown(
    f"""
    <div class="workspace-head">
        <div>
            <div class="workspace-title">Powerplant Operations Workspace</div>
            <div class="workspace-note">One entry point for reliability intelligence and shop-visit execution monitoring.</div>
        </div>
        <div class="cc-greeting">Hi, {display_name}!</div>
    </div>
    """,
    unsafe_allow_html=True,
)

left, middle, right = st.columns(3, gap="large")

with left:
    st.markdown(
        """
        <div class="room-card">
            <div class="room-topline">
                <div class="room-head">
                    <div class="room-icon">↗</div>
                    <div>
                        <div class="room-code">Reliability Intelligence</div>
                        <div class="room-title">Reliability & Technical Delay</div>
                    </div>
                </div>
                <div class="room-number">01</div>
            </div>
            <div class="room-grid">
                <div class="room-item"><div class="item-label">Performance</div><div class="item-value">Delay & Rate</div></div>
                <div class="room-item"><div class="item-label">Investigation</div><div class="item-value">ATA / Repetitive</div></div>
                <div class="room-item"><div class="item-label">Components</div><div class="item-value">Unscheduled Removal</div></div>
            </div>
                    </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="open-rel">', unsafe_allow_html=True)
    if st.button("Open Reliability Room  →", use_container_width=True, key="open_rel_v35"):
        st.switch_page("reliability_page.py")
    st.markdown("</div>", unsafe_allow_html=True)

with middle:
    st.markdown(
        """
        <div class="room-card shop">
            <div class="room-topline">
                <div class="room-head">
                    <div class="room-icon">⚙</div>
                    <div>
                        <div class="room-code">Shop Visit Execution</div>
                        <div class="room-title">Engine Shop Visit</div>
                    </div>
                </div>
                <div class="room-number">02</div>
            </div>
            <div class="room-grid">
                <div class="room-item"><div class="item-label">Execution</div><div class="item-value">Status & TAT</div></div>
                <div class="room-item"><div class="item-label">Release</div><div class="item-value">Scope & Forecast</div></div>
                <div class="room-item"><div class="item-label">Performance</div><div class="item-value">MRO & Cost</div></div>
            </div>
                    </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="open-shop">', unsafe_allow_html=True)
    if st.button("Open Engine Shop Visit Room  →", use_container_width=True, key="open_shop_v35"):
        st.switch_page("engine_shop_visit_page.py")
    st.markdown("</div>", unsafe_allow_html=True)


with right:
    st.markdown(
        """
        <div class="room-card shop">
            <div class="room-topline">
                <div class="room-head">
                    <div class="room-icon">◉</div>
                    <div>
                        <div class="room-code">APU Shop Visit Execution</div>
                        <div class="room-title">APU Shop Visit</div>
                    </div>
                </div>
                <div class="room-number">03</div>
            </div>
            <div class="room-grid">
                <div class="room-item"><div class="item-label">Execution</div><div class="item-value">Status & TAT</div></div>
                <div class="room-item"><div class="item-label">Asset Context</div><div class="item-value">TSN · CSN · TSLV</div></div>
                <div class="room-item"><div class="item-label">Performance</div><div class="item-value">MRO & SV Cost</div></div>
            </div>
                    </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="open-shop">', unsafe_allow_html=True)
    if st.button("Open APU Shop Visit Room  →", use_container_width=True, key="open_apu_shop"):
        st.switch_page("apu_shop_visit_page.py")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="home-footer">
        <div><span class="ready-dot"></span><strong>Control Center ready</strong></div>
        <div>Garuda Indonesia · Powerplant Engineering</div>
    </div>
    """,
    unsafe_allow_html=True,
)
