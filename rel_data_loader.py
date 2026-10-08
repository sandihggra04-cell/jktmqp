from __future__ import annotations

import hashlib
import io
import re
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Iterable

import numpy as np
import pandas as pd

from rel_enrichment import enrich_delay_dataframe

from rel_config import (
    CANONICAL_COLUMNS,
    DELAY_BANDS,
    HEADER_ALIASES,
    ALL_TECHNICAL_ATAS,
    POWERPLANT_ATAS,
    SEVERE_THRESHOLD_MIN,
)

SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}


def _clean_header(value: object) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"\s+", " ", text.replace("\n", " ").replace("\r", " ")).strip()
    return text


def _canonical_header(value: object) -> str:
    raw = _clean_header(value)
    key = raw.casefold()
    return HEADER_ALIASES.get(key, raw)


def _find_header_row(preview: pd.DataFrame) -> int:
    required_tokens = {"date", "a/c type", "tech dur", "ata"}
    best_idx = 0
    best_score = -1
    for idx, row in preview.iterrows():
        cells = {_clean_header(v).casefold() for v in row.tolist() if pd.notna(v)}
        normalized = set()
        for cell in cells:
            normalized.add(cell)
            if cell in HEADER_ALIASES:
                normalized.add(HEADER_ALIASES[cell].casefold())
        score = sum(1 for token in required_tokens if token in normalized)
        if score > best_score:
            best_idx, best_score = int(idx), score
    if best_score < 3:
        raise ValueError(
            "Header row tidak terdeteksi. File harus memiliki minimal Date, A/C Type, Tech Dur, dan ATA."
        )
    return best_idx


def _read_excel(source, extension: str) -> pd.DataFrame:
    engine = "openpyxl" if extension == ".xlsx" else "xlrd"
    # Open the workbook once and reuse the same ExcelFile object for both the
    # lightweight header probe and the full data read. This avoids reopening
    # and reparsing the XLSX archive twice on every load.
    if hasattr(source, "seek"):
        source.seek(0)
    excel = pd.ExcelFile(source, engine=engine)
    preview = pd.read_excel(excel, header=None, nrows=10)
    header_row = _find_header_row(preview)
    return pd.read_excel(excel, header=header_row)


def _read_csv(source) -> pd.DataFrame:
    raw = source.read() if hasattr(source, "read") else Path(source).read_bytes()
    if hasattr(source, "seek"):
        source.seek(0)
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    preview = pd.read_csv(io.StringIO(text), header=None, nrows=10)
    header_row = _find_header_row(preview)
    return pd.read_csv(io.StringIO(text), header=header_row)


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {_col: _canonical_header(_col) for _col in df.columns}
    df = df.rename(columns=renamed)
    # If aliases create duplicate column names, preserve the first non-null value.
    if df.columns.duplicated().any():
        rebuilt = {}
        for col in dict.fromkeys(df.columns):
            candidates = df.loc[:, df.columns == col]
            rebuilt[col] = candidates.bfill(axis=1).iloc[:, 0]
        df = pd.DataFrame(rebuilt)
    missing = [c for c in CANONICAL_COLUMNS[:-1] if c not in df.columns]
    # For non-Powerplant denominator rows, only core event fields are required.
    # Powerplant engineering detail is checked separately by Data Quality.
    hard_required = ["Date", "A/C Type", "Tech Dur", "ATA"]
    hard_missing = [c for c in hard_required if c not in df.columns]
    if hard_missing:
        raise ValueError(f"Kolom wajib tidak ditemukan: {', '.join(hard_missing)}")
    for col in CANONICAL_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[CANONICAL_COLUMNS].copy()


def _normalise_text(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .fillna("")
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def _make_event_id(row: pd.Series) -> str:
    pieces = [
        str(row.get("Notif", "")),
        str(row.get("Date", "")),
        str(row.get("A/C Reg", "")),
        str(row.get("Tech Dur", "")),
        str(row.get("Problem", "")),
    ]
    digest = hashlib.sha1("|".join(pieces).encode("utf-8", errors="ignore")).hexdigest()
    return digest[:16]


def _delay_band(minutes: object) -> str:
    try:
        value = float(minutes)
    except (TypeError, ValueError):
        return "Unknown"
    for low, high, label in DELAY_BANDS:
        if value > low and value <= high:
            return label
    return "Unknown"


def prepare_delay_dataframe(df: pd.DataFrame, source_name: str, modified_at: datetime | None = None) -> pd.DataFrame:
    df = _normalise_columns(df)
    df["_Source_File"] = source_name
    df["_Source_Modified"] = modified_at or datetime.now()

    for col in [
        "Notif", "A/C Type", "A/C Reg", "Sta Dep", "Sta Arr", "Flight No", "Problem",
        "KeyProblem", "Rectification", "Chronology", "DCP", "Event Type",
    ]:
        df[col] = _normalise_text(df[col])

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Tech Dur"] = pd.to_numeric(df["Tech Dur"], errors="coerce")
    df["ATA"] = pd.to_numeric(df["ATA"], errors="coerce").astype("Int64")
    df["Sub ATA"] = pd.to_numeric(df["Sub ATA"], errors="coerce").astype("Int64")

    df["Route"] = np.where(
        (df["Sta Dep"] != "") | (df["Sta Arr"] != ""),
        df["Sta Dep"].fillna("") + " → " + df["Sta Arr"].fillna(""),
        "",
    )
    df["Delay Hours"] = df["Tech Dur"] / 60
    # Vectorized delay-band classification; avoids Python row-by-row apply on
    # large technical-delay exports.
    _dur = df["Tech Dur"]
    _conditions = [(_dur > low) & (_dur <= high) for low, high, _label in DELAY_BANDS]
    _labels = [label for _low, _high, label in DELAY_BANDS]
    df["Delay Band"] = np.select(_conditions, _labels, default="Unknown")
    df["Technical ATA Flag"] = np.where(df["ATA"].isin(ALL_TECHNICAL_ATAS), "Approved Technical ATA", "Outside Approved ATA")
    df["All Technical Event"] = (df["Technical ATA Flag"] == "Approved Technical ATA").astype(int)
    df["Powerplant Flag"] = np.where(df["ATA"].isin(POWERPLANT_ATAS), "Powerplant", "Other ATA")
    df["PP Event"] = (df["Powerplant Flag"] == "Powerplant").astype(int)
    df["PP Delay Min"] = np.where(df["Powerplant Flag"] == "Powerplant", df["Tech Dur"].fillna(0), 0)
    df["Operational Impact"] = np.where(
        df["Event Type"].str.upper().isin(["RTA", "RTB", "RTO"]), "Significant", "Normal"
    )
    df["Severe Flag"] = np.where(df["Tech Dur"].fillna(-1) >= SEVERE_THRESHOLD_MIN, "Severe", "Normal")
    df["Year"] = df["Date"].dt.year.astype("Int64")
    df["Month"] = df["Date"].dt.month.astype("Int64")
    df["Year-Month"] = df["Date"].dt.to_period("M").astype("string")
    df["Occurrence"] = 1

    invalid = (
        df["Date"].isna()
        | df["Tech Dur"].isna()
        | (df["Tech Dur"] < 0)
        | df["ATA"].isna()
        | (df["A/C Type"] == "")
    )
    df["Data Quality"] = np.where(invalid, "CHECK", "OK")
    # Stable vectorized event identifier. pandas hashes the selected columns in
    # compiled code and is substantially faster than DataFrame.apply(axis=1).
    _event_cols = ["Notif", "Date", "A/C Reg", "Tech Dur", "Problem"]
    _event_key = df[_event_cols].astype("string").fillna("")
    _event_hash = pd.util.hash_pandas_object(_event_key, index=False).astype("uint64")
    df["Event_ID"] = _event_hash.map(lambda value: f"{int(value):016x}")
    return enrich_delay_dataframe(df)


def read_delay_source(source, name: str | None = None, modified_at: datetime | None = None) -> pd.DataFrame:
    source_name = name or (Path(source).name if isinstance(source, (str, Path)) else getattr(source, "name", "uploaded_file"))
    extension = Path(source_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Format {extension or '(tanpa ekstensi)'} belum didukung.")

    if isinstance(source, (str, Path)):
        source_path = Path(source)
        modified_at = datetime.fromtimestamp(source_path.stat().st_mtime)
        if extension == ".csv":
            raw = _read_csv(source_path)
        else:
            raw = _read_excel(source_path, extension)
    else:
        if extension == ".csv":
            raw = _read_csv(source)
        else:
            raw = _read_excel(source, extension)
    return prepare_delay_dataframe(raw, source_name=source_name, modified_at=modified_at)


def combine_delay_sources(sources: Iterable[tuple[object, str, datetime | None]]) -> tuple[pd.DataFrame, dict]:
    frames: list[pd.DataFrame] = []
    errors: list[str] = []
    source_names: list[str] = []
    for source, name, modified_at in sources:
        try:
            frame = read_delay_source(source, name=name, modified_at=modified_at)
            frames.append(frame)
            source_names.append(name)
        except Exception as exc:  # show source-level validation cleanly in UI
            errors.append(f"{name}: {exc}")

    if not frames:
        return pd.DataFrame(), {"errors": errors, "sources": source_names, "exact_duplicates_removed": 0}

    combined = pd.concat(frames, ignore_index=True, sort=False)
    before = len(combined)
    # Remove only exact repeated export rows. Repeated Notif IDs with changed details are retained for review.
    exact_key = [c for c in CANONICAL_COLUMNS if c in combined.columns]
    combined = combined.drop_duplicates(subset=exact_key, keep="first").reset_index(drop=True)
    duplicates_removed = before - len(combined)
    combined = combined.sort_values(["Date", "Notif"], na_position="last").reset_index(drop=True)
    return combined, {
        "errors": errors,
        "sources": source_names,
        "exact_duplicates_removed": duplicates_removed,
    }


def discover_delay_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        [p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS],
        key=lambda p: p.name.casefold(),
    )


def _source_for_excel(source):
    """Return a reusable Excel input. UploadedFile objects need rewinding between reads."""
    if hasattr(source, "seek"):
        source.seek(0)
    return source


def _find_label_row(raw: pd.DataFrame, patterns: list[str]) -> int | None:
    for idx, row in raw.iterrows():
        cells = [str(v).strip() for v in row.tolist() if pd.notna(v)]
        line = " | ".join(cells).casefold()
        if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in patterns):
            return int(idx)
    return None


def _summary_year_columns(raw: pd.DataFrame) -> dict[int, int]:
    best: dict[int, int] = {}
    for _, row in raw.head(8).iterrows():
        current: dict[int, int] = {}
        for col_idx, value in enumerate(row.tolist()):
            try:
                year = int(float(value))
            except Exception:
                continue
            if 2000 <= year <= 2100:
                current[year] = col_idx
        if len(current) > len(best):
            best = current
    return best


def _row_value_by_year(raw: pd.DataFrame, row_idx: int | None, years: dict[int, int]) -> dict[int, float]:
    if row_idx is None:
        return {}
    out: dict[int, float] = {}
    for year, col_idx in years.items():
        value = pd.to_numeric(pd.Series([raw.iat[row_idx, col_idx]]), errors="coerce").iloc[0]
        if pd.notna(value):
            out[int(year)] = float(value)
    return out


def read_support_workbook(source, name: str | None = None) -> pd.DataFrame:
    """Parse the user's Powerplant calculation support workbook.

    Expected sheets resemble `All Fleet`, `737`, `777`, `A330`. The parser does
    not depend on fixed row numbers; it searches row labels such as Total
    Powerplant, Total Delay all ATA, and Total Revenue T/O. This provides a
    historical annual audit/fallback for Contribution and Delay Rate charts.
    """
    source_name = name or getattr(source, "name", "support_workbook.xlsx")
    if Path(source_name).suffix.lower() not in {".xlsx", ".xls"}:
        raise ValueError("Support workbook harus XLSX atau XLS.")
    engine = "openpyxl" if Path(source_name).suffix.lower() == ".xlsx" else "xlrd"
    excel = pd.ExcelFile(_source_for_excel(source), engine=engine)
    target_sheets = [s for s in excel.sheet_names if s.casefold() == "all fleet" or re.fullmatch(r"(?i)(b?737|b?777|a330)", s.strip())]
    if not target_sheets:
        raise ValueError("Format support workbook tidak dikenali: sheet All Fleet / fleet tidak ditemukan.")

    rows: list[dict] = []
    for sheet_name in target_sheets:
        raw = pd.read_excel(excel, sheet_name=sheet_name, header=None)
        years = _summary_year_columns(raw)
        if not years:
            continue
        if sheet_name.casefold() == "all fleet":
            fleet = "All Aircraft"
            pp_row = _find_label_row(raw, [r"ata\s*powerplant\s*delay\s*event", r"total\s*powerplant"])
            all_row = _find_label_row(raw, [r"total\s*delay\s*all\s*ata"])
            to_row = _find_label_row(raw, [r"total\s*take[- ]?off\s*revenue", r"total\s*revenue\s*t/?o"])
        else:
            title = str(raw.iat[0, 1]).strip() if raw.shape[1] > 1 and pd.notna(raw.iat[0, 1]) else sheet_name
            fleet = title or sheet_name
            pp_row = _find_label_row(raw, [r"total\s*powerplant"])
            all_row = _find_label_row(raw, [r"total\s*delay\s*all\s*ata"])
            to_row = _find_label_row(raw, [r"total\s*revenue\s*t/?o", r"total\s*take[- ]?off\s*revenue"])

        pp = _row_value_by_year(raw, pp_row, years)
        all_delay = _row_value_by_year(raw, all_row, years)
        revenue_to = _row_value_by_year(raw, to_row, years)
        for year in sorted(years):
            pp_events = pp.get(year)
            all_events = all_delay.get(year)
            to = revenue_to.get(year)
            if pp_events is None and all_events is None and to is None:
                continue
            contribution = (pp_events / all_events * 100) if pp_events is not None and all_events and all_events > 0 else None
            rate = (pp_events / to * 100) if pp_events is not None and to and to > 0 else None
            rows.append({
                "Year": year,
                "A/C Type": fleet,
                "PP Delay Events": pp_events,
                "All ATA Delay Events": all_events,
                "PP Delay Contribution %": contribution,
                "Revenue T/O": to,
                "PP Delay Rate /100 T/O": rate,
                "Exposure Granularity": "Yearly",
                "_Source_File": source_name,
            })
    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError("Tidak ada historical calculation row yang berhasil dibaca dari support workbook.")
    return out


def _read_utilization_cycles_exposure(source, source_name: str, engine: str) -> pd.DataFrame:
    """Parse monthly Revenue T/O from the user's Utilization workbook layout.

    Source contract requested by the user:
    - use sheet `Utilization` only (case-insensitive)
    - inspect Excel columns B:N only
    - use rows whose column B label is `cycles`
    - C:N represent Jan-Dec monthly Total Revenue T/O
    - ignore `hours` rows and every other worksheet / dashboard block

    The workbook does not encode fleet identity inside B:N. `_Exposure_Format` is
    therefore tagged so the app can bind the utilization rows to the loaded fleet
    automatically when only one aircraft type exists, or ask for the intended scope
    when multiple aircraft types are loaded.
    """
    excel = pd.ExcelFile(_source_for_excel(source), engine=engine)
    utilization_sheet = next((s for s in excel.sheet_names if str(s).strip().casefold() == "utilization"), None)
    if utilization_sheet is None:
        raise ValueError("Sheet Utilization tidak ditemukan.")

    # Deliberately read only B:N as requested. In this layout B contains the year /
    # row label and C:N contain Jan-Dec values.
    raw = pd.read_excel(excel, sheet_name=utilization_sheet, header=None, usecols="B:N")
    if raw.empty or raw.shape[1] < 13:
        raise ValueError("Sheet Utilization tidak memiliki struktur B:N yang diharapkan.")

    rows: list[dict] = []
    current_year: int | None = None
    for _, row in raw.iterrows():
        label = row.iloc[0]

        # A four-digit year row establishes the year for the following cycles row.
        try:
            maybe_year = int(float(label))
        except Exception:
            maybe_year = None
        if maybe_year is not None and 2000 <= maybe_year <= 2100:
            current_year = maybe_year
            continue

        label_text = _clean_header(label).casefold()
        if label_text not in {"cycle", "cycles"}:
            continue
        if current_year is None:
            continue

        month_values = row.iloc[1:13].tolist()  # C:N = Jan-Dec
        for month_no, value in enumerate(month_values, start=1):
            numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
            if pd.isna(numeric):
                continue
            rows.append({
                "Year": int(current_year),
                "Year-Month": f"{int(current_year):04d}-{month_no:02d}",
                "Revenue T/O": float(numeric),
                "Departures": float(numeric),
                "Flight Cycles": float(numeric),
                "Exposure Granularity": "Monthly",
                "_Exposure_Format": "Utilization cycles B:N",
                "_Source_File": source_name,
            })

    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError("Tidak ada nilai `cycles` bulanan yang terbaca dari Utilization!B:N.")
    return out


def read_exposure_source(source, name: str | None = None) -> pd.DataFrame:
    """Read operational exposure.

    Preferred XLSX/XLS format is the user's multi-sheet operational workbook:
    only sheet `Utilization`, columns B:N, and the `cycles` row for each year are
    read as monthly Revenue T/O. Flat CSV/XLSX exposure tables remain supported.
    The canonical denominator field used by the dashboard is `Revenue T/O`.
    """
    source_name = name or getattr(source, "name", "exposure")
    ext = Path(source_name).suffix.lower()
    if ext not in {".csv", ".xlsx", ".xls"}:
        raise ValueError("Exposure harus CSV, XLSX, atau XLS.")

    if ext in {".xlsx", ".xls"}:
        engine = "openpyxl" if ext == ".xlsx" else "xlrd"

        # Primary operational-exposure format: the user's multi-sheet utilization
        # workbook. Only Utilization!B:N and the `cycles` rows are used.
        try:
            return _read_utilization_cycles_exposure(source, source_name, engine)
        except Exception:
            if hasattr(source, "seek"):
                source.seek(0)

        # Backward compatibility: an explicitly uploaded historical support workbook
        # can still be parsed as annual exposure. It is no longer injected implicitly
        # by app.py when no operational exposure file is supplied.
        try:
            support = read_support_workbook(source, source_name)
            exp = support[[c for c in ["Year", "A/C Type", "Revenue T/O", "Exposure Granularity", "_Source_File"] if c in support.columns]].copy()
            exp["Departures"] = exp["Revenue T/O"]  # backward compatibility with older code
            exp["_Exposure_Format"] = "Historical support annual T/O"
            return exp
        except Exception:
            if hasattr(source, "seek"):
                source.seek(0)

    if ext == ".csv":
        df = pd.read_csv(source)
    else:
        engine = "openpyxl" if ext == ".xlsx" else "xlrd"
        df = pd.read_excel(source, engine=engine)

    df.columns = [_clean_header(c) for c in df.columns]
    rename = {}
    for col in df.columns:
        key = re.sub(r"\s+", " ", col.casefold()).strip()
        if key in {"a/c type", "ac type", "aircraft type", "fleet"}:
            rename[col] = "A/C Type"
        elif key in {"year-month", "year month", "yearmonth", "period"}:
            rename[col] = "Year-Month"
        elif key in {"departures", "departure", "revenue t/o", "total revenue t/o", "revenue to", "takeoff", "take-off", "take offs", "take-offs", "t/o", "total take-off revenue"}:
            rename[col] = "Revenue T/O"
        elif key in {"flight hours", "fh"}:
            rename[col] = "Flight Hours"
        elif key in {"flight cycles", "fc"}:
            rename[col] = "Flight Cycles"
        elif key == "date":
            rename[col] = "Date"
        elif key == "year":
            rename[col] = "Year"
    df = df.rename(columns=rename)

    if "Revenue T/O" not in df.columns:
        raise ValueError("Kolom Revenue T/O / Departures tidak ditemukan pada Exposure.")
    df["Revenue T/O"] = pd.to_numeric(df["Revenue T/O"], errors="coerce")
    df["Departures"] = df["Revenue T/O"]  # backward compatibility
    for c in ["Flight Hours", "Flight Cycles"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "A/C Type" in df.columns:
        df["A/C Type"] = _normalise_text(df["A/C Type"])

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Year"] = df["Date"].dt.year.astype("Int64")
        df["Year-Month"] = df["Date"].dt.to_period("M").astype("string")
        df["Exposure Granularity"] = "Daily"
    elif "Year-Month" in df.columns:
        ym = df["Year-Month"].astype("string").str.strip()
        ym = pd.to_datetime(ym, errors="coerce").dt.to_period("M")
        df["Year-Month"] = ym.astype("string")
        df["Year"] = ym.dt.year.astype("Int64")
        df["Exposure Granularity"] = "Monthly"
    elif "Year" in df.columns:
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
        df["Exposure Granularity"] = "Yearly"
    else:
        raise ValueError("Exposure membutuhkan Date, Year-Month, atau Year.")

    df["_Source_File"] = source_name
    return df

