from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd

EVENT_METRICS = ["IFSD", "RTO", "RTB", "UER", "ERR", "SVR", "D&C"]
FLEET_ORDER = ["B737", "B777", "A330"]

RATE_CONFIG = {
    "IFSD": {"exposure": "FH", "multiplier": 1000.0, "unit": "per 1,000 FH"},
    "RTO": {"exposure": "FC", "multiplier": 1000.0, "unit": "per 1,000 FC"},
    "RTB": {"exposure": "FC", "multiplier": 100.0, "unit": "per 100 FC"},
    "UER": {"exposure": "FH", "multiplier": 1000.0, "unit": "per 1,000 FH"},
    "ERR": {"exposure": "FH", "multiplier": 1000.0, "unit": "per 1,000 FH"},
    "SVR": {"exposure": "FH", "multiplier": 1000.0, "unit": "per 1,000 FH"},
    "D&C": {"exposure": "FC", "multiplier": 100.0, "unit": "per 100 FC"},
}


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().casefold())


def infer_operational_fleet(source_name: str) -> str | None:
    """Infer B737/B777/A330 from standard fleet or engine-family filenames."""
    token = _norm(Path(source_name).stem)
    if not token:
        return None
    if any(x in token for x in ["b737", "737", "cfm567b", "leap1b"]):
        return "B737"
    if any(x in token for x in ["b777", "777", "ge90"]):
        return "B777"
    if any(x in token for x in ["a330", "330", "trent700", "trent7000"]):
        return "A330"
    if "trent" in token and not any(x in token for x in ["trent500", "trent800", "trent900", "trent1000", "trentxwb"]):
        return "A330"
    return None


def _excel_input(source: Any) -> Any:
    if isinstance(source, (str, Path)):
        return source
    if isinstance(source, (bytes, bytearray)):
        return BytesIO(bytes(source))
    if hasattr(source, "getvalue"):
        return BytesIO(bytes(source.getvalue()))
    if hasattr(source, "read"):
        try:
            source.seek(0)
        except Exception:
            pass
        data = source.read()
        try:
            source.seek(0)
        except Exception:
            pass
        return BytesIO(bytes(data))
    return source


def _sheet_map(excel: pd.ExcelFile) -> dict[str, str]:
    return {_norm(name): name for name in excel.sheet_names}


def _resolve_sheet(excel: pd.ExcelFile, logical_name: str) -> str | None:
    smap = _sheet_map(excel)
    key = _norm(logical_name)
    if key in smap:
        return smap[key]
    # Small tolerance for D&C labels while keeping the template deterministic.
    aliases = {
        "dc": ["dandc", "delaycancellation"],
        "dcperata": ["dandcperata", "dcata", "dandcata"],
    }
    for alt in aliases.get(key, []):
        if alt in smap:
            return smap[alt]
    return None


def _year_value(value: object) -> int | None:
    try:
        y = int(float(value))
    except Exception:
        return None
    return y if 2000 <= y <= 2100 else None


def _read_utilization(excel: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(excel, sheet_name=sheet_name, header=None, usecols="B:N")
    if raw.empty or raw.shape[1] < 13:
        raise ValueError("Utilization!B:N tidak sesuai template yang diharapkan.")

    records: dict[pd.Timestamp, dict[str, object]] = {}
    current_year: int | None = None
    for _, row in raw.iterrows():
        y = _year_value(row.iloc[0])
        if y is not None:
            current_year = y
            continue
        if current_year is None:
            continue
        label = _norm(row.iloc[0])
        if label not in {"hours", "hour", "fh", "cycles", "cycle", "fc"}:
            continue
        field = "FH" if label in {"hours", "hour", "fh"} else "FC"
        for month_no, value in enumerate(row.iloc[1:13].tolist(), start=1):
            numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
            date = pd.Timestamp(current_year, month_no, 1)
            rec = records.setdefault(date, {"Date": date, "Year": current_year, "Month": month_no})
            rec[field] = float(numeric) if pd.notna(numeric) else np.nan

    if not records:
        raise ValueError("Baris hours/cycles pada Utilization!B:N tidak ditemukan.")
    return pd.DataFrame(records.values()).sort_values("Date").reset_index(drop=True)


def _read_event_sheet(excel: pd.ExcelFile, sheet_name: str, metric: str) -> pd.DataFrame:
    raw = pd.read_excel(excel, sheet_name=sheet_name, header=None, usecols="B:N")
    if raw.empty or raw.shape[1] < 13:
        raise ValueError(f"{sheet_name}!B:N tidak sesuai template.")

    rows: list[dict[str, object]] = []
    current_year: int | None = None
    for _, row in raw.iterrows():
        y = _year_value(row.iloc[0])
        if y is not None:
            current_year = y
            continue
        if current_year is None or _norm(row.iloc[0]) != "event":
            continue
        for month_no, value in enumerate(row.iloc[1:13].tolist(), start=1):
            numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
            rows.append({
                "Date": pd.Timestamp(current_year, month_no, 1),
                metric: float(numeric) if pd.notna(numeric) else np.nan,
            })

    if not rows:
        raise ValueError(f"Baris Event tidak ditemukan pada sheet {sheet_name}.")
    return pd.DataFrame(rows).drop_duplicates(subset=["Date"], keep="last").sort_values("Date")


def _read_dc_ata(excel: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(excel, sheet_name=sheet_name, header=None)
    if raw.empty or raw.shape[1] < 35:
        raise ValueError("Sheet D&C per ata tidak memiliki 12 blok bulanan yang diharapkan.")

    rows: list[dict[str, object]] = []
    for idx in range(len(raw)):
        year = _year_value(raw.iat[idx, 1] if raw.shape[1] > 1 else None)
        if year is None:
            continue
        data_start = idx + 2  # year row -> month row -> ATA 71 row
        if data_start + 9 >= len(raw):
            continue
        for month_no in range(1, 13):
            ata_col = 1 + (month_no - 1) * 3
            count_col = ata_col + 1
            if count_col >= raw.shape[1]:
                continue
            for r in range(data_start, min(data_start + 10, len(raw))):
                ata_value = pd.to_numeric(pd.Series([raw.iat[r, ata_col]]), errors="coerce").iloc[0]
                if pd.isna(ata_value):
                    continue
                ata = int(ata_value)
                if ata < 71 or ata > 80:
                    continue
                count_value = pd.to_numeric(pd.Series([raw.iat[r, count_col]]), errors="coerce").iloc[0]
                if pd.isna(count_value):
                    continue
                rows.append({
                    "Date": pd.Timestamp(year, month_no, 1),
                    "Year": year,
                    "Month": month_no,
                    "ATA": ata,
                    "D&C ATA Events": float(count_value),
                })

    return pd.DataFrame(rows).sort_values(["Date", "ATA"]).reset_index(drop=True) if rows else pd.DataFrame(
        columns=["Date", "Year", "Month", "ATA", "D&C ATA Events"]
    )


def _read_targets(excel: pd.ExcelFile, sheet_name: str | None) -> dict[str, float]:
    if not sheet_name:
        return {}
    raw = pd.read_excel(excel, sheet_name=sheet_name, header=None)
    labels = ["IFSD", "RTO", "RTB", "UER", "ERR", "SVR", "D&C", "DISPATCH"]
    norm_labels = [_norm(x) for x in labels]

    candidates: list[tuple[int, dict[str, float]]] = []
    for r in range(max(len(raw) - 1, 0)):
        for c in range(max(raw.shape[1] - len(labels) + 1, 0)):
            seq = [_norm(raw.iat[r, c + j]) for j in range(len(labels))]
            if seq != norm_labels:
                continue
            vals = [pd.to_numeric(pd.Series([raw.iat[r + 1, c + j]]), errors="coerce").iloc[0] for j in range(len(labels))]
            numeric_count = sum(pd.notna(v) for v in vals)
            if numeric_count >= 7:
                candidate = {label: float(v) for label, v in zip(labels, vals) if pd.notna(v)}
                candidates.append((numeric_count, candidate))
    if not candidates:
        return {}
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def parse_operational_reliability_workbook(
    source: Any,
    source_name: str,
    fleet: str,
) -> dict[str, object]:
    """Parse the fixed fleet reliability workbook without using Summary calculations.

    Source-of-truth cells are the raw monthly Utilization, event sheets, and D&C per ATA.
    Derived rolling rates are recalculated separately by the dashboard.
    """
    ext = Path(source_name).suffix.lower()
    if ext not in {".xlsx", ".xls"}:
        raise ValueError("Operational Reliability Events membutuhkan workbook XLSX/XLS.")
    engine = "openpyxl" if ext == ".xlsx" else "xlrd"
    excel = pd.ExcelFile(_excel_input(source), engine=engine)

    logical_sheets = ["Utilization", "IFSD", "RTO", "RTB", "UER", "ERR", "SVR", "D&C", "D&C per ata"]
    resolved = {name: _resolve_sheet(excel, name) for name in logical_sheets}
    missing = [name for name, actual in resolved.items() if actual is None]
    if missing:
        raise ValueError("Template tidak sesuai; sheet wajib tidak ditemukan: " + ", ".join(missing))

    monthly = _read_utilization(excel, resolved["Utilization"])
    warnings: list[str] = []
    for metric in EVENT_METRICS:
        event_frame = _read_event_sheet(excel, resolved[metric], metric)
        monthly = monthly.merge(event_frame, on="Date", how="left", validate="one_to_one")

    valid_exp = monthly["FH"].notna() & monthly["FC"].notna()
    if not valid_exp.any():
        raise ValueError("Tidak ada bulan dengan FH dan FC valid pada sheet Utilization.")
    first_valid = monthly.loc[valid_exp, "Date"].min()
    last_valid = monthly.loc[valid_exp, "Date"].max()
    active = monthly[(monthly["Date"] >= first_valid) & (monthly["Date"] <= last_valid)].copy()

    full_range = pd.date_range(first_valid, last_valid, freq="MS")
    if len(active) != len(full_range):
        warnings.append("Ada bulan yang hilang di antara awal dan akhir coverage utilization.")
    if active[["FH", "FC"]].isna().any(axis=None):
        warnings.append("Ada FH/FC kosong di dalam active coverage; rate pada window terkait akan ditandai tidak tersedia.")
    for metric in EVENT_METRICS:
        missing_events = int(active[metric].isna().sum())
        if missing_events:
            warnings.append(f"{metric}: {missing_events} bulan kosong di dalam active coverage; blank tidak dianggap zero.")

    active["Fleet"] = fleet
    active["Source File"] = source_name
    active["Year"] = active["Date"].dt.year
    active["Month"] = active["Date"].dt.month
    active["Year-Month"] = active["Date"].dt.strftime("%Y-%m")

    dc_ata = _read_dc_ata(excel, resolved["D&C per ata"])
    if not dc_ata.empty:
        dc_ata = dc_ata[(dc_ata["Date"] >= first_valid) & (dc_ata["Date"] <= last_valid)].copy()
        _dc_rows_per_month = dc_ata.groupby("Date")["ATA"].nunique()
        _incomplete_dc_dates = [d for d in active["Date"].tolist() if int(_dc_rows_per_month.get(d, 0)) < 10]
        if _incomplete_dc_dates:
            warnings.append(
                f"D&C per ATA: {len(_incomplete_dc_dates)} bulan tidak memiliki lengkap ATA 71–80; "
                "bulan tersebut dikeluarkan dari breakdown agar blank tidak dianggap zero."
            )
            dc_ata = dc_ata[~dc_ata["Date"].isin(_incomplete_dc_dates)].copy()
        dc_ata["Fleet"] = fleet
        dc_ata["Source File"] = source_name

    reconciliation = pd.DataFrame(columns=["Date", "D&C Total", "ATA 71-80 Total", "Difference"])
    if not dc_ata.empty:
        ata_monthly = dc_ata.groupby("Date", as_index=False)["D&C ATA Events"].sum().rename(
            columns={"D&C ATA Events": "ATA 71-80 Total"}
        )
        reconciliation = active[["Date", "D&C"]].merge(ata_monthly, on="Date", how="left").rename(columns={"D&C": "D&C Total"})
        reconciliation["Difference"] = reconciliation["ATA 71-80 Total"] - reconciliation["D&C Total"]
        reconciliation = reconciliation[
            reconciliation["D&C Total"].notna()
            & reconciliation["ATA 71-80 Total"].notna()
            & reconciliation["Difference"].abs().gt(1e-9)
        ].reset_index(drop=True)
        if not reconciliation.empty:
            warnings.append(
                f"D&C reconciliation: {len(reconciliation)} bulan memiliki total ATA 71-80 yang berbeda dari sheet D&C. "
                "Sheet D&C tetap digunakan sebagai authoritative total."
            )

    background_sheet = _resolve_sheet(excel, "Background")
    targets = _read_targets(excel, background_sheet)

    return {
        "monthly": active.reset_index(drop=True),
        "dc_ata": dc_ata.reset_index(drop=True),
        "targets": targets,
        "reconciliation": reconciliation,
        "warnings": warnings,
        "coverage_start": first_valid,
        "coverage_end": last_valid,
        "source_name": source_name,
        "fleet": fleet,
    }


def combine_operational_monthly(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True, sort=False)
    # Updated/re-uploaded source for the same fleet/month supersedes an older source.
    return out.drop_duplicates(subset=["Fleet", "Date"], keep="last").sort_values(["Fleet", "Date"]).reset_index(drop=True)


def combine_dc_ata(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True, sort=False)
    return out.drop_duplicates(subset=["Fleet", "Date", "ATA"], keep="last").sort_values(["Fleet", "Date", "ATA"]).reset_index(drop=True)


def aggregate_operational_view(monthly: pd.DataFrame, fleet_choice: str) -> tuple[pd.DataFrame, dict[str, object]]:
    """Return an individual-fleet or strict-comparable all-fleet monthly view."""
    if monthly is None or monthly.empty:
        return pd.DataFrame(), {"fleets": [], "coverage_start": None, "coverage_end": None}

    data = monthly.copy()
    available_fleets = [f for f in FLEET_ORDER if f in data["Fleet"].astype(str).unique().tolist()]
    if fleet_choice != "All Fleet":
        view = data[data["Fleet"] == fleet_choice].copy().sort_values("Date")
        if view.empty:
            return view, {"fleets": [fleet_choice], "coverage_start": None, "coverage_end": None}
        return view.reset_index(drop=True), {
            "fleets": [fleet_choice],
            "coverage_start": view["Date"].min(),
            "coverage_end": view["Date"].max(),
            "strict_comparable": False,
        }

    if not available_fleets:
        return pd.DataFrame(), {"fleets": [], "coverage_start": None, "coverage_end": None}

    starts = data.groupby("Fleet")["Date"].min().reindex(available_fleets)
    ends = data.groupby("Fleet")["Date"].max().reindex(available_fleets)
    common_start = starts.max()
    common_end = ends.min()
    scoped = data[data["Fleet"].isin(available_fleets) & data["Date"].between(common_start, common_end)].copy()

    numeric_cols = ["FH", "FC"] + EVENT_METRICS
    # min_count enforces complete fleet coverage for each aggregated monthly value.
    grouped = scoped.groupby("Date", as_index=False)[numeric_cols].sum(min_count=len(available_fleets))
    grouped["Fleet"] = "All Fleet"
    grouped["Year"] = grouped["Date"].dt.year
    grouped["Month"] = grouped["Date"].dt.month
    grouped["Year-Month"] = grouped["Date"].dt.strftime("%Y-%m")
    return grouped.sort_values("Date").reset_index(drop=True), {
        "fleets": available_fleets,
        "coverage_start": common_start,
        "coverage_end": common_end,
        "strict_comparable": True,
    }


def add_rolling_operational_rates(view: pd.DataFrame) -> pd.DataFrame:
    if view is None or view.empty:
        return pd.DataFrame()
    out = view.sort_values("Date").copy().reset_index(drop=True)
    window_expected = pd.Series(np.minimum(np.arange(1, len(out) + 1), 12), index=out.index, dtype=float)

    for metric, cfg in RATE_CONFIG.items():
        event_s = pd.to_numeric(out[metric], errors="coerce")
        exp_s = pd.to_numeric(out[cfg["exposure"]], errors="coerce")
        event_sum = event_s.rolling(12, min_periods=1).sum()
        exp_sum = exp_s.rolling(12, min_periods=1).sum()
        event_n = event_s.notna().astype(int).rolling(12, min_periods=1).sum()
        exp_n = exp_s.notna().astype(int).rolling(12, min_periods=1).sum()
        complete = event_n.eq(window_expected) & exp_n.eq(window_expected) & exp_sum.gt(0)
        out[f"{metric} 12M Events"] = event_sum.where(complete)
        out[f"{metric} 12M Rate"] = (event_sum / exp_sum * float(cfg["multiplier"])).where(complete)
        out[f"{metric} 3M Events"] = event_s.rolling(3, min_periods=1).sum()
    return out


def common_target(targets_by_fleet: dict[str, dict[str, float]], fleets: list[str], metric: str) -> float | None:
    values = []
    for fleet in fleets:
        value = targets_by_fleet.get(fleet, {}).get(metric)
        if value is None:
            return None
        values.append(float(value))
    if not values:
        return None
    if max(values) - min(values) > 1e-12:
        return None
    return values[0]
