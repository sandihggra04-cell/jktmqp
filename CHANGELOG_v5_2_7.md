# v5.2.7 — Reliability room menu same size as Engine/APU

- Removed the oversized 62 px / 18 px Reliability navigation styling.
- Copied the actual Engine/APU room-menu measurements:
  - ROOMS label: 10 px
  - active card: minimum 40 px, 11 px radius, 12 px label
  - inactive buttons: 2.55 rem minimum height, 11 px radius, .82 rem label
  - inactive fill: #17344F with #2E506E border
  - active fill: the same teal-to-blue gradient and cyan dot as Engine/APU
- Removed the extra custom navigation separator rules so spacing follows the Engine/APU pattern.
- Reliability Room remains the active item.
- Flat GitHub layout and all analytics/data-source behavior are unchanged.
