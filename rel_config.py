from __future__ import annotations

from pathlib import Path

APP_TITLE = "Powerplant Reliability & Technical Delay Dashboard"
APP_SUBTITLE = "Multi-Fleet Monitoring for Powerplant Engineering"

BASE_DIR = Path(__file__).resolve().parent
# Runtime source folders are created automatically by the app when needed.
# They do not need to exist in the GitHub repository.
DELAY_DIR = BASE_DIR / ".runtime_delay"
DEMO_DIR = BASE_DIR / ".runtime_demo"
EXPOSURE_DIR = BASE_DIR / ".runtime_exposure"
SUPPORT_DIR = BASE_DIR / ".runtime_support"
PARTS_DIR = BASE_DIR / ".runtime_parts"

for _runtime_dir in (DELAY_DIR, DEMO_DIR, EXPOSURE_DIR, SUPPORT_DIR, PARTS_DIR):
    _runtime_dir.mkdir(parents=True, exist_ok=True)

# Approved technical-delay universe for the official Powerplant Delay Contribution denominator.
# ATA 05 is normalized to integer 5 during data loading.
ALL_TECHNICAL_ATAS = {
    5, 11, 12, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 38,
    42, 45, 46, 47, 49, 50, 52, 53, 54, 55, 56, 57, 58, 61, 70, 71, 72, 73, 74, 75, 76,
    77, 78, 79, 80,
}

# Dashboard engineering scope. Non-Powerplant ATA are retained only for the all-ATA denominator.
POWERPLANT_ATAS = {49, *range(71, 81)}
SEVERE_THRESHOLD_MIN = 60

# Component-removal codes treated as unscheduled for Part Replacement analysis.
# Kept explicit so engineering can revise the mapping if source coding changes.
UNSCHEDULED_REMOVAL_CODES = {"U", "UM"}

CANONICAL_COLUMNS = [
    "No",
    "Notif",
    "Date",
    "A/C Type",
    "A/C Reg",
    "Sta Dep",
    "Sta Arr",
    "Flight No",
    "Tech Dur",
    "ATA",
    "Sub ATA",
    "Problem",
    "KeyProblem",
    "Rectification",
    "Chronology",
    "DCP",
    "Event Type",
    "#",
]

HEADER_ALIASES = {
    "no": "No",
    "notif": "Notif",
    "notification": "Notif",
    "date": "Date",
    "a/c type": "A/C Type",
    "ac type": "A/C Type",
    "aircraft type": "A/C Type",
    "a/c reg": "A/C Reg",
    "ac reg": "A/C Reg",
    "registration": "A/C Reg",
    "sta dep": "Sta Dep",
    "station dep": "Sta Dep",
    "departure station": "Sta Dep",
    "sta arr": "Sta Arr",
    "station arr": "Sta Arr",
    "arrival station": "Sta Arr",
    "flight no": "Flight No",
    "flight number": "Flight No",
    "tech dur": "Tech Dur",
    "technical duration": "Tech Dur",
    "delay": "Tech Dur",
    "ata": "ATA",
    "sub ata": "Sub ATA",
    "sub-ata": "Sub ATA",
    "problem": "Problem",
    "keyproblem": "KeyProblem",
    "key problem": "KeyProblem",
    "rectification": "Rectification",
    "chronology": "Chronology",
    "dcp": "DCP",
    "rtb rta rto": "Event Type",
    "rtb/rta/rto": "Event Type",
    "rtb  rta  rto": "Event Type",
    "event type": "Event Type",
    "#": "#",
}

SEARCH_COLUMNS = ["Problem", "KeyProblem", "Rectification", "Chronology"]

DELAY_BANDS = [
    (-1, 15, "≤15 min"),
    (15, 30, "16–30 min"),
    (30, 60, "31–60 min"),
    (60, 120, "61–120 min"),
    (120, float("inf"), ">120 min"),
]

STATUS_COLORS = {
    "READY": "#15803D",
    "WARNING": "#B45309",
    "CHECK": "#B91C1C",
}

PLOT_COLORS = {
    "navy": "#0B1F33",
    "blue": "#245B9E",
    "teal": "#448F92",
    "sky": "#76A7DF",
    "green": "#2B7C47",
    "amber": "#A96F18",
    "red": "#B84B43",
    "slate": "#667085",
    "grid": "#EEF2F6",
}
