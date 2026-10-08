from __future__ import annotations

from base64 import b64encode
from pathlib import Path
import sys

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

def _data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    suffix = path.suffix.lower().lstrip(".") or "png"
    mime = "jpeg" if suffix in {"jpg", "jpeg"} else suffix
    return f"data:image/{mime};base64," + b64encode(path.read_bytes()).decode("ascii")


st.set_page_config(
    page_title="Powerplant Engineering Control Center",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# LOGIN GATE
# -----------------------------------------------------------------------------
ACCESS_PASSWORD = "PowerplantGarudaIndonesia2026"
LOGIN_LOGO_PATH = ROOT_DIR / "garuda_logo_login_hd.png"

if "cc_authenticated" not in st.session_state:
    st.session_state["cc_authenticated"] = False

if not st.session_state["cc_authenticated"]:
    logo_uri = _data_uri(LOGIN_LOGO_PATH)

    login_markup = r"""
        <style>
        html, body, #root {
            margin:0 !important; padding:0 !important;
            width:100% !important; min-height:100% !important;
            overflow:hidden !important; background:#07265a !important;
        }
        html, body, [class*="css"] {
            font-family:"Segoe UI",Inter,Arial,sans-serif !important;
            -webkit-font-smoothing:antialiased !important;
            text-rendering:optimizeLegibility !important;
        }
        .stApp {
            width:100vw !important; min-height:100vh !important;
            margin:0 !important; padding:0 !important;
            border:0 !important; border-radius:0 !important;
            overflow:hidden !important; position:relative !important;
            background:
                radial-gradient(1050px 680px at 96% 4%, rgba(116,217,228,.28), transparent 68%),
                radial-gradient(880px 650px at 2% 104%, rgba(47,106,197,.27), transparent 73%),
                radial-gradient(1150px 720px at 92% 55%, transparent 0 58%, rgba(106,205,219,.12) 58.4% 65%, transparent 65.4%),
                radial-gradient(1050px 720px at 4% 103%, transparent 0 55%, rgba(45,105,196,.18) 55.4% 63%, transparent 63.4%),
                linear-gradient(116deg,#07265A 0%,#0B3A76 48%,#53ADBC 100%) !important;
        }
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main {
            width:100vw !important; min-height:100vh !important;
            margin:0 !important; padding:0 !important;
            background:transparent !important; overflow:hidden !important;
        }
        [data-testid="stHeader"], [data-testid="stSidebar"],
        [data-testid="collapsedControl"], [data-testid="stToolbar"],
        [data-testid="stDecoration"] { display:none !important; }
        #MainMenu, footer { visibility:hidden !important; }

        .block-container {
            position:absolute !important; left:50% !important; top:50% !important;
            transform:translate(-50%,-50%) !important;
            box-sizing:border-box !important;
            width:min(590px,calc(100vw - 42px)) !important; max-width:590px !important; min-height:500px !important;
            margin:0 !important; padding:38px 34px 36px 34px !important;
            background:#fff !important;
            border:1px solid rgba(218,226,236,.96) !important;
            border-radius:22px !important;
            box-shadow:0 26px 64px rgba(2,26,60,.27),0 8px 22px rgba(2,26,60,.12) !important;
            overflow:visible !important;
        }
        .cc-login-brand {
            display:flex !important; align-items:center !important; justify-content:center !important;
            width:100% !important; margin:0 auto 22px auto !important;
        }
        .cc-login-brand img {
            display:block !important; width:min(320px,68%) !important; max-width:320px !important;
            height:auto !important; object-fit:contain !important; image-rendering:auto !important;
        }
        .cc-login-title-row {
            display:grid !important; grid-template-columns:minmax(48px,1fr) auto minmax(48px,1fr) !important;
            align-items:center !important; gap:13px !important; width:100% !important;
            margin:0 0 28px 0 !important;
        }
        .cc-login-title-line { height:1.5px !important; border-radius:999px !important; background:#6E9ABB !important; opacity:.80 !important; }
        .cc-login-title {
            color:#123F71 !important; font-size:18.5px !important; line-height:1.16 !important;
            font-weight:800 !important; letter-spacing:-.016em !important;
            text-align:center !important; white-space:nowrap !important;
        }

        [data-testid="stForm"] { width:100% !important; margin:0 !important; padding:0 !important; border:0 !important; background:transparent !important; }
        [data-testid="stForm"] > div { gap:0 !important; }
        [data-testid="stTextInput"] { position:relative !important; width:100% !important; margin:0 0 16px 0 !important; padding:0 !important; }
        [data-testid="stTextInput"] > div { width:100% !important; margin:0 !important; padding:0 !important; }

        /* ---------------------------------------------------------
           INPUTS — style the real HTML input element directly.
           This intentionally avoids relying on BaseWeb wrapper borders,
           which vary between Streamlit releases.
           --------------------------------------------------------- */
        [data-testid="stTextInput"] div[data-baseweb="input"],
        [data-testid="stTextInput"] div[data-baseweb="base-input"] {
            position: relative !important;
            width: 100% !important;
            height: auto !important;
            min-height: 0 !important;
            border: 0 !important;
            border-radius: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
            overflow: visible !important;
        }

        [data-testid="stTextInput"] input {
            -webkit-appearance: none !important;
            appearance: none !important;
            box-sizing: border-box !important;
            display: block !important;
            width: 100% !important;
            height: 58px !important;
            min-height: 58px !important;
            margin: 0 !important;

            border: 0 !important;
            border-radius: 11px !important;
            outline: none !important;

            background-color: #FBFDFF !important;
            background-repeat: no-repeat !important;
            background-position: 19px center !important;
            background-size: 22px 22px !important;

            color: #2C405C !important;
            caret-color: #276B98 !important;
            font-family: "Segoe UI", Inter, Arial, sans-serif !important;
            font-size: 16px !important;
            line-height: normal !important;
            font-weight: 500 !important;
            letter-spacing: 0 !important;

            padding: 0 54px 0 56px !important;
            box-shadow:
                inset 0 0 0 1.35px #C6D6E6,
                0 1px 4px rgba(26,57,91,.035) !important;
            transition: border-color .17s ease, box-shadow .17s ease, background-color .17s ease !important;
        }

        [data-testid="stTextInput"] input:not([type="password"]) {
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='22' height='22' viewBox='0 0 24 24' fill='none' stroke='%23445F83' stroke-width='1.75' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M20 21a8 8 0 0 0-16 0'/%3E%3Ccircle cx='12' cy='7' r='4'/%3E%3C/svg%3E") !important;
        }

        [data-testid="stTextInput"] input[type="password"] {
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='22' height='22' viewBox='0 0 24 24' fill='none' stroke='%23445F83' stroke-width='1.75' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='4' y='10' width='16' height='11' rx='2'/%3E%3Cpath d='M8 10V7a4 4 0 0 1 8 0v3'/%3E%3C/svg%3E") !important;
        }

        [data-testid="stTextInput"] input:hover {
            background-color: #FFFFFF !important;
            box-shadow: inset 0 0 0 1.45px #AFC4D8, 0 1px 4px rgba(26,57,91,.04) !important;
        }

        [data-testid="stTextInput"] input:focus {
            border: 0 !important;
            outline: none !important;
            background-color: #FFFFFF !important;
            box-shadow: inset 0 0 0 1.55px #5C96BD, 0 0 0 3px rgba(68,149,186,.10) !important;
        }

        [data-testid="stTextInput"] input::placeholder {
            color: #687A94 !important;
            opacity: 1 !important;
            font-size: 16px !important;
            font-weight: 500 !important;
        }

        /* Password visibility control */
        [data-testid="stTextInput"] button {
            position: absolute !important;
            z-index: 6 !important;
            right: 10px !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 38px !important;
            min-width: 38px !important;
            height: 38px !important;
            min-height: 38px !important;
            margin: 0 !important;
            padding: 0 !important;
            border: 0 !important;
            border-radius: 50% !important;
            background: transparent !important;
            box-shadow: none !important;
            color: #244F7E !important;
        }
        [data-testid="stTextInput"] button:hover { background: rgba(41,92,137,.055) !important; }
        [data-testid="stTextInput"] button svg {
            width: 20px !important;
            height: 20px !important;
            color: #244F7E !important;
            stroke: #244F7E !important;
            fill: none !important;
        }

        [data-testid="stFormSubmitButton"] { width:100% !important; margin:14px 0 0 0 !important; padding:0 !important; }
        [data-testid="stFormSubmitButton"] > div { width:100% !important; }
        [data-testid="stFormSubmitButton"] button {
            display:flex !important; align-items:center !important; justify-content:center !important;
            box-sizing:border-box !important; width:100% !important; height:60px !important; min-height:60px !important;
            margin:0 !important; padding:0 24px !important; border:0 !important; border-radius:12px !important;
            background:linear-gradient(90deg,#318DA7 0%,#4FAABD 100%) !important; color:#fff !important;
            font-size:17px !important; line-height:1 !important; font-weight:800 !important; letter-spacing:.003em !important;
            box-shadow:0 8px 18px rgba(42,135,162,.17) !important;
            transition:transform .15s ease,box-shadow .15s ease,filter .15s ease !important;
        }
        [data-testid="stFormSubmitButton"] button:hover { filter:brightness(1.03) !important; transform:translateY(-1px) !important; box-shadow:0 10px 22px rgba(42,135,162,.22) !important; }
        [data-testid="stFormSubmitButton"] button:active { transform:translateY(0) !important; }
        [data-testid="stAlert"] { margin:16px 0 0 0 !important; border-radius:10px !important; font-size:14px !important; }

        @media (max-width:760px) {
            .block-container { width:min(570px,calc(100vw - 30px)) !important; padding:34px 28px 30px 28px !important; border-radius:20px !important; }
            .cc-login-brand { margin-bottom:20px !important; }
            .cc-login-brand img { width:min(300px,72%) !important; }
            .cc-login-title-row { gap:10px !important; margin-bottom:24px !important; }
            .cc-login-title { font-size:clamp(16px,3vw,18px) !important; white-space:normal !important; }
        }
        @media (max-width:520px) {
            html, body, #root, .stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main { overflow:auto !important; }
            .block-container { position:relative !important; left:auto !important; top:auto !important; transform:none !important; width:calc(100vw - 24px) !important; margin:24px auto !important; padding:28px 18px 24px 18px !important; border-radius:19px !important; }
            .cc-login-brand img { width:78% !important; }
            .cc-login-title-row { grid-template-columns:1fr !important; margin-bottom:26px !important; }
            .cc-login-title-line { display:none !important; }
                        [data-testid="stTextInput"] input { height:56px !important; min-height:56px !important; padding-left:54px !important; background-position:18px center !important; background-size:21px 21px !important; font-size:16px !important; }
            [data-testid="stTextInput"] input::placeholder { font-size:16px !important; }
                        [data-testid="stFormSubmitButton"] button { height:58px !important; min-height:58px !important; font-size:17px !important; }
        }
        </style>

        <div class="cc-login-brand">
            <img src="__LOGO_URI__" alt="Garuda Indonesia">
        </div>
        <div class="cc-login-title-row">
            <div class="cc-login-title-line"></div>
            <div class="cc-login-title">Powerplant Engineering Control Center</div>
            <div class="cc-login-title-line"></div>
        </div>
        """
    login_markup = login_markup.replace("__LOGO_URI__", logo_uri)
    st.markdown(login_markup, unsafe_allow_html=True)

    with st.form("control_center_login", clear_on_submit=False):
        username = st.text_input(
            "Username",
            placeholder="Enter your name",
            label_visibility="collapsed",
            autocomplete="name",
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Password",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        entered_name = str(username).strip()
        if not entered_name:
            st.error("Please enter your name.")
        elif password != ACCESS_PASSWORD:
            st.error("Incorrect password.")
        else:
            st.session_state["cc_authenticated"] = True
            st.session_state["cc_user"] = entered_name
            st.rerun()

    st.stop()

# -----------------------------------------------------------------------------
# AUTHENTICATED APPLICATION SHELL
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --cc-navy:#0B1F33;
        --cc-navy-2:#153B63;
        --cc-blue:#245B9E;
        --cc-teal:#448F92;
        --cc-bg:#F4F7FB;
        --cc-card:#FFFFFF;
        --cc-line:#E3E9F0;
        --cc-text:#122033;
        --cc-muted:#667085;
        --cc-green:#2D8A55;
        --cc-amber:#B7791F;
        --cc-red:#C64B48;
    }

    html, body, [class*="css"] {
        font-family:"Segoe UI", Inter, Arial, sans-serif;
        -webkit-font-smoothing:antialiased;
        text-rendering:optimizeLegibility;
    }
    .stApp { background:var(--cc-bg); color:var(--cc-text); }
    .block-container {
        max-width:1660px;
        padding-top:.75rem;
        padding-bottom:2.5rem;
        padding-left:1.35rem;
        padding-right:1.35rem;
    }
    #MainMenu { visibility:hidden; }
    footer { visibility:hidden; }
    [data-testid="stHeader"] { background:transparent; }

    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stSidebar"] button[aria-label="Collapse sidebar"] {
        background:#25466D !important;
        border:1px solid rgba(255,255,255,.18) !important;
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
        border:1px solid #D4DEE9 !important;
        border-radius:11px !important;
        box-shadow:0 2px 8px rgba(16,33,59,.10) !important;
    }
    [data-testid="collapsedControl"] svg,
    button[aria-label="Expand sidebar"] svg {
        color:#334155 !important;
        stroke:#334155 !important;
        fill:#334155 !important;
        opacity:1 !important;
    }

    div[data-testid="stHorizontalBlock"] .stButton > button {
        border-radius:11px;
        min-height:40px;
        font-size:12.5px;
        font-weight:750;
        border:1px solid #DCE4EE;
        background:#FFFFFF;
        color:#20324A;
        box-shadow:none;
    }
    div[data-testid="stHorizontalBlock"] .stButton > button:hover {
        border-color:#AFC4DD;
        color:#0B2A5B;
        background:#F8FBFF;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# MULTIPAGE ROUTER
# Use resolved absolute Paths so navigation is independent of the process CWD
# on Windows, local Streamlit, GitHub Codespaces, and Streamlit Community Cloud.
# -----------------------------------------------------------------------------
HOME_PAGE = ROOT_DIR / "home.py"
RELIABILITY_PAGE = ROOT_DIR / "reliability_page.py"
ENGINE_SV_PAGE = ROOT_DIR / "engine_shop_visit_page.py"
APU_SV_PAGE = ROOT_DIR / "apu_shop_visit_page.py"

_required_pages = {
    "Control Center": HOME_PAGE,
    "Reliability & Technical Delay": RELIABILITY_PAGE,
    "Engine Shop Visit": ENGINE_SV_PAGE,
    "APU Shop Visit": APU_SV_PAGE,
}
_missing_pages = {
    name: path for name, path in _required_pages.items() if not path.is_file()
}

if _missing_pages:
    st.error(
        "Dashboard deployment tidak lengkap. Beberapa file halaman tidak ditemukan "
        "di server, sehingga Streamlit tidak dapat membuat navigasi."
    )
    st.code(
        "\n".join(
            f"{name}: {path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path}"
            for name, path in _missing_pages.items()
        ),
        language="text",
    )
    st.info(
        "Untuk Streamlit Cloud/GitHub, upload atau commit SELURUH folder project—"
        "termasuk reliability_page.py, engine_shop_visit_page.py, dan "
        "apu_shop_visit_page.py—bukan hanya app.py."
    )
    st.stop()

pages = {
    "CONTROL CENTER": [
        st.Page(HOME_PAGE, title="Control Center", icon="🏠", default=True),
    ],
    "POWERPLANT ROOMS": [
        st.Page(
            RELIABILITY_PAGE,
            title="Reliability & Technical Delay",
            icon="📊",
            url_path="reliability",
        ),
        st.Page(
            ENGINE_SV_PAGE,
            title="Engine Shop Visit",
            icon="🛠️",
            url_path="shop-visit",
        ),
        st.Page(
            APU_SV_PAGE,
            title="APU Shop Visit",
            icon="⚙️",
            url_path="apu-shop-visit",
        ),
    ],
}

navigation = st.navigation(pages, position="hidden")
navigation.run()
