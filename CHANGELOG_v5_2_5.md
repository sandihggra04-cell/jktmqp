# v5.2.5 — Reliability menu visual lock

- Replaced the Reliability room switcher buttons with pure HTML anchors.
- This prevents Streamlit's global button theme from overriding the intended navy/teal room-menu colors.
- Engine Shop Visit and APU Shop Visit are now dark navy rounded buttons with white labels.
- Reliability Room is a teal-to-blue active card with a cyan status dot and bold white label.
- Control Center is a dark navy rounded button with white label.
- Navigation uses the registered Streamlit URL paths: `/shop-visit`, `/apu-shop-visit`, `/reliability`, and `/`.
- Flat GitHub layout remains unchanged.
- No changes to analytics, source loading, Google Sheets, SharePoint, or session behavior.
