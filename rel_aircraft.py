from __future__ import annotations

import re

import pandas as pd


# Project rule:
# A330-200, A330-300, and A330-900 share one utilization denominator,
# therefore they are presented and filtered as one A330 fleet family.
# A330-800 is intentionally NOT grouped by this rule unless the project
# convention is explicitly expanded later.


def canonical_aircraft_type(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    compact = re.sub(r"[^a-z0-9]+", "", text.casefold())
    compact = compact.replace("airbus", "")

    # Accept labels such as A330-200 / A330200 / A330-243,
    # A330-300 / A330-343, and A330-900 / A330-941 / A330-900neo.
    if re.match(r"^a?330(?:2\d{2}|3\d{2}|9\d{2})(?:neo)?$", compact):
        return "A330"

    if compact in {"a330", "330"}:
        return "A330"

    return text


def apply_aircraft_grouping(df: pd.DataFrame, column: str = "A/C Type") -> pd.DataFrame:
    """Return a copy with project fleet-family grouping applied.

    The original source label is preserved in `<column> Raw` so detailed source
    provenance remains available if engineering needs it later.
    """
    if df is None or df.empty or column not in df.columns:
        return df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()

    out = df.copy()
    raw_col = f"{column} Raw"
    if raw_col not in out.columns:
        out[raw_col] = out[column]

    out[column] = out[column].map(canonical_aircraft_type)
    return out
