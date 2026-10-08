from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from rel_config import PLOT_COLORS


NAVY = "#0B1F33"
BLUE = "#245B9E"
TEAL = "#448F92"
TEXT = "#233247"
MUTED = "#667085"
GRID = "#EEF2F6"


def _base_layout(fig: go.Figure, height: int = 300, title: str | None = None) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=16, r=16, t=48 if title else 26, b=16),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Segoe UI, Arial, sans-serif", color=TEXT, size=11.5),
        hoverlabel=dict(bgcolor="white", bordercolor="#D9E1EA", font_color=TEXT, font_size=11.5),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            font=dict(size=10.5, color=MUTED),
        ),
        title=(
            dict(text=title, x=0.015, xanchor="left", y=0.97, yanchor="top", font=dict(size=14.5, color=NAVY))
            if title
            else None
        ),
    )
    fig.update_xaxes(
        showgrid=False,
        linecolor="#DCE3EC",
        tickfont=dict(color="#52657D", size=10.5),
        title_font=dict(color="#52657D", size=10.5),
        zeroline=False,
    )
    fig.update_yaxes(
        gridcolor=GRID,
        gridwidth=1,
        linecolor="#DCE3EC",
        tickfont=dict(color="#52657D", size=10.5),
        title_font=dict(color="#52657D", size=10.5),
        zeroline=False,
    )
    return fig


def empty_chart(message: str, height: int = 290, title: str | None = None) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.48,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=11, color=MUTED),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _base_layout(fig, height, title)


def _trend_point_windows(periods, granularity: str, start_date=None, end_date=None):
    """Return human-readable start/end dates behind each Trend Analysis point.

    Monthly points represent that calendar month, yearly points that calendar year,
    and daily points the individual day. The first/last point is clipped to the
    active dashboard Date Range when it is a partial period.
    """
    p = pd.to_datetime(pd.Series(periods), errors="coerce")
    mode = str(granularity).strip().lower()
    if mode.startswith("year"):
        starts = p.dt.to_period("Y").dt.start_time
        ends = p.dt.to_period("Y").dt.end_time.dt.normalize()
    elif mode.startswith("day"):
        starts = p.dt.normalize()
        ends = p.dt.normalize()
    else:
        starts = p.dt.to_period("M").dt.start_time
        ends = p.dt.to_period("M").dt.end_time.dt.normalize()

    if start_date is not None:
        active_start = pd.Timestamp(start_date).normalize()
        starts = starts.map(lambda x: max(x, active_start) if pd.notna(x) else x)
    if end_date is not None:
        active_end = pd.Timestamp(end_date).normalize()
        ends = ends.map(lambda x: min(x, active_end) if pd.notna(x) else x)

    return (
        starts.dt.strftime("%d %b %Y").fillna("—"),
        ends.dt.strftime("%d %b %Y").fillna("—"),
    )


def delay_minutes_line(
    data: pd.DataFrame,
    metric: str = "Delay Minutes",
    title: str | None = None,
    granularity: str = "Monthly",
    start_date=None,
    end_date=None,
) -> go.Figure:
    """Powerplant burden trend with point-level date-window traceability."""
    value = "PP Events" if metric == "Events" else "PP Delay Minutes"
    unit = "events" if metric == "Events" else "min"
    granularity = "Daily" if str(granularity).strip().lower() in {"daily", "day"} else "Monthly"
    metric_title = "Powerplant Event Count Trend" if metric == "Events" else "Powerplant Delay Minutes Trend"
    title = title or metric_title
    if data.empty or value not in data.columns:
        return empty_chart(f"No Powerplant {unit} data for selected scope", title=title)

    color = TEAL if metric == "Events" else BLUE
    daily = granularity == "Daily"
    hover_date = "%d %b %Y" if daily else "%b %Y"
    tick_format = "%d %b" if daily else "%b %Y"
    marker_size = 4.5 if daily else 6
    line_width = 2.1 if daily else 2.6
    win_start, win_end = _trend_point_windows(data["Period"], granularity, start_date, end_date)
    pp_events = pd.to_numeric(data.get("PP Events", pd.Series(index=data.index, dtype=float)), errors="coerce")
    custom = list(zip(win_start, win_end, pp_events))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["Period"],
            y=data[value],
            mode="lines+markers",
            name="Event Count" if metric == "Events" else "Delay Minutes",
            line=dict(color=color, width=line_width),
            marker=dict(size=marker_size, color="white", line=dict(color=color, width=1.7)),
            customdata=custom,
            hovertemplate=(
                f"%{{x|{hover_date}}}<br><b>%{{y:,.0f}} events</b>"
                "<br>Window: %{customdata[0]} → %{customdata[1]}"
                "<br>PP events: %{customdata[2]:,.0f}<extra></extra>"
                if metric == "Events"
                else f"%{{x|{hover_date}}}<br><b>%{{y:,.0f}} min</b>"
                "<br>Window: %{customdata[0]} → %{customdata[1]}"
                "<br>PP events: %{customdata[2]:,.0f}<extra></extra>"
            ),
        )
    )
    fig.update_yaxes(title=None, rangemode="tozero", tickformat="~s")
    fig.update_xaxes(
        title=None,
        tickformat=tick_format,
        nticks=12 if daily else None,
        rangeslider=dict(visible=daily, thickness=0.07, bgcolor="#F5F8FC", bordercolor="#DCE3EC", borderwidth=1) if daily else None,
    )
    return _base_layout(fig, 500 if daily else 420, title)


def delay_rate_line(
    data: pd.DataFrame,
    metric: str = "Events",
    title: str | None = None,
) -> go.Figure:
    """Exposure-normalized trend for event count or delay-minute burden."""
    if metric == "Events":
        value = "Event Rate /100 Dep"
        label = "Events /100 Dep"
        unit = "events /100 dep"
        title = title or "Powerplant Events /100 Departures"
        color = TEAL
        fmt = ".3f"
    else:
        value = "Delay Minutes /100 Dep"
        label = "Delay Min /100 Dep"
        unit = "min /100 dep"
        title = title or "Powerplant Delay Minutes /100 Departures"
        color = BLUE
        fmt = ".1f"

    if data.empty or value not in data.columns or data[value].notna().sum() == 0:
        return empty_chart(f"Add monthly Exposure to calculate {label}", title=title)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["Period"],
            y=data[value],
            mode="lines+markers",
            name=label,
            line=dict(color=color, width=2.6),
            marker=dict(size=6, color="white", line=dict(color=color, width=2)),
            hovertemplate=f"%{{x|%b %Y}}<br><b>%{{y:{fmt}}} {unit}</b><extra></extra>",
        )
    )
    fig.update_yaxes(title=None, rangemode="tozero")
    fig.update_xaxes(title=None, tickformat="%b %Y")
    return _base_layout(fig, 285, title)


def powerplant_contribution_line(
    data: pd.DataFrame,
    title: str = "Powerplant Delay Contribution Trend",
    granularity: str = "Yearly",
    start_date=None,
    end_date=None,
) -> go.Figure:
    value = "PP Delay Contribution %"
    if data is None or data.empty or value not in data.columns or data[value].notna().sum() == 0:
        return empty_chart(
            "All-ATA denominator is required to calculate Powerplant Delay Contribution",
            height=430,
            title=title,
        )
    mode = str(granularity).strip().lower()
    tick = "%Y" if mode.startswith("year") else ("%d %b" if mode.startswith("day") else "%b %Y")
    hover = "%Y" if mode.startswith("year") else ("%d %b %Y" if mode.startswith("day") else "%b %Y")
    win_start, win_end = _trend_point_windows(data["Period"], granularity, start_date, end_date)
    custom = list(zip(
        win_start,
        win_end,
        pd.to_numeric(data["PP Delay Events"], errors="coerce"),
        pd.to_numeric(data["All ATA Delay Events"], errors="coerce"),
    ))
    fig = go.Figure(
        go.Scatter(
            x=data["Period"],
            y=data[value],
            mode="lines+markers+text" if mode.startswith("year") else "lines+markers",
            text=data[value].map(lambda x: "" if pd.isna(x) else f"{x:.1f}%") if mode.startswith("year") else None,
            textposition="top center",
            name="PP Contribution",
            line=dict(color=BLUE, width=2.8),
            marker=dict(size=7, color="white", line=dict(color=BLUE, width=2)),
            customdata=custom,
            hovertemplate=(
                f"%{{x|{hover}}}<br><b>%{{y:.2f}}%</b>"
                "<br>Window: %{customdata[0]} → %{customdata[1]}"
                "<br>PP events: %{customdata[2]:,.0f}"
                "<br>All ATA events: %{customdata[3]:,.0f}<extra></extra>"
            ),
        )
    )
    fig.update_yaxes(title=None, rangemode="tozero", ticksuffix="%")
    fig.update_xaxes(title=None, tickformat=tick)
    return _base_layout(fig, 440, title)


def powerplant_delay_rate_line(
    data: pd.DataFrame,
    title: str = "Powerplant Delay Rate",
    granularity: str = "Yearly",
    start_date=None,
    end_date=None,
) -> go.Figure:
    value = "PP Delay Rate /100 T/O"
    if data is None or data.empty or value not in data.columns or data[value].notna().sum() == 0:
        return empty_chart(
            "Revenue T/O exposure is required at a compatible time grain",
            height=430,
            title=title,
        )
    mode = str(granularity).strip().lower()
    tick = "%Y" if mode.startswith("year") else "%b %Y"
    hover = "%Y" if mode.startswith("year") else "%b %Y"
    valid = data[data[value].notna()].copy()
    win_start, win_end = _trend_point_windows(valid["Period"], granularity, start_date, end_date)
    custom = list(zip(
        win_start,
        win_end,
        pd.to_numeric(valid["PP Delay Events"], errors="coerce"),
        pd.to_numeric(valid["Revenue T/O"], errors="coerce"),
    ))
    fig = go.Figure(
        go.Scatter(
            x=valid["Period"],
            y=valid[value],
            mode="lines+markers+text" if mode.startswith("year") else "lines+markers",
            text=valid[value].map(lambda x: f"{x:.3f}") if mode.startswith("year") else None,
            textposition="top center",
            name="PP Delay Rate /100 T/O",
            line=dict(color=TEAL, width=2.8),
            marker=dict(size=7, color="white", line=dict(color=TEAL, width=2)),
            customdata=custom,
            hovertemplate=(
                f"%{{x|{hover}}}<br><b>%{{y:.3f}} /100 T/O</b>"
                "<br>Window: %{customdata[0]} → %{customdata[1]}"
                "<br>PP events: %{customdata[2]:,.0f}"
                "<br>Revenue T/O: %{customdata[3]:,.0f}<extra></extra>"
            ),
        )
    )
    fig.update_yaxes(title=None, rangemode="tozero", tickformat=".3f")
    fig.update_xaxes(title=None, tickformat=tick)
    return _base_layout(fig, 440, title)


def top_ata_bar(
    data: pd.DataFrame,
    metric: str = "Delay Minutes",
    top_n: int = 8,
    title: str = "Top ATA Contributors",
) -> go.Figure:
    if data.empty:
        return empty_chart("No Powerplant ATA data", title=title)
    value = "Events" if metric == "Events" else "Delay Minutes"
    unit = "events" if value == "Events" else "min"
    plot = data.head(top_n).copy().sort_values(value, ascending=True)
    plot["ATA Label"] = plot["ATA"].astype(int).astype(str).radd("ATA ")
    plot["Bar Label"] = plot.apply(
        lambda r: f"{r[value]:,.0f} {unit} ({r['Share %']:.1f}%)",
        axis=1,
    )
    fig = go.Figure(
        go.Bar(
            x=plot[value],
            y=plot["ATA Label"],
            orientation="h",
            text=plot["Bar Label"],
            textposition="outside",
            cliponaxis=False,
            marker=dict(color=TEAL if metric == "Events" else BLUE, line=dict(color="#0A459A", width=.4)),
            customdata=np.stack([plot["Share %"]], axis=-1),
            hovertemplate=f"%{{y}}<br><b>%{{x:,.0f}} {unit}</b><br>%{{customdata[0]:.1f}}% contribution<extra></extra>",
        )
    )
    fig.update_xaxes(title=None, rangemode="tozero", tickformat="~s")
    fig.update_yaxes(title=None, gridcolor="white")
    return _base_layout(fig, 300, title)


def key_problem_bar(
    data: pd.DataFrame,
    top_n: int = 8,
    metric: str = "Delay Minutes",
    title: str = "Top Key Problems",
) -> go.Figure:
    if data.empty:
        return empty_chart("No KeyProblem data", title=title)
    value = "Events" if metric == "Events" else "Delay Minutes"
    unit = "events" if value == "Events" else "min"
    total = float(data[value].sum()) if len(data) else 0.0
    plot = data.sort_values(value, ascending=False).head(top_n).copy()
    plot["Share"] = np.where(total > 0, plot[value] / total * 100, 0.0)
    plot = plot.sort_values(value, ascending=True)
    plot["Bar Label"] = plot.apply(lambda r: f"{r[value]:,.0f} {unit} ({r['Share']:.1f}%)", axis=1)
    fig = go.Figure(
        go.Bar(
            x=plot[value],
            y=plot["KeyProblem"],
            orientation="h",
            text=plot["Bar Label"],
            textposition="outside",
            cliponaxis=False,
            marker=dict(color=TEAL if metric == "Events" else BLUE, line=dict(color="#087D8E", width=.4)),
            hovertemplate=f"%{{y}}<br><b>%{{x:,.0f}} {unit}</b><extra></extra>",
        )
    )
    fig.update_xaxes(title=None, rangemode="tozero", tickformat="~s")
    fig.update_yaxes(title=None, gridcolor="white", tickfont=dict(size=10))
    return _base_layout(fig, 300, title)


def fleet_bar(
    data: pd.DataFrame,
    metric: str = "PP Delay Minutes",
    title: str = "Fleet Comparison",
) -> go.Figure:
    if data.empty or metric not in data.columns:
        return empty_chart("No fleet data", title=title)
    plot = data.sort_values(metric, ascending=False).copy()
    is_events = metric == "PP Events"
    fig = go.Figure(
        go.Bar(
            x=plot["A/C Type"],
            y=plot[metric],
            text=plot[metric].map(lambda x: f"{x:,.0f}"),
            textposition="outside",
            marker=dict(color=TEAL if is_events else BLUE, line=dict(color="#0A459A", width=.5)),
            hovertemplate=f"%{{x}}<br><b>%{{y:,.0f}} {'events' if is_events else 'min'}</b><extra></extra>",
        )
    )
    fig.update_yaxes(title=None, rangemode="tozero", tickformat="~s")
    fig.update_xaxes(title=None)
    return _base_layout(fig, 292, title)


def severity_donut(
    df: pd.DataFrame,
    metric: str = "Events",
    title: str = "Severity Distribution",
) -> go.Figure:
    if df.empty:
        return empty_chart("No severity data", title=title)
    order = ["≤15 min", "16–30 min", "31–60 min", "61–120 min", ">120 min", "Unknown"]
    pp = df[df["Powerplant Flag"] == "Powerplant"].copy()
    if pp.empty:
        return empty_chart("No severity data", title=title)

    if metric == "Events":
        values = pp["Delay Band"].value_counts().reindex(order, fill_value=0).astype(float)
        unit = "events"
        center_label = "Events"
    else:
        pp["Tech Dur"] = pd.to_numeric(pp["Tech Dur"], errors="coerce").fillna(0).clip(lower=0)
        values = pp.groupby("Delay Band")["Tech Dur"].sum().reindex(order, fill_value=0).astype(float)
        unit = "min"
        center_label = "Delay Min"

    values = values[values > 0]
    if values.empty:
        return empty_chart("No severity data", title=title)
    palette = {
        "≤15 min": "#2E9D58",
        "16–30 min": "#8BC34A",
        "31–60 min": "#F2C94C",
        "61–120 min": "#F2994A",
        ">120 min": "#E53935",
        "Unknown": "#94A3B8",
    }
    total = float(values.sum())
    fig = go.Figure(
        go.Pie(
            labels=values.index,
            values=values.values,
            hole=.58,
            sort=False,
            marker=dict(colors=[palette[x] for x in values.index], line=dict(color="white", width=1)),
            textinfo="none",
            hovertemplate=f"%{{label}}<br><b>%{{value:,.0f}} {unit}</b><br>%{{percent}}<extra></extra>",
        )
    )
    fig.add_annotation(
        x=.5,
        y=.5,
        text=f"<b>{total:,.0f}</b><br><span style='font-size:10px'>{center_label}</span>",
        showarrow=False,
        font=dict(color=NAVY, size=16),
    )
    fig.update_layout(
        legend=dict(orientation="v", y=.5, yanchor="middle", x=1.02, xanchor="left", font=dict(size=9.2))
    )
    metric_suffix = " · Event Count" if metric == "Events" else " · Delay Minutes"
    return _base_layout(fig, 292, title + metric_suffix)


def ata_deterioration_heatmap(
    matrix: pd.DataFrame,
    metric: str = "Events",
    title: str = "ATA Deterioration · 3-Year View",
) -> go.Figure:
    if matrix is None or matrix.empty:
        return empty_chart("Not enough dated data for 3-year ATA view", title=title)
    year_cols = [c for c in matrix.columns if str(c).isdigit()]
    if not year_cols:
        return empty_chart("Not enough dated data for 3-year ATA view", title=title)
    plot = matrix[["ATA", *year_cols]].copy()
    plot = plot[plot[year_cols].sum(axis=1) > 0]
    if plot.empty:
        return empty_chart("No Powerplant ATA data in 3-year view", title=title)

    z = plot[year_cols].to_numpy(dtype=float)
    max_value = float(np.nanmax(z)) if z.size else 1.0
    zmax = max(max_value, 1.0)
    unit = "events" if metric == "Events" else "min"
    metric_suffix = " · Event Count" if metric == "Events" else " · Delay Minutes"
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=year_cols,
            y=[f"ATA {int(x)}" for x in plot["ATA"]],
            text=np.rint(z).astype(int),
            texttemplate="%{text}",
            colorscale=[
                [0.00, "#E8F5E9"],
                [0.35, "#DCECB8"],
                [0.55, "#F7E7A2"],
                [0.78, "#F5B278"],
                [1.00, "#EB6A5B"],
            ],
            zmin=0,
            zmax=zmax,
            colorbar=dict(title=dict(text="Higher", font=dict(size=8)), thickness=8, len=.72, tickfont=dict(size=8)),
            xgap=1,
            ygap=1,
            hovertemplate=f"%{{y}}<br>%{{x}}: <b>%{{z:,.0f}} {unit}</b><extra></extra>",
        )
    )
    fig.update_xaxes(side="top", title=None, tickfont=dict(size=10))
    fig.update_yaxes(title=None, autorange="reversed", gridcolor="white", tickfont=dict(size=9.5))
    return _base_layout(fig, 292, title + metric_suffix)


def severity_bar(df: pd.DataFrame) -> go.Figure:
    """Retained for backwards compatibility with older views."""
    if df.empty:
        return empty_chart("No data", title="Severity Distribution")
    order = ["≤15 min", "16–30 min", "31–60 min", "61–120 min", ">120 min", "Unknown"]
    counts = df[df["Powerplant Flag"] == "Powerplant"]["Delay Band"].value_counts().reindex(order, fill_value=0).reset_index()
    counts.columns = ["Delay Band", "Events"]
    counts = counts[counts["Events"] > 0]
    fig = px.bar(counts, x="Delay Band", y="Events", text="Events")
    fig.update_traces(marker_color=PLOT_COLORS["sky"], textposition="outside")
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="Events", rangemode="tozero")
    return _base_layout(fig, 300, "Severity Distribution")


def frequency_impact_scatter(
    data: pd.DataFrame,
    title: str = "KeyProblem Frequency × Impact Matrix",
) -> go.Figure:
    if data is None or data.empty:
        return empty_chart("No KeyProblem data for frequency-impact analysis", title=title)
    plot = data.copy()
    x_mid = float(plot["Events"].median()) if len(plot) else 0.0
    y_mid = float(plot["Delay Minutes"].median()) if len(plot) else 0.0
    size = np.clip(plot["Aircraft"].astype(float), 1, None)
    sizeref = max(size.max() / 28.0, 0.25)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=plot["Events"],
            y=plot["Delay Minutes"],
            mode="markers",
            text=plot["Problem Group"],
            customdata=np.stack([plot["Aircraft"], plot["Avg Delay / Event"]], axis=-1),
            marker=dict(
                size=size,
                sizemode="area",
                sizeref=sizeref,
                sizemin=7,
                color=plot["Delay Minutes"],
                colorscale=[[0, "#7DD3FC"], [.55, "#2563EB"], [1, "#DC2626"]],
                line=dict(color="white", width=1.2),
                showscale=False,
                opacity=.88,
            ),
            hovertemplate=(
                "<b>%{text}</b><br>Events: %{x:,.0f}<br>Delay: %{y:,.0f} min"
                "<br>Aircraft: %{customdata[0]:,.0f}<br>Avg delay/event: %{customdata[1]:,.1f} min<extra></extra>"
            ),
        )
    )
    fig.add_vline(x=x_mid, line_dash="dash", line_color="#94A3B8", line_width=1)
    fig.add_hline(y=y_mid, line_dash="dash", line_color="#94A3B8", line_width=1)
    fig.add_annotation(x=x_mid, y=1, xref="x", yref="paper", text="Frequency median", showarrow=False, yshift=8, font=dict(size=9.5, color=MUTED))
    fig.add_annotation(x=1, y=y_mid, xref="paper", yref="y", text="Impact median", showarrow=False, xshift=-6, font=dict(size=9.5, color=MUTED))
    fig.update_xaxes(title="Event Count", rangemode="tozero")
    fig.update_yaxes(title="Delay Minutes", rangemode="tozero", tickformat="~s")
    return _base_layout(fig, 360, title)


def concentration_bar(
    data: pd.DataFrame,
    category: str,
    metric: str = "Delay Minutes",
    top_n: int = 12,
    title: str = "Concentration",
) -> go.Figure:
    if data is None or data.empty or category not in data.columns:
        return empty_chart("No data for selected concentration view", title=title)
    value = "Events" if metric == "Events" else "Delay Minutes"
    unit = "events" if metric == "Events" else "min"
    plot = data.sort_values(value, ascending=False).head(top_n).copy().sort_values(value, ascending=True)
    labels = plot[category].astype(str)
    share = plot["Share %"] if "Share %" in plot.columns else pd.Series(np.nan, index=plot.index)
    text = [f"{v:,.0f} {unit}" + (f" ({s:.1f}%)" if pd.notna(s) else "") for v, s in zip(plot[value], share)]
    fig = go.Figure(
        go.Bar(
            x=plot[value], y=labels, orientation="h", text=text, textposition="outside", cliponaxis=False,
            marker=dict(color=TEAL if metric == "Events" else BLUE),
            hovertemplate=f"%{{y}}<br><b>%{{x:,.0f}} {unit}</b><extra></extra>",
        )
    )
    fig.update_xaxes(title=None, rangemode="tozero", tickformat="~s")
    fig.update_yaxes(title=None, gridcolor="white", tickfont=dict(size=9.8))
    return _base_layout(fig, 330, title)


def repeat_defect_bar(data: pd.DataFrame, window_days: int = 90, top_n: int = 12) -> go.Figure:
    title = f"Top Repetitive Defects · ≤{window_days} Days"
    if data is None or data.empty:
        return empty_chart("No repetitive defects detected in the active scope", title=title)
    col = f"Repeats ≤{window_days}d"
    plot = data.head(top_n).copy()
    plot["Label"] = plot["A/C Reg"].astype(str) + " · ATA " + plot["ATA"].astype("Int64").astype(str) + " · " + plot["Problem Group"].astype(str)
    plot = plot.sort_values([col, "Delay Minutes"], ascending=True)
    fig = go.Figure(
        go.Bar(
            x=plot[col], y=plot["Label"], orientation="h",
            text=plot[col].map(lambda x: f"{int(x)} repeat" + ("s" if int(x) != 1 else "")),
            textposition="outside", cliponaxis=False, marker=dict(color="#D97706"),
            customdata=np.stack([plot["Occurrences"], plot["Delay Minutes"]], axis=-1),
            hovertemplate="%{y}<br><b>%{x:.0f} repeats</b><br>Total occurrences: %{customdata[0]:.0f}<br>Delay: %{customdata[1]:,.0f} min<extra></extra>",
        )
    )
    fig.update_xaxes(title="Repeat Events", rangemode="tozero", dtick=1)
    fig.update_yaxes(title=None, gridcolor="white", tickfont=dict(size=9.2))
    return _base_layout(fig, 360, title)

def rolling_12m_delay_minutes_line(
    data: pd.DataFrame,
    title: str = "Powerplant Delay Minutes · Rolling 12 Months",
) -> go.Figure:
    value = "PP Delay Minutes 12M"
    if data is None or data.empty or value not in data.columns or data[value].notna().sum() == 0:
        return empty_chart(
            "At least 12 complete monthly periods are required for a Rolling 12-Month trend",
            height=430,
            title=title,
        )
    valid = data[data[value].notna()].copy()
    custom = list(zip(
        valid["Window Start"].dt.strftime("%b %Y"),
        valid["Window End"].dt.strftime("%b %Y"),
        pd.to_numeric(valid["PP Events 12M"], errors="coerce"),
    ))
    fig = go.Figure(
        go.Scatter(
            x=valid["Period"],
            y=valid[value],
            mode="lines+markers",
            name="Rolling 12M Delay Minutes",
            line=dict(color=BLUE, width=2.8),
            marker=dict(size=7, color="white", line=dict(color=BLUE, width=2)),
            customdata=custom,
            hovertemplate=(
                "Ending %{x|%b %Y}<br>"
                "<b>%{y:,.0f} min</b>"
                "<br>Window: %{customdata[0]} → %{customdata[1]}"
                "<br>PP events: %{customdata[2]:,.0f}<extra></extra>"
            ),
        )
    )
    fig.update_yaxes(title=None, rangemode="tozero", tickformat="~s")
    fig.update_xaxes(title=None, tickformat="%b %Y")
    return _base_layout(fig, 440, title)


def rolling_12m_contribution_line(
    data: pd.DataFrame,
    title: str = "Powerplant Delay Contribution · Rolling 12 Months (%)",
) -> go.Figure:
    value = "PP Delay Contribution % 12M"
    if data is None or data.empty or value not in data.columns or data[value].notna().sum() == 0:
        return empty_chart(
            "At least 12 complete monthly periods and the All-ATA denominator are required",
            height=430,
            title=title,
        )
    valid = data[data[value].notna()].copy()
    custom = list(zip(
        valid["Window Start"].dt.strftime("%b %Y"),
        valid["Window End"].dt.strftime("%b %Y"),
        pd.to_numeric(valid["PP Delay Events 12M"], errors="coerce"),
        pd.to_numeric(valid["All ATA Delay Events 12M"], errors="coerce"),
    ))
    fig = go.Figure(
        go.Scatter(
            x=valid["Period"],
            y=valid[value],
            mode="lines+markers",
            name="Rolling 12M PP Contribution",
            line=dict(color=BLUE, width=2.8),
            marker=dict(size=7, color="white", line=dict(color=BLUE, width=2)),
            customdata=custom,
            hovertemplate=(
                "Ending %{x|%b %Y}<br>"
                "<b>%{y:.2f}%</b>"
                "<br>Window: %{customdata[0]} → %{customdata[1]}"
                "<br>PP events: %{customdata[2]:,.0f}"
                "<br>All ATA events: %{customdata[3]:,.0f}<extra></extra>"
            ),
        )
    )
    fig.update_yaxes(title=None, rangemode="tozero", ticksuffix="%")
    fig.update_xaxes(title=None, tickformat="%b %Y")
    return _base_layout(fig, 440, title)


def rolling_12m_delay_rate_line(
    data: pd.DataFrame,
    title: str = "Powerplant Delay Rate · Rolling 12 Months (/100 Revenue T/O)",
) -> go.Figure:
    value = "PP Delay Rate /100 T/O 12M"
    if data is None or data.empty or value not in data.columns or data[value].notna().sum() == 0:
        return empty_chart(
            "Twelve complete months of Revenue T/O exposure are required for a Rolling 12-Month rate",
            height=430,
            title=title,
        )
    valid = data[data[value].notna()].copy()
    custom = list(zip(
        valid["Window Start"].dt.strftime("%b %Y"),
        valid["Window End"].dt.strftime("%b %Y"),
        pd.to_numeric(valid["PP Delay Events 12M"], errors="coerce"),
        pd.to_numeric(valid["Revenue T/O 12M"], errors="coerce"),
    ))
    fig = go.Figure(
        go.Scatter(
            x=valid["Period"],
            y=valid[value],
            mode="lines+markers",
            name="Rolling 12M Delay Rate",
            line=dict(color=TEAL, width=2.8),
            marker=dict(size=7, color="white", line=dict(color=TEAL, width=2)),
            customdata=custom,
            hovertemplate=(
                "Ending %{x|%b %Y}<br>"
                "<b>%{y:.3f} /100 T/O</b>"
                "<br>Window: %{customdata[0]} → %{customdata[1]}"
                "<br>PP events: %{customdata[2]:,.0f}"
                "<br>Revenue T/O: %{customdata[3]:,.0f}<extra></extra>"
            ),
        )
    )
    fig.update_yaxes(title=None, rangemode="tozero", tickformat=".3f")
    fig.update_xaxes(title=None, tickformat="%b %Y")
    return _base_layout(fig, 440, title)
