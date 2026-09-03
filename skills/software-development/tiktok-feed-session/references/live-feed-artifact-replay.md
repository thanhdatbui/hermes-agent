# LIVE feed artifact replay

## Trigger
Use for recurring `unknown TikTok state`, `manual-needed:popup`, or detector-miss alerts where the screenshot appears to show a normal TikTok feed or LIVE content.

## Evidence sequence
1. Read the target-scoped `log.jsonl` around the alert, including the next recovery/dismiss events.
2. Resolve the exact attempt from `xml_path`/`screenshot_path`; do not use a later cleanup image.
3. Open and parse the exact `ui.xml`, then inspect the matching `screen.png`.
4. Confirm the same attempt has TikTok focus/package, selected top tab, selected bottom Home tab, and LIVE/feed evidence.
5. Replay the current classifier against the exact XML offline and record the result.

## Valid LIVE feed predicate
A normal LIVE card/feed can be accepted as the selected feed type when the same capture has:

- TikTok package/focus;
- selected `Đề xuất`/For You (or another known feed tab);
- selected `Trang chủ`/Home; and
- structured LIVE evidence such as `LIVE`, `Nhấn để xem LIVE`, or `Đang LIVE`.

Do not accept a bare `LIVE` string alone. Keep typed live-room invite/product-drawer evidence on their specific popup handlers.

## Regression shape
Use an artifact-backed test when the exact artifact is available:

```python
artifact = Path(".ai-runs/<run>/machines/machine_<n>/<run>/artifacts/.../ui.xml")
if not artifact.exists():
    self.skipTest(f"artifact not available: {artifact}")
result = classify_tiktok_screen(parse_xml(artifact.read_text(encoding="utf-8")))
assert result.screen == "for-you"
assert result.manual_needed is False
assert "real TikTok LIVE feed visible" in result.reasons
```

If the artifact is unavailable, use a minimal XML fixture that preserves the production anchors and add a separate evidence note; never weaken the production detector just to satisfy a sparse fixture.

## Reporting
Separate:
- `confirmed`: exact XML + matching image establish a valid LIVE feed and classifier result;
- `excluded`: popup/unknown interpretation contradicted by the same-attempt evidence;
- `unproven`: live runtime version, account mapping, or current-device state not established by the artifact.

Do not claim a live machine is fixed from offline replay alone. Do not touch ADB/device/live recovery unless explicitly authorized.