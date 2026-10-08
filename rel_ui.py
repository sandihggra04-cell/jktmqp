from __future__ import annotations

from datetime import datetime
from html import escape
from base64 import b64encode
from pathlib import Path

import streamlit as st

from rel_config import APP_SUBTITLE, APP_TITLE


CONTROL_CENTER_ROOT = Path(__file__).resolve().parents[3]

def _local_image_data_uri(path: Path, mime: str = "image/png") -> str:
    try:
        data = path.read_bytes()
        return f"data:{mime};base64,{b64encode(data).decode('ascii')}"
    except Exception:
        return ""

def _get_garuda_logo_uri() -> str:
    local_hd = CONTROL_CENTER_ROOT / "garuda_logo_white_ultra_hd.png"
    local_default = CONTROL_CENTER_ROOT / "garuda_logo_white_transparent.png"
    if local_hd.exists():
        uri = _local_image_data_uri(local_hd, "image/png")
        if uri:
            return uri
    if local_default.exists():
        uri = _local_image_data_uri(local_default, "image/png")
        if uri:
            return uri
    return "https://gate.garuda-indonesia.com/assets/garuda/images/logo_white.png"


LIGHT_CSS = r"""
<style>
    :root {
        --pp-navy: #0B2A5B;
        --pp-blue: #0E5AC7;
        --pp-teal: #0C9DB0;
        --pp-bg: #F5F7FA;
        --pp-card: #FFFFFF;
        --pp-border: #E2E8F0;
        --pp-text: #10213B;
        --pp-muted: #64748B;
        --pp-green: #189447;
        --pp-red: #D64545;
        --pp-amber: #C98316;
    }

    html, body, [class*="css"] { font-family: "Segoe UI", Arial, sans-serif; }
    .stApp { background: var(--pp-bg); color: var(--pp-text); }
    .block-container {
        padding-top: 1.05rem;
        padding-bottom: 2.5rem;
        max-width: 1680px;
    }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stHeader"] { background: transparent; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 1px solid #E3E8EF;
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: .55rem; }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown p {
        color: #22334B;
        font-size: 12px;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="input"] > div,
    [data-testid="stSidebar"] .stDateInput > div > div {
        border-radius: 9px !important;
        border-color: #DCE3EC !important;
        min-height: 38px;
        background: #FFFFFF;
    }
    [data-testid="stSidebar"] .stButton > button {
        border-radius: 9px;
        border: 1px solid #DCE3EC;
        font-weight: 600;
    }
    [data-testid="stSidebar"] details {
        border: 1px solid #E4E9F0;
        border-radius: 10px;
        background: #FAFBFD;
    }

    .sidebar-brand {
        padding: 8px 4px 14px 4px;
        margin-bottom: 4px;
        border-bottom: 1px solid #E8EDF3;
    }
    .sidebar-brand-row { display:flex; gap:10px; align-items:center; }
    .sidebar-mark {
        width:38px; height:38px; border-radius:11px;
        display:flex; align-items:center; justify-content:center;
        background: linear-gradient(145deg, #0E5AC7, #08A4B7);
        color:white; font-size:20px; box-shadow:0 5px 14px rgba(14,90,199,.20);
    }
    .sidebar-brand-title { color:#0B2A5B; font-size:14px; font-weight:800; line-height:1.15; }
    .sidebar-brand-sub { color:#66758B; font-size:11px; margin-top:2px; }
    .garuda-sidebar-brand {
        padding-top: 0 !important;
    }
    .garuda-logo-wrap {
        display:flex; align-items:center; justify-content:flex-start;
        min-height:34px; padding:0 1px 6px 1px; overflow:hidden;
    }
    .garuda-corporate-logo {
        display:block; width:220px; max-width:96%; height:auto; object-fit:contain; image-rendering:-webkit-optimize-contrast; image-rendering:crisp-edges;
        filter:none; opacity:1;
    }
    .garuda-brand-divider {
        width:100%; height:1px; margin:2px 0 10px 0;
        background:linear-gradient(90deg, rgba(14,90,199,.78), rgba(12,157,176,.72), rgba(255,255,255,0));
    }
    .garuda-dashboard-lockup { padding:0 1px 1px 1px; }
    .sidebar-section {
        color:#142642; font-size:13px; font-weight:800;
        margin: 14px 0 7px 0;
    }
    .sidebar-status {
        background:#FBFCFE; border:1px solid #DDE4ED; border-radius:12px;
        padding:12px 13px; margin-top:14px;
        box-shadow: 0 2px 8px rgba(16,33,59,.035);
    }
    .sidebar-status-title { font-weight:800; color:#142642; font-size:12px; margin-bottom:8px; }
    .status-ready { color:#168442; font-weight:800; font-size:13px; }
    .status-check { color:#C43D3D; font-weight:800; font-size:13px; }
    .status-dot { font-size:12px; margin-right:6px; }
    .status-row { display:flex; justify-content:space-between; gap:8px; margin-top:8px; font-size:11px; color:#64748B; }
    .status-row b { color:#273950; font-weight:700; }

    /* Top title */
    .pp-topbar {
        display:flex; align-items:flex-start; justify-content:space-between; gap:24px;
        padding: 2px 2px 9px 2px;
    }
    .pp-title { color:#0A2B63; font-size:29px; line-height:1.15; font-weight:800; letter-spacing:-.45px; margin:0; }
    .pp-subtitle { color:#65758B; font-size:13px; margin-top:5px; }
    .pp-updated { color:#607089; font-size:11px; white-space:nowrap; padding-top:7px; text-align:right; }
    .pp-meta-line { color:#7A889A; font-size:10px; margin-top:4px; }

    /* Active analysis period — compact executive scope ribbon */
    .analysis-scope {
        display:flex; align-items:center; gap:0;
        min-height:48px; margin:0 0 10px 0;
        background:#FFFFFF; border:1px solid #DCE4EE; border-left:4px solid #0E5AC7;
        border-radius:11px; overflow:hidden;
        box-shadow:0 2px 8px rgba(18,42,76,.04);
    }
    .scope-primary, .scope-comparator {
        display:flex; align-items:center; gap:10px; min-width:0;
        padding:8px 13px;
    }
    .scope-primary { flex:1 1 auto; }
    .scope-comparator {
        flex:0 1 430px; border-left:1px solid #E5EAF1;
        background:#FAFCFE;
    }
    .scope-icon {
        flex:0 0 30px; width:30px; height:30px; border-radius:8px;
        display:flex; align-items:center; justify-content:center;
        background:#EAF2FF; color:#0E5AC7; font-size:14px; font-weight:900;
    }
    .scope-comparator .scope-icon { background:#EAF7F8; color:#087F8C; }
    .scope-copy { min-width:0; }
    .scope-label {
        color:#6B7B90; font-size:8.5px; font-weight:900; letter-spacing:.62px;
        text-transform:uppercase; margin-bottom:1px;
    }
    .scope-value {
        color:#0B2A5B; font-size:13.5px; font-weight:850; line-height:1.15;
        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
    }
    .scope-comparator .scope-value { color:#165C69; font-size:12.5px; }
    .scope-sub { color:#8190A2; font-size:8.9px; margin-top:2px; line-height:1.2; }
    .scope-pill {
        display:inline-block; margin-left:5px; padding:1px 6px; border-radius:999px;
        background:#EEF4FF; color:#0E5AC7; font-size:7.7px; font-weight:900; vertical-align:1px;
    }
    .scope-mini-status {
        display:inline-flex; align-items:center; padding:2px 7px; border-radius:999px;
        background:#F2F6FA; color:#63758B; border:1px solid #DCE4ED;
        font-size:9px; font-weight:850; white-space:nowrap;
    }
    .scope-footnote {
        color:#8592A4; font-size:9.5px; line-height:1.25; margin:-3px 1px 8px 1px;
    }

    /* KPI cards */
    .kpi-card {
        position:relative;
        background:#FFFFFF;
        border:1px solid #E3E8EF;
        border-radius:15px;
        padding:15px 14px 13px 14px;
        min-height:124px;
        box-shadow: 0 3px 11px rgba(18,42,76,.055);
        overflow:hidden;
    }
    .kpi-head { display:flex; align-items:flex-start; gap:10px; min-height:34px; }
    .kpi-icon {
        flex:0 0 34px; width:34px; height:34px; border-radius:50%;
        display:flex; align-items:center; justify-content:center;
        background:#0D4FA8; color:white; font-size:16px; font-weight:800;
        box-shadow: inset 0 0 0 1px rgba(255,255,255,.18);
    }
    .kpi-icon.teal { background:#0B99AA; }
    .kpi-icon.green { background:#2E9D58; }
    .kpi-icon.purple { background:#6D4EDC; }
    .kpi-icon.red { background:#D94B45; }
    .kpi-icon.amber { background:#D9921E; }
    .kpi-label { color:#24334A; font-size:11.5px; line-height:1.22; font-weight:750; padding-top:2px; }
    .kpi-value { color:#10213B; font-size:26px; font-weight:800; line-height:1.08; margin:8px 0 3px 44px; letter-spacing:-.3px; }
    .kpi-sub { color:#7A8798; font-size:9.8px; margin-left:44px; line-height:1.25; min-height:13px; }
    .kpi-delta { margin:7px 0 0 44px; font-size:10px; font-weight:700; }
    .delta-good { color:var(--pp-green); }
    .delta-bad { color:var(--pp-red); }
    .delta-neutral { color:#7A8798; font-weight:500; }

    /* Section and chart cards */
    .section-title {
        color:#142642; font-size:15px; font-weight:800;
        margin: 9px 0 7px 1px;
    }
    .section-kicker { color:#708096; font-size:10.5px; margin-top:-4px; margin-bottom:8px; }
    div[data-testid="stPlotlyChart"] {
        background:#FFFFFF;
        border:1px solid #E3E8EF;
        border-radius:14px;
        padding: 2px 6px 1px 6px;
        box-shadow:0 2px 9px rgba(16,33,59,.045);
    }
    div[data-testid="stDataFrame"] {
        background:#FFFFFF;
        border:1px solid #E3E8EF;
        border-radius:14px;
        overflow:hidden;
        box-shadow:0 2px 9px rgba(16,33,59,.04);
    }


    .kpi-card.green { border-left-color:#2E9D58; }
    .kpi-card.purple { border-left-color:#6D4EDC; }
    .kpi-card.red { border-left-color:#D94B45; }
    .kpi-card.amber { border-left-color:#D9921E; }

    /* Engineering Focus — professional review table */
    .focus-box {
        background:#FFFFFF;
        border:1px solid #D7E1EC;
        border-top:3px solid #0E5AC7;
        border-radius:13px;
        padding:0;
        overflow:hidden;
        box-shadow:0 3px 12px rgba(16,33,59,.055);
    }
    .focus-title-row {
        display:flex; align-items:center; justify-content:space-between; gap:10px;
        padding:10px 13px 9px 13px;
        border-bottom:1px solid #DDE6EF;
        background:#FFFFFF;
    }
    .focus-title-group { display:flex; align-items:center; gap:9px; min-width:0; }
    .focus-title {
        color:#08275A; font-size:17px; line-height:1; font-weight:900;
        letter-spacing:-.08px; text-transform:uppercase; white-space:nowrap;
    }
    .focus-title:before { content:"◎"; color:#0E5AC7; margin-right:6px; }
    .focus-period-inline {
        color:#718197; font-size:11px; font-weight:800; white-space:nowrap;
        padding-left:9px; border-left:1px solid #D7E2EE;
    }
    .focus-priority-badge {
        flex:0 0 auto; background:#EEF4FF; border:1px solid #D2E0F4; color:#0E5AC7;
        border-radius:999px; padding:3px 8px; font-size:9px; font-weight:900;
        text-transform:uppercase; letter-spacing:.45px;
    }
    .focus-table {
        width:100%;
        background:#FFFFFF;
    }
    .focus-table-head,
    .focus-table-row {
        display:grid;
        grid-template-columns:66px minmax(210px, 1fr) minmax(430px, 2.8fr) 112px;
        column-gap:0;
        align-items:center;
    }
    .focus-table-head {
        min-height:36px;
        background:#F4F7FB;
        color:#677B94;
        border-bottom:1px solid #DDE6EF;
        font-size:9.2px;
        line-height:1;
        font-weight:900;
        letter-spacing:.52px;
        text-transform:uppercase;
    }
    .focus-table-head > div,
    .focus-table-row > div {
        padding-left:11px;
        padding-right:11px;
    }
    .focus-table-head > div:not(:last-child),
    .focus-table-row > div:not(:last-child) {
        border-right:1px solid #EDF1F5;
    }
    .focus-table-row {
        min-height:64px;
        color:#1B3352;
        border-bottom:1px solid #E9EEF4;
        background:#FFFFFF;
        font-size:14.2px;
        line-height:1.34;
    }
    .focus-table-row:nth-child(odd) { background:#FBFCFE; }
    .focus-table-row:last-child { border-bottom:0; }
    .focus-table-row[data-level="CRITICAL"] { background:#FDEEEE; }
    .focus-table-row[data-level="HIGH"] { background:#FFF4F1; }
    .focus-table-row[data-level="WATCH"], .focus-table-row[data-level="REVIEW"] { background:#FFF9E9; }
    .focus-table-row[data-level="DATA REVIEW"] { background:#F1F7FF; }
    .focus-table-row[data-level="INFO"], .focus-table-row[data-level="NORMAL"] { background:#F0F8F2; }

    .focus-priority-cell {
        text-align:center;
        color:#0E5AC7;
        font-weight:900;
        font-size:15px;
    }
    .focus-category-cell {
        color:#153765;
        font-weight:850;
        font-size:12px;
        letter-spacing:.06px;
        text-transform:uppercase;
    }
    .focus-signal-cell {
        color:#243B5B;
        font-weight:650;
        font-size:14.4px;
    }
    .focus-status-cell { text-align:center; }
    .focus-level-badge {
        display:inline-flex; align-items:center; justify-content:center;
        min-width:58px; white-space:nowrap; border-radius:999px; padding:4px 8px;
        background:#EEF4FF; border:1px solid #D2E0F4; color:#0E5AC7;
        font-size:9.5px; line-height:1; font-weight:900; letter-spacing:.42px; text-transform:uppercase;
    }
    .focus-level-badge[data-level="CRITICAL"] {
        background:#FFF0F0; border-color:#EFCBCB; color:#C83737;
    }
    .focus-level-badge[data-level="HIGH"] {
        background:#FFF3F1; border-color:#F0D3CF; color:#C94A3F;
    }
    .focus-level-badge[data-level="WATCH"], .focus-level-badge[data-level="REVIEW"] {
        background:#FFF7E8; border-color:#EEDCB1; color:#9B6A08;
    }
    .focus-level-badge[data-level="DATA REVIEW"] {
        background:#EDF4FF; border-color:#CFE0F7; color:#1F5DBA;
    }
    .focus-level-badge[data-level="INFO"], .focus-level-badge[data-level="NORMAL"] {
        background:#EEF8F1; border-color:#D1E7D6; color:#2D7D46;
    }
    @media (max-width: 980px) {
        .focus-title-row { align-items:flex-start; flex-wrap:wrap; }
        .focus-period-inline { border-left:0; padding-left:0; }
        .focus-table-head { display:none; }
        .focus-table-row {
            grid-template-columns:42px minmax(0,1fr) 78px;
            grid-template-areas:
                "priority category status"
                "priority signal status";
            row-gap:2px;
            padding:6px 0;
        }
        .focus-priority-cell { grid-area:priority; }
        .focus-category-cell { grid-area:category; }
        .focus-signal-cell { grid-area:signal; }
        .focus-status-cell { grid-area:status; }
        .focus-table-row > div { border-right:0 !important; }
    }

    .focus-top {
        background:linear-gradient(110deg,#FFFFFF 0%,#F8FBFF 68%,#F0F9FA 100%);
        border:1px solid #DDE6F0; border-radius:15px; padding:12px 14px 13px 14px;
        box-shadow:0 3px 11px rgba(18,42,76,.05); margin:0 0 11px 0;
    }
    .focus-top-head {
        display:flex; align-items:center; gap:10px; color:#0B2A5B;
        font-size:14px; font-weight:850; letter-spacing:.12px; margin-bottom:10px;
    }
    .focus-top-badge {
        display:inline-flex; align-items:center; justify-content:center;
        width:30px; height:30px; border-radius:9px; background:#0E5AC7;
        color:#FFFFFF; font-size:14px; font-weight:900;
    }
    .focus-grid {
        display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:9px;
    }
    .focus-tile {
        display:flex; align-items:flex-start; gap:11px; min-height:74px;
        background:#FFFFFF; border:1px solid #E6EBF1; border-radius:12px;
        padding:12px 13px; color:#253954; font-size:16px; line-height:1.42;
    }
    .focus-tile-num {
        flex:0 0 32px; width:32px; height:32px; border-radius:9px;
        display:flex; align-items:center; justify-content:center;
        background:#EDF4FF; color:#0E5AC7; font-weight:900; font-size:14px;
    }

    .method-note {
        background:#EFF8FA; border:1px solid #D9EEF1; border-left:4px solid #0C9DB0;
        border-radius:9px; padding:10px 12px; color:#33536A; font-size:11px;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap:6px; border-bottom:1px solid #E2E8F0; }
    .stTabs [data-baseweb="tab"] {
        height:38px; border-radius:9px 9px 0 0; padding:0 14px;
        color:#63738A; font-size:12px; font-weight:650;
    }
    .stTabs [aria-selected="true"] { color:#0B2A5B !important; background:#FFFFFF; }

    /* Native metrics used in drill-down */
    [data-testid="stMetric"] {
        background:#FFFFFF; border:1px solid #E3E8EF; border-radius:12px;
        padding:10px 12px; box-shadow:0 2px 8px rgba(16,33,59,.035);
    }

    @media (max-width: 1100px) {
        .pp-title { font-size:24px; }
        .kpi-value { font-size:22px; }
        .pp-updated { display:none; }
        .analysis-scope { flex-direction:column; align-items:stretch; }
        .scope-comparator { border-left:0; border-top:1px solid #E5EAF1; flex-basis:auto; }
        .focus-grid { grid-template-columns:1fr; }
    }


    /* Reader-friendly executive narrative */
    .reading-order {
        display:flex; align-items:center; gap:8px; flex-wrap:wrap;
        margin:2px 0 13px 0; padding:9px 12px;
        background:#F8FAFD; border:1px solid #DFE7F0; border-radius:11px;
        color:#53657D; font-size:11px; font-weight:650;
    }
    .reading-order b { color:#173B6B; font-weight:850; }
    .reading-step {
        display:inline-flex; align-items:center; gap:5px; white-space:nowrap;
    }
    .reading-num {
        display:inline-flex; align-items:center; justify-content:center;
        width:18px; height:18px; border-radius:6px;
        background:#E8F1FF; color:#0E5AC7; font-size:9px; font-weight:900;
    }
    .reading-arrow { color:#9AA8B9; font-weight:900; }

    .metric-guide {
        display:grid; grid-template-columns:minmax(260px,1.1fr) minmax(360px,1.6fr);
        gap:0; margin:7px 0 8px 0;
        border:1px solid #DCE5EF; border-radius:11px; overflow:hidden;
        background:#FFFFFF;
    }
    .metric-guide > div { padding:10px 13px; min-height:58px; }
    .metric-guide > div:not(:last-child) { border-right:1px solid #E6ECF3; }
    .metric-guide-label {
        color:#718197; font-size:8.5px; font-weight:900; letter-spacing:.55px;
        text-transform:uppercase; margin-bottom:4px;
    }
    .metric-guide-value { color:#102F5B; font-size:12px; line-height:1.35; font-weight:750; }
    .metric-guide-formula { color:#0E5AC7; font-size:12px; font-weight:850; }
    .metric-guide.rate { border-left:4px solid #0C9DB0; }
    .metric-guide.contribution { border-left:4px solid #0E5AC7; }
    .metric-guide-note {
        margin:4px 0 11px 0; padding:8px 11px;
        background:#FFF9EB; border:1px solid #F0E0AF; border-radius:9px;
        color:#71530E; font-size:10.5px; line-height:1.4;
    }
    .metric-guide-note.blue {
        background:#F1F6FF; border-color:#D6E3F8; color:#31577F;
    }
    .executive-section-head {
        display:flex; align-items:baseline; gap:9px; margin:16px 0 6px 0;
    }
    .executive-section-first { margin-top:9px; }
    .executive-section-no {
        color:#0E5AC7; font-size:10px; font-weight:900; letter-spacing:.55px;
    }
    .executive-section-title {
        color:#0B2A5B; font-size:15px; font-weight:900; letter-spacing:-.1px;
    }
    .executive-section-desc { color:#718197; font-size:10.5px; font-weight:600; }

    @media (max-width: 980px) {
        .metric-guide { grid-template-columns:1fr; }
        .metric-guide > div:not(:last-child) { border-right:0; border-bottom:1px solid #E6ECF3; }
    }



    /* Sidebar collapse / expand controls — explicit contrast for both states. */
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stSidebar"] button[aria-label="Collapse sidebar"] {
        background:#203A59 !important;
        border:1px solid rgba(255,255,255,.16) !important;
        border-radius:11px !important;
        box-shadow:none !important;
    }
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="stSidebar"] button[aria-label="Collapse sidebar"] svg {
        color:#FFFFFF !important;
        stroke:#FFFFFF !important;
        fill:#FFFFFF !important;
        opacity:1 !important;
    }
    [data-testid="collapsedControl"] button,
    button[aria-label="Expand sidebar"] {
        background:#FFFFFF !important;
        border:1px solid #D7E0EB !important;
        border-radius:11px !important;
        box-shadow:0 2px 7px rgba(16,33,59,.08) !important;
    }
    [data-testid="collapsedControl"] svg,
    button[aria-label="Expand sidebar"] svg {
        color:#334155 !important;
        stroke:#334155 !important;
        fill:#334155 !important;
        opacity:1 !important;
    }

    /* Quick context chips keep the active scope visible without reopening the sidebar */
    .scope-chip-bar {
        display:flex; flex-wrap:wrap; gap:8px; margin:2px 0 14px 0;
    }
    .scope-chip {
        display:inline-flex; align-items:center; gap:8px;
        padding:7px 11px; border-radius:999px;
        background:#FFFFFF; border:1px solid #DCE4EE;
        color:#334155; font-size:12px; font-weight:700;
        box-shadow:0 1px 4px rgba(18,42,76,.03);
    }
    .scope-chip b { color:#0B2A5B; font-size:11px; text-transform:uppercase; letter-spacing:.35px; }

    /* More compact header with stronger information hierarchy */
    .pp-topbar {
        align-items:flex-end;
        padding: 0 2px 8px 2px;
        margin-bottom:2px;
    }
    .pp-title { font-size:26px; letter-spacing:-.40px; }
    .pp-subtitle { font-size:12.5px; margin-top:4px; }
    .pp-updated { font-size:10.8px; padding-top:0; }
    .pp-meta-line { font-size:10px; }

    /* KPI hierarchy: first three cards are the primary management signal */
    .kpi-card.primary {
        min-height:132px;
        border-top:3px solid #0E5AC7;
        box-shadow:0 6px 18px rgba(18,42,76,.08);
    }
    .kpi-card.primary .kpi-value { font-size:31px; }
    .kpi-card.secondary {
        min-height:116px;
        background:#FCFDFE;
    }
    .kpi-card.secondary .kpi-value { font-size:24px; }
    .kpi-card.secondary .kpi-sub { min-height:24px; }

    /* Tabs should read like intentional navigation */
    .stTabs [data-baseweb="tab-list"] {
        gap:10px; border-bottom:1px solid #E2E8F0;
    }
    .stTabs [data-baseweb="tab"] {
        height:42px;
        padding:0 8px 0 8px;
        font-size:14px;
        font-weight:700;
        color:#65748B;
    }
    .stTabs [aria-selected="true"] {
        color:#0B2A5B !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        background:#0E5AC7 !important; height:3px !important;
    }

    /* Executive headings remain prominent but less bulky */
    .executive-section-head { margin: 12px 0 10px 0; }
    .executive-section-title { font-size:15px; }
    .executive-section-desc { font-size:11.5px; }


    /* v3.9 compact sidebar + utility navigation */
    [data-testid="stSidebarUserContent"] {
        padding-top: 0 !important;
        margin-top: -0.35rem !important;
    }
    [data-testid="stSidebar"] .garuda-sidebar-brand {
        margin-top: -3.2rem !important;
        padding-top: 0 !important;
        padding-bottom: 6px !important;
    }
    [data-testid="stSidebar"] .garuda-logo-wrap {
        min-height: 0 !important;
        padding: 0 0 3px 0 !important;
        align-items: flex-start !important;
        justify-content: flex-start !important;
    }
    [data-testid="stSidebar"] .garuda-corporate-logo {
        width: 236px !important;
        max-width: 98% !important;
        image-rendering: -webkit-optimize-contrast !important;
        filter: none !important;
        opacity: 1 !important;
    }
    [data-testid="stSidebar"] .garuda-brand-divider {
        margin: 1px 0 4px 0 !important;
    }
    [data-testid="stPopover"] > button {
        min-height: 34px !important;
        padding: 0 11px !important;
        border-radius: 10px !important;
        border: 1px solid #D6E0EB !important;
        background: #FFFFFF !important;
        color: #38506C !important;
        font-size: 11px !important;
        font-weight: 750 !important;
        box-shadow: 0 2px 8px rgba(16,33,59,.04) !important;
    }
</style>
"""


DARK_CSS = r"""
<style>
    :root {
        --pp-navy: #DCEBFF;
        --pp-blue: #67A7FF;
        --pp-teal: #49C6D5;
        --pp-bg: #0A1220;
        --pp-card: #111B2B;
        --pp-border: #27364A;
        --pp-text: #EAF1FB;
        --pp-muted: #9AABC0;
        --pp-green: #55C67A;
        --pp-red: #FF7878;
        --pp-amber: #F5B64E;
    }

    html, body, [class*="css"] { color-scheme: dark; }
    .stApp, [data-testid="stAppViewContainer"] { background:#0A1220 !important; color:#EAF1FB !important; }
    [data-testid="stHeader"] { background:rgba(10,18,32,.92) !important; }

    /* Sidebar and native controls */
    [data-testid="stSidebar"] { background:#0D1726 !important; border-right:1px solid #26364A !important; }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] span { color:#D7E2F0; }
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="input"] > div,
    [data-testid="stSidebar"] .stDateInput > div > div,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] input {
        background:#111D2E !important; color:#EAF1FB !important; border-color:#304158 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="popover"] > div,
    [data-baseweb="popover"] > div,
    [data-baseweb="menu"] { background:#111D2E !important; color:#EAF1FB !important; }
    [data-testid="stSidebar"] .stButton > button {
        background:#142136 !important; color:#EAF1FB !important; border-color:#304158 !important;
    }
    [data-testid="stSidebar"] details { background:#101B2C !important; border-color:#2A3A50 !important; }
    .sidebar-brand { border-bottom-color:#27364A; }
    .sidebar-brand-title, .sidebar-section, .sidebar-status-title { color:#E6EFFB; }
    .sidebar-brand-sub, .status-row { color:#91A3BA; }
    .sidebar-status { background:#101B2C; border-color:#2B3B51; box-shadow:none; }
    .status-row b { color:#DDE8F5; }

    /* Header / scope */
    .pp-title { color:#E8F1FF; }
    .pp-subtitle, .pp-updated, .pp-meta-line { color:#91A3BA; }
    .analysis-scope { background:#111B2B; border-color:#2A3A50; border-left-color:#4F95F7; box-shadow:none; }
    .scope-comparator { background:#0F1A2A; border-left-color:#29394E; }
    .scope-icon { background:#173156; color:#79B3FF; }
    .scope-comparator .scope-icon { background:#12343B; color:#68D4DE; }
    .scope-label, .scope-sub, .scope-footnote { color:#8FA1B8; }
    .scope-value, .scope-comparator .scope-value { color:#E7F0FC; }
    .scope-pill { background:#173156; color:#83B9FF; }
    .scope-mini-status { background:#172235; color:#A7B7CA; border-color:#304158; }

    /* KPI */
    .kpi-card { background:#111B2B; border-color:#28384D; box-shadow:0 4px 14px rgba(0,0,0,.20); }
    .kpi-label, .kpi-value { color:#EDF4FD; }
    .kpi-sub, .delta-neutral { color:#91A3BA; }

    /* Sections / Plotly / dataframe */
    .section-title, .executive-section-title { color:#E2ECFA; }
    .section-kicker, .executive-section-desc { color:#8FA1B8; }
    .executive-section-no { color:#68A8FF; }
    div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"] {
        background:#111B2B !important; border-color:#28384D !important; box-shadow:none;
    }
    div[data-testid="stDataFrame"] iframe { background:#111B2B !important; }

    /* Engineering Focus */
    .focus-box { background:#111B2B; border-color:#2A3A50; border-top-color:#4F95F7; box-shadow:none; }
    .focus-title-row { background:#111B2B; border-bottom-color:#2A3A50; }
    .focus-title { color:#E7F0FC; }
    .focus-title:before { color:#68A8FF; }
    .focus-period-inline { color:#91A3BA; border-left-color:#2C3C51; }
    .focus-priority-badge { background:#173156; border-color:#274A76; color:#8BC0FF; }
    .focus-table { background:#111B2B; }
    .focus-table-head { background:#142033; color:#92A5BD; border-bottom-color:#2A3A50; }
    .focus-table-head > div:not(:last-child), .focus-table-row > div:not(:last-child) { border-right-color:#253449; }
    .focus-table-row { color:#DCE7F5; border-bottom-color:#26364A; background:#111B2B; }
    .focus-table-row:nth-child(odd) { background:#101A29; }
    .focus-table-row[data-level="CRITICAL"] { background:#2A171B; }
    .focus-table-row[data-level="HIGH"] { background:#2B1C1B; }
    .focus-table-row[data-level="WATCH"], .focus-table-row[data-level="REVIEW"] { background:#2A2415; }
    .focus-table-row[data-level="DATA REVIEW"] { background:#14233A; }
    .focus-table-row[data-level="INFO"], .focus-table-row[data-level="NORMAL"] { background:#14271E; }
    .focus-priority-cell { color:#79B3FF; }
    .focus-category-cell { color:#BBD6FA; }
    .focus-signal-cell { color:#D7E4F3; }
    .focus-level-badge { background:#173156; border-color:#274A76; color:#8BC0FF; }
    .focus-level-badge[data-level="CRITICAL"] { background:#3A1C21; border-color:#6B3039; color:#FF8E98; }
    .focus-level-badge[data-level="HIGH"] { background:#3A211E; border-color:#6E3832; color:#FF9488; }
    .focus-level-badge[data-level="WATCH"], .focus-level-badge[data-level="REVIEW"] { background:#392F17; border-color:#655126; color:#F2C45F; }
    .focus-level-badge[data-level="DATA REVIEW"] { background:#173156; border-color:#274A76; color:#8BC0FF; }
    .focus-level-badge[data-level="INFO"], .focus-level-badge[data-level="NORMAL"] { background:#173523; border-color:#2D6040; color:#78D798; }

    .focus-top { background:linear-gradient(110deg,#111B2B 0%,#101D30 68%,#10262C 100%); border-color:#293A50; box-shadow:none; }
    .focus-top-head { color:#E7F0FC; }
    .focus-tile { background:#111B2B; border-color:#29394D; color:#D7E4F3; }
    .focus-tile-num { background:#173156; color:#83B9FF; }

    /* Notes / tabs / native metrics */
    .method-note { background:#10282D; border-color:#21454C; border-left-color:#36B4C3; color:#B9DADE; }
    .stTabs [data-baseweb="tab-list"] { border-bottom-color:#29394D; }
    .stTabs [data-baseweb="tab"] { color:#9AAEC5; }
    .stTabs [aria-selected="true"] { color:#EAF1FB !important; background:#111B2B !important; }
    [data-testid="stMetric"] { background:#111B2B; border-color:#28384D; box-shadow:none; }
    [data-testid="stMetric"] label, [data-testid="stMetric"] [data-testid="stMetricValue"] { color:#EAF1FB !important; }

    .reading-order { background:#101A29; border-color:#29394D; color:#A0B1C4; }
    .reading-order b { color:#D9E9FF; }
    .reading-num { background:#173156; color:#83B9FF; }
    .reading-arrow { color:#64758B; }
    .metric-guide { background:#111B2B; border-color:#29394D; }
    .metric-guide > div:not(:last-child) { border-color:#29394D; }
    .metric-guide-label { color:#91A3BA; }
    .metric-guide-value { color:#E3EDF9; }
    .metric-guide-formula { color:#75B2FF; }
    .metric-guide-note { background:#2A2415; border-color:#594A20; color:#E5C775; }
    .metric-guide-note.blue { background:#14233A; border-color:#29466B; color:#A9C9EF; }

    /* General Streamlit text / widgets */
    [data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"] { color:#DCE7F5; }
    [data-testid="stCaptionContainer"] { color:#9FB0C4 !important; }
    .stSelectbox label, .stMultiSelect label, .stTextInput label, .stRadio label,
    .stDateInput label, .stFileUploader label, .stNumberInput label,
    .stCheckbox label, .stToggle label { color:#DCE7F5 !important; }

    /* Inputs / select controls */
    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div,
    [data-baseweb="base-input"],
    [data-testid="stDateInput"] input,
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    textarea {
        background:#121F31 !important;
        border-color:#334963 !important;
        color:#EDF4FD !important;
        box-shadow:none !important;
    }
    [data-baseweb="select"] svg,
    [data-baseweb="input"] svg { fill:#9FB3CB !important; color:#9FB3CB !important; }
    [data-baseweb="tag"] { background:#173A63 !important; color:#E5F0FF !important; border-color:#28507C !important; }

    /* Popovers / dropdown menus */
    [data-baseweb="popover"] > div,
    [data-baseweb="menu"],
    [role="listbox"] {
        background:#111D2E !important;
        color:#EAF1FB !important;
        border-color:#31445C !important;
        box-shadow:0 12px 28px rgba(0,0,0,.34) !important;
    }
    [role="option"] { color:#E0EAF7 !important; background:#111D2E !important; }
    [role="option"]:hover, [aria-selected="true"][role="option"] { background:#18304F !important; }

    /* File uploader: remove the bright light-theme drop zone */
    [data-testid="stFileUploader"] {
        background:transparent !important;
        color:#EAF1FB !important;
    }
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploaderDropzone"] {
        background:#111D2E !important;
        border:1px dashed #405873 !important;
        border-radius:12px !important;
        color:#EAF1FB !important;
        box-shadow:inset 0 0 0 1px rgba(255,255,255,.012) !important;
    }
    [data-testid="stFileUploader"] section:hover,
    [data-testid="stFileUploaderDropzone"]:hover {
        background:#14243A !important;
        border-color:#5C8FD0 !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"],
    [data-testid="stFileUploaderDropzoneInstructions"] div,
    [data-testid="stFileUploaderDropzoneInstructions"] span,
    [data-testid="stFileUploaderDropzoneInstructions"] small,
    [data-testid="stFileUploader"] small {
        color:#9FB0C4 !important;
    }
    [data-testid="stFileUploader"] button,
    [data-testid="stFileUploaderDropzone"] button,
    [data-testid="stBaseButton-secondary"] {
        background:#17283F !important;
        color:#EAF2FF !important;
        border:1px solid #405873 !important;
        border-radius:9px !important;
        box-shadow:none !important;
    }
    [data-testid="stFileUploader"] button:hover,
    [data-testid="stBaseButton-secondary"]:hover {
        background:#1B3352 !important;
        border-color:#5C8FD0 !important;
        color:#FFFFFF !important;
    }
    [data-testid="stFileUploader"] svg { color:#8FB9EE !important; fill:#8FB9EE !important; }
    [data-testid="stFileUploaderFile"] {
        background:#101B2C !important;
        border-color:#2E4057 !important;
        color:#DCE7F5 !important;
    }

    /* Buttons */
    .stButton > button, .stDownloadButton > button {
        background:#17283F !important;
        color:#EAF1FB !important;
        border:1px solid #3B506A !important;
        box-shadow:none !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background:#1B3352 !important;
        color:#FFFFFF !important;
        border-color:#5C8FD0 !important;
    }
    .stButton > button[kind="primary"] {
        background:#2563B8 !important;
        border-color:#3677CD !important;
        color:#FFFFFF !important;
    }

    /* Expanders */
    [data-testid="stExpander"], .stExpander {
        background:#101A29 !important;
        border-color:#2D3E54 !important;
        box-shadow:none !important;
    }
    [data-testid="stExpander"] details,
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary:hover {
        background:#101A29 !important;
        color:#E3EDF9 !important;
    }
    [data-testid="stExpander"] summary svg { color:#91A8C4 !important; fill:#91A8C4 !important; }

    /* Checkbox / toggle / radio controls */
    [data-testid="stCheckbox"] label,
    [data-testid="stToggle"] label,
    [data-testid="stRadio"] label { color:#DCE7F5 !important; }
    [data-testid="stCheckbox"] [data-baseweb="checkbox"] > div,
    [data-testid="stToggle"] [role="switch"] { border-color:#3A506A !important; }
    [data-testid="stRadio"] [role="radiogroup"] { color:#DCE7F5 !important; }

    /* Tabs: active state clear without a white block */
    .stTabs [data-baseweb="tab-list"] { gap:2px; background:transparent !important; }
    .stTabs [data-baseweb="tab"] {
        background:transparent !important;
        color:#9FB0C4 !important;
        border-radius:8px 8px 0 0 !important;
    }
    .stTabs [data-baseweb="tab"]:hover { background:#101D2F !important; color:#E4EDF8 !important; }
    .stTabs [aria-selected="true"] { color:#FFFFFF !important; background:#13243A !important; }

    /* Dataframe / tables / toolbar containers */
    [data-testid="stDataFrame"] { background:#111B2B !important; }
    [data-testid="stElementToolbar"] button,
    [data-testid="stElementToolbar"] svg { color:#A8B9CC !important; fill:#A8B9CC !important; }

    /* Alerts */
    [data-testid="stAlert"] { border-color:#33465E !important; }
    [data-testid="stAlert"] p { color:#D8E4F2 !important; }

    /* Scrollbar */
    * { scrollbar-color:#344A64 #0D1726; }
    ::-webkit-scrollbar { width:10px; height:10px; }
    ::-webkit-scrollbar-track { background:#0D1726; }
    ::-webkit-scrollbar-thumb { background:#344A64; border-radius:8px; border:2px solid #0D1726; }
    ::-webkit-scrollbar-thumb:hover { background:#48617F; }

    hr { border-color:#28384D !important; }
</style>
"""


PROFESSIONAL_COMMON_CSS = r"""
<style>
    /* Professional polish layer — presentation only. */
    #MainMenu { visibility:hidden; }
    [data-testid="stAppDeployButton"] { display:none !important; }
    [data-testid="stToolbar"] { right: .55rem !important; }

    .block-container {
        max-width: 1720px;
        padding-top: .7rem;
        padding-bottom: 3rem;
        padding-left: 1.35rem;
        padding-right: 1.35rem;
    }

    /* Header: quieter, denser, more executive. */
    .pp-topbar { padding: 0 2px 7px 2px; align-items:center; }
    .pp-title {
        font-size: 30px; line-height:1.08; font-weight:800;
        letter-spacing:-.55px;
    }
    .pp-subtitle { font-size:14px; margin-top:4px; font-weight:500; }
    .pp-updated { font-size:11.5px; line-height:1.4; padding-top:0; }
    .pp-meta-line { font-size:10.5px; }

    .analysis-scope {
        min-height:44px; margin-bottom:10px; border-radius:10px;
        box-shadow:none;
    }
    .scope-primary, .scope-comparator { padding:7px 12px; }
    .scope-comparator { flex-basis:360px; }
    .scope-icon { width:28px; height:28px; flex-basis:28px; border-radius:7px; }
    .scope-label { font-size:9px; letter-spacing:.72px; }
    .scope-value { font-size:14.5px; }
    .scope-comparator .scope-value { font-size:12.5px; }
    .scope-sub { font-size:9.5px; }
    .scope-footnote { font-size:10px; margin:0 2px 8px; }

    /* KPI row: flatter, denser and less colourful. */
    .kpi-card {
        border-radius:12px; padding:13px 14px 12px;
        min-height:112px; box-shadow:0 2px 7px rgba(16,33,59,.045);
    }
    .kpi-head { min-height:29px; gap:9px; align-items:center; }
    .kpi-icon {
        width:30px; height:30px; flex-basis:30px; border-radius:8px;
        background:#EDF3FA; color:#1E5AA8; font-size:14px;
        box-shadow:none; border:1px solid #DDE7F2;
    }
    .kpi-icon.teal { background:#EDF6F7; color:#167A88; border-color:#D8E9EB; }
    .kpi-icon.green { background:#EEF7F1; color:#2B7C47; border-color:#DAEADF; }
    .kpi-icon.purple { background:#F0EFFA; color:#5A4BB0; border-color:#E1DEF1; }
    .kpi-icon.red { background:#FBF0EF; color:#B84B43; border-color:#EFDAD7; }
    .kpi-icon.amber { background:#FBF4E7; color:#A96F18; border-color:#EDDFC2; }
    .kpi-label { font-size:12.5px; font-weight:750; padding-top:0; }
    .kpi-value {
        margin:9px 0 3px 0; font-size:29px; line-height:1.02;
        letter-spacing:-.55px;
    }
    .kpi-sub { margin-left:0; font-size:10.5px; line-height:1.3; min-height:27px; }
    .kpi-delta { margin:5px 0 0 0; font-size:10.5px; }

    /* Navigation: simple underline rather than card-like tabs. */
    .stTabs [data-baseweb="tab-list"] {
        gap:20px; border-bottom:1px solid #DDE4EC; padding-left:2px;
    }
    .stTabs [data-baseweb="tab"] {
        height:43px; padding:0 1px; border-radius:0;
        font-size:13.5px; font-weight:650; background:transparent !important;
    }
    .stTabs [aria-selected="true"] {
        background:transparent !important; font-weight:800;
    }

    /* Section rhythm and typography. */
    .executive-section-head {
        margin:25px 0 9px; gap:10px; align-items:center;
        padding-bottom:7px; border-bottom:1px solid #E3E9F0;
    }
    .executive-section-first { margin-top:20px; }
    .executive-section-no {
        display:inline-flex; align-items:center; justify-content:center;
        min-width:38px; height:32px; padding:0 10px;
        border-radius:10px; background:#EDF4FF;
        font-size:13.5px; letter-spacing:.35px;
    }
    .executive-section-title { font-size:22px; letter-spacing:-.22px; }
    .executive-section-desc { font-size:13px; font-weight:600; }
    .section-title { font-size:17px; margin:12px 0 8px; }
    .section-kicker { font-size:11.5px; }

    /* Engineering focus as an executive briefing list, not a spreadsheet. */
    .focus-box {
        border-radius:12px; border:1px solid #DCE4ED; border-top:none;
        box-shadow:none; overflow:hidden;
    }
    .focus-briefing-row {
        display:grid; grid-template-columns:54px minmax(0,1fr) 104px;
        align-items:center; gap:14px; min-height:74px;
        padding:12px 15px; border-bottom:1px solid #E6ECF2;
        background:#FFFFFF;
    }
    .focus-briefing-row:last-child { border-bottom:0; }
    .focus-briefing-row[data-level="CRITICAL"] { background:#FFF8F7; }
    .focus-briefing-row[data-level="HIGH"] { background:#FFFAF8; }
    .focus-briefing-row[data-level="WATCH"],
    .focus-briefing-row[data-level="REVIEW"] { background:#FFFCF5; }
    .focus-briefing-row[data-level="INFO"],
    .focus-briefing-row[data-level="NORMAL"] { background:#F8FBF9; }
    .focus-briefing-num {
        width:42px; height:42px; border-radius:10px;
        display:flex; align-items:center; justify-content:center;
        background:#EDF4FF; color:#1D5FB7; font-weight:900; font-size:18px;
    }
    .focus-briefing-copy { min-width:0; }
    .focus-briefing-label {
        color:#24456F; font-size:12.5px; line-height:1.25;
        font-weight:850; letter-spacing:.35px; text-transform:uppercase;
        margin-bottom:5px;
    }
    .focus-briefing-message {
        color:#172F50; font-size:16px; line-height:1.45;
        font-weight:650;
    }
    .focus-briefing-status { text-align:right; }
    .focus-level-badge { font-size:10px; padding:5px 9px; min-width:66px; }

    /* Chart and table surfaces: restrained. */
    div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"] {
        border-radius:11px; box-shadow:none; border-color:#DDE5EE;
    }
    [data-testid="stMetric"] { border-radius:10px; box-shadow:none; }

    /* Native control text is large enough for routine engineering use. */
    .stSelectbox label, .stMultiSelect label, .stTextInput label,
    .stRadio label, .stDateInput label, .stFileUploader label,
    .stNumberInput label, .stCheckbox label, .stToggle label {
        font-size:13px !important; font-weight:650 !important;
    }
    [data-testid="stCaptionContainer"], .stCaption { font-size:11.5px !important; }
    .stRadio [role="radiogroup"] label p { font-size:13px !important; }

    @media (max-width:1100px) {
        .pp-title { font-size:26px; }
        .kpi-value { font-size:25px; }
        .executive-section-desc { display:none; }
        .stTabs [data-baseweb="tab-list"] { gap:13px; }
    }
    @media (max-width:820px) {
        .focus-briefing-row {
            grid-template-columns:42px minmax(0,1fr);
            grid-template-areas:"num copy" "num status";
            gap:5px 10px;
        }
        .focus-briefing-num { grid-area:num; }
        .focus-briefing-copy { grid-area:copy; }
        .focus-briefing-status { grid-area:status; text-align:left; }
    }
</style>
"""

PROFESSIONAL_DARK_CSS = r"""
<style>
    [data-testid="stHeader"] { background:#0B1422 !important; }
    .kpi-card { background:#111C2C; border-color:#293A50; box-shadow:none; }
    .kpi-icon { background:#17283E; color:#8AB9F2; border-color:#30465F; }
    .kpi-icon.teal { background:#153039; color:#73CAD5; border-color:#28505A; }
    .kpi-icon.green { background:#173323; color:#78CE94; border-color:#2A553B; }
    .kpi-icon.purple { background:#252441; color:#ADA2EF; border-color:#414066; }
    .kpi-icon.red { background:#382321; color:#F29A91; border-color:#5A3935; }
    .kpi-icon.amber { background:#362C1C; color:#E9C06D; border-color:#584827; }
    .stTabs [data-baseweb="tab-list"] { border-bottom-color:#2A3A4E; }
    .executive-section-head { border-bottom-color:#2A3A4E; }
    .executive-section-no { background:#173156; color:#8DBFFF; }
    .focus-box { background:#111C2C; border-color:#293A50; }
    .focus-briefing-row { background:#111C2C; border-bottom-color:#293A50; }
    .focus-briefing-row[data-level="CRITICAL"] { background:#25191D; }
    .focus-briefing-row[data-level="HIGH"] { background:#251C1B; }
    .focus-briefing-row[data-level="WATCH"],
    .focus-briefing-row[data-level="REVIEW"] { background:#252216; }
    .focus-briefing-row[data-level="INFO"],
    .focus-briefing-row[data-level="NORMAL"] { background:#15231B; }
    .focus-briefing-num { background:#173156; color:#8DBFFF; }
    .focus-briefing-label { color:#B8D2F3; }
    .focus-briefing-message { color:#E0EAF6; }
    div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"] {
        border-color:#293A50 !important;
    }
</style>
"""



V16_VISUAL_SKIN_CSS = r"""
<style>
    /* ============================================================
       V16-inspired visual skin
       Presentation only: dashboard logic/content is unchanged.
       ============================================================ */
    :root {
        --pp-navy: #0B1F33;
        --pp-blue: #245B9E;
        --pp-teal: #448F92;
        --pp-bg: #F6F8FB;
        --pp-card: #FFFFFF;
        --pp-border: #E5EAF0;
        --pp-text: #142033;
        --pp-muted: #667085;
        --pp-green: #2B7C47;
        --pp-red: #B84B43;
        --pp-amber: #A96F18;
    }

    html, body, [class*="css"] {
        font-family: "Segoe UI", Arial, sans-serif;
    }

    .stApp {
        background: #F6F8FB !important;
        color: #142033 !important;
    }

    .block-container {
        max-width: 1600px !important;
        padding-top: 1rem !important;
        padding-bottom: 2.4rem !important;
        padding-left: 1.45rem !important;
        padding-right: 1.45rem !important;
    }

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    /* ---------- Left navigation / control rail ---------- */
    [data-testid="stSidebar"] {
        background: #0B1F33 !important;
        border-right: none !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: .25rem !important;
    }
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"] {
        padding-top: 0 !important;
        margin-top: -0.25rem !important;
    }

    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #E8EEF6 !important;
    }

    [data-testid="stSidebar"] .sidebar-brand {
        padding: 0 3px 12px 3px !important;
        margin-top: -16px !important;
        margin-bottom: 6px !important;
        border-bottom: 1px solid rgba(255,255,255,.11) !important;
    }

    [data-testid="stSidebar"] .sidebar-mark {
        width: 38px !important;
        height: 38px !important;
        border-radius: 11px !important;
        background: #245B9E !important;
        color: #FFFFFF !important;
        box-shadow: none !important;
    }

    [data-testid="stSidebar"] .sidebar-brand-title {
        color: #FFFFFF !important;
        font-size: 14px !important;
        font-weight: 800 !important;
    }

    [data-testid="stSidebar"] .sidebar-brand-sub {
        color: #B7C3D3 !important;
        font-size: 11px !important;
    }

    [data-testid="stSidebar"] .garuda-logo-wrap {
        min-height: 12px !important;
        padding: 0 !important;
        align-items: flex-start !important;
        justify-content: flex-start !important;
    }
    [data-testid="stSidebar"] .garuda-corporate-logo {
        width: 214px !important;
        max-width: 94% !important;
        image-rendering: -webkit-optimize-contrast !important;
        filter: none !important;
        opacity: 1 !important;
        height: auto !important;
    }
    [data-testid="stSidebar"] .garuda-brand-divider {
        margin: 1px 0 10px 0 !important;
        background: linear-gradient(90deg,#2F78C8 0%,#24A6B6 48%,rgba(255,255,255,0) 100%) !important;
    }

    [data-testid="stSidebar"] .cc-nav-label {
        margin: 12px 1px 7px 1px;
        color:#8FA4BD !important;
        font-size:9.5px !important;
        font-weight:850 !important;
        letter-spacing:.12em !important;
        text-transform:uppercase !important;
    }
    [data-testid="stSidebar"] .cc-nav-active {
        display:flex; align-items:center; gap:9px;
        width:100%; min-height:38px; box-sizing:border-box;
        padding:9px 11px; margin:4px 0; border-radius:10px;
        background:linear-gradient(90deg,rgba(36,91,158,.95),rgba(36,91,158,.68));
        border:1px solid rgba(122,174,235,.22);
        color:#FFFFFF !important; font-size:11.5px !important; font-weight:800 !important;
        box-shadow:0 4px 12px rgba(0,0,0,.08);
    }
    [data-testid="stSidebar"] .cc-nav-active .nav-dot {
        width:7px; height:7px; border-radius:50%; background:#7ED4DF; flex:0 0 7px;
    }
    [data-testid="stSidebar"] .cc-nav-button-note {
        color:#8FA4BD !important; font-size:9.5px !important; margin:7px 1px 10px 1px !important;
    }

    [data-testid="stSidebar"] .sidebar-section {
        color: #F8FAFC !important;
        font-size: 12px !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: .045em !important;
        margin-top: 16px !important;
    }

    [data-testid="stSidebar"] .sidebar-status {
        background: rgba(255,255,255,.075) !important;
        border: 1px solid rgba(255,255,255,.11) !important;
        border-radius: 13px !important;
        box-shadow: none !important;
    }

    [data-testid="stSidebar"] .sidebar-status-title {
        color: #FFFFFF !important;
    }

    [data-testid="stSidebar"] .status-ready {
        color: #83D6A0 !important;
    }

    [data-testid="stSidebar"] .status-check {
        color: #FF9C96 !important;
    }

    [data-testid="stSidebar"] .status-row {
        color: #B7C3D3 !important;
    }

    [data-testid="stSidebar"] .status-row b {
        color: #FFFFFF !important;
    }

    /* Native controls: white inputs on navy rail, same visual language as v16. */
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="input"] > div,
    [data-testid="stSidebar"] .stDateInput > div > div,
    [data-testid="stSidebar"] textarea {
        background: #FFFFFF !important;
        border-color: rgba(255,255,255,.16) !important;
        border-radius: 11px !important;
        min-height: 40px !important;
        color: #142033 !important;
        box-shadow: none !important;
    }

    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [data-baseweb="select"] span,
    [data-testid="stSidebar"] [data-baseweb="select"] div {
        color: #142033 !important;
    }

    [data-testid="stSidebar"] [data-baseweb="tag"] {
        background: #E7EFFA !important;
        color: #245B9E !important;
        border-color: #C8D8EC !important;
    }

    [data-testid="stSidebar"] details {
        background: rgba(255,255,255,.055) !important;
        border: 1px solid rgba(255,255,255,.10) !important;
        border-radius: 12px !important;
    }

    [data-testid="stSidebar"] details summary,
    [data-testid="stSidebar"] details summary span,
    [data-testid="stSidebar"] details summary p {
        color: #F8FAFC !important;
    }

    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] .stDownloadButton > button,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
        border-radius: 11px !important;
        border: 1px solid rgba(255,255,255,.10) !important;
        background: #245B9E !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        box-shadow: none !important;
    }

    [data-testid="stSidebar"] .stButton > button:hover,
    [data-testid="stSidebar"] .stDownloadButton > button:hover,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button:hover {
        background: #2D68AF !important;
        color: #FFFFFF !important;
    }

    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background: rgba(255,255,255,.05) !important;
        border-color: rgba(255,255,255,.15) !important;
        border-radius: 12px !important;
    }

    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] small,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] p {
        color: #C8D3E0 !important;
    }

    /* ---------- Main header becomes the v16-style hero ---------- */
    .pp-topbar {
        background: linear-gradient(120deg,#0B1F33,#153B63 58%,#245B9E) !important;
        border-radius: 18px !important;
        padding: 20px 25px !important;
        margin: 0 0 13px 0 !important;
        min-height: 118px !important;
        align-items: center !important;
        box-shadow: 0 8px 28px rgba(11,31,51,.12) !important;
    }

    .pp-title {
        color: #FFFFFF !important;
        font-size: 30px !important;
        font-weight: 780 !important;
        letter-spacing: -.45px !important;
    }

    .pp-subtitle {
        color: #D7E3F1 !important;
        font-size: 14px !important;
        margin-top: 6px !important;
    }

    .pp-updated {
        color: #F4F7FB !important;
        font-size: 11.5px !important;
    }

    .pp-meta-line {
        color: #C8D6E7 !important;
        font-size: 10.5px !important;
    }

    /* ---------- Analysis scope ribbon ---------- */
    .analysis-scope {
        background: #FFFFFF !important;
        border: 1px solid #E5EAF0 !important;
        border-left: 4px solid #245B9E !important;
        border-radius: 14px !important;
        min-height: 50px !important;
        box-shadow: 0 2px 10px rgba(16,24,40,.03) !important;
    }

    .scope-comparator {
        background: #F9FBFD !important;
        border-left-color: #E5EAF0 !important;
    }

    .scope-icon {
        background: #EAF1F9 !important;
        color: #245B9E !important;
    }

    .scope-comparator .scope-icon {
        background: #EDF5F5 !important;
        color: #448F92 !important;
    }

    .scope-label,
    .scope-sub,
    .scope-footnote {
        color: #667085 !important;
    }

    .scope-value {
        color: #142033 !important;
    }

    .scope-pill {
        background: #EAF1F9 !important;
        color: #245B9E !important;
    }

    /* ---------- KPI / native metric cards ---------- */
    .kpi-card,
    [data-testid="stMetric"] {
        background: #FFFFFF !important;
        border: 1px solid #E5EAF0 !important;
        border-radius: 14px !important;
        box-shadow: 0 2px 10px rgba(16,24,40,.03) !important;
    }

    .kpi-card {
        padding: 14px 15px 13px !important;
        min-height: 116px !important;
    }

    .kpi-label,
    [data-testid="stMetricLabel"] {
        color: #667085 !important;
    }

    .kpi-value,
    [data-testid="stMetricValue"] {
        color: #0B1F33 !important;
    }

    .kpi-icon {
        background: #EAF1F9 !important;
        border-color: #D5E0EE !important;
        color: #245B9E !important;
    }

    .kpi-icon.teal { background:#EDF5F5 !important; color:#448F92 !important; border-color:#D6E6E7 !important; }
    .kpi-icon.green { background:#EEF7F1 !important; color:#2B7C47 !important; border-color:#DAEADF !important; }
    .kpi-icon.purple { background:#F0EFFA !important; color:#5A4BB0 !important; border-color:#E1DEF1 !important; }
    .kpi-icon.red { background:#FBF0EF !important; color:#B84B43 !important; border-color:#EFDAD7 !important; }
    .kpi-icon.amber { background:#FBF4E7 !important; color:#A96F18 !important; border-color:#EDDFC2 !important; }

    /* ---------- Tabs / navigation ---------- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 22px !important;
        border-bottom: 1px solid #DDE4EC !important;
        padding-left: 2px !important;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: #667085 !important;
        height: 43px !important;
        padding: 0 1px !important;
        border-radius: 0 !important;
        font-weight: 650 !important;
    }

    .stTabs [aria-selected="true"] {
        background: transparent !important;
        color: #245B9E !important;
        font-weight: 800 !important;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #245B9E !important;
    }

    /* ---------- Section rhythm ---------- */
    .section-title,
    .executive-section-title {
        color: #0B1F33 !important;
    }

    .section-kicker,
    .executive-section-desc {
        color: #667085 !important;
    }

    .executive-section-head {
        border-bottom-color: #E5EAF0 !important;
    }

    .executive-section-no {
        background: #EAF1F9 !important;
        color: #245B9E !important;
    }

    /* ---------- Focus / briefing surfaces ---------- */
    .focus-box {
        background: #FFFFFF !important;
        border: 1px solid #E5EAF0 !important;
        border-radius: 14px !important;
        box-shadow: 0 2px 10px rgba(16,24,40,.03) !important;
    }

    .focus-briefing-row {
        background: #FFFFFF !important;
        border-bottom-color: #E5EAF0 !important;
    }

    .focus-briefing-row[data-level="CRITICAL"] { background:#FFF8F7 !important; }
    .focus-briefing-row[data-level="HIGH"] { background:#FFFAF8 !important; }
    .focus-briefing-row[data-level="WATCH"],
    .focus-briefing-row[data-level="REVIEW"] { background:#FFFCF5 !important; }
    .focus-briefing-row[data-level="INFO"],
    .focus-briefing-row[data-level="NORMAL"] { background:#F8FBF9 !important; }

    .focus-briefing-num {
        background: #EAF1F9 !important;
        color: #245B9E !important;
    }

    .focus-briefing-label {
        color: #245B9E !important;
    }

    .focus-briefing-message {
        color: #142033 !important;
    }

    /* ---------- Charts / tables / native controls ---------- */
    div[data-testid="stPlotlyChart"],
    div[data-testid="stDataFrame"] {
        background: #FFFFFF !important;
        border: 1px solid #E5EAF0 !important;
        border-radius: 14px !important;
        box-shadow: 0 2px 10px rgba(16,24,40,.03) !important;
    }

    .stButton > button,
    .stDownloadButton > button {
        border-radius: 11px !important;
        border-color: #D8E1EC !important;
        box-shadow: none !important;
    }

    .stButton > button[kind="primary"] {
        background: #245B9E !important;
        color: #FFFFFF !important;
        border-color: #245B9E !important;
    }

    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div,
    .stDateInput > div > div,
    textarea {
        border-radius: 11px !important;
    }

    /* ---------- Alerts / notes ---------- */
    [data-testid="stAlert"] {
        border-radius: 12px !important;
    }

    .method-note,
    .metric-guide,
    .reading-order {
        border-radius: 13px !important;
    }

    /* Keep full dashboard readable on normal laptop screens. */
    @media (max-width: 1100px) {
        .pp-topbar { min-height: 105px !important; padding: 17px 20px !important; }
        .pp-title { font-size: 27px !important; }
        .pp-updated { max-width: 38%; }
    }
</style>
"""


PREMIUM_COMMON_CSS = r"""
<style>
    /* ============================================================
       Premium UI hardening
       Final typography / spacing layer. Logic is untouched.
       ============================================================ */

    html, body, [class*="css"] {
        font-family: "Segoe UI", Inter, Arial, sans-serif !important;
        font-size: 14px;
        -webkit-font-smoothing: antialiased;
        text-rendering: optimizeLegibility;
    }

    /* Main information hierarchy */
    .pp-title {
        font-size: 30px !important;
        line-height: 1.12 !important;
        font-weight: 780 !important;
        letter-spacing: -.42px !important;
    }
    .pp-subtitle {
        font-size: 13.5px !important;
        line-height: 1.45 !important;
        font-weight: 450 !important;
    }
    .pp-updated { font-size: 11.5px !important; line-height:1.35 !important; }
    .pp-meta-line { font-size: 10.5px !important; line-height:1.35 !important; }

    .section-title,
    .executive-section-title {
        font-size: 17px !important;
        line-height: 1.25 !important;
        font-weight: 780 !important;
        letter-spacing: -.12px !important;
    }
    .section-kicker,
    .executive-section-desc {
        font-size: 11.5px !important;
        line-height: 1.45 !important;
    }

    /* KPI hierarchy: big enough to scan, not oversized. */
    .kpi-label { font-size: 12px !important; line-height:1.28 !important; font-weight:700 !important; }
    .kpi-value { font-size: 27px !important; line-height:1.06 !important; font-weight:800 !important; }
    .kpi-sub { font-size: 10.5px !important; line-height:1.35 !important; }
    .kpi-delta { font-size: 10.5px !important; line-height:1.3 !important; }

    /* Tabs become deliberate navigation rather than generic Streamlit tabs. */
    .stTabs [data-baseweb="tab"] {
        font-size: 13.5px !important;
        font-weight: 650 !important;
        letter-spacing: .01em !important;
        min-height: 43px !important;
    }
    .stTabs [aria-selected="true"] { font-weight: 780 !important; }

    /* Native labels / controls */
    .stSelectbox label,
    .stMultiSelect label,
    .stTextInput label,
    .stRadio label,
    .stDateInput label,
    .stFileUploader label,
    .stNumberInput label,
    .stCheckbox label,
    .stToggle label {
        font-size: 13px !important;
        line-height: 1.35 !important;
        font-weight: 650 !important;
    }
    [data-testid="stCaptionContainer"], .stCaption {
        font-size: 11.5px !important;
        line-height: 1.45 !important;
    }
    .stButton > button,
    .stDownloadButton > button {
        min-height: 40px !important;
        font-size: 13px !important;
        font-weight: 700 !important;
    }

    /* Sidebar hierarchy */
    [data-testid="stSidebar"] .sidebar-brand-title {
        font-size: 15px !important;
        line-height: 1.22 !important;
        font-weight: 800 !important;
    }
    [data-testid="stSidebar"] .sidebar-brand-sub {
        font-size: 11.5px !important;
        line-height:1.4 !important;
    }
    [data-testid="stSidebar"] .sidebar-section {
        font-size: 12px !important;
        line-height:1.25 !important;
        letter-spacing:.075em !important;
        font-weight:800 !important;
    }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        font-size: 13px !important;
        line-height:1.45 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="input"] > div,
    [data-testid="stSidebar"] .stDateInput > div > div {
        min-height: 42px !important;
    }

    /* Expander: robust across Streamlit DOM variants. */
    [data-testid="stSidebar"] [data-testid="stExpander"],
    [data-testid="stSidebar"] .stExpander,
    [data-testid="stSidebar"] details {
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: none !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary > div,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] details summary,
    [data-testid="stSidebar"] details summary > div {
        min-height: 46px !important;
        font-size: 13px !important;
        font-weight: 760 !important;
        line-height: 1.3 !important;
        box-shadow: none !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpanderDetails"] {
        padding-top: 6px !important;
    }

    /* Uploaders: denser and more premium. */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] {
        border-radius: 12px !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        min-height: 92px !important;
        border-radius: 12px !important;
        padding: 12px !important;
        box-shadow: none !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"],
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] div,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] span,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] small,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] small {
        font-size: 11.5px !important;
        line-height: 1.35 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {
        border-radius: 11px !important;
        padding: 8px 10px !important;
        box-shadow:none !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] * {
        font-size: 11.5px !important;
    }

    /* Tables/charts share one visual rhythm. */
    div[data-testid="stPlotlyChart"],
    div[data-testid="stDataFrame"] {
        border-radius: 14px !important;
        overflow: hidden !important;
    }

    /* Standard markdown/body copy */
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li {
        line-height: 1.48;
    }

    @media (max-width: 1180px) {
        .pp-title { font-size: 27px !important; }
        .section-title, .executive-section-title { font-size: 16px !important; }
        .kpi-value { font-size: 25px !important; }
    }
</style>
"""

PREMIUM_LIGHT_CSS = r"""
<style>
    /* Keep the v16 navy control rail while eliminating accidental white blocks. */
    [data-testid="stSidebar"] [data-testid="stExpander"],
    [data-testid="stSidebar"] .stExpander,
    [data-testid="stSidebar"] details {
        background: rgba(255,255,255,.055) !important;
        border: 1px solid rgba(255,255,255,.11) !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary > div,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] details summary,
    [data-testid="stSidebar"] details summary > div,
    [data-testid="stSidebar"] [data-testid="stExpanderDetails"] {
        background: transparent !important;
        color: #F8FAFC !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary p,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary span,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary svg,
    [data-testid="stSidebar"] details summary p,
    [data-testid="stSidebar"] details summary span {
        color: #F8FAFC !important;
        fill: #AFC0D5 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background: rgba(255,255,255,.055) !important;
        border: 1px dashed rgba(255,255,255,.20) !important;
        color: #EAF1F8 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {
        background: rgba(255,255,255,.075) !important;
        border: 1px solid rgba(255,255,255,.12) !important;
        color: #F8FAFC !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] p,
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] span,
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] small {
        color: #E5EDF7 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] button {
        background: rgba(255,255,255,.05) !important;
        border-color: rgba(255,255,255,.12) !important;
        color:#BFD0E4 !important;
    }

    /* Sidebar option controls must stay readable on the navy rail. */
    [data-testid="stSidebar"] [data-testid="stRadio"] label,
    [data-testid="stSidebar"] [data-testid="stRadio"] label p,
    [data-testid="stSidebar"] [data-testid="stRadio"] label span,
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label,
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label *,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label *,
    [data-testid="stSidebar"] [data-testid="stToggle"] label,
    [data-testid="stSidebar"] [data-testid="stToggle"] label * {
        color:#F8FAFC !important;
        opacity:1 !important;
        fill:#F8FAFC !important;
    }
    [data-testid="stSidebar"] [data-baseweb="radio"] *,
    [data-testid="stSidebar"] [data-baseweb="checkbox"] * {
        color:#F8FAFC !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] p,
    [data-testid="stSidebar"] [data-testid="stToggle"] p,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] p {
        font-size:13.5px !important;
        font-weight:650 !important;
        line-height:1.4 !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radio"] > div:first-child,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] [data-baseweb="checkbox"] > div:first-child {
        border-color:rgba(255,255,255,.45) !important;
    }
</style>
"""

PREMIUM_DARK_CSS = r"""
<style>
    /* Dark mode final pass — no white/light surface may leak into the navy rail. */
    [data-testid="stSidebar"] {
        background:#0B1F33 !important;
        border-right:1px solid #22364D !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"],
    [data-testid="stSidebar"] .stExpander,
    [data-testid="stSidebar"] details {
        background:#12243A !important;
        border:1px solid #29415C !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary > div,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] [data-testid="stExpanderDetails"],
    [data-testid="stSidebar"] details summary,
    [data-testid="stSidebar"] details summary > div {
        background:#12243A !important;
        color:#F4F8FD !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary p,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary span,
    [data-testid="stSidebar"] details summary p,
    [data-testid="stSidebar"] details summary span {
        color:#F4F8FD !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary svg,
    [data-testid="stSidebar"] details summary svg {
        color:#9FB8D4 !important;
        fill:#9FB8D4 !important;
    }

    /* Inputs stay distinct, but are dark rather than bright white. */
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="input"] > div,
    [data-testid="stSidebar"] .stDateInput > div > div,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] input {
        background:#16283E !important;
        color:#F3F7FC !important;
        border-color:#36516D !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] span,
    [data-testid="stSidebar"] [data-baseweb="select"] div {
        color:#F3F7FC !important;
    }

    [data-testid="stSidebar"] [data-testid="stFileUploader"],
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background:#14273D !important;
        border-color:#3B5876 !important;
        color:#EAF1F8 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"],
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] div,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] span,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] small,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] small {
        color:#B9C8D9 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {
        background:#182D45 !important;
        border:1px solid #385571 !important;
        color:#F4F8FD !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] p,
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] span,
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] small {
        color:#EAF1F8 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
        background:#245B9E !important;
        color:#FFFFFF !important;
        border-color:#356DAF !important;
        font-weight:700 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] button {
        background:transparent !important;
        color:#BFD0E4 !important;
        border-color:transparent !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label,
    [data-testid="stSidebar"] [data-testid="stRadio"] label *,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label *,
    [data-testid="stSidebar"] [data-testid="stToggle"] label,
    [data-testid="stSidebar"] [data-testid="stToggle"] label * {
        color:#F4F8FD !important;
        opacity:1 !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] p,
    [data-testid="stSidebar"] [data-testid="stToggle"] p,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] p {
        font-size:13.5px !important;
        font-weight:650 !important;
        line-height:1.4 !important;
    }

    /* Main dark surfaces use the same navy family as the v16 visual language. */
    .stApp, [data-testid="stAppViewContainer"] {
        background:#0B1422 !important;
        color:#EAF1FB !important;
    }
    .pp-topbar {
        background:linear-gradient(120deg,#0B1F33,#153B63 58%,#245B9E) !important;
    }
    div[data-testid="stPlotlyChart"],
    div[data-testid="stDataFrame"],
    .kpi-card,
    [data-testid="stMetric"] {
        background:#111E30 !important;
        border-color:#293E57 !important;
    }
</style>
"""

EXECUTIVE_REFINED_CSS = r"""
<style>
    .exec-period-bar {
        display:grid; grid-template-columns:minmax(0,1.35fr) 1px minmax(250px,.65fr);
        gap:20px; align-items:center; padding:13px 17px; margin-bottom:8px;
        background:linear-gradient(180deg,#FFFFFF 0%,#FBFCFE 100%);
        border:1px solid #E2E8F0; border-left:4px solid #245B9E; border-radius:14px;
        box-shadow:0 4px 16px rgba(16,33,59,.035);
    }
    .exec-period-label { color:#7A8798; font-size:8.8px; font-weight:850; letter-spacing:.10em; }
    .exec-period-value { color:#102139; font-size:15px; line-height:1.25; font-weight:820; margin-top:3px; }
    .exec-period-value.small { font-size:13px; }
    .exec-period-meta { color:#8895A6; font-size:9.8px; margin-top:2px; }
    .exec-period-divider { width:1px; height:39px; background:#E4EAF1; }

    .scope-context-line {
        display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin:0 2px 12px 2px;
        color:#6F7F91; font-size:10.5px; line-height:1.35;
    }
    .scope-context-prefix { color:#245B9E; font-size:8.8px; font-weight:850; letter-spacing:.09em; }
    .scope-context-sep { color:#C0CAD6; }
    .scope-context-item b { color:#52677F; font-size:9.2px; font-weight:800; text-transform:uppercase; letter-spacing:.04em; margin-right:3px; }
    .scope-context-dot { color:#BCC6D1; padding:0 3px; }

    .kpi-card.primary {
        min-height:123px !important; padding:15px 16px 14px !important; border-radius:16px !important;
        box-shadow:0 7px 22px rgba(16,33,59,.05) !important; border-color:#E1E7EF !important;
    }
    .kpi-card.primary .kpi-value { font-size:29px !important; letter-spacing:-.03em !important; }
    .kpi-card.primary .kpi-sub { min-height:27px !important; color:#8090A3 !important; }
    .kpi-card.primary .kpi-delta { margin-top:5px !important; }

    .secondary-kpi-strip {
        display:grid; grid-template-columns:1fr 1px 1fr; align-items:center; gap:18px; margin:9px 0 12px 0;
        padding:10px 14px; background:#F9FBFD; border:1px solid #E3E9F0; border-radius:13px;
    }
    .secondary-kpi { display:grid; grid-template-columns:minmax(0,1fr) auto; column-gap:14px; row-gap:2px; align-items:center; }
    .secondary-kpi > div:first-child { grid-column:1; grid-row:1; }
    .secondary-kpi-value { grid-column:2; grid-row:1 / span 2; color:#102139; font-size:20px; font-weight:830; letter-spacing:-.02em; }
    .secondary-kpi-delta { grid-column:1; grid-row:2; font-size:9.8px; }
    .secondary-kpi-label { color:#53677E; font-size:10.8px; font-weight:720; vertical-align:middle; }
    .secondary-kpi-icon {
        display:inline-flex; width:23px; height:23px; margin-right:7px; border-radius:7px;
        align-items:center; justify-content:center; font-size:11px; vertical-align:middle;
    }
    .secondary-kpi-icon.red { background:#FBF0EF; color:#B84B43; }
    .secondary-kpi-icon.amber { background:#FBF4E7; color:#A96F18; }
    .secondary-kpi-separator { width:1px; height:35px; background:#E2E8F0; }

    .executive-section-head { margin:18px 0 9px 0 !important; padding-bottom:8px !important; border-bottom:1px solid #E5EAF0 !important; }
    .executive-section-no { display:none !important; }
    .executive-section-title { font-size:17px !important; font-weight:820 !important; letter-spacing:-.015em !important; }
    .executive-section-desc { font-size:10.8px !important; color:#8794A5 !important; margin-left:8px !important; }

    .focus-box { border-radius:15px !important; box-shadow:0 5px 18px rgba(16,33,59,.04) !important; overflow:hidden; }
    .focus-briefing-row {
        grid-template-columns:42px minmax(0,1fr) auto !important; gap:13px !important; min-height:67px !important;
        padding:11px 14px !important; background:#FFFFFF !important;
    }
    .focus-briefing-row[data-level="CRITICAL"], .focus-briefing-row[data-level="HIGH"],
    .focus-briefing-row[data-level="WATCH"], .focus-briefing-row[data-level="REVIEW"],
    .focus-briefing-row[data-level="INFO"], .focus-briefing-row[data-level="NORMAL"] { background:#FFFFFF !important; }
    .focus-briefing-row[data-level="CRITICAL"] { box-shadow:inset 3px 0 0 #C53F37; }
    .focus-briefing-row[data-level="HIGH"] { box-shadow:inset 3px 0 0 #D96B42; }
    .focus-briefing-row[data-level="WATCH"], .focus-briefing-row[data-level="REVIEW"] { box-shadow:inset 3px 0 0 #D5A541; }
    .focus-briefing-row[data-level="INFO"], .focus-briefing-row[data-level="NORMAL"] { box-shadow:inset 3px 0 0 #5A9B70; }
    .focus-briefing-num { width:34px !important; height:34px !important; font-size:12.5px !important; border-radius:10px !important; }
    .focus-briefing-label { font-size:9.3px !important; letter-spacing:.075em !important; margin-bottom:4px !important; }
    .focus-briefing-message { font-size:13.2px !important; line-height:1.4 !important; font-weight:650 !important; }
    .focus-level-badge { min-width:65px !important; padding:5px 9px !important; font-size:8.6px !important; }

    .stTabs [data-baseweb="tab-list"] { gap:16px !important; padding-top:1px !important; }
    .stTabs [data-baseweb="tab"] { font-size:12.2px !important; min-height:39px !important; color:#748195 !important; }

    @media(max-width:1050px) {
        .exec-period-bar { grid-template-columns:1fr; gap:8px; }
        .exec-period-divider { display:none; }
        .secondary-kpi-strip { grid-template-columns:1fr; gap:8px; }
        .secondary-kpi-separator { display:none; }
    }
</style>
"""

EXECUTIVE_HIERARCHY_CSS = r"""
<style>
    /* Unified context panel: full information without visual clutter. */
    .exec-context-card {
        margin: 2px 0 14px 0;
        border:1px solid #DCE4ED;
        border-radius:16px;
        background:linear-gradient(180deg,#FFFFFF 0%,#FBFCFE 100%);
        box-shadow:0 7px 22px rgba(16,33,59,.045);
        overflow:hidden;
    }
    .exec-context-top {
        display:grid;
        grid-template-columns:minmax(0,1.45fr) minmax(300px,.75fr);
        align-items:center;
        gap:18px;
        padding:14px 18px 12px 18px;
    }
    .exec-context-period {
        min-width:0;
    }
    .exec-context-compare {
        min-width:0;
        border-left:1px solid #E4EAF1;
        padding-left:18px;
    }
    .exec-context-eyebrow {
        color:#7A8798;
        font-size:8.7px;
        font-weight:850;
        letter-spacing:.11em;
        text-transform:uppercase;
        margin-bottom:5px;
    }
    .exec-context-period-row,
    .exec-context-compare-row {
        display:flex;
        align-items:center;
        gap:10px;
        flex-wrap:wrap;
    }
    .exec-context-date {
        color:#102139;
        font-size:15px;
        line-height:1.2;
        font-weight:830;
        letter-spacing:-.01em;
    }
    .exec-context-period-pill,
    .exec-context-state {
        display:inline-flex;
        align-items:center;
        min-height:23px;
        padding:4px 8px;
        border-radius:999px;
        background:#EEF4FB;
        border:1px solid #DCE7F3;
        color:#35649A;
        font-size:8.8px;
        font-weight:800;
        letter-spacing:.025em;
    }
    .exec-context-state.ready {
        background:#EDF7F1;
        border-color:#D8EBDD;
        color:#397451;
    }
    .exec-context-state.muted {
        background:#F4F6F8;
        border-color:#E5E9EE;
        color:#7B8796;
    }
    .exec-context-compare strong {
        color:#20364F;
        font-size:12.5px;
        font-weight:800;
    }
    .exec-context-scope {
        display:grid;
        grid-template-columns:repeat(5,minmax(0,1fr));
        border-top:1px solid #E8EDF3;
        background:#F8FAFC;
    }
    .ctx-scope-item {
        position:relative;
        padding:10px 14px 11px 14px;
        min-width:0;
    }
    .ctx-scope-item + .ctx-scope-item {
        border-left:1px solid #E8EDF3;
    }
    .ctx-scope-item span {
        display:block;
        color:#8995A4;
        font-size:8.2px;
        font-weight:850;
        letter-spacing:.075em;
        text-transform:uppercase;
        margin-bottom:3px;
    }
    .ctx-scope-item strong {
        display:block;
        color:#40546C;
        font-size:10.8px;
        line-height:1.25;
        font-weight:740;
        overflow:hidden;
        text-overflow:ellipsis;
        white-space:nowrap;
    }

    /* Performance block gives the KPI row a clear reason to exist. */
    .performance-heading {
        display:flex;
        align-items:flex-end;
        justify-content:space-between;
        gap:14px;
        margin:18px 2px 9px 2px;
    }
    .performance-title {
        color:#102139;
        font-size:17px;
        font-weight:830;
        letter-spacing:-.015em;
    }
    .performance-subtitle {
        color:#8794A5;
        font-size:10.4px;
        font-weight:580;
        margin-top:3px;
    }
    .performance-badge {
        color:#6F7F91;
        font-size:8.5px;
        font-weight:850;
        letter-spacing:.08em;
        padding:5px 8px;
        border-radius:999px;
        border:1px solid #E0E6ED;
        background:#F8FAFC;
    }

    .kpi-card.hero {
        min-height:128px !important;
        border-top:3px solid #245B9E !important;
        background:linear-gradient(180deg,#FFFFFF 0%,#F9FBFE 100%) !important;
        box-shadow:0 10px 28px rgba(36,91,158,.08) !important;
    }
    .kpi-card.hero .kpi-value {
        font-size:32px !important;
        color:#0B2A5B !important;
    }
    .kpi-card.primary {
        min-height:128px !important;
        box-shadow:0 7px 22px rgba(16,33,59,.045) !important;
    }

    .secondary-kpi-strip {
        margin-top:10px !important;
        padding:11px 16px !important;
        border-radius:14px !important;
        background:linear-gradient(180deg,#FAFBFD,#F7F9FC) !important;
    }
    .secondary-kpi {
        grid-template-columns:minmax(0,1fr) auto !important;
        align-items:center !important;
    }
    .secondary-kpi-copy {
        display:flex;
        align-items:center;
        gap:8px;
    }
    .secondary-kpi-note {
        color:#919CAB;
        font-size:9.1px;
        margin-top:2px;
    }
    .secondary-kpi-delta {
        margin-left:31px;
        margin-top:3px;
    }

    /* App-like, restrained navigation. */
    .stTabs [data-baseweb="tab-list"] {
        background:#F4F7FA !important;
        border:1px solid #E1E7EE !important;
        border-radius:12px !important;
        padding:4px !important;
        gap:3px !important;
        margin-top:14px !important;
    }
    .stTabs [data-baseweb="tab"] {
        height:35px !important;
        min-height:35px !important;
        padding:0 12px !important;
        border-radius:9px !important;
        font-size:11.5px !important;
        font-weight:680 !important;
        color:#68788B !important;
    }
    .stTabs [aria-selected="true"] {
        background:#FFFFFF !important;
        color:#183C69 !important;
        box-shadow:0 2px 7px rgba(16,33,59,.08) !important;
        font-weight:820 !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display:none !important;
    }

    /* Engineering priorities: information-rich without looking like a table. */
    .focus-card-grid {
        display:grid;
        grid-template-columns:repeat(3,minmax(0,1fr));
        gap:12px;
        margin:2px 0 8px 0;
    }
    .focus-card {
        position:relative;
        min-height:154px;
        padding:15px 16px 14px 16px;
        border:1px solid #DFE6EE;
        border-radius:15px;
        background:linear-gradient(180deg,#FFFFFF 0%,#FCFDFE 100%);
        box-shadow:0 7px 20px rgba(16,33,59,.045);
        overflow:hidden;
    }
    .focus-card::before {
        content:"";
        position:absolute;
        left:0; right:0; top:0;
        height:3px;
        background:#D5A541;
    }
    .focus-card[data-level="CRITICAL"]::before { background:#C4433B; }
    .focus-card[data-level="HIGH"]::before { background:#D96B42; }
    .focus-card[data-level="WATCH"]::before,
    .focus-card[data-level="REVIEW"]::before { background:#D5A541; }
    .focus-card[data-level="INFO"]::before,
    .focus-card[data-level="NORMAL"]::before { background:#5A9B70; }

    .focus-card-top {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
    }
    .focus-card-index {
        color:#89A0BB;
        font-size:10px;
        font-weight:850;
        letter-spacing:.08em;
    }
    .focus-card-label {
        margin-top:13px;
        color:#607894;
        font-size:9px;
        font-weight:850;
        letter-spacing:.085em;
        text-transform:uppercase;
    }
    .focus-card-key {
        margin-top:5px;
        color:#102139;
        font-size:17px;
        line-height:1.18;
        font-weight:840;
        letter-spacing:-.012em;
    }
    .focus-facts {
        display:flex;
        flex-wrap:wrap;
        gap:6px;
        margin-top:13px;
    }
    .focus-fact {
        display:inline-flex;
        align-items:center;
        padding:5px 7px;
        border-radius:8px;
        background:#F3F6F9;
        border:1px solid #E5EAF0;
        color:#52677F;
        font-size:9.5px;
        line-height:1.2;
        font-weight:650;
    }
    .focus-message-full {
        color:#52677F;
        font-size:11.2px;
        line-height:1.45;
        font-weight:600;
    }
    .focus-level-badge {
        min-width:auto !important;
        padding:4px 7px !important;
        font-size:8px !important;
        letter-spacing:.06em;
    }

    /* Section headers become calmer and more editorial. */
    .executive-section-head {
        margin:22px 0 10px 0 !important;
        padding-bottom:7px !important;
    }
    .executive-section-title {
        font-size:16.5px !important;
    }
    .executive-section-desc {
        font-size:10.3px !important;
        font-weight:580 !important;
    }

    @media(max-width:1150px) {
        .exec-context-scope { grid-template-columns:repeat(3,minmax(0,1fr)); }
        .ctx-scope-item:nth-child(4) { border-left:0; }
        .focus-card-grid { grid-template-columns:1fr; }
    }
    @media(max-width:780px) {
        .exec-context-top { grid-template-columns:1fr; }
        .exec-context-compare { border-left:0; border-top:1px solid #E4EAF1; padding-left:0; padding-top:10px; }
        .exec-context-scope { grid-template-columns:1fr 1fr; }
        .ctx-scope-item:nth-child(odd) { border-left:0; }
        .performance-heading { align-items:flex-start; flex-direction:column; gap:5px; }
    }
</style>
"""


EXECUTIVE_COMPOSITION_CSS = r"""
<style>
    /* The executive page should read as three surfaces, not a collection of cards. */
    .exec-scope-toolbar {
        display:grid;
        grid-template-columns:auto 1px minmax(0,1fr) auto;
        align-items:center;
        gap:16px;
        min-height:62px;
        padding:10px 15px;
        margin:2px 0 13px 0;
        background:#FFFFFF;
        border:1px solid #DFE6EE;
        border-radius:14px;
        box-shadow:0 5px 16px rgba(16,33,59,.035);
    }
    .exec-scope-primary { display:flex; align-items:center; gap:9px; flex-wrap:wrap; }
    .exec-scope-eyebrow { color:#8996A6; font-size:7.8px; font-weight:850; letter-spacing:.1em; text-transform:uppercase; }
    .exec-scope-date { color:#11243D; font-size:13.2px; font-weight:830; white-space:nowrap; }
    .exec-scope-period { color:#315F93; font-size:8.4px; font-weight:800; padding:4px 7px; border-radius:999px; background:#EDF4FC; border:1px solid #DCE8F5; white-space:nowrap; }
    .exec-scope-divider { width:1px; height:32px; background:#E6EBF1; }
    .exec-scope-values { color:#66778B; font-size:10px; line-height:1.55; min-width:0; }
    .ctx-inline b { color:#314A67; font-size:8.4px; letter-spacing:.04em; text-transform:uppercase; margin-right:3px; }
    .ctx-dot { color:#B0BBC7; margin:0 3px; }
    .exec-scope-compare { text-align:right; min-width:165px; }
    .exec-scope-compare-value { color:#233B56; font-size:10.5px; font-weight:780; margin-top:2px; }
    .exec-scope-state { display:inline-flex; margin-top:4px; color:#7A8797; background:#F3F5F7; border:1px solid #E5E9EE; border-radius:999px; padding:3px 6px; font-size:7.8px; font-weight:740; }
    .exec-scope-state.ready { color:#38734F; background:#EDF7F1; border-color:#D6EADB; }

    .exec-performance-wrap {
        background:#FFFFFF;
        border:1px solid #DFE6EE;
        border-radius:17px;
        box-shadow:0 9px 26px rgba(16,33,59,.05);
        overflow:hidden;
        margin:0 0 12px 0;
    }
    .exec-performance-heading { display:flex; align-items:flex-end; justify-content:space-between; padding:15px 18px 11px 18px; border-bottom:1px solid #EDF1F5; }
    .exec-performance-kicker { color:#2C609D; font-size:8.2px; font-weight:900; letter-spacing:.11em; text-transform:uppercase; }
    .exec-performance-title { color:#102139; font-size:16.5px; font-weight:830; margin-top:3px; letter-spacing:-.012em; }
    .exec-performance-status { color:#7A8798; font-size:7.8px; font-weight:850; letter-spacing:.08em; border:1px solid #E2E7ED; border-radius:999px; padding:4px 7px; background:#F8FAFC; }
    .exec-performance-body { display:grid; grid-template-columns:minmax(260px,.9fr) minmax(0,2.1fr); }
    .exec-hero-metric { padding:20px 20px 17px 20px; background:linear-gradient(135deg,#F7FAFE 0%,#FFFFFF 78%); border-right:1px solid #E9EEF4; }
    .exec-metric-label { color:#59718E; font-size:8.5px; font-weight:880; letter-spacing:.085em; text-transform:uppercase; }
    .exec-hero-value { color:#0B2A5B; font-size:36px; line-height:1.05; font-weight:880; letter-spacing:-.035em; margin-top:10px; }
    .exec-hero-value span { font-size:15px; font-weight:740; letter-spacing:0; color:#425A76; }
    .exec-metric-caption { color:#7C899A; font-size:9.5px; margin-top:7px; }
    .exec-metric-delta, .exec-support-delta, .exec-footer-delta { font-size:8.5px; font-weight:680; margin-top:9px; }
    .exec-support-metrics { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); }
    .exec-support-metric { padding:19px 17px 15px 17px; min-width:0; }
    .exec-support-metric + .exec-support-metric { border-left:1px solid #E9EEF4; }
    .exec-support-label { color:#62748A; font-size:9px; font-weight:800; }
    .exec-support-value { color:#102139; font-size:25px; line-height:1.05; font-weight:850; letter-spacing:-.025em; margin-top:10px; }
    .exec-support-caption { color:#8794A4; font-size:8.8px; line-height:1.35; margin-top:7px; min-height:24px; }
    .exec-performance-footer { display:grid; grid-template-columns:1fr 1px 1fr; align-items:center; border-top:1px solid #E9EEF4; background:#FAFBFD; min-height:55px; }
    .exec-footer-metric { display:grid; grid-template-columns:auto auto 1fr; align-items:center; gap:9px; padding:10px 17px; }
    .exec-footer-metric > div:nth-child(2) { display:flex; align-items:baseline; gap:8px; }
    .exec-footer-metric b { color:#172C45; font-size:18px; font-weight:850; }
    .exec-footer-metric span:not(.exec-footer-dot) { color:#66788D; font-size:9.5px; font-weight:700; }
    .exec-footer-dot { width:8px; height:8px; border-radius:50%; }
    .exec-footer-dot.severe { background:#D9684C; box-shadow:0 0 0 4px #FBEDE9; }
    .exec-footer-dot.ops { background:#C39134; box-shadow:0 0 0 4px #FCF3E2; }
    .exec-footer-separator { width:1px; height:28px; background:#E0E6EC; }
    .exec-footer-delta { margin:0 0 0 auto; text-align:right; }

    /* One attention surface, ranked rows; avoids a wall of equal-sized cards. */
    .attention-panel { border:1px solid #DFE6EE; border-radius:16px; background:#FFFFFF; box-shadow:0 8px 23px rgba(16,33,59,.045); overflow:hidden; margin-bottom:10px; }
    .attention-row { position:relative; display:grid; grid-template-columns:38px minmax(0,1fr) auto; align-items:center; gap:13px; min-height:84px; padding:12px 15px 12px 13px; }
    .attention-row + .attention-row { border-top:1px solid #E9EEF3; }
    .attention-row::before { content:""; position:absolute; top:0; bottom:0; left:0; width:3px; background:#D6A243; }
    .attention-row[data-level="HIGH"]::before { background:#D96A45; }
    .attention-row[data-level="CRITICAL"]::before { background:#C3433D; }
    .attention-row[data-level="INFO"]::before, .attention-row[data-level="NORMAL"]::before { background:#589B70; }
    .attention-index { width:34px; height:34px; border-radius:10px; display:flex; align-items:center; justify-content:center; background:#F0F5FA; color:#386598; font-size:10px; font-weight:850; }
    .attention-main { min-width:0; }
    .attention-label { color:#6380A0; font-size:8.4px; font-weight:880; letter-spacing:.075em; text-transform:uppercase; }
    .attention-key { color:#102139; font-size:15px; line-height:1.2; font-weight:830; margin-top:3px; }
    .attention-facts { display:flex; flex-wrap:wrap; gap:9px; margin-top:6px; }
    .attention-fact { color:#65778B; font-size:9.2px; font-weight:650; }
    .attention-fact + .attention-fact::before { content:"•"; color:#B0BAC5; margin-right:9px; }
    .attention-priority { min-width:67px; text-align:center; border-radius:999px; padding:5px 8px; font-size:7.8px; font-weight:900; letter-spacing:.07em; border:1px solid #F0D9D1; background:#FFF5F2; color:#B85A3E; }
    .attention-priority[data-level="CRITICAL"] { background:#FFF1F0; border-color:#EECBC7; color:#B53E38; }
    .attention-priority[data-level="INFO"], .attention-priority[data-level="NORMAL"] { background:#EFF8F2; border-color:#D7EADB; color:#4B805F; }

    /* Executive section heading should be editorial, not another card. */
    .executive-section-head { margin:18px 0 8px 0 !important; padding:0 1px 7px 1px !important; border-bottom:1px solid #E3E8EE !important; }
    .executive-section-no { display:none !important; }
    .executive-section-title { font-size:16px !important; color:#102139 !important; }
    .executive-section-desc { font-size:9.7px !important; color:#8A96A5 !important; margin-left:10px !important; }

    /* Keep navigation compact; all pages remain available. */
    .stTabs [data-baseweb="tab-list"] { margin-top:11px !important; }

    @media(max-width:1100px) {
        .exec-scope-toolbar { grid-template-columns:1fr; gap:7px; }
        .exec-scope-divider { display:none; }
        .exec-scope-compare { text-align:left; min-width:0; }
        .exec-performance-body { grid-template-columns:1fr; }
        .exec-hero-metric { border-right:0; border-bottom:1px solid #E9EEF4; }
    }
    @media(max-width:760px) {
        .exec-support-metrics { grid-template-columns:1fr; }
        .exec-support-metric + .exec-support-metric { border-left:0; border-top:1px solid #E9EEF4; }
        .exec-performance-footer { grid-template-columns:1fr; }
        .exec-footer-separator { width:auto; height:1px; }
        .attention-row { grid-template-columns:34px minmax(0,1fr); }
        .attention-priority { grid-column:2; justify-self:start; }
    }
</style>
"""



EXECUTIVE_READABILITY_CSS = r"""
<style>
    /* ==========================================================
       v4.3 READABILITY PASS
       Keep information complete, but make every important item
       readable at normal laptop viewing distance.
       ========================================================== */

    /* ---- Context / active scope ---- */
    .exec-scope-toolbar {
        min-height:72px !important;
        padding:13px 18px !important;
        gap:18px !important;
        border-radius:16px !important;
    }
    .exec-scope-primary {
        gap:11px !important;
    }
    .exec-scope-eyebrow {
        font-size:10.5px !important;
        letter-spacing:.075em !important;
        color:#65758A !important;
    }
    .exec-scope-date {
        font-size:16px !important;
        line-height:1.25 !important;
        color:#10243D !important;
    }
    .exec-scope-period {
        font-size:10.5px !important;
        padding:5px 9px !important;
    }
    .exec-scope-values {
        font-size:12.8px !important;
        line-height:1.55 !important;
        color:#586B82 !important;
    }
    .ctx-inline b {
        font-size:10.5px !important;
        color:#37536F !important;
        letter-spacing:.035em !important;
    }
    .ctx-dot {
        margin:0 6px !important;
    }
    .exec-scope-compare {
        min-width:220px !important;
    }
    .exec-scope-compare-value {
        font-size:13.5px !important;
        line-height:1.35 !important;
    }
    .exec-scope-state {
        font-size:10px !important;
        padding:4px 8px !important;
    }

    /* ---- Performance surface ---- */
    .exec-performance-wrap {
        border-radius:18px !important;
        box-shadow:0 12px 30px rgba(16,33,59,.065) !important;
        margin-bottom:16px !important;
    }
    .exec-performance-heading {
        padding:19px 22px 15px 22px !important;
    }
    .exec-performance-kicker {
        font-size:10.5px !important;
        letter-spacing:.085em !important;
        color:#315F93 !important;
    }
    .exec-performance-title {
        font-size:22px !important;
        line-height:1.25 !important;
        margin-top:5px !important;
        color:#10243D !important;
    }
    .exec-performance-status {
        font-size:10px !important;
        padding:5px 9px !important;
    }

    .exec-hero-metric {
        padding:25px 24px 22px 24px !important;
    }
    .exec-metric-label {
        font-size:11.5px !important;
        letter-spacing:.065em !important;
        color:#536B86 !important;
    }
    .exec-hero-value {
        font-size:46px !important;
        line-height:1 !important;
        margin-top:14px !important;
    }
    .exec-hero-value span {
        font-size:19px !important;
        margin-left:4px !important;
    }
    .exec-metric-caption {
        font-size:13.5px !important;
        line-height:1.45 !important;
        margin-top:10px !important;
        color:#64758A !important;
    }

    .exec-support-metric {
        padding:24px 20px 20px 20px !important;
    }
    .exec-support-label {
        font-size:12px !important;
        line-height:1.35 !important;
        color:#536B84 !important;
        font-weight:780 !important;
    }
    .exec-support-value {
        font-size:34px !important;
        margin-top:13px !important;
    }
    .exec-support-caption {
        font-size:12.5px !important;
        line-height:1.45 !important;
        min-height:36px !important;
        margin-top:9px !important;
        color:#6E7F93 !important;
    }
    .exec-metric-delta,
    .exec-support-delta,
    .exec-footer-delta {
        font-size:11.5px !important;
        line-height:1.4 !important;
        margin-top:12px !important;
    }
    .delta-good,
    .delta-bad,
    .delta-neutral {
        font-size:11.5px !important;
        font-weight:740 !important;
    }

    /* ---- Secondary KPIs ---- */
    .exec-performance-footer {
        min-height:68px !important;
    }
    .exec-footer-metric {
        gap:11px !important;
        padding:13px 22px !important;
    }
    .exec-footer-metric b {
        font-size:23px !important;
    }
    .exec-footer-metric span:not(.exec-footer-dot) {
        font-size:12.5px !important;
        line-height:1.3 !important;
    }
    .exec-footer-dot {
        width:10px !important;
        height:10px !important;
    }
    .exec-footer-separator {
        height:35px !important;
    }
    .exec-footer-delta {
        margin-left:auto !important;
    }

    /* ---- Tabs / primary navigation ---- */
    .stTabs [data-baseweb="tab-list"] {
        padding:5px !important;
        gap:4px !important;
        margin-top:14px !important;
        border-radius:13px !important;
    }
    .stTabs [data-baseweb="tab"] {
        height:42px !important;
        min-height:42px !important;
        padding:0 15px !important;
        font-size:14px !important;
        font-weight:680 !important;
        color:#55687F !important;
    }
    .stTabs [aria-selected="true"] {
        color:#123F78 !important;
        font-weight:820 !important;
    }

    /* ---- Section hierarchy ---- */
    .executive-section-head {
        margin:26px 0 12px 0 !important;
        padding:0 2px 10px 2px !important;
    }
    .executive-section-title {
        font-size:22px !important;
        line-height:1.25 !important;
        color:#10243D !important;
        font-weight:840 !important;
    }
    .executive-section-desc {
        font-size:13px !important;
        line-height:1.4 !important;
        color:#738398 !important;
        margin-left:12px !important;
    }

    /* ---- Engineering attention rows ---- */
    .attention-panel {
        border-radius:17px !important;
        box-shadow:0 10px 26px rgba(16,33,59,.055) !important;
    }
    .attention-row {
        grid-template-columns:48px minmax(0,1fr) auto !important;
        gap:16px !important;
        min-height:108px !important;
        padding:17px 20px 17px 16px !important;
    }
    .attention-index {
        width:42px !important;
        height:42px !important;
        border-radius:11px !important;
        font-size:13px !important;
    }
    .attention-label {
        font-size:11px !important;
        letter-spacing:.065em !important;
        color:#56718F !important;
    }
    .attention-key {
        font-size:20px !important;
        line-height:1.25 !important;
        margin-top:5px !important;
        color:#10243D !important;
    }
    .attention-facts {
        gap:0 !important;
        margin-top:9px !important;
    }
    .attention-fact {
        font-size:13px !important;
        line-height:1.45 !important;
        color:#5D6F84 !important;
        font-weight:620 !important;
    }
    .attention-fact + .attention-fact::before {
        margin:0 10px !important;
    }
    .attention-priority {
        min-width:82px !important;
        padding:7px 11px !important;
        font-size:10.5px !important;
        letter-spacing:.055em !important;
    }

    /* ---- Common explanatory text on Executive ---- */
    [data-testid="stCaptionContainer"],
    .stCaption,
    small {
        font-size:12.5px !important;
        line-height:1.45 !important;
    }

    /* Chart headings generated by Streamlit should not disappear into the page. */
    h3 {
        font-size:20px !important;
        line-height:1.3 !important;
    }

    /* Maintain density on medium screens without shrinking text again. */
    @media(max-width:1200px) {
        .exec-performance-body {
            grid-template-columns:1fr !important;
        }
        .exec-hero-metric {
            border-right:0 !important;
            border-bottom:1px solid #E9EEF4 !important;
        }
        .exec-scope-toolbar {
            grid-template-columns:1fr !important;
        }
        .exec-scope-divider {
            display:none !important;
        }
        .exec-scope-compare {
            text-align:left !important;
            min-width:0 !important;
        }
    }

    @media(max-width:800px) {
        .exec-support-metrics {
            grid-template-columns:1fr !important;
        }
        .exec-support-metric + .exec-support-metric {
            border-left:0 !important;
            border-top:1px solid #E9EEF4 !important;
        }
        .exec-performance-footer {
            grid-template-columns:1fr !important;
        }
        .exec-footer-separator {
            width:auto !important;
            height:1px !important;
        }
        .attention-row {
            grid-template-columns:44px minmax(0,1fr) !important;
        }
        .attention-priority {
            grid-column:2 !important;
            justify-self:start !important;
        }
    }
</style>
"""



EXECUTIVE_PREMIUM_COLORS_CSS = r"""
<style>
    /* ==========================================================
       v4.4 PREMIUM COLOR SYSTEM
       Premium but readable: subtle depth, restrained corporate color,
       and clearer grouping for the executive snapshot.
       ========================================================== */

    .exec-performance-wrap {
        background:
            linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(250,252,255,1) 100%) !important;
        border:1px solid #DCE5EF !important;
        border-radius:22px !important;
        box-shadow:
            0 14px 34px rgba(14,32,57,.055),
            0 2px 8px rgba(14,32,57,.03) !important;
        overflow:hidden !important;
        position:relative !important;
    }
    .exec-performance-wrap::before {
        content:"";
        position:absolute;
        inset:0 0 auto 0;
        height:5px;
        background:linear-gradient(90deg, #123C77 0%, #2D5EA8 42%, #68A7D5 100%);
    }

    .exec-performance-heading {
        background:
            linear-gradient(180deg, rgba(247,250,254,.92) 0%, rgba(255,255,255,1) 100%) !important;
    }
    .exec-performance-kicker {
        color:#2E5D93 !important;
    }
    .exec-performance-title {
        color:#0F223B !important;
    }
    .exec-performance-status {
        background:linear-gradient(180deg, #F7FAFD 0%, #EEF4FA 100%) !important;
        border:1px solid #D7E2ED !important;
        color:#60758E !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.85);
    }

    .exec-hero-metric {
        background:
            radial-gradient(circle at top left, rgba(48,102,180,.06), transparent 40%),
            linear-gradient(180deg, #FCFEFF 0%, #F8FBFF 100%) !important;
        border-right:1px solid #E8EEF5 !important;
    }
    .exec-support-metric {
        background:#FFFFFF !important;
        transition:all .18s ease !important;
    }
    .exec-support-metric:nth-child(1) {
        background:
            linear-gradient(180deg, #FBFAFF 0%, #F7F5FE 100%) !important;
    }
    .exec-support-metric:nth-child(2) {
        background:
            linear-gradient(180deg, #F8FBFF 0%, #F3F8FE 100%) !important;
    }
    .exec-support-metric:nth-child(3) {
        background:
            linear-gradient(180deg, #FAFEFA 0%, #F5FBF6 100%) !important;
    }
    .exec-support-metric + .exec-support-metric {
        border-left:1px solid #E8EEF5 !important;
    }

    .exec-metric-label,
    .exec-support-label {
        color:#536B86 !important;
    }
    .exec-hero-value,
    .exec-support-value {
        color:#132E5E !important;
    }
    .exec-metric-caption,
    .exec-support-caption {
        color:#667A90 !important;
    }

    .exec-metric-delta,
    .exec-support-delta,
    .exec-footer-delta {
        color:#5F738A !important;
    }
    .delta-good {
        color:#137A52 !important;
    }
    .delta-bad {
        color:#C96447 !important;
    }
    .delta-neutral {
        color:#6C7D91 !important;
    }

    .exec-performance-footer {
        background:
            linear-gradient(180deg, #FBFCFE 0%, #F7F9FC 100%) !important;
    }
    .exec-footer-metric:first-child {
        background:
            linear-gradient(90deg, rgba(221,113,72,.06) 0%, rgba(255,255,255,0) 58%) !important;
    }
    .exec-footer-metric:last-child {
        background:
            linear-gradient(90deg, rgba(199,155,62,.08) 0%, rgba(255,255,255,0) 58%) !important;
    }
    .exec-footer-separator {
        background:#E6EDF5 !important;
    }
    .exec-footer-dot {
        box-shadow:0 0 0 5px rgba(255,255,255,.85) !important;
    }
    .exec-footer-metric b {
        color:#10243D !important;
    }
    .exec-footer-metric span:not(.exec-footer-dot) {
        color:#6A7B8E !important;
    }

    /* Executive tabs feel more intentional */
    .stTabs [data-baseweb="tab-list"] {
        background:linear-gradient(180deg, #FBFCFE 0%, #F2F6FA 100%) !important;
        border:1px solid #E4EAF2 !important;
        border-radius:14px !important;
        padding:5px !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius:10px !important;
    }
    .stTabs [aria-selected="true"] {
        background:linear-gradient(180deg, #FFFFFF 0%, #F8FBFF 100%) !important;
        box-shadow:
            0 1px 2px rgba(16,36,61,.04),
            0 6px 14px rgba(16,36,61,.04) !important;
    }

    /* Engineering Attention cards */
    .attention-panel {
        background:
            linear-gradient(180deg, #FFFFFF 0%, #FBFCFE 100%) !important;
        border:1px solid #DFE7F0 !important;
        box-shadow:
            0 14px 28px rgba(15,33,59,.04),
            0 3px 10px rgba(15,33,59,.025) !important;
        border-radius:18px !important;
    }
    .attention-row {
        background:transparent !important;
    }
    .attention-row + .attention-row {
        border-top:1px solid #ECF1F6 !important;
    }
    .attention-index {
        background:linear-gradient(180deg, #F7FAFE 0%, #EDF3FA 100%) !important;
        border:1px solid #E0E8F2 !important;
        color:#3A5E8E !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.9);
    }
    .attention-label {
        color:#4C6B90 !important;
    }
    .attention-key {
        color:#122742 !important;
    }
    .attention-fact {
        color:#607388 !important;
    }
    .attention-priority {
        box-shadow: inset 0 1px 0 rgba(255,255,255,.65);
    }

    /* Small chip-like facts feel more premium when grouped clearly */
    .attention-facts {
        row-gap:7px !important;
    }

    /* section headers */
    .executive-section-head {
        border-bottom:1px solid #E7EDF4 !important;
    }
</style>
"""



EXECUTIVE_LUXE_COLOR_CSS = """
<style>
    /* ==========================================================
       Executive Luxe Color Layer (v4.5)
       Gives the dashboard a more premium, editorial, high-end feel
       with clearer hierarchy and more intentional color separation.
       ========================================================== */

    .exec-scope-toolbar {
        background:
            linear-gradient(135deg, rgba(17,47,86,.035) 0%, rgba(73,125,183,.02) 45%, rgba(255,255,255,.92) 100%) !important;
        border:1px solid #D8E2ED !important;
        border-radius:22px !important;
        box-shadow:0 12px 30px rgba(15,33,59,.05) !important;
        padding:16px 20px !important;
    }
    .exec-scope-date { color:#122947 !important; font-size:14px !important; }
    .exec-scope-values { color:#5E7188 !important; font-size:10.6px !important; }
    .exec-scope-compare-value { color:#173557 !important; font-size:12px !important; }
    .exec-scope-period {
        background:linear-gradient(180deg, #F2F7FD 0%, #E8F0FA 100%) !important;
        border-color:#D2E0F0 !important;
        color:#2A5A92 !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.88);
    }

    .exec-performance-wrap {
        background:linear-gradient(180deg, #FFFFFF 0%, #F8FBFE 100%) !important;
        border:1px solid #D7E2EE !important;
        border-radius:24px !important;
        box-shadow:
            0 20px 44px rgba(15,33,59,.07),
            0 2px 8px rgba(15,33,59,.03) !important;
    }
    .exec-performance-wrap::before {
        height:8px !important;
        background:linear-gradient(90deg, #0E2B52 0%, #245491 50%, #5AA8CB 100%) !important;
    }
    .exec-performance-heading {
        background:
            linear-gradient(90deg, rgba(14,43,82,.055) 0%, rgba(39,92,147,.028) 42%, rgba(255,255,255,1) 100%) !important;
        padding:18px 20px 14px 20px !important;
    }
    .exec-performance-kicker {
        color:#2C5B92 !important;
        font-size:9px !important;
    }
    .exec-performance-title {
        color:#10223B !important;
        font-size:18px !important;
        letter-spacing:-.018em !important;
    }
    .exec-performance-status {
        background:linear-gradient(180deg, #F7FBFF 0%, #EDF3F9 100%) !important;
        border:1px solid #D8E2EE !important;
        color:#567089 !important;
        font-size:8.5px !important;
        padding:6px 10px !important;
    }

    .exec-performance-body {
        grid-template-columns:minmax(300px,.95fr) minmax(0,2.05fr) !important;
    }
    .exec-hero-metric {
        position:relative !important;
        padding:24px 24px 20px 24px !important;
        background:
            radial-gradient(circle at top left, rgba(39,92,147,.09), transparent 42%),
            linear-gradient(180deg, #FFFFFF 0%, #F7FAFE 100%) !important;
        border-right:1px solid #E4ECF4 !important;
    }
    .exec-hero-metric::before {
        content:"";
        position:absolute;
        inset:0 auto 0 0;
        width:6px;
        background:linear-gradient(180deg, #143F78 0%, #2D6AA8 52%, #6FB8D4 100%);
    }
    .exec-metric-label,
    .exec-support-label {
        color:#5A728F !important;
        font-size:9.5px !important;
    }
    .exec-hero-value {
        color:#12305E !important;
        font-size:40px !important;
        margin-top:12px !important;
    }
    .exec-hero-value span {
        font-size:16px !important;
        color:#4E6580 !important;
    }
    .exec-metric-caption {
        color:#62768E !important;
        font-size:11px !important;
        line-height:1.5 !important;
        margin-top:9px !important;
    }
    .exec-metric-delta,
    .exec-support-delta,
    .exec-footer-delta {
        font-size:10px !important;
        font-weight:760 !important;
    }

    .exec-support-metric {
        position:relative !important;
        overflow:hidden !important;
        padding:22px 20px 18px 20px !important;
        background:#FFFFFF !important;
    }
    .exec-support-metric::before {
        content:"";
        position:absolute;
        left:20px;
        right:20px;
        top:0;
        height:5px;
        border-radius:0 0 12px 12px;
    }
    .exec-support-metric:nth-child(1) {
        background:linear-gradient(180deg, #FCFBFF 0%, #F6F4FF 100%) !important;
    }
    .exec-support-metric:nth-child(1)::before {
        background:linear-gradient(90deg, #6857E6 0%, #958CFF 100%);
    }
    .exec-support-metric:nth-child(2) {
        background:linear-gradient(180deg, #F8FBFF 0%, #F1F7FE 100%) !important;
    }
    .exec-support-metric:nth-child(2)::before {
        background:linear-gradient(90deg, #2E6DB2 0%, #68A9CF 100%);
    }
    .exec-support-metric:nth-child(3) {
        background:linear-gradient(180deg, #FBFEFA 0%, #F2FBF5 100%) !important;
    }
    .exec-support-metric:nth-child(3)::before {
        background:linear-gradient(90deg, #2E8A67 0%, #77C69B 100%);
    }
    .exec-support-metric + .exec-support-metric {
        border-left:1px solid #E6EDF5 !important;
    }
    .exec-support-value {
        color:#122744 !important;
        font-size:28px !important;
        margin-top:14px !important;
    }
    .exec-support-caption {
        color:#667A90 !important;
        font-size:10.6px !important;
        line-height:1.5 !important;
        min-height:36px !important;
        margin-top:9px !important;
    }

    .exec-performance-footer {
        background:linear-gradient(180deg, #FAFCFE 0%, #F4F8FC 100%) !important;
        min-height:64px !important;
    }
    .exec-footer-metric {
        padding:14px 18px !important;
    }
    .exec-footer-metric:first-child {
        background:
            linear-gradient(90deg, rgba(222,110,75,.10) 0%, rgba(255,255,255,0) 52%),
            linear-gradient(180deg, #FFFDFC 0%, #FFF9F7 100%) !important;
    }
    .exec-footer-metric:last-child {
        background:
            linear-gradient(90deg, rgba(201,152,58,.10) 0%, rgba(255,255,255,0) 52%),
            linear-gradient(180deg, #FFFDF9 0%, #FFFAF1 100%) !important;
    }
    .exec-footer-metric b {
        font-size:19px !important;
        color:#16304E !important;
    }
    .exec-footer-metric span:not(.exec-footer-dot) {
        font-size:11px !important;
        color:#6A7B90 !important;
    }
    .exec-footer-dot.severe {
        box-shadow:0 0 0 6px #FCEEE8 !important;
    }
    .exec-footer-dot.ops {
        box-shadow:0 0 0 6px #FCF2DE !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        background:linear-gradient(180deg, #F7FAFD 0%, #EEF4FA 100%) !important;
        border:1px solid #E0E8F1 !important;
        border-radius:15px !important;
        padding:5px !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.88);
    }
    .stTabs [data-baseweb="tab"] {
        color:#536980 !important;
        font-weight:760 !important;
        font-size:13px !important;
        border-radius:11px !important;
        min-height:42px !important;
        padding:0 14px !important;
    }
    .stTabs [aria-selected="true"] {
        color:#16365D !important;
        background:linear-gradient(180deg, #FFFFFF 0%, #F6FAFE 100%) !important;
        border:1px solid #DCE6F1 !important;
        box-shadow:0 8px 18px rgba(16,36,61,.06) !important;
    }

    .executive-section-head {
        margin:24px 0 10px 0 !important;
        padding:0 1px 12px 1px !important;
        border-bottom:1px solid #E3EAF2 !important;
    }
    .executive-section-title {
        font-size:18px !important;
        font-weight:840 !important;
        color:#10243D !important;
    }
    .executive-section-desc {
        font-size:11px !important;
        color:#74869A !important;
        margin-left:12px !important;
    }

    .attention-panel {
        background:linear-gradient(180deg, #FFFFFF 0%, #FBFDFF 100%) !important;
        border:1px solid #DCE5EF !important;
        border-radius:22px !important;
        box-shadow:
            0 18px 36px rgba(15,33,59,.06),
            0 3px 10px rgba(15,33,59,.025) !important;
        overflow:hidden !important;
    }
    .attention-row {
        min-height:104px !important;
        padding:18px 18px 18px 16px !important;
        gap:16px !important;
        background:linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(251,253,255,1) 100%) !important;
    }
    .attention-row[data-level="HIGH"] {
        background:
            linear-gradient(90deg, rgba(217,106,69,.055) 0%, rgba(255,255,255,0) 22%),
            linear-gradient(180deg, #FFFFFF 0%, #FFFCFB 100%) !important;
    }
    .attention-row[data-level="CRITICAL"] {
        background:
            linear-gradient(90deg, rgba(195,67,61,.06) 0%, rgba(255,255,255,0) 22%),
            linear-gradient(180deg, #FFFFFF 0%, #FFF9F9 100%) !important;
    }
    .attention-row[data-level="INFO"],
    .attention-row[data-level="NORMAL"] {
        background:
            linear-gradient(90deg, rgba(76,134,96,.055) 0%, rgba(255,255,255,0) 22%),
            linear-gradient(180deg, #FFFFFF 0%, #FAFDFB 100%) !important;
    }
    .attention-row::before {
        width:5px !important;
        border-radius:0 10px 10px 0 !important;
        box-shadow:0 0 14px rgba(0,0,0,.03) !important;
    }
    .attention-row + .attention-row {
        border-top:1px solid #E8EEF5 !important;
    }
    .attention-index {
        width:42px !important;
        height:42px !important;
        border-radius:12px !important;
        background:linear-gradient(180deg, #F8FBFE 0%, #EEF4FB 100%) !important;
        border:1px solid #DFE8F2 !important;
        color:#3D6394 !important;
        font-size:12px !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.92) !important;
    }
    .attention-label {
        color:#567190 !important;
        font-size:10px !important;
        font-weight:880 !important;
        letter-spacing:.08em !important;
    }
    .attention-key {
        color:#122844 !important;
        font-size:20px !important;
        line-height:1.22 !important;
        margin-top:6px !important;
    }
    .attention-facts {
        gap:8px !important;
        margin-top:10px !important;
    }
    .attention-fact {
        display:inline-flex !important;
        align-items:center !important;
        min-height:29px !important;
        padding:6px 10px !important;
        border-radius:999px !important;
        background:#F3F7FB !important;
        border:1px solid #E1E8F1 !important;
        color:#61758D !important;
        font-size:11px !important;
        font-weight:760 !important;
    }
    .attention-fact + .attention-fact::before {
        content:none !important;
        margin:0 !important;
    }
    .attention-priority {
        min-width:92px !important;
        padding:8px 14px !important;
        font-size:10.5px !important;
        font-weight:900 !important;
        border-radius:999px !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.6) !important;
        letter-spacing:.08em !important;
    }
    .attention-priority[data-level="HIGH"] {
        background:linear-gradient(180deg, #FFF1EC 0%, #FFE7DF 100%) !important;
        border-color:#F2CCBE !important;
        color:#B55A3E !important;
    }
    .attention-priority[data-level="CRITICAL"] {
        background:linear-gradient(180deg, #FEEDEB 0%, #FFDCD8 100%) !important;
        border-color:#EDC0BA !important;
        color:#B8453C !important;
    }
    .attention-priority[data-level="INFO"],
    .attention-priority[data-level="NORMAL"] {
        background:linear-gradient(180deg, #EEF8F1 0%, #DFF1E5 100%) !important;
        border-color:#CDE6D5 !important;
        color:#3D7A57 !important;
    }

    @media (max-width: 760px) {
        .exec-performance-title { font-size:16px !important; }
        .exec-hero-value { font-size:34px !important; }
        .exec-support-value { font-size:24px !important; }
        .attention-key { font-size:17px !important; }
        .attention-row { min-height:unset !important; }
        .attention-fact { font-size:10px !important; }
    }
</style>
"""


RELIABILITY_NAV_FORCE_CSS = r"""
<style>
/* ============================================================
   RELIABILITY MAIN NAVIGATION — FINAL OVERRIDE
   This block intentionally targets several Streamlit DOM variants.
   ============================================================ */

/* Tab strip */
div[data-testid="stTabs"] div[role="tablist"],
div[data-testid="stTabs"] [data-baseweb="tab-list"],
.stTabs div[role="tablist"],
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    min-height: 68px !important;
    padding: 5px 4px 0 4px !important;
    align-items: stretch !important;
    border-bottom: 1px solid #D7E0EA !important;
    overflow-x: auto !important;
    background: transparent !important;
}

/* Every top-level tab button */
div[data-testid="stTabs"] button[role="tab"],
div[data-testid="stTabs"] [data-baseweb="tab"],
.stTabs button[role="tab"],
.stTabs [data-baseweb="tab"] {
    min-height: 64px !important;
    height: 64px !important;
    padding: 0 20px !important;
    margin: 0 !important;
    border-radius: 7px 7px 0 0 !important;
    background: transparent !important;
    color: #17263C !important;
    font-family: "Segoe UI", Inter, Arial, sans-serif !important;
    font-size: 21px !important;
    line-height: 1.1 !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em !important;
    white-space: nowrap !important;
}

/* Force Streamlit's nested Markdown elements to inherit the requested size. */
div[data-testid="stTabs"] button[role="tab"] *,
div[data-testid="stTabs"] [data-baseweb="tab"] *,
.stTabs button[role="tab"] *,
.stTabs [data-baseweb="tab"] * {
    font-family: "Segoe UI", Inter, Arial, sans-serif !important;
    font-size: 21px !important;
    line-height: 1.1 !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em !important;
    white-space: nowrap !important;
}

/* Explicitly cover Markdown paragraph containers used by Streamlit >=1.48. */
div[data-testid="stTabs"] button[role="tab"] [data-testid="stMarkdownContainer"] p,
div[data-testid="stTabs"] [data-baseweb="tab"] [data-testid="stMarkdownContainer"] p,
.stTabs button[role="tab"] p,
.stTabs [data-baseweb="tab"] p {
    margin: 0 !important;
    font-size: 21px !important;
    font-weight: 800 !important;
    line-height: 1.1 !important;
    color: #17263C !important;
}

/* Hover */
div[data-testid="stTabs"] button[role="tab"]:hover,
div[data-testid="stTabs"] [data-baseweb="tab"]:hover,
.stTabs button[role="tab"]:hover,
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(31, 91, 171, 0.055) !important;
}

/* Active tab */
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
div[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"],
.stTabs button[role="tab"][aria-selected="true"],
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: rgba(36, 95, 186, 0.065) !important;
    color: #154FA6 !important;
    box-shadow: inset 0 -4px 0 #245FBA !important;
}

div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] *,
div[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] *,
.stTabs button[role="tab"][aria-selected="true"] *,
.stTabs [data-baseweb="tab"][aria-selected="true"] * {
    color: #154FA6 !important;
    font-weight: 850 !important;
}

/* Hide Streamlit's thin native moving underline; the 4px inset line above
   becomes the single active indicator. */
div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-highlight"] {
    display: none !important;
}

/* Laptop widths: still clearly larger than the previous 13–16px navigation. */
@media (max-width: 1200px) {
    div[data-testid="stTabs"] button[role="tab"],
    div[data-testid="stTabs"] [data-baseweb="tab"],
    .stTabs button[role="tab"],
    .stTabs [data-baseweb="tab"] {
        min-height: 58px !important;
        height: 58px !important;
        padding: 0 15px !important;
    }

    div[data-testid="stTabs"] button[role="tab"] *,
    div[data-testid="stTabs"] [data-baseweb="tab"] *,
    .stTabs button[role="tab"] *,
    .stTabs [data-baseweb="tab"] * {
        font-size: 19px !important;
        font-weight: 800 !important;
    }
}

@media (max-width: 900px) {
    div[data-testid="stTabs"] button[role="tab"],
    div[data-testid="stTabs"] [data-baseweb="tab"],
    .stTabs button[role="tab"],
    .stTabs [data-baseweb="tab"] {
        min-height: 54px !important;
        height: 54px !important;
        padding: 0 13px !important;
    }

    div[data-testid="stTabs"] button[role="tab"] *,
    div[data-testid="stTabs"] [data-baseweb="tab"] *,
    .stTabs button[role="tab"] *,
    .stTabs [data-baseweb="tab"] * {
        font-size: 17.5px !important;
        font-weight: 800 !important;
    }
}
</style>
"""

def inject_css(night_mode: bool = False) -> None:
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)
    st.markdown(EXECUTIVE_REFINED_CSS, unsafe_allow_html=True)
    st.markdown(EXECUTIVE_HIERARCHY_CSS, unsafe_allow_html=True)
    st.markdown(EXECUTIVE_COMPOSITION_CSS, unsafe_allow_html=True)
    st.markdown(EXECUTIVE_READABILITY_CSS, unsafe_allow_html=True)
    st.markdown(EXECUTIVE_PREMIUM_COLORS_CSS, unsafe_allow_html=True)
    if night_mode:
        st.markdown(DARK_CSS, unsafe_allow_html=True)
    st.markdown(PROFESSIONAL_COMMON_CSS, unsafe_allow_html=True)
    if night_mode:
        st.markdown(PROFESSIONAL_DARK_CSS, unsafe_allow_html=True)
    else:
        st.markdown(V16_VISUAL_SKIN_CSS, unsafe_allow_html=True)

    # Final presentation layer is injected last on purpose so native Streamlit
    # widgets cannot leak incompatible theme colors into the sidebar.
    st.markdown(PREMIUM_COMMON_CSS, unsafe_allow_html=True)
    if night_mode:
        st.markdown(PREMIUM_DARK_CSS, unsafe_allow_html=True)
    else:
        st.markdown(PREMIUM_LIGHT_CSS, unsafe_allow_html=True)
    st.markdown(EXECUTIVE_REFINED_CSS, unsafe_allow_html=True)
    if not night_mode:
        st.markdown(EXECUTIVE_LUXE_COLOR_CSS, unsafe_allow_html=True)

    # Must remain last: Reliability top navigation typography is intentionally
    # stronger than the general dashboard tab skin.
    st.markdown(RELIABILITY_NAV_FORCE_CSS, unsafe_allow_html=True)


def fmt_date(value) -> str:
    try:
        return value.strftime("%d %b %Y")
    except Exception:
        return "—"


def render_sidebar_brand() -> None:
    # Use the official Garuda asset for a sharper corporate lockup.
    logo_url = _get_garuda_logo_uri()
    st.sidebar.markdown(
        f"""
        <div class="sidebar-brand garuda-sidebar-brand">
            <div class="garuda-logo-wrap">
                <img class="garuda-corporate-logo" src="{logo_url}" alt="Garuda Indonesia" />
            </div>
            <div class="garuda-brand-divider"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_status(status: str, coverage_start, coverage_end, aircraft_count: int, exposure_ready: bool) -> None:
    is_ready = status.startswith("READY")
    status_class = "status-ready" if is_ready else "status-check"
    status_label = escape(status)
    coverage = f"{coverage_start.year}–{coverage_end.year}" if coverage_start is not None and coverage_end is not None else "—"
    exposure = "Available" if exposure_ready else "Not loaded"
    st.sidebar.markdown(
        f"""
        <div class="sidebar-status">
            <div class="sidebar-status-title">System Status</div>
            <div class="{status_class}"><span class="status-dot">●</span>{status_label}</div>
            <div class="status-row"><span>Data Coverage</span><b>{coverage}</b></div>
            <div class="status-row"><span>Aircraft Types</span><b>{aircraft_count}</b></div>
            <div class="status-row"><span>Exposure</span><b>{exposure}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scope_bar(chips: list[tuple[str, str]]) -> None:
    """Render active scope as a quiet one-line context summary."""
    safe = [(str(k).strip(), str(v).strip()) for k, v in (chips or []) if str(v).strip()]
    if not safe:
        return
    parts = []
    for label, value in safe:
        if label.lower() == "period":
            continue
        parts.append(f"<span class='scope-context-item'><b>{escape(label)}</b> {escape(value)}</span>")
    if not parts:
        return
    st.markdown(
        "<div class='scope-context-line'><span class='scope-context-prefix'>ACTIVE SCOPE</span>"
        + "<span class='scope-context-sep'>•</span><span class='scope-context-items'>"
        + "<span class='scope-context-dot'> · </span>".join(parts)
        + "</span></div>",
        unsafe_allow_html=True,
    )



def render_analysis_context(
    start_date,
    end_date,
    period_label: str,
    chips: list[tuple[str, str]],
    prev_start=None,
    prev_end=None,
    comparator_available: bool = False,
) -> None:
    """Compact executive scope toolbar: complete context, low visual noise."""
    safe = [(str(k).strip(), str(v).strip()) for k, v in (chips or []) if str(v).strip()]
    safe = [(k, v) for k, v in safe if k.lower() != "period"]

    if prev_start is not None and prev_end is not None and comparator_available:
        comparator = f"{fmt_date(prev_start)} → {fmt_date(prev_end)}"
        comparator_state = "Comparator active"
        comparator_class = "ready"
    elif prev_start is not None and prev_end is not None:
        comparator = "Comparator unavailable"
        comparator_state = f"Expected {fmt_date(prev_start)} → {fmt_date(prev_end)}"
        comparator_class = "muted"
    else:
        comparator = "No comparator"
        comparator_state = "All History"
        comparator_class = "muted"

    scope_text = " <span class='ctx-dot'>•</span> ".join(
        f"<span class='ctx-inline'><b>{escape(label)}</b> {escape(value)}</span>" for label, value in safe
    )

    st.markdown(
        f"""
        <div class='exec-scope-toolbar'>
            <div class='exec-scope-primary'>
                <div class='exec-scope-eyebrow'>ACTIVE ANALYSIS</div>
                <div class='exec-scope-date'>{fmt_date(start_date)} → {fmt_date(end_date)}</div>
                <span class='exec-scope-period'>{escape(period_label or 'Selected period')}</span>
            </div>
            <div class='exec-scope-divider'></div>
            <div class='exec-scope-values'>{scope_text}</div>
            <div class='exec-scope-compare'>
                <div class='exec-scope-eyebrow'>COMPARE</div>
                <div class='exec-scope-compare-value'>{escape(comparator)}</div>
                <span class='exec-scope-state {comparator_class}'>{escape(comparator_state)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_header(coverage_start, coverage_end, last_refresh: datetime | None, source_count: int, status: str) -> None:
    refresh = last_refresh.strftime("%d %b %Y %H:%M") if last_refresh else "—"
    st.markdown(
        f"""
        <div class="pp-topbar">
            <div>
                <div class="pp-title">{escape(APP_TITLE)}</div>
                <div class="pp-subtitle">{escape(APP_SUBTITLE)}</div>
            </div>
            <div class="pp-updated">
                ↻ Last Updated: <b>{refresh}</b>
                <div class="pp-meta-line">Coverage {fmt_date(coverage_start)} → {fmt_date(coverage_end)} · {source_count} source(s) · {escape(status)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_active_period(
    start_date,
    end_date,
    period_label: str,
    prev_start=None,
    prev_end=None,
    comparator_available: bool = False,
) -> None:
    """Compact executive period context."""
    try:
        day_count = (end_date - start_date).days + 1
    except Exception:
        day_count = None

    period_meta = escape(period_label or "Selected period")
    if day_count is not None:
        period_meta += f" · {day_count:,} days"

    if prev_start is not None and prev_end is not None and comparator_available:
        comparator = f"{fmt_date(prev_start)} → {fmt_date(prev_end)}"
        comp_state = "Comparator"
    elif prev_start is not None and prev_end is not None:
        comparator = "No comparator data"
        comp_state = f"Expected {fmt_date(prev_start)} → {fmt_date(prev_end)}"
    else:
        comparator = "Not available"
        comp_state = "All History"

    st.markdown(
        f"""
        <div class='exec-period-bar'>
            <div class='exec-period-main'>
                <div class='exec-period-label'>ANALYSIS PERIOD</div>
                <div class='exec-period-value'>{fmt_date(start_date)} → {fmt_date(end_date)}</div>
                <div class='exec-period-meta'>{period_meta}</div>
            </div>
            <div class='exec-period-divider'></div>
            <div class='exec-period-compare'>
                <div class='exec-period-label'>COMPARE WITH</div>
                <div class='exec-period-value small'>{escape(comparator)}</div>
                <div class='exec-period-meta'>{escape(comp_state)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _pct_change(current: float | int | None, previous: float | int | None) -> float | None:
    if current is None or previous is None:
        return None
    try:
        if float(previous) == 0:
            return None
        return (float(current) - float(previous)) / abs(float(previous)) * 100.0
    except Exception:
        return None


def _delta_text(current, previous, *, percentage_points: bool = False, lower_is_better: bool = True) -> str:
    if current is None or previous is None:
        return "<span class='delta-neutral'>No comparable prior period</span>"

    if percentage_points:
        try:
            delta = float(current) - float(previous)
        except Exception:
            return "<span class='delta-neutral'>No comparable prior period</span>"
        direction_good = delta < 0 if lower_is_better else delta > 0
        css = "delta-good" if direction_good else "delta-bad" if delta != 0 else "delta-neutral"
        arrow = "▼" if delta < 0 else "▲" if delta > 0 else "•"
        return f"<span class='{css}'>{arrow} {abs(delta):.1f} pp vs comparator</span>"

    delta = _pct_change(current, previous)
    if delta is None:
        return "<span class='delta-neutral'>No comparable prior period</span>"
    direction_good = delta < 0 if lower_is_better else delta > 0
    css = "delta-good" if direction_good else "delta-bad" if delta != 0 else "delta-neutral"
    arrow = "▼" if delta < 0 else "▲" if delta > 0 else "•"
    return f"<span class='{css}'>{arrow} {abs(delta):.1f}% vs comparator</span>"


def _kpi_card(icon: str, icon_class: str, label: str, value: str, sub: str, delta_html: str, emphasis: str = "secondary") -> None:
    st.markdown(
        f"""
        <div class="kpi-card {escape(emphasis)}">
            <div class="kpi-head">
                <div class="kpi-icon {icon_class}">{escape(icon)}</div>
                <div class="kpi-label">{escape(label)}</div>
            </div>
            <div class="kpi-value">{escape(value)}</div>
            <div class="kpi-sub">{escape(sub)}</div>
            <div class="kpi-delta">{delta_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(kpi, all_technical_events: int | None = None, previous_kpi=None) -> None:
    """Full KPI set inside one executive performance surface."""
    if kpi.pp_delay_contribution_pct is None:
        contribution_value = "—"
        contribution_sub = "All-ATA denominator unavailable" if not kpi.all_ata_source_ready else "No valid denominator"
    else:
        contribution_value = f"{kpi.pp_delay_contribution_pct:.1f}%"
        contribution_sub = f"{kpi.pp_contribution_numerator:,} PP / {kpi.pp_contribution_denominator:,} all-ATA"

    prev = previous_kpi
    event_delta = _delta_text(kpi.pp_events, getattr(prev, "pp_events", None))
    minute_delta = _delta_text(kpi.pp_delay_minutes, getattr(prev, "pp_delay_minutes", None))
    rate_delta = _delta_text(kpi.delay_rate_100, getattr(prev, "delay_rate_100", None))
    contrib_delta = _delta_text(kpi.pp_delay_contribution_pct, getattr(prev, "pp_delay_contribution_pct", None), percentage_points=True)
    severe_delta = _delta_text(kpi.severe_events, getattr(prev, "severe_events", None))
    significant_delta = _delta_text(kpi.significant_events, getattr(prev, "significant_events", None))

    rate_value = "—" if kpi.delay_rate_100 is None else f"{kpi.delay_rate_100:.3f}"

    performance_html = f"""
        <div class='exec-performance-wrap'>
            <div class='exec-performance-heading'>
                <div>
                    <div class='exec-performance-kicker'>CURRENT PERFORMANCE</div>
                    <div class='exec-performance-title'>Powerplant reliability snapshot</div>
                </div>
                <div class='exec-performance-status'>ACTIVE SCOPE</div>
            </div>

            <div class='exec-performance-body'>
                <div class='exec-hero-metric'>
                    <div class='exec-metric-label'>POWERPLANT DELAY BURDEN</div>
                    <div class='exec-hero-value'>{kpi.pp_delay_minutes:,.0f}<span> min</span></div>
                    <div class='exec-metric-caption'>Total delay minutes in the selected scope</div>
                    <div class='exec-metric-delta'>{minute_delta}</div>
                </div>

                <div class='exec-support-metrics'>
                    <div class='exec-support-metric'>
                        <div class='exec-support-label'>Delay Rate /100 T/O</div>
                        <div class='exec-support-value'>{rate_value}</div>
                        <div class='exec-support-caption'>{escape(kpi.exposure_note)}</div>
                        <div class='exec-support-delta'>{rate_delta}</div>
                    </div>
                    <div class='exec-support-metric'>
                        <div class='exec-support-label'>PP Delay Events</div>
                        <div class='exec-support-value'>{kpi.pp_events:,}</div>
                        <div class='exec-support-caption'>{kpi.all_technical_events:,} all-ATA events in scope</div>
                        <div class='exec-support-delta'>{event_delta}</div>
                    </div>
                    <div class='exec-support-metric'>
                        <div class='exec-support-label'>PP Contribution</div>
                        <div class='exec-support-value'>{contribution_value}</div>
                        <div class='exec-support-caption'>{escape(contribution_sub)}</div>
                        <div class='exec-support-delta'>{contrib_delta}</div>
                    </div>
                </div>
            </div>

            <div class='exec-performance-footer'>
                <div class='exec-footer-metric'>
                    <span class='exec-footer-dot severe'></span>
                    <div><b>{kpi.severe_events:,}</b><span>Severe Events ≥60 min</span></div>
                    <div class='exec-footer-delta'>{severe_delta}</div>
                </div>
                <div class='exec-footer-separator'></div>
                <div class='exec-footer-metric'>
                    <span class='exec-footer-dot ops'></span>
                    <div><b>{kpi.significant_events:,}</b><span>RTA / RTB / RTO</span></div>
                    <div class='exec-footer-delta'>{significant_delta}</div>
                </div>
            </div>
        </div>
        """
    # Markdown treats indented HTML after blank lines as code blocks. Compact the
    # fragment so the whole executive panel is parsed as one HTML block.
    performance_html = "".join(line.strip() for line in performance_html.splitlines())
    st.markdown(performance_html, unsafe_allow_html=True)

def render_focus(items, start_date=None, end_date=None) -> None:
    """One executive attention surface containing up to three ranked signals."""
    default_tags = ["Dominant Driver", "Repetitive Defect", "Aircraft / Tail Watch", "Engineering Signal"]
    normalized = []
    for idx, item in enumerate(items or []):
        if isinstance(item, dict):
            label = str(item.get("label") or default_tags[min(idx, len(default_tags)-1)]).strip()
            message = str(item.get("message") or "").strip()
            priority = str(item.get("priority") or "REVIEW").upper().strip()
        else:
            label = default_tags[min(idx, len(default_tags)-1)]
            message = str(item).strip()
            priority = "REVIEW"
        if message:
            normalized.append((label, message, priority))
        if len(normalized) >= 3:
            break

    if not normalized:
        normalized = [("Engineering Status", "No priority signal in the active scope.", "INFO")]

    rows = []
    for idx, (label, message, priority) in enumerate(normalized, start=1):
        priority_attr = escape(priority, quote=True)
        parts = [p.strip() for p in message.split("·") if p.strip()]
        key = parts[0] if parts else message
        facts = [p for p in parts[1:] if p.upper() != priority]
        facts_html = "".join(f"<span class='attention-fact'>{escape(fact)}</span>" for fact in facts)
        if not facts_html:
            facts_html = f"<span class='attention-fact'>{escape(message)}</span>"

        rows.append(
            f"<div class='attention-row' data-level='{priority_attr}'>"
            f"<div class='attention-index'>{idx:02d}</div>"
            f"<div class='attention-main'>"
            f"<div class='attention-label'>{escape(label)}</div>"
            f"<div class='attention-key'>{escape(key)}</div>"
            f"<div class='attention-facts'>{facts_html}</div>"
            f"</div>"
            f"<div class='attention-priority' data-level='{priority_attr}'>{escape(priority)}</div>"
            f"</div>"
        )

    st.markdown(
        "<div class='attention-panel'>" + "".join(rows) + "</div>",
        unsafe_allow_html=True,
    )

def render_focus_top(items: list[str]) -> None:
    """Compact management-priority strip shown above the KPI cards."""
    safe_items = [str(x) for x in (items or []) if str(x).strip()][:3]
    if not safe_items:
        safe_items = ["Tidak ada priority signal pada filter aktif."]
    body = "".join(
        f"<div class='focus-tile'><div class='focus-tile-num'>{idx}</div><div>{escape(text)}</div></div>"
        for idx, text in enumerate(safe_items, start=1)
    )
    st.markdown(
        f"""
        <div class='focus-top'>
            <div class='focus-top-head'><span class='focus-top-badge'>◎</span> Engineering Focus · Priority Signals</div>
            <div class='focus-grid'>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

