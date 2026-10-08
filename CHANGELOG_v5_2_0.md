# v5.2.0 — Flat Reliability runtime fix

- Fixed the Reliability Room `RuntimeError` on Streamlit Cloud.
- Removed the obsolete check that still required an old `src/` folder.
- Reliability now imports the flattened `rel_*` modules directly from the repository root.
- Fixed one remaining APU logo path that still assumed the former nested folder structure.
- Runtime fallback data directories are now created automatically at startup and do not need to be uploaded to GitHub.
- Re-audited the flat Python source for old `rooms/`, `src/`, and `parents[2]` dependencies.
- No changes to Reliability calculations, Engine/APU Shop Visit calculations, Google Sheets, SharePoint Doc.aspx support, or session behavior.
