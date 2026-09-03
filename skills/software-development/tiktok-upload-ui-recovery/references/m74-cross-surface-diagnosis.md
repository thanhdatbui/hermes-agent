# Cross-surface diagnosis after media push

## Evidence pattern

For `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`, inspect the raw run artifacts before changing selectors or adding machine-specific coordinates:

1. Read `execution.log`, `checkpoint.json`, `report.json`, UI-capture JSON/XML, and before/after screenshots.
2. Compare the surface at initial startup with the surface immediately after `MEDIA_PUSH`.
3. A log sequence such as:
   - `WAIT_FEED ... Trang chủ`
   - Profile tap/account verification
   - media push
   - `WAIT_FEED ... Hồ sơ`
   proves the transition retained Profile rather than returning to Home.
4. A screenshot with a back arrow, one video's metadata/actions, privacy/location prompt, and no bottom navigation is Video Detail—not Home/Feed—and cannot prove a bottom-center Create/+ control.
5. Persistent UiAutomator `HTTP 502` followed by shell `NULL_ROOT_NODE`/`EXIT_137` is a secondary capture/backend failure. Do not reinterpret the earlier wrong-surface evidence as a timeout.

## Generic invariant to enforce

`MEDIA_PUSH -> bring TikTok foreground -> semantic Home/Trang chủ normalization -> fresh recapture -> verify bottom navigation and labelled bottom-center Create/+ -> VIDEO_PICK`

Use semantic selectors and fresh before/after capture. Never tap a guessed coordinate, weaken the foreground gate, or add a machine-specific workaround merely because one machine retained a different route. Keep fail-closed behavior when Home or Create is not proven.

## Replay checklist

- [ ] Initial Home/Feed proof recorded.
- [ ] Profile/account verification surface recorded separately.
- [ ] Post-push foreground package/activity recorded.
- [ ] Post-push surface is semantically normalized to Home.
- [ ] Fresh XML contains bottom navigation and labelled Create/+ control in the bounded bottom-center region.
- [ ] Screenshot agrees with XML.
- [ ] Only then enter `VIDEO_PICK`.
