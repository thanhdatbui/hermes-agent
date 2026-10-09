# Case UI-47: Feed Photo Post Swipe Safety & Soft Deadline Budgeting (120s Reserve)

## Incident Context
- **Incident Machine**: Machine 72 (Serial: `ce12160cd19f847f0c`, Account: `caotrinh16022004`)
- **Alert**: `GIỮ HIỆN TRƯỜNG FOLLOW TIMEOUT` • `Script: tiktok-follow` • `reason: follow-timeout`
- **Scene**: Machine 72 stranded on TikTok Home Feed (For You / Đề xuất) displaying a Photo Carousel post (`text="Ảnh"`, `id/tv_label`) with account avatar and Follow (+) button.

## Root Cause Analysis
1. **Feed Photo Post Caption Collision (`swipe_feed` starting at y = 1600)**:
   In `follow_runner/core/adapter.py`, `swipe_feed` originally calculated starting swipe coordinates at `y1 = int(h * 5 / 6)` (`y = 1600` on 1080x1920).
   On TikTok Home Feed when a post is a Photo Carousel (`text="Ảnh"`, `id/tv_label`), `y = 1600` falls directly inside the bottom caption area (`id/desc` `bounds=[36,1649][840,1757]`, `id/title` `[36,1565][222,1631]`, or `id/tv_upvote` `[60,1481][551,1529]`).
   Swiping vertically from `y = 1600` on a photo post is consumed by the Carousel / TextView widget to scroll or expand caption text rather than advancing the feed video/post, trapping the runner on the photo post.

2. **Soft Deadline Reserve Margin (60s vs 120s)**:
   In `FollowEngine`, `has_time_for_next_action` previously checked `reserve_seconds = 60.0`.
   A single follow cycle (search UID, check profile, verify Path B, or ladder recovery) can consume 40–90 seconds, and terminal application cleanup (`cleanup_after_result` / `close_all_recent_apps`) requires 15–30 seconds.
   When an action commenced with 65 seconds remaining, it finished with < 15 seconds, causing subsequent cleanup and JSON emission to exceed the 1200-second parent process deadline (`multi_machine_feed_session.py` `subprocess.run(timeout=1200)`), triggering dirty `subprocess.TimeoutExpired` and Farm Alert.

3. **Unbounded Missing UID Loops in Mode 1**:
   When workbook UIDs do not exist or fail search, each search attempt takes ~40s (12s wait on Top tab + 12s wait on Users tab). An unbounded loop over 150 missing UIDs burns through all available session time without following any accounts.

## Standardized Fixes
1. **Safe Video Viewport Coordinates in `swipe_feed` (`follow_runner/core/adapter.py`)**:
   - `cx = int(w * 0.45)` (~486px on 1080x1920, avoiding right-side action buttons).
   - `y1 = int(h * 0.72)` (~1380px, well above the bottom caption band at `y > 1500`).
   - `y2 = int(h * 0.25)` (~480px, below top tab headers at `y < 250`).
   - `duration_ms = 320` ms.

2. **Soft Deadline Budgeting (120s Reserve) in `FollowEngine`**:
   - Set default `reserve_seconds = 120.0` in `has_time_for_next_action`.
   - Gate all major loop points:
     - Top of anchor loop in `run_mode2`.
     - Top of UID loop in `run_mode1`.
     - Inside Mode 2 follower scroll loop (`while (used < budget ...)`) and pending row loop (`for row in pending:`).
     - Prior to search / anchor retries in `follow_one_uid` and `_open_following_tab`.
     - Prior to entering Mode 1 after Mode 2 in `FollowEngine.run_session`.

3. **Consecutive Missing UID Limit (`max_consecutive_not_found = 5`)**:
   - In `run_mode1`, automatically complete the session gracefully with `status: "OK"` if 5 consecutive UIDs return `skipped: không tìm thấy`.

## Verification & Regression Contract
- Unit tests: `test_swipe_feed_uses_screen_size_from_dump`, `test_swipe_feed_prefers_adapter_screen_size_api`, `test_run_mode1_breaks_gracefully_on_soft_deadline`, `test_run_mode1_breaks_on_max_consecutive_not_found`, `test_run_mode2_breaks_gracefully_on_soft_deadline`, `test_run_session_skips_mode1_when_soft_deadline_approaching`.
- Suite pass count: 511/511 tests passed.
- Live canary: `powershell.exe -ExecutionPolicy Bypass -File D:/Taadaa/tiktok-follow/scripts/run-follow.ps1 -Machine 72 -AccountRowIndex 2 -Config config/machine72.yaml -Mode 2 -ForcePreempt` -> `status: "OK"`, `followed: ["truong.thuy950"]`, `failed: false`.
