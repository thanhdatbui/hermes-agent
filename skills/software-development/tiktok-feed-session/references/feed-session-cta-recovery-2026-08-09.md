# Feed-session CTA / recovery evidence (2026-08-09)

## Shop CTA live XML variants

Afternoon artifacts showed changing TikTok resource IDs for the same benign in-feed Shop surface:

- Machine 4: `Mua ngay = ...:hyq`; `Đóng = ...:hyw`.
- Machine 19: `Mua ngay = ...:hwh`; `Đóng = ...:hwn`.

The stable contract is semantic + scoped: exact `Mua ngay` and exact `Đóng`, both in TikTok package, button/clickable evidence, then tap the returned `close_element`.

## Required action order

1. `drain_known_popups` / `_dismiss_feed_ad_overlay_by_swipe` tries one bounded swipe first.
2. Recapture and verify TikTok focus + a feed screen + no fullscreen Shop overlay + no Shop CTA overlay + no sensitive marker.
3. Only if swipe is not applicable or not verified, use the dynamic `Đóng` tap fallback.
4. If neither path is safe/evidenced, keep `MANUAL_NEEDED` (fail-closed).

Never tap `Mua ngay`, never use an unbounded or coordinate-only action, and never treat an unverified recapture as success.

## Machine 7 recovery evidence

The second image was transport failure rather than a TikTok popup: persistent UIAutomator returned HTTP 502, shell `uiautomator dump` timed out, then package probing timed out. The terminal signature was `ADB_TRANSPORT_LOST_AFTER_VERIFIED_PERSISTENT_CAPTURE`; keeping the machine blocked/fail-closed was correct until transport recovery is independently verified.

## Structured repair parser

Hermes/Codex repair JSON containing `decision: PATCH_READY` must be parsed at the patch boundary before planner parsing. Planner status parsing treats `PATCH_READY` as invalid by design. Preserve provider-quota detection and fail-closed validation after the decision parse.

Hermes one-shot calls need explicit UTF-8 for Vietnamese prompt/output and a bounded 900-second slot timeout; Codex's default subprocess behavior should remain unchanged unless its path needs the same fix.
