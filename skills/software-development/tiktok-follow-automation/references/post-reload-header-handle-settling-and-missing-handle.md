# Post-Reload Header Handle Settling & Transient missing_header_handle (Case UI-48)

## Incident & Symptoms
- Farm Alert `[MÁY 7]`, `[MÁY 13]`: `hồ sơ identity mismatch sau khi reload (missing_header_handle) — từ chối tap Following`.
- Target: Mode 2 anchor follow in `follow_runner/flows/mode2_follow_followers.py`.
- Result: Anchor follow aborted, escalating to `MANUAL_REVIEW` and holding the device scene.

## Root Cause
1. In `_open_following_tab`, when an anchor is not yet followed, `_ensure_anchor_followed` taps `Follow` and executes `pull_to_refresh_profile(engine.adapter, sleep_after=3.5, xml_text=profile_xml)` to reload the profile and verify the updated relationship button.
2. Pull-to-refresh drags the UI down by 864px (from y=35% to 80%). When the gesture completes, Android's `SwipeRefreshLayout` / custom view displays a refresh spinner and animates the content back up to resting position.
3. On standard 1080x1920 profile headers, the handle `@uid` node (`id/sf5`) has resting bounds around `top_y = 594px`. The header scoping filter in `_find_header_handle_node` strictly enforces `top_y < 650` (Case UI-46).
4. If network response latency or device rendering causes the spring-back animation to take slightly longer than 3.5s, the initial dump in `_ensure_anchor_followed` captures the header while still pulled down (`top_y >= 650`).
5. `_find_header_handle_node` discards any handle node at `top_y >= 650` and returns `(None, "missing_header_handle")`.
6. Settling Window Insufficiency on Slower Devices (Machine 13):
   - `retries = int(getattr(engine.cfg, "verify_reload_retries", 2) or 2)` results in `settle_attempts = 3`.
   - Attempt 0 checks `ensured_xml` (immediate dump from `_ensure_anchor_followed`).
   - Attempts 1 and 2 sleep 1.0s and dump.
   - Total extra wait time is only 2.0s (attempts 1..2). On devices experiencing proxy/network latency or slower Samsung UI spring-back, the total animation + reload render latency can exceed 5.5s (3.5s initial + 2.0s settling), exhausting all attempts while the header is still returning to resting position.
   - When all attempts are exhausted, `_open_following_tab` fails closed with `hồ sơ identity mismatch sau khi reload (missing_header_handle) — từ chối tap Following`.

## Solution & Implementation
In `follow_runner/flows/mode2_follow_followers.py` (`_open_following_tab`):
When `ensured_xml != profile_xml`:
- Bounded settling poll loop with `settle_attempts = max(1, retries + 1)` using `retries = max(3, int(getattr(engine.cfg, "verify_reload_retries", 3) or 3))` guaranteeing at least 4 total attempts.
- On farm environments with slower devices (e.g. Máy 13), enforce minimum 3 retries and increase poll sleep interval to 1.5s (yielding 4.5s extra settling window post-pull-to-refresh).
- **Attempt 0 (Fast Path):** Inspect `ensured_xml`. If identity verification (`status == "ok"` and `_normalize_handle(profile_handle) == target_normalized`) passes, break immediately without extra sleep or dump.
- **Attempts > 0 (Settling Path):** Sleep 1.5s, re-dump `adapter.dump_ui()`, re-parse nodes, re-check `profile_identity_from_xml` and `_find_header_handle_node`.
- As soon as the animation finishes and the header returns to `top_y < 650`, identity verification succeeds and the loop breaks to proceed to `_following_tab_node`.
- If all attempts are exhausted and identity is still unproven, fail closed to `MANUAL_REVIEW`.

## Farm Incident Fast Triage Rule
- **CẤM chạy recursive grep/find** trên toàn bộ cây `D:/Taadaa/runtime/kibe/live` (gây 900s timeout do hàng trăm ngàn file dump/screenshot).
- **Targeted lookup:**
  1. Lấy thư mục ca/phiên mới nhất: `ls -td /d/Taadaa/runtime/kibe/live/<today>/row-* | head -n 3`
  2. Định vị trực tiếp artifact của máy: `/d/Taadaa/runtime/kibe/live/<today>/<row_dir>/<run_id>/machines/machine_<N>/`
  3. Đọc ngay `follow_result.json` và `summary.txt` tại thư mục máy đó để trích xuất exact reason và danh sách `followed` / `skipped`.

## Regression Testing
- Focused test: `test_open_following_tab_reloads_and_recovers_from_transient_missing_header_handle` in `follow_runner/tests/test_mode2_follow_followers.py`.
- Simulates initial post-reload dump with `top_y >= 650` (`status == "missing_header_handle"`), followed by a settled dump with `top_y < 650` and valid `@uid`, asserting clean recovery and successful Following tab navigation (`return True`).
- Asserts fail-closed behavior when mismatch or missing handle persists across all retries.
