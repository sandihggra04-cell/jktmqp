from datetime import datetime
from io import BytesIO
from base64 import b64encode
from urllib.parse import quote
from urllib.request import Request, urlopen
from html import unescape as html_unescape
from pathlib import Path
import re
import sys
import time

PAGE_ROOT = Path(__file__).resolve().parent
CONTROL_CENTER_ROOT = PAGE_ROOT


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

GARUDA_LOGO_URI = _get_garuda_logo_uri()
if str(PAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PAGE_ROOT))

import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from engine_config import (
    GOOGLE_SHEET_URL,
    SHOP_VISIT_SHEET,
    AUTO_REFRESH_SECONDS,
    COST_CURRENCY,
    MAX_PLAUSIBLE_TAT_DAYS,
    PHASES,
)
from engine_data_utils import clean_data, esn_source_column, recognized_columns, promote_header_row
if str(CONTROL_CENTER_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_CENTER_ROOT))
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sv_source_loader import source_kind, is_supported_source_url, dataframes_from_remote_file, dataframes_from_uploaded_file, sharepoint_graph_status, configured_source_url
from session_uploads import remember_upload, restore_upload, upload_memory_info



# ============================================================
# STYLE
# ============================================================
st.markdown(
    """
    <style>
    :root {
        --navy:#0B1F33;
        --blue:#245B9E;
        --muted:#667085;
        --line:#E5EAF0;
        --bg:#F6F8FB;
    }

    .stApp {background:var(--bg);}

    .block-container {
        padding-top:1rem;
        padding-bottom:2.2rem;
        max-width:1550px;
    }

    .hero {
        background:linear-gradient(120deg,#0B1F33,#153B63 58%,#245B9E);
        border-radius:18px;
        padding:20px 25px;
        color:white;
        margin-bottom:13px;
        box-shadow:0 8px 28px rgba(11,31,51,.12);
    }

    .hero h1 {
        font-size:1.65rem;
        margin:0 0 4px;
        color:white;
        font-weight:760;
    }

    .hero p {
        margin:0;
        color:#D7E3F1;
        font-size:.95rem;
    }

    [data-testid="stMetric"] {
        background:#FFFFFF;
        border:1px solid var(--line);
        padding:13px 15px;
        border-radius:14px;
        box-shadow:0 2px 10px rgba(16,24,40,.03);
    }

    [data-testid="stMetricLabel"] {
        color:#667085;
        font-weight:600;
    }

    [data-testid="stMetricValue"] {
        color:#0B1F33;
        font-weight:760;
    }

    .section-title {
        font-size:1.08rem;
        font-weight:760;
        color:#0B1F33;
        margin:12px 0 4px;
    }

    .section-note {
        color:#667085;
        font-size:.86rem;
        margin-bottom:9px;
    }

    .toolbar {
        background:#FFFFFF;
        border:1px solid #E5EAF0;
        border-radius:14px;
        padding:10px 13px 3px;
        margin-bottom:12px;
    }

    .detail-card {
        background:#FFFFFF;
        border:1px solid #E5EAF0;
        border-radius:14px;
        padding:15px 17px;
        min-height:108px;
    }

    .detail-label {
        color:#667085;
        font-size:.76rem;
        text-transform:uppercase;
        letter-spacing:.04em;
        font-weight:700;
    }

    .detail-value {
        color:#0B1F33;
        font-size:1.08rem;
        font-weight:760;
        margin-top:4px;
    }

    .detail-sub {
        color:#475467;
        font-size:.83rem;
        margin-top:5px;
    }

    .sidebar-title {
        color:#FFFFFF;
        font-size:1.08rem;
        font-weight:760;
        margin-bottom:.1rem;
    }

    .sidebar-caption {
        color:#B7C3D3;
        font-size:.88rem;
        margin-bottom:1rem;
    }

    .sidebar-section {
        color:#E5EEF8;
        font-size:.84rem;
        font-weight:700;
        text-transform:uppercase;
        letter-spacing:.04em;
        margin-top:1rem;
        margin-bottom:.35rem;
    }

    .sidebar-info {
        background:rgba(255,255,255,.08);
        border:1px solid rgba(255,255,255,.12);
        border-radius:12px;
        padding:12px 13px;
        margin:10px 0;
    }

    .sidebar-info strong {
        color:#FFFFFF;
    }

    .sidebar-info span {
        color:#D3DDEA;
        font-size:.84rem;
    }

    div[data-testid="stDataFrame"] {
        border:1px solid #E5EAF0;
        border-radius:12px;
        overflow:hidden;
    }

    [data-testid="stSidebar"] {
        background:#0B1F33;
    }
    [data-testid="stSidebar"] > div:first-child { padding-top:.25rem!important; }
    [data-testid="stSidebarContent"], [data-testid="stSidebarUserContent"] { padding-top:.35rem!important; }

    [data-testid="stSidebar"] * {
        color:#F8FAFC;
    }

    /* Sidebar navigation and source controls */
    .cc-nav-label {
        margin:14px 1px 7px;
        color:#8FA4BD!important;
        font-size:10px!important;
        font-weight:850!important;
        letter-spacing:.13em!important;
        text-transform:uppercase!important;
    }
    .cc-nav-active {
        display:flex;
        align-items:center;
        gap:9px;
        width:100%;
        min-height:40px;
        box-sizing:border-box;
        padding:10px 12px;
        margin:4px 0 7px;
        border-radius:11px;
        background:linear-gradient(90deg,rgba(57,139,146,.95),rgba(45,103,142,.82));
        border:1px solid rgba(139,220,221,.22);
        color:#FFFFFF!important;
        font-size:12px!important;
        font-weight:800!important;
        box-shadow:0 5px 14px rgba(0,0,0,.10);
    }
    .cc-nav-active .nav-dot {
        width:7px;
        height:7px;
        border-radius:50%;
        background:#A3ECE8;
        flex:0 0 7px;
        box-shadow:0 0 0 3px rgba(163,236,232,.10);
    }
    .source-label {
        color:#F2F6FB!important;
        font-size:.82rem!important;
        font-weight:720!important;
        margin:9px 0 6px!important;
    }
    .source-meta {
        color:#8098B2!important;
        font-size:.70rem!important;
        line-height:1.35!important;
        margin:-2px 0 8px!important;
    }

    /* Text input: dark, low-contrast border; no white focus ring. */
    [data-testid="stSidebar"] [data-testid="stTextInput"] label { display:none!important; }
    [data-testid="stSidebar"] [data-testid="stTextInput"] [data-baseweb="input"] {
        background:#102943!important;
        border:1px solid #2E4D6B!important;
        border-radius:11px!important;
        box-shadow:none!important;
        min-height:44px!important;
        transition:border-color .16s ease, box-shadow .16s ease!important;
    }
    [data-testid="stSidebar"] [data-testid="stTextInput"] [data-baseweb="input"]:focus-within {
        border-color:#5E91C5!important;
        box-shadow:0 0 0 2px rgba(94,145,197,.16)!important;
    }
    [data-testid="stSidebar"] [data-testid="stTextInput"] [data-baseweb="input"] > div,
    [data-testid="stSidebar"] [data-testid="stTextInput"] input,
    [data-testid="stSidebar"] [data-testid="stTextInput"] input[type="text"] {
        background:transparent!important;
        color:#111827!important;
        -webkit-text-fill-color:#111827!important;
        caret-color:#111827!important;
        border:0!important;
        outline:0!important;
        box-shadow:none!important;
        font-size:.86rem!important;
        opacity:1!important;
    }
    [data-testid="stSidebar"] [data-testid="stTextInput"] input::placeholder,
    [data-testid="stSidebar"] [data-testid="stTextInput"] input[type="text"]::placeholder {
        color:#6B7280!important;
        -webkit-text-fill-color:#6B7280!important;
        opacity:1!important;
    }
    /* Browser autofill can otherwise re-introduce light/white text. */
    [data-testid="stSidebar"] [data-testid="stTextInput"] input:-webkit-autofill,
    [data-testid="stSidebar"] [data-testid="stTextInput"] input:-webkit-autofill:hover,
    [data-testid="stSidebar"] [data-testid="stTextInput"] input:-webkit-autofill:focus {
        -webkit-text-fill-color:#111827!important;
        caret-color:#111827!important;
    }

    /* File uploader: keep the complete control on the navy surface. */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] > div,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] > div > div,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] ul,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] li {
        background:transparent!important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background:#102943!important;
        border:1px dashed #355A79!important;
        border-radius:11px!important;
        box-shadow:none!important;
        min-height:72px!important;
        padding:.55rem .7rem!important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {
        border-color:#5E91C5!important;
        background:#122E49!important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"],
    [data-testid="stSidebar"] [data-testid*="stFileUploaderFile"] {
        background:#102943!important;
        border:1px solid #2E4D6B!important;
        border-radius:10px!important;
        box-shadow:none!important;
        padding:.42rem .55rem!important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] *,
    [data-testid="stSidebar"] [data-testid*="stFileUploaderFile"] * {
        background-color:transparent!important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] small,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] p,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] span,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] div {
        color:#DCE8F4!important;
        -webkit-text-fill-color:#DCE8F4!important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] small {
        color:#7891AA!important;
        -webkit-text-fill-color:#7891AA!important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] svg {
        color:#91B8DA!important;
        stroke:#91B8DA!important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button {
        background:#193956!important;
        border:1px solid #365B7B!important;
        color:#F8FAFC!important;
        -webkit-text-fill-color:#F8FAFC!important;
        border-radius:9px!important;
        box-shadow:none!important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button:hover {
        background:#214563!important;
        border-color:#4F7798!important;
    }

    /* v4.7.9: keep every uploaded-file surface dark, including Streamlit's selected-file pill. */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] div,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] ul,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] li {
        background-color:transparent!important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section {
        background:#102943!important;
        border-color:#355A79!important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section + div,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section ~ div,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] ul > li,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid*="UploaderFile"],
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid*="UploadedFile"],
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid*="FileData"] {
        background:#132D47!important;
        border-color:#355A79!important;
        color:#EAF2FA!important;
        border-radius:10px!important;
        box-shadow:none!important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section + div *,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section ~ div *,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] ul > li *,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid*="UploaderFile"] *,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid*="UploadedFile"] *,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid*="FileData"] * {
        background-color:transparent!important;
        color:#EAF2FA!important;
        -webkit-text-fill-color:#EAF2FA!important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button[aria-label*="Remove"],
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button[title*="Remove"] {
        background:#173B5B!important;
        border:1px solid #3E6484!important;
        color:#CFE1F2!important;
    }

    /* Sidebar alerts also stay dark. */
    [data-testid="stSidebar"] .stAlert {
        background:#132C45!important;
        border:1px solid #35536F!important;
        border-radius:11px!important;
    }
    [data-testid="stSidebar"] .stAlert * {
        color:#EDF5FC!important;
        -webkit-text-fill-color:#EDF5FC!important;
        opacity:1!important;
    }

    /* Secondary buttons are room navigation; primary is Connect / Test. */
    [data-testid="stSidebar"] .stButton > button {
        width:100%;
        border-radius:11px;
        min-height:2.55rem;
        font-size:.82rem;
        font-weight:750;
        box-shadow:none!important;
    }
    [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {
        background:#17344F!important;
        border:1px solid #2E506E!important;
        color:#EAF2FA!important;
        -webkit-text-fill-color:#EAF2FA!important;
    }
    [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover {
        background:#1D405F!important;
        border-color:#4E7596!important;
    }
    [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
        background:linear-gradient(90deg,#2C62A8,#3E72B9)!important;
        border:1px solid #4A79B8!important;
        color:#FFFFFF!important;
        -webkit-text-fill-color:#FFFFFF!important;
    }
    [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover {
        filter:brightness(1.05)!important;
    }

    .footer-note {
        color:#667085;
        font-size:.77rem;
        margin-top:18px;
    }

    .shop-room-brand {
        padding:0 2px 7px; margin-top:-18px; margin-bottom:4px;
        border-bottom:1px solid rgba(255,255,255,.12);
    }
    .shop-room-brand img {
        display:block; width:236px; max-width:98%; height:auto; margin-bottom:3px; image-rendering:-webkit-optimize-contrast; image-rendering:crisp-edges; filter:none; opacity:1;
    }
    .shop-room-name { display:none !important; }
    .shop-room-sub { display:none !important; }
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stSidebar"] button[aria-label="Collapse sidebar"] {
        background:#203A59!important; border:1px solid rgba(255,255,255,.16)!important; border-radius:11px!important;
    }
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="stSidebar"] button[aria-label="Collapse sidebar"] svg {
        color:#FFFFFF!important; stroke:#FFFFFF!important; fill:#FFFFFF!important; opacity:1!important;
    }
    [data-testid="collapsedControl"] button, button[aria-label="Expand sidebar"] {
        background:#FFFFFF!important; border:1px solid #D7E0EB!important; border-radius:11px!important;
    }
    [data-testid="collapsedControl"] svg, button[aria-label="Expand sidebar"] svg {
        color:#334155!important; stroke:#334155!important; fill:#334155!important; opacity:1!important;
    }
    
    /* v3.9: compact sidebar brand; room switcher moved out of sidebar */
    [data-testid="stSidebarUserContent"] { padding-top:0 !important; margin-top:-0.35rem !important; }
    .shop-room-brand {
        margin-top:-2.55rem !important;
        padding-top:0 !important;
        padding-bottom:10px !important;
        margin-bottom:6px !important;
    }
    .shop-room-brand img {
        width:220px !important;
        max-width:96% !important;
        margin-bottom:6px !important;
        image-rendering:-webkit-optimize-contrast !important;
        filter:none !important;
        opacity:1 !important;
    }
    [data-testid="stPopover"] > button {
        min-height:34px !important;
        padding:0 11px !important;
        border-radius:10px !important;
        border:1px solid #D6E0EB !important;
        background:#FFFFFF !important;
        color:#38506C !important;
        font-size:11px !important;
        font-weight:750 !important;
        box-shadow:0 2px 8px rgba(16,33,59,.04) !important;
    }
</style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# GOOGLE SHEET / DATA STATE
# ============================================================
def parse_sheet_url(value):
    text = (value or "").strip()

    if (
        not text
        or text == "PASTE_YOUR_GOOGLE_SHEET_LINK_HERE"
    ):
        return None

    match = re.search(
        r"docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]{15,})",
        text,
        flags=re.I,
    )

    if match:
        return match.group(1)

    if re.fullmatch(
        r"[A-Za-z0-9_-]{15,}",
        text,
    ):
        return text

    return None


def parse_sheet_gid(value):
    text = (value or "").strip()
    match = re.search(r"(?:[?#&]gid=)(\d+)", text, flags=re.I)
    return match.group(1) if match else None


def discover_sheet_gids(sheet_url, timeout=6):
    """Best-effort discovery of worksheet gids from any accessible Google Sheets link."""
    sheet_id = parse_sheet_url(sheet_url)
    if not sheet_id:
        return []

    edit_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    try:
        request = Request(
            edit_url,
            headers={"User-Agent": "Mozilla/5.0 Powerplant-Shop-Visit-Dashboard/1.0"},
        )
        with urlopen(request, timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    html = html_unescape(html)
    patterns = [
        r'"sheetId"\s*:\s*(\d+)',
        r'"gid"\s*:\s*(\d+)',
        r'gid=(\d+)',
        r'gid%3D(\d+)',
    ]
    gids = []
    for pattern in patterns:
        for match in re.findall(pattern, html, flags=re.I):
            if match not in gids:
                gids.append(match)
            if len(gids) >= 24:
                return gids
    return gids


def candidate_csv_urls(sheet_url):
    """Build candidates from the pasted link itself; no spreadsheet ID or tab is hard-coded."""
    sheet_id = parse_sheet_url(sheet_url)
    if not sheet_id:
        return []

    candidates = []
    selected_gid = parse_sheet_gid(sheet_url)

    # 1) The tab currently selected in the pasted URL is always the first choice.
    if selected_gid:
        candidates.append((
            f"selected tab (gid={selected_gid})",
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={selected_gid}",
        ))

    # 2) Discover all accessible tabs and let schema matching decide which one is Shop Visit data.
    for gid in discover_sheet_gids(sheet_url):
        if gid == selected_gid:
            continue
        candidates.append((
            f"discovered tab (gid={gid})",
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}",
        ))

    # 3) Default/first tab works even if the copied link has no gid.
    candidates.append((
        "first/default tab",
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv",
    ))

    # 4) Backward compatibility only. The system no longer depends on this tab name.
    candidates.append((
        f"legacy tab '{SHOP_VISIT_SHEET}'",
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={quote(SHOP_VISIT_SHEET, safe='')}",
    ))

    seen = set()
    unique = []
    for label, url in candidates:
        if url not in seen:
            seen.add(url)
            unique.append((label, url))
    return unique


def schema_match_score(raw):
    """Score a worksheet by its Shop Visit schema, not by link or tab name."""
    mapping = recognized_columns(raw)
    esn_col = esn_source_column(raw)
    if esn_col is None:
        return -1, mapping

    core_fields = [
        "ESN", "removal date", "Induction Date", "reason of removal",
        "MRO", "Scope of work", "Release date", "Engine Owner", "Progres",
        "TAT", "TSN", "CSN", "engine type",
    ]
    matched_core = sum(1 for name in core_fields if name in mapping)
    matched_all = len(mapping)

    # ESN is mandatory; the rest increases confidence. Row count breaks close ties.
    score = 100 + matched_core * 12 + matched_all * 3 + min(len(raw), 500) / 500.0
    return score, mapping


def csv_url(sheet_url):
    """Backward-compatible helper: return the first candidate URL."""
    candidates = candidate_csv_urls(sheet_url)
    return candidates[0][1] if candidates else ""


def _read_sheet_candidate(url):
    raw = pd.read_csv(url)

    # Reject common authentication/HTML responses early.
    joined_cols = " ".join(map(str, raw.columns)).lower()
    if "<!doctype" in joined_cols or "<html" in joined_cols:
        raise ValueError("Google returned an HTML/login page instead of sheet data.")

    if esn_source_column(raw) is None:
        # Some Excel / Microsoft Lists imports contain title rows above the real header.
        raw_no_header = pd.read_csv(url, header=None)
        promoted = promote_header_row(raw_no_header)
        if not promoted.empty:
            raw = promoted

    return raw


def _engine_best_from_frames(frames):
    errors = []
    valid_candidates = []
    for source_label, raw in frames:
        try:
            if esn_source_column(raw) is None:
                promoted = promote_header_row(raw)
                if not promoted.empty:
                    raw = promoted
            score, mapping = schema_match_score(raw)
            if score < 0:
                visible_cols = [str(c) for c in list(raw.columns)[:12]]
                errors.append(
                    f"{source_label}: bukan format Engine Shop Visit / ESN tidak dikenali. "
                    f"Kolom terbaca: {', '.join(visible_cols) or '(none)'}"
                )
                continue
            cleaned = clean_data(raw, PHASES, MAX_PLAUSIBLE_TAT_DAYS)
            cleaned.attrs["source_label"] = source_label
            cleaned.attrs["source_rows"] = int(len(raw))
            cleaned.attrs["source_esn_column"] = str(esn_source_column(raw))
            cleaned.attrs["recognized_columns"] = mapping
            cleaned.attrs["schema_match_count"] = len(mapping)
            cleaned.attrs["schema_score"] = score
            valid_candidates.append((score, len(cleaned), cleaned))
        except Exception as exc:
            errors.append(f"{source_label}: {type(exc).__name__}: {exc}")
    if valid_candidates:
        valid_candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return valid_candidates[0][2]
    raise ValueError(
        "Source berhasil dibaca, tetapi tidak ditemukan worksheet dengan format Engine Shop Visit yang dikenali. "
        + " | ".join(errors[-4:])
    )


def fetch_uploaded_dashboard_data(uploaded):
    return _engine_best_from_frames(dataframes_from_uploaded_file(uploaded))


def fetch_dashboard_data(sheet_url):
    """Load Engine Shop Visit from Google Sheets, SharePoint/OneDrive Excel, or direct file URL."""
    kind = source_kind(sheet_url)
    if kind in ("microsoft_list", "sharepoint", "file_url", "remote_data", "local_file"):
        return _engine_best_from_frames(dataframes_from_remote_file(sheet_url))

    if kind != "google":
        raise ValueError(
            "Source tidak dikenali. Gunakan Google Sheets, SharePoint Doc.aspx/OneDrive Excel, direct Excel/CSV URL, atau Upload Excel/CSV."
        )

    candidates = candidate_csv_urls(sheet_url)
    if not candidates:
        raise ValueError("Google Sheet URL tidak valid.")

    errors = []
    frames = []
    for source_label, url in candidates:
        try:
            frames.append((f"Google Sheet · {source_label}", _read_sheet_candidate(url)))
        except Exception as exc:
            errors.append(f"{source_label}: {exc}")

    if frames:
        try:
            return _engine_best_from_frames(frames)
        except Exception as exc:
            errors.append(str(exc))

    raise ValueError(
        "Google Sheet tidak dapat dibaca sebagai Engine Shop Visit. Sistem membaca berdasarkan schema/header, "
        "bukan berdasarkan nama file/tab. " + " | ".join(errors[-4:])
    )


def refresh_data(sheet_url):
    """
    Fetch remote source, then keep the prepared dataframe in session memory.
    """
    data = fetch_dashboard_data(
        sheet_url
    )

    st.session_state.dashboard_df = data
    st.session_state.engine_room_cached_df = data.copy()
    st.session_state.engine_room_cached_source = sheet_url
    st.session_state.loaded_sheet_url = sheet_url
    st.session_state.source_label = data.attrs.get("source_label", "Google Sheet")
    st.session_state.source_rows = data.attrs.get("source_rows", len(data))
    st.session_state.source_esn_column = data.attrs.get("source_esn_column", "ESN")
    st.session_state.schema_match_count = data.attrs.get("schema_match_count", 0)
    st.session_state.schema_score = data.attrs.get("schema_score", 0)
    st.session_state.last_fetch_epoch = time.time()
    st.session_state.last_sync = (
        datetime.now().strftime(
            "%d %b %Y · %H:%M:%S"
        )
    )

    return data


def ensure_data(sheet_url, force=False):
    """
    Filter/search interactions NEVER trigger a network request.

    A remote fetch happens only when:
    - data has not been loaded yet,
    - the Google Sheet URL changes,
    - 60 seconds have passed,
    - Refresh now is pressed.
    """
    if sheet_url == "__uploaded_engine__":
        if "dashboard_df" not in st.session_state:
            raise ValueError("Uploaded Engine Shop Visit file is no longer in session. Upload it again from the sidebar.")
        return st.session_state.dashboard_df

    now = time.time()

    missing = (
        "dashboard_df"
        not in st.session_state
    )

    url_changed = (
        st.session_state.get(
            "loaded_sheet_url",
            "",
        )
        != sheet_url
    )

    last_fetch = st.session_state.get(
        "last_fetch_epoch",
        0.0,
    )

    refresh_due = (
        now - last_fetch
        >= AUTO_REFRESH_SECONDS
    )

    if (
        force
        or missing
        or url_changed
        or refresh_due
    ):
        return refresh_data(
            sheet_url
        )

    return st.session_state.dashboard_df


# ============================================================
# HELPERS
# ============================================================
def money(value):
    if pd.isna(value):
        return "—"

    prefix = (
        f"{COST_CURRENCY} "
        if COST_CURRENCY
        else ""
    )

    return f"{prefix}{value:,.0f}"


def date_text(value):
    if pd.isna(value):
        return "—"

    return pd.Timestamp(
        value
    ).strftime(
        "%d %b %Y"
    )


def table_view(frame):
    out = frame.copy()

    for col in [
        "Induction Date",
        "Release date",
        "Forecast Release Date",
        "Last Update",
    ]:
        if col in out.columns:
            out[col] = out[
                col
            ].apply(
                date_text
            )

    if "TAT" in out.columns:
        if "TAT valid" in out.columns:
            out["TAT"] = out.apply(
                lambda row: (
                    "Check data"
                    if not bool(
                        row["TAT valid"]
                    )
                    else (
                        "—"
                        if pd.isna(
                            row["TAT"]
                        )
                        else f"{row['TAT']:,.0f}"
                    )
                ),
                axis=1,
            )

            out = out.drop(
                columns=[
                    "TAT valid"
                ]
            )

        else:
            out["TAT"] = out[
                "TAT"
            ].apply(
                lambda value: (
                    "—"
                    if pd.isna(value)
                    else f"{value:,.0f}"
                )
            )

    if "SV cost" in out.columns:
        out["SV cost"] = out[
            "SV cost"
        ].apply(
            money
        )

    return out


def chart_style(
    fig,
    height=350,
):
    fig.update_layout(
        height=height,
        margin=dict(
            l=8,
            r=8,
            t=48,
            b=8,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        title_font=dict(
            size=16,
            color="#0B1F33",
        ),
        font=dict(
            color="#233247",
        ),
        legend_title_text="",
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
    )

    fig.update_yaxes(
        gridcolor="#EEF2F6",
        zeroline=False,
    )

    return fig


PLOT_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
}


def reset_monitor_filters():
    st.session_state[
        "phase_filter_v13"
    ] = "All"

    st.session_state[
        "progress_filter_v471"
    ] = []

    st.session_state[
        "mro_filter_v13"
    ] = "All"

    st.session_state[
        "engine_type_filter_v13"
    ] = "All"

    st.session_state[
        "scope_filter_v15"
    ] = "All"

    st.session_state[
        "esn_filter_v13"
    ] = ""

    st.session_state[
        "table_search_v13"
    ] = ""

    st.session_state[
        "monitor_period_v455"
    ] = "All History"

    st.session_state[
        "monitor_date_basis_v455"
    ] = "Induction Date"

    st.session_state.pop(
        "monitor_custom_range_v455",
        None,
    )


# ============================================================
# SESSION
# ============================================================
configured = configured_source_url(
    "engine_shop_visit",
    GOOGLE_SHEET_URL.strip(),
)

if (
    configured
    == "PASTE_YOUR_GOOGLE_SHEET_LINK_HERE"
):
    configured = ""

if (
    "sheet_url"
    not in st.session_state
):
    st.session_state.sheet_url = (
        configured
    )

if (
    "sheet_input"
    not in st.session_state
):
    _active_engine_source = str(st.session_state.get("sheet_url", "") or "").strip()
    st.session_state.sheet_input = (
        _active_engine_source
        if _active_engine_source and _active_engine_source != "__uploaded_engine__"
        else configured
    )

if (
    "selected_esn"
    not in st.session_state
):
    st.session_state.selected_esn = ""


# v4.8.9 — restore Engine room data after moving through another room.
if "dashboard_df" not in st.session_state and isinstance(st.session_state.get("engine_room_cached_df"), pd.DataFrame):
    st.session_state.dashboard_df = st.session_state["engine_room_cached_df"].copy()
    _cached_engine_source = str(st.session_state.get("engine_room_cached_source", "") or "").strip()
    if _cached_engine_source:
        st.session_state.sheet_url = _cached_engine_source
        st.session_state.loaded_sheet_url = _cached_engine_source

# v4.7.5 — sidebar source controls are defined in the main stylesheet above.

# ============================================================
# SIDEBAR CONNECTION
# ============================================================
with st.sidebar:
    st.markdown(
        f"""
        <div class="shop-room-brand">
          <img src="{GARUDA_LOGO_URI}" alt="Garuda Indonesia" />
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="cc-nav-label">Rooms</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="cc-nav-active"><span class="nav-dot"></span>Engine Shop Visit</div>',
        unsafe_allow_html=True,
    )
    if st.button("APU Shop Visit", use_container_width=True, key="engine_side_apu"):
        st.switch_page("apu_shop_visit_page.py")
    if st.button("Reliability Room", use_container_width=True, key="engine_side_reliability"):
        st.switch_page("reliability_page.py")
    if st.button("Control Center", use_container_width=True, key="engine_side_home"):
        st.switch_page("home.py")

    st.markdown('<div class="sidebar-section">Data connection</div>', unsafe_allow_html=True)
    st.markdown('<div class="source-label">Source URL or local file</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="source-meta">Google Sheets · SharePoint Doc.aspx / OneDrive Excel · local Excel/CSV</div>',
        unsafe_allow_html=True,
    )
    st.text_input(
        "Source URL / file path",
        key="sheet_input",
        placeholder="Paste Google Sheet / SharePoint URL or file path…",
        label_visibility="collapsed",
    )

    st.markdown('<div class="source-label">Upload file</div>', unsafe_allow_html=True)
    uploaded_engine_source = st.file_uploader(
        "Upload Excel / CSV",
        type=["xlsx", "xls", "csv"],
        key="engine_sv_source_upload",
        label_visibility="collapsed",
    )
    if uploaded_engine_source is not None:
        remember_upload("engine_sv_session_upload", uploaded_engine_source)

    # File-uploader widgets cannot be repopulated by Streamlit after navigating
    # to another page. Keep the bytes in a separate session key and rebuild a
    # file-like object transparently when the user returns to this room.
    _engine_remembered_info = upload_memory_info("engine_sv_session_upload")
    if _engine_remembered_info and uploaded_engine_source is None:
        st.markdown(
            f'<div style="margin-top:-4px;margin-bottom:8px;color:#9FB7D1;font-size:11px;">'
            f'Active session file: <b style="color:#EAF3FC">{_engine_remembered_info["name"]}</b></div>',
            unsafe_allow_html=True,
        )

    connect_clicked = st.button(
        "Connect / Test",
        type="primary",
        use_container_width=True,
    )


# Restore remembered Engine upload when returning from another room. A newly
# typed URL still takes precedence when Connect / Test is clicked.
_engine_candidate_now = str(st.session_state.get("sheet_input", "") or "").strip()
if uploaded_engine_source is None and not _engine_candidate_now:
    uploaded_engine_source = restore_upload("engine_sv_session_upload")

if connect_clicked:
    candidate = (
        st.session_state
        .sheet_input
        .strip()
    )

    if uploaded_engine_source is not None and not candidate:
        try:
            with st.spinner("Reading uploaded Engine Shop Visit file..."):
                data = fetch_uploaded_dashboard_data(uploaded_engine_source)
            st.session_state.dashboard_df = data
            st.session_state.engine_room_cached_df = data.copy()
            st.session_state.engine_room_cached_source = "__uploaded_engine__"
            st.session_state.loaded_sheet_url = "__uploaded_engine__"
            st.session_state.source_label = data.attrs.get("source_label", "Uploaded Excel/CSV")
            st.session_state.source_rows = data.attrs.get("source_rows", len(data))
            st.session_state.source_esn_column = data.attrs.get("source_esn_column", "ESN")
            st.session_state.schema_match_count = data.attrs.get("schema_match_count", 0)
            st.session_state.schema_score = data.attrs.get("schema_score", 0)
            st.session_state.last_fetch_epoch = time.time()
            st.session_state.last_sync = datetime.now().strftime("%d %b %Y · %H:%M:%S")
            st.session_state.sheet_url = "__uploaded_engine__"
            st.rerun()
        except Exception as exc:
            st.sidebar.error(str(exc))
    elif not is_supported_source_url(candidate):
        st.sidebar.error(
            "Source tidak dikenali. Gunakan Google Sheets, SharePoint Doc.aspx/OneDrive Excel, local Excel/CSV, atau Upload Excel/CSV."
        )

    else:
        try:
            with st.spinner(
                "Connecting to data source..."
            ):
                data = refresh_data(
                    candidate
                )

            st.session_state.sheet_url = candidate
            if len(data):
                st.sidebar.success(
                    f"Connected · {len(data):,} rows · {st.session_state.get('source_label', 'Google Sheet')} · "
                    f"{st.session_state.get('schema_match_count', 0)} fields matched"
                )
            else:
                st.sidebar.warning(
                    "Connected, tetapi 0 valid shop-visit rows. "
                    f"Source: {st.session_state.get('source_label', 'Google Sheet')} · "
                    f"ESN column: {st.session_state.get('source_esn_column', 'not detected')}"
                )

            st.rerun()

        except Exception as exc:
            st.sidebar.error(
                str(exc)
            )


active_url = str(st.session_state.sheet_url or "").strip()

if not active_url:
    st.title(
        "Engine Shop Visit Dashboard"
    )

    st.info(
        "Connect Google Sheets / SharePoint Excel atau upload Excel/CSV dari sidebar."
    )

    st.stop()


# First load only.
try:
    if active_url != "__uploaded_engine__" and (
        "dashboard_df" not in st.session_state
        or st.session_state.get("loaded_sheet_url", "") != active_url
    ):
        with st.spinner("Loading data source..."):
            refresh_data(active_url)

except Exception as exc:
    st.error(
        str(exc)
    )
    st.stop()

# Share a concise live snapshot with the Control Center.
_cc_df = st.session_state.get("dashboard_df", pd.DataFrame())
if isinstance(_cc_df, pd.DataFrame) and not _cc_df.empty:
    st.session_state["cc_shop_snapshot"] = {
        "total": int(len(_cc_df)),
        "active": int(_cc_df["Status"].eq("Active").sum()) if "Status" in _cc_df.columns else 0,
        "on_hold": int(_cc_df["Phase"].eq("On Hold").sum()) if "Phase" in _cc_df.columns else 0,
        "ready_release": int(_cc_df["Phase"].eq("Ready for Release").sum()) if "Phase" in _cc_df.columns else 0,
        "need_review": int(_cc_df["Flag"].isin(["Review", "Check Data"]).sum()) if "Flag" in _cc_df.columns else 0,
        "last_sync": st.session_state.get("last_sync", "—"),
    }


# ============================================================
# LIVE SIDEBAR FRAGMENT
# Only this small area refreshes every 60 seconds.
# ============================================================
@st.fragment(
    run_every=AUTO_REFRESH_SECONDS
)
def live_sidebar():
    try:
        data = ensure_data(
            active_url
        )
    except Exception as exc:
        with st.sidebar:
            st.error(
                str(exc)
            )
        return

    latest_data_update = None

    if (
        "Last Update"
        in data.columns
        and data[
            "Last Update"
        ].notna().any()
    ):
        latest_data_update = (
            data[
                "Last Update"
            ].max()
        )

    with st.sidebar:
        st.markdown(
            '<div class="sidebar-section">Live status</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="sidebar-info">
                <strong>● LIVE</strong><br>
                <span>Connected to data source</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        extra_update = (
            f"<br><span>Last data update: {date_text(latest_data_update)}</span>"
            if latest_data_update is not None
            else ""
        )

        st.markdown(
            f"""
            <div class="sidebar-info">
              <strong>{len(data):,} shop visits</strong><br>
              <span>Auto sync: every {AUTO_REFRESH_SECONDS}s</span><br>
              <span>Filters: local / instant</span><br>
              <span>Last sync: {st.session_state.get('last_sync', '—')}</span><br>
              <span>Source: {st.session_state.get('source_label', 'Google Sheet')}</span><br>
              <span>Schema match: {st.session_state.get('schema_match_count', 0)} field(s)</span>
              {extra_update}
            </div>
            """,
            unsafe_allow_html=True,
        )

        refresh_clicked = st.button(
            "↻ Refresh now",
            use_container_width=True,
            key="refresh_now_v13",
        )

    if refresh_clicked:
        try:
            with st.spinner(
                "Refreshing data source..."
            ):
                ensure_data(
                    active_url,
                    force=True,
                )

            st.rerun()

        except Exception as exc:
            st.sidebar.error(
                str(exc)
            )


live_sidebar()


# ============================================================
# HEADER
# ============================================================
_nav_spacer, _nav_col = st.columns([9.2, 0.8])
with _nav_col:
    with st.popover("☰ Rooms"):
        st.markdown("**Workspace**")
        st.caption("Current: Engine Shop Visit")
        if st.button("Control Center", use_container_width=True, key="cc_home_from_shop_popover"):
            st.switch_page("home.py")
        if st.button("Reliability Room", use_container_width=True, key="cc_rel_from_shop_popover"):
            st.switch_page("reliability_page.py")
        if st.button("APU Shop Visit", use_container_width=True, key="cc_apu_from_engine_popover"):
            st.switch_page("apu_shop_visit_page.py")

st.markdown(
    """
    <div class="hero">
        <h1>Engine Shop Visit Room</h1>
        <p>Live engine-level monitoring · Shop-visit progress · TAT · Scope · MRO time & cost performance</p>
    </div>
    """,
    unsafe_allow_html=True,
)


view_mode = st.radio(
    "Dashboard view",
    [
        "Monitoring",
        "MRO Performance",
    ],
    horizontal=True,
    label_visibility="collapsed",
    key="dashboard_view_v13",
)


# ============================================================
# MONITORING FRAGMENT
# Filter/search reruns ONLY this fragment.
# ============================================================
@st.fragment(
    run_every=AUTO_REFRESH_SECONDS
)
def monitoring_view():
    try:
        df = ensure_data(
            active_url
        )
    except Exception as exc:
        st.error(
            str(exc)
        )
        return

    # --------------------------------------------------------
    # MONITORING PERIOD
    # --------------------------------------------------------
    st.markdown(
        "<div class='section-title'>Monitoring period</div>",
        unsafe_allow_html=True,
    )

    p1, p2, p3 = st.columns([1.0, 1.05, 1.95])

    with p1:
        period_choice = st.selectbox(
            "Period",
            [
                "All History",
                "Year to Date",
                "Last 12 Months",
                "Last 24 Months",
                "Custom",
            ],
            key="monitor_period_v455",
            help="This period filter applies to the Monitoring KPIs, charts and engine table.",
        )

    date_basis_labels = {
        "Induction Date": "Induction Date",
        "removal date": "Removal Date",
        "Release date": "Release Date",
    }

    with p2:
        date_basis = st.selectbox(
            "Date basis",
            list(date_basis_labels.keys()),
            format_func=lambda value: date_basis_labels[value],
            key="monitor_date_basis_v455",
            help=(
                "Induction Date is recommended for shop-visit monitoring because it represents "
                "the start of TAT. Release Date is useful for completed-shop-visit history."
            ),
        )

    date_series = pd.to_datetime(
        df[date_basis],
        errors="coerce",
    )
    valid_dates = date_series.dropna()
    today = pd.Timestamp.today().normalize()
    period_start = None
    period_end = None

    if not valid_dates.empty:
        data_min = valid_dates.min().normalize()
        data_max = valid_dates.max().normalize()

        if period_choice == "Year to Date":
            period_start = pd.Timestamp(year=today.year, month=1, day=1)
            period_end = today
        elif period_choice == "Last 12 Months":
            period_start = today - pd.DateOffset(months=12)
            period_end = today
        elif period_choice == "Last 24 Months":
            period_start = today - pd.DateOffset(months=24)
            period_end = today
        elif period_choice == "Custom":
            default_start = max(data_min, today - pd.DateOffset(months=12))
            default_end = min(max(data_max, default_start), today)
            with p3:
                custom_range = st.date_input(
                    "Custom date range",
                    value=(default_start.date(), default_end.date()),
                    min_value=data_min.date(),
                    max_value=max(data_max, today).date(),
                    key="monitor_custom_range_v455",
                )
            if isinstance(custom_range, (tuple, list)) and len(custom_range) == 2:
                period_start = pd.Timestamp(custom_range[0])
                period_end = pd.Timestamp(custom_range[1])
        else:
            with p3:
                st.markdown(
                    f"<div style='padding-top:30px;color:#667085;font-size:.86rem;'>"
                    f"Available data: <b>{data_min:%d %b %Y}</b> → <b>{data_max:%d %b %Y}</b>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
    else:
        with p3:
            st.warning(f"No valid {date_basis_labels[date_basis]} values found in the source.")

    if period_start is not None and period_end is not None:
        if period_start > period_end:
            period_start, period_end = period_end, period_start
        date_mask = date_series.between(period_start, period_end, inclusive="both")
        df = df.loc[date_mask].copy()
        st.caption(
            f"Monitoring period: **{period_start:%d %b %Y} → {period_end:%d %b %Y}** "
            f"based on **{date_basis_labels[date_basis]}** · {len(df):,} source record(s) in period"
        )
    else:
        st.caption(
            f"Monitoring period: **All History** · date basis: **{date_basis_labels[date_basis]}**"
        )

    # --------------------------------------------------------
    # FILTERS
    # --------------------------------------------------------
    st.markdown(
        '<div class="toolbar">',
        unsafe_allow_html=True,
    )

    f1, f2, f3, f4, f5, f6, f7 = (
        st.columns(
            [
                1.05,
                1.15,
                .85,
                .85,
                1.35,
                .95,
                .45,
            ]
        )
    )

    phase_counts = (
        df["Phase"]
        .value_counts(
            dropna=False
        )
        .to_dict()
    )

    phase_map = {
        "All": "All"
    }

    for phase_name in PHASES:
        count = int(
            phase_counts.get(
                phase_name,
                0,
            )
        )

        phase_map[
            f"{phase_name} ({count})"
        ] = phase_name

    # Preserve unexpected values in the source.
    extras = sorted(
        str(value)
        for value in df[
            "Phase"
        ].dropna().unique()
        if (
            str(value).strip()
            and str(value)
            not in set(PHASES)
        )
    )

    for phase_name in extras:
        count = int(
            phase_counts.get(
                phase_name,
                0,
            )
        )

        phase_map[
            f"{phase_name} ({count})"
        ] = phase_name

    if (
        "phase_filter_v13"
        not in st.session_state
    ):
        st.session_state[
            "phase_filter_v13"
        ] = "All"

    with f1:
        phase_label = st.selectbox(
            "Phase",
            list(
                phase_map.keys()
            ),
            key="phase_filter_v13",
        )

        phase = phase_map[
            phase_label
        ]

    # Synthetic operational filter. ``Off Wing`` means every populated
    # Progress/Progres state except a completed state. Keep the original
    # source values available as exact filters as well.
    OFF_WING_PROGRESS = "Off Wing"
    source_progress_options = sorted(
        str(value)
        for value in df[
            "Progres"
        ].dropna().unique()
        if str(value).strip()
        and str(value).strip().casefold() != OFF_WING_PROGRESS.casefold()
    )
    progress_options = [OFF_WING_PROGRESS] + source_progress_options

    mro_options = (
        ["All"]
        + sorted(
            str(value)
            for value in df[
                "MRO"
            ].dropna().unique()
            if str(value).strip()
        )
    )

    engine_types = (
        ["All"]
        + sorted(
            str(value)
            for value in df[
                "engine type"
            ].dropna().unique()
            if str(value).strip()
        )
    )

    scope_options = (
        ["All"]
        + sorted(
            str(value)
            for value in df[
                "Scope of work"
            ].dropna().unique()
            if str(value).strip()
        )
    )

    with f2:
        progress_filter = st.multiselect(
            "Progress",
            progress_options,
            key="progress_filter_v471",
            help="Off Wing = all progress states except Completed. Other options match the exact Progress/Progres value from the source.",
        )

    with f3:
        mro = st.selectbox(
            "MRO",
            mro_options,
            key="mro_filter_v13",
        )

    with f4:
        engine_type = st.selectbox(
            "Engine type",
            engine_types,
            key="engine_type_filter_v13",
        )

    with f5:
        scope_filter = st.selectbox(
            "Scope of work",
            scope_options,
            key="scope_filter_v15",
            help="Exact Scope of work value from the Google Sheet / Excel source.",
        )

    with f6:
        esn_search = st.text_input(
            "Search ESN",
            placeholder=(
                "Type ESN, e.g. 804352"
            ),
            key="esn_filter_v13",
        )

    with f7:
        st.write("")
        st.write("")

        st.button(
            "Reset",
            use_container_width=True,
            on_click=reset_monitor_filters,
            key="reset_filters_v13",
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # LOCAL FILTERING
    # --------------------------------------------------------
    monitor_view = (
        df.copy()
    )

    if phase != "All":
        monitor_view = (
            monitor_view[
                monitor_view[
                    "Phase"
                ]
                == phase
            ]
        )
    else:
        monitor_view = (
            monitor_view[
                monitor_view[
                    "Status"
                ]
                == "Active"
            ]
        )

    if progress_filter:
        selected_progress = set(progress_filter)
        progress_text = (
            monitor_view["Progres"]
            .astype("string")
            .fillna("")
            .str.strip()
        )

        progress_mask = pd.Series(False, index=monitor_view.index)

        if OFF_WING_PROGRESS in selected_progress:
            normalized_progress = progress_text.str.casefold()
            progress_mask |= (
                normalized_progress.ne("")
                & ~normalized_progress.isin({"completed", "complete"})
            )

        exact_progress = selected_progress - {OFF_WING_PROGRESS}
        if exact_progress:
            progress_mask |= progress_text.isin(exact_progress)

        monitor_view = monitor_view[progress_mask]

    if mro != "All":
        monitor_view = (
            monitor_view[
                monitor_view[
                    "MRO"
                ].astype(str)
                == mro
            ]
        )

    if engine_type != "All":
        monitor_view = (
            monitor_view[
                monitor_view[
                    "engine type"
                ].astype(str)
                == engine_type
            ]
        )

    if scope_filter != "All":
        monitor_view = (
            monitor_view[
                monitor_view[
                    "Scope of work"
                ].astype(str)
                == scope_filter
            ]
        )

    if esn_search.strip():
        monitor_view = (
            monitor_view[
                monitor_view[
                    "ESN"
                ].astype(str)
                .str.contains(
                    re.escape(
                        esn_search.strip()
                    ),
                    case=False,
                    na=False,
                )
            ]
        )

    st.caption(
        f"Showing **{len(monitor_view):,}** record(s)"
    )

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------
    k1, k2, k3, k4, k5 = (
        st.columns(5)
    )

    k1.metric(
        "Records in View",
        f"{len(monitor_view):,}",
    )

    k2.metric(
        "Active",
        f"{int(monitor_view['Status'].eq('Active').sum()):,}",
    )

    k3.metric(
        "On Hold",
        f"{int(monitor_view['Phase'].eq('On Hold').sum()):,}",
    )

    k4.metric(
        "Ready Release",
        f"{int(monitor_view['Phase'].eq('Ready for Release').sum()):,}",
    )

    k5.metric(
        "Need Review",
        f"{int(monitor_view['Flag'].isin(['Review','Check Data']).sum()):,}",
    )

    # --------------------------------------------------------
    # CHARTS
    # --------------------------------------------------------
    st.markdown(
        '<div class="section-title">Monitoring snapshot</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = (
        st.columns(2)
    )

    with c1:
        if phase == "All":
            phase_source = (
                monitor_view
                .groupby("Phase")
                .size()
                .reset_index(
                    name="Engines"
                )
            )

            if (
                phase_source.empty
            ):
                st.info(
                    "No phase data."
                )

            else:
                fig = px.bar(
                    phase_source,
                    x="Phase",
                    y="Engines",
                    text="Engines",
                    title=(
                        "Active portfolio by phase"
                    ),
                )

                fig.update_traces(
                    textposition="outside"
                )

                st.plotly_chart(
                    chart_style(
                        fig,
                        345,
                    ),
                    use_container_width=True,
                    config=PLOT_CONFIG,
                )

        else:
            mro_source = (
                monitor_view[
                    monitor_view[
                        "MRO"
                    ]
                    .astype("string")
                    .fillna("")
                    .str.strip()
                    .ne("")
                ]
            )

            if (
                mro_source.empty
            ):
                st.info(
                    "No MRO distribution available."
                )

            else:
                mro_counts = (
                    mro_source
                    .groupby("MRO")
                    .size()
                    .reset_index(
                        name="Engines"
                    )
                    .sort_values(
                        "Engines"
                    )
                )

                fig = px.bar(
                    mro_counts,
                    x="Engines",
                    y="MRO",
                    orientation="h",
                    text="Engines",
                    title=(
                        f"{phase} by MRO"
                    ),
                )

                fig.update_traces(
                    textposition="outside"
                )

                st.plotly_chart(
                    chart_style(
                        fig,
                        345,
                    ),
                    use_container_width=True,
                    config=PLOT_CONFIG,
                )

    with c2:
        tat_source = (
            monitor_view[
                (
                    monitor_view[
                        "Status"
                    ]
                    == "Active"
                )
                & monitor_view[
                    "TAT valid"
                ]
            ]
            .copy()
        )

        invalid_count = int(
            (
                (
                    monitor_view[
                        "Status"
                    ]
                    == "Active"
                )
                & (
                    ~monitor_view[
                        "TAT valid"
                    ]
                )
            ).sum()
        )

        if (
            tat_source.empty
        ):
            st.info(
                "No valid active TAT records."
            )

        else:
            watch = (
                tat_source
                .sort_values(
                    "TAT",
                    ascending=False,
                )
                .head(10)
                .sort_values(
                    "TAT"
                )
                .copy()
            )

            watch[
                "Engine"
            ] = watch.apply(
                lambda row: (
                    f"{row['ESN']} · {row['MRO']}"
                    if str(
                        row["MRO"]
                    ).strip()
                    else str(
                        row["ESN"]
                    )
                ),
                axis=1,
            )

            fig = px.bar(
                watch,
                x="TAT",
                y="Engine",
                orientation="h",
                text="TAT",
                color="Flag",
                custom_data=[
                    "ESN",
                    "MRO",
                    "Phase",
                    "Engine Owner",
                    "Key Issue",
                ],
                title=(
                    "Active TAT watchlist"
                ),
            )

            fig.update_traces(
                texttemplate=(
                    "%{text:.0f}d"
                ),
                textposition="outside",
                hovertemplate=(
                    "<b>ESN %{customdata[0]}</b><br>"
                    "TAT: %{x:.0f} days<br>"
                    "MRO: %{customdata[1]}<br>"
                    "Phase: %{customdata[2]}<br>"
                    "Owner: %{customdata[3]}<br>"
                    "Issue: %{customdata[4]}"
                    "<extra></extra>"
                ),
            )

            fig.update_yaxes(
                type="category",
                title="Engine",
            )

            fig.update_xaxes(
                title="TAT (days)"
            )

            st.plotly_chart(
                chart_style(
                    fig,
                    345,
                ),
                use_container_width=True,
                config=PLOT_CONFIG,
            )

            if invalid_count:
                st.caption(
                    f"{invalid_count} invalid / implausible TAT record(s) excluded."
                )

    # --------------------------------------------------------
    # TABLE SEARCH
    # --------------------------------------------------------
    st.markdown(
        '<div class="section-title">Engine status</div>',
        unsafe_allow_html=True,
    )

    table_search = st.text_input(
        "Search in table",
        placeholder=(
            "ESN, MRO, phase, owner, issue, scope..."
        ),
        key="table_search_v13",
    )

    table_df = (
        monitor_view.copy()
    )

    if table_search.strip():
        query = (
            table_search
            .strip()
        )

        searchable = [
            "ESN",
            "MRO",
            "Phase",
            "Engine Owner",
            "Key Issue",
            "Scope of work",
            "reason of removal",
            "engine type",
        ]

        mask = pd.Series(
            False,
            index=table_df.index,
        )

        for col in searchable:
            if (
                col
                in table_df.columns
            ):
                mask = (
                    mask
                    | table_df[
                        col
                    ]
                    .astype("string")
                    .fillna("")
                    .str.contains(
                        re.escape(query),
                        case=False,
                        na=False,
                    )
                )

        table_df = (
            table_df[
                mask
            ]
        )

    st.caption(
        f"Table records: {len(table_df):,}"
    )

    table_cols = [
        "ESN",
        "MRO",
        "Scope of work",
        "Phase",
        "TAT",
        "TAT valid",
        "Forecast Release Date",
        "Flag",
        "Key Issue",
        "Engine Owner",
        "SV cost",
    ]

    event = st.dataframe(
        table_view(
            table_df[
                table_cols
            ]
        ),
        hide_index=True,
        use_container_width=True,
        height=min(
            560,
            80
            + 36
            * max(
                len(table_df),
                1,
            ),
        ),
        on_select="rerun",
        selection_mode="single-row",
        key="monitor_table_v13",
        column_config={
            "Scope of work": st.column_config.TextColumn(
                "Scope of Work",
                width="large",
                help="Workscope exactly as recorded in the source spreadsheet.",
            ),
            "ESN": st.column_config.TextColumn("ESN", width="small"),
            "MRO": st.column_config.TextColumn("MRO", width="small"),
        },
    )

    selected_rows = []

    try:
        selected_rows = (
            event
            .selection
            .rows
        )
    except Exception:
        pass

    if selected_rows:
        selected_index = (
            selected_rows[0]
        )

        if (
            0
            <= selected_index
            < len(table_df)
        ):
            st.session_state[
                "selected_esn"
            ] = str(
                table_df.iloc[
                    selected_index
                ]["ESN"]
            )

    # --------------------------------------------------------
    # ENGINE DETAIL
    # --------------------------------------------------------
    selected_esn = (
        st.session_state
        .get(
            "selected_esn",
            "",
        )
    )

    if (
        selected_esn
        and selected_esn
        in table_df[
            "ESN"
        ].astype(str).values
    ):
        engine_rows = (
            df[
                df[
                    "ESN"
                ].astype(str)
                == selected_esn
            ]
            .copy()
        )

        engine_rows[
            "_sort"
        ] = (
            engine_rows[
                "Induction Date"
            ]
            .fillna(
                pd.Timestamp(
                    "1900-01-01"
                )
            )
        )

        active_rows = (
            engine_rows[
                engine_rows[
                    "Status"
                ]
                == "Active"
            ]
        )

        if (
            not active_rows.empty
        ):
            row = (
                active_rows
                .sort_values(
                    "_sort",
                    ascending=False,
                )
                .iloc[0]
            )
        else:
            row = (
                engine_rows
                .sort_values(
                    "_sort",
                    ascending=False,
                )
                .iloc[0]
            )

        st.markdown("---")
        st.markdown(
            f"## ESN {row['ESN']}"
        )

        scope_text = (
            row["Scope of work"]
            if str(row["Scope of work"]).strip()
            else "—"
        )

        st.markdown(
            f"**Scope of Work:** {scope_text}"
        )

        d1, d2, d3, d4 = (
            st.columns(4)
        )

        tat_text = (
            "Check data"
            if not bool(
                row[
                    "TAT valid"
                ]
            )
            else (
                f"{row['TAT']:.0f} days"
                if pd.notna(
                    row["TAT"]
                )
                else "—"
            )
        )

        d1.markdown(
            f"""
            <div class="detail-card">
              <div class="detail-label">Current Phase</div>
              <div class="detail-value">{row['Phase']}</div>
              <div class="detail-sub">TAT: {tat_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        d2.markdown(
            f"""
            <div class="detail-card">
              <div class="detail-label">Forecast Release</div>
              <div class="detail-value">{date_text(row['Forecast Release Date'])}</div>
              <div class="detail-sub">Actual: {date_text(row['Release date'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        d3.markdown(
            f"""
            <div class="detail-card">
              <div class="detail-label">Issue</div>
              <div class="detail-value">{row['Key Issue'] or 'No issue recorded'}</div>
              <div class="detail-sub">{row['Flag'] or 'Completed'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        d4.markdown(
            f"""
            <div class="detail-card">
              <div class="detail-label">SV Cost</div>
              <div class="detail-value">{money(row['SV cost'])}</div>
              <div class="detail-sub">Owner: {row['Engine Owner'] or '—'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(
            "View full engine detail & history"
        ):
            left, right = (
                st.columns(2)
            )

            with left:
                st.write(
                    "**Reason of removal:**",
                    row[
                        "reason of removal"
                    ]
                    if pd.notna(
                        row[
                            "reason of removal"
                        ]
                    )
                    else "—",
                )

                st.write(
                    "**Scope of work:**",
                    row[
                        "Scope of work"
                    ]
                    if pd.notna(
                        row[
                            "Scope of work"
                        ]
                    )
                    else "—",
                )

                st.write(
                    "**Induction:**",
                    date_text(
                        row[
                            "Induction Date"
                        ]
                    ),
                )

                st.write(
                    "**Release:**",
                    date_text(
                        row[
                            "Release date"
                        ]
                    ),
                )

            with right:
                st.write(
                    "**TSN:**",
                    "—"
                    if pd.isna(
                        row["TSN"]
                    )
                    else f"{row['TSN']:,.0f}",
                )

                st.write(
                    "**CSN:**",
                    "—"
                    if pd.isna(
                        row["CSN"]
                    )
                    else f"{row['CSN']:,.0f}",
                )

                st.write(
                    "**Lessor:**",
                    row["lessor"]
                    or "—",
                )

                st.write(
                    "**7B config:**",
                    row["7B config"]
                    or "—",
                )

            history_cols = [
                "Induction Date",
                "Release date",
                "MRO",
                "Scope of work",
                "Phase",
                "TAT",
                "TAT valid",
                "SV cost",
            ]

            st.dataframe(
                table_view(
                    engine_rows
                    .sort_values(
                        "Induction Date",
                        ascending=False,
                    )[
                        history_cols
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )


# ============================================================
# MRO PERFORMANCE FRAGMENT
# ============================================================
@st.fragment(
    run_every=AUTO_REFRESH_SECONDS
)


def mro_view():
    try:
        df = ensure_data(active_url)
    except Exception as exc:
        st.error(str(exc))
        return

    # --------------------------------------------------------
    # CLEAN MRO DATA
    # --------------------------------------------------------
    excluded_mro_labels = {
        "", "no sv", "hold", "unspecified", "n/a", "na", "-"
    }

    mro_text = (
        df["MRO"]
        .astype("string")
        .fillna("")
        .str.strip()
    )

    real_mro_mask = ~mro_text.str.lower().isin(excluded_mro_labels)

    completed_base = df[
        (df["Status"] == "Completed")
        & df["TAT valid"]
        & real_mro_mask
    ].copy()

    if completed_base.empty:
        st.info("No valid completed MRO records available.")
        return

    # --------------------------------------------------------
    # PRIMARY FILTERS
    # --------------------------------------------------------
    st.markdown(
        '<div class="section-title">MRO performance</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '''
        <div class="section-note">
        MRO TAT and cost should only be compared for the same Scope of Work.
        Start with Engine Type / Year, then select one specific scope for an apples-to-apples comparison.
        </div>
        ''',
        unsafe_allow_html=True,
    )

    f1, f2 = st.columns(2)

    engine_types = ["All"] + sorted(
        str(v) for v in completed_base["engine type"].dropna().unique()
        if str(v).strip()
    )

    years = ["All"] + sorted(
        [str(int(v)) for v in completed_base["Release Year"].dropna().unique()],
        reverse=True,
    )

    with f1:
        selected_type = st.selectbox(
            "Engine type",
            engine_types,
            key="mro_type_v16",
        )

    with f2:
        selected_year = st.selectbox(
            "Release year",
            years,
            key="mro_year_v16",
        )

    filtered_base = completed_base.copy()

    if selected_type != "All":
        filtered_base = filtered_base[
            filtered_base["engine type"].astype(str) == selected_type
        ]

    if selected_year != "All":
        filtered_base = filtered_base[
            filtered_base["Release Year"] == int(selected_year)
        ]

    if filtered_base.empty:
        st.info("No completed records match Engine Type / Year filters.")
        return

    # --------------------------------------------------------
    # SCOPE SELECTOR WITH CONTEXT
    # --------------------------------------------------------
    scope_series = (
        filtered_base["Scope of work"]
        .astype("string")
        .fillna("")
        .str.strip()
    )

    scope_ready = filtered_base[scope_series.ne("")].copy()
    missing_scope_n = int(scope_series.eq("").sum())

    if scope_ready.empty:
        st.warning(
            "Scope of Work is empty for the selected records. "
            "A fair MRO comparison cannot be built until Scope of Work is populated."
        )
        return

    scope_stats = (
        scope_ready
        .groupby("Scope of work")
        .agg(
            Completed_SV=("ESN", "count"),
            MRO_Count=("MRO", "nunique"),
            Median_TAT=("TAT", "median"),
        )
        .reset_index()
        .sort_values(["Completed_SV", "MRO_Count"], ascending=[False, False])
    )

    scope_label_to_value = {"All scopes — overview only": "__ALL__"}
    for _, r in scope_stats.iterrows():
        scope_name = str(r["Scope of work"])
        label = (
            f"{scope_name}  ·  N={int(r['Completed_SV'])}  ·  "
            f"MROs={int(r['MRO_Count'])}"
        )
        scope_label_to_value[label] = scope_name

    scope_label = st.selectbox(
        "Scope of work",
        list(scope_label_to_value.keys()),
        key="mro_scope_v16",
        help=(
            "Select one exact Scope of Work to enable like-for-like MRO TAT / cost comparison. "
            "All scopes intentionally disables cross-MRO performance ranking."
        ),
    )
    selected_scope = scope_label_to_value[scope_label]

    if missing_scope_n:
        st.caption(
            f"{missing_scope_n} completed record(s) have no Scope of Work and are excluded from scope-based analysis."
        )

    # --------------------------------------------------------
    # ALL-SCOPES MODE = CONTEXT ONLY, NO MRO RANKING
    # --------------------------------------------------------
    if selected_scope == "__ALL__":
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Completed SV", f"{len(scope_ready):,}")
        s2.metric("Distinct Scopes", f"{scope_ready['Scope of work'].nunique():,}")
        s3.metric("MROs", f"{scope_ready['MRO'].nunique():,}")
        s4.metric("Portfolio Median TAT", f"{scope_ready['TAT'].median():.0f} d")

        st.info(
            "Cross-MRO TAT/cost ranking is intentionally hidden while Scope of Work = All. "
            "Different scopes can have fundamentally different TAT and cost. Select one scope above to compare MROs fairly."
        )

        st.markdown(
            '<div class="section-title">Scope mix overview</div>',
            unsafe_allow_html=True,
        )

        scope_display = scope_stats.copy()
        scope_display["Median_TAT"] = scope_display["Median_TAT"].apply(
            lambda v: f"{v:.0f} d" if pd.notna(v) else "—"
        )
        scope_display.columns = [
            "Scope of Work",
            "Completed SV",
            "MROs represented",
            "Portfolio Median TAT",
        ]

        st.dataframe(
            scope_display,
            hide_index=True,
            use_container_width=True,
            height=min(520, 80 + 36 * max(len(scope_display), 1)),
        )

        c1, c2 = st.columns(2)

        with c1:
            top_scope = scope_stats.head(12).sort_values("Completed_SV")
            fig = px.bar(
                top_scope,
                x="Completed_SV",
                y="Scope of work",
                orientation="h",
                text="Completed_SV",
                title="Completed shop visits by scope",
                custom_data=["MRO_Count", "Median_TAT"],
            )
            fig.update_traces(
                texttemplate="N=%{text}",
                textposition="outside",
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Completed SV: %{x}<br>"
                    "MROs represented: %{customdata[0]}<br>"
                    "Portfolio median TAT: %{customdata[1]:.0f} d"
                    "<extra></extra>"
                ),
            )
            fig.update_xaxes(title="Completed shop visits")
            fig.update_yaxes(title="Scope of Work")
            st.plotly_chart(
                chart_style(fig, 420),
                use_container_width=True,
                config=PLOT_CONFIG,
            )

        with c2:
            mro_sample = (
                scope_ready.groupby("MRO")
                .agg(
                    Completed_SV=("ESN", "count"),
                    Distinct_Scopes=("Scope of work", "nunique"),
                )
                .reset_index()
                .sort_values("Completed_SV")
            )
            fig = px.bar(
                mro_sample,
                x="Completed_SV",
                y="MRO",
                orientation="h",
                text="Completed_SV",
                title="Historical workload by MRO — context only",
                custom_data=["Distinct_Scopes"],
            )
            fig.update_traces(
                texttemplate="N=%{text}",
                textposition="outside",
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Completed SV: %{x}<br>"
                    "Distinct scopes: %{customdata[0]}"
                    "<extra></extra>"
                ),
            )
            fig.update_xaxes(title="Completed shop visits")
            st.plotly_chart(
                chart_style(fig, 420),
                use_container_width=True,
                config=PLOT_CONFIG,
            )

        st.caption(
            "This overview describes workload mix only. It is not an MRO performance ranking."
        )
        return

    # --------------------------------------------------------
    # SPECIFIC-SCOPE MODE = LIKE-FOR-LIKE MRO COMPARISON
    # --------------------------------------------------------
    completed = scope_ready[
        scope_ready["Scope of work"].astype(str) == selected_scope
    ].copy()

    if completed.empty:
        st.info("No completed records are available for this scope.")
        return

    active_scope_text = (
        df["Scope of work"]
        .astype("string")
        .fillna("")
        .str.strip()
    )
    active_now_df = df[
        (df["Status"] == "Active")
        & real_mro_mask
        & (active_scope_text == selected_scope)
    ].copy()

    if selected_type != "All":
        active_now_df = active_now_df[
            active_now_df["engine type"].astype(str) == selected_type
        ]

    active_now = active_now_df.groupby("MRO").size().rename("Active_Now")

    score = (
        completed
        .groupby("MRO")
        .agg(
            Completed=("ESN", "count"),
            Median_TAT=("TAT", "median"),
            P75_TAT_RAW=("TAT", lambda s: s.quantile(.75)),
            Cost_Records=("SV cost", "count"),
            Median_Cost=("SV cost", "median"),
        )
        .join(active_now, how="left")
        .fillna({"Active_Now": 0})
        .reset_index()
    )

    score["Active_Now"] = score["Active_Now"].astype(int)
    score["P75_TAT"] = score["P75_TAT_RAW"].where(score["Completed"] >= 4)

    def sample_context(n):
        n = int(n)
        if n < 3:
            return "Very small sample"
        if n < 8:
            return "Small sample"
        return "Larger sample"

    score["Sample_Context"] = score["Completed"].apply(sample_context)
    score["Cost_Coverage"] = score["Cost_Records"] / score["Completed"]

    cost_records_total = int(completed["SV cost"].notna().sum())
    comparable_mros = int((score["Completed"] >= 3).sum())

    st.success(f"Like-for-like comparison active: {selected_scope}")

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Completed SV", f"{len(completed):,}")
    s2.metric("MROs Represented", f"{score['MRO'].nunique():,}")
    s3.metric(
        "Comparable MROs",
        f"{comparable_mros:,}",
        help="MROs with at least 3 completed visits for this exact scope.",
    )
    s4.metric("Scope Median TAT", f"{completed['TAT'].median():.0f} d")

    # --------------------------------------------------------
    # SCORECARD
    # --------------------------------------------------------
    st.markdown(
        '<div class="section-title">Scope-controlled MRO scorecard</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '''
        <div class="section-note">
        Every row below uses the same exact Scope of Work. MROs with fewer than 3 completed visits remain visible,
        but are not used in the comparative ranking chart.
        </div>
        ''',
        unsafe_allow_html=True,
    )

    display = score[[
        "MRO", "Completed", "Active_Now", "Median_TAT", "P75_TAT", "Sample_Context"
    ]].copy()

    display["Median_TAT"] = display["Median_TAT"].apply(
        lambda v: "—" if pd.isna(v) else f"{v:.0f} d"
    )
    display["P75_TAT"] = display["P75_TAT"].apply(
        lambda v: "—" if pd.isna(v) else f"{v:.0f} d"
    )
    display.columns = [
        "MRO", "Completed SV", "Active Now", "Median TAT", "P75 TAT", "Sample Context"
    ]

    if cost_records_total > 0:
        cost_display = score[["MRO", "Cost_Records", "Cost_Coverage", "Median_Cost"]].copy()
        cost_display["Cost_Coverage"] = cost_display["Cost_Coverage"].apply(
            lambda v: f"{v*100:.0f}%"
        )
        cost_display["Median_Cost"] = cost_display["Median_Cost"].apply(money)
        cost_display.columns = ["MRO", "Cost Records", "Cost Coverage", "Median Cost"]
        display = display.merge(cost_display, on="MRO", how="left")

    st.dataframe(
        display.sort_values(["Completed SV", "MRO"], ascending=[False, True]),
        hide_index=True,
        use_container_width=True,
    )

    if cost_records_total == 0:
        st.info("No SV cost is populated for this scope, so cost comparison is hidden.")

    # --------------------------------------------------------
    # TRUE COMPARISON CHARTS
    # --------------------------------------------------------
    comparison = score[score["Completed"] >= 3].copy()

    st.markdown(
        '<div class="section-title">Like-for-like performance comparison</div>',
        unsafe_allow_html=True,
    )

    if comparison.empty:
        st.warning(
            "This scope does not yet have any MRO with at least 3 completed shop visits. "
            "Use the scorecard as descriptive history only; a comparative chart would be too fragile."
        )
    else:
        c1, c2 = st.columns(2)

        with c1:
            comparison["MRO_Label"] = comparison.apply(
                lambda r: f"{r['MRO']} (N={int(r['Completed'])})",
                axis=1,
            )
            comparison = comparison.sort_values("Median_TAT")

            fig = px.bar(
                comparison,
                x="Median_TAT",
                y="MRO_Label",
                orientation="h",
                text="Median_TAT",
                custom_data=["MRO", "Completed", "P75_TAT"],
                title=f"Median TAT — {selected_scope}",
            )
            fig.update_traces(
                texttemplate="%{text:.0f}d",
                textposition="outside",
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Median TAT: %{x:.0f} d<br>"
                    "Completed sample: %{customdata[1]}<br>"
                    "P75: %{customdata[2]:.0f} d"
                    "<extra></extra>"
                ),
            )
            fig.update_xaxes(title="Median TAT (days)")
            fig.update_yaxes(title="MRO")
            st.plotly_chart(
                chart_style(fig, 395),
                use_container_width=True,
                config=PLOT_CONFIG,
            )

        with c2:
            if cost_records_total > 0:
                cost_comp = comparison[
                    comparison["Cost_Records"] > 0
                ].dropna(subset=["Median_Cost"]).copy()

                if cost_comp.empty:
                    st.info("No comparable cost records for this scope.")
                else:
                    cost_comp["MRO_Label"] = cost_comp.apply(
                        lambda r: f"{r['MRO']} (cost N={int(r['Cost_Records'])})",
                        axis=1,
                    )
                    fig = px.bar(
                        cost_comp.sort_values("Median_Cost"),
                        x="Median_Cost",
                        y="MRO_Label",
                        orientation="h",
                        custom_data=["MRO", "Cost_Records", "Cost_Coverage"],
                        title=f"Median SV cost — {selected_scope}",
                    )
                    fig.update_traces(
                        hovertemplate=(
                            "<b>%{customdata[0]}</b><br>"
                            "Median cost: %{x:,.0f}<br>"
                            "Cost sample: %{customdata[1]}<br>"
                            "Cost coverage: %{customdata[2]:.0%}"
                            "<extra></extra>"
                        )
                    )
                    fig.update_yaxes(title="MRO")
                    st.plotly_chart(
                        chart_style(fig, 395),
                        use_container_width=True,
                        config=PLOT_CONFIG,
                    )
            else:
                sample_chart = score.sort_values("Completed").copy()
                fig = px.bar(
                    sample_chart,
                    x="Completed",
                    y="MRO",
                    orientation="h",
                    text="Completed",
                    title=f"Sample size — {selected_scope}",
                )
                fig.update_traces(texttemplate="N=%{text}", textposition="outside")
                fig.update_xaxes(title="Completed shop visits")
                st.plotly_chart(
                    chart_style(fig, 395),
                    use_container_width=True,
                    config=PLOT_CONFIG,
                )

    # --------------------------------------------------------
    # SCOPE-SPECIFIC TAT TREND
    # --------------------------------------------------------
    st.markdown(
        '<div class="section-title">TAT trend for selected scope</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '''
        <div class="section-note">
        The trend below keeps Scope of Work fixed. Choose the selected-scope portfolio or one MRO.
        Each point shows the sample size used for the median.
        </div>
        ''',
        unsafe_allow_html=True,
    )

    trend_options = ["Selected-scope portfolio"] + sorted(
        str(v) for v in completed["MRO"].dropna().unique()
        if str(v).strip()
    )

    trend_choice = st.selectbox(
        "Trend to display",
        trend_options,
        key="tat_trend_v16",
    )

    if trend_choice == "Selected-scope portfolio":
        trend_source = completed.copy()
        trend_title = f"{selected_scope} — portfolio median TAT by quarter"
    else:
        trend_source = completed[
            completed["MRO"].astype(str) == trend_choice
        ].copy()
        trend_title = f"{trend_choice} · {selected_scope} — median TAT by quarter"

    trend = (
        trend_source
        .dropna(subset=["Release Quarter Period"])
        .groupby("Release Quarter Period")
        .agg(
            Median_TAT=("TAT", "median"),
            Sample=("ESN", "count"),
        )
        .reset_index()
        .sort_values("Release Quarter Period")
        .tail(10)
    )

    if len(trend) < 2:
        st.info("Not enough quarters for a meaningful trend for this scope / MRO selection.")
        return

    trend["Quarter"] = trend["Release Quarter Period"].astype(str)
    latest = trend.iloc[-1]
    previous = trend.iloc[-2]

    t1, t2, t3 = st.columns(3)
    t1.metric("Latest Median TAT", f"{latest['Median_TAT']:.0f} d")
    t2.metric("Latest Sample", f"N={int(latest['Sample'])}")
    t3.metric(
        "Change vs Previous",
        f"{latest['Median_TAT'] - previous['Median_TAT']:+.0f} d",
    )

    point_labels = [
        f"{tat:.0f}d<br>N={int(n)}"
        for tat, n in zip(trend["Median_TAT"], trend["Sample"])
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=trend["Quarter"],
            y=trend["Median_TAT"],
            mode="lines+markers+text",
            text=point_labels,
            textposition="top center",
            customdata=trend[["Sample"]],
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Median TAT: %{y:.0f} d<br>"
                "Completed sample: %{customdata[0]}"
                "<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title=trend_title,
        xaxis_title="Release quarter",
        yaxis_title="Median TAT (days)",
        showlegend=False,
    )
    st.plotly_chart(
        chart_style(fig, 410),
        use_container_width=True,
        config=PLOT_CONFIG,
    )

    low_sample = trend[trend["Sample"] < 3]
    if not low_sample.empty:
        st.warning(
            "Interpret with caution: these quarters have fewer than 3 completed shop visits: "
            + ", ".join(low_sample["Quarter"].tolist())
            + "."
        )

    current_quarter = pd.Timestamp.today().to_period("Q")
    if trend["Release Quarter Period"].iloc[-1] == current_quarter:
        st.caption("Latest point is the current quarter and may still be incomplete.")


if (
    view_mode
    == "Monitoring"
):
    monitoring_view()

else:
    mro_view()


st.markdown(
    f"""
    <div class="footer-note">
      Data is kept in session memory. Filter/search does not re-download Google Sheets.
    </div>
    """,
    unsafe_allow_html=True,
)
