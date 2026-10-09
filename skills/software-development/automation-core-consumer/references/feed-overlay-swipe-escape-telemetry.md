# TikTok Feed Overlay Swipe Escape & Structured Telemetry

## Problem Context
When consumer adapters (such as `scripts/tiktok_workflow/adapter.py` in `Tiktok-video`) navigate between tabs via bottom navigation (e.g., `tap_profile()`), TikTok full-screen feed videos may display interactive overlays, live ad promotions, or swipe guides:
- `"Vuốt lên để xem thêm"`
- `"Đọc hoặc viết bình luận"`
- `"Thích video"`
- `"Nhấp ngay có thưởng"`
- `"nhấp ngay"`

Direct bottom-nav clicks in this state can be intercepted by ad click handlers or fail to transition tabs.

## Escape Strategy
1. **Marker Detection:**
   Identify if any overlay marker is present in the current UI XML dump:
   ```python
   OVERLAY_MARKERS = (
       "Vuốt lên để xem thêm",
       "Đọc hoặc viết bình luận",
       "Thích video",
       "Nhấp ngay có thưởng",
       "nhấp ngay",
   )
   overlay_matched = next((k for k in OVERLAY_MARKERS if k in (xml_text or "")), None)
   ```

2. **Swipe Escape:**
   Perform a gentle vertical swipe up to advance to the next video, bypassing the interactive overlay:
   ```python
   if overlay_matched:
       logger.info("[TAP_PROFILE] Phát hiện Feed video overlay; vuốt nhẹ (540, 1400) -> (540, 800) để thoát video overlay")
       self.swipe(540, 1400, 540, 800, 300)
       time.sleep(1.5)
       xml_text = self.dump_ui()
   ```

3. **Structured Telemetry:**
   Log telemetry immediately after re-dumping UI to record the marker matched and whether it was successfully cleared:
   ```python
       escaped = overlay_matched not in (xml_text or "")
       logger.info("[TELEMETRY:FEED_OVERLAY] action=swipe_escape marker='%s' escaped=%s", overlay_matched, escaped)
   ```

## Test Verification Pattern (pytest + caplog)
Unit tests should parameterize over overlay variants and assert both ADB swipe dispatch and structured telemetry:
```python
@pytest.mark.parametrize("marker", ["Vuốt lên để xem thêm", "Nhấp ngay có thưởng"])
def test_tiktok_adapter_tap_profile_escapes_feed_video_overlay_via_swipe(caplog, marker):
    adb = MagicMock()
    adb.shell.return_value = MagicMock(ok=True)
    adapter = TikTokAdapter(adb, dry_run=False)

    overlay_xml = f"<hierarchy><node text='{marker}' bounds='[96,1264][984,1345]' /><node text='Hồ sơ' bounds='[864,1794][1080,1920]' clickable='true' enabled='true' visible-to-user='true' /></hierarchy>"
    clean_profile_xml = "<hierarchy><node text='Sửa hồ sơ' bounds='[100,500][400,600]' /></hierarchy>"

    adapter.dump_ui = MagicMock(side_effect=[overlay_xml, clean_profile_xml])
    adapter.is_profile_root = MagicMock(side_effect=[False, True])

    with caplog.at_level("INFO"):
        adapter.tap_profile(force=False)

    adb.shell.assert_any_call(["input", "swipe", "540", "1400", "540", "800", "300"], timeout=15, check=False)
    assert f"[TELEMETRY:FEED_OVERLAY] action=swipe_escape marker='{marker}' escaped=True" in caplog.text
```
