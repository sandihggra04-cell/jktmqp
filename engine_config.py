# ENGINE SHOP VISIT EASY DASHBOARD — V7

GOOGLE_SHEET_URL = "PASTE_YOUR_GOOGLE_SHEET_LINK_HERE"
SHOP_VISIT_SHEET = "SHOP_VISIT_DATA"
AUTO_REFRESH_SECONDS = 60
COST_CURRENCY = ""

# TAT outside this range is excluded from analytics.
MAX_PLAUSIBLE_TAT_DAYS = 2000

PHASES = [
    "Planned",
    "Removed / In Transit",
    "Inducted",
    "Disassembly",
    "Inspection",
    "Repair / Material",
    "Assembly",
    "Test Cell",
    "Ready for Release",
    "On Hold",
    "Completed",
]
