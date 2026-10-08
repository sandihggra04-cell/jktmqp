from __future__ import annotations
import re
import pandas as pd

EXPECTED = [
    "ESN", "removal date", "Induction Date", "reason of removal", "MRO",
    "Scope of work", "Release date", "Engine Owner", "Progres", "TAT",
    "TSN", "CSN", "TSLV", "engine type", "lessor", "7B config", "SV cost",
    "Forecast Release Date", "Last Update", "Key Issue", "Next Action",
]

ALIASES = {
    "ESN": [
        "APU SN", "APU Serial Number", "APU Serial No", "APU Serial No.",
        "APU Serial", "APU S/N", "Serial Number", "Serial No", "Serial No."
    ],
    "removal date": ["removal date", "Removal Date", "Date Removal", "Removed Date"],
    "Induction Date": ["Induction Date", "induction date", "Induction", "Date Induction"],
    "reason of removal": [
        "reason of removal", "Reason of Removal", "Removal Reason", "Reason Removal",
        "Shop Visit Reason", "SV Reason", "Title"
    ],
    "MRO": ["MRO", "MRO Facility", "MRO Shop", "Repair Shop"],
    "Scope of work": ["Scope of work", "Scope of Work", "Workscope", "Work Scope", "SOW"],
    "Release date": ["Release date", "Release Date", "Actual Release Date", "Date Release"],
    "Engine Owner": ["APU Owner", "Project Owner", "PIC", "Owner"],
    "Progres": ["Progres", "Progress", "Current Phase", "Phase", "Status", "SV Status", "Shop Visit Status"],
    "TAT": ["TAT", "Turnaround Time", "Turn Around Time"],
    "TSN": ["TSN", "Time Since New"],
    "CSN": ["CSN", "Cycle Since New", "Cycles Since New"],
    "TSLV": ["TSLV", "Time Since Last Visit", "Time Since Last SV"],
    "engine type": ["APU Type", "APU Model", "APU Family", "APU type"],
    "lessor": ["lessor", "Lessor", "Asset Owner", "APU Lessor"],
    "7B config": ["Configuration", "Config", "APU Configuration"],
    "SV cost": ["SV cost", "SV Cost", "Shop Visit Cost", "SV Cost Actual", "Cost", "APU SV Cost"],
    "Forecast Release Date": ["Forecast Release Date", "Forecast Release", "Expected Release Date"],
    "Last Update": ["Last Update", "Updated Date", "Last Updated", "Modified", "Modified Date"],
    "Key Issue": ["Key Issue", "Issue", "Current Issue", "Major Issue"],
    "Next Action": ["Next Action", "Action", "Follow Up", "Follow-up", "Next Step"],
}

def _norm_col(value):
    text = str(value or "").strip().lower().replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "", text)

def _first(df, names):
    lookup = {_norm_col(c): c for c in df.columns}
    for name in names:
        key = _norm_col(name)
        if key in lookup:
            return lookup[key]
    return None

def esn_source_column(df):
    """Compatibility helper: returns the source APU serial-number column."""
    return _first(df, ALIASES["ESN"])

def recognized_columns(df):
    result = {}
    for canonical in EXPECTED:
        src = esn_source_column(df) if canonical == "ESN" else _first(df, ALIASES.get(canonical, [canonical]))
        if src is not None:
            result[canonical] = str(src)
    return result

def promote_header_row(raw_no_header, max_rows=12):
    if raw_no_header is None or raw_no_header.empty:
        return pd.DataFrame()
    alias_keys = set()
    for names in ALIASES.values():
        alias_keys.update(_norm_col(x) for x in names)
    best_idx, best_score = None, 0
    for idx in range(min(max_rows, len(raw_no_header))):
        score = sum(1 for value in raw_no_header.iloc[idx].tolist() if _norm_col(value) in alias_keys)
        if score > best_score:
            best_idx, best_score = idx, score
    if best_idx is None or best_score < 2:
        return pd.DataFrame()
    headers = [str(v).strip() if pd.notna(v) else "" for v in raw_no_header.iloc[best_idx].tolist()]
    seen, safe_headers = {}, []
    for pos, header in enumerate(headers):
        base = header or f"Column_{pos+1}"
        n = seen.get(base, 0)
        seen[base] = n + 1
        safe_headers.append(base if n == 0 else f"{base}_{n+1}")
    promoted = raw_no_header.iloc[best_idx + 1:].copy()
    promoted.columns = safe_headers
    return promoted.dropna(how="all").reset_index(drop=True)

def _num(s):
    return pd.to_numeric(
        s.astype("string")
        .str.replace(",", "", regex=False)
        .str.replace(r"[^0-9.\-]", "", regex=True),
        errors="coerce",
    )

def _txt(s):
    return s.astype("string").fillna("").str.replace(r"\.0$", "", regex=True).str.strip()

def canonical_phase(value, phases):
    text = str(value or "").strip()
    if not text:
        return "Unspecified"
    key = text.lower()
    synonyms = {
        "planned": "Planned",
        "removed": "Removed / In Transit",
        "in transit": "Removed / In Transit",
        "removed / in transit": "Removed / In Transit",
        "removed/in transit": "Removed / In Transit",
        "inducted": "Inducted",
        "induction": "Inducted",
        "disassembly": "Disassembly",
        "inspection": "Inspection",
        "repair": "Repair / Material",
        "material": "Repair / Material",
        "repair / material": "Repair / Material",
        "repair/material": "Repair / Material",
        "assembly": "Assembly",
        "test cell": "Test Cell",
        "testcell": "Test Cell",
        "ready for release": "Ready for Release",
        "ready release": "Ready for Release",
        "on hold": "On Hold",
        "hold": "On Hold",
        "completed": "Completed",
        "complete": "Completed",
        "closed": "Completed",
    }
    if key in synonyms:
        return synonyms[key]
    for phase in phases:
        if key == phase.lower():
            return phase
    return text

def clean_data(raw, phases, max_tat=2000):
    raw = pd.DataFrame() if raw is None else raw
    out = pd.DataFrame(index=raw.index)

    for col in EXPECTED:
        src = esn_source_column(raw) if col == "ESN" else _first(raw, ALIASES.get(col, [col]))
        out[col] = raw[src] if src is not None else pd.NA

    out["ESN"] = _txt(out["ESN"])
    out = out[out["ESN"].ne("")].copy()

    for col in ["removal date", "Induction Date", "Release date", "Forecast Release Date", "Last Update"]:
        out[col] = pd.to_datetime(out[col], errors="coerce", format="mixed", dayfirst=True)

    for col in ["TAT", "TSN", "CSN", "TSLV", "SV cost"]:
        out[col] = _num(out[col])

    out["Source TAT"] = out["TAT"]

    for col in [
        "MRO", "Engine Owner", "Progres", "engine type", "lessor", "7B config",
        "Key Issue", "Next Action", "Scope of work", "reason of removal",
    ]:
        out[col] = _txt(out[col])

    today = pd.Timestamp.today().normalize()
    calc_tat = (out["Release date"].fillna(today) - out["Induction Date"]).dt.days
    has_induction = out["Induction Date"].notna()
    out.loc[has_induction, "TAT"] = calc_tat[has_induction]

    out["Phase"] = out["Progres"].apply(lambda x: canonical_phase(x, phases))
    out.loc[out["Release date"].notna(), "Phase"] = "Completed"

    out["Status"] = "Active"
    out.loc[out["Phase"].eq("Completed"), "Status"] = "Completed"

    out["TAT valid"] = out["TAT"].notna() & out["TAT"].ge(0) & out["TAT"].le(max_tat)
    out["TAT issue"] = ""
    out.loc[out["TAT"].isna(), "TAT issue"] = "Missing TAT / Induction Date"
    out.loc[out["TAT"].lt(0), "TAT issue"] = "Negative TAT"
    out.loc[out["TAT"].gt(max_tat), "TAT issue"] = "Implausible TAT — check dates"

    out["Release Year"] = out["Release date"].dt.year
    out["Release Quarter Period"] = out["Release date"].dt.to_period("Q")
    out["Release Quarter"] = out["Release Quarter Period"].astype("string")

    hist = out[(out["Status"] == "Completed") & out["TAT valid"]].copy()
    overall_p75 = hist["TAT"].quantile(.75) if len(hist) >= 4 else pd.NA

    by_type = pd.DataFrame()
    if not hist.empty:
        by_type = (
            hist.dropna(subset=["engine type"])
            .groupby("engine type")["TAT"]
            .agg(count="count", p75=lambda s: s.quantile(.75))
        )

    def p75_for(row):
        apu_type = row["engine type"]
        if (
            not by_type.empty
            and apu_type
            and apu_type in by_type.index
            and by_type.loc[apu_type, "count"] >= 3
        ):
            return by_type.loc[apu_type, "p75"]
        return overall_p75

    out["Historical P75 TAT"] = out.apply(p75_for, axis=1) if not out.empty else pd.NA

    def simple_flag(row):
        if row["Status"] != "Active":
            return ""
        if not bool(row["TAT valid"]):
            return "Check Data"
        if row["Phase"] == "On Hold":
            return "Review"
        if str(row["Key Issue"]).strip():
            return "Review"
        if pd.notna(row["Historical P75 TAT"]) and row["TAT"] > row["Historical P75 TAT"]:
            return "Review"
        return "Normal"

    out["Flag"] = out.apply(simple_flag, axis=1)
    return out
