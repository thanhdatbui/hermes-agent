# ATX-Agent Stub Foreground & WebView Input/Retry Discipline

## 1. ATX-Agent UIAutomator Stub Activity Foreground Lockout

### Symptoms
- 100% of batch machines crash immediately upon launching target app (e.g. TikTok):
  `RuntimeError: [01_open] TikTok not foreground after clean launch`
- `dumpsys window windows | grep mCurrentFocus` shows:
  `mCurrentFocus=Window{... u0 com.github.uiautomator/com.github.uiautomator.MainActivity}`
- Screen resolution in UI dump shows Landscape (1920x1080) instead of Portrait (1080x1920), displaying the Chinese developer options UI of the UIAutomator stub.

### Root Cause
- When `reset_atx_agent(adb)` executes recovery, it kicks the stub package using:
  `adb.shell(["monkey", "-p", "com.github.uiautomator", "1"])`
- This directly opens `com.github.uiautomator.MainActivity` into the foreground.
- When `open_app()` subsequently attempts clean launch of TikTok or other target apps via `monkey -p <target_pkg> 1`, the target app is prevented from taking foreground focus by the top-level stub activity or fails to transition out of landscape orientation.

### Invariant & Fix Rules
1. **Never leave stub in foreground**: Any helper invoking `monkey -p com.github.uiautomator` or restarting the atx daemon MUST follow up with `adb.shell(["input", "keyevent", "3"])` (HOME) to guarantee the screen returns to the launcher.
2. **Foreground preflight guard in `open_app`**:
   Before launching the target app, inspect `_foreground_focus(device_id)`:
   ```python
   if "com.github.uiautomator" in fg:
       shell(device_id, "am", "force-stop", "com.github.uiautomator")
       shell(device_id, "am", "force-stop", "com.github.uiautomator.test")
       shell(device_id, "input", "keyevent", "3")
       time.sleep(1.0)
   ```

---

## 2. Android WebView Input Clearing & Stale Validation Error Races

### Symptoms
- Registration scripts fail with `Username bị taken sau 5 lần thử` on virtually all machines, even when generating high-entropy pseudo-random usernames (e.g. `giaxuanphuongngo872krmw556`).
- Log shows attempt 1, 2, 3, 4, 5 each logging a longer username or immediately flagging the newly typed username as taken.

### Root Causes
1. **`clear_field` failure in WebViews**:
   - `input keyevent 123` (MOVE_END) is frequently ignored by Android WebViews.
   - Sending 60x `keyevent 67` (DEL) while the cursor is not at the end fails to clear the existing text.
   - The subsequent `input text <new_username>` appends to the old username, producing strings exceeding the 30-character Google username limit.
2. **Stale DOM Error Text Race**:
   - When attempt 1 fails with *"Tên người dùng này đã được sử dụng. Hãy thử tên khác"* (or *"That username is taken"*), the error text remains rendered on the WebView.
   - In attempt 2, after entering the new username and tapping Next, Google makes an asynchronous server request.
   - The runner executes `xml = get_ui_xml(device_id)` after a short sleep (`D_MEDIUM` ~3s) without verifying that the form has actually initiated/completed a state transition.
   - The scraper reads the persistent error message from attempt 1 and falsely concludes that attempt 2 was also taken.

### Invariant & Fix Rules
1. **WebView Input Text Replacement (`clear_field` Multi-Strategy & Verification)**:
   - Do not rely solely on `keyevent 123 + keyevent 67`.
   - Use double-tap at target coordinates to select text.
   - Attempt multiple Select All mechanisms: `input keycombination 113 29` (Ctrl+A), `input keyevent --meta 4096 29`, and `input keyevent 28` (KEYCODE_CLEAR), then `input keyevent 67` (DEL).
   - Perform bidirectional deletion to catch cursors regardless of position:
     - `keyevent 123` (MOVE_END) + batch 50 `keyevent 67` (DEL).
     - `keyevent 122` (MOVE_HOME) + batch 50 `keyevent 112` (FORWARD_DEL).
     - Batch 30 `keyevent 67` (DEL) as cleanup.
   - Verify text in UI XML dump (recognizing valid placeholders like `"Tên người dùng"`, `"Username"`). If text persists, retry clearing up to 3 times.
   ```python
   def clear_field(device_id, node=None, coord=None, label="field"):
       target_coord = coord or (node.get("coord") if isinstance(node, dict) else None)
       target_rid = node.get("rid") if isinstance(node, dict) else None
       empty_placeholders = {"", "tên người dùng", "username", "tạo địa chỉ gmail", ...}
       for attempt in range(1, 4):
           if target_coord:
               shell(device_id, "input", "tap", str(target_coord[0]), str(target_coord[1]))
               time.sleep(0.06)
               shell(device_id, "input", "tap", str(target_coord[0]), str(target_coord[1]))
               time.sleep(0.12)
           try: shell(device_id, "input", "keycombination", "113", "29", timeout=5)
           except Exception: pass
           try: shell(device_id, "input", "keyevent", "--meta", "4096", "29", timeout=5)
           except Exception: pass
           try: shell(device_id, "input", "keyevent", "28", timeout=5)
           except Exception: pass
           shell(device_id, "input", "keyevent", "67")
           shell(device_id, "input", "keyevent", "123")
           shell(device_id, "input", "keyevent", *(["67"] * 50))
           shell(device_id, "input", "keyevent", "122")
           shell(device_id, "input", "keyevent", *(["112"] * 50))
           shell(device_id, "input", "keyevent", *(["67"] * 30))
           # Verify via XML dump and break if cleared
   ```

2. **State Transition Gate Before Checking Error Text (`wait_for_username_response`)**:
   - Never check for taken error strings immediately or during loading.
   - Poll for active loading indicators (`class="android.widget.ProgressBar"`, `role="progressbar"`, `Đang tải`, `Loading`, `Please wait`) until loading finishes.
   - Check if screen transitioned to Password screen (`is_google_password_screen_xml`) BEFORE evaluating taken error strings: if password screen is reached, immediately break out of the loop with success.
   ```python
   def wait_for_username_response(device_id, timeout=12.0, interval=0.5):
       time.sleep(2.0)
       end = time.time() + max(1.0, timeout - 2.0)
       saw_loading = False
       while True:
           xml = get_ui_xml(device_id)
           is_loading = ('class="android.widget.ProgressBar"' in xml or has_text_loose(xml, "Đang tải", "Loading", "Please wait"))
           if is_loading:
               saw_loading = True
               if time.time() < end:
                   time.sleep(interval)
                   continue
           if saw_loading:
               time.sleep(0.3)
               xml = get_ui_xml(device_id)
           return xml
   ```

3. **Consumer Contract Test Synchronization for `get_ui_xml`**:
   - When consumer repos upgrade `get_ui_xml` to use `capture_atx_session_ui` instead of legacy `capture_ui_xml`, legacy tests mocking `capture_ui_xml` fail because real ADB calls are made against mock serials (causing multi-minute timeouts and `assert '' == '<hierarchy />'`).
   - Mock `automation_core.persistent_ui.capture_atx_session_ui` (and `reset_atx_agent`) directly in the contract tests.
   - Always ensure `pytest.ini` with `pythonpath = . D:/Taadaa/automation-core/src` exists in consumer repos to avoid collection/import errors.
