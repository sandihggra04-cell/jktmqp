from __future__ import annotations


from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import base64
import hashlib
import re
import sys


import pandas as pd
import plotly.express as px
import requests
import streamlit as st

CONTROL_CENTER_ROOT = Path(__file__).resolve().parent
if str(CONTROL_CENTER_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_CENTER_ROOT))
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sv_source_loader import source_kind, is_supported_source_url, dataframes_from_remote_file, dataframes_from_uploaded_file, sharepoint_graph_status
from session_uploads import remember_upload, restore_upload, upload_memory_info


try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None


st.set_page_config(
    page_title="APU Shop Visit | Powerplant Engineering",
    page_icon="⚙️",
    layout="wide",
)


SOURCE_COLUMNS = [
    "APU SN",
    "Title",
    "induction date",
    "MRO",
    "scope of work",
    "release date",
    "Progress",
    "TAT",
    "removal date",
    "TSN",
    "CSN",
    "TSLV",
    "APU Type",
    "lessor",
    "Item Type",
    "Path",
    "SV cost",
]
DATE_COLUMNS = ["induction date", "release date", "removal date"]
NUMERIC_COLUMNS = ["TAT", "TSN", "CSN", "TSLV", "SV cost"]
ALIASES = {
    "APU SN": ["APU SN", "APU Serial Number", "APU Serial No", "APU S/N"],
    "Title": ["Title"],
    "induction date": ["induction date", "Induction Date"],
    "MRO": ["MRO"],
    "scope of work": ["scope of work", "Scope of work", "Scope of Work"],
    "release date": ["release date", "Release date", "Release Date"],
    "Progress": ["Progress", "Progres"],
    "TAT": ["TAT"],
    "removal date": ["removal date", "Removal Date"],
    "TSN": ["TSN"],
    "CSN": ["CSN"],
    "TSLV": ["TSLV"],
    "APU Type": ["APU Type", "APU type"],
    "lessor": ["lessor", "Lessor"],
    "Item Type": ["Item Type"],
    "Path": ["Path"],
    "SV cost": ["SV cost", "SV Cost"],
}


st.markdown(
    """
    <style>
      .block-container {padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1500px;}
      [data-testid="stSidebar"] {background: linear-gradient(180deg,#071a2c 0%,#0c2947 100%);}
      [data-testid="stSidebar"] * {color: #f6fbff;}
      [data-testid="stSidebar"] input {color: #0c1b2a !important; background: white !important;}
      [data-testid="stSidebar"] .stAlert {background:#ffffff !important;border:1px solid #d8e1ea !important;}
      [data-testid="stSidebar"] .stAlert * {color:#102A43 !important;-webkit-text-fill-color:#102A43 !important;}
      .apu-hero {
        border-radius: 20px; padding: 24px 28px; margin-bottom: 14px;
        background: linear-gradient(120deg,#071a2c 0%,#0b3154 72%,#0c6d92 145%);
        box-shadow: 0 12px 30px rgba(7,26,44,.16);
      }
      .apu-eyebrow {font-size: 12px; letter-spacing: .13em; color:#91d5ef; font-weight:700;}
      .apu-title {font-size: 34px; line-height:1.05; color:white; font-weight:760; margin-top:8px;}
      .apu-sub {font-size: 14px; color:#d9e9f5; margin-top:8px;}
      .section-label {font-size:12px; letter-spacing:.08em; text-transform:uppercase; color:#64748b; font-weight:750; margin:8px 0 4px;}
      .source-note {padding:10px 12px;border-radius:12px;background:#f5f8fb;border:1px solid #e3eaf0;color:#425466;font-size:12px;}
      div[data-testid="stMetric"] {border:1px solid #e3eaf0;border-radius:14px;padding:12px 14px;background:#fff;}
      div[data-testid="stMetricLabel"] {font-size:12px;}
    </style>
    """,
    unsafe_allow_html=True,
)




def _norm(value) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())




def _find_column(df: pd.DataFrame, canonical: str):
    lookup = {_norm(c): c for c in df.columns}
    for alias in ALIASES.get(canonical, [canonical]):
        key = _norm(alias)
        if key in lookup:
            return lookup[key]
    return None




def _recognized_count(df: pd.DataFrame) -> int:
    return sum(_find_column(df, col) is not None for col in SOURCE_COLUMNS)




def _is_apu_schema(df: pd.DataFrame) -> bool:
    return _find_column(df, "APU SN") is not None and _recognized_count(df) >= 10




def _sheet_id(url: str) -> str:
    text = str(url or "").strip()
    match = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", text)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{20,}", text):
        return text
    raise ValueError("Google Sheet URL tidak valid.")




def _sheet_gid(url: str):
    parsed = urlparse(str(url or "").strip())
    values = parse_qs(parsed.query)
    if values.get("gid"):
        return values["gid"][0]
    frag = parse_qs(parsed.fragment)
    if frag.get("gid"):
        return frag["gid"][0]
    match = re.search(r"(?:^|[&#?])gid=([0-9]+)", str(url or ""))
    return match.group(1) if match else None




def _numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    cleaned = (
        series.astype("string")
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace(r"[^0-9.\-]", "", regex=True)
    )
    return pd.to_numeric(cleaned, errors="coerce")




def clean_apu_source(raw: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=raw.index)
    for col in SOURCE_COLUMNS:
        src = _find_column(raw, col)
        out[col] = raw[src] if src is not None else pd.NA


    out["APU SN"] = out["APU SN"].astype("string").fillna("").str.strip()
    out = out[out["APU SN"].ne("")].copy()


    for col in DATE_COLUMNS:
        out[col] = pd.to_datetime(out[col], errors="coerce", dayfirst=True)


    for col in NUMERIC_COLUMNS:
        out[col] = _numeric(out[col])


    for col in ["Title", "MRO", "scope of work", "Progress", "APU Type", "lessor", "Item Type", "Path"]:
        out[col] = out[col].astype("string").fillna("").str.strip()


    return out.reset_index(drop=True)




LOCAL_APU_SNAPSHOT = Path(__file__).resolve().parent / "data" / "APU_Shop_Visit_Data_Snapshot.xlsx"


def _load_local_apu_snapshot():
    """Offline-safe snapshot bundled with this APU room.

    Used only when the selected Google Sheet cannot be exported anonymously
    (for example a company-private Sheet returning HTTP 401/403).
    """
    if not LOCAL_APU_SNAPSHOT.exists():
        raise FileNotFoundError("Bundled APU snapshot is not available.")
    book = pd.ExcelFile(LOCAL_APU_SNAPSHOT)
    best = None
    diagnostics = []
    for tab in book.sheet_names:
        try:
            df = pd.read_excel(book, sheet_name=tab)
        except Exception:
            continue
        score = _recognized_count(df)
        diagnostics.append(f"snapshot/{tab}: {score}/17 fields")
        if _find_column(df, "APU SN") is not None:
            candidate = (score, tab, df)
            if best is None or candidate[0] > best[0]:
                best = candidate
    if best is None or best[0] < 10:
        raise ValueError("Bundled APU snapshot does not match the expected schema.")
    score, tab, df = best
    return clean_apu_source(df), f"Bundled snapshot · {tab}", score, diagnostics


@st.cache_data(ttl=60, show_spinner=False)
def load_apu_source(url: str):
    kind = source_kind(url)
    diagnostics = []

    if kind in ("microsoft_list", "sharepoint", "file_url", "remote_data", "local_file"):
        frames = dataframes_from_remote_file(url)
        best = None
        for label, df in frames:
            score = _recognized_count(df)
            diagnostics.append(f"{label}: {score}/17 fields")
            if _find_column(df, "APU SN") is not None:
                candidate = (score, label, df)
                if best is None or candidate[0] > best[0]:
                    best = candidate
        if best is None or best[0] < 10:
            raise ValueError(
                "Source berhasil dibaca tetapi tidak ditemukan dataset dengan format APU Shop Visit terbaru."
            )
        score, label, df = best
        return clean_apu_source(df), label, score, diagnostics

    if kind != "google":
        raise ValueError(
            "Source tidak dikenali. Gunakan Google Sheets, SharePoint Doc.aspx/OneDrive Excel, direct Excel/CSV URL, atau Upload Excel/CSV."
        )

    sid = _sheet_id(url)
    gid = _sheet_gid(url)
    last_error = None

    if gid:
        csv_url = f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}"
        try:
            response = requests.get(csv_url, timeout=30)
            response.raise_for_status()
            df = pd.read_csv(BytesIO(response.content))
            diagnostics.append(f"gid={gid}: {_recognized_count(df)}/17 fields")
            if _is_apu_schema(df):
                return clean_apu_source(df), f"Live Google Sheet · gid={gid}", _recognized_count(df), diagnostics
        except Exception as exc:
            last_error = exc
            diagnostics.append(f"gid={gid}: {type(exc).__name__}")

    xlsx_url = f"https://docs.google.com/spreadsheets/d/{sid}/export?format=xlsx"
    try:
        response = requests.get(xlsx_url, timeout=40)
        response.raise_for_status()
        book = pd.ExcelFile(BytesIO(response.content))
        best = None
        for tab in book.sheet_names:
            try:
                df = pd.read_excel(book, sheet_name=tab)
            except Exception:
                continue
            score = _recognized_count(df)
            diagnostics.append(f"{tab}: {score}/17 fields")
            if _find_column(df, "APU SN") is not None:
                candidate = (score, tab, df)
                if best is None or candidate[0] > best[0]:
                    best = candidate
        if best is None or best[0] < 10:
            raise ValueError("Tidak ditemukan tab dengan format APU Shop Visit terbaru.")
        score, tab, df = best
        return clean_apu_source(df), f"Live Google Sheet · {tab}", score, diagnostics
    except Exception as exc:
        last_error = exc
        diagnostics.append(f"xlsx export: {type(exc).__name__}")

    raise RuntimeError(
        "Google Sheet tidak dapat di-export dari aplikasi lokal. Jika source perusahaan bersifat private, "
        "gunakan SharePoint private via Microsoft Graph atau Upload Excel/CSV di sidebar."
    ) from last_error


def load_apu_uploaded(uploaded):
    frames = dataframes_from_uploaded_file(uploaded)
    best = None
    diagnostics = []
    for label, df in frames:
        score = _recognized_count(df)
        diagnostics.append(f"{label}: {score}/17 fields")
        if _find_column(df, "APU SN") is not None:
            candidate = (score, label, df)
            if best is None or candidate[0] > best[0]:
                best = candidate
    if best is None or best[0] < 10:
        raise ValueError("Uploaded file tidak memiliki schema APU Shop Visit yang dikenali.")
    score, label, df = best
    return clean_apu_source(df), label, score, diagnostics


def _uploaded_file_signature(uploaded) -> str | None:
    if uploaded is None:
        return None
    try:
        data = uploaded.getvalue()
    except Exception:
        try:
            uploaded.seek(0)
            data = uploaded.read()
            uploaded.seek(0)
        except Exception:
            return None
    name = str(getattr(uploaded, "name", "uploaded_apu"))
    return f"{name}|{len(data)}|{hashlib.sha1(bytes(data)).hexdigest()}"


def _apu_cached_payload():
    if not isinstance(st.session_state.get("apu_room_cached_df"), pd.DataFrame):
        return None
    return (
        st.session_state["apu_room_cached_df"],
        st.session_state.get("apu_room_cached_source_label", "Session data"),
        st.session_state.get("apu_room_cached_schema_count", 0),
        st.session_state.get("apu_room_cached_diagnostics", []),
    )


def _fmt_number(value, decimals=0):
    if pd.isna(value):
        return "—"
    return f"{value:,.{decimals}f}"




def _excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df[SOURCE_COLUMNS].to_excel(writer, sheet_name="APU Shop Visit", index=False)
    return buffer.getvalue()




def _date_range(df: pd.DataFrame, basis: str, preset: str, custom):
    if df.empty or basis not in df.columns or preset == "All History":
        return df
    dates = df[basis]
    today = pd.Timestamp.today().normalize()
    if preset == "Year to Date":
        start = pd.Timestamp(today.year, 1, 1)
        end = today
    elif preset == "Last 12 Months":
        start = today - pd.DateOffset(months=12)
        end = today
    elif preset == "Last 24 Months":
        start = today - pd.DateOffset(months=24)
        end = today
    elif preset == "Custom" and custom and len(custom) == 2:
        start, end = pd.Timestamp(custom[0]), pd.Timestamp(custom[1])
    else:
        return df
    return df[dates.between(start, end, inclusive="both")].copy()




def _plot(fig, height=330):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=38, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
        legend_title_text="",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})




# Sidebar branding and source control
# v4.7.8 — use the same sidebar styling as Engine Shop Visit.
# v4.7.8 — APU sidebar navigation/source controls match Engine Shop Visit.
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background:#0B1F33 !important;
    }
    [data-testid="stSidebar"] > div:first-child { padding-top:.25rem!important; }
    [data-testid="stSidebarContent"], [data-testid="stSidebarUserContent"] { padding-top:.35rem!important; }
    [data-testid="stSidebarUserContent"] { margin-top:-.35rem!important; }

    .shop-room-brand {
        margin-top:-2.55rem!important;
        padding:0 2px 10px!important;
        margin-bottom:6px!important;
        border-bottom:1px solid rgba(255,255,255,.12);
    }
    .shop-room-brand img {
        display:block;
        width:220px!important;
        max-width:96%!important;
        height:auto;
        margin-bottom:6px!important;
    }
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
    .sidebar-section {
        color:#E5EEF8!important;
        font-size:.84rem!important;
        font-weight:700!important;
        text-transform:uppercase!important;
        letter-spacing:.04em!important;
        margin-top:1rem!important;
        margin-bottom:.35rem!important;
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

    [data-testid="stSidebar"] .stButton > button {
        width:100%;
        border-radius:11px!important;
        min-height:2.55rem;
        font-size:.82rem;
        font-weight:750!important;
        box-shadow:none!important;
    }
    [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {
        background:#17344F!important;
        border:1px solid #2E506E!important;
        color:#EAF2FA!important;
        -webkit-text-fill-color:#EAF2FA!important;
    }
    [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] * {
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
    [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] * {
        color:#FFFFFF!important;
        -webkit-text-fill-color:#FFFFFF!important;
    }
    [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover {
        filter:brightness(1.05)!important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

root = Path(__file__).resolve().parents[2]
logo_candidates = [
    root / "garuda_logo_white_generated_hd.png",
    root / "garuda_logo_white_ultra_hd.png",
    root / "garuda_logo_white.png",
]

def _apu_logo_data_uri() -> str:
    for logo in logo_candidates:
        if logo.exists():
            try:
                return "data:image/png;base64," + base64.b64encode(logo.read_bytes()).decode("ascii")
            except Exception:
                pass
    return ""

APU_LOGO_URI = _apu_logo_data_uri()

with st.sidebar:
    if APU_LOGO_URI:
        st.markdown(
            f'<div class="shop-room-brand"><img src="{APU_LOGO_URI}" alt="Garuda Indonesia" /></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="cc-nav-label">Rooms</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="cc-nav-active"><span class="nav-dot"></span>APU Shop Visit</div>',
        unsafe_allow_html=True,
    )
    if st.button("Engine Shop Visit", use_container_width=True, key="apu_to_engine"):
        st.switch_page("engine_shop_visit_page.py")
    if st.button("Reliability Room", use_container_width=True, key="apu_to_reliability"):
        st.switch_page("reliability_page.py")
    if st.button("Control Center", use_container_width=True, key="apu_exact_home"):
        st.switch_page("home.py")

    st.markdown('<div class="sidebar-section">Data connection</div>', unsafe_allow_html=True)
    st.markdown('<div class="source-label">Source URL or local file</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="source-meta">Google Sheets · SharePoint Doc.aspx / OneDrive Excel · local Excel/CSV</div>',
        unsafe_allow_html=True,
    )

    # v4.7.8: explicitly disconnect the previous bundled/default APU source once.
    # After that, preserve only what the user enters during the current session.
    if not st.session_state.get("apu_manual_source_v478_initialized", False):
        st.session_state["apu_exact_sheet_url"] = ""
        st.session_state["apu_manual_source_v478_initialized"] = True
    source_url = st.text_input(
        "Source URL / file path",
        value=st.session_state["apu_exact_sheet_url"],
        key="apu_exact_sheet_input",
        placeholder="Paste Google Sheet / SharePoint URL or file path…",
        label_visibility="collapsed",
    )
    st.session_state["apu_exact_sheet_url"] = source_url.strip()

    st.markdown('<div class="source-label">Upload file</div>', unsafe_allow_html=True)
    uploaded_apu_source = st.file_uploader(
        "Upload Excel / CSV",
        type=["xlsx", "xls", "csv"],
        key="apu_sv_source_upload",
        label_visibility="collapsed",
    )
    if uploaded_apu_source is not None:
        remember_upload("apu_sv_session_upload", uploaded_apu_source)

    _apu_remembered_info = upload_memory_info("apu_sv_session_upload")
    if _apu_remembered_info and uploaded_apu_source is None:
        st.markdown(
            f'<div style="margin-top:-4px;margin-bottom:8px;color:#9FB7D1;font-size:11px;">'
            f'Active session file: <b style="color:#EAF3FC">{_apu_remembered_info["name"]}</b></div>',
            unsafe_allow_html=True,
        )

    refresh = st.button(
        "Connect / Test",
        type="primary",
        use_container_width=True,
        key="apu_exact_refresh",
    )


if refresh:
    load_apu_source.clear()


if st_autorefresh is not None:
    st_autorefresh(interval=60_000, limit=None, key="apu_exact_auto_refresh")


# Header
h1, h2 = st.columns([0.84, 0.16])
with h1:
    st.markdown(
        """
        <div class="apu-hero">
          <div class="apu-eyebrow">GARUDA INDONESIA · POWERPLANT ENGINEERING</div>
          <div class="apu-title">APU Shop Visit Monitoring</div>
          <div class="apu-sub">TAT · TSLV · MRO · Scope of Work · SV Cost</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with h2:
    with st.popover("Rooms", use_container_width=True):
        if st.button("Control Center", use_container_width=True, key="apu_pop_home"):
            st.switch_page("home.py")
        if st.button("Engine Shop Visit", use_container_width=True, key="apu_pop_engine"):
            st.switch_page("engine_shop_visit_page.py")
        if st.button("Reliability", use_container_width=True, key="apu_pop_rel"):
            st.switch_page("reliability_page.py")


active_source_url = source_url.strip()

# v4.8.9 — a file uploaded in this room remains available while the browser
# session is alive, even after the user opens another room and comes back.
# A typed URL always takes precedence over an older remembered upload.
if uploaded_apu_source is None and not active_source_url:
    uploaded_apu_source = restore_upload("apu_sv_session_upload")

_has_apu_cache = isinstance(st.session_state.get("apu_room_cached_df"), pd.DataFrame)

if not active_source_url and uploaded_apu_source is None and not _has_apu_cache:
    st.info("Masukkan source URL / file path atau upload Excel/CSV APU Shop Visit pada sidebar.")
    st.stop()


try:
    _upload_sig = _uploaded_file_signature(uploaded_apu_source)
    _cached_source = st.session_state.get("apu_room_cached_source")
    _cached_upload_sig = st.session_state.get("apu_room_cached_upload_signature")
    _can_reuse_upload = (
        uploaded_apu_source is not None
        and not refresh
        and _cached_source == "__uploaded_apu__"
        and _cached_upload_sig == _upload_sig
        and _has_apu_cache
    )
    _can_reuse_url = (
        bool(active_source_url)
        and not refresh
        and _cached_source == active_source_url
        and _has_apu_cache
    )

    if _can_reuse_upload or _can_reuse_url or (uploaded_apu_source is None and not active_source_url and _has_apu_cache):
        data, source_label, schema_count, diagnostics = _apu_cached_payload()
    else:
        with st.spinner("Reading APU Shop Visit data..."):
            if uploaded_apu_source is not None:
                data, source_label, schema_count, diagnostics = load_apu_uploaded(uploaded_apu_source)
                st.session_state["apu_room_cached_source"] = "__uploaded_apu__"
                st.session_state["apu_room_cached_upload_signature"] = _upload_sig
            elif active_source_url:
                data, source_label, schema_count, diagnostics = load_apu_source(active_source_url)
                st.session_state["apu_room_cached_source"] = active_source_url
                st.session_state.pop("apu_room_cached_upload_signature", None)
            else:
                raise RuntimeError("No APU data source is available.")

            st.session_state["apu_room_cached_df"] = data.copy()
            st.session_state["apu_room_cached_source_label"] = source_label
            st.session_state["apu_room_cached_schema_count"] = schema_count
            st.session_state["apu_room_cached_diagnostics"] = diagnostics
except Exception as exc:
    st.error(f"APU Shop Visit data tidak dapat dibaca: {exc}")
    st.caption(
        "Format yang diharapkan: APU SN, Title, induction date, MRO, scope of work, "
        "release date, Progress, TAT, removal date, TSN, CSN, TSLV, APU Type, "
        "lessor, Item Type, Path, SV cost."
    )
    st.stop()


st.markdown(
    f'<div class="source-note"><b>Source:</b> {source_label} &nbsp;·&nbsp; '
    f'<b>Rows:</b> {len(data):,} &nbsp;·&nbsp; '
    f'<b>Schema match:</b> {schema_count}/17 fields</div>',
    unsafe_allow_html=True,
)
if data.empty:
    st.warning("Data source terbaca tetapi tidak ada APU SN yang berisi data.")
    st.stop()


# Monitoring filters — only fields that exist in the latest source
st.markdown('<div class="section-label">Monitoring filters</div>', unsafe_allow_html=True)
f1, f2, f3, f4, f5 = st.columns([1.05, 1, 1, 1, 1.15])
with f1:
    date_preset = st.selectbox(
        "Date Range",
        ["All History", "Year to Date", "Last 12 Months", "Last 24 Months", "Custom"],
        key="apu_exact_date_range",
    )
with f2:
    date_basis = st.selectbox(
        "Date basis",
        ["induction date", "removal date", "release date"],
        key="apu_exact_date_basis",
    )
with f3:
    # Synthetic operational filter: Off Wing = every populated progress
    # state except completed. Exact source progress values remain selectable.
    OFF_WING_PROGRESS = "Off Wing"
    source_progress_values = sorted(
        [
            str(x).strip()
            for x in data["Progress"].dropna().unique().tolist()
            if str(x).strip()
            and str(x).strip().casefold() != OFF_WING_PROGRESS.casefold()
        ],
        key=lambda value: value.casefold(),
    )
    progress_values = [OFF_WING_PROGRESS] + source_progress_values
    progress_filter = st.multiselect(
        "Progress",
        progress_values,
        key="apu_exact_progress",
        help="Off Wing = all progress states except Completed.",
    )
with f4:
    mro_values = sorted([x for x in data["MRO"].dropna().unique().tolist() if str(x).strip()])
    mro_filter = st.multiselect("MRO", mro_values, key="apu_exact_mro")
with f5:
    type_values = sorted([x for x in data["APU Type"].dropna().unique().tolist() if str(x).strip()])
    type_filter = st.multiselect("APU Type", type_values, key="apu_exact_type")


g1, g2, g3 = st.columns([1.1, 1.1, 1.8])
with g1:
    scope_values = sorted([x for x in data["scope of work"].dropna().unique().tolist() if str(x).strip()])
    scope_filter = st.multiselect("Scope of work", scope_values, key="apu_exact_scope")
with g2:
    lessor_values = sorted([x for x in data["lessor"].dropna().unique().tolist() if str(x).strip()])
    lessor_filter = st.multiselect("Lessor", lessor_values, key="apu_exact_lessor")
with g3:
    search_text = st.text_input(
        "Search APU SN / Title",
        placeholder="e.g. P-10262 or APU HI TIME",
        key="apu_exact_search",
    ).strip()


custom_range = None
if date_preset == "Custom":
    valid_dates = data[date_basis].dropna()
    if not valid_dates.empty:
        default_start = valid_dates.min().date()
        default_end = valid_dates.max().date()
    else:
        default_start = pd.Timestamp.today().date()
        default_end = pd.Timestamp.today().date()
    custom_range = st.date_input(
        "Custom monitoring date",
        value=(default_start, default_end),
        key="apu_exact_custom_date",
    )


filtered = _date_range(data.copy(), date_basis, date_preset, custom_range)


if progress_filter:
    selected_progress = set(progress_filter)
    progress_text = filtered["Progress"].astype("string").fillna("").str.strip()
    progress_mask = pd.Series(False, index=filtered.index)

    if OFF_WING_PROGRESS in selected_progress:
        normalized_progress = progress_text.str.casefold()
        progress_mask |= (
            normalized_progress.ne("")
            & ~normalized_progress.isin({"completed", "complete"})
        )

    exact_progress = selected_progress - {OFF_WING_PROGRESS}
    if exact_progress:
        progress_mask |= progress_text.isin(exact_progress)

    filtered = filtered[progress_mask]
if mro_filter:
    filtered = filtered[filtered["MRO"].isin(mro_filter)]
if type_filter:
    filtered = filtered[filtered["APU Type"].isin(type_filter)]
if scope_filter:
    filtered = filtered[filtered["scope of work"].isin(scope_filter)]
if lessor_filter:
    filtered = filtered[filtered["lessor"].isin(lessor_filter)]
if search_text:
    q = search_text.casefold()
    mask = (
        filtered["APU SN"].str.casefold().str.contains(q, na=False, regex=False)
        | filtered["Title"].str.casefold().str.contains(q, na=False, regex=False)
    )
    filtered = filtered[mask]


# KPIs are derived only from available spreadsheet fields.
progress_lower = filtered["Progress"].astype("string").fillna("").str.lower()
completed_mask = progress_lower.str.contains("complete", regex=False) | filtered["release date"].notna()
completed = int(completed_mask.sum())
active = int(len(filtered) - completed)
median_tat = filtered["TAT"].dropna().median()
total_cost = filtered["SV cost"].dropna().sum(min_count=1)


k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Shop Visits", f"{len(filtered):,}")
k2.metric("Active", f"{active:,}")
k3.metric("Completed", f"{completed:,}")
k4.metric("Median TAT", "—" if pd.isna(median_tat) else f"{median_tat:,.0f} d")
k5.metric("Total SV Cost", _fmt_number(total_cost))


tabs = st.tabs(["Monitoring", "APU Detail", "MRO Performance", "Source Data"])


with tabs[0]:
    if filtered.empty:
        st.info("Tidak ada data yang sesuai dengan filter.")
    else:
        phase = (
            filtered.assign(_Progress=filtered["Progress"].replace("", "Unspecified"))
            .groupby("_Progress", dropna=False)
            .size()
            .reset_index(name="Shop Visits")
            .sort_values("Shop Visits", ascending=True)
        )
        fig = px.bar(
            phase,
            x="Shop Visits",
            y="_Progress",
            orientation="h",
            title="Shop Visits by Progress",
            labels={"_Progress": "Progress"},
        )
        _plot(fig)


        c3, c4 = st.columns(2, gap="large")
        with c3:
            tat_data = filtered.dropna(subset=["TAT"]).copy()
            if tat_data.empty:
                st.info("TAT belum tersedia pada data yang terfilter.")
            else:
                mro_tat = (
                    tat_data.assign(_MRO=tat_data["MRO"].replace("", "Unspecified"))
                    .groupby("_MRO")["TAT"]
                    .median()
                    .reset_index(name="Median TAT")
                    .sort_values("Median TAT", ascending=False)
                )
                fig = px.bar(
                    mro_tat,
                    x="_MRO",
                    y="Median TAT",
                    title="Median TAT by MRO",
                    labels={"_MRO": "MRO"},
                )
                _plot(fig)


        with c4:
            cost_data = filtered.dropna(subset=["SV cost"]).copy()
            if cost_data.empty:
                st.info("SV cost belum diisi pada data yang terfilter.")
            else:
                mro_cost = (
                    cost_data.assign(_MRO=cost_data["MRO"].replace("", "Unspecified"))
                    .groupby("_MRO")["SV cost"]
                    .sum()
                    .reset_index(name="SV Cost")
                    .sort_values("SV Cost", ascending=False)
                )
                fig = px.bar(
                    mro_cost,
                    x="_MRO",
                    y="SV Cost",
                    title="SV Cost by MRO",
                    labels={"_MRO": "MRO"},
                )
                _plot(fig)


        # Active TAT Watchlist — mirrors the Engine Shop Visit monitoring chart.
        apu_watch = filtered.copy()
        apu_watch_progress = apu_watch["Progress"].astype("string").fillna("").str.strip()
        apu_watch_completed = (
            apu_watch_progress.str.casefold().str.contains("complete", regex=False)
            | apu_watch["release date"].notna()
        )
        apu_watch = apu_watch[~apu_watch_completed].copy()

        if not apu_watch.empty:
            today = pd.Timestamp.today().normalize()
            calculated_active_tat = (today - apu_watch["induction date"]).dt.days
            apu_watch["Watch TAT"] = calculated_active_tat.where(
                apu_watch["induction date"].notna(),
                apu_watch["TAT"],
            )
            apu_watch = apu_watch[
                apu_watch["Watch TAT"].notna()
                & apu_watch["Watch TAT"].ge(0)
                & apu_watch["Watch TAT"].le(5000)
            ].copy()

        if apu_watch.empty:
            st.info("Tidak ada active APU dengan TAT valid untuk watchlist.")
        else:
            completed_tat = filtered.loc[completed_mask, "TAT"].dropna()
            completed_tat = completed_tat[completed_tat.ge(0) & completed_tat.le(5000)]
            historical_p75 = completed_tat.quantile(0.75) if len(completed_tat) >= 4 else pd.NA

            watch_progress = apu_watch["Progress"].astype("string").fillna("").str.casefold()
            review_mask = watch_progress.str.contains("hold", regex=False) | watch_progress.str.contains("behind", regex=False)
            if pd.notna(historical_p75):
                review_mask |= apu_watch["Watch TAT"].gt(float(historical_p75))
            apu_watch["Flag"] = "Normal"
            apu_watch.loc[review_mask, "Flag"] = "Review"

            apu_watch = (
                apu_watch.sort_values("Watch TAT", ascending=False)
                .head(10)
                .sort_values("Watch TAT")
                .copy()
            )
            apu_watch["APU"] = apu_watch.apply(
                lambda row: (
                    f"{row['APU SN']} · {row['MRO']}"
                    if str(row["MRO"]).strip()
                    else str(row["APU SN"])
                ),
                axis=1,
            )

            fig = px.bar(
                apu_watch,
                x="Watch TAT",
                y="APU",
                orientation="h",
                text="Watch TAT",
                color="Flag",
                color_discrete_map={"Normal": "#2F69BF", "Review": "#8BBEF0"},
                category_orders={"Flag": ["Normal", "Review"]},
                custom_data=["APU SN", "MRO", "Progress", "APU Type", "scope of work"],
                title="Active TAT Watchlist",
            )
            fig.update_traces(
                texttemplate="%{text:.0f}d",
                textposition="outside",
                hovertemplate=(
                    "<b>APU %{customdata[0]}</b><br>"
                    "TAT: %{x:.0f} days<br>"
                    "MRO: %{customdata[1]}<br>"
                    "Progress: %{customdata[2]}<br>"
                    "APU Type: %{customdata[3]}<br>"
                    "Scope: %{customdata[4]}"
                    "<extra></extra>"
                ),
            )
            fig.update_yaxes(type="category", title="APU")
            fig.update_xaxes(title="TAT (days)")
            _plot(fig, height=390)


        st.markdown('<div class="section-label">APU Shop Visit Table</div>', unsafe_allow_html=True)
        primary_columns = [
            "APU SN", "Title", "APU Type", "MRO", "scope of work", "Progress",
            "TAT", "removal date", "induction date", "release date",
            "TSN", "CSN", "TSLV", "lessor", "SV cost",
        ]
        show = filtered[primary_columns].copy()
        st.dataframe(
            show,
            use_container_width=True,
            hide_index=True,
            height=430,
            column_config={
                "removal date": st.column_config.DateColumn("removal date", format="DD/MM/YYYY"),
                "induction date": st.column_config.DateColumn("induction date", format="DD/MM/YYYY"),
                "release date": st.column_config.DateColumn("release date", format="DD/MM/YYYY"),
                "TAT": st.column_config.NumberColumn("TAT", format="%.0f"),
                "TSN": st.column_config.NumberColumn("TSN", format="%.0f"),
                "CSN": st.column_config.NumberColumn("CSN", format="%.0f"),
                "TSLV": st.column_config.NumberColumn("TSLV", format="%.0f"),
                "SV cost": st.column_config.NumberColumn("SV cost", format="%.0f"),
            },
        )


        st.download_button(
            "Download filtered APU Shop Visit (Excel)",
            data=_excel_bytes(filtered),
            file_name="APU_Shop_Visit_Filtered.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=False,
            key="apu_exact_download",
        )


with tabs[1]:
    apu_options = sorted(filtered["APU SN"].dropna().astype(str).unique().tolist())
    if not apu_options:
        st.info("Tidak ada APU yang sesuai filter.")
    else:
        selected_apu = st.selectbox("APU SN", apu_options, key="apu_exact_selected_sn")
        history = filtered[filtered["APU SN"] == selected_apu].copy()
        sort_col = "induction date"
        history = history.sort_values(sort_col, ascending=False, na_position="last")
        row = history.iloc[0]


        st.subheader(f"APU {selected_apu}")
        st.caption(f"Title: {row['Title'] or '—'} · APU Type: {row['APU Type'] or '—'} · MRO: {row['MRO'] or '—'}")


        d1, d2, d3, d4 = st.columns(4)
        d1.metric("TAT", "—" if pd.isna(row["TAT"]) else f"{row['TAT']:,.0f} d")
        d2.metric("TSLV", _fmt_number(row["TSLV"]))
        d3.metric("TSN", _fmt_number(row["TSN"]))
        d4.metric("CSN", _fmt_number(row["CSN"]))


        left, right = st.columns(2, gap="large")
        with left:
            st.markdown("**Shop Visit**")
            detail_left = pd.DataFrame(
                [
                    ["Title", row["Title"] or "—"],
                    ["MRO", row["MRO"] or "—"],
                    ["scope of work", row["scope of work"] or "—"],
                    ["Progress", row["Progress"] or "—"],
                    ["SV cost", _fmt_number(row["SV cost"])],
                ],
                columns=["Field", "Value"],
            )
            st.dataframe(detail_left, use_container_width=True, hide_index=True)
        with right:
            st.markdown("**Dates & Asset**")
            detail_right = pd.DataFrame(
                [
                    ["removal date", "—" if pd.isna(row["removal date"]) else row["removal date"].strftime("%d/%m/%Y")],
                    ["induction date", "—" if pd.isna(row["induction date"]) else row["induction date"].strftime("%d/%m/%Y")],
                    ["release date", "—" if pd.isna(row["release date"]) else row["release date"].strftime("%d/%m/%Y")],
                    ["APU Type", row["APU Type"] or "—"],
                    ["lessor", row["lessor"] or "—"],
                ],
                columns=["Field", "Value"],
            )
            st.dataframe(detail_right, use_container_width=True, hide_index=True)


        with st.expander("Source metadata"):
            st.write("**Item Type:**", row["Item Type"] or "—")
            st.write("**Path:**", row["Path"] or "—")


        st.markdown("**Shop Visit History**")
        st.dataframe(
            history[SOURCE_COLUMNS],
            use_container_width=True,
            hide_index=True,
            height=330,
        )


with tabs[2]:
    if filtered.empty:
        st.info("Tidak ada data untuk MRO Performance.")
    else:
        work = filtered.copy()
        work["_MRO"] = work["MRO"].replace("", "Unspecified")
        rows = []
        for mro, group in work.groupby("_MRO"):
            tat = group["TAT"].dropna()
            cost = group["SV cost"].dropna()
            rows.append(
                {
                    "MRO": mro,
                    "Shop Visits": len(group),
                    "Completed": int(
                        (
                            group["Progress"].astype("string").fillna("").str.lower().str.contains("complete", regex=False)
                            | group["release date"].notna()
                        ).sum()
                    ),
                    "Median TAT": tat.median() if not tat.empty else pd.NA,
                    "P75 TAT": tat.quantile(0.75) if not tat.empty else pd.NA,
                    "Total SV Cost": cost.sum() if not cost.empty else pd.NA,
                    "Median SV Cost": cost.median() if not cost.empty else pd.NA,
                }
            )
        mro_summary = pd.DataFrame(rows).sort_values(["Shop Visits", "MRO"], ascending=[False, True])
        st.dataframe(mro_summary, use_container_width=True, hide_index=True)


        st.caption(
            "Perbandingan MRO mengikuti filter Scope of work di atas. "
            "TAT dan SV cost hanya dihitung dari nilai yang tersedia pada spreadsheet."
        )


with tabs[3]:
    st.markdown("**Exact source schema**")
    st.caption(
        "APU Room hanya menggunakan 17 kolom pada spreadsheet terbaru. "
        "Tidak ada Forecast Release, Last Update, Key Issue, Next Action, Owner, "
        "configuration, atau field Engine Shop Visit yang disisipkan ke APU."
    )
    st.dataframe(
        filtered[SOURCE_COLUMNS],
        use_container_width=True,
        hide_index=True,
        height=520,
    )
    with st.expander("Schema detection detail"):
        st.write("Detected fields:", [col for col in SOURCE_COLUMNS if col in data.columns])
        st.write("Source checks:", diagnostics)