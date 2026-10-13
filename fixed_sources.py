from __future__ import annotations

import os

DEFAULT_FIXED_SOURCES = {
    "technical_delay": {
        "name": "DATA DELAY ALL AIRCRAFT & ALL ATA.xlsx",
        "url": "https://docs.google.com/spreadsheets/d/1tuSTISpnlq4AxCKAEbRNj8OOHAg1HDQlYyvMwrBCa0c/edit?usp=drivesdk",
        "mode": "google_sheet",
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
        "name": "DATA ENGINE SHOP VISIT.xlsx",
        "url": "https://docs.google.com/spreadsheets/d/14RQYoNBy7LXeJutbJxJ1FgNH-Byx4NdFf859EUn6fIE/edit?usp=drivesdk",
        "mode": "google_sheet",
    },
    "apu_shop_visit": {
        "name": "DATA APU SHOP VISIT.xlsx",
        "url": "https://docs.google.com/spreadsheets/d/1KJJxpayLGKBVPlDu_MKshfCslD1zrxPKQxF2gQpfO9g/edit?usp=drivesdk",
        "mode": "google_sheet",
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
