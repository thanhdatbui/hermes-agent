# Case UI-29: Search Submit Keycode Enter Fallback & Search Button Classification

## Background & Incident Context
- **Incident:** Máy 28 (`tienpham7676`) halted in `tiktok-follow` during Mode 1/Mode 2 UID search:
  `🚨 [MÁY 28] DỪNG PHIÊN • Script: tiktok-follow • Tài khoản: tienpham7676 • Lý do: hồ sơ identity mismatch: expected @masyctsyy02 got • Trạng thái: 🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`.
- **Live UI Observation:** The search screen had already received the typed UID (`masyctsyy02`) into the search bar (`hnl`), but the Samsung Keypad IME (`com.sec.android.inputmethod`) remained open on the lower half of the screen. The search autocomplete suggestions were displayed, but the search query was never formally submitted.

## Root Cause (Anti-Pattern)
1. In `follow_runner/flows/mode1_search_follow.py::_unique_search_submit`, the selector strictly matched only nodes with `class="android.widget.Button"`.
2. On some devices or newer TikTok/Samsung IME UI layouts, the search action text `tv_search_textview` ("Tìm kiếm" / "Search") might render as an `android.widget.TextView` or its bounds might be partially occluded / not resolved cleanly in XML when the IME is active.
3. When `_unique_search_submit` returned `None`, `_nav_search` skipped tapping the Search submit button and immediately proceeded to `_wait_search_result(adapter, uid, timeout=12)`.
4. Because the search query was never submitted, the screen remained stuck on the autocomplete suggestions dropdown rather than navigating to Top / Users results. The subsequent profile check failed with an empty handle `got ` causing the identity mismatch farm alert.

## Proven Fix Pattern
1. **Broaden Widget Class & Filter Non-TikTok Packages in `_unique_search_submit`:**
   ```python
   matches = [
       node for node in nodes
       if node.get("bounds")
       and node.get("clickable") is True
       and node.get("class") in ("android.widget.Button", "android.widget.TextView")
       and (node.get("resource_id") or "").rstrip("/").endswith("id/tv_search_textview")
       and (not node.get("package") or node.get("package") not in non_tiktok_packages)
       and _normalize_search_value(node.get("text") or "") in labels
   ]
   ```
2. **Fallback to `KEYCODE_ENTER` (keyevent 66):**
   If `_unique_search_submit(initial_xml)` returns `None` (e.g. submit node not present or occluded), dispatch `adapter.keyevent(66)` (`KEYCODE_ENTER`) to submit the active search query directly through the input method editor before polling for results:
   ```python
   submit = _unique_search_submit(initial_xml)
   if submit is not None:
       tap_center(adapter, submit)
       time.sleep(2)
   else:
       adapter.keyevent(66)  # KEYCODE_ENTER fallback
       time.sleep(2)
   node = _wait_search_result(adapter, uid, timeout=12)
   ```

## Verification & Regressions
- Unit test: `test_nav_search_submits_exact_uid_before_waiting_for_results`
- Full suite test: `pytest follow_runner/tests/` (402 passed)
- Device verification: Send HOME (`keyevent 3`) to return to clean launcher state and capture live screenshot proof.
