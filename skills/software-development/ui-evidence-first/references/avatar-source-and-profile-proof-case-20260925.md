# Avatar source and proof case — 2026-09-25

## What failed
The run mixed three separate claims: source-image validity, upload workflow completion, and final profile rendering. It used `exit=0`, `verified=True`, `AVATAR_SMOKE_SUCCESS`, picker/crop screenshots, and a later profile screenshot as if they were equivalent. They are not. The live screen was also later found on `@vy.nguyen8730`, not the requested `@bmwarclxp1f`, so the alleged final proof was invalid.

## Durable procedure
- Confirm the live target handle immediately before every final capture. A workbook row, account-switcher expectation, old screenshot, or OCR from an earlier attempt is not current identity proof.
- Validate avatar candidates from the central video content region. OpenCV Haar detections can select TikTok’s bottom-right music-disc/UI icon; reject detections near UI borders. Inspect metadata/title and the actual candidate image; `#cosplayer`, anime, film still, dark transition, or ambiguous crop is not acceptable for a human-photo avatar.
- Treat picker tile, crop screen, Save tap, return-to-profile, and runner status as intermediate evidence only.
- Final proof requires a fresh reload of the exact target profile, a screenshot containing the exact handle and the rendered avatar, and a crop/sanity check of that actual avatar. If identity or avatar content is not visible, report `UNPROVEN`/`FINAL_BLOCKED`.
- For a failed Telegram `MEDIA:` send, retry the same artifact once only after checking that the file exists and is readable. Use a fresh unique filename/JPG when resending a corrected screenshot to avoid media-cache collision. Never claim the user saw an attachment unless delivery is confirmed.

## Evidence labels
Use `[OBSERVED]`, `[HYPOTHESIS]`, and `[UNPROVEN]`. Never convert a successful local action into a claim about TikTok CDN/profile state without fresh visual proof.
