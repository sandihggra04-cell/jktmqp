from __future__ import annotations

import numpy as np
import pandas as pd

from rel_config import SEVERE_THRESHOLD_MIN


def _pp(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    return df[df["Powerplant Flag"] == "Powerplant"].copy()


def repetitive_event_rows(df: pd.DataFrame) -> pd.DataFrame:
    pp = _pp(df).dropna(subset=["Date"]).copy()
    if pp.empty:
        return pp
    pp["Problem Group"] = pp["Problem Group"].replace("", "NEEDS CLASSIFICATION")
    pp = pp.sort_values(["A/C Reg", "ATA", "Problem Group", "Date", "Event_ID"])
    group_cols = ["A/C Reg", "ATA", "Problem Group"]
    pp["Previous Occurrence"] = pp.groupby(group_cols)["Date"].shift(1)
    pp["Days Since Previous"] = (pp["Date"] - pp["Previous Occurrence"]).dt.days
    for days in (7, 30, 90, 365):
        pp[f"Repeat ≤{days}d"] = pp["Days Since Previous"].between(0, days, inclusive="both")
    return pp


def repetitive_defect_summary(df: pd.DataFrame, window_days: int = 90, min_occurrences: int = 2) -> pd.DataFrame:
    rows = repetitive_event_rows(df)
    if rows.empty:
        return pd.DataFrame()
    flag = f"Repeat ≤{window_days}d"
    rows["_Severe"] = (rows["Tech Dur"].fillna(-1) >= SEVERE_THRESHOLD_MIN).astype(int)
    rows["_Operational"] = rows["Event Type"].str.upper().isin(["RTA", "RTB", "RTO"]).astype(int)
    out = rows.groupby(["A/C Reg", "A/C Type", "ATA", "Problem Group"], dropna=False).agg(
        Occurrences=("Occurrence", "sum"),
        **{
            "Delay Minutes": ("Tech Dur", "sum"),
            "Severe": ("_Severe", "sum"),
            "RTA/RTB/RTO": ("_Operational", "sum"),
            "First Occurrence": ("Date", "min"),
            "Last Occurrence": ("Date", "max"),
            f"Repeats ≤{window_days}d": (flag, "sum"),
            "Median Recurrence Days": ("Days Since Previous", "median"),
            "Last Rectification": ("Rectification", "last"),
            "Last Action Type": ("Rectification Action", "last"),
        },
    ).reset_index()
    out = out[out["Occurrences"] >= min_occurrences].copy()
    if out.empty:
        return out
    out["Recurrence Span (days)"] = (out["Last Occurrence"] - out["First Occurrence"]).dt.days
    out["Repeat Density %"] = np.where(
        out["Occurrences"] > 1,
        out[f"Repeats ≤{window_days}d"] / (out["Occurrences"] - 1) * 100,
        0,
    )
    return out.sort_values([f"Repeats ≤{window_days}d", "Occurrences", "Delay Minutes"], ascending=False)


def rectification_effectiveness(df: pd.DataFrame, recurrence_days: int = 30) -> pd.DataFrame:
    rows = repetitive_event_rows(df)
    if rows.empty:
        return pd.DataFrame()
    # Shift the next same-defect occurrence backwards to the action/event that preceded it.
    group_cols = ["A/C Reg", "ATA", "Problem Group"]
    rows["Next Occurrence"] = rows.groupby(group_cols)["Date"].shift(-1)
    rows["Days To Next Same Defect"] = (rows["Next Occurrence"] - rows["Date"]).dt.days
    scope_end = rows["Date"].max()
    rows["Observation Days Available"] = (scope_end - rows["Date"]).dt.days
    eligible = rows[rows["Observation Days Available"] >= recurrence_days].copy()
    if eligible.empty:
        return pd.DataFrame()
    eligible["Recurred"] = eligible["Days To Next Same Defect"].between(0, recurrence_days, inclusive="both")
    eligible["No Recurrence Observed"] = ~eligible["Recurred"]
    out = eligible.groupby("Rectification Action", dropna=False).agg(
        **{
            "Eligible Actions": ("Occurrence", "sum"),
            f"Recurrence ≤{recurrence_days}d": ("Recurred", "sum"),
            "Median Days To Recurrence": ("Days To Next Same Defect", "median"),
            "Affected Aircraft": ("A/C Reg", "nunique"),
            "Delay Minutes": ("Tech Dur", "sum"),
        }
    ).reset_index()
    out[f"Recurrence ≤{recurrence_days}d %"] = np.where(
        out["Eligible Actions"] > 0,
        out[f"Recurrence ≤{recurrence_days}d"] / out["Eligible Actions"] * 100,
        np.nan,
    )
    return out.sort_values([f"Recurrence ≤{recurrence_days}d %", "Eligible Actions"], ascending=False)


def classification_health(df: pd.DataFrame) -> dict:
    pp = _pp(df)
    total = len(pp)
    if total == 0:
        return {"total": 0, "classified": 0, "suggested": 0, "needs": 0, "coverage_pct": None}
    statuses = pp["KeyProblem Classification"].value_counts()
    classified = int(statuses.get("CLASSIFIED / NORMALIZED", 0))
    suggested = int(statuses.get("SUGGESTED FROM FREE TEXT", 0))
    needs = int(statuses.get("NEEDS CLASSIFICATION", 0))
    return {
        "total": total,
        "classified": classified,
        "suggested": suggested,
        "needs": needs,
        "coverage_pct": (classified / total * 100) if total else None,
        "actionable_coverage_pct": ((classified + suggested) / total * 100) if total else None,
    }


def needs_classification(df: pd.DataFrame) -> pd.DataFrame:
    pp = _pp(df)
    if pp.empty:
        return pd.DataFrame()
    mask = pp["KeyProblem Classification"].isin(["SUGGESTED FROM FREE TEXT", "NEEDS CLASSIFICATION"])
    cols = [
        "Date", "A/C Type", "A/C Reg", "ATA", "Sub ATA", "Tech Dur", "KeyProblem", "Problem",
        "Problem Group", "System", "Component", "Failure Mode", "KeyProblem Classification", "Rectification",
    ]
    return pp.loc[mask, cols].sort_values(["KeyProblem Classification", "Tech Dur"], ascending=[False, False])


def tail_watchlist(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    pp = _pp(df).copy()
    if pp.empty:
        return pd.DataFrame()
    repeats = repetitive_event_rows(pp)
    repeat_count = repeats.groupby("A/C Reg")["Repeat ≤90d"].sum().rename("Repeat ≤90d")
    pp["_Severe"] = (pp["Tech Dur"].fillna(-1) >= SEVERE_THRESHOLD_MIN).astype(int)
    pp["_Operational"] = pp["Event Type"].str.upper().isin(["RTA", "RTB", "RTO"]).astype(int)
    base = pp.groupby(["A/C Reg", "A/C Type"], dropna=False).agg(
        **{
            "PP Events": ("Occurrence", "sum"),
            "Delay Minutes": ("Tech Dur", "sum"),
            "Severe": ("_Severe", "sum"),
            "RTA/RTB/RTO": ("_Operational", "sum"),
            "First Event": ("Date", "min"),
            "Last Event": ("Date", "max"),
        }
    ).reset_index()
    base = base.merge(repeat_count, on="A/C Reg", how="left")
    base["Repeat ≤90d"] = base["Repeat ≤90d"].fillna(0).astype(int)

    # Dominant problem and ATA per tail.
    dominant_problem = (
        pp.groupby(["A/C Reg", "Problem Group"])["Tech Dur"].sum().reset_index()
        .sort_values(["A/C Reg", "Tech Dur"], ascending=[True, False])
        .drop_duplicates("A/C Reg")
        .set_index("A/C Reg")["Problem Group"]
    )
    dominant_ata = (
        pp.groupby(["A/C Reg", "ATA"])["Tech Dur"].sum().reset_index()
        .sort_values(["A/C Reg", "Tech Dur"], ascending=[True, False])
        .drop_duplicates("A/C Reg")
        .set_index("A/C Reg")["ATA"]
    )
    base["Dominant Problem"] = base["A/C Reg"].map(dominant_problem).fillna("—")
    base["Top ATA"] = base["A/C Reg"].map(dominant_ata).apply(lambda x: f"ATA {int(x)}" if pd.notna(x) else "—")

    def pct_rank(s: pd.Series) -> pd.Series:
        if len(s) <= 1 or s.nunique(dropna=False) <= 1:
            return pd.Series(np.full(len(s), 50.0), index=s.index)
        return s.rank(pct=True, method="average") * 100

    score = (
        pct_rank(base["PP Events"]) * 0.28
        + pct_rank(base["Delay Minutes"]) * 0.30
        + pct_rank(base["Severe"]) * 0.17
        + pct_rank(base["RTA/RTB/RTO"]) * 0.12
        + pct_rank(base["Repeat ≤90d"]) * 0.13
    )
    base["Priority Index"] = score.round(1)
    if len(base) < 5:
        base["Status"] = "INSUFFICIENT BASELINE"
    else:
        base["Status"] = pd.cut(
            base["Priority Index"],
            bins=[-np.inf, 45, 65, 80, np.inf],
            labels=["NORMAL", "WATCH", "HIGH", "CRITICAL"],
            right=False,
        ).astype(str)
    cols = [
        "Status", "Priority Index", "A/C Reg", "A/C Type", "PP Events", "Delay Minutes", "Severe",
        "RTA/RTB/RTO", "Repeat ≤90d", "Top ATA", "Dominant Problem", "First Event", "Last Event",
    ]
    return base.sort_values(["Priority Index", "Delay Minutes"], ascending=False)[cols].head(top_n)


def subata_summary(df: pd.DataFrame, ata: int | None = None, metric: str = "Delay Minutes") -> pd.DataFrame:
    pp = _pp(df).copy()
    if ata is not None:
        pp = pp[pp["ATA"] == ata]
    if pp.empty:
        return pd.DataFrame()
    pp["Sub ATA Label"] = pp["Sub ATA"].apply(lambda x: "N/A" if pd.isna(x) else str(int(x)))
    out = pp.groupby(["ATA", "Sub ATA Label"], dropna=False).agg(
        Events=("Occurrence", "sum"),
        **{"Delay Minutes": ("Tech Dur", "sum"), "Aircraft": ("A/C Reg", "nunique")},
    ).reset_index()
    col = "Events" if metric == "Events" else "Delay Minutes"
    total = out[col].sum()
    out["Share %"] = np.where(total > 0, out[col] / total * 100, 0)
    return out.sort_values([col, "Events"], ascending=False)


def operational_impact_by_ata(df: pd.DataFrame) -> pd.DataFrame:
    pp = _pp(df).copy()
    if pp.empty:
        return pd.DataFrame()
    event = pp["Event Type"].str.upper()
    pp["RTA"] = event.eq("RTA").astype(int)
    pp["RTB"] = event.eq("RTB").astype(int)
    pp["RTO"] = event.eq("RTO").astype(int)
    out = pp.groupby("ATA").agg(
        Events=("Occurrence", "sum"),
        **{"Delay Minutes": ("Tech Dur", "sum"), "RTA": ("RTA", "sum"), "RTB": ("RTB", "sum"), "RTO": ("RTO", "sum")},
    ).reset_index()
    out["Operational Interruptions"] = out[["RTA", "RTB", "RTO"]].sum(axis=1)
    out["Operational Impact %"] = np.where(out["Events"] > 0, out["Operational Interruptions"] / out["Events"] * 100, 0)
    return out.sort_values(["Operational Interruptions", "Delay Minutes"], ascending=False)


def concentration_summary(df: pd.DataFrame, dimension: str, metric: str = "Delay Minutes", top_n: int = 15) -> pd.DataFrame:
    pp = _pp(df).copy()
    if pp.empty or dimension not in pp.columns:
        return pd.DataFrame()
    pp[dimension] = pp[dimension].astype("string").fillna("").str.strip().replace("", "UNKNOWN")
    out = pp.groupby(dimension, dropna=False).agg(
        Events=("Occurrence", "sum"),
        **{"Delay Minutes": ("Tech Dur", "sum"), "Aircraft": ("A/C Reg", "nunique")},
    ).reset_index()
    col = "Events" if metric == "Events" else "Delay Minutes"
    total = out[col].sum()
    out["Share %"] = np.where(total > 0, out[col] / total * 100, 0)
    return out.sort_values([col, "Events"], ascending=False).head(top_n)


def engine_position_summary(df: pd.DataFrame, metric: str = "Delay Minutes") -> pd.DataFrame:
    return concentration_summary(df, "Engine Position", metric=metric, top_n=10)


def problem_taxonomy_summary(df: pd.DataFrame, metric: str = "Delay Minutes", top_n: int = 30) -> pd.DataFrame:
    pp = _pp(df).copy()
    if pp.empty:
        return pd.DataFrame()
    out = pp.groupby(["System", "Component", "Failure Mode", "Problem Group"], dropna=False).agg(
        Events=("Occurrence", "sum"),
        **{"Delay Minutes": ("Tech Dur", "sum"), "Aircraft": ("A/C Reg", "nunique")},
    ).reset_index()
    col = "Events" if metric == "Events" else "Delay Minutes"
    return out.sort_values([col, "Events"], ascending=False).head(top_n)


def frequency_impact_data(df: pd.DataFrame) -> pd.DataFrame:
    pp = _pp(df).copy()
    if pp.empty:
        return pd.DataFrame()
    pp["Problem Group"] = pp["Problem Group"].replace("", "NEEDS CLASSIFICATION")
    out = pp.groupby("Problem Group").agg(
        Events=("Occurrence", "sum"),
        **{"Delay Minutes": ("Tech Dur", "sum"), "Aircraft": ("A/C Reg", "nunique")},
    ).reset_index()
    out["Avg Delay / Event"] = np.where(out["Events"] > 0, out["Delay Minutes"] / out["Events"], 0)
    return out.sort_values(["Delay Minutes", "Events"], ascending=False)


def pareto_80_20(df: pd.DataFrame, dimension: str, metric: str = "Delay Minutes") -> dict:
    summary = concentration_summary(df, dimension, metric=metric, top_n=100000)
    if summary.empty:
        return {"categories": 0, "top_20_categories": 0, "contribution_pct": None}
    col = "Events" if metric == "Events" else "Delay Minutes"
    n = len(summary)
    top_n = max(1, int(np.ceil(n * 0.20)))
    total = summary[col].sum()
    contribution = summary.head(top_n)[col].sum() / total * 100 if total else None
    return {"categories": n, "top_20_categories": top_n, "contribution_pct": contribution}


def engineering_focus_v2(current_df: pd.DataFrame, comparator_df: pd.DataFrame | None = None) -> list[dict]:
    """Return management-readable engineering priority signals.

    The function prefers signals that are actionable from delay-only data:
    dominant ATA burden, repetitive defects, bad-actor tails, and classification
    gaps. If a comparable prior scope is supplied, deterioration is calculated
    apples-to-apples for the same ATA rather than full-year vs partial-year.
    """
    pp = _pp(current_df)
    if pp.empty:
        return [{"label": "Engineering Status", "message": "Tidak ada Powerplant event pada scope aktif.", "priority": "INFO"}]

    signals: list[dict] = []
    ata = pp.groupby("ATA").agg(Events=("Occurrence", "sum"), **{"Delay Minutes": ("Tech Dur", "sum")}).reset_index()
    ata = ata.sort_values("Delay Minutes", ascending=False)
    if not ata.empty:
        top = ata.iloc[0]
        total = float(ata["Delay Minutes"].sum())
        share = float(top["Delay Minutes"] / total * 100) if total > 0 else 0.0
        if len(ata) >= 2:
            message = f"ATA {int(top['ATA'])} · {top['Delay Minutes']:,.0f} delay min · {share:.1f}% of PP delay burden"
            priority = "HIGH" if share >= 30 else "REVIEW"
        else:
            message = f"ATA {int(top['ATA'])} · {top['Delay Minutes']:,.0f} delay min · single ATA chapter in current scope"
            priority = "REVIEW"
        signals.append({
            "label": "Dominant ATA / Delay Burden",
            "message": message,
            "priority": priority,
        })

    repeats = repetitive_defect_summary(current_df, window_days=90, min_occurrences=2)
    if not repeats.empty:
        row = repeats.iloc[0]
        signals.append({
            "label": "Repetitive Defect",
            "message": f"{row['A/C Reg']} · ATA {int(row['ATA'])} · {row['Problem Group']} · {int(row['Occurrences'])} events · {int(row['Repeats ≤90d'])} repeats ≤90d · {row['Delay Minutes']:,.0f} min",
            "priority": "HIGH" if row["Repeats ≤90d"] >= 2 else "WATCH",
        })

    # Comparator deterioration for the same current dominant ATA.
    if comparator_df is not None and not comparator_df.empty and not ata.empty:
        top_ata = int(ata.iloc[0]["ATA"])
        cur = float(pp.loc[pp["ATA"] == top_ata, "Tech Dur"].fillna(0).sum())
        prev_pp = _pp(comparator_df)
        prev = float(prev_pp.loc[prev_pp["ATA"] == top_ata, "Tech Dur"].fillna(0).sum())
        if prev > 0:
            delta = (cur - prev) / prev * 100
            if delta > 0:
                signals.append({
                    "label": "Deterioration vs Comparator",
                    "message": f"ATA {top_ata} · +{delta:.1f}% vs comparator · {prev:,.0f} → {cur:,.0f} min",
                    "priority": "HIGH" if delta >= 25 else "WATCH",
                })

    watch = tail_watchlist(current_df, top_n=1)
    if not watch.empty and len(signals) < 4:
        row = watch.iloc[0]
        if str(row["Status"]) != "INSUFFICIENT BASELINE":
            signals.append({
                "label": "Aircraft / Tail Watch",
                "message": f"{row['A/C Reg']} · Priority Index {row['Priority Index']:.1f} · {row['Status']} · {int(row['PP Events'])} events · {row['Delay Minutes']:,.0f} min · {int(row['Repeat ≤90d'])} repeats ≤90d",
                "priority": str(row["Status"]),
            })

    health = classification_health(current_df)
    if health.get("needs", 0) > 0 and len(signals) < 4:
        signals.append({
            "label": "Classification Coverage",
            "message": f"{health['needs']} events need KeyProblem classification · {health.get('actionable_coverage_pct', 0):.1f}% actionable coverage",
            "priority": "DATA REVIEW",
        })

    # Ensure a high-impact event remains visible when no deterioration signal exists.
    if len(signals) < 3:
        worst = pp.sort_values("Tech Dur", ascending=False).head(1)
        if not worst.empty:
            row = worst.iloc[0]
            signals.append({
                "label": "High-Impact Event",
                "message": f"{row['Tech Dur']:,.0f} min · ATA {int(row['ATA']) if pd.notna(row['ATA']) else '—'} · {row['A/C Reg'] or 'reg N/A'} · {row['Problem Group'] or row['Problem']}",
                "priority": "REVIEW",
            })
    return signals[:4]
