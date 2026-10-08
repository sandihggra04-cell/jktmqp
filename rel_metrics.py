from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from rel_config import ALL_TECHNICAL_ATAS, POWERPLANT_ATAS, SEVERE_THRESHOLD_MIN


@dataclass
class KPIResult:
    pp_events: int
    pp_delay_minutes: float
    pp_delay_contribution_pct: float | None
    all_technical_events: int
    pp_contribution_numerator: int
    pp_contribution_denominator: int
    all_ata_source_ready: bool
    ata_contribution_pct: float | None
    contribution_ata: int | None
    contribution_basis: str
    contribution_numerator: float
    contribution_denominator: float
    ata_chapter_count: int
    delay_rate_100: float | None
    severe_events: int
    significant_events: int
    departures: float | None
    exposure_note: str


def _pp(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=getattr(df, "columns", []))
    return df[df["Powerplant Flag"] == "Powerplant"]


def _all_technical(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=getattr(df, "columns", []))
    if "Technical ATA Flag" in df.columns:
        return df[df["Technical ATA Flag"] == "Approved Technical ATA"]
    return df[df["ATA"].isin(ALL_TECHNICAL_ATAS)]


def powerplant_delay_contribution(
    df: pd.DataFrame,
    all_ata_source_ready: bool = True,
) -> tuple[float | None, int, int]:
    """Official event-based Powerplant Delay Contribution.

    numerator = ATA 49 + ATA 71–80 delay-event rows
    denominator = all approved technical ATA delay-event rows
    """
    technical = _all_technical(df)
    denominator = int(len(technical))
    numerator = int((technical["Powerplant Flag"] == "Powerplant").sum()) if denominator else 0
    if not all_ata_source_ready or denominator <= 0:
        return None, numerator, denominator
    return numerator / denominator * 100, numerator, denominator


def ata_contribution(
    df: pd.DataFrame,
    selected_ata: int | None = None,
    basis: str = "Delay Minutes",
) -> tuple[float | None, int | None, float, float, int]:
    """Return one ATA chapter's share of the total Powerplant burden.

    Denominator is always all Powerplant ATA chapters in the current scope,
    before the dedicated ATA analysis filter is applied. This prevents the
    KPI from becoming 100% simply because the user filtered the analysis to
    one ATA chapter.

    If fewer than two Powerplant ATA chapters are present, percentage is
    intentionally returned as None because there is no inter-ATA comparator.
    """
    pp = _pp(df).dropna(subset=["ATA"]).copy()
    if pp.empty:
        return None, selected_ata, 0.0, 0.0, 0

    chapters = sorted(int(x) for x in pp["ATA"].dropna().unique().tolist())
    chapter_count = len(chapters)
    metric_col = "Occurrence" if basis == "Events" else "Tech Dur"

    if metric_col == "Tech Dur":
        pp[metric_col] = pd.to_numeric(pp[metric_col], errors="coerce").fillna(0).clip(lower=0)
    else:
        pp[metric_col] = pd.to_numeric(pp[metric_col], errors="coerce").fillna(0)

    grouped = pp.groupby("ATA", dropna=True)[metric_col].sum().sort_values(ascending=False)
    denominator = float(grouped.sum())
    if grouped.empty or denominator <= 0:
        return None, selected_ata, 0.0, denominator, chapter_count

    if selected_ata is None:
        selected_ata = int(grouped.index[0])

    if selected_ata not in chapters:
        return None, selected_ata, 0.0, denominator, chapter_count

    numerator = float(grouped.get(selected_ata, 0.0))
    if chapter_count < 2:
        return None, selected_ata, numerator, denominator, chapter_count

    return numerator / denominator * 100, selected_ata, numerator, denominator, chapter_count


def _normalise_fleet_label(value: object) -> str:
    import re as _re
    return _re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def _filter_exposure_aircraft(exp: pd.DataFrame, aircraft_type: str | None) -> pd.DataFrame:
    if exp.empty or "A/C Type" not in exp.columns:
        return exp
    labels = exp["A/C Type"].astype("string").fillna("").str.strip()
    if not aircraft_type or aircraft_type == "All Aircraft":
        explicit = exp[labels.str.casefold().isin({"all aircraft", "all fleet", "all fleets"})]
        if not explicit.empty:
            return explicit
        # Otherwise sum individual fleets downstream.
        return exp[~labels.str.casefold().isin({"all aircraft", "all fleet", "all fleets"})]

    wanted = _normalise_fleet_label(aircraft_type)
    normalised = labels.map(_normalise_fleet_label)
    exact = exp[normalised == wanted]
    if not exact.empty:
        return exact
    # Tolerate labels such as B737 vs B737-800 when there is one unambiguous match.
    mask = normalised.map(lambda x: bool(x) and (x in wanted or wanted in x))
    candidates = exp[mask]
    return candidates


def exposure_for_period(
    exposure_df: pd.DataFrame,
    start_date,
    end_date,
    aircraft_type: str | None,
) -> tuple[float | None, str]:
    if exposure_df is None or exposure_df.empty:
        return None, "Revenue T/O belum tersedia"
    exp = _filter_exposure_aircraft(exposure_df.copy(), aircraft_type)
    if exp.empty:
        return None, "Tidak ada Revenue T/O yang cocok untuk aircraft terpilih"

    denom_col = "Revenue T/O" if "Revenue T/O" in exp.columns else "Departures"
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)

    if "Date" in exp.columns and exp["Date"].notna().any():
        exp = exp[(exp["Date"] >= start) & (exp["Date"] <= end)]
        note = "Daily Revenue T/O"
    elif "Year-Month" in exp.columns and exp["Year-Month"].notna().any():
        months = pd.period_range(start=start, end=end, freq="M").astype(str)
        exp = exp[exp["Year-Month"].isin(months)]
        note = "Monthly Revenue T/O; partial-month filters use full touched months"
    elif "Year" in exp.columns:
        # Do not divide a partial-year event window by a full-year annual denominator.
        full_start = start.month == 1 and start.day == 1
        full_end = end.month == 12 and end.day == 31
        if not (full_start and full_end):
            return None, "Yearly Revenue T/O tersedia; KPI rate butuh full calendar-year scope atau monthly exposure"
        years = list(range(start.year, end.year + 1))
        exp = exp[exp["Year"].isin(years)]
        note = "Yearly Revenue T/O"
    else:
        return None, "Periode Revenue T/O tidak dapat ditentukan"

    total = pd.to_numeric(exp[denom_col], errors="coerce").sum(min_count=1)
    if pd.isna(total) or total <= 0:
        return None, note
    return float(total), note


def compute_kpis(
    scope_df: pd.DataFrame,
    exposure_df: pd.DataFrame | None,
    start_date,
    end_date,
    aircraft_type: str | None,
    contribution_ata: int | None = None,
    contribution_basis: str = "Events",
    all_ata_source_ready: bool = True,
) -> KPIResult:
    pp = _pp(scope_df)
    pp_events = int(len(pp))
    pp_delay = float(pd.to_numeric(pp["Tech Dur"], errors="coerce").fillna(0).clip(lower=0).sum())
    severe = int((pd.to_numeric(pp["Tech Dur"], errors="coerce").fillna(-1) >= SEVERE_THRESHOLD_MIN).sum())
    significant = int(pp["Event Type"].astype("string").str.upper().isin(["RTA", "RTB", "RTO"]).sum())
    pp_contribution_pct, pp_num, pp_den = powerplant_delay_contribution(scope_df, all_ata_source_ready)
    contribution_pct, selected_ata, numerator, denominator, chapter_count = ata_contribution(
        scope_df,
        selected_ata=contribution_ata,
        basis=contribution_basis,
    )
    revenue_to, note = exposure_for_period(exposure_df, start_date, end_date, aircraft_type)
    rate = (pp_events / revenue_to * 100) if revenue_to else None
    return KPIResult(
        pp_events=pp_events,
        pp_delay_minutes=pp_delay,
        pp_delay_contribution_pct=pp_contribution_pct,
        all_technical_events=pp_den,
        pp_contribution_numerator=pp_num,
        pp_contribution_denominator=pp_den,
        all_ata_source_ready=bool(all_ata_source_ready),
        ata_contribution_pct=contribution_pct,
        contribution_ata=selected_ata,
        contribution_basis=contribution_basis,
        contribution_numerator=numerator,
        contribution_denominator=denominator,
        ata_chapter_count=chapter_count,
        delay_rate_100=rate,
        severe_events=severe,
        significant_events=significant,
        departures=revenue_to,
        exposure_note=note,
    )


def previous_year_scope(df: pd.DataFrame, start_date, end_date, aircraft_type: str | None) -> pd.DataFrame:
    prev_start = pd.Timestamp(start_date) - pd.DateOffset(years=1)
    prev_end = pd.Timestamp(end_date) - pd.DateOffset(years=1)
    out = df[(df["Date"] >= prev_start) & (df["Date"] <= prev_end)]
    if aircraft_type and aircraft_type != "All Aircraft":
        out = out[out["A/C Type"] == aircraft_type]
    return out


def delta_pct(current: float | int | None, previous: float | int | None) -> float | None:
    if current is None or previous is None or previous == 0:
        return None
    return (float(current) - float(previous)) / abs(float(previous)) * 100


def powerplant_contribution_trend(
    scope_df: pd.DataFrame,
    freq: str = "Monthly",
    all_ata_source_ready: bool = True,
) -> pd.DataFrame:
    columns = ["Period", "PP Delay Events", "All ATA Delay Events", "PP Delay Contribution %"]
    if scope_df is None or scope_df.empty:
        return pd.DataFrame(columns=columns)
    d = _all_technical(scope_df).dropna(subset=["Date"]).copy()
    if d.empty:
        return pd.DataFrame(columns=columns)
    mode = str(freq).strip().lower()
    if mode.startswith("day"):
        d["Period"] = pd.to_datetime(d["Date"]).dt.normalize()
    elif mode.startswith("year"):
        d["Period"] = pd.to_datetime(d["Date"]).dt.to_period("Y").dt.start_time
    else:
        d["Period"] = pd.to_datetime(d["Date"]).dt.to_period("M").dt.start_time
    grouped = d.groupby("Period", dropna=False).agg(
        **{
            "PP Delay Events": ("PP Event", "sum"),
            "All ATA Delay Events": ("All Technical Event", "sum") if "All Technical Event" in d.columns else ("Occurrence", "sum"),
        }
    ).reset_index()
    if all_ata_source_ready:
        grouped["PP Delay Contribution %"] = np.where(
            grouped["All ATA Delay Events"] > 0,
            grouped["PP Delay Events"] / grouped["All ATA Delay Events"] * 100,
            np.nan,
        )
    else:
        grouped["PP Delay Contribution %"] = np.nan
    return grouped[columns].sort_values("Period")


def reliability_calculation_summary(
    scope_df: pd.DataFrame,
    exposure_df: pd.DataFrame | None,
    aircraft_type: str | None,
    freq: str = "Yearly",
    all_ata_source_ready: bool = True,
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    """Contribution + Delay Rate audit table on a common time grain."""
    contribution = powerplant_contribution_trend(scope_df, freq=freq, all_ata_source_ready=all_ata_source_ready)
    if contribution.empty:
        return pd.DataFrame(columns=["Period", "PP Delay Events", "All ATA Delay Events", "PP Delay Contribution %", "Revenue T/O", "PP Delay Rate /100 T/O"])
    out = contribution.copy()
    out["Revenue T/O"] = np.nan
    if exposure_df is not None and not exposure_df.empty:
        exp = _filter_exposure_aircraft(exposure_df.copy(), aircraft_type)
        denom_col = "Revenue T/O" if "Revenue T/O" in exp.columns else ("Departures" if "Departures" in exp.columns else None)
        if denom_col:
            mode = str(freq).strip().lower()
            start_ts = pd.Timestamp(start_date) if start_date is not None else None
            end_ts = pd.Timestamp(end_date) if end_date is not None else None
            # Restrict daily/monthly exposure to the active management scope before aggregation.
            if "Date" in exp.columns and exp["Date"].notna().any() and start_ts is not None and end_ts is not None:
                exp = exp[(exp["Date"] >= start_ts) & (exp["Date"] <= end_ts)]
            elif "Year-Month" in exp.columns and exp["Year-Month"].notna().any() and start_ts is not None and end_ts is not None:
                allowed_months = set(pd.period_range(start=start_ts, end=end_ts, freq="M").astype(str))
                exp = exp[exp["Year-Month"].astype(str).isin(allowed_months)]
            if mode.startswith("year"):
                if "Year" not in exp.columns:
                    if "Date" in exp.columns:
                        exp["Year"] = pd.to_datetime(exp["Date"], errors="coerce").dt.year
                    elif "Year-Month" in exp.columns:
                        exp["Year"] = pd.to_datetime(exp["Year-Month"], errors="coerce").dt.year
                if "Year" in exp.columns:
                    e = exp.groupby("Year", dropna=True)[denom_col].sum(min_count=1).reset_index()
                    # If the only available denominator is yearly, do not apply a full-year T/O
                    # to a partial-year event window. Daily/monthly exposure is already filtered above.
                    gran = set(exp.get("Exposure Granularity", pd.Series(dtype=str)).dropna().astype(str).unique())
                    if gran and gran.issubset({"Yearly"}) and start_ts is not None and end_ts is not None:
                        def full_year_in_scope(year):
                            y = int(year)
                            return start_ts <= pd.Timestamp(y, 1, 1) and end_ts >= pd.Timestamp(y, 12, 31)
                        e = e[e["Year"].map(full_year_in_scope)]
                    e["Period"] = pd.to_datetime(e["Year"].astype("Int64").astype(str) + "-01-01", errors="coerce")
                    out = out.merge(e[["Period", denom_col]], on="Period", how="left", suffixes=("", "_exp"))
                    if f"{denom_col}_exp" in out.columns:
                        out["Revenue T/O"] = out[f"{denom_col}_exp"]
                        out = out.drop(columns=[f"{denom_col}_exp"])
                    elif denom_col in out.columns and denom_col != "Revenue T/O":
                        out["Revenue T/O"] = out[denom_col]
            elif mode.startswith("month"):
                # Monthly rate requires Daily/Monthly exposure. Yearly exposure is intentionally not spread across months.
                gran = set(exp.get("Exposure Granularity", pd.Series(dtype=str)).dropna().astype(str).unique())
                if not gran or not gran.issubset({"Yearly"}):
                    if "Year-Month" not in exp.columns and "Date" in exp.columns:
                        exp["Year-Month"] = pd.to_datetime(exp["Date"], errors="coerce").dt.to_period("M").astype("string")
                    if "Year-Month" in exp.columns:
                        e = exp.groupby("Year-Month", dropna=True)[denom_col].sum(min_count=1).reset_index()
                        e["Period"] = pd.to_datetime(e["Year-Month"], errors="coerce").dt.to_period("M").dt.start_time
                        out = out.merge(e[["Period", denom_col]], on="Period", how="left", suffixes=("", "_exp"))
                        if f"{denom_col}_exp" in out.columns:
                            out["Revenue T/O"] = out[f"{denom_col}_exp"]
                            out = out.drop(columns=[f"{denom_col}_exp"])
                        elif denom_col in out.columns and denom_col != "Revenue T/O":
                            out["Revenue T/O"] = out[denom_col]
    out["PP Delay Rate /100 T/O"] = np.where(
        pd.to_numeric(out["Revenue T/O"], errors="coerce") > 0,
        out["PP Delay Events"] / pd.to_numeric(out["Revenue T/O"], errors="coerce") * 100,
        np.nan,
    )
    return out[["Period", "PP Delay Events", "All ATA Delay Events", "PP Delay Contribution %", "Revenue T/O", "PP Delay Rate /100 T/O"]]



def annual_reliability_from_inputs(
    delay_df: pd.DataFrame,
    exposure_df: pd.DataFrame | None,
    aircraft_type: str | None,
    all_ata_source_ready: bool = True,
) -> pd.DataFrame:
    """Build the annual comparison strictly from the currently loaded inputs.

    This is used by the two Executive Trend Analysis tables. It deliberately
    ignores the active date-window so all years present in the loaded delay
    source remain visible for year-on-year comparison. It does *not* use the
    historical calculation-support table as an event/count fallback.

    Delay event counts come from the loaded All-ATA delay source. Revenue T/O
    comes only from the operational exposure source passed to this function.
    Therefore changing/replacing either input changes the annual table on rerun,
    and years that are not present in the delay input are not fabricated.
    """
    columns = [
        "Year",
        "PP Delay Events",
        "All ATA Delay Events",
        "PP Delay Contribution %",
        "Revenue T/O",
        "PP Delay Rate /100 T/O",
    ]
    if delay_df is None or delay_df.empty or "Date" not in delay_df.columns:
        return pd.DataFrame(columns=columns)

    d = _all_technical(delay_df).copy()
    if d.empty:
        return pd.DataFrame(columns=columns)

    if aircraft_type and aircraft_type != "All Aircraft" and "A/C Type" in d.columns:
        d = d[d["A/C Type"].astype(str) == str(aircraft_type)].copy()
    if d.empty:
        return pd.DataFrame(columns=columns)

    d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
    d = d.dropna(subset=["Date"]).copy()
    if d.empty:
        return pd.DataFrame(columns=columns)
    d["Year"] = d["Date"].dt.year.astype("Int64")

    # Keep the same event semantics as the rest of the dashboard. The flags are
    # produced by the loader/enrichment layer from each accepted technical-delay row.
    if "PP Event" in d.columns:
        d["_PP_Event"] = pd.to_numeric(d["PP Event"], errors="coerce").fillna(0)
    else:
        d["_PP_Event"] = d["ATA"].isin(POWERPLANT_ATAS).astype(int)

    if "All Technical Event" in d.columns:
        d["_All_Event"] = pd.to_numeric(d["All Technical Event"], errors="coerce").fillna(0)
    elif "Occurrence" in d.columns:
        d["_All_Event"] = pd.to_numeric(d["Occurrence"], errors="coerce").fillna(0)
    else:
        d["_All_Event"] = 1

    annual = (
        d.groupby("Year", dropna=True)
        .agg(
            **{
                "PP Delay Events": ("_PP_Event", "sum"),
                "All ATA Delay Events": ("_All_Event", "sum"),
            }
        )
        .reset_index()
        .sort_values("Year")
    )

    pp = pd.to_numeric(annual["PP Delay Events"], errors="coerce")
    all_events = pd.to_numeric(annual["All ATA Delay Events"], errors="coerce")
    if all_ata_source_ready:
        annual["PP Delay Contribution %"] = (pp / all_events * 100).where(all_events > 0)
    else:
        annual["PP Delay Contribution %"] = np.nan

    annual["Revenue T/O"] = np.nan
    if exposure_df is not None and not exposure_df.empty:
        exp = _filter_exposure_aircraft(exposure_df.copy(), aircraft_type)
        denom_col = "Revenue T/O" if "Revenue T/O" in exp.columns else ("Departures" if "Departures" in exp.columns else None)
        if denom_col and not exp.empty:
            if "Year" in exp.columns:
                exp["_Year"] = pd.to_numeric(exp["Year"], errors="coerce")
            elif "Date" in exp.columns:
                exp["_Year"] = pd.to_datetime(exp["Date"], errors="coerce").dt.year
            elif "Year-Month" in exp.columns:
                exp["_Year"] = pd.to_datetime(exp["Year-Month"], errors="coerce").dt.year
            else:
                exp["_Year"] = np.nan
            exp["_Revenue"] = pd.to_numeric(exp[denom_col], errors="coerce")
            e = (
                exp.dropna(subset=["_Year"])
                .groupby("_Year", dropna=True)["_Revenue"]
                .sum(min_count=1)
                .reset_index()
                .rename(columns={"_Year": "Year", "_Revenue": "Revenue T/O"})
            )
            if not e.empty:
                e["Year"] = pd.to_numeric(e["Year"], errors="coerce").astype("Int64")
                annual = annual.drop(columns=["Revenue T/O"]).merge(e, on="Year", how="left")

    revenue = pd.to_numeric(annual["Revenue T/O"], errors="coerce")
    annual["PP Delay Rate /100 T/O"] = (pp / revenue * 100).where(revenue > 0)

    for col in columns:
        if col not in annual.columns:
            annual[col] = np.nan
    return annual[columns].sort_values("Year").reset_index(drop=True)

def delay_minutes_trend(
    scope_df: pd.DataFrame,
    freq: str = "Monthly",
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    """Powerplant burden by Daily or Monthly time grain.

    For Daily view, calendar days with no Powerplant delay are retained as zero
    so the chart communicates both event spikes and quiet days. Monthly view
    likewise retains zero-event months inside the active analysis period.
    """
    columns = ["Period", "PP Events", "PP Delay Minutes"]
    if scope_df.empty:
        return pd.DataFrame(columns=columns)

    freq = "Daily" if str(freq).strip().lower() in {"daily", "day"} else "Monthly"
    d = _pp(scope_df).dropna(subset=["Date"]).copy()
    if d.empty:
        return pd.DataFrame(columns=columns)

    d["Date"] = pd.to_datetime(d["Date"], errors="coerce").dt.normalize()
    d = d.dropna(subset=["Date"])
    d["Tech Dur"] = pd.to_numeric(d["Tech Dur"], errors="coerce").fillna(0).clip(lower=0)

    if freq == "Daily":
        d["Period"] = d["Date"]
        result = (
            d.groupby("Period", dropna=False)
            .agg(**{"PP Events": ("Occurrence", "sum"), "PP Delay Minutes": ("Tech Dur", "sum")})
            .reset_index()
        )
        first = pd.Timestamp(start_date).normalize() if start_date is not None else result["Period"].min()
        last = pd.Timestamp(end_date).normalize() if end_date is not None else result["Period"].max()
        full_period = pd.date_range(first, last, freq="D")
    else:
        d["Period"] = d["Date"].dt.to_period("M").dt.start_time
        result = (
            d.groupby("Period", dropna=False)
            .agg(**{"PP Events": ("Occurrence", "sum"), "PP Delay Minutes": ("Tech Dur", "sum")})
            .reset_index()
        )
        first_raw = pd.Timestamp(start_date) if start_date is not None else result["Period"].min()
        last_raw = pd.Timestamp(end_date) if end_date is not None else result["Period"].max()
        first = first_raw.to_period("M").start_time
        last = last_raw.to_period("M").start_time
        full_period = pd.date_range(first, last, freq="MS")

    if len(full_period) == 0:
        return result[columns]

    result = (
        result.set_index("Period")
        .reindex(full_period, fill_value=0)
        .rename_axis("Period")
        .reset_index()
    )
    result["PP Events"] = pd.to_numeric(result["PP Events"], errors="coerce").fillna(0)
    result["PP Delay Minutes"] = pd.to_numeric(result["PP Delay Minutes"], errors="coerce").fillna(0)
    return result[columns]



def delay_rate_trend(
    scope_df: pd.DataFrame,
    exposure_df: pd.DataFrame | None,
    aircraft_type: str | None,
) -> pd.DataFrame:
    """Monthly exposure-normalized event frequency and delay-minute burden.

    Both measures share the same departures denominator so the dashboard can
    switch chart perspective without changing the selected operational scope.
    """
    columns = [
        "Period", "PP Events", "PP Delay Minutes", "Departures",
        "Event Rate /100 Dep", "Delay Minutes /100 Dep", "Rate /100 Dep",
    ]
    if scope_df.empty or exposure_df is None or exposure_df.empty:
        return pd.DataFrame(columns=columns)

    # Monthly is the safest common grain for operational exposure.
    pp = _pp(scope_df).dropna(subset=["Date"]).copy()
    if pp.empty:
        return pd.DataFrame(columns=columns)
    pp["Period"] = pp["Date"].dt.to_period("M").astype(str)
    pp["Tech Dur"] = pd.to_numeric(pp["Tech Dur"], errors="coerce").fillna(0).clip(lower=0)
    burden = (
        pp.groupby("Period", dropna=False)
        .agg(**{"PP Events": ("Occurrence", "sum"), "PP Delay Minutes": ("Tech Dur", "sum")})
        .reset_index()
    )

    exp = _filter_exposure_aircraft(exposure_df.copy(), aircraft_type)
    if "Year-Month" not in exp.columns:
        return pd.DataFrame(columns=columns)
    exp = exp.dropna(subset=["Year-Month"]).copy()
    exposure = exp.groupby("Year-Month")["Departures"].sum().rename("Departures").reset_index()
    exposure = exposure.rename(columns={"Year-Month": "Period"})
    out = burden.merge(exposure, on="Period", how="left")
    out["Event Rate /100 Dep"] = np.where(
        out["Departures"] > 0, out["PP Events"] / out["Departures"] * 100, np.nan
    )
    out["Delay Minutes /100 Dep"] = np.where(
        out["Departures"] > 0, out["PP Delay Minutes"] / out["Departures"] * 100, np.nan
    )
    # Backwards-compatible alias used by earlier versions.
    out["Rate /100 Dep"] = out["Event Rate /100 Dep"]
    out["Period"] = pd.to_datetime(out["Period"] + "-01", errors="coerce")
    return out[columns].sort_values("Period")


def ata_summary(df: pd.DataFrame, metric: str = "Delay Minutes") -> pd.DataFrame:
    pp = _pp(df).dropna(subset=["ATA"]).copy()
    if pp.empty:
        return pd.DataFrame(columns=["ATA", "Events", "Delay Minutes", "Share %"])
    out = pp.groupby("ATA").agg(Events=("Occurrence", "sum"), **{"Delay Minutes": ("Tech Dur", "sum")}).reset_index()
    metric_col = "Events" if metric == "Events" else "Delay Minutes"
    total = out[metric_col].sum()
    out["Share %"] = np.where(total > 0, out[metric_col] / total * 100, 0)
    return out.sort_values(metric_col, ascending=False)


def key_problem_summary(df: pd.DataFrame, top_n: int = 10, metric: str = "Events") -> pd.DataFrame:
    pp = _pp(df).copy()
    if pp.empty:
        return pd.DataFrame(columns=["KeyProblem", "Events", "Delay Minutes", "Aircraft"])
    # Prefer the normalized/suggested engineering problem group when available.
    # Raw KeyProblem remains untouched in Event Explorer for traceability.
    if "Problem Group" in pp.columns:
        pp["_ProblemAnalytics"] = pp["Problem Group"].astype("string").fillna("").replace("", "NEEDS CLASSIFICATION")
    else:
        pp["_ProblemAnalytics"] = pp["KeyProblem"].astype("string").fillna("").replace("", "NEEDS CLASSIFICATION")
    out = pp.groupby("_ProblemAnalytics").agg(
        Events=("Occurrence", "sum"),
        **{"Delay Minutes": ("Tech Dur", "sum"), "Aircraft": ("A/C Reg", "nunique")},
    ).reset_index().rename(columns={"_ProblemAnalytics": "KeyProblem"})
    primary = "Delay Minutes" if metric == "Delay Minutes" else "Events"
    secondary = "Events" if primary == "Delay Minutes" else "Delay Minutes"
    return out.sort_values([primary, secondary], ascending=False).head(top_n)


def fleet_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "A/C Type", "PP Events", "PP Delay Minutes", "Top ATA",
                "Top ATA Contribution %", "RTA/RTB/RTO", "Operational Impact %",
            ]
        )
    d = df.copy()
    d["_OperationalImpact"] = (
        (d["Powerplant Flag"] == "Powerplant")
        & d["Event Type"].str.upper().isin(["RTA", "RTB", "RTO"])
    ).astype(int)
    grouped = d.groupby("A/C Type").agg(
        **{
            "PP Events": ("PP Event", "sum"),
            "PP Delay Minutes": ("PP Delay Min", "sum"),
            "RTA/RTB/RTO": ("_OperationalImpact", "sum"),
        }
    ).reset_index()
    grouped["Operational Impact %"] = np.where(
        grouped["PP Events"] > 0, grouped["RTA/RTB/RTO"] / grouped["PP Events"] * 100, np.nan
    )

    top_ata_by_fleet: dict[str, str] = {}
    top_share_by_fleet: dict[str, float | None] = {}
    for fleet, fleet_df in d.groupby("A/C Type"):
        pct, selected_ata, _, _, _ = ata_contribution(fleet_df, basis="Delay Minutes")
        top_ata_by_fleet[fleet] = f"ATA {selected_ata}" if selected_ata is not None else "—"
        top_share_by_fleet[fleet] = pct
    grouped["Top ATA"] = grouped["A/C Type"].map(top_ata_by_fleet)
    grouped["Top ATA Contribution %"] = grouped["A/C Type"].map(top_share_by_fleet)
    return grouped.sort_values("PP Events", ascending=False)


def ata_deterioration_matrix(
    df: pd.DataFrame,
    latest_year: int | None = None,
    metric: str = "Events",
) -> pd.DataFrame:
    """Build a three-year ATA matrix using event count or delay minutes."""
    if df.empty or df["Year"].dropna().empty:
        return pd.DataFrame()
    latest_year = latest_year or int(df["Year"].dropna().max())
    years = [latest_year - 2, latest_year - 1, latest_year]
    pp = _pp(df).copy()
    use_minutes = metric == "Delay Minutes"
    pp["Tech Dur"] = pd.to_numeric(pp["Tech Dur"], errors="coerce").fillna(0).clip(lower=0)

    rows = []
    for ata in sorted(POWERPLANT_ATAS):
        values: list[float] = []
        for year in years:
            subset = pp[(pp["ATA"] == ata) & (pp["Year"] == year)]
            value = float(subset["Tech Dur"].sum()) if use_minutes else float(subset["Occurrence"].sum())
            values.append(value)
        yoy = None if values[-2] == 0 else (values[-1] / values[-2] - 1) * 100
        rows.append(
            {
                "ATA": ata,
                str(years[0]): values[0],
                str(years[1]): values[1],
                str(years[2]): values[2],
                "3Y Total": sum(values),
                "YoY %": yoy,
            }
        )
    return pd.DataFrame(rows)


def significant_events(df: pd.DataFrame, limit: int = 25) -> pd.DataFrame:
    pp = _pp(df).copy()
    sig = pp[
        (pp["Tech Dur"].fillna(-1) >= SEVERE_THRESHOLD_MIN)
        | pp["Event Type"].str.upper().isin(["RTA", "RTB", "RTO"])
    ]
    cols = ["Date", "A/C Type", "A/C Reg", "Route", "ATA", "Sub ATA", "Event Type", "Tech Dur", "KeyProblem", "Problem"]
    return sig.sort_values(["Tech Dur", "Date"], ascending=[False, False])[cols].head(limit)


def aircraft_watchlist(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    pp = _pp(df).copy()
    if pp.empty:
        return pd.DataFrame(columns=["A/C Reg", "A/C Type", "PP Events", "Delay Minutes", "Severe", "RTA/RTB/RTO", "Key Problems"])
    pp["_Significant"] = pp["Event Type"].str.upper().isin(["RTA", "RTB", "RTO"]).astype(int)
    pp["_Severe"] = (pp["Tech Dur"].fillna(-1) >= SEVERE_THRESHOLD_MIN).astype(int)
    out = pp.groupby(["A/C Reg", "A/C Type"], dropna=False).agg(
        **{
            "PP Events": ("Occurrence", "sum"),
            "Delay Minutes": ("Tech Dur", "sum"),
            "Severe": ("_Severe", "sum"),
            "RTA/RTB/RTO": ("_Significant", "sum"),
            "Key Problems": ("KeyProblem", lambda s: s.replace("", pd.NA).nunique()),
        }
    ).reset_index()
    return out.sort_values(["PP Events", "Delay Minutes"], ascending=False).head(top_n)


def station_summary(df: pd.DataFrame, top_n: int = 12) -> pd.DataFrame:
    pp = _pp(df).copy()
    if pp.empty:
        return pd.DataFrame(columns=["Station", "PP Events", "Delay Minutes"])
    # Departure station is used as the operational location reference. Do not interpret causally.
    pp = pp[pp["Sta Dep"] != ""]
    out = pp.groupby("Sta Dep").agg(
        **{"PP Events": ("Occurrence", "sum"), "Delay Minutes": ("Tech Dur", "sum")}
    ).reset_index().rename(columns={"Sta Dep": "Station"})
    return out.sort_values(["PP Events", "Delay Minutes"], ascending=False).head(top_n)


def data_quality_summary(df: pd.DataFrame, exact_duplicates_removed: int = 0) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            [{"Control": "Raw events loaded", "Value": 0, "Status": "CHECK", "Action": "Load source data"}]
        )
    duplicate_notif = int(df.loc[df["Notif"] != "", "Notif"].duplicated(keep=False).sum())
    checks = [
        ("Raw events loaded", len(df), "READY" if len(df) else "CHECK", "At least one event required"),
        ("Aircraft types detected", df["A/C Type"].replace("", pd.NA).nunique(), "READY", "Production may contain six or more types"),
        ("Missing Date", int(df["Date"].isna().sum()), "READY" if df["Date"].isna().sum() == 0 else "CHECK", "Correct before trend analysis"),
        ("Missing / negative Tech Dur", int((df["Tech Dur"].isna() | (df["Tech Dur"] < 0)).sum()), "READY" if (df["Tech Dur"].isna() | (df["Tech Dur"] < 0)).sum() == 0 else "CHECK", "Tech Dur must be numeric minutes"),
        ("Missing ATA", int(df["ATA"].isna().sum()), "READY" if df["ATA"].isna().sum() == 0 else "CHECK", "ATA required for Powerplant classification"),
        ("Rows flagged by model", int((df["Data Quality"] == "CHECK").sum()), "READY" if (df["Data Quality"] == "CHECK").sum() == 0 else "CHECK", "Review invalid rows"),
        ("Repeated Notif rows", duplicate_notif, "WARNING" if duplicate_notif else "READY", "Review; repeated Notif may be valid revisions/events"),
        ("Exact export duplicates removed", exact_duplicates_removed, "WARNING" if exact_duplicates_removed else "READY", "Exact repeated rows are automatically removed"),
    ]
    return pd.DataFrame(checks, columns=["Control", "Value", "Status", "Action"])


def engineering_focus(df: pd.DataFrame) -> list[str]:
    pp = _pp(df)
    if pp.empty:
        return ["Tidak ada Powerplant event pada filter aktif."]

    actions: list[str] = []
    ata = ata_summary(df, "Delay Minutes")
    if not ata.empty:
        top = ata.iloc[0]
        if len(ata) >= 2:
            actions.append(
                f"ATA {int(top['ATA'])} adalah kontributor terbesar: {top['Delay Minutes']:,.0f} delay min ({top['Share %']:.1f}% dari PP delay minutes pada scope terpilih)."
            )
        else:
            actions.append(
                f"ATA {int(top['ATA'])} mencatat {top['Delay Minutes']:,.0f} delay min; hanya satu Powerplant ATA chapter tersedia pada scope ini, sehingga belum ada pembanding antar-ATA."
            )

    key = key_problem_summary(df, 10, "Events")
    if not key.empty:
        top_key = key.iloc[0]
        actions.append(
            f"Review repetisi '{top_key['KeyProblem']}': {int(top_key['Events'])} event pada {int(top_key['Aircraft'])} aircraft."
        )

    latest_year = int(pp["Year"].dropna().max()) if not pp["Year"].dropna().empty else None
    if latest_year:
        matrix = ata_deterioration_matrix(df, latest_year)
        worsening = matrix.dropna(subset=["YoY %"]).sort_values("YoY %", ascending=False)
        if not worsening.empty and worsening.iloc[0]["YoY %"] > 0:
            row = worsening.iloc[0]
            actions.append(
                f"Deterioration watch: ATA {int(row['ATA'])} naik {row['YoY %']:.1f}% YoY pada {latest_year} dibanding {latest_year-1}."
            )

    if len(actions) < 3:
        worst = pp.sort_values("Tech Dur", ascending=False).head(1)
        if not worst.empty:
            row = worst.iloc[0]
            actions.append(
                f"Review high-impact event: {row['Tech Dur']:.0f} min, ATA {int(row['ATA']) if pd.notna(row['ATA']) else '-'}, {row['A/C Reg'] or 'reg N/A'} — {row['KeyProblem'] or row['Problem']}."
            )
    return actions[:3]

def rolling_12m_delay_minutes(
    scope_df: pd.DataFrame,
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    """Trailing 12-month Powerplant delay burden.

    This is an additive reporting view only. It does not alter the existing
    Monthly/Daily/Yearly calculations. A value is emitted only after twelve
    complete monthly buckets are present in the selected scope.
    """
    columns = [
        "Period", "Window Start", "Window End",
        "PP Events 12M", "PP Delay Minutes 12M",
    ]
    monthly = delay_minutes_trend(
        scope_df,
        freq="Monthly",
        start_date=start_date,
        end_date=end_date,
    )
    if monthly is None or monthly.empty:
        return pd.DataFrame(columns=columns)

    out = monthly.sort_values("Period").copy()
    out["PP Events 12M"] = (
        pd.to_numeric(out["PP Events"], errors="coerce")
        .rolling(window=12, min_periods=12)
        .sum()
    )
    out["PP Delay Minutes 12M"] = (
        pd.to_numeric(out["PP Delay Minutes"], errors="coerce")
        .rolling(window=12, min_periods=12)
        .sum()
    )
    out["Window End"] = pd.to_datetime(out["Period"], errors="coerce").dt.to_period("M").dt.end_time.dt.normalize()
    out["Window Start"] = (
        pd.to_datetime(out["Period"], errors="coerce") - pd.DateOffset(months=11)
    ).dt.to_period("M").dt.start_time
    return out[columns]


def rolling_12m_reliability_summary(
    scope_df: pd.DataFrame,
    exposure_df: pd.DataFrame | None,
    aircraft_type: str | None,
    all_ata_source_ready: bool = True,
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    """Trailing 12-month Contribution and Delay Rate from pooled numerators/denominators.

    Contribution is calculated from rolling sums of PP events and all-ATA events;
    it is never the average of monthly percentages. Delay Rate is calculated from
    rolling PP events divided by rolling Revenue T/O; it is never the average of
    monthly rates.
    """
    columns = [
        "Period", "Window Start", "Window End",
        "PP Delay Events 12M", "All ATA Delay Events 12M",
        "PP Delay Contribution % 12M", "Revenue T/O 12M",
        "PP Delay Rate /100 T/O 12M",
    ]
    if scope_df is None or scope_df.empty:
        return pd.DataFrame(columns=columns)

    d = _all_technical(scope_df).dropna(subset=["Date"]).copy()
    if d.empty:
        return pd.DataFrame(columns=columns)

    d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
    d = d.dropna(subset=["Date"])
    if d.empty:
        return pd.DataFrame(columns=columns)
    d["Period"] = d["Date"].dt.to_period("M").dt.start_time

    pp_event_col = "PP Event" if "PP Event" in d.columns else None
    all_event_col = "All Technical Event" if "All Technical Event" in d.columns else ("Occurrence" if "Occurrence" in d.columns else None)
    if pp_event_col is None:
        d["_PP_R12M"] = d["ATA"].isin(POWERPLANT_ATAS).astype(int)
        pp_event_col = "_PP_R12M"
    if all_event_col is None:
        d["_ALL_R12M"] = 1
        all_event_col = "_ALL_R12M"

    monthly = (
        d.groupby("Period", dropna=False)
        .agg(
            **{
                "PP Delay Events": (pp_event_col, "sum"),
                "All ATA Delay Events": (all_event_col, "sum"),
            }
        )
        .reset_index()
    )

    first_raw = pd.Timestamp(start_date) if start_date is not None else monthly["Period"].min()
    last_raw = pd.Timestamp(end_date) if end_date is not None else monthly["Period"].max()
    first = first_raw.to_period("M").start_time
    last = last_raw.to_period("M").start_time
    full_months = pd.date_range(first, last, freq="MS")
    monthly = (
        monthly.set_index("Period")
        .reindex(full_months, fill_value=0)
        .rename_axis("Period")
        .reset_index()
    )
    monthly["PP Delay Events"] = pd.to_numeric(monthly["PP Delay Events"], errors="coerce").fillna(0)
    monthly["All ATA Delay Events"] = pd.to_numeric(monthly["All ATA Delay Events"], errors="coerce").fillna(0)
    monthly["Revenue T/O"] = np.nan

    if exposure_df is not None and not exposure_df.empty:
        exp = _filter_exposure_aircraft(exposure_df.copy(), aircraft_type)
        denom_col = "Revenue T/O" if "Revenue T/O" in exp.columns else ("Departures" if "Departures" in exp.columns else None)
        if denom_col and not exp.empty:
            # R12M requires month-level exposure. Yearly totals are deliberately
            # not spread across months because doing so would fabricate exposure.
            gran = set(exp.get("Exposure Granularity", pd.Series(dtype=str)).dropna().astype(str).unique())
            if not gran or not gran.issubset({"Yearly"}):
                if "Year-Month" not in exp.columns:
                    if "Date" in exp.columns and exp["Date"].notna().any():
                        exp["Year-Month"] = pd.to_datetime(exp["Date"], errors="coerce").dt.to_period("M").astype("string")
                    elif {"Year", "Month"}.issubset(exp.columns):
                        year = pd.to_numeric(exp["Year"], errors="coerce").astype("Int64").astype("string")
                        month = pd.to_numeric(exp["Month"], errors="coerce").astype("Int64").astype("string").str.zfill(2)
                        exp["Year-Month"] = year + "-" + month
                if "Year-Month" in exp.columns:
                    exp["_Revenue_R12M"] = pd.to_numeric(exp[denom_col], errors="coerce")
                    e = (
                        exp.groupby("Year-Month", dropna=True)["_Revenue_R12M"]
                        .sum(min_count=1)
                        .reset_index()
                    )
                    e["Period"] = pd.to_datetime(e["Year-Month"], errors="coerce").dt.to_period("M").dt.start_time
                    e = e.dropna(subset=["Period"]).groupby("Period", as_index=False)["_Revenue_R12M"].sum(min_count=1)
                    monthly = monthly.merge(e, on="Period", how="left")
                    monthly["Revenue T/O"] = monthly["_Revenue_R12M"]
                    monthly = monthly.drop(columns=["_Revenue_R12M"])

    monthly["PP Delay Events 12M"] = monthly["PP Delay Events"].rolling(12, min_periods=12).sum()
    monthly["All ATA Delay Events 12M"] = monthly["All ATA Delay Events"].rolling(12, min_periods=12).sum()

    if all_ata_source_ready:
        monthly["PP Delay Contribution % 12M"] = np.where(
            monthly["All ATA Delay Events 12M"] > 0,
            monthly["PP Delay Events 12M"] / monthly["All ATA Delay Events 12M"] * 100,
            np.nan,
        )
    else:
        monthly["PP Delay Contribution % 12M"] = np.nan

    # min_periods=12 also acts as an exposure-completeness gate: if any month in
    # the trailing window lacks Revenue T/O, no R12M rate is produced.
    monthly["Revenue T/O 12M"] = pd.to_numeric(monthly["Revenue T/O"], errors="coerce").rolling(12, min_periods=12).sum()
    monthly["PP Delay Rate /100 T/O 12M"] = np.where(
        monthly["Revenue T/O 12M"] > 0,
        monthly["PP Delay Events 12M"] / monthly["Revenue T/O 12M"] * 100,
        np.nan,
    )

    monthly["Window End"] = monthly["Period"].dt.to_period("M").dt.end_time.dt.normalize()
    monthly["Window Start"] = (monthly["Period"] - pd.DateOffset(months=11)).dt.to_period("M").dt.start_time
    return monthly[columns]
