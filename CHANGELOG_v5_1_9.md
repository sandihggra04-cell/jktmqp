# v5.1.9 — Flat GitHub upload layout

- Removed the runtime dependency on `rooms/`, `pages/`, `src/`, and `assets/` folders.
- Reliability, Engine Shop Visit, and APU Shop Visit page scripts now live directly beside `app.py`.
- Reliability helper modules were renamed with `rel_` prefixes and moved to repository root.
- Engine helper modules were renamed with `engine_` prefixes and moved to repository root.
- Shared source loader and session upload helpers now live directly in repository root.
- Required image assets now live directly in repository root.
- All `st.Page` and `st.switch_page` targets were updated to flat filenames.
- Runtime source directories are created automatically when needed and do not have to be uploaded to GitHub.
- Google Sheets, SharePoint Doc.aspx, black Source URL text, analytics, and session-only upload behavior remain intact.
