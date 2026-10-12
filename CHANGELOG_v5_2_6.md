# v5.2.6 — Reliability room menu exact-match fix

- Removed the HTML-anchor navigation that Streamlit Cloud rendered as literal code.
- Reliability now uses the same native `st.button` room-switching pattern as Engine/APU.
- Injected the room-menu CSS after the Reliability global theme so the blue generic button skin cannot override it.
- Inactive room buttons: dark navy, 16 px radius, 62 px height, white 18 px labels.
- Active Reliability room: teal-to-blue gradient, cyan status dot, bold white 18 px label.
- HTML fragments are single-line to prevent Markdown code-block interpretation.
- Flat GitHub upload structure is preserved.
- No changes to analytics, calculations, source loading, Google Sheets, SharePoint, or session behavior.
