# v5.3.0 — Automatic Google Drive data integration

- Added seven permanent Google Drive / Google Sheets sources supplied for the dashboard.
- Reliability loads automatically from 1 Technical Delay source, 3 Utilization sources, and 1 Component Removal source.
- Engine Shop Visit and APU Shop Visit load their fixed Google Sheet automatically when the room opens.
- Manual Excel/CSV upload remains available as a session-only override / backup.
- Browser refresh returns manual overrides to the permanent automatic source.
- Reliability auto-sync interval is 5 minutes because the Component Removal workbook is large; Refresh Data forces an immediate fetch.
- Engine/APU keep a 60-second live refresh cadence.
- Google Drive loader supports public Viewer links and optional private service-account authentication via `[google_drive]` Streamlit Secrets.
- Fixed URLs can still be overridden without code changes through `[fixed_sources]` Streamlit Secrets.
- Flat GitHub deployment structure is preserved.
