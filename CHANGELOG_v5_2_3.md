# v5.2.3 — Reliability menu readability fix

- Rebuilt the Reliability Room `ROOMS` navigation using native Streamlit buttons instead of `st.page_link`.
- This removes the theme/CSS conflict that caused dark, nearly invisible labels.
- Engine Shop Visit, APU Shop Visit, and Control Center now use full-width navy rounded buttons with forced white text.
- Reliability Room remains the active teal-to-blue gradient card with white bold text and cyan status dot.
- Styling now explicitly forces text color using both `color` and `-webkit-text-fill-color`.
- Flat GitHub upload structure remains unchanged.
- No changes to calculations, charts, filters, source loaders, Google Sheets, SharePoint, or session behavior.
