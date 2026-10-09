from __future__ import annotations

from datetime import datetime
from io import BytesIO
import hashlib
from pathlib import Path
import re
import sys

# Make the flat project root importable regardless of Streamlit working directory.
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from session_uploads import remember_upload, restore_upload, remember_uploads, restore_uploads, upload_memory_info, upload_memories_info

from rel_charts import (
    powerplant_contribution_line,
    powerplant_delay_rate_line,
    rolling_12m_delay_minutes_line,
    rolling_12m_contribution_line,
    rolling_12m_delay_rate_line,
    ata_deterioration_heatmap,
    concentration_bar,
    delay_minutes_line,
    fleet_bar,
    frequency_impact_scatter,
    key_problem_bar,
    repeat_defect_bar,
    severity_donut,
    top_ata_bar,
)
from rel_config import ALL_TECHNICAL_ATAS, DELAY_DIR, DEMO_DIR, EXPOSURE_DIR, SUPPORT_DIR, PARTS_DIR, POWERPLANT_ATAS, SEARCH_COLUMNS, SEVERE_THRESHOLD_MIN, UNSCHEDULED_REMOVAL_CODES
from rel_data_loader import combine_delay_sources, discover_delay_files, read_exposure_source, read_support_workbook
from rel_operational_events import (
    EVENT_METRICS,
    FLEET_ORDER,
    RATE_CONFIG,
    add_rolling_operational_rates,
    aggregate_operational_view,
    combine_dc_ata,
    combine_operational_monthly,
    common_target,
    infer_operational_fleet,
    parse_operational_reliability_workbook,
)
from rel_aircraft import apply_aircraft_grouping
from rel_part_removal import combine_part_sources, discover_part_files, filter_part_scope, link_parts_to_delay, part_summary, top_reason_for_part
from rel_filters import filter_analysis, filter_scope
from rel_metrics import (
    aircraft_watchlist,
    ata_deterioration_matrix,
    ata_summary,
    compute_kpis,
    data_quality_summary,
    delay_minutes_trend,
    powerplant_contribution_trend,
    reliability_calculation_summary,
    annual_reliability_from_inputs,
    rolling_12m_delay_minutes,
    rolling_12m_reliability_summary,
    engineering_focus,
    fleet_summary,
    key_problem_summary,
    significant_events,
    station_summary,
)

from rel_intelligence import (
    classification_health,
    concentration_summary,
    engine_position_summary,
    engineering_focus_v2,
    frequency_impact_data,
    needs_classification,
    operational_impact_by_ata,
    pareto_80_20,
    problem_taxonomy_summary,
    rectification_effectiveness,
    repetitive_defect_summary,
    subata_summary,
    tail_watchlist,
)

from rel_ui import (
    inject_css,
    render_active_period,
    render_analysis_context,
    render_focus,
    render_header,
    render_kpis,
    render_scope_bar,
    render_sidebar_brand,
    render_sidebar_status,
)


if "night_mode" not in st.session_state:
    st.session_state["night_mode"] = False

inject_css(bool(st.session_state["night_mode"]))

# Reliability tab styling is injected last by src.ui.inject_css().

render_sidebar_brand()


# -----------------------------------------------------------------------------
# ROOM NAVIGATION — locked visual using pure HTML anchors
# -----------------------------------------------------------------------------
st.sidebar.markdown(
    r"""
    <style>
    div[data-testid="stSidebar"] .room-nav-shell {
        width: 100%;
        box-sizing: border-box;
    }

    div[data-testid="stSidebar"] .room-nav-rule {
        height: 1px;
        background: rgba(145,164,189,.24);
        margin: 8px 0 24px 0;
    }

    div[data-testid="stSidebar"] .room-nav-title {
        color: #9BAFC8 !important;
        -webkit-text-fill-color: #9BAFC8 !important;
        font-size: 13px !important;
        line-height: 1 !important;
        font-weight: 800 !important;
        letter-spacing: .14em !important;
        margin: 0 0 20px 2px !important;
        padding: 0 !important;
    }

    div[data-testid="stSidebar"] a.room-nav-btn,
    div[data-testid="stSidebar"] a.room-nav-btn:link,
    div[data-testid="stSidebar"] a.room-nav-btn:visited {
        min-height: 62px;
        height: 62px;
        width: 100%;
        border-radius: 16px;
        border: 1px solid #35577D;
        background: #213C5D;
        color: #F5F8FC !important;
        -webkit-text-fill-color: #F5F8FC !important;
        display: flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
        padding: 0 16px;
        margin: 0 0 10px 0;
        text-decoration: none !important;
        font-size: 18px;
        line-height: 1.15;
        font-weight: 500;
        text-align: center;
        box-shadow: none;
        opacity: 1 !important;
    }

    div[data-testid="stSidebar"] a.room-nav-btn:hover {
        background: #294867;
        border-color: #5F91B6;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        text-decoration: none !important;
    }

    div[data-testid="stSidebar"] .room-active-card {
        min-height: 62px;
        height: 62px;
        width: 100%;
        border-radius: 16px;
        border: 1px solid #5D9BB5;
        background: linear-gradient(90deg, #4D9098 0%, #3D668E 100%);
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        display: flex;
        align-items: center;
        box-sizing: border-box;
        padding: 0 18px;
        margin: 0 0 10px 0;
        font-size: 18px;
        line-height: 1.15;
        font-weight: 800;
        text-align: left;
        opacity: 1 !important;
    }

    div[data-testid="stSidebar"] .room-active-card span {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        opacity: 1 !important;
    }

    div[data-testid="stSidebar"] .room-active-dot {
        width: 11px;
        height: 11px;
        border-radius: 50%;
        background: #A9F0EB;
        box-shadow: 0 0 0 5px rgba(169,240,235,.12);
        margin-right: 14px;
        flex: 0 0 auto;
    }

    div[data-testid="stSidebar"] .room-nav-bottom-rule {
        height: 1px;
        background: rgba(145,164,189,.24);
        margin: 22px 0 16px 0;
    }
    </style>

    <div class="room-nav-shell">
        <div class="room-nav-rule"></div>
        <div class="room-nav-title">ROOMS</div>

        <a class="room-nav-btn" href="/shop-visit" target="_self">Engine Shop Visit</a>
        <a class="room-nav-btn" href="/apu-shop-visit" target="_self">APU Shop Visit</a>

        <div class="room-active-card">
            <span class="room-active-dot"></span>
            <span>Reliability Room</span>
        </div>

        <a class="room-nav-btn" href="/" target="_self">Control Center</a>

        <div class="room-nav-bottom-rule"></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.toggle("Night mode", key="night_mode", help="Switch between light and dark display modes.")

PLOT_CONFIG = {
    # Keep the Plotly toolbar visible so every chart has a direct image-export option.
    "displayModeBar": True,
    "displaylogo": False,
    "responsive": True,
    # Reports normally need a sharper image than an on-screen screenshot.
    # The filename is replaced per-chart inside plot().
    "toImageButtonOptions": {
        "format": "png",
        "filename": "powerplant_chart",
        "width": 1800,
        "height": 900,
        "scale": 2,
    },
}


def local_source_tuples(paths: list[Path]) -> list[tuple[object, str, datetime | None]]:
    return [(p, p.name, datetime.fromtimestamp(p.stat().st_mtime)) for p in paths]


def uploaded_source_tuples(files) -> list[tuple[object, str, datetime | None]]:
    now = datetime.now()
    result = []
    for file in files or []:
        file.seek(0)
        result.append((file, file.name, now))
    return result


def load_exposure(local_files: list[Path], uploaded_files):
    """Load one or many Revenue T/O / utilization files without changing KPI formulas."""
    frames = []
    errors = []
    for path in local_files:
        try:
            frames.append(read_exposure_source(path, path.name))
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
    for uploaded_file in uploaded_files or []:
        try:
            uploaded_file.seek(0)
            frames.append(read_exposure_source(uploaded_file, uploaded_file.name))
        except Exception as exc:
            errors.append(f"{uploaded_file.name}: {exc}")
    if not frames:
        return pd.DataFrame(), errors
    combined = pd.concat(frames, ignore_index=True, sort=False)
    if "Departures" in combined.columns:
        combined = combined[pd.to_numeric(combined["Departures"], errors="coerce").notna()].copy()
    return combined.reset_index(drop=True), errors



def load_support(local_files: list[Path], uploaded_file=None):
    frames = []
    errors = []
    for path in local_files:
        try:
            frames.append(read_support_workbook(path, path.name))
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
    if uploaded_file is not None:
        try:
            uploaded_file.seek(0)
            frames.append(read_support_workbook(uploaded_file, uploaded_file.name))
        except Exception as exc:
            errors.append(f"{uploaded_file.name}: {exc}")
    if not frames:
        return pd.DataFrame(), errors
    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined = combined.drop_duplicates(subset=[c for c in ["Year", "A/C Type"] if c in combined.columns], keep="last")
    return combined.reset_index(drop=True), errors


def save_support_upload(uploaded_file) -> tuple[Path | None, str | None]:
    if uploaded_file is None:
        return None, None
    try:
        SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = Path(uploaded_file.name).name
        target = SUPPORT_DIR / safe_name
        stem, suffix = target.stem, target.suffix
        counter = 2
        while target.exists():
            target = SUPPORT_DIR / f"{stem}_{counter}{suffix}"
            counter += 1
        uploaded_file.seek(0)
        target.write_bytes(uploaded_file.read())
        return target, None
    except Exception as exc:
        return None, str(exc)

def save_uploads(uploaded_files) -> tuple[int, list[str]]:
    saved = 0
    errors = []
    DELAY_DIR.mkdir(parents=True, exist_ok=True)
    for file in uploaded_files or []:
        try:
            safe_name = Path(file.name).name
            target = DELAY_DIR / safe_name
            stem, suffix = target.stem, target.suffix
            counter = 2
            while target.exists():
                target = DELAY_DIR / f"{stem}_{counter}{suffix}"
                counter += 1
            file.seek(0)
            target.write_bytes(file.read())
            saved += 1
        except Exception as exc:
            errors.append(f"{file.name}: {exc}")
    return saved, errors


def save_exposure_uploads(uploaded_files) -> tuple[int, list[str]]:
    """Persist any number of utilization / Revenue T/O files."""
    saved = 0
    errors: list[str] = []
    EXPOSURE_DIR.mkdir(parents=True, exist_ok=True)
    for uploaded_file in uploaded_files or []:
        try:
            safe_name = Path(uploaded_file.name).name
            target = EXPOSURE_DIR / safe_name
            stem, suffix = target.stem, target.suffix
            counter = 2
            while target.exists():
                target = EXPOSURE_DIR / f"{stem}_{counter}{suffix}"
                counter += 1
            uploaded_file.seek(0)
            target.write_bytes(uploaded_file.read())
            saved += 1
        except Exception as exc:
            errors.append(f"{getattr(uploaded_file, 'name', 'exposure')}: {exc}")
    return saved, errors


def previous_period_dates(period_option: str, start_date, end_date):
    """Return a comparable previous period without fabricating a benchmark."""
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)

    if period_option == "All History":
        return None, None
    if period_option in {"YTD Latest Year", "Last 12 Months"}:
        return (start - pd.DateOffset(years=1)).date(), (end - pd.DateOffset(years=1)).date()
    if period_option == "Last 3 Years":
        return (start - pd.DateOffset(years=3)).date(), (end - pd.DateOffset(years=3)).date()

    # Custom: compare to the immediately preceding equal-length window.
    span = end - start
    prev_end = start - pd.Timedelta(days=1)
    prev_start = prev_end - span
    return prev_start.date(), prev_end.date()


def _apply_plotly_display_theme(fig):
    """Apply display-only professional chart styling; never changes data or calculations."""
    night = bool(st.session_state.get("night_mode", False))
    if night:
        bg = "#111C2C"
        text = "#E7EEF8"
        muted = "#A8B6C8"
        grid = "#26374A"
        line = "#38506A"
        title = "#F0F5FC"
        hover_bg = "#17263A"
    else:
        bg = "#FFFFFF"
        text = "#172B49"
        muted = "#65758A"
        grid = "#E7ECF2"
        line = "#CBD5E1"
        title = "#102C56"
        hover_bg = "#FFFFFF"

    fig.update_layout(
        paper_bgcolor=bg,
        plot_bgcolor=bg,
        font=dict(family="Segoe UI, Arial, sans-serif", size=12, color=text),
        hoverlabel=dict(bgcolor=hover_bg, bordercolor=line, font_color=text, font_size=12),
    )
    if fig.layout.title is not None:
        fig.layout.title.font = dict(family="Segoe UI, Arial, sans-serif", size=18, color=title)
    if fig.layout.legend is not None:
        fig.layout.legend.font = dict(family="Segoe UI, Arial, sans-serif", size=12, color=muted)

    fig.update_xaxes(
        gridcolor=grid, linecolor=line, zerolinecolor=line,
        tickfont=dict(family="Segoe UI, Arial, sans-serif", size=12, color=muted),
        title_font=dict(family="Segoe UI, Arial, sans-serif", size=13, color=muted),
    )
    fig.update_yaxes(
        gridcolor=grid, linecolor=line, zerolinecolor=line,
        tickfont=dict(family="Segoe UI, Arial, sans-serif", size=12, color=muted),
        title_font=dict(family="Segoe UI, Arial, sans-serif", size=13, color=muted),
    )

    for ann in fig.layout.annotations or []:
        if ann.font is None:
            ann.font = dict(family="Segoe UI, Arial, sans-serif", size=12, color=text)
        else:
            ann.font.family = "Segoe UI, Arial, sans-serif"
            if ann.font.size is None or ann.font.size < 12:
                ann.font.size = 12
            ann.font.color = text

    if night:
        for trace in fig.data:
            try:
                marker = trace.marker
                if marker is not None and str(marker.color).lower() in {"white", "#ffffff", "rgb(255, 255, 255)"}:
                    marker.color = bg
            except Exception:
                pass
    return fig


def plot(fig, key: str):
    """Render a chart with a report-ready PNG download option in its Plotly toolbar."""
    fig = _apply_plotly_display_theme(fig)
    chart_config = dict(PLOT_CONFIG)
    chart_config["toImageButtonOptions"] = dict(PLOT_CONFIG["toImageButtonOptions"])
    chart_config["toImageButtonOptions"]["filename"] = f"powerplant_{key}"
    st.plotly_chart(fig, use_container_width=True, config=chart_config, key=key)


def _source_bytes(source) -> bytes:
    """Return source bytes without consuming Streamlit upload objects."""
    if isinstance(source, Path):
        return source.read_bytes()
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    if hasattr(source, "getvalue"):
        return bytes(source.getvalue())
    try:
        source.seek(0)
    except Exception:
        pass
    data = source.read()
    try:
        source.seek(0)
    except Exception:
        pass
    return bytes(data)


def _source_signature(sources) -> tuple:
    """Cheap, content-safe signature for local and uploaded sources.

    The signature lets the Reliability Room reuse already parsed DataFrames while
    the same Streamlit browser session is alive. Uploaded bytes are still
    session-only: a browser refresh drops both the bytes and these processed
    DataFrames, matching the requested lifecycle.
    """
    items = []
    for source, name, modified_at in sources or []:
        if isinstance(source, Path):
            try:
                stat = source.stat()
                items.append(("path", str(source.resolve()), int(stat.st_size), int(stat.st_mtime_ns)))
            except Exception:
                items.append(("path", str(source), str(modified_at or "")))
        else:
            data = _source_bytes(source)
            digest = hashlib.sha1(data).hexdigest()
            items.append(("upload", str(name), len(data), digest))
    return tuple(items)


def _clear_reliability_processed_cache() -> None:
    for key in [
        "rel_delay_signature", "rel_delay_df", "rel_delay_meta",
        "rel_part_signature", "rel_part_df", "rel_part_meta",
        "rel_exposure_signature", "rel_exposure_df", "rel_exposure_errors",
        "rel_support_signature", "rel_support_df", "rel_support_errors",
        "rel_operational_signature", "rel_operational_bundle",
    ]:
        st.session_state.pop(key, None)


def _cached_delay_dataset(sources):
    signature = _source_signature(sources)
    if (
        signature
        and st.session_state.get("rel_delay_signature") == signature
        and isinstance(st.session_state.get("rel_delay_df"), pd.DataFrame)
    ):
        return st.session_state["rel_delay_df"], dict(st.session_state.get("rel_delay_meta", {})), True

    frame, meta = combine_delay_sources(sources)
    if not frame.empty:
        frame = apply_aircraft_grouping(frame)
    st.session_state["rel_delay_signature"] = signature
    st.session_state["rel_delay_df"] = frame
    st.session_state["rel_delay_meta"] = dict(meta)
    return frame, meta, False


def _cached_part_dataset(sources):
    signature = _source_signature(sources)
    if (
        st.session_state.get("rel_part_signature") == signature
        and isinstance(st.session_state.get("rel_part_df"), pd.DataFrame)
    ):
        return st.session_state["rel_part_df"], dict(st.session_state.get("rel_part_meta", {})), True

    if sources:
        frame, meta = combine_part_sources(sources)
        if not frame.empty:
            frame = apply_aircraft_grouping(frame)
    else:
        frame = pd.DataFrame()
        meta = {"errors": [], "sources": [], "duplicates_removed": 0}
    st.session_state["rel_part_signature"] = signature
    st.session_state["rel_part_df"] = frame
    st.session_state["rel_part_meta"] = dict(meta)
    return frame, meta, False


def _cached_exposure_dataset(local_files, uploaded_files):
    source_list = local_source_tuples(local_files) + uploaded_source_tuples(uploaded_files)
    signature = _source_signature(source_list)
    if (
        st.session_state.get("rel_exposure_signature") == signature
        and isinstance(st.session_state.get("rel_exposure_df"), pd.DataFrame)
    ):
        return st.session_state["rel_exposure_df"], list(st.session_state.get("rel_exposure_errors", [])), signature, True

    frame, errors = load_exposure(local_files, uploaded_files)
    st.session_state["rel_exposure_signature"] = signature
    st.session_state["rel_exposure_df"] = frame
    st.session_state["rel_exposure_errors"] = list(errors)
    return frame, errors, signature, False


def _cached_support_dataset(local_files, uploaded_file=None):
    sources = local_source_tuples(local_files)
    if uploaded_file is not None:
        sources += uploaded_source_tuples([uploaded_file])
    signature = _source_signature(sources)
    if (
        st.session_state.get("rel_support_signature") == signature
        and isinstance(st.session_state.get("rel_support_df"), pd.DataFrame)
    ):
        return st.session_state["rel_support_df"], list(st.session_state.get("rel_support_errors", [])), True
    frame, errors = load_support(local_files, uploaded_file)
    st.session_state["rel_support_signature"] = signature
    st.session_state["rel_support_df"] = frame
    st.session_state["rel_support_errors"] = list(errors)
    return frame, errors, False


@st.cache_data(show_spinner=False)
def _parse_operational_workbook_cached(data: bytes, source_name: str, fleet: str):
    return parse_operational_reliability_workbook(data, source_name, fleet)


def _period_window(data: pd.DataFrame, option: str):
    if data is None or data.empty:
        return None, None
    end = pd.Timestamp(data["Date"].max())
    start = pd.Timestamp(data["Date"].min())
    if option == "Last 12 Months":
        start = max(start, end - pd.DateOffset(months=11))
    elif option == "Last 24 Months":
        start = max(start, end - pd.DateOffset(months=23))
    elif option == "Last 36 Months":
        start = max(start, end - pd.DateOffset(months=35))
    return start, end


def _operational_heatmap_figure(view: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp):
    """Show exactly when each operational event occurred in a user-selected monthly range."""
    scoped = view[view["Date"].between(start, end)].copy().sort_values("Date")
    if scoped.empty:
        return go.Figure()

    dates = pd.to_datetime(scoped["Date"])
    labels = dates.dt.strftime("%b %Y").tolist()
    z = []
    text_matrix = []
    max_count = 0
    for metric in EVENT_METRICS:
        values = pd.to_numeric(scoped[metric], errors="coerce").tolist()
        clean_values = [None if pd.isna(v) else float(v) for v in values]
        z.append(clean_values)
        for v in clean_values:
            if v is not None:
                max_count = max(max_count, int(v))
        text_matrix.append([
            "—" if pd.notna(v) and float(v) == 0 else ("" if pd.isna(v) else str(int(v)))
            for v in values
        ])

    if max_count <= 10:
        color_ticks = list(range(0, max_count + 1))
    else:
        step = max(1, int((max_count + 4) // 5))
        color_ticks = list(range(0, max_count + 1, step))
        if color_ticks[-1] != max_count:
            color_ticks.append(max_count)

    month_count = len(labels)
    tick_step = 1 if month_count <= 18 else 2 if month_count <= 30 else 3 if month_count <= 48 else 6
    tick_indices = list(range(0, month_count, tick_step))
    if tick_indices[-1] != month_count - 1:
        tick_indices.append(month_count - 1)
    tickvals = [labels[i] for i in tick_indices]
    ticktext = [pd.Timestamp(dates.iloc[i]).strftime("%b\n%Y") for i in tick_indices]

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=labels,
            y=EVENT_METRICS,
            text=text_matrix,
            texttemplate="%{text}",
            hovertemplate="%{y}<br>%{x}<br>Events: %{z:.0f}<extra></extra>",
            colorscale=[[0.0, "#F4F7FB"], [0.15, "#CDE7F6"], [0.45, "#5CAED6"], [1.0, "#0B4F83"]],
            colorbar=dict(title="Events", thickness=12, tickmode="array", tickvals=color_ticks),
            zmin=0,
            zmax=max(max_count, 1),
            xgap=2,
            ygap=2,
        )
    )
    fig.update_layout(
        title=f"Event occurrence · {pd.Timestamp(start).strftime('%b %Y')} – {pd.Timestamp(end).strftime('%b %Y')}",
        margin=dict(l=55, r=25, t=55, b=55),
        height=365,
    )
    fig.update_xaxes(
        title=None,
        side="bottom",
        tickmode="array",
        tickvals=tickvals,
        ticktext=ticktext,
    )
    fig.update_yaxes(title=None, autorange="reversed")
    return fig

def _operational_event_trend_figure(monthly: pd.DataFrame, fleet_choice: str, metric: str, start: pd.Timestamp, end: pd.Timestamp):
    """Monthly event occurrence chart with integer-only event-count axis."""
    scoped = monthly[monthly["Date"].between(start, end)].copy()
    if fleet_choice != "All Fleet":
        scoped = scoped[scoped["Fleet"] == fleet_choice]
    if scoped.empty:
        return go.Figure()

    if fleet_choice == "All Fleet":
        fig = px.bar(
            scoped, x="Date", y=metric, color="Fleet", barmode="stack",
            category_orders={"Fleet": FLEET_ORDER},
            labels={metric: "Events", "Date": "Month"},
            title=f"{metric} occurrence by month",
        )
        monthly_total = scoped.groupby("Date", as_index=False)[metric].sum(min_count=1)
    else:
        fig = px.bar(
            scoped, x="Date", y=metric,
            labels={metric: "Events", "Date": "Month"},
            title=f"{metric} occurrence by month · {fleet_choice}",
        )
        monthly_total = scoped[["Date", metric]].copy()

    monthly_total[metric] = pd.to_numeric(monthly_total[metric], errors="coerce")
    for _, row in monthly_total.dropna(subset=[metric]).iterrows():
        value = int(row[metric])
        if value > 0:
            fig.add_annotation(
                x=row["Date"], y=value, text=str(value), showarrow=False,
                yshift=10, font=dict(size=12),
            )

    max_value = int(monthly_total[metric].max()) if monthly_total[metric].notna().any() else 0
    fig.update_layout(height=365, margin=dict(l=35, r=20, t=55, b=40), legend_title_text="Fleet")
    fig.update_xaxes(dtick="M1", tickformat="%b", title=None)
    fig.update_yaxes(
        title="Event count", tick0=0, dtick=1, tickformat="d", rangemode="tozero",
        range=[0, max(max_value + 1, 1)],
    )
    return fig


def _operational_fleet_contribution_figure(monthly: pd.DataFrame, metric: str, start: pd.Timestamp, end: pd.Timestamp):
    scoped = monthly[monthly["Date"].between(start, end)].copy()
    if scoped.empty:
        return go.Figure()
    grouped = (
        scoped.groupby("Fleet", as_index=False)[metric]
        .sum(min_count=1)
        .dropna(subset=[metric])
    )
    grouped[metric] = pd.to_numeric(grouped[metric], errors="coerce")
    grouped = grouped.sort_values(metric, ascending=True)
    fig = px.bar(
        grouped, y="Fleet", x=metric, orientation="h", text=metric,
        category_orders={"Fleet": FLEET_ORDER},
        labels={metric: "Events", "Fleet": ""},
        title=f"Which fleet contributed to {metric}?",
    )
    fig.update_traces(texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
    max_value = int(grouped[metric].max()) if not grouped.empty else 0
    fig.update_layout(height=300, margin=dict(l=35, r=35, t=55, b=35), showlegend=False)
    fig.update_xaxes(title="Event count", tick0=0, dtick=1, tickformat="d", range=[0, max(max_value + 1, 1)])
    fig.update_yaxes(title=None)
    return fig


def _event_occurrence_text(view: pd.DataFrame, metric: str, start: pd.Timestamp, end: pd.Timestamp) -> tuple[str, int, int, str, str]:
    scoped = view[view["Date"].between(start, end)].copy().sort_values("Date")
    values = pd.to_numeric(scoped[metric], errors="coerce")
    occurred = scoped[values.fillna(0).gt(0)].copy()
    if occurred.empty:
        return "No occurrence in the selected year.", 0, 0, "—", "—"
    occurred["_count"] = pd.to_numeric(occurred[metric], errors="coerce").fillna(0).astype(int)
    parts = [f"{pd.Timestamp(r['Date']).strftime('%b %Y')} ({int(r['_count'])})" for _, r in occurred.iterrows()]
    total = int(occurred["_count"].sum())
    event_months = int(len(occurred))
    latest_row = occurred.iloc[-1]
    latest_text = pd.Timestamp(latest_row["Date"]).strftime("%b %Y")
    peak_value = int(occurred["_count"].max())
    peak_months = occurred.loc[occurred["_count"].eq(peak_value), "Date"].dt.strftime("%b").tolist()
    peak_text = " / ".join(peak_months) + f" · {peak_value}"
    return ", ".join(parts), total, event_months, latest_text, peak_text

def _operational_rate_figure(rate_view: pd.DataFrame, metric: str, target: float | None):
    cfg = RATE_CONFIG[metric]
    rate_col = f"{metric} 12M Rate"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rate_view["Date"], y=rate_view[rate_col], mode="lines+markers", name="12M rolling rate",
        line=dict(width=2.5), marker=dict(size=5),
        hovertemplate="%{x|%b %Y}<br>Rate: %{y:.4f}<extra></extra>",
    ))
    if target is not None:
        fig.add_hline(y=float(target), line_dash="dash", annotation_text=f"Target {target:g}", annotation_position="top right")
    fig.update_layout(
        title=f"{metric} 12-Month Rolling Rate",
        height=360,
        margin=dict(l=45, r=20, t=55, b=40),
        yaxis_title=cfg["unit"],
        xaxis_title=None,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(dtick="M6", tickformat="%b\n%Y")
    return fig


def _dc_ata_figure(dc_ata: pd.DataFrame, fleet_choice: str, start: pd.Timestamp, end: pd.Timestamp):
    scoped = dc_ata[dc_ata["Date"].between(start, end)].copy()
    if fleet_choice != "All Fleet":
        scoped = scoped[scoped["Fleet"] == fleet_choice]
    if scoped.empty:
        return go.Figure()
    grouped = scoped.groupby(["ATA", "Fleet"], as_index=False)["D&C ATA Events"].sum()
    grouped["ATA Label"] = "ATA " + grouped["ATA"].astype(int).astype(str)
    if fleet_choice == "All Fleet":
        fig = px.bar(
            grouped, y="ATA Label", x="D&C ATA Events", color="Fleet", orientation="h", barmode="stack",
            category_orders={"Fleet": FLEET_ORDER},
            labels={"D&C ATA Events": "D&C Events", "ATA Label": ""},
            title="D&C by ATA Chapter",
        )
    else:
        total = grouped.groupby(["ATA", "ATA Label"], as_index=False)["D&C ATA Events"].sum().sort_values("D&C ATA Events", ascending=True)
        fig = px.bar(
            total, y="ATA Label", x="D&C ATA Events", orientation="h",
            labels={"D&C ATA Events": "D&C Events", "ATA Label": ""},
            title=f"D&C by ATA Chapter · {fleet_choice}",
        )
    max_value = pd.to_numeric(grouped["D&C ATA Events"], errors="coerce").sum() if not grouped.empty else 0
    fig.update_layout(height=390, margin=dict(l=45, r=35, t=55, b=35), legend_title_text="Fleet")
    fig.update_xaxes(title="D&C event count", tick0=0, dtick=1, tickformat="d", rangemode="tozero")
    return fig


def _safe_file_token(value: object, fallback: str = "component") -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip()).strip("_.")
    return token[:80] or fallback


def build_part_detail_excel(
    detail_df: pd.DataFrame,
    selected_part: str,
    ata: int | None,
    start_date=None,
    end_date=None,
) -> bytes:
    """Build a review-ready Excel package for one removed/replaced component."""
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    detail = detail_df.copy()
    if "Date Removal" in detail.columns:
        detail["Date Removal"] = pd.to_datetime(detail["Date Removal"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "_Source_Modified" in detail.columns:
        detail["_Source_Modified"] = pd.to_datetime(detail["_Source_Modified"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")

    preferred_columns = [
        "No", "Notification", "Date Removal", "ATA", "A/C Type", "Register", "Equipment",
        "Part Name", "Part Display", "Part Number", "Serial Number", "RemCode", "Real Reason", "NFF",
        "TSN", "TSI", "TSC", "CSN", "CSI", "CSC", "Shop_Visit", "Shop_Finding",
        "Link Status", "Delay KeyProblem", "Delay Problem Group", "Delay Problem", "Delay Minutes", "Delay Event Type",
        "_Source_File", "_Source_Modified", "Part Event ID",
    ]
    export_columns = [c for c in preferred_columns if c in detail.columns]
    export_columns += [c for c in detail.columns if c not in export_columns and not str(c).startswith("Notification Key")]
    detail = detail[export_columns].copy()

    reason_series = detail.get("Real Reason", pd.Series(dtype="string")).astype("string").fillna("").str.strip()
    reason_series = reason_series.replace("", "UNSPECIFIED / BLANK")
    reason_summary = (
        reason_series.value_counts(dropna=False)
        .rename_axis("Real Reason")
        .reset_index(name="Occurrences")
    )
    total = int(len(detail))
    reason_summary["Share %"] = (reason_summary["Occurrences"] / total * 100).round(1) if total else 0.0

    top_reason = "—"
    if not reason_summary.empty:
        top_reason = str(reason_summary.iloc[0]["Real Reason"])
    aircraft_count = int(detail.get("Register", pd.Series(dtype="string")).replace("", pd.NA).nunique(dropna=True))
    pn_count = int(detail.get("Part Number", pd.Series(dtype="string")).replace("", pd.NA).nunique(dropna=True))

    start_text = pd.Timestamp(start_date).strftime("%Y-%m-%d") if start_date is not None else "All history"
    end_text = pd.Timestamp(end_date).strftime("%Y-%m-%d") if end_date is not None else "All history"
    summary_rows = [
        ["Component", selected_part],
        ["ATA", f"ATA {ata}" if ata is not None else "All Powerplant"],
        ["Unscheduled removals", total],
        ["Aircraft affected", aircraft_count],
        ["Unique part numbers", pn_count],
        ["Top real reason", top_reason],
        ["Active period", f"{start_text} to {end_text}"],
        ["Unscheduled RemCode rule", ", ".join(sorted(str(x) for x in UNSCHEDULED_REMOVAL_CODES))],
        ["Generated at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    ]
    summary_df = pd.DataFrame(summary_rows, columns=["Field", "Value"])

    link_summary = pd.DataFrame()
    if "Link Status" in detail.columns:
        link_summary = (
            detail["Link Status"].astype("string").fillna("UNSPECIFIED").replace("", "UNSPECIFIED")
            .value_counts()
            .rename_axis("Link Status")
            .reset_index(name="Occurrences")
        )

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
        detail.to_excel(writer, index=False, sheet_name="Removal Details")
        reason_summary.to_excel(writer, index=False, sheet_name="Reason Summary")
        if not link_summary.empty:
            link_summary.to_excel(writer, index=False, sheet_name="Delay Link Summary")

        wb = writer.book
        navy = "17365D"
        blue = "2D5EA7"
        light_blue = "EAF1FA"
        pale = "F7F9FC"
        white = "FFFFFF"
        muted = "62748A"
        thin = Side(style="thin", color="DDE5EE")

        for ws in wb.worksheets:
            ws.freeze_panes = "A2"
            ws.sheet_view.showGridLines = False
            ws.auto_filter.ref = ws.dimensions
            for cell in ws[1]:
                cell.fill = PatternFill("solid", fgColor=navy)
                cell.font = Font(color=white, bold=True)
                cell.alignment = Alignment(vertical="center")
            ws.row_dimensions[1].height = 24

            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.border = Border(bottom=thin)
                    cell.alignment = Alignment(vertical="top", wrap_text=True)

            for col_cells in ws.columns:
                letter = col_cells[0].column_letter
                max_len = 0
                for cell in col_cells[:250]:
                    value = "" if cell.value is None else str(cell.value)
                    max_len = max(max_len, len(value))
                ws.column_dimensions[letter].width = min(max(max_len + 2, 11), 42)

        ws = wb["Summary"]
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 52
        for row in range(2, ws.max_row + 1):
            ws.cell(row, 1).font = Font(bold=True, color=navy)
            if row % 2 == 0:
                for col in range(1, 3):
                    ws.cell(row, col).fill = PatternFill("solid", fgColor=pale)

        reason_ws = wb["Reason Summary"]
        if reason_ws.max_row >= 2:
            for row in range(2, reason_ws.max_row + 1):
                if row == 2:
                    for col in range(1, reason_ws.max_column + 1):
                        reason_ws.cell(row, col).fill = PatternFill("solid", fgColor=light_blue)
                        reason_ws.cell(row, col).font = Font(bold=True, color=blue)

    return buffer.getvalue()


def apply_system_group(df: pd.DataFrame, choice: str) -> pd.DataFrame:
    if df.empty or choice == "All Powerplant":
        return df
    if choice.startswith("APU"):
        return df[df["ATA"] == 49].copy()
    if choice.startswith("Propulsion"):
        return df[df["ATA"].between(71, 80, inclusive="both")].copy()
    return df


def filter_support_metrics(df: pd.DataFrame, aircraft_type: str | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if not aircraft_type or aircraft_type == "All Aircraft":
        explicit = out[out["A/C Type"].astype(str).str.casefold().isin({"all aircraft", "all fleet", "all fleets"})]
        return explicit if not explicit.empty else out
    import re as _re
    norm = lambda x: _re.sub(r"[^a-z0-9]+", "", str(x or "").casefold())
    wanted = norm(aircraft_type)
    labels = out["A/C Type"].map(norm)
    exact = out[labels == wanted]
    if not exact.empty:
        return exact
    fuzzy = out[labels.map(lambda x: bool(x) and (x in wanted or wanted in x))]
    return fuzzy



def _normalise_aircraft_token(value: str) -> str:
    import re
    text = str(value or "").casefold()
    text = re.sub(r"\.(xlsx?|csv)$", "", text)
    text = text.replace("boeing", "b").replace("airbus", "a")
    return re.sub(r"[^a-z0-9]+", "", text)


def _aircraft_aliases(label: str) -> set[str]:
    """Conservative filename aliases for direct aircraft-name matching."""
    import re
    n = _normalise_aircraft_token(label)
    aliases = {n} if n else set()
    m = re.search(r"b?(717|727|737|747|757|767|777|787)(\d{1,4})?", n)
    if m:
        family, variant = m.group(1), m.group(2) or ""
        aliases.update({f"b{family}", family})
        if variant:
            aliases.update({f"b{family}{variant}", f"{family}{variant}"})
    m = re.search(r"a?(220|300|310|318|319|320|321|330|340|350|380)(\d{1,4})?", n)
    if m:
        family, variant = m.group(1), m.group(2) or ""
        aliases.update({f"a{family}", family})
        if variant:
            aliases.update({f"a{family}{variant}", f"{family}{variant}"})
    m = re.search(r"atr(42|72)(\d{2,3})?", n)
    if m:
        family, variant = m.group(1), m.group(2) or ""
        aliases.add(f"atr{family}")
        if variant:
            aliases.add(f"atr{family}{variant}")
    return {a for a in aliases if len(a) >= 3}


def _loaded_family_members(loaded_fleets: list[str], family: str) -> list[str]:
    """Return delay-data A/C Type labels belonging to the requested family."""
    import re
    family_norm = _normalise_aircraft_token(family)
    family_digits = re.sub(r"[^0-9]", "", family_norm)
    members = []
    for fleet in loaded_fleets:
        token = _normalise_aircraft_token(fleet)
        if family_norm and (family_norm in token or token == family_norm):
            members.append(fleet)
        elif family_digits and family_digits in token:
            members.append(fleet)
    return sorted(dict.fromkeys(members))


def _detect_engine_utilization_group(source_name: str) -> tuple[str | None, str | None]:
    """Known engine-group filename conventions supplied for this dashboard."""
    import re
    stem = Path(source_name).stem.casefold()
    spaced = re.sub(r"[^a-z0-9]+", " ", stem)
    compact = re.sub(r"[^a-z0-9]+", "", stem)

    has_ge90 = bool(re.search(r"\bge\s*90\b", spaced)) or "ge90" in compact
    has_cfm7b = bool(re.search(r"\bcfm\s*56\s*7b\b", spaced)) or "cfm567b" in compact
    has_leap1b = bool(re.search(r"\bleap\s*1b\b", spaced)) or "leap1b" in compact
    has_trent = "trent" in spaced
    has_other_trent = bool(re.search(r"\btrent\s*(?:500|800|900|1000|xwb)\b", spaced))

    if has_cfm7b and has_leap1b:
        return "CFM56-7B & LEAP-1B", "B737"
    if has_ge90:
        return "GE90", "B777"
    # Project convention: generic TRENT filename represents combined Trent 700 + 7000.
    if has_trent and not has_other_trent:
        return "Trent 700 & Trent 7000", "A330"
    if has_cfm7b:
        return "CFM56-7B", "B737"
    if has_leap1b:
        return "LEAP-1B", "B737"
    return None, None


def infer_aircraft_type_from_filename(source_name: str, loaded_fleets: list[str]) -> tuple[str | None, str]:
    """Fallback for utilization files named by aircraft instead of engine group."""
    filename_token = _normalise_aircraft_token(Path(source_name).stem)
    if not filename_token:
        return None, "filename is empty"
    scored: list[tuple[int, str]] = []
    for fleet in loaded_fleets:
        aliases = _aircraft_aliases(fleet)
        hits = [a for a in aliases if a and a in filename_token]
        if hits:
            longest = max(hits, key=len)
            score = 1000 + len(longest) if longest == _normalise_aircraft_token(fleet) else len(longest)
            scored.append((score, fleet))
    if not scored:
        return None, "no aircraft/engine mapping found in filename"
    scored.sort(reverse=True)
    best_score = scored[0][0]
    best = sorted({fleet for score, fleet in scored if score == best_score})
    if len(best) != 1:
        return None, "ambiguous aircraft filename match: " + ", ".join(best)
    return best[0], "aircraft type from filename"


def map_utilization_files_to_fleets(exposure_df: pd.DataFrame, loaded_fleets: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Map utilization workbooks to aircraft scope using filename only.

    This changes only source identification. All Contribution and Delay Rate
    formulas remain the same as the v1.26 calculation engine.
    """
    if exposure_df is None or exposure_df.empty or "_Exposure_Format" not in exposure_df.columns:
        return exposure_df, []

    out = exposure_df.copy()
    if "A/C Type" not in out.columns:
        out["A/C Type"] = ""
    if "Utilization Group" not in out.columns:
        out["Utilization Group"] = ""

    util_mask = out["_Exposure_Format"].astype("string").eq("Utilization cycles B:N")
    warnings: list[str] = []
    excluded: list[str] = []

    for source_name in out.loc[util_mask, "_Source_File"].astype("string").dropna().unique().tolist():
        source_mask = util_mask & out["_Source_File"].astype("string").eq(source_name)
        group_label, family = _detect_engine_utilization_group(source_name)
        if group_label and family:
            members = _loaded_family_members(loaded_fleets, family)
            if not members:
                excluded.append(source_name)
                warnings.append(
                    f"Utilization '{source_name}' dikenali sebagai {group_label} → {family}, "
                    "tetapi family tersebut tidak ditemukan pada delay data aktif."
                )
                continue
            # Keep family-level exposure as supplied by the utilization source.
            out.loc[source_mask, "A/C Type"] = family
            out.loc[source_mask, "Utilization Group"] = group_label
            continue

        fleet, reason = infer_aircraft_type_from_filename(source_name, loaded_fleets)
        if fleet is None:
            excluded.append(source_name)
            warnings.append(f"Utilization '{source_name}' tidak digunakan untuk Delay Rate: {reason}.")
        else:
            out.loc[source_mask, "A/C Type"] = fleet
            out.loc[source_mask, "Utilization Group"] = fleet

    if excluded:
        out = out[~(util_mask & out["_Source_File"].astype("string").isin(excluded))].copy()

    # De-duplicate only replacement files within the same utilization group/month.
    # This prevents accidental double-counting when a revised workbook is saved.
    if util_mask.any() and "Year-Month" in out.columns:
        util = out[out["_Exposure_Format"].astype("string").eq("Utilization cycles B:N")].copy()
        other = out[~out["_Exposure_Format"].astype("string").eq("Utilization cycles B:N")].copy()
        key = ["Utilization Group", "Year-Month"]
        dup_count = int(util.duplicated(subset=key, keep="last").sum())
        util = util.drop_duplicates(subset=key, keep="last")
        out = pd.concat([other, util], ignore_index=True, sort=False)
        if dup_count:
            warnings.append(f"{dup_count} overlapping utilization month(s) de-duplicated; last-loaded value used.")

    return out.reset_index(drop=True), warnings




def save_part_uploads(uploaded_files) -> tuple[int, list[str]]:
    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    saved = 0
    errors = []
    for uploaded_file in uploaded_files or []:
        try:
            safe_name = Path(uploaded_file.name).name
            target = PARTS_DIR / safe_name
            uploaded_file.seek(0)
            target.write_bytes(uploaded_file.read())
            saved += 1
        except Exception as exc:
            errors.append(f"{getattr(uploaded_file, 'name', 'component-removal')}: {exc}")
    return saved, errors

# -----------------------------------------------------------------------------
# DATA MANAGEMENT
# -----------------------------------------------------------------------------
with st.sidebar.expander("⬆ INPUT / UPDATE DATA", expanded=False):
    local_delay_files = discover_delay_files(DELAY_DIR)
    uploaded_delay_files = st.file_uploader(
        "All-ATA technical-delay Excel / CSV",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
        help=(
            "Upload raw technical-delay rows for ALL approved ATA. Powerplant ATA 49 & 71–80 are used for engineering analytics; "
            "other ATA are retained for the official Powerplant Delay Contribution denominator."
        ),
        key="upload_delay",
    )
    if uploaded_delay_files:
        remember_uploads("reliability_delay_session_uploads", uploaded_delay_files)
    else:
        uploaded_delay_files = restore_uploads("reliability_delay_session_uploads")
    _delay_session_files = upload_memories_info("reliability_delay_session_uploads")

    uploaded_exposure_files = st.file_uploader(
        "Revenue T/O / Utilization",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
        help=(
            "Upload satu atau banyak workbook fleet. Untuk exposure, dashboard membaca Utilization!B:N (row cycles). "
            "Workbook standard yang juga memiliki IFSD/RTO/RTB/UER/ERR/SVR/D&C akan otomatis dipakai pada tab Operational Events. "
            "Fleet dibaca dari nama file/engine family; file yang ambigu dapat dipetakan manual."
        ),
        key="upload_exposure",
    )
    if uploaded_exposure_files:
        remember_uploads("reliability_exposure_session_uploads", uploaded_exposure_files)
    else:
        uploaded_exposure_files = restore_uploads("reliability_exposure_session_uploads")
    _exposure_session_files = upload_memories_info("reliability_exposure_session_uploads")

    # Historical calculation support remains available from the packaged
    # reference workbook in data/support, but its upload control is intentionally
    # hidden from the operational dashboard UI.
    uploaded_support = None

    uploaded_part_files = st.file_uploader(
        "Component Removal / Part Replacement",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
        help=(
            "Upload component-removal report. Dashboard uses Powerplant ATA 49 & 71–80 and RemCode "
            f"{', '.join(sorted(UNSCHEDULED_REMOVAL_CODES))} as unscheduled. Part Name / Part Number are read directly; no Rectification parser is used."
        ),
        key="upload_parts",
    )
    if uploaded_part_files:
        remember_uploads("reliability_parts_session_uploads", uploaded_part_files)
    else:
        uploaded_part_files = restore_uploads("reliability_parts_session_uploads")
    _parts_session_files = upload_memories_info("reliability_parts_session_uploads")

    include_local = st.checkbox("Use files in data/delay", value=True, key="include_local")
    if st.button("↻ Refresh Data", use_container_width=True, key="refresh_data"):
        _clear_reliability_processed_cache()
        st.cache_data.clear()
        st.rerun()

sources = []
if include_local and local_delay_files:
    sources.extend(local_source_tuples(local_delay_files))
sources.extend(uploaded_source_tuples(uploaded_delay_files))

using_demo = False
if not sources:
    demo_files = discover_delay_files(DEMO_DIR)
    sources.extend(local_source_tuples(demo_files))
    using_demo = True

_delay_cache_hit = (
    st.session_state.get("rel_delay_signature") == _source_signature(sources)
    and isinstance(st.session_state.get("rel_delay_df"), pd.DataFrame)
)
if _delay_cache_hit:
    delay_df, load_meta, _ = _cached_delay_dataset(sources)
else:
    with st.spinner("Loading and validating all-ATA technical-delay data..."):
        delay_df, load_meta, _ = _cached_delay_dataset(sources)

if delay_df.empty:
    st.error("Tidak ada data yang berhasil dimuat.")
    for error in load_meta.get("errors", []):
        st.error(error)
    st.stop()

# A330 grouping is applied once when the processed session dataset is created.

# Component-removal / part-replacement source is independent from technical-delay rows.
# It is used only for unscheduled Part Replacement analysis.
local_part_files = discover_part_files(PARTS_DIR)
part_sources = local_source_tuples(local_part_files)
part_sources.extend(uploaded_source_tuples(uploaded_part_files))
_part_sig = _source_signature(part_sources)
_part_cache_hit = (
    st.session_state.get("rel_part_signature") == _part_sig
    and isinstance(st.session_state.get("rel_part_df"), pd.DataFrame)
)
if _part_cache_hit:
    part_df, part_meta, _ = _cached_part_dataset(part_sources)
elif part_sources:
    with st.spinner("Loading component-removal / part-replacement data..."):
        part_df, part_meta, _ = _cached_part_dataset(part_sources)
else:
    part_df, part_meta, _ = _cached_part_dataset(part_sources)

# Normal operational exposure has precedence. If absent, the calculation-support
# workbook can provide yearly Revenue T/O as a method-consistent fallback.
exposure_files = [
    p for p in discover_delay_files(EXPOSURE_DIR)
    if "template" not in p.stem.casefold()
]
exposure_df, exposure_errors, _exposure_signature, _exposure_cache_hit = _cached_exposure_dataset(
    exposure_files, uploaded_exposure_files
)
raw_exposure_df = exposure_df.copy()
loaded_fleets = sorted(
    x for x in delay_df.get("A/C Type", pd.Series(dtype="string")).astype("string").fillna("").str.strip().unique().tolist()
    if x
)
exposure_df, utilization_mapping_warnings = map_utilization_files_to_fleets(exposure_df, loaded_fleets)
if not exposure_df.empty:
    exposure_df = apply_aircraft_grouping(exposure_df)

# Standard fleet reliability workbooks are reused for Operational Events.
# Raw monthly sheets are parsed independently from Summary to avoid inheriting workbook formula errors.
_operational_source_objects: dict[str, object] = {}
for _p in exposure_files:
    if _p.suffix.lower() in {".xlsx", ".xls"}:
        _operational_source_objects[_p.name] = _p
for _uploaded in uploaded_exposure_files or []:
    _name = str(getattr(_uploaded, "name", ""))
    if Path(_name).suffix.lower() in {".xlsx", ".xls"}:
        _operational_source_objects[_name] = _uploaded  # uploaded/session copy supersedes saved local copy

_raw_standard_sources: list[str] = []
if not raw_exposure_df.empty and "_Exposure_Format" in raw_exposure_df.columns:
    _raw_standard_sources = (
        raw_exposure_df.loc[
            raw_exposure_df["_Exposure_Format"].astype("string").eq("Utilization cycles B:N"),
            "_Source_File",
        ].astype("string").dropna().unique().tolist()
    )

_source_fleet_map: dict[str, str] = {}
if not exposure_df.empty and {"_Source_File", "A/C Type"}.issubset(exposure_df.columns):
    for _source_name, _group in exposure_df.groupby("_Source_File", dropna=True):
        _fleets = [x for x in _group["A/C Type"].astype("string").dropna().unique().tolist() if x in FLEET_ORDER]
        if len(_fleets) == 1:
            _source_fleet_map[str(_source_name)] = _fleets[0]

_unmapped_operational = [
    n for n in _raw_standard_sources
    if n in _operational_source_objects and not (_source_fleet_map.get(n) or infer_operational_fleet(n))
]
_manual_operational_map: dict[str, str] = {}
if _unmapped_operational:
    with st.sidebar.expander("Operational Events · Fleet Mapping", expanded=True):
        st.caption("Only needed when the workbook filename does not identify B737, B777, or A330.")
        for _name in _unmapped_operational:
            _choice = st.selectbox(
                _name, ["Ignore", "B737", "B777", "A330"], index=0,
                key=f"operational_fleet_map_{re.sub(r'[^A-Za-z0-9]+', '_', _name)}",
            )
            if _choice != "Ignore":
                _manual_operational_map[_name] = _choice

# A manual mapping also restores that workbook to the utilization denominator,
# so the same fleet file drives both exposure and Operational Events consistently.
if _manual_operational_map and not raw_exposure_df.empty:
    _manual_exposure_rows = []
    for _name, _fleet in _manual_operational_map.items():
        _rows = raw_exposure_df[raw_exposure_df["_Source_File"].astype("string").eq(_name)].copy()
        if _rows.empty:
            continue
        _rows["A/C Type"] = _fleet
        _rows["Utilization Group"] = _fleet
        _manual_exposure_rows.append(_rows)
    if _manual_exposure_rows:
        exposure_df = pd.concat([exposure_df] + _manual_exposure_rows, ignore_index=True, sort=False)
        if "Year-Month" in exposure_df.columns:
            exposure_df = exposure_df.drop_duplicates(subset=["A/C Type", "Year-Month"], keep="last")
        exposure_df = apply_aircraft_grouping(exposure_df)
        utilization_mapping_warnings = [
            w for w in utilization_mapping_warnings
            if not any(name in w for name in _manual_operational_map)
        ]

_operational_signature = (
    _exposure_signature,
    tuple(_raw_standard_sources),
    tuple(sorted(_source_fleet_map.items())),
    tuple(sorted(_manual_operational_map.items())),
)

_operational_bundle = None
if st.session_state.get("rel_operational_signature") == _operational_signature:
    _candidate_bundle = st.session_state.get("rel_operational_bundle")
    if isinstance(_candidate_bundle, dict):
        _operational_bundle = _candidate_bundle

if _operational_bundle is None:
    _operational_monthly_frames: list[pd.DataFrame] = []
    _operational_dc_frames: list[pd.DataFrame] = []
    _operational_recon_frames: list[pd.DataFrame] = []
    operational_targets_by_fleet: dict[str, dict[str, float]] = {}
    operational_source_status: list[dict[str, object]] = []
    operational_source_warnings: list[str] = []
    operational_source_errors: list[str] = []
    _seen_fleet_sources: dict[str, list[str]] = {}

    for _source_name in _raw_standard_sources:
        _source = _operational_source_objects.get(_source_name)
        if _source is None:
            continue
        _fleet = _manual_operational_map.get(_source_name) or _source_fleet_map.get(_source_name) or infer_operational_fleet(_source_name)
        if _fleet not in FLEET_ORDER:
            continue
        try:
            _parsed = _parse_operational_workbook_cached(_source_bytes(_source), _source_name, _fleet)
            _monthly = _parsed["monthly"].copy()
            _dc = _parsed["dc_ata"].copy()
            _recon = _parsed["reconciliation"].copy()
            _operational_monthly_frames.append(_monthly)
            if not _dc.empty:
                _operational_dc_frames.append(_dc)
            if not _recon.empty:
                _recon["Fleet"] = _fleet
                _recon["Source File"] = _source_name
                _operational_recon_frames.append(_recon)
            operational_targets_by_fleet[_fleet] = dict(_parsed.get("targets", {}))
            _seen_fleet_sources.setdefault(_fleet, []).append(_source_name)
            operational_source_status.append({
                "Fleet": _fleet,
                "Source": _source_name,
                "Coverage": f"{pd.Timestamp(_parsed['coverage_start']).strftime('%b %Y')} – {pd.Timestamp(_parsed['coverage_end']).strftime('%b %Y')}",
                "Months": len(_monthly),
                "Status": "Ready",
            })
            operational_source_warnings.extend([f"{_fleet} · {_source_name}: {w}" for w in _parsed.get("warnings", [])])
        except Exception as _exc:
            operational_source_errors.append(f"{_source_name}: {_exc}")
            operational_source_status.append({
                "Fleet": _fleet, "Source": _source_name, "Coverage": "—", "Months": 0, "Status": "Template issue"
            })

    for _fleet, _sources_for_fleet in _seen_fleet_sources.items():
        if len(_sources_for_fleet) > 1:
            operational_source_warnings.append(
                f"{_fleet}: multiple workbooks loaded ({', '.join(_sources_for_fleet)}). For overlapping months, the last-loaded source is used."
            )

    operational_monthly_df = combine_operational_monthly(_operational_monthly_frames)
    operational_dc_ata_df = combine_dc_ata(_operational_dc_frames)
    operational_reconciliation_df = (
        pd.concat(_operational_recon_frames, ignore_index=True, sort=False) if _operational_recon_frames else pd.DataFrame()
    )
    _operational_bundle = {
        "monthly": operational_monthly_df,
        "dc_ata": operational_dc_ata_df,
        "reconciliation": operational_reconciliation_df,
        "targets": operational_targets_by_fleet,
        "status": operational_source_status,
        "warnings": operational_source_warnings,
        "errors": operational_source_errors,
    }
    st.session_state["rel_operational_signature"] = _operational_signature
    st.session_state["rel_operational_bundle"] = _operational_bundle
else:
    operational_monthly_df = _operational_bundle.get("monthly", pd.DataFrame())
    operational_dc_ata_df = _operational_bundle.get("dc_ata", pd.DataFrame())
    operational_reconciliation_df = _operational_bundle.get("reconciliation", pd.DataFrame())
    operational_targets_by_fleet = dict(_operational_bundle.get("targets", {}))
    operational_source_status = list(_operational_bundle.get("status", []))
    operational_source_warnings = list(_operational_bundle.get("warnings", []))
    operational_source_errors = list(_operational_bundle.get("errors", []))

# Keep the actual operational-exposure input for the two annual Trend tables.
annual_table_exposure_df = exposure_df.copy()
support_files = discover_delay_files(SUPPORT_DIR)
support_metrics_df, support_errors, _support_cache_hit = _cached_support_dataset(support_files, uploaded_support)
if not support_metrics_df.empty:
    support_metrics_df = apply_aircraft_grouping(support_metrics_df)
# Preserve the accurate v1.26 behavior: historical calculation-support is only
# a fallback when there is no usable operational exposure at all.
if exposure_df.empty and not support_metrics_df.empty:
    fallback = support_metrics_df[[c for c in ["Year", "A/C Type", "Revenue T/O", "Exposure Granularity", "_Source_File"] if c in support_metrics_df.columns]].copy()
    fallback["Departures"] = fallback["Revenue T/O"]
    exposure_df = fallback

for err in load_meta.get("errors", []):
    st.sidebar.warning(err)
for err in exposure_errors:
    st.sidebar.warning(err)
for err in utilization_mapping_warnings:
    st.sidebar.warning(err)
for err in support_errors:
    st.sidebar.warning(err)
for err in part_meta.get("errors", []):
    st.sidebar.warning(err)
if using_demo:
    st.sidebar.info("Demo mode aktif. Upload all-ATA production data untuk mengaktifkan official Powerplant Delay Contribution.")

# Denominator readiness is evaluated from the loaded source, not from the active
# day/month. Once non-Powerplant approved ATA are present, a 100% active-period
# contribution can legitimately occur if every delay in that period is Powerplant.
approved_source = delay_df[delay_df["ATA"].isin(ALL_TECHNICAL_ATAS)].copy()
all_ata_source_ready = bool((~approved_source["ATA"].isin(POWERPLANT_ATAS)).any())
outside_approved_ata = int((~delay_df["ATA"].isin(ALL_TECHNICAL_ATAS) & delay_df["ATA"].notna()).sum())

valid_dates = delay_df["Date"].dropna()
if valid_dates.empty:
    st.error("Semua kolom Date gagal dibaca. Periksa source file.")
    st.stop()
coverage_start = valid_dates.min()
coverage_end = valid_dates.max()
last_refresh = delay_df["_Source_Modified"].max() if "_Source_Modified" in delay_df else datetime.now()


# -----------------------------------------------------------------------------
# FILTERS — deliberately kept visually close to the dashboard mock-up.
# -----------------------------------------------------------------------------
st.sidebar.markdown("<div class='sidebar-section'>Filters</div>", unsafe_allow_html=True)

period_option = st.sidebar.selectbox(
    "Date Range",
    ["All History", "YTD Latest Year", "Last 12 Months", "Last 3 Years", "Custom"],
    index=0,
    key="period_option",
)
if period_option == "All History":
    start_date, end_date = coverage_start.date(), coverage_end.date()
elif period_option == "YTD Latest Year":
    start_date, end_date = coverage_end.replace(month=1, day=1).date(), coverage_end.date()
elif period_option == "Last 12 Months":
    start_date = (coverage_end - pd.DateOffset(months=12) + pd.Timedelta(days=1)).date()
    end_date = coverage_end.date()
elif period_option == "Last 3 Years":
    start_date = (coverage_end - pd.DateOffset(years=3) + pd.Timedelta(days=1)).date()
    end_date = coverage_end.date()
else:
    picked = st.sidebar.date_input(
        "Custom range",
        value=(coverage_start.date(), coverage_end.date()),
        min_value=coverage_start.date(),
        max_value=coverage_end.date(),
        key="custom_range",
    )
    if isinstance(picked, (tuple, list)) and len(picked) == 2:
        start_date, end_date = picked
    else:
        start_date = end_date = picked

aircraft_options = ["All Aircraft"] + sorted(x for x in delay_df["A/C Type"].dropna().unique().tolist() if x)
aircraft_type = st.sidebar.selectbox(
    "Aircraft Type",
    aircraft_options,
    index=0,
    key="aircraft_type",
    help="A330-200, A330-300, dan A330-900 digabung sebagai A330 karena menggunakan satu utilization denominator pada project ini.",
)
system_group_choice = st.sidebar.selectbox(
    "System Group",
    ["All Powerplant", "APU · ATA 49", "Propulsion · ATA 71–80"],
    index=0,
    key="system_group",
    help="Separate APU (ATA 49) from propulsion ATA 71–80 when required for engineering review.",
)

# Management scope drives official KPI numerators/denominators. Engineering
# drill-down filters (System Group, ATA, severity, keyword) must not collapse the
# official All-ATA Contribution denominator.
base_scope = filter_scope(delay_df, start_date, end_date, aircraft_type=aircraft_type)
station_options = sorted(set(base_scope["Sta Dep"].tolist() + base_scope["Sta Arr"].tolist()) - {""})
stations = st.sidebar.multiselect("Station", station_options, key="station_filter", placeholder="All Stations")

scope_for_routes = filter_scope(delay_df, start_date, end_date, aircraft_type=aircraft_type, stations=stations)
route_options = sorted(x for x in scope_for_routes["Route"].dropna().unique().tolist() if x)

pp_preanalysis = scope_for_routes[scope_for_routes["Powerplant Flag"] == "Powerplant"].copy()
pp_preanalysis = apply_system_group(pp_preanalysis, system_group_choice)
ata_options = sorted(int(x) for x in pp_preanalysis["ATA"].dropna().unique().tolist())
atas = st.sidebar.multiselect("ATA Analysis", ata_options, key="ata_filter", placeholder="All PP ATA")

event_options = sorted(x for x in pp_preanalysis["Event Type"].dropna().unique().tolist() if x)
event_types = st.sidebar.multiselect("Event Type", event_options, key="event_filter", placeholder="All Event Types")
severity = st.sidebar.selectbox("Severity", ["All", "Severe only", "Non-severe only"], index=0, key="severity_filter")
keyword = st.sidebar.text_input("Keyword Search", placeholder="fuel filter, EEC, surge...", key="keyword_search")

st.sidebar.markdown("<div class='sidebar-section'>Chart Display</div>", unsafe_allow_html=True)
chart_metric_label = st.sidebar.radio(
    "Metric for Engineering Charts",
    ["Delay Minutes", "Event Count"],
    index=0,
    horizontal=True,
    key="global_chart_metric",
    help="Switch engineering charts between Powerplant delay-minute burden and Powerplant event count.",
)
chart_metric = "Events" if chart_metric_label == "Event Count" else "Delay Minutes"

st.sidebar.markdown("<div class='sidebar-section'>ATA Share of Powerplant</div>", unsafe_allow_html=True)
contribution_basis = st.sidebar.radio(
    "ATA share basis",
    ["Events", "Delay Minutes"],
    index=0,
    horizontal=True,
    key="contribution_basis",
    help="This is an internal Powerplant breakdown. Official PP Delay Contribution remains based on the complete all-ATA management scope.",
)

# Route is kept under Advanced Filters because it is a management-scope filter;
# keyword/ATA/severity remain engineering-only filters.
with st.sidebar.expander("Advanced Filters", expanded=False):
    routes = st.multiselect("Route", route_options, key="route_filter", placeholder="All Routes")
    keyword_columns = st.multiselect("Keyword search in", SEARCH_COLUMNS, default=SEARCH_COLUMNS, key="keyword_columns")
    keyword_mode = st.radio(
        "Keyword match",
        ["Any words", "All words", "Exact phrase", "Regex (advanced)"],
        index=0,
        key="keyword_mode",
    )

# Official management scope: date + aircraft + station + route, ALL approved ATA retained.
all_scope_df = filter_scope(
    delay_df,
    start_date,
    end_date,
    aircraft_type=aircraft_type,
    stations=stations,
    routes=routes,
)

# Engineering scope: Powerplant only, with optional APU/propulsion split.
pp_scope_df = all_scope_df[all_scope_df["Powerplant Flag"] == "Powerplant"].copy()
pp_scope_df = apply_system_group(pp_scope_df, system_group_choice)

pp_contribution_atas = sorted(int(x) for x in pp_scope_df["ATA"].dropna().unique().tolist())
contribution_options = ["Top contributor (Auto)"] + [f"ATA {ata}" for ata in pp_contribution_atas]
contribution_choice = st.sidebar.selectbox(
    "ATA chapter",
    contribution_options,
    index=0,
    key="contribution_ata",
    help="Selected ATA share is compared with all Powerplant ATA in the same management scope.",
)
contribution_ata = None if contribution_choice == "Top contributor (Auto)" else int(contribution_choice.split()[-1])

analysis_df = filter_analysis(
    pp_scope_df,
    atas=atas,
    severity=severity,
    event_types=event_types,
    keyword=keyword,
    keyword_columns=keyword_columns,
    keyword_mode=keyword_mode,
)

# Unscheduled Powerplant part-removal scope follows the same management date / aircraft filters.
part_scope_df = filter_part_scope(
    part_df,
    start_date=start_date,
    end_date=end_date,
    aircraft_type=aircraft_type,
    unscheduled_only=True,
) if not part_df.empty else pd.DataFrame()
if not part_scope_df.empty:
    part_scope_df = apply_system_group(part_scope_df, system_group_choice)
linked_part_scope_df = link_parts_to_delay(part_scope_df, delay_df) if not part_scope_df.empty else pd.DataFrame()

# Keep compatibility with older modules that refer to scope_df as the Powerplant scope.
scope_df = pp_scope_df

quality = data_quality_summary(delay_df, load_meta.get("exact_duplicates_removed", 0))
pp_detail_missing = int(((delay_df["Powerplant Flag"] == "Powerplant") & ((delay_df["A/C Reg"] == "") | (delay_df["Problem"] == ""))).sum())
quality_extra = pd.DataFrame([
    {
        "Control": "All-ATA denominator source",
        "Value": int((approved_source["Powerplant Flag"] != "Powerplant").sum()),
        "Status": "READY" if all_ata_source_ready else "CHECK",
        "Action": "Load non-Powerplant ATA rows as denominator for official PP Delay Contribution",
    },
    {
        "Control": "ATA outside approved technical scope",
        "Value": outside_approved_ata,
        "Status": "WARNING" if outside_approved_ata else "READY",
        "Action": "Review; rows outside the approved ATA universe are excluded from contribution denominator",
    },
    {
        "Control": "PP rows missing Reg / Problem",
        "Value": pp_detail_missing,
        "Status": "WARNING" if pp_detail_missing else "READY",
        "Action": "Non-PP denominator rows may be minimal; Powerplant rows should retain engineering detail",
    },
])
quality = pd.concat([quality, quality_extra], ignore_index=True)
core_checks = quality[quality["Status"] == "CHECK"]
status = "READY" if core_checks.empty else "CHECK DATA"
if exposure_df.empty:
    status = status + " · RATE BLANK"
if not all_ata_source_ready:
    status = status + " · CONTRIBUTION BLANK"

render_sidebar_status(
    status,
    coverage_start,
    coverage_end,
    delay_df["A/C Type"].replace("", pd.NA).nunique(),
    not exposure_df.empty,
)


# -----------------------------------------------------------------------------
# HEADER & KPI STRIP
# -----------------------------------------------------------------------------
# Compact workspace switcher: navigation stays available without consuming sidebar space.
_nav_spacer, _nav_col = st.columns([9.2, 0.8])
with _nav_col:
    with st.popover("☰ Rooms"):
        st.markdown("**Workspace**")
        st.caption("Current: Reliability Room")
        if st.button("Control Center", use_container_width=True, key="cc_home_from_rel_popover"):
            st.switch_page("home.py")
        if st.button("Engine Shop Visit", use_container_width=True, key="cc_shop_from_rel_popover"):
            st.switch_page("engine_shop_visit_page.py")
        if st.button("APU Shop Visit", use_container_width=True, key="cc_apu_from_rel_popover"):
            st.switch_page("apu_shop_visit_page.py")

render_header(coverage_start, coverage_end, last_refresh, len(load_meta.get("sources", [])), status)

kpi = compute_kpis(
    all_scope_df,
    exposure_df,
    start_date,
    end_date,
    aircraft_type,
    contribution_ata=contribution_ata,
    contribution_basis=contribution_basis,
    all_ata_source_ready=all_ata_source_ready,
)

# Share only high-level room health with the Control Center.
st.session_state["cc_reliability_snapshot"] = {
    "pp_events": int(kpi.pp_events),
    "delay_minutes": float(kpi.pp_delay_minutes),
    "contribution": kpi.pp_delay_contribution_pct,
    "delay_rate": kpi.delay_rate_100,
    "severe": int(kpi.severe_events),
    "significant": int(kpi.significant_events),
    "exposure_ready": not exposure_df.empty,
    "status": status,
    "aircraft": aircraft_type,
    "period": period_option,
}

prev_start, prev_end = previous_period_dates(period_option, start_date, end_date)
previous_kpi = None
prev_all_scope = pd.DataFrame()
prev_scope = pd.DataFrame()  # Powerplant comparator scope for Engineering Focus
if prev_start is not None and prev_end is not None:
    prev_all_scope = filter_scope(
        delay_df,
        prev_start,
        prev_end,
        aircraft_type=aircraft_type,
        stations=stations,
        routes=routes,
    )
    prev_scope = prev_all_scope[prev_all_scope["Powerplant Flag"] == "Powerplant"].copy()
    prev_scope = apply_system_group(prev_scope, system_group_choice)
    if not prev_all_scope.empty:
        previous_kpi = compute_kpis(
            prev_all_scope,
            exposure_df,
            prev_start,
            prev_end,
            aircraft_type,
            contribution_ata=kpi.contribution_ata,
            contribution_basis=contribution_basis,
            all_ata_source_ready=all_ata_source_ready,
        )

scope_chips = [
    ("Period", period_option),
    ("Aircraft", aircraft_type),
    ("System", system_group_choice),
    ("Metric", chart_metric_label),
    ("Severity", severity.replace(" only", "") if severity != "All" else "All"),
]
if atas:
    scope_chips.append(("ATA", ", ".join([str(a) for a in atas[:3]]) + (f" +{len(atas)-3} more" if len(atas) > 3 else "")))
elif system_group_choice == "APU · ATA 49":
    scope_chips.append(("ATA", "49 only"))
elif system_group_choice == "Propulsion · ATA 71–80":
    scope_chips.append(("ATA", "71–80"))
else:
    scope_chips.append(("ATA", "All PP ATA"))
if stations:
    scope_chips.append(("Station", ", ".join(stations[:2]) + (f" +{len(stations)-2} more" if len(stations) > 2 else "")))
if keyword:
    scope_chips.append(("Keyword", keyword[:24] + ("…" if len(keyword) > 24 else "")))

render_analysis_context(
    start_date,
    end_date,
    period_option,
    scope_chips,
    prev_start=prev_start,
    prev_end=prev_end,
    comparator_available=previous_kpi is not None,
)

render_kpis(kpi, kpi.all_technical_events, previous_kpi=previous_kpi)

if not all_ata_source_ready:
    st.warning(
        "Official Powerplant Delay Contribution belum ditampilkan karena source yang dimuat belum memiliki non-Powerplant ATA sebagai denominator. "
        "Upload all-ATA technical-delay data; engineering Powerplant analytics tetap dapat digunakan."
    )
if stations and not exposure_df.empty:
    st.caption(
        "PP Delay Rate denominator mengikuti period dan aircraft type. Station/route hanya diterapkan ke numerator kecuali Revenue T/O Anda tersedia pada grain yang sama."
    )


# -----------------------------------------------------------------------------
# DASHBOARD TABS
# -----------------------------------------------------------------------------
executive_tab, operational_tab, intelligence_tab, ata_tab, parts_tab, events_tab = st.tabs(
    [
        "**Overview**",
        "**Operational Events**",
        "**Aircraft**",
        "**ATA / Problems**",
        "**Parts**",
        "**Events**",
    ]
)

with executive_tab:
    # Executive Dashboard is intentionally concise. It answers:
    # 1) What needs attention? 2) How is the trend moving?
    # 3) Which ATA drives the burden? 4) Which tails deserve a quick review?

    # 01 — Engineering priorities. Keep executive attention on operational /
    # engineering signals; classification coverage remains available in System Check.
    st.markdown(
        "<div class='executive-section-head executive-section-first'><span class='executive-section-no'>01</span>"
        "<span class='executive-section-title'>Priority signals</span>"
        "<span class='executive-section-desc'>What requires engineering attention now</span></div>",
        unsafe_allow_html=True,
    )
    executive_focus_items = [
        item
        for item in engineering_focus_v2(scope_df, prev_scope if not prev_scope.empty else None)
        if str(item.get("label", "")).strip().lower() != "classification coverage"
    ][:3]
    st.session_state["cc_reliability_focus"] = executive_focus_items
    render_focus(
        executive_focus_items,
        start_date=start_date,
        end_date=end_date,
    )

    # 02 — One trend panel instead of three separate large charts.
    st.markdown(
        "<div class='executive-section-head'><span class='executive-section-no'>02</span>"
        "<span class='executive-section-title'>Trend analysis</span>"
        "<span class='executive-section-desc'>How performance is moving over time</span></div>",
        unsafe_allow_html=True,
    )
    t_left, t_right = st.columns([3.5, 2.2], gap="small")
    with t_left:
        trend_view = st.radio(
            "Trend view",
            ["Delay Minutes", "PP Contribution %", "Delay Rate /100 T/O"],
            index=0,
            horizontal=True,
            key="exec_clean_trend_view",
            help="Delay Minutes = operational burden. PP Contribution = Powerplant share of all technical-delay events. Delay Rate = Powerplant occurrence frequency relative to Revenue T/O.",
            label_visibility="collapsed",
        )
    with t_right:
        if trend_view == "Delay Minutes":
            trend_granularity = st.radio(
                "Granularity",
                ["Monthly", "Daily"],
                index=0,
                horizontal=True,
                key="exec_clean_burden_grain",
                label_visibility="collapsed",
            )
        else:
            trend_granularity = st.radio(
                "Granularity",
                ["Monthly", "Yearly"],
                index=1,
                horizontal=True,
                key="exec_clean_reliability_grain",
                label_visibility="collapsed",
            )

    # Trend Analysis follows the dashboard's active Date Range. The date window
    # behind each plotted point is shown in the hover tooltip instead of adding
    # a second display-window selector.
    trend_scope_df = scope_df.copy()
    trend_all_scope_df = all_scope_df.copy()

    if trend_view == "Delay Minutes":
        st.caption("Operational burden caused by Powerplant delays. Use Daily to inspect individual spike dates; Monthly is better for management review.")
        plot(
            delay_minutes_line(
                delay_minutes_trend(trend_scope_df, trend_granularity, start_date=start_date, end_date=end_date),
                metric="Delay Minutes",
                title="Powerplant Delay Minutes Trend",
                granularity=trend_granularity,
                start_date=start_date,
                end_date=end_date,
            ),
            f"exec_clean_delay_minutes_{trend_granularity.lower()}",
        )
    else:
        reliability_summary = reliability_calculation_summary(
            trend_all_scope_df,
            exposure_df,
            aircraft_type,
            freq=trend_granularity,
            all_ata_source_ready=all_ata_source_ready,
            start_date=start_date,
            end_date=end_date,
        )
        if trend_view == "PP Contribution %":
            st.caption("Powerplant share of all technical-delay events. A rising percentage does not necessarily mean PP event count increased; read it together with the PP Events KPI.")
            plot(
                powerplant_contribution_line(
                    reliability_summary,
                    title="Powerplant Share of All Technical Delay Events (%)",
                    granularity=trend_granularity,
                    start_date=start_date,
                    end_date=end_date,
                ),
                f"exec_clean_contribution_{trend_granularity.lower()}",
            )
        else:
            st.caption("Powerplant delay occurrence frequency relative to Revenue T/O. Lower is generally better when fleet scope and exposure definition are comparable.")
            plot(
                powerplant_delay_rate_line(
                    reliability_summary,
                    title="Powerplant Delay Rate /100 Revenue T/O",
                    granularity=trend_granularity,
                    start_date=start_date,
                    end_date=end_date,
                ),
                f"exec_clean_rate_{trend_granularity.lower()}",
            )

    # Preserve the annual numerical support table in the v1.26 Executive Trend Analysis.
    # It gives users the exact values behind Contribution and Delay Rate without showing formulas.
    annual_trend_values = annual_reliability_from_inputs(
        delay_df,
        annual_table_exposure_df,
        aircraft_type,
        all_ata_source_ready=all_ata_source_ready,
    )
    if annual_trend_values.empty:
        st.info("Annual contribution/rate values are not available for the active scope.")
    else:
        annual_display = annual_trend_values.copy()
        annual_columns = [
            "Year",
            "PP Delay Events",
            "All ATA Delay Events",
            "PP Delay Contribution %",
            "Revenue T/O",
            "PP Delay Rate /100 T/O",
        ]
        for col in annual_columns:
            if col not in annual_display.columns:
                annual_display[col] = pd.NA
        annual_display = annual_display[annual_columns].copy()
        annual_display["Year"] = pd.to_numeric(annual_display["Year"], errors="coerce").astype("Int64")
        annual_display["PP Delay Events"] = pd.to_numeric(annual_display["PP Delay Events"], errors="coerce").round(0).astype("Int64")
        annual_display["All ATA Delay Events"] = pd.to_numeric(annual_display["All ATA Delay Events"], errors="coerce").round(0).astype("Int64")
        annual_display["PP Delay Contribution %"] = pd.to_numeric(annual_display["PP Delay Contribution %"], errors="coerce").round(2)
        annual_display["Revenue T/O"] = pd.to_numeric(annual_display["Revenue T/O"], errors="coerce").round(0).astype("Int64")
        annual_display["PP Delay Rate /100 T/O"] = pd.to_numeric(annual_display["PP Delay Rate /100 T/O"], errors="coerce").round(3)
        annual_display = annual_display.sort_values("Year").drop_duplicates(subset=["Year"], keep="last")

        # Compact annual reliability matrix for fast executive reading.
        # This intentionally mirrors the management-report layout: years across columns,
        # Contribution and Delay Rate as the two headline reliability rows.
        compact = annual_display.dropna(subset=["Year"]).copy()
        if not compact.empty:
            def _fmt_pct(value):
                if pd.isna(value):
                    return "—"
                return f"{float(value):.1f}%".replace(".", ",")

            def _fmt_rate(value):
                if pd.isna(value):
                    return "—"
                return f"{float(value):.3f}".replace(".", ",")

            years = [str(int(y)) for y in compact["Year"].tolist()]
            contrib_values = [_fmt_pct(v) for v in compact["PP Delay Contribution %"].tolist()]
            rate_values = [_fmt_rate(v) for v in compact["PP Delay Rate /100 T/O"].tolist()]

            header_cells = "".join(f"<th>{year}</th>" for year in years)
            contrib_cells = "".join(f"<td>{value}</td>" for value in contrib_values)
            rate_cells = "".join(f"<td>{value}</td>" for value in rate_values)

            st.markdown("#### Reliability Trend Summary")
            st.caption("Year-on-year comparison calculated from the currently loaded delay and Revenue T/O inputs for the selected aircraft type.")
            st.markdown(
                f"""
                <style>
                .pp-rel-summary-wrap {{
                    width: 100%; overflow-x: auto; margin: 0.15rem 0 1.15rem 0;
                    border-radius: 12px; background: var(--pp-card);
                }}
                table.pp-rel-summary {{
                    width: 100%; min-width: 860px; border-collapse: collapse;
                    font-family: inherit; background: var(--pp-card);
                }}
                table.pp-rel-summary th, table.pp-rel-summary td {{
                    padding: 13px 14px; text-align: center; white-space: nowrap;
                    border: none; font-size: 1.00rem;
                }}
                table.pp-rel-summary thead th {{
                    color: var(--pp-text); font-weight: 700; border-bottom: 2px solid var(--pp-blue);
                }}
                table.pp-rel-summary thead th:first-child {{
                    min-width: 220px; text-align: center;
                }}
                table.pp-rel-summary tbody th {{
                    color: var(--pp-text); font-weight: 650; text-align: center; line-height: 1.15;
                    border-bottom: 2px solid var(--pp-blue);
                }}
                table.pp-rel-summary tbody td {{
                    color: var(--pp-navy); font-weight: 750; font-size: 1.08rem;
                    border-bottom: 2px solid var(--pp-blue);
                }}
                table.pp-rel-summary tbody tr:last-child th,
                table.pp-rel-summary tbody tr:last-child td {{
                    border-bottom: none;
                }}
                </style>
                <div class="pp-rel-summary-wrap">
                    <table class="pp-rel-summary">
                        <thead>
                            <tr><th>Year</th>{header_cells}</tr>
                        </thead>
                        <tbody>
                            <tr>
                                <th>Powerplant Delay<br>Contribution (%)</th>
                                {contrib_cells}
                            </tr>
                            <tr>
                                <th>Powerplant Delay Rate<br>(/100 Departs)</th>
                                {rate_cells}
                            </tr>
                        </tbody>
                    </table>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("#### Annual Trend Values")
        st.caption(
            "Exact yearly values calculated from the currently loaded inputs. Years not present in the delay source are not added to this table."
        )
        st.dataframe(
            annual_display,
            use_container_width=True,
            hide_index=True,
            height=min(390, 78 + max(len(annual_display), 1) * 46),
            column_config={
                "Year": st.column_config.NumberColumn("Year", format="%d"),
                "PP Delay Events": st.column_config.NumberColumn("PP Delay Events", format="%d"),
                "All ATA Delay Events": st.column_config.NumberColumn("All ATA Delay Events", format="%d"),
                "PP Delay Contribution %": st.column_config.NumberColumn("PP Delay Contribution %", format="%.2f"),
                "Revenue T/O": st.column_config.NumberColumn("Revenue T/O", format="%d"),
                "PP Delay Rate /100 T/O": st.column_config.NumberColumn("PP Delay Rate /100 T/O", format="%.3f"),
            },
            key="exec_v126_annual_trend_values",
        )

    # 02B — Restored from v1.26: Rolling 12-Month analysis.
    st.markdown(
        "<div class='executive-section-head'><span class='executive-section-no'>02B</span>"
        "<span class='executive-section-title'>12-Month Rolling trend</span>"
        "<span class='executive-section-desc'>Trailing 12-month reliability movement; restored from v1.26</span></div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Each point represents the complete trailing 12 months ending in that month. "
        "The first point appears only after 12 complete monthly periods are available."
    )
    rolling_metric = st.radio(
        "12-MONTH ROLLING METRIC",
        ["Delay Minutes", "PP Contribution %", "Delay Rate /100 T/O"],
        index=0,
        horizontal=True,
        key="exec_r12m_metric_selector",
    )

    if rolling_metric == "Delay Minutes":
        rolling_data = rolling_12m_delay_minutes(
            scope_df, start_date=start_date, end_date=end_date
        )
        rolling_fig = rolling_12m_delay_minutes_line(
            rolling_data, title="Powerplant Delay Minutes · Rolling 12 Months"
        )
        rolling_key = "exec_r12m_delay_minutes"
    else:
        rolling_data = rolling_12m_reliability_summary(
            all_scope_df,
            exposure_df,
            aircraft_type,
            all_ata_source_ready=all_ata_source_ready,
            start_date=start_date,
            end_date=end_date,
        )
        if rolling_metric == "PP Contribution %":
            rolling_fig = rolling_12m_contribution_line(
                rolling_data, title="Powerplant Delay Contribution · Rolling 12 Months (%)"
            )
            rolling_key = "exec_r12m_contribution"
        else:
            rolling_fig = rolling_12m_delay_rate_line(
                rolling_data, title="Powerplant Delay Rate · Rolling 12 Months (/100 Revenue T/O)"
            )
            rolling_key = "exec_r12m_delay_rate"

    plot(rolling_fig, rolling_key)

    # 03 — Driver analysis: top 3 ATA then one selected ATA problem breakdown.
    st.markdown(
        "<div class='executive-section-head'><span class='executive-section-no'>03</span>"
        "<span class='executive-section-title'>Top ATA → problem driver</span>"
        "<span class='executive-section-desc'>Rank the dominant ATA chapters, then inspect the underlying problem drivers</span></div>",
        unsafe_allow_html=True,
    )

    top3_rank_view = st.radio(
        "TOP ATA RANKING",
        ["Delay Minutes", "Event Count"],
        index=0,
        horizontal=True,
        key="exec_clean_top3_metric",
    )
    top3_metric = "Events" if top3_rank_view == "Event Count" else "Delay Minutes"
    top3_scope = scope_df
    top3_ata = ata_summary(top3_scope, top3_metric).head(3).copy()
    if top3_ata.empty:
        st.info("No Powerplant ATA data for the active scope.")
    else:
        top3_title = (
            "Top 3 Powerplant ATA Contributors by Event Count"
            if top3_metric == "Events"
            else "Top 3 Powerplant ATA Contributors by Delay Minutes"
        )
        plot(
            top_ata_bar(
                top3_ata,
                top3_metric,
                top_n=3,
                title=top3_title,
            ),
            "exec_clean_top3_ata",
        )
        top3_options = [int(v) for v in top3_ata["ATA"].tolist()]
        if top3_metric == "Events":
            top3_label = {
                int(r["ATA"]): f"ATA {int(r['ATA'])} · {float(r['Events']):,.0f} events · {float(r['Share %']):.1f}% of PP events"
                for _, r in top3_ata.iterrows()
            }
        else:
            top3_label = {
                int(r["ATA"]): f"ATA {int(r['ATA'])} · {float(r['Delay Minutes']):,.0f} min · {float(r['Share %']):.1f}% of PP delay"
                for _, r in top3_ata.iterrows()
            }
        selected_driver_ata = st.radio(
            "SELECT ATA TO REVIEW",
            top3_options,
            index=0,
            horizontal=True,
            format_func=lambda ata: top3_label.get(int(ata), f"ATA {ata}"),
            key="exec_clean_top3_selector",
        )

        ata_detail = scope_df[pd.to_numeric(scope_df["ATA"], errors="coerce") == int(selected_driver_ata)].copy()
        ata_detail["Tech Dur"] = pd.to_numeric(ata_detail["Tech Dur"], errors="coerce").fillna(0).clip(lower=0)
        ata_delay = float(ata_detail["Tech Dur"].sum())
        ata_events = int(len(ata_detail))
        pp_delay_total = float(pd.to_numeric(scope_df["Tech Dur"], errors="coerce").fillna(0).clip(lower=0).sum())
        ata_share = (ata_delay / pp_delay_total * 100) if pp_delay_total > 0 else 0.0
        ata_aircraft = int(ata_detail["A/C Reg"].replace("", pd.NA).nunique(dropna=True))
        ata_severe = int((ata_detail["Tech Dur"] >= SEVERE_THRESHOLD_MIN).sum())
        ata_operational = int(ata_detail["Event Type"].astype("string").str.upper().isin(["RTA", "RTB", "RTO"]).sum())

        s1, s2, s3, s4, s5 = st.columns(5, gap="small")
        s1.metric("ATA", f"{selected_driver_ata}")
        s2.metric("Delay Minutes", f"{ata_delay:,.0f}")
        s3.metric("Events", f"{ata_events:,}")
        s4.metric("Share of PP Delay", f"{ata_share:.1f}%")
        s5.metric("Aircraft / Severe", f"{ata_aircraft} / {ata_severe}")

        problem_col = "Problem Group" if "Problem Group" in ata_detail.columns else "KeyProblem"
        problem_source = ata_detail.copy()
        problem_source[problem_col] = problem_source[problem_col].astype("string").fillna("").str.strip().replace("", "NEEDS CLASSIFICATION")
        problem_source["_Severe"] = (problem_source["Tech Dur"] >= SEVERE_THRESHOLD_MIN).astype(int)
        problem_source["_Operational"] = problem_source["Event Type"].astype("string").str.upper().isin(["RTA", "RTB", "RTO"]).astype(int)
        problem_table = problem_source.groupby(problem_col, dropna=False).agg(
            Events=("Occurrence", "sum"),
            **{
                "Delay Minutes": ("Tech Dur", "sum"),
                "Aircraft": ("A/C Reg", "nunique"),
                "Severe": ("_Severe", "sum"),
                "RTA/RTB/RTO": ("_Operational", "sum"),
            },
        ).reset_index().rename(columns={problem_col: "Problem Group"})
        problem_table["Share of ATA Delay %"] = (problem_table["Delay Minutes"] / ata_delay * 100) if ata_delay > 0 else 0.0
        problem_table = problem_table.sort_values(["Delay Minutes", "Events"], ascending=False)
        problem_table["Delay Minutes"] = problem_table["Delay Minutes"].round(0).astype(int)
        problem_table["Share of ATA Delay %"] = problem_table["Share of ATA Delay %"].round(1)

        driver_chart, driver_table = st.columns([1.05, 0.95], gap="small")
        with driver_chart:
            driver_source = ata_detail
            plot(
                key_problem_bar(
                    key_problem_summary(driver_source, 10000, "Delay Minutes"),
                    top_n=8,
                    metric="Delay Minutes",
                    title=f"ATA {selected_driver_ata} · Main Problem Drivers",
                ),
                f"exec_clean_ata_{selected_driver_ata}_problems",
            )
        with driver_table:
            st.markdown(f"<div class='section-title'>ATA {selected_driver_ata} · Problem Review</div>", unsafe_allow_html=True)
            st.dataframe(
                problem_table.head(8),
                use_container_width=True,
                hide_index=True,
                height=300,
            )
        st.caption("Detailed individual events remain available in Event Explorer; repetitive patterns and rectification recurrence remain in Aircraft & Repetitive Analysis.")

        # Unscheduled component removals for the same selected ATA.
        # Part names come directly from the component-removal report, not from Rectification text parsing.
        exec_parts = part_scope_df[part_scope_df["ATA"] == int(selected_driver_ata)].copy() if not part_scope_df.empty else pd.DataFrame()
        st.markdown(f"<div class='section-title'>ATA {selected_driver_ata} · Unscheduled Parts Changed</div>", unsafe_allow_html=True)
        if exec_parts.empty:
            st.info(
                "No unscheduled component-removal records for this ATA in the active date / aircraft scope. "
                "Upload the Component Removal report in Input Data when available."
            )
        else:
            exec_parts_chart = exec_parts
            exec_part_summary = part_summary(exec_parts_chart).head(6).copy()
            exec_part_summary["Part Short"] = exec_part_summary["Part"].astype(str).map(
                lambda x: x if len(x) <= 48 else x[:45] + "..."
            )
            part_fig = px.bar(
                exec_part_summary.sort_values("Removals"),
                x="Removals",
                y="Part Short",
                orientation="h",
                text="Removals",
                custom_data=["Part", "Aircraft", "Share %"],
                title=f"ATA {selected_driver_ata} · Most Frequent Unscheduled Part Removals",
            )
            part_fig.update_traces(
                textposition="outside",
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Removals: %{x}<br>"
                    "Aircraft affected: %{customdata[1]}<br>"
                    "Share of ATA removals: %{customdata[2]:.1f}%<extra></extra>"
                ),
            )
            part_fig.update_layout(yaxis_title="Part", xaxis_title="Unscheduled removals")
            plot(part_fig, f"exec_parts_ata_{selected_driver_ata}")

            st.markdown(
                "<div class='section-title' style='margin-top:10px;'>Removal Detail Table</div>",
                unsafe_allow_html=True,
            )
            exec_show = exec_part_summary[["Part", "Removals", "Share %", "Aircraft", "Part Numbers", "Latest Removal"]].copy()
            exec_show["Share %"] = exec_show["Share %"].round(1)
            exec_show["Latest Removal"] = pd.to_datetime(exec_show["Latest Removal"], errors="coerce").dt.strftime("%Y-%m-%d")
            st.dataframe(exec_show, use_container_width=True, hide_index=True, height=280)

            # Component drill-down: show every underlying removal event and export a review-ready Excel workbook.
            st.markdown(
                "<div class='section-title' style='margin-top:18px;'>Component Drill-down · Underlying Removal Events</div>",
                unsafe_allow_html=True,
            )
            part_options = exec_part_summary["Part"].astype(str).tolist()
            selected_exec_part = st.selectbox(
                "Select component to investigate",
                part_options,
                index=0,
                key=f"exec_part_drilldown_{selected_driver_ata}",
                help="Default is the most frequently removed component in the current ATA / date / aircraft scope.",
            )

            exec_parts_linked = link_parts_to_delay(exec_parts, delay_df)
            exec_parts_linked["Linked Problem"] = exec_parts_linked["Delay Problem Group"].where(
                exec_parts_linked["Delay Problem Group"].astype("string").str.strip() != "",
                exec_parts_linked["Delay KeyProblem"],
            )
            selected_exec_detail = exec_parts_linked[
                exec_parts_linked["Part Display"].astype(str) == str(selected_exec_part)
            ].copy().sort_values("Date Removal", ascending=False)

            selected_reason = selected_exec_detail["Real Reason"].astype("string").fillna("").str.strip()
            selected_reason_nonblank = selected_reason[selected_reason != ""]
            top_real_reason = selected_reason_nonblank.value_counts().index[0] if not selected_reason_nonblank.empty else "—"
            unique_tail_count = selected_exec_detail["Register"].replace("", pd.NA).nunique(dropna=True)
            unique_pn_count = selected_exec_detail["Part Number"].replace("", pd.NA).nunique(dropna=True)

            m1, m2, m3, m4 = st.columns(4, gap="small")
            m1.metric("Removal Events", f"{len(selected_exec_detail):,}")
            m2.metric("Aircraft Affected", f"{int(unique_tail_count):,}")
            m3.metric("Unique P/N", f"{int(unique_pn_count):,}")
            m4.metric("Real Reason Available", f"{int((selected_reason != '').sum()):,}/{len(selected_exec_detail):,}")
            if top_real_reason != "—":
                st.caption(f"Most frequent Real Reason: {top_real_reason}")

            exec_detail_cols = [
                "Date Removal", "Notification", "ATA", "A/C Type", "Register", "Equipment",
                "Part Name", "Part Number", "Serial Number", "RemCode", "Real Reason", "NFF",
                "TSN", "TSI", "TSC", "CSN", "CSI", "CSC", "Shop_Visit", "Shop_Finding",
                "Linked Problem", "Delay Problem", "Delay Minutes", "Delay Event Type", "Link Status",
            ]
            exec_detail_cols = [c for c in exec_detail_cols if c in selected_exec_detail.columns]
            exec_detail_show = selected_exec_detail[exec_detail_cols].copy()
            if "Date Removal" in exec_detail_show.columns:
                exec_detail_show["Date Removal"] = pd.to_datetime(exec_detail_show["Date Removal"], errors="coerce").dt.strftime("%Y-%m-%d")

            show_exec_detail_table = st.toggle(
                "Show underlying removal events table",
                value=False,
                key=f"show_exec_detail_table_{selected_driver_ata}_{_safe_file_token(selected_exec_part)}",
                help="Turn on to display the detailed component removal-event table.",
            )
            if show_exec_detail_table:
                st.dataframe(
                    exec_detail_show,
                    use_container_width=True,
                    hide_index=True,
                    height=min(460, 92 + 35 * max(len(exec_detail_show), 1)),
                )

            reason_counts = (
                selected_reason.replace("", "UNSPECIFIED / BLANK")
                .value_counts()
                .rename_axis("Real Reason")
                .reset_index(name="Occurrences")
            )
            if not reason_counts.empty:
                reason_counts["Share %"] = (reason_counts["Occurrences"] / max(len(selected_exec_detail), 1) * 100).round(1)
                with st.expander("Real Reason breakdown", expanded=False):
                    st.dataframe(reason_counts, use_container_width=True, hide_index=True)

            excel_bytes = build_part_detail_excel(
                selected_exec_detail,
                selected_part=selected_exec_part,
                ata=int(selected_driver_ata),
                start_date=start_date,
                end_date=end_date,
            )
            st.download_button(
                "Download selected component detail (Excel)",
                data=excel_bytes,
                file_name=(
                    f"ATA_{selected_driver_ata}_{_safe_file_token(selected_exec_part)}_"
                    f"unscheduled_removal_detail.xlsx"
                ),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key=f"download_exec_part_detail_{selected_driver_ata}",
                help="Excel contains Summary, Removal Details, Real Reason Summary, and Delay Link Summary (when available).",
            )

            st.caption(
                f"Unscheduled definition from removal source: RemCode in {', '.join(sorted(UNSCHEDULED_REMOVAL_CODES))}. "
                "Part Name / Part Number are read directly from the component-removal report."
            )

    # 04 — Only a compact Tail Watch summary remains on the Executive page.
    st.markdown(
        "<div class='executive-section-head'><span class='executive-section-no'>04</span>"
        "<span class='executive-section-title'>Aircraft watch summary</span>"
        "<span class='executive-section-desc'>Highest-priority tails for engineering review</span></div>",
        unsafe_allow_html=True,
    )
    exec_watch = tail_watchlist(scope_df, top_n=5).copy()
    if exec_watch.empty:
        st.info("No aircraft watchlist data for the active scope.")
    else:
        compact_watch_cols = [
            "Status", "Priority Index", "A/C Reg", "A/C Type", "PP Events", "Delay Minutes",
            "Severe", "RTA/RTB/RTO", "Repeat ≤90d", "Top ATA", "Dominant Problem",
        ]
        compact_watch_cols = [c for c in compact_watch_cols if c in exec_watch.columns]
        st.dataframe(exec_watch[compact_watch_cols], use_container_width=True, hide_index=True, height=230)
        st.caption("Priority Index is a triage indicator, not a utilization-normalized reliability rate. Open Aircraft & Repetitive Analysis for full tail history and recurrence review.")



with operational_tab:
    st.markdown("<div class='section-title'>Operational Reliability Events</div>", unsafe_allow_html=True)
    st.caption(
        "A question-driven view of IFSD, RTO, RTB, UER, ERR, SVR and D&C. "
        "Use this page to answer: what happened, when did it happen, how often, and which fleet contributed?"
    )

    if operational_monthly_df.empty:
        st.info(
            "Upload the standard B737 / B777 / A330 fleet workbook(s) under Revenue T/O / Utilization in the sidebar. "
            "The same workbook drives utilization and Operational Events."
        )
        if operational_source_errors:
            with st.expander("Source validation details", expanded=False):
                for _err in operational_source_errors:
                    st.error(_err)
    else:
        loaded_operational_fleets = [f for f in FLEET_ORDER if f in operational_monthly_df["Fleet"].unique().tolist()]
        missing_operational_fleets = [f for f in FLEET_ORDER if f not in loaded_operational_fleets]

        # Keep source status compact; it should not compete with the reliability information itself.
        with st.expander("Fleet source status", expanded=False):
            status_cols = st.columns(3, gap="small")
            for _idx, _fleet in enumerate(FLEET_ORDER):
                with status_cols[_idx]:
                    _fleet_status = [x for x in operational_source_status if x.get("Fleet") == _fleet and x.get("Status") == "Ready"]
                    if _fleet_status:
                        _s = _fleet_status[-1]
                        st.metric(_fleet, "Ready", delta=str(_s.get("Coverage", "")), delta_color="off")
                        st.caption(str(_s.get("Source", "")))
                    else:
                        st.metric(_fleet, "Not loaded")
                        st.caption("Upload fleet workbook")

        if missing_operational_fleets:
            st.caption("All Fleet calculations use only loaded fleets. Common coverage is used when more than one fleet is selected.")

        c1, c2, c3 = st.columns([1.0, 0.9, 1.0], gap="small")
        with c1:
            op_fleet = st.selectbox(
                "Fleet", ["All Fleet"] + loaded_operational_fleets, index=0, key="operational_event_fleet"
            )

        op_view, op_meta = aggregate_operational_view(operational_monthly_df, op_fleet)
        op_rate_view = add_rolling_operational_rates(op_view)
        if op_view.empty:
            st.warning("No operational-event data is available for the selected fleet.")
        else:
            available_years = sorted(pd.to_datetime(op_view["Date"]).dt.year.dropna().astype(int).unique().tolist(), reverse=True)
            with c2:
                op_year = st.selectbox("Year", available_years, index=0, key="operational_event_year")
            with c3:
                op_metric = st.selectbox("Investigate event", EVENT_METRICS, index=0, key="operational_event_metric")

            year_data = op_view[pd.to_datetime(op_view["Date"]).dt.year.eq(int(op_year))].copy().sort_values("Date")
            if year_data.empty:
                st.info("No data is available for the selected year.")
            else:
                op_start = pd.Timestamp(year_data["Date"].min())
                op_end = pd.Timestamp(year_data["Date"].max())
                latest_available = pd.Timestamp(op_view["Date"].max())

                st.markdown("<div class='section-title'>1 · What happened?</div>", unsafe_allow_html=True)
                st.caption(
                    f"Monthly event counts for {op_fleet} · {op_year}. Coverage shown through {op_end.strftime('%b %Y')}. "
                    "A zero means the source explicitly reports no event; blank source cells are treated as No Data."
                )

                summary_cols = st.columns(len(EVENT_METRICS), gap="small")
                for idx, metric in enumerate(EVENT_METRICS):
                    s = pd.to_numeric(year_data[metric], errors="coerce")
                    total = s.sum(min_count=1)
                    occurred_dates = year_data.loc[s.fillna(0).gt(0), "Date"]
                    latest_occ = pd.Timestamp(occurred_dates.max()).strftime("%b") if not occurred_dates.empty else "None"
                    with summary_cols[idx]:
                        st.metric(metric, "—" if pd.isna(total) else f"{int(total)}")
                        st.caption(f"Last: {latest_occ}")

                st.markdown("<div class='section-title'>2 · When did it happen?</div>", unsafe_allow_html=True)
                st.caption("Choose any monthly range to see exactly when IFSD, RTO, RTB, UER, ERR, SVR and D&C occurred.")

                occurrence_months = sorted(pd.to_datetime(op_view["Date"]).dropna().drop_duplicates().tolist())
                default_range_start = op_start if op_start in occurrence_months else occurrence_months[0]
                default_range_end = op_end if op_end in occurrence_months else occurrence_months[-1]

                range_c1, range_c2 = st.columns(2, gap="small")
                with range_c1:
                    occurrence_start = st.selectbox(
                        "From month",
                        occurrence_months,
                        index=occurrence_months.index(default_range_start),
                        format_func=lambda d: pd.Timestamp(d).strftime("%b %Y"),
                        key="operational_occurrence_range_start",
                    )
                valid_end_months = [d for d in occurrence_months if pd.Timestamp(d) >= pd.Timestamp(occurrence_start)]
                if default_range_end not in valid_end_months:
                    default_range_end = valid_end_months[-1]
                with range_c2:
                    occurrence_end = st.selectbox(
                        "To month",
                        valid_end_months,
                        index=valid_end_months.index(default_range_end),
                        format_func=lambda d: pd.Timestamp(d).strftime("%b %Y"),
                        key="operational_occurrence_range_end",
                    )

                occurrence_start = pd.Timestamp(occurrence_start)
                occurrence_end = pd.Timestamp(occurrence_end)
                plot(
                    _operational_heatmap_figure(op_view, occurrence_start, occurrence_end),
                    f"operational_occurrence_{op_fleet}_{occurrence_start:%Y%m}_{occurrence_end:%Y%m}",
                )
                selected_month_count = int(
                    op_view[op_view["Date"].between(occurrence_start, occurrence_end)]["Date"].nunique()
                )
                st.caption(
                    f"Showing {selected_month_count} month(s), {occurrence_start.strftime('%b %Y')} to {occurrence_end.strftime('%b %Y')}. "
                    "Numbers are event counts; '—' means confirmed zero event."
                )

                occurrence_text, metric_total, event_months, latest_occurrence, peak_text = _event_occurrence_text(
                    op_view, op_metric, op_start, op_end
                )

                st.markdown(f"<div class='section-title'>3 · {op_metric} · occurrence detail</div>", unsafe_allow_html=True)
                if metric_total > 0:
                    st.success(f"{op_metric} occurred in: {occurrence_text}")
                else:
                    st.info(f"{op_metric}: {occurrence_text}")

                d1, d2, d3, d4 = st.columns(4, gap="small")
                d1.metric(f"{op_metric} events", f"{metric_total}", help=f"Total events during {op_year}")
                d2.metric("Occurrence months", f"{event_months}", help="Number of months with at least one event")
                d3.metric("Last occurrence", latest_occurrence)
                d4.metric("Peak month", peak_text)

                plot(
                    _operational_event_trend_figure(operational_monthly_df, op_fleet, op_metric, op_start, op_end),
                    f"operational_monthly_{op_fleet}_{op_metric}_{op_year}",
                )
                st.caption("Event-count axis uses whole numbers only. Labels above non-zero bars show the monthly count directly.")


                if op_fleet == "All Fleet" and len(loaded_operational_fleets) > 1:
                    st.markdown("<div class='section-title'>4 · Which fleet contributed?</div>", unsafe_allow_html=True)
                    plot(
                        _operational_fleet_contribution_figure(operational_monthly_df, op_metric, op_start, op_end),
                        f"operational_contribution_{op_metric}_{op_year}",
                    )
                    st.caption("Counts are summed by fleet for the selected year. This chart answers contributor, not rate performance.")

                if op_metric == "D&C":
                    st.markdown("<div class='section-title'>5 · What drives D&C?</div>", unsafe_allow_html=True)
                    if operational_dc_ata_df.empty:
                        st.info("D&C per ATA data is not available in the loaded workbook(s).")
                    else:
                        plot(
                            _dc_ata_figure(operational_dc_ata_df, op_fleet, op_start, op_end),
                            f"operational_dc_ata_{op_fleet}_{op_year}",
                        )
                        st.caption("ATA 71–80 only. The workbook total row (90) is excluded because it is a monthly subtotal, not ATA 90.")

                if op_fleet == "All Fleet" and len(op_meta.get("fleets", [])) > 1:
                    st.caption(
                        "All Fleet rate = total event numerator ÷ total FH/FC exposure across the common fleet coverage. "
                        "Fleet rates are never averaged."
                    )

                with st.expander("Source validation & reconciliation", expanded=False):
                    if operational_source_status:
                        st.dataframe(pd.DataFrame(operational_source_status), use_container_width=True, hide_index=True)
                    if operational_source_warnings:
                        for _warning in operational_source_warnings:
                            st.warning(_warning)
                    if operational_source_errors:
                        for _error in operational_source_errors:
                            st.error(_error)
                    if not operational_reconciliation_df.empty:
                        st.markdown("**D&C total vs ATA 71–80 reconciliation exceptions**")
                        _recon_show = operational_reconciliation_df.copy()
                        _recon_show["Month"] = pd.to_datetime(_recon_show["Date"]).dt.strftime("%b %Y")
                        _cols = [c for c in ["Fleet", "Month", "D&C Total", "ATA 71-80 Total", "Difference", "Source File"] if c in _recon_show.columns]
                        st.dataframe(_recon_show[_cols], use_container_width=True, hide_index=True)
                    else:
                        st.success("D&C monthly totals reconcile with the ATA 71–80 breakdown for the loaded active coverage.")


with intelligence_tab:
    st.markdown("<div class='section-title'>Engineering Intelligence · Decision Support</div>", unsafe_allow_html=True)
    st.caption(
        "Derived analytics use the existing delay export only. Raw Problem, KeyProblem, Rectification, and Chronology remain unchanged; "
        "taxonomy and recurrence fields are review aids, not authoritative maintenance findings."
    )

    health = classification_health(scope_df)
    h1, h2, h3, h4, h5 = st.columns(5, gap="small")
    h1.metric("PP Events", f"{health['total']:,}")
    h2.metric("Classified KeyProblem", f"{health['classified']:,}")
    h3.metric("Suggested from Text", f"{health['suggested']:,}")
    h4.metric("Needs Classification", f"{health['needs']:,}")
    h5.metric(
        "Actionable Coverage",
        "—" if health.get("actionable_coverage_pct") is None else f"{health['actionable_coverage_pct']:.1f}%",
    )

    st.markdown("<div class='section-title'>Priority Pattern Detection</div>", unsafe_allow_html=True)
    fi_col, rep_col = st.columns([1.05, .95], gap="small")
    with fi_col:
        fi_source = analysis_df
        fi = frequency_impact_data(fi_source)
        plot(frequency_impact_scatter(fi), "intel_frequency_impact")
        st.caption("Upper-right = high-frequency + high-impact; upper-left = low-frequency but high-impact. Bubble size = aircraft affected.")
    with rep_col:
        repeat_window = st.selectbox("Repetitive-defect window", [30, 90, 365], index=1, key="repeat_window")
        repeat_source = analysis_df
        repeat_summary = repetitive_defect_summary(repeat_source, window_days=repeat_window, min_occurrences=2)
        plot(repeat_defect_bar(repeat_summary, window_days=repeat_window, top_n=10), "intel_repeat_bar")

    st.markdown("<div class='section-title'>Repetitive Defect Review</div>", unsafe_allow_html=True)
    if repeat_summary.empty:
        st.info("No repetitive defects detected with the selected recurrence window.")
    else:
        rep_table = repeat_summary.copy()
        for col in ["First Occurrence", "Last Occurrence"]:
            rep_table[col] = pd.to_datetime(rep_table[col], errors="coerce").dt.strftime("%Y-%m-%d")
        st.dataframe(rep_table, use_container_width=True, hide_index=True, height=360)

    st.markdown("<div class='section-title'>Aircraft / Tail Watchlist & Tail Detail</div>", unsafe_allow_html=True)
    watch = tail_watchlist(analysis_df, top_n=50).copy()
    if watch.empty:
        st.info("No aircraft watchlist data for current analysis filters.")
    else:
        w_left, w_right = st.columns([1.15, .85], gap="small")
        with w_left:
            watch_display = watch.copy()
            for col in ["First Event", "Last Event"]:
                watch_display[col] = pd.to_datetime(watch_display[col], errors="coerce").dt.strftime("%Y-%m-%d")
            st.dataframe(watch_display, use_container_width=True, hide_index=True, height=430)
        with w_right:
            selected_tail = st.selectbox("Tail detail", watch["A/C Reg"].tolist(), key="tail_detail")
            tail_row = watch.loc[watch["A/C Reg"] == selected_tail].iloc[0]
            t1, t2, t3 = st.columns(3, gap="small")
            t1.metric("Priority", f"{tail_row['Priority Index']:.1f}", str(tail_row["Status"]))
            t2.metric("PP Events", f"{int(tail_row['PP Events'])}")
            t3.metric("Delay", f"{tail_row['Delay Minutes']:,.0f} min")
            st.markdown(
                f"**Top ATA:** {tail_row['Top ATA']}  \n"
                f"**Dominant problem:** {tail_row['Dominant Problem']}  \n"
                f"**Repeat ≤90d:** {int(tail_row['Repeat ≤90d'])}  \n"
                f"**Severe:** {int(tail_row['Severe'])} · **RTA/RTB/RTO:** {int(tail_row['RTA/RTB/RTO'])}"
            )
            tail_events = analysis_df[(analysis_df["Powerplant Flag"] == "Powerplant") & (analysis_df["A/C Reg"] == selected_tail)].copy()
            tail_cols = ["Date", "ATA", "Sub ATA", "Tech Dur", "Event Type", "Problem Group", "KeyProblem", "Rectification Action", "Problem"]
            tail_events = tail_events.sort_values("Date", ascending=False)[tail_cols]
            tail_events["Date"] = pd.to_datetime(tail_events["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
            st.dataframe(tail_events, use_container_width=True, hide_index=True, height=300)
        st.caption("Bad-actor status is triage only. Fair reliability comparison across tails requires FH/FC or departures by registration.")

    st.markdown("<div class='section-title'>Recurrence After Rectification</div>", unsafe_allow_html=True)
    recurrence_days = st.selectbox("Recurrence observation window", [7, 30, 90], index=1, key="rect_recur_days")
    rect_eff = rectification_effectiveness(analysis_df, recurrence_days=recurrence_days)
    if rect_eff.empty:
        st.info("Not enough follow-up observation time to evaluate recurrence after rectification in this scope.")
    else:
        st.dataframe(rect_eff, use_container_width=True, hide_index=True, height=320)
        st.caption(
            "Descriptive recurrence only: association after a recorded action does not prove that the action caused or failed to prevent the subsequent event. "
            "The last events near the end of the scope are excluded when they do not have enough observation days."
        )

    st.markdown("<div class='section-title'>ATA → Sub ATA → System / Component / Failure Mode</div>", unsafe_allow_html=True)
    available_pp_atas = sorted(int(x) for x in analysis_df.loc[analysis_df["Powerplant Flag"] == "Powerplant", "ATA"].dropna().unique())
    if available_pp_atas:
        drill_ata = st.selectbox("ATA chapter for drill-down", available_pp_atas, key="drill_ata")
        d1, d2 = st.columns([.85, 1.15], gap="small")
        with d1:
            sub = subata_summary(analysis_df, drill_ata, metric=chart_metric)
            st.dataframe(sub, use_container_width=True, hide_index=True, height=330)
        with d2:
            tax = problem_taxonomy_summary(analysis_df[analysis_df["ATA"] == drill_ata], metric=chart_metric, top_n=30)
            st.dataframe(tax, use_container_width=True, hide_index=True, height=330)
    else:
        st.info("No Powerplant ATA available for drill-down.")

    st.markdown("<div class='section-title'>Operational Impact Profile</div>", unsafe_allow_html=True)
    op = operational_impact_by_ata(analysis_df)
    if op.empty:
        st.info("No operational-impact data for the active filters.")
    else:
        st.dataframe(op, use_container_width=True, hide_index=True, height=320)
        st.caption("RTA/RTB/RTO share describes consequence among recorded delay events. A true interruption rate requires departures exposure.")

    st.markdown("<div class='section-title'>Multi-Dimensional Pareto & Concentration</div>", unsafe_allow_html=True)
    dim_map = {
        "Aircraft Registration": "A/C Reg",
        "Departure Station": "Sta Dep",
        "Route": "Route",
        "Rectification Action": "Rectification Action",
        "Engine Position": "Engine Position",
        "System": "System",
        "Component": "Component",
        "Problem Group": "Problem Group",
    }
    pareto_source = analysis_df
    p1, p2 = st.columns([.32, .68], gap="small")
    with p1:
        dim_label = st.selectbox("Analyze by", list(dim_map), key="pareto_dimension")
        pareto_metric = st.radio("Pareto metric", ["Delay Minutes", "Events"], horizontal=True, key="pareto_metric")
        dim = dim_map[dim_label]
        pareto = pareto_80_20(pareto_source, dim, pareto_metric)
        st.metric("Categories", pareto["categories"])
        st.metric("Top 20% categories", pareto["top_20_categories"])
        st.metric("Contribution of top 20%", "—" if pareto["contribution_pct"] is None else f"{pareto['contribution_pct']:.1f}%")
    with p2:
        conc = concentration_summary(pareto_source, dim_map[dim_label], metric=pareto_metric, top_n=15)
        plot(concentration_bar(conc, dim_map[dim_label], pareto_metric, 15, f"{dim_label} Pareto"), "intel_multi_pareto")

    st.markdown("<div class='section-title'>Engine Position Extraction</div>", unsafe_allow_html=True)
    engine_pos_source = analysis_df
    eng = engine_position_summary(engine_pos_source, metric=chart_metric)
    if eng.empty:
        st.info("No engine-position text could be evaluated.")
    else:
        e1, e2 = st.columns([.65, .35], gap="small")
        with e1:
            plot(concentration_bar(eng, "Engine Position", chart_metric, 10, "Engine Position · Text-Derived"), "intel_engine_position")
        with e2:
            st.dataframe(eng, use_container_width=True, hide_index=True, height=330)
        st.caption("ENG 1 / ENG 2 is extracted from free text and should be treated as a derived field; UNKNOWN means the source wording did not identify position.")

    st.markdown("<div class='section-title'>Classification Coverage & Review Queue</div>", unsafe_allow_html=True)
    review = needs_classification(scope_df).copy()
    if review.empty:
        st.success("All Powerplant events in the active scope have a usable KeyProblem classification.")
    else:
        review["Date"] = pd.to_datetime(review["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        st.dataframe(review, use_container_width=True, hide_index=True, height=400)
        st.download_button(
            "Download classification review queue (CSV)",
            review.to_csv(index=False).encode("utf-8-sig"),
            file_name="powerplant_needs_classification.csv",
            mime="text/csv",
            key="download_classification_queue",
        )
        st.caption("Suggested groups come from transparent keyword rules. Engineer validation remains required before using them as controlled taxonomy.")


with ata_tab:
    st.markdown("<div class='section-title'>ATA Burden & Deterioration Analysis</div>", unsafe_allow_html=True)
    a1, a2, a3 = st.columns(3, gap="small")
    a1.metric(
        "Official PP Delay Contribution",
        "—" if kpi.pp_delay_contribution_pct is None else f"{kpi.pp_delay_contribution_pct:.1f}%",
        help="Share of all approved technical-delay events that are Powerplant-related.",
    )
    a2.metric(
        f"ATA {kpi.contribution_ata} Share of Powerplant" if kpi.contribution_ata is not None else "ATA Share of Powerplant",
        "—" if kpi.ata_contribution_pct is None else f"{kpi.ata_contribution_pct:.1f}%",
        help=f"Basis: {kpi.contribution_basis}. This is an internal PP breakdown, not the official PP Delay Contribution.",
    )
    a3.metric("Powerplant ATA Chapters in Scope", f"{kpi.ata_chapter_count}")
    left, right = st.columns([1.08, 0.92], gap="small")
    with left:
        ata_metric = st.selectbox(
            "Top ATA metric",
            ["Delay Minutes", "Events"],
            index=1 if chart_metric == "Events" else 0,
            key="ata_metric_detail",
        )
        ata_chart_source = analysis_df
        summary = ata_summary(ata_chart_source, ata_metric)
        plot(top_ata_bar(summary, ata_metric, top_n=11, title="ATA Share of Powerplant"), "ata_detail_top_ata")
    with right:
        fleet_metric = st.selectbox(
            "Fleet comparison metric",
            ["PP Delay Minutes", "PP Events"],
            index=1 if chart_metric == "Events" else 0,
            key="fleet_metric_detail",
        )
        fleet_chart_source = scope_df
        plot(fleet_bar(fleet_summary(fleet_chart_source), metric=fleet_metric, title="Fleet Burden Comparison"), "ata_detail_fleet")
        st.caption("Fleet comparison uses the date/station/route scope and intentionally ignores the dedicated ATA analysis filter.")

    st.markdown("<div class='section-title'>3-Year ATA Deterioration</div>", unsafe_allow_html=True)
    heatmap_metric = st.selectbox(
        "3-year heatmap metric",
        ["Delay Minutes", "Events"],
        index=1 if chart_metric == "Events" else 0,
        key="heatmap_metric_detail",
    )
    heatmap_source = scope_df
    latest_year = int(heatmap_source["Year"].dropna().max()) if not heatmap_source.empty and not heatmap_source["Year"].dropna().empty else None
    matrix = ata_deterioration_matrix(heatmap_source, latest_year, metric=heatmap_metric)
    h1, h2 = st.columns([1.25, 1], gap="small")
    with h1:
        plot(
            ata_deterioration_heatmap(matrix, metric=heatmap_metric, title="ATA Deterioration Heatmap"),
            "ata_detail_heatmap",
        )
    with h2:
        if matrix.empty:
            st.info("Not enough dated data to build the matrix.")
        else:
            styled = matrix.style.format({"YoY %": lambda x: "—" if pd.isna(x) else f"{x:+.1f}%"})
            st.dataframe(styled, use_container_width=True, hide_index=True, height=292)

    st.markdown("<div class='section-title'>Key Problem Analysis</div>", unsafe_allow_html=True)
    k1, k2 = st.columns([1, 1], gap="small")
    with k1:
        problem_metric = st.selectbox(
            "Problem ranking basis",
            ["Delay Minutes", "Events"],
            index=1 if chart_metric == "Events" else 0,
            key="problem_metric",
        )
        top_n = st.slider("Number of Key Problems", 5, 25, 10, key="top_problem_n")
        key_problem_source = analysis_df
        key_all = key_problem_summary(key_problem_source, 10000, problem_metric)
        key_summary = key_all.head(top_n)
        plot(
            key_problem_bar(key_all, top_n=top_n, metric=problem_metric, title="Top Key Problems"),
            "ata_detail_key_problems",
        )
    with k2:
        st.dataframe(key_summary, use_container_width=True, hide_index=True, height=340)

    st.markdown(
        "<div class='method-note'>Standardize KeyProblem for management Pareto. Keep free-text Problem / Rectification / Chronology for engineering investigation because maintenance wording naturally varies.</div>",
        unsafe_allow_html=True,
    )

    support_col, station_col = st.columns(2, gap="small")
    with support_col:
        st.markdown("<div class='section-title'>Severity Distribution</div>", unsafe_allow_html=True)
        severity_source = analysis_df
        plot(severity_donut(severity_source, metric=chart_metric), "ata_detail_severity")
    with station_col:
        st.markdown("<div class='section-title'>Station Concentration · Departure Station</div>", unsafe_allow_html=True)
        station = station_summary(analysis_df, 15)
        if station.empty:
            st.info("No station data for the selected scope.")
        else:
            st.dataframe(station, use_container_width=True, hide_index=True, height=360)
            st.caption("Descriptive only: traffic volume, route mix, and maintenance capability can confound station comparisons.")



with parts_tab:
    st.markdown("<div class='section-title'>Unscheduled Part Replacement Analysis</div>", unsafe_allow_html=True)
    st.caption(
        "Powerplant only: ATA 49 and ATA 71–80. This page reads Part Name / Part Number directly from the component-removal report. "
        "It does not infer replaced parts from Rectification text."
    )

    if part_df.empty:
        st.info(
            "No Component Removal / Part Replacement source is loaded. Upload the removal report from the sidebar or Input Data page."
        )
    else:
        pp_unsched = part_scope_df.copy()
        total_pp_parts = len(pp_unsched)
        unique_parts = pp_unsched["Part Display"].replace("", pd.NA).nunique(dropna=True) if not pp_unsched.empty else 0
        affected_tails = pp_unsched["Register"].replace("", pd.NA).nunique(dropna=True) if not pp_unsched.empty else 0
        direct_links = int((linked_part_scope_df.get("Link Status", pd.Series(dtype="string")) == "DIRECT MATCH").sum()) if not linked_part_scope_df.empty else 0
        link_pct = (direct_links / total_pp_parts * 100) if total_pp_parts else 0.0

        k1, k2, k3, k4 = st.columns(4, gap="small")
        k1.metric("Unscheduled PP Removals", f"{total_pp_parts:,}")
        k2.metric("Unique Part Names", f"{unique_parts:,}")
        k3.metric("Aircraft Affected", f"{affected_tails:,}")
        k4.metric("Notif → Delay Link", "—" if not total_pp_parts else f"{link_pct:.0f}%")

        if pp_unsched.empty:
            st.warning(
                "Component-removal file is loaded, but there are no Powerplant unscheduled rows in the active date / aircraft scope. "
                f"Current unscheduled code mapping: {', '.join(sorted(UNSCHEDULED_REMOVAL_CODES))}."
            )
        else:
            ata_values = sorted(int(x) for x in pp_unsched["ATA"].dropna().unique().tolist())
            f1, f2 = st.columns([0.34, 0.66], gap="small")
            with f1:
                part_ata_choice = st.selectbox(
                    "ATA chapter",
                    ["All Powerplant"] + [f"ATA {ata}" for ata in ata_values],
                    key="part_analysis_ata",
                )
            selected_part_ata = None if part_ata_choice == "All Powerplant" else int(part_ata_choice.split()[-1])

            ata_parts = pp_unsched if selected_part_ata is None else pp_unsched[pp_unsched["ATA"] == selected_part_ata].copy()
            ata_linked = link_parts_to_delay(ata_parts, delay_df)
            ata_linked["Linked Problem"] = ata_linked["Delay Problem Group"].where(
                ata_linked["Delay Problem Group"].astype("string").str.strip() != "",
                ata_linked["Delay KeyProblem"],
            )
            ata_linked["Linked Problem"] = ata_linked["Linked Problem"].astype("string").fillna("").str.strip()

            linked_problem_options = sorted(
                x for x in ata_linked.loc[ata_linked["Link Status"] == "DIRECT MATCH", "Linked Problem"].unique().tolist() if x
            )
            with f2:
                problem_choice = st.selectbox(
                    "Key problem linkage",
                    ["All unscheduled removals"] + linked_problem_options,
                    key="part_analysis_problem",
                    help=(
                        "Key problem linkage uses Notification ↔ Notif when one unique technical-delay event is found. "
                        "If no direct match exists, ATA-level part frequency remains valid but problem-level linkage is not claimed."
                    ),
                )

            if problem_choice == "All unscheduled removals":
                working_parts = ata_linked.copy()
            else:
                working_parts = ata_linked[
                    (ata_linked["Link Status"] == "DIRECT MATCH") & (ata_linked["Linked Problem"] == problem_choice)
                ].copy()

            if working_parts.empty:
                st.info("No part-removal rows match the selected ATA / key-problem combination.")
            else:
                working_parts_chart = working_parts
                summary = part_summary(working_parts_chart).head(15).copy()
                summary["Top Reason"] = summary["Part"].map(lambda p: top_reason_for_part(working_parts, p))
                summary["Part Short"] = summary["Part"].astype(str).map(lambda x: x if len(x) <= 55 else x[:52] + "...")

                scope_label = "Powerplant" if selected_part_ata is None else f"ATA {selected_part_ata}"
                if problem_choice != "All unscheduled removals":
                    scope_label += f" · {problem_choice}"

                left, right = st.columns([1.08, 0.92], gap="small")
                with left:
                    fig = px.bar(
                        summary.sort_values("Removals"),
                        x="Removals",
                        y="Part Short",
                        orientation="h",
                        text="Removals",
                        custom_data=["Part", "Aircraft", "Part Numbers", "Share %"],
                        title=f"{scope_label} · Most Frequently Removed / Replaced Parts",
                    )
                    fig.update_traces(
                        textposition="outside",
                        hovertemplate=(
                            "<b>%{customdata[0]}</b><br>"
                            "Unscheduled removals: %{x}<br>"
                            "Aircraft affected: %{customdata[1]}<br>"
                            "Unique P/N: %{customdata[2]}<br>"
                            "Share: %{customdata[3]:.1f}%<extra></extra>"
                        ),
                    )
                    fig.update_layout(xaxis_title="Unscheduled removals", yaxis_title="Part")
                    plot(fig, "parts_top_frequency")

                with right:
                    show = summary[["Part", "Removals", "Share %", "Aircraft", "Part Numbers", "Latest Removal", "Top Reason"]].copy()
                    show["Share %"] = show["Share %"].round(1)
                    show["Latest Removal"] = pd.to_datetime(show["Latest Removal"], errors="coerce").dt.strftime("%Y-%m-%d")
                    st.markdown("<div class='section-title'>Top Part Replacement / Removal</div>", unsafe_allow_html=True)
                    st.dataframe(show, use_container_width=True, hide_index=True, height=405)

                # Direct relationship: Key Problem -> Part Changed.
                direct = ata_linked[(ata_linked["Link Status"] == "DIRECT MATCH") & (ata_linked["Linked Problem"] != "")].copy()
                if not direct.empty:
                    st.markdown("<div class='section-title'>Key Problem → Part Changed</div>", unsafe_allow_html=True)
                    kp_part = (
                        direct.groupby(["Linked Problem", "Part Display"], dropna=False)
                        .agg(Removals=("Part Event ID", "count"), Aircraft=("Register", lambda s: s.replace("", pd.NA).nunique(dropna=True)))
                        .reset_index()
                        .rename(columns={"Linked Problem": "Key Problem", "Part Display": "Part"})
                        .sort_values(["Removals", "Aircraft"], ascending=False)
                    )
                    st.dataframe(kp_part.head(30), use_container_width=True, hide_index=True, height=340)
                    st.caption(
                        "This table is shown only for direct unique Notification ↔ Notif matches. No fuzzy join is used."
                    )
                else:
                    st.info(
                        "No direct unique Notification ↔ Notif link is available in the active scope, so the dashboard does not claim a Key Problem → Part relationship. "
                        "ATA-level part frequency above remains sourced directly from the removal report."
                    )

                st.markdown("<div class='section-title'>Removal Event Records</div>", unsafe_allow_html=True)
                event_cols = [
                    "Notification", "Date Removal", "ATA", "A/C Type", "Register", "Part Name", "Part Number",
                    "Serial Number", "RemCode", "Real Reason", "Shop_Finding", "Linked Problem", "Link Status",
                ]
                available_cols = [c for c in event_cols if c in working_parts.columns]
                detail = working_parts[available_cols].copy().sort_values("Date Removal", ascending=False)
                detail["Date Removal"] = pd.to_datetime(detail["Date Removal"], errors="coerce").dt.strftime("%Y-%m-%d")
                st.dataframe(detail, use_container_width=True, hide_index=True, height=420)

                if not summary.empty:
                    part_export_options = summary["Part"].astype(str).tolist()
                    export_part_choice = st.selectbox(
                        "Component for detailed Excel export",
                        part_export_options,
                        index=0,
                        key="parts_tab_export_component",
                    )
                    export_part_rows = working_parts[
                        working_parts["Part Display"].astype(str) == str(export_part_choice)
                    ].copy().sort_values("Date Removal", ascending=False)
                    export_bytes = build_part_detail_excel(
                        export_part_rows,
                        selected_part=export_part_choice,
                        ata=selected_part_ata,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    st.download_button(
                        "Download component investigation detail (Excel)",
                        data=export_bytes,
                        file_name=(
                            f"{('ATA_' + str(selected_part_ata)) if selected_part_ata is not None else 'Powerplant'}_"
                            f"{_safe_file_token(export_part_choice)}_removal_detail.xlsx"
                        ),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key="parts_tab_download_component_excel",
                    )

                st.caption(
                    f"Unscheduled source rule: RemCode ∈ {{{', '.join(sorted(UNSCHEDULED_REMOVAL_CODES))}}}. "
                    "If your organization uses different RemCode definitions, update UNSCHEDULED_REMOVAL_CODES in src/config.py."
                )


with events_tab:
    st.markdown("<div class='section-title'>Event Explorer</div>", unsafe_allow_html=True)
    st.caption(f"{len(analysis_df):,} records after all active filters. Use keyword search in the sidebar for free-text investigation.")

    table_cols = [
        "Date", "Notif", "A/C Type", "A/C Reg", "Route", "Flight No", "Tech Dur", "ATA", "Sub ATA",
        "System Group", "Engine Position", "Event Type", "Problem Group", "System", "Component", "Failure Mode",
        "KeyProblem Classification", "KeyProblem", "Problem", "Rectification Action", "Rectification", "Chronology",
    ]
    event_table = analysis_df.sort_values(["Date", "Tech Dur"], ascending=[False, False])[table_cols].copy()
    event_table["Date"] = event_table["Date"].dt.strftime("%Y-%m-%d")
    st.dataframe(event_table, use_container_width=True, hide_index=True, height=480)

    if not analysis_df.empty:
        st.markdown("<div class='section-title'>Event Detail</div>", unsafe_allow_html=True)
        choices = analysis_df.sort_values("Date", ascending=False).copy()

        def event_label(row) -> str:
            date_text = row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "Date N/A"
            dur = f"{row['Tech Dur']:.0f}" if pd.notna(row["Tech Dur"]) else "—"
            ata = int(row["ATA"]) if pd.notna(row["ATA"]) else "—"
            problem = row["KeyProblem"] or row["Problem"] or "No description"
            return f"{date_text} | {row['A/C Reg']} | ATA {ata} | {dur} min | {problem}"

        choices["_label"] = choices.apply(event_label, axis=1)
        selected_label = st.selectbox("Choose an event", choices["_label"].tolist(), key="event_detail_select")
        row = choices.loc[choices["_label"] == selected_label].iloc[0]
        a, b, c, d = st.columns(4, gap="small")
        a.metric("Aircraft", row["A/C Type"] or "—")
        b.metric("Registration", row["A/C Reg"] or "—")
        ata_text = f"{int(row['ATA']) if pd.notna(row['ATA']) else '—'} / {row['Sub ATA'] if pd.notna(row['Sub ATA']) else '—'}"
        c.metric("ATA / Sub ATA", ata_text)
        d.metric("Tech Dur", "—" if pd.isna(row["Tech Dur"]) else f"{row['Tech Dur']:.0f} min")
        st.markdown(f"**Route / Flight:** {row['Route'] or '—'} · {row['Flight No'] or '—'} &nbsp;&nbsp; **Event:** {row['Event Type'] or '—'}")
        st.markdown(
            f"**Derived engineering fields:** {row.get('Problem Group', '—')} · {row.get('System', '—')} · "
            f"{row.get('Component', '—')} · {row.get('Failure Mode', '—')} · {row.get('Engine Position', '—')}"
        )
        for title, column in [
            ("Problem", "Problem"),
            ("Key Problem", "KeyProblem"),
            ("Classification / Normalized Problem Group", "Problem Group"),
            ("Rectification", "Rectification"),
            ("Rectification Action", "Rectification Action"),
            ("Chronology", "Chronology"),
        ]:
            with st.expander(title, expanded=(title in {"Problem", "Key Problem"})):
                st.write(row[column] or "—")


if False:  # Hidden legacy Data page; operational uploads remain in the sidebar.
    st.markdown("<div class='section-title'>Input / Update Data Center</div>", unsafe_allow_html=True)
    st.caption("Use this page for routine updates. Saved files are picked up automatically on the next rerun; historical files are appended, not overwritten.")

    i1, i2, i3, i4, i5 = st.columns(5, gap="small")
    i1.metric("Stored Delay Files", f"{len(discover_delay_files(DELAY_DIR)):,}")
    i2.metric("Delay Rows", f"{len(delay_df):,}")
    i3.metric("Aircraft Types", f"{delay_df['A/C Type'].replace('', pd.NA).nunique():,}")
    i4.metric("Exposure", "READY" if not exposure_df.empty else "NOT LOADED")
    i5.metric("Part Removal Rows", f"{len(part_df):,}" if not part_df.empty else "0")

    delay_box, exposure_box, support_box = st.columns([1.15, 1.0, 1.0], gap="small")
    with delay_box:
        st.markdown("### 01 · All-ATA Technical Delay Data")
        page_delay_uploads = st.file_uploader(
            "Upload one or many all-ATA technical-delay Excel / CSV files",
            type=["xlsx", "xls", "csv"],
            accept_multiple_files=True,
            key="page_delay_uploads",
            help=(
                "Official PP Delay Contribution requires all approved ATA rows. Powerplant ATA 49 & 71–80 keep full engineering detail; "
                "other ATA may be denominator-only rows as long as Date, A/C Type, Tech Dur, and ATA are available."
            ),
        )
        if page_delay_uploads:
            remember_uploads("reliability_page_delay_session_uploads", page_delay_uploads)
        else:
            page_delay_uploads = restore_uploads("reliability_page_delay_session_uploads")
        if page_delay_uploads:
            st.info(f"{len(page_delay_uploads)} file(s) selected for this browser session.")
            if st.button("Save All-ATA Delay File(s)", use_container_width=True, type="primary", key="page_save_delay"):
                saved, errors = save_uploads(page_delay_uploads)
                if saved:
                    st.success(f"{saved} file(s) saved to data/delay. Refreshing dashboard...")
                for error in errors:
                    st.error(error)
                if saved:
                    st.cache_data.clear()
                    st.rerun()

    with exposure_box:
        st.markdown("### 02 · Fleet Reliability / Utilization Workbooks")
        page_exposure_uploads = st.file_uploader(
            "Upload B737 / B777 / A330 reliability-utilization workbook(s)",
            type=["xlsx", "xls", "csv"],
            accept_multiple_files=True,
            key="page_exposure_upload",
            help=(
                "Satu workbook fleet dapat dipakai sekaligus untuk Revenue T/O / utilization dan tab Operational Events. "
                "Exposure dibaca dari Utilization!B:N; event dibaca dari raw IFSD/RTO/RTB/UER/ERR/SVR/D&C sheets. "
                "Nama file sebaiknya memuat B737, B777, A330 atau engine family agar mapping otomatis."
            ),
        )
        if page_exposure_uploads:
            remember_uploads("reliability_page_exposure_session_uploads", page_exposure_uploads)
        else:
            page_exposure_uploads = restore_uploads("reliability_page_exposure_session_uploads")
        if page_exposure_uploads:
            st.info(f"{len(page_exposure_uploads)} fleet workbook(s) selected.")
            if st.button("Save Revenue T/O File(s)", use_container_width=True, key="page_save_exposure"):
                saved, errors = save_exposure_uploads(page_exposure_uploads)
                if saved:
                    st.success(f"{saved} utilization file(s) saved. Refreshing dashboard...")
                for error in errors:
                    st.error(error)
                if saved:
                    st.cache_data.clear()
                    st.rerun()

        exposure_template = "Year-Month,A/C Type,Revenue T/O,Flight Hours,Flight Cycles\n2026-01,TYPE A,0,0,0\n"
        st.download_button(
            "Download Revenue T/O Template",
            exposure_template.encode("utf-8-sig"),
            file_name="revenue_takeoff_template.csv",
            mime="text/csv",
            use_container_width=True,
            key="page_exposure_template",
        )

    with support_box:
        st.markdown("### 03 · Calculation Support Workbook")
        page_support_upload = st.file_uploader(
            "Upload historical Powerplant calculation workbook (optional)",
            type=["xlsx", "xls"],
            accept_multiple_files=False,
            key="page_support_upload",
            help="Parses All Fleet / fleet annual rows for PP Events, All ATA Delay, Contribution, Revenue T/O, and Delay Rate.",
        )
        if page_support_upload is not None:
            remember_upload("reliability_page_support_session_upload", page_support_upload)
        else:
            page_support_upload = restore_upload("reliability_page_support_session_upload")
        if page_support_upload is not None:
            if st.button("Save Support Workbook", use_container_width=True, key="page_save_support"):
                target, error = save_support_upload(page_support_upload)
                if error:
                    st.error(error)
                else:
                    st.success(f"Saved as {target.name}. Refreshing dashboard...")
                    st.cache_data.clear()
                    st.rerun()
        st.caption(f"Stored support workbook(s): {len(discover_delay_files(SUPPORT_DIR))}")

    st.markdown("<div class='section-title'>04 · Component Removal / Part Replacement</div>", unsafe_allow_html=True)
    st.caption(
        "Use the component-removal report to identify which Powerplant parts are most frequently changed/removed unscheduled. "
        f"Current unscheduled RemCode mapping: {', '.join(sorted(UNSCHEDULED_REMOVAL_CODES))}."
    )
    page_part_uploads = st.file_uploader(
        "Upload one or many Component Removal Excel / CSV files",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
        key="page_part_uploads",
        help="Expected fields include Notification, ATA, Part Name, Part Number, RemCode, Date Removal, A/C Type/Register.",
    )
    if page_part_uploads:
        remember_uploads("reliability_page_parts_session_uploads", page_part_uploads)
    else:
        page_part_uploads = restore_uploads("reliability_page_parts_session_uploads")
    if page_part_uploads:
        st.info(f"{len(page_part_uploads)} component-removal file(s) selected.")
        if st.button("Save Component Removal File(s)", use_container_width=True, key="page_save_parts"):
            saved, errors = save_part_uploads(page_part_uploads)
            if saved:
                st.success(f"{saved} file(s) saved to data/parts. Refreshing dashboard...")
            for error in errors:
                st.error(error)
            if saved:
                st.cache_data.clear()
                st.rerun()
    st.caption(f"Stored component-removal file(s): {len(discover_part_files(PARTS_DIR))}")

    st.markdown("<div class='section-title'>Current Source Inventory</div>", unsafe_allow_html=True)
    inventory_rows = []
    inventory_rows += [{"Source Type": "All-ATA Technical Delay", "File": x} for x in load_meta.get("sources", [])]
    inventory_rows += [{"Source Type": "Revenue T/O / Exposure", "File": str(x)} for x in discover_delay_files(EXPOSURE_DIR)]
    inventory_rows += [{"Source Type": "Calculation Support", "File": str(x)} for x in discover_delay_files(SUPPORT_DIR)]
    inventory_rows += [{"Source Type": "Component Removal / Part Replacement", "File": str(x)} for x in discover_part_files(PARTS_DIR)]
    source_inventory = pd.DataFrame(inventory_rows)
    if source_inventory.empty:
        st.info("No source inventory available.")
    else:
        st.dataframe(source_inventory, use_container_width=True, hide_index=True, height=260)

    st.markdown("<div class='section-title'>Immediate Data Quality Gate</div>", unsafe_allow_html=True)
    st.dataframe(quality, use_container_width=True, hide_index=True, height=330)
    st.caption("Recommended workflow: Upload → Save → automatic rerun → System Check → Executive Dashboard.")


if False:  # Hidden legacy System page.
    st.markdown("<div class='section-title'>System Check / Data Health</div>", unsafe_allow_html=True)
    q1, q2, q3, q4, q5, q6 = st.columns(6, gap="small")
    q1.metric("Rows Loaded", f"{len(delay_df):,}")
    q2.metric("Aircraft Types", f"{delay_df['A/C Type'].replace('', pd.NA).nunique():,}")
    q3.metric("Powerplant Events", f"{int((delay_df['Powerplant Flag'] == 'Powerplant').sum()):,}")
    q4.metric("All-ATA Denominator", "READY" if all_ata_source_ready else "CHECK")
    q5.metric("Exact Duplicates Removed", f"{load_meta.get('exact_duplicates_removed', 0):,}")
    q6.metric("Part Source", "READY" if not part_df.empty else "NOT LOADED")

    class_health = classification_health(delay_df)
    c1, c2, c3, c4 = st.columns(4, gap="small")
    c1.metric("KeyProblem Coverage", "—" if class_health.get("coverage_pct") is None else f"{class_health['coverage_pct']:.1f}%")
    c2.metric("Suggested from Text", f"{class_health.get('suggested', 0):,}")
    c3.metric("Needs Classification", f"{class_health.get('needs', 0):,}")
    c4.metric("Actionable Coverage", "—" if class_health.get("actionable_coverage_pct") is None else f"{class_health['actionable_coverage_pct']:.1f}%")

    st.dataframe(quality, use_container_width=True, hide_index=True)

    st.markdown("<div class='section-title'>Detected Aircraft Types & Coverage</div>", unsafe_allow_html=True)
    types = delay_df.groupby("A/C Type").agg(
        Events=("Occurrence", "sum"), First_Date=("Date", "min"), Last_Date=("Date", "max")
    ).reset_index()
    types["First_Date"] = types["First_Date"].dt.strftime("%Y-%m-%d")
    types["Last_Date"] = types["Last_Date"].dt.strftime("%Y-%m-%d")
    st.dataframe(types, use_container_width=True, hide_index=True)

    repeated = delay_df[(delay_df["Notif"] != "") & delay_df["Notif"].duplicated(keep=False)].sort_values(["Notif", "Date"])
    if not repeated.empty:
        st.markdown("<div class='section-title'>Repeated Notification IDs · Review, Do Not Auto-Delete</div>", unsafe_allow_html=True)
        st.dataframe(
            repeated[["Notif", "Date", "A/C Reg", "ATA", "Tech Dur", "Problem", "_Source_File"]],
            use_container_width=True,
            hide_index=True,
        )

    if exposure_df.empty:
        st.warning("Revenue T/O belum tersedia. PP Delay Rate /100 T/O sengaja dibiarkan blank.")
    else:
        st.success(f"Revenue T/O / exposure loaded: {len(exposure_df):,} rows.")

    st.markdown("<div class='section-title'>Reliability Metric Support</div>", unsafe_allow_html=True)
    support_summary = reliability_calculation_summary(
        all_scope_df,
        exposure_df,
        aircraft_type,
        freq="Yearly",
        all_ata_source_ready=all_ata_source_ready,
        start_date=start_date,
        end_date=end_date,
    )
    if support_summary is None or support_summary.empty:
        st.info("No yearly metric-support rows are available for the active scope.")
    else:
        support_display = support_summary.copy()
        support_display["Period"] = pd.to_datetime(support_display["Period"], errors="coerce").dt.strftime("%Y")
        if "PP Delay Contribution %" in support_display.columns:
            support_display["PP Delay Contribution %"] = pd.to_numeric(support_display["PP Delay Contribution %"], errors="coerce").round(2)
        if "PP Delay Rate /100 T/O" in support_display.columns:
            support_display["PP Delay Rate /100 T/O"] = pd.to_numeric(support_display["PP Delay Rate /100 T/O"], errors="coerce").round(3)
        st.dataframe(support_display, use_container_width=True, hide_index=True, height=280)

    if not support_metrics_df.empty:
        with st.expander("Historical annual reference workbook", expanded=False):
            ref = filter_support_metrics(support_metrics_df, aircraft_type)
            ref = ref[(ref["Year"] >= pd.Timestamp(start_date).year) & (ref["Year"] <= pd.Timestamp(end_date).year)].copy()
            if ref.empty:
                st.info("No historical reference rows match the active fleet and period.")
            else:
                cols = ["Year", "PP Delay Events", "All ATA Delay Events", "PP Delay Contribution %", "Revenue T/O", "PP Delay Rate /100 T/O"]
                cols = [c for c in cols if c in ref.columns]
                ref_show = ref[cols].copy()
                if "PP Delay Contribution %" in ref_show.columns:
                    ref_show["PP Delay Contribution %"] = pd.to_numeric(ref_show["PP Delay Contribution %"], errors="coerce").round(2)
                if "PP Delay Rate /100 T/O" in ref_show.columns:
                    ref_show["PP Delay Rate /100 T/O"] = pd.to_numeric(ref_show["PP Delay Rate /100 T/O"], errors="coerce").round(3)
                st.dataframe(ref_show, use_container_width=True, hide_index=True, height=260)



if False:  # Hidden legacy Method page.
    st.markdown("<div class='section-title'>Metric Definitions & Operating Rules</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
**Official Powerplant definition**  
ATA **49 and ATA 71–80**.

**Approved All-ATA denominator universe**  
ATA **05, 11, 12, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 38, 42, 45, 46, 47, 49, 50, 52, 53, 54, 55, 56, 57, 58, 61, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80**.  
ATA 05 is normalized internally as integer `5`. Rows outside this approved universe are retained for review but excluded from the official contribution denominator.

**Powerplant Delay Contribution % — official management KPI**  
Shows the share of all approved technical-delay events that are Powerplant-related. It is **event/case based**, matching the calculation-support workbook, and is not calculated from delay minutes. All Fleet uses pooled event totals rather than averaging fleet percentages.

**ATA Share of Powerplant — engineering breakdown**  
Shows how much one selected ATA chapter contributes to the total Powerplant event or delay-minute burden. This is intentionally separate from the official Powerplant Delay Contribution.

**Powerplant Delay Rate /100 T/O**  
Shows Powerplant delay-event frequency relative to Revenue T/O exposure. Monthly Revenue T/O is recommended for monthly trend monitoring; yearly Revenue T/O is appropriate for full-calendar-year reporting.

**Management vs engineering filters**  
Date, aircraft type, station, and route define the official scope. System Group, ATA Analysis, severity, Event Type, and keyword are engineering drill-down filters and do **not** collapse the official Powerplant Delay Contribution denominator.

**KPI previous-period comparison**  
YTD and Last-12-Month views compare against the equivalent period one year earlier. Last-3-Years compares against the preceding three-year window. Custom ranges compare against the immediately preceding equal-length range. All History has no artificial prior-period delta.

**Severe event**  
Tech Dur ≥ {SEVERE_THRESHOLD_MIN} minutes.

**RTA / RTB / RTO**  
Shown separately as operational-consequence Powerplant events.

**Historical data**  
Keep historical all-ATA technical-delay source exports in `data/delay/`. Non-Powerplant rows are required for the contribution denominator but are intentionally excluded from Powerplant engineering Pareto/watchlist views.

**Keyword search**  
Searches Problem, KeyProblem, Rectification, and Chronology only within the Powerplant engineering scope.

**Interpretation guardrail**  
ATA, fleet, station, route, recurrence, and text analyses describe association and contribution in the available records. They do not, by themselves, establish causal maintenance effectiveness.
        """
    )

    st.markdown(
        """
### Engineering Intelligence additions
- **Repetitive defect:** same A/C Reg + ATA + normalized Problem Group within the selected recurrence window.
- **Tail Priority Index:** percentile-based triage using events, delay minutes, severe events, RTA/RTB/RTO, and repeat defects. It is **not** FH/FC-normalized reliability.
- **Recurrence after rectification:** descriptive follow-up signal only; it does not prove maintenance-action causality.
- **Problem Group / System / Component / Failure Mode:** transparent rule-based derived fields. Raw source text remains unchanged.
- **Engine Position:** extracted from free text when ENG 1 / ENG 2 wording is unambiguous.
- **Station / route concentration:** descriptive only; traffic volume and maintenance capability can confound comparisons.
- **Classification queue:** suggestions require engineer validation before they become controlled taxonomy.

For true fleet/tail reliability benchmarking, add `Revenue T/O`, `Flight Hours`, and `Flight Cycles` exposure at the appropriate fleet/tail grain.
        """
    )

st.caption("Powerplant Engineering · Internal Reliability Analytics · Streamlit dashboard")
