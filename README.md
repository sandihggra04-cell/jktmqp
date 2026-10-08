# Powerplant Engineering Control Center v4.7.4


Start with `START_CONTROL_CENTER.bat` or run:

```powershell
python -m streamlit run app.py
```

Rooms remain separate:
- Reliability & Technical Delay
- Engine Shop Visit

The Control Center home provides cross-room status and room switching.

---

# Powerplant Engineering Control Center

Unified Streamlit workspace with two separated rooms:

1. **Reliability & Technical Delay Room** — based on Powerplant Dashboard v1.35.
2. **Engine Shop Visit Room** — based on Engine Shop Visit Dashboard v16.

The rooms share one navigation shell but intentionally keep separate data sources, filters, calculations and operational workflows.


## Recommended Windows start

After extracting the ZIP, double-click `START_CONTROL_CENTER.bat`.

Do not paste the navigation/tree diagram into PowerShell. Menu names such as `Reliability & Technical Delay` or `Engine Detail & History` are labels, not terminal commands.

## Install

```bash
python -m pip install -r requirements.txt
```

## Run

```bash
python -m streamlit run app.py
```

Open `http://localhost:8501`.

## Room 01 — Reliability & Technical Delay

Preserves the Powerplant v1.35 capabilities, including technical-delay analysis, ATA/key problems, rolling 12-month trends, repetitive events, utilization normalization, aircraft grouping and unscheduled component-removal analytics.

The `INPUT / UPDATE DATA` section starts collapsed so routine users see filters and monitoring controls first.

## Room 02 — Engine Shop Visit

Preserves Engine Shop Visit v16, including live Google Sheet connection, local cached filtering, engine status/detail/history, Scope of Work, TAT trend and scope-controlled MRO comparison.

Paste the Google Sheet URL inside the Shop Visit room as before.

## Important design rule

Data is not force-merged. Reliability analysis and shop-visit execution remain separate because their grains are different (event/aircraft vs engine/shop visit). A future ESN linkage can be added only where trustworthy mapping data exists.

## Navigation URLs (v1.2)

The Control Center uses explicit unique Streamlit page paths:

- `/` — Control Center
- `/reliability` — Reliability & Technical Delay
- `/shop-visit` — Engine Shop Visit

This avoids the duplicate `app` pathname error that occurs when two room entry files are both named `app.py`.



## Shop Visit multi-source data (v4.7.0)

Both APU Shop Visit and Engine Shop Visit can read:

- Google Sheets URLs
- SharePoint / OneDrive Excel URLs
- local Excel / CSV paths (automatic refresh on the host machine)
- local Excel / CSV uploads

Private corporate SharePoint links are supported through Microsoft Graph. See `SHAREPOINT_SETUP.md` and `.streamlit/secrets.toml.example`.


## v4.7.1 UI/filter update
- Sidebar upload controls are readable on the navy theme.
- Engine Shop Visit now includes an exact-source **Progress** multiselect filter, like APU Shop Visit.

## v4.7.4 Clean source panel
- Microsoft List / bridge controls were removed from the Shop Visit sidebars.
- Source panels are now compact and use a dark professional treatment consistent with the navy sidebar.
- Supported user-facing sources: Google Sheets, SharePoint/OneDrive Excel, local Excel/CSV, and manual Excel/CSV upload.


## v4.7.6 Off Wing filter

Engine Shop Visit and APU Shop Visit include an **Off Wing** Progress option. Off Wing includes every populated progress value except Completed/Complete.
