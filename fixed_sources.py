from __future__ import annotations

import os

DEFAULT_FIXED_SOURCES = {
    "technical_delay": {
        "name": "Delay - A330-200,A330-300,A330-900,B737-800,B737-MAX,B777-3002020-01-01 - 2026-10-06.xlsx",
        "url": "https://docs.google.com/spreadsheets/d/14zkC02XKIky5UEv-1tXHLerrJdao-rJA/edit?usp=drivesdk&ouid=100771707533387912207&rtpof=true&sd=true",
        "mode": "drive_xlsx",
    },
    "utilization_b737": {
        "name": "Master Dashboard CFM56-7B & LEAP-1B 2026_Rev 1.xlsx",
        "url": "https://docs.google.com/spreadsheets/d/1A7KiJKAizjzHg4ELQ6CMgvhJVecTyY_x/edit?usp=drivesdk&ouid=100771707533387912207&rtpof=true&sd=true",
        "mode": "drive_xlsx",
    },
    "utilization_b777": {
        "name": "Master Dashboard GE90 2026_Rev 1 (2).xlsx",
        "url": "https://docs.google.com/spreadsheets/d/1jga7ZaqPtgfD3iUmcTPXbHXOACE3ZQ4u/edit?usp=drivesdk&ouid=100771707533387912207&rtpof=true&sd=true",
        "mode": "drive_xlsx",
    },
    "utilization_a330": {
        "name": "Master Dashboard TRENT 2026_Rev 1 (2).xlsx",
        "url": "https://docs.google.com/spreadsheets/d/1YQXRWSAChGsGvEpH9GpaiMZDDwDvf249/edit?usp=drivesdk&ouid=100771707533387912207&rtpof=true&sd=true",
        "mode": "drive_xlsx",
    },
    "component_removal": {
        "name": "REPORT Component Removal A330-200,A330-300,A330-900,B737-800,B737-MAX,B777-300 (1).xlsx",
        "url": "https://docs.google.com/spreadsheets/d/1CXTgkEmbvhPNCQgtasKCGUpsFDZguXyo/edit?usp=drivesdk&ouid=100771707533387912207&rtpof=true&sd=true",
        "mode": "drive_xlsx",
    },
    "engine_shop_visit": {
        "name": "DATA ENGINE SHOP VISIT aga.xlsx",
        "url": "https://docs.google.com/spreadsheets/d/1B_m0TcnISZxLNJHaF7wayE7upz0TUhwx/edit?usp=drivesdk&ouid=100771707533387912207&rtpof=true&sd=true",
        "mode": "drive_xlsx",
    },
    "apu_shop_visit": {
        "name": "DATA APU SHOP VISIT (2).xlsx",
        "url": "https://docs.google.com/spreadsheets/d/12aqNtB0XHDnIvby_yHqRb4BgC2sH1wpQ/edit?usp=drivesdk&ouid=100771707533387912207&rtpof=true&sd=true",
        "mode": "drive_xlsx",
    },
}

RELIABILITY_AUTO_SYNC_SECONDS = 300
SHOP_VISIT_AUTO_SYNC_SECONDS = 60


def get_fixed_source(key: str) -> dict:
    if key not in DEFAULT_FIXED_SOURCES:
        raise KeyError(f"Unknown fixed source: {key}")
    cfg = dict(DEFAULT_FIXED_SOURCES[key])
    env_value = os.getenv(f"FIXED_{key.upper()}_URL", "").strip()
    if env_value:
        cfg["url"] = env_value
    try:
        import streamlit as st
        section = st.secrets.get("fixed_sources", {})
        if hasattr(section, "get"):
            value = str(section.get(key, "") or "").strip()
            if value:
                cfg["url"] = value
    except Exception:
        pass
    return cfg
