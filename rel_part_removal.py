from __future__ import annotations

import hashlib
import io
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from rel_config import POWERPLANT_ATAS, UNSCHEDULED_REMOVAL_CODES

SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}

PART_COLUMNS = [
    "No",
    "Notification",
    "ATA",
    "Equipment",
    "Part Number",
    "Part Name",
    "Serial Number",
    "Register",
    "A/C Type",
    "RemCode",
    "Real Reason",
    "NFF",
    "Date Removal",
    "TSN",
    "TSI",
    "TSC",
    "CSN",
    "CSI",
    "CSC",
    "Shop_Visit",
    "Shop_Finding",
]

ALIASES = {
    "no": "No",
    "notification": "Notification",
    "notif": "Notification",
    "ata": "ATA",
    "equipment": "Equipment",
    "part number": "Part Number",
    "pn": "Part Number",
    "p/n": "Part Number",
    "part name": "Part Name",
    "component": "Part Name",
    "serial number": "Serial Number",
    "sn": "Serial Number",
    "s/n": "Serial Number",
    "register": "Register",
    "registration": "Register",
    "a/c reg": "Register",
    "a/c type": "A/C Type",
    "aircraft type": "A/C Type",
    "remcode": "RemCode",
    "rem code": "RemCode",
    "removal code": "RemCode",
    "real reason": "Real Reason",
    "reason": "Real Reason",
    "nff": "NFF",
    "date removal": "Date Removal",
    "removal date": "Date Removal",
    "tsn": "TSN",
    "tsi": "TSI",
    "tsc": "TSC",
    "csn": "CSN",
    "csi": "CSI",
    "csc": "CSC",
    "shop_visit": "Shop_Visit",
    "shop visit": "Shop_Visit",
    "shop_finding": "Shop_Finding",
    "shop finding": "Shop_Finding",
}


def _clean_header(value: object) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text.replace("\n", " ").replace("\r", " ")).strip()


def _canonical_header(value: object) -> str:
    raw = _clean_header(value)
    return ALIASES.get(raw.casefold(), raw)


def _find_header_row(preview: pd.DataFrame) -> int:
    required = {"notification", "ata", "part name", "remcode"}
    best_idx = 0
    best_score = -1
    for idx, row in preview.iterrows():
        cells = {_clean_header(v).casefold() for v in row.tolist() if pd.notna(v)}
        normalized = set(cells)
        for cell in cells:
            if cell in ALIASES:
                normalized.add(ALIASES[cell].casefold())
        score = sum(1 for token in required if token in normalized)
        if score > best_score:
            best_idx, best_score = int(idx), score
    if best_score < 3:
        raise ValueError(
            "Header component-removal tidak terdeteksi. File minimal harus memiliki Notification, ATA, Part Name, dan RemCode."
        )
    return best_idx


def _read_excel(source, extension: str) -> pd.DataFrame:
    engine = "openpyxl" if extension == ".xlsx" else "xlrd"
    if hasattr(source, "seek"):
        source.seek(0)
    excel = pd.ExcelFile(source, engine=engine)
    preview = pd.read_excel(excel, header=None, nrows=15)
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
    preview = pd.read_csv(io.StringIO(text), header=None, nrows=15)
    header_row = _find_header_row(preview)
    return pd.read_csv(io.StringIO(text), header=header_row)


def _normalise_text(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .fillna("")
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def _notification_key(series: pd.Series) -> pd.Series:
    return (
        _normalise_text(series)
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"[^A-Za-z0-9]", "", regex=True)
        .str.upper()
    )


def _clean_part_name(series: pd.Series) -> pd.Series:
    # Intentionally conservative: whitespace/quote cleanup only.
    # No semantic merging such as EEC connector -> EEC.
    return (
        _normalise_text(series)
        .str.strip('"')
        .str.replace(r'^["\']+|["\']+$', "", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def prepare_part_dataframe(df: pd.DataFrame, source_name: str, modified_at: datetime | None = None) -> pd.DataFrame:
    renamed = {col: _canonical_header(col) for col in df.columns}
    df = df.rename(columns=renamed)

    if df.columns.duplicated().any():
        rebuilt = {}
        for col in dict.fromkeys(df.columns):
            candidates = df.loc[:, df.columns == col]
            rebuilt[col] = candidates.bfill(axis=1).iloc[:, 0]
        df = pd.DataFrame(rebuilt)

    hard_required = ["Notification", "ATA", "Part Name", "RemCode"]
    missing = [col for col in hard_required if col not in df.columns]
    if missing:
        raise ValueError(f"Kolom component-removal wajib tidak ditemukan: {', '.join(missing)}")

    for col in PART_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    out = df[PART_COLUMNS].copy()
    out["_Source_File"] = source_name
    out["_Source_Modified"] = modified_at or datetime.now()

    text_cols = [
        "Notification", "Equipment", "Part Number", "Part Name", "Serial Number", "Register",
        "A/C Type", "RemCode", "Real Reason", "NFF", "Shop_Visit", "Shop_Finding",
    ]
    for col in text_cols:
        out[col] = _normalise_text(out[col])

    out["Part Name"] = _clean_part_name(out["Part Name"])
    out["Part Number"] = _normalise_text(out["Part Number"])
    out["Date Removal"] = pd.to_datetime(out["Date Removal"], errors="coerce")
    out["ATA"] = pd.to_numeric(out["ATA"], errors="coerce").astype("Int64")

    for col in ["TSN", "TSI", "TSC", "CSN", "CSI", "CSC"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    remcode = out["RemCode"].str.upper().str.strip()
    out["Unscheduled Flag"] = remcode.isin({str(x).upper() for x in UNSCHEDULED_REMOVAL_CODES})
    out["Powerplant Flag"] = out["ATA"].isin(POWERPLANT_ATAS)
    out["Notification Key"] = _notification_key(out["Notification"])

    # Keep source wording; use PN only as a fallback when name is absent.
    out["Part Display"] = out["Part Name"].where(out["Part Name"] != "", out["Part Number"])
    out["Part Display"] = out["Part Display"].replace("", "UNSPECIFIED PART")

    _part_key = pd.DataFrame({
        "Notification Key": out["Notification Key"],
        "Part Number": out["Part Number"],
        "Serial Number": out["Serial Number"],
        "Date Removal": out["Date Removal"].astype("string"),
    }).astype("string").fillna("")
    _part_hash = pd.util.hash_pandas_object(_part_key, index=False).astype("uint64")
    out["Part Event ID"] = _part_hash.map(lambda value: f"{int(value):016x}")
    return out


def read_part_source(source, name: str | None = None, modified_at: datetime | None = None) -> pd.DataFrame:
    source_name = name or (Path(source).name if isinstance(source, (str, Path)) else getattr(source, "name", "uploaded_part_file"))
    extension = Path(source_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Format {extension or '(tanpa ekstensi)'} belum didukung untuk component-removal.")

    if isinstance(source, (str, Path)):
        path = Path(source)
        modified_at = datetime.fromtimestamp(path.stat().st_mtime)
        raw = _read_csv(path) if extension == ".csv" else _read_excel(path, extension)
    else:
        raw = _read_csv(source) if extension == ".csv" else _read_excel(source, extension)

    return prepare_part_dataframe(raw, source_name=source_name, modified_at=modified_at)


def combine_part_sources(sources: Iterable[tuple[object, str, datetime | None]]) -> tuple[pd.DataFrame, dict]:
    frames = []
    errors = []
    source_names = []
    for source, name, modified_at in sources:
        try:
            frame = read_part_source(source, name=name, modified_at=modified_at)
            frames.append(frame)
            source_names.append(name)
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    if not frames:
        return pd.DataFrame(), {"errors": errors, "sources": source_names, "duplicates_removed": 0}

    combined = pd.concat(frames, ignore_index=True, sort=False)
    before = len(combined)
    combined = combined.drop_duplicates(subset=["Part Event ID"], keep="first").reset_index(drop=True)
    combined = combined.sort_values(["Date Removal", "Notification"], na_position="last").reset_index(drop=True)
    return combined, {
        "errors": errors,
        "sources": source_names,
        "duplicates_removed": before - len(combined),
    }


def discover_part_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        [p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS],
        key=lambda p: p.name.casefold(),
    )


def filter_part_scope(
    df: pd.DataFrame,
    start_date=None,
    end_date=None,
    aircraft_type: str | None = None,
    ata: int | None = None,
    unscheduled_only: bool = True,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    out = out[out["Powerplant Flag"]].copy()

    if unscheduled_only:
        out = out[out["Unscheduled Flag"]].copy()

    if start_date is not None:
        out = out[out["Date Removal"].dt.date >= pd.Timestamp(start_date).date()].copy()
    if end_date is not None:
        out = out[out["Date Removal"].dt.date <= pd.Timestamp(end_date).date()].copy()

    if aircraft_type and aircraft_type != "All Aircraft":
        out = out[out["A/C Type"].astype("string") == str(aircraft_type)].copy()

    if ata is not None:
        out = out[out["ATA"] == int(ata)].copy()

    return out.reset_index(drop=True)


def link_parts_to_delay(parts_df: pd.DataFrame, delay_df: pd.DataFrame) -> pd.DataFrame:
    if parts_df is None or parts_df.empty:
        return pd.DataFrame()

    out = parts_df.copy()
    out["Link Status"] = "NO MATCH"
    out["Delay KeyProblem"] = ""
    out["Delay Problem Group"] = ""
    out["Delay Problem"] = ""
    out["Delay Minutes"] = pd.NA
    out["Delay Event Type"] = ""

    if delay_df is None or delay_df.empty or "Notif" not in delay_df.columns:
        return out

    delay = delay_df.copy()
    delay["Notification Key"] = _notification_key(delay["Notif"])
    delay = delay[delay["Notification Key"] != ""].copy()

    if delay.empty:
        return out

    counts = delay.groupby("Notification Key").size().rename("_Notif_Count")
    delay = delay.join(counts, on="Notification Key")

    unique_delay = delay[delay["_Notif_Count"] == 1].copy()
    keep_cols = ["Notification Key"]
    mapping = {
        "KeyProblem": "Delay KeyProblem",
        "Problem Group": "Delay Problem Group",
        "Problem": "Delay Problem",
        "Tech Dur": "Delay Minutes",
        "Event Type": "Delay Event Type",
    }
    for source_col in mapping:
        if source_col in unique_delay.columns:
            keep_cols.append(source_col)

    unique_delay = unique_delay[keep_cols].rename(columns=mapping)

    merged = out.drop(columns=[
        "Delay KeyProblem", "Delay Problem Group", "Delay Problem", "Delay Minutes", "Delay Event Type", "Link Status"
    ]).merge(unique_delay, on="Notification Key", how="left")

    for col in ["Delay KeyProblem", "Delay Problem Group", "Delay Problem", "Delay Event Type"]:
        if col not in merged.columns:
            merged[col] = ""
        merged[col] = _normalise_text(merged[col])
    if "Delay Minutes" not in merged.columns:
        merged["Delay Minutes"] = pd.NA

    unique_keys = set(unique_delay["Notification Key"].tolist())
    ambiguous_keys = set(counts[counts > 1].index.tolist())
    merged["Link Status"] = "NO MATCH"
    merged.loc[merged["Notification Key"].isin(unique_keys), "Link Status"] = "DIRECT MATCH"
    merged.loc[merged["Notification Key"].isin(ambiguous_keys), "Link Status"] = "AMBIGUOUS NOTIF"
    return merged


def part_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["Part", "Removals", "Share %", "Aircraft", "Part Numbers", "Latest Removal"])

    total = len(df)
    summary = (
        df.groupby("Part Display", dropna=False)
        .agg(
            Removals=("Part Event ID", "count"),
            Aircraft=("Register", lambda s: s.replace("", pd.NA).nunique(dropna=True)),
            **{"Part Numbers": ("Part Number", lambda s: s.replace("", pd.NA).nunique(dropna=True))},
            **{"Latest Removal": ("Date Removal", "max")},
        )
        .reset_index()
        .rename(columns={"Part Display": "Part"})
    )
    summary["Share %"] = summary["Removals"] / total * 100 if total else 0.0
    summary = summary.sort_values(["Removals", "Aircraft", "Part"], ascending=[False, False, True]).reset_index(drop=True)
    return summary


def top_reason_for_part(df: pd.DataFrame, part: str) -> str:
    subset = df[df["Part Display"] == part]
    reasons = subset["Real Reason"].replace("", pd.NA).dropna()
    if reasons.empty:
        return "—"
    counts = reasons.value_counts()
    return str(counts.index[0])
