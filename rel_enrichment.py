from __future__ import annotations

import re
import numpy as np
import pandas as pd


def _text(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").str.replace(r"\s+", " ", regex=True).str.strip()


def _contains(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


PROBLEM_RULES = [
    (r"FUEL\s*FILTER|FILTER\s*BYPASS|FFDP|DIFFERENTIAL\s*PRESSURE", "FUEL FILTER", "Fuel & Control", "Fuel Filter", "Bypass / restriction indication"),
    (r"ENGINE\s*CONTROL|ENG\s*CTL|\bEEC\b|\bECU\b", "ENGINE CONTROL", "Engine Control", "EEC / Engine Control", "Control fault / indication"),
    (r"AIR\s*TURBINE\s*STARTER|\bSTARTER\b", "STARTER", "Starting", "Starter", "Start / starter fault"),
    (r"FAIL(?:ED)?\s+TO\s+START|START\s*FAULT|START\s*ABORT|NO\s*START", "ENGINE START", "Starting", "Engine Start System", "Start failure"),
    (r"THRUST\s*REVERSER|\bT\/R\b|REVERSER", "THRUST REVERSER", "Exhaust / Reverser", "Thrust Reverser", "Deploy / indication / fault"),
    (r"OIL\s*FILTER", "OIL FILTER", "Oil", "Oil Filter", "Bypass / restriction indication"),
    (r"OIL\s*LEAK|LEAK.*OIL", "OIL LEAK", "Oil", "Oil System", "Leak"),
    (r"HIGH\s*OIL\s*CONS|OIL\s*CONSUM", "HIGH OIL CONSUMPTION", "Oil", "Oil System", "High consumption"),
    (r"FUEL\s*LEAK|LEAK.*FUEL", "ENGINE FUEL LEAK", "Fuel & Control", "Fuel System", "Leak"),
    (r"\bBLEED\b|PRSOV|HPSOV", "BLEED SYSTEM", "Air / Bleed", "Bleed Air System", "Leak / valve / indication"),
    (r"IGNIT|IGNITER", "IGNITION", "Ignition", "Ignition System", "Ignition fault"),
    (r"\bVSV\b", "VSV", "Air / Compressor Control", "VSV", "Stuck / slow / actuator fault"),
    (r"\bVBV\b", "VBV", "Air / Compressor Control", "VBV", "Stuck / slow / actuator fault"),
    (r"HPTACC", "HPTACC", "Turbine Clearance Control", "HPTACC", "Valve / control fault"),
    (r"\bHMU\b|HYDROMECHANICAL", "HMU", "Fuel & Control", "HMU", "Control / metering fault"),
    (r"VIBRATION|VIB\s*HIGH", "ENGINE VIBRATION", "Indicating", "Vibration Monitoring", "High vibration"),
    (r"\bEGT\b|EXHAUST\s*GAS\s*TEMP", "EGT / TEMPERATURE", "Indicating", "Temperature Indication", "High / abnormal indication"),
    (r"SURGE|STALL", "ENGINE SURGE / STALL", "Engine Core", "Compressor", "Surge / stall"),
    (r"FLAMEOUT|FLAME\s*OUT|IFSD|IN.FLIGHT\s*SHUT", "ENGINE SHUTDOWN / FLAMEOUT", "Engine Core", "Engine", "Shutdown / flameout"),
    (r"APU\s*AUTO\s*SHUT|APU.*SHUTDOWN", "APU AUTO SHUTDOWN", "APU", "APU", "Automatic shutdown"),
    (r"APU.*UNABLE\s*TO\s*START|APU.*NO\s*START", "APU UNABLE TO START", "APU", "APU Starting", "Start failure"),
]


RECTIFICATION_RULES = [
    (r"REPLAC|REMOVE.*INSTALL|R\/I\b|R&I\b|CHANG(?:E|ED)", "COMPONENT REPLACEMENT"),
    (r"RESET|POWER\s*CYCLE|CYCLE\s*POWER", "RESET / POWER CYCLE"),
    (r"RESEAT|RE-SEAT|RECONNECT|RE-CONNECT|CONNECTOR.*CLEAN", "CONNECTOR / RESEAT"),
    (r"CLEAN|WASH|FLUSH", "CLEANING / FLUSH"),
    (r"ADJUST|RIGG|CALIBRAT", "ADJUSTMENT / RIGGING"),
    (r"REPAIR|RECTIF|REWORK", "REPAIR / REWORK"),
    (r"INSPECT|BORESCOPE|VISUAL\s*CHECK", "INSPECTION"),
    (r"TEST|OPS\s*CHECK|OPERATIONAL\s*CHECK|BITE|TROUBLESHOOT|TS\b", "TEST / TROUBLESHOOT"),
    (r"DEFER|DCP|MEL", "DEFERRED / MEL"),
]


def _ata_system(ata: object) -> str:
    try:
        value = int(ata)
    except Exception:
        return "Unknown"
    mapping = {
        49: "APU",
        71: "Powerplant General",
        72: "Engine Core",
        73: "Fuel & Control",
        74: "Ignition",
        75: "Air / Bleed",
        76: "Engine Controls",
        77: "Engine Indicating",
        78: "Exhaust / Thrust Reverser",
        79: "Oil",
        80: "Starting",
    }
    return mapping.get(value, "Other")


def _classify_problem(row: pd.Series) -> tuple[str, str, str, str]:
    combined = " ".join(
        str(row.get(c, "") or "")
        for c in ["KeyProblem", "Problem", "Rectification", "Chronology"]
    ).upper()
    for pattern, group, system, component, failure in PROBLEM_RULES:
        if _contains(combined, pattern):
            return group, system, component, failure
    system = _ata_system(row.get("ATA"))
    raw = str(row.get("KeyProblem", "") or "").strip()
    if raw:
        return raw.upper(), system, "Unmapped component", "Unmapped failure mode"
    return "NEEDS CLASSIFICATION", system, "Needs classification", "Needs classification"


def _engine_position(row: pd.Series) -> str:
    combined = " ".join(str(row.get(c, "") or "") for c in ["Problem", "KeyProblem", "Rectification"]).upper()
    patterns = [
        r"\b(?:ENGINE|ENG)\s*(?:NO\.?\s*)?#?\s*([12])\b",
        r"\bENG\s*([12])\b",
        r"\bENGINE\s*([12])\b",
        r"\b#\s*([12])\b",
    ]
    hits: set[str] = set()
    for pattern in patterns:
        for match in re.findall(pattern, combined, flags=re.IGNORECASE):
            hits.add(str(match))
    if hits == {"1"}:
        return "ENG 1"
    if hits == {"2"}:
        return "ENG 2"
    if len(hits) > 1:
        return "MULTIPLE / AMBIGUOUS"
    return "UNKNOWN"


def _rectification_action(value: object) -> str:
    text = str(value or "").upper().strip()
    if not text:
        return "NO ACTION TEXT"
    for pattern, label in RECTIFICATION_RULES:
        if _contains(text, pattern):
            return label
    return "OTHER / UNMAPPED"


def enrich_delay_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Add engineering-derived fields without changing the source columns.

    All classifications are rule-based aids for review. They are not treated as
    authoritative maintenance findings and the raw free-text source is retained.
    """
    if df.empty:
        return df
    out = df.copy()
    raw_key = _text(out["KeyProblem"])
    raw_unclassified = raw_key.str.upper().isin({"", "UNCLASSIFIED", "UNKNOWN", "N/A", "NA", "-"})

    classified = out.apply(_classify_problem, axis=1, result_type="expand")
    classified.columns = ["Problem Group", "System", "Component", "Failure Mode"]
    out = pd.concat([out, classified], axis=1)

    out["KeyProblem Classification"] = np.select(
        [~raw_unclassified, raw_unclassified & (out["Problem Group"] != "NEEDS CLASSIFICATION")],
        ["CLASSIFIED / NORMALIZED", "SUGGESTED FROM FREE TEXT"],
        default="NEEDS CLASSIFICATION",
    )
    out["Engine Position"] = out.apply(_engine_position, axis=1)
    out["Rectification Action"] = out["Rectification"].apply(_rectification_action)
    out["System Group"] = np.where(out["ATA"].eq(49), "APU · ATA 49", np.where(out["ATA"].between(71, 80), "PROPULSION · ATA 71–80", "OTHER"))
    return out
