# v5.3.1 — Excel files on Google Drive

- Replaced three permanent primary sources from native Google Sheets to Excel (.xlsx) files stored in Google Drive:
  - Technical Delay → `Delay - A330-200,A330-300,A330-900,B737-800,B737-MAX,B777-3002020-01-01 - 2026-10-06.xlsx`
  - Engine Shop Visit → `DATA ENGINE SHOP VISIT (2).xlsx`
  - APU Shop Visit → `DATA APU SHOP VISIT (2).xlsx`
- Set all three mappings to `drive_xlsx`.
- Engine and APU Google-source loaders now use the unified Drive loader so both native Google Sheets and stored Excel files remain supported.
- Automatic loading, auto-refresh, Refresh Data, and manual Excel/CSV override remain unchanged.
- Reliability Utilization (3 files) and Component Removal sources are unchanged.
- Flat GitHub repository layout is preserved.
