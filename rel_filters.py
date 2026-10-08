from __future__ import annotations

import re
from typing import Iterable

import pandas as pd


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def filter_scope(
    df: pd.DataFrame,
    start_date,
    end_date,
    aircraft_type: str | None = None,
    stations: Iterable[str] | None = None,
    routes: Iterable[str] | None = None,
) -> pd.DataFrame:
    out = df.copy()
    if start_date is not None:
        out = out[out["Date"] >= pd.Timestamp(start_date)]
    if end_date is not None:
        out = out[out["Date"] <= pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)]
    if aircraft_type and aircraft_type != "All Aircraft":
        out = out[out["A/C Type"] == aircraft_type]
    stations = [x for x in _as_list(stations) if x]
    if stations:
        out = out[out["Sta Dep"].isin(stations) | out["Sta Arr"].isin(stations)]
    routes = [x for x in _as_list(routes) if x]
    if routes:
        out = out[out["Route"].isin(routes)]
    return out


def keyword_filter(
    df: pd.DataFrame,
    query: str,
    columns: list[str],
    mode: str = "Any words",
) -> pd.DataFrame:
    query = (query or "").strip()
    valid_columns = [c for c in columns if c in df.columns]
    if not query or not valid_columns:
        return df

    combined = df[valid_columns].fillna("").astype(str).agg(" ".join, axis=1)

    if mode == "Exact phrase":
        mask = combined.str.contains(query, case=False, regex=False, na=False)
    elif mode == "All words":
        words = [w for w in re.split(r"\s+", query) if w]
        mask = pd.Series(True, index=df.index)
        for word in words:
            mask &= combined.str.contains(word, case=False, regex=False, na=False)
    elif mode == "Regex (advanced)":
        try:
            mask = combined.str.contains(query, case=False, regex=True, na=False)
        except re.error:
            return df.iloc[0:0]
    else:  # Any words
        words = [w for w in re.split(r"\s+", query) if w]
        mask = pd.Series(False, index=df.index)
        for word in words:
            mask |= combined.str.contains(word, case=False, regex=False, na=False)
    return df[mask]


def filter_analysis(
    df: pd.DataFrame,
    atas: Iterable[int] | None = None,
    severity: str = "All",
    event_types: Iterable[str] | None = None,
    keyword: str = "",
    keyword_columns: list[str] | None = None,
    keyword_mode: str = "Any words",
) -> pd.DataFrame:
    out = df.copy()
    atas = [int(x) for x in _as_list(atas) if pd.notna(x)]
    if atas:
        out = out[out["ATA"].isin(atas)]
    if severity == "Severe only":
        out = out[out["Severe Flag"] == "Severe"]
    elif severity == "Non-severe only":
        out = out[out["Severe Flag"] != "Severe"]
    event_types = [str(x) for x in _as_list(event_types) if x]
    if event_types:
        out = out[out["Event Type"].isin(event_types)]
    if keyword:
        out = keyword_filter(out, keyword, keyword_columns or [], keyword_mode)
    return out
