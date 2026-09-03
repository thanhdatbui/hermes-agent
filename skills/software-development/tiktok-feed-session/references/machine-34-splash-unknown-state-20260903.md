# Machine 34 — Splash-focused "unknown TikTok state" (2026-09-03)

## Hiện trường
- Alert: Farm Alert Máy 34 (unknown TikTok state), repo `tiktok-luot nuoi acc`.
- `D:/Taadaa/tools/inspect_machine.py 34` chỉ là stub: in `adb devices`, KHÔNG cho screen/log/step.
- Kiểm chứng trực tiếp: máy 34 online (`ce031603b3158b0b02`), đã cài
  `com.ss.android.ugc.trill`, focus OS là TikTok **SplashActivity**
  (`com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity`),
  không phải launcher.
- Screenshot tươi ~101KB tối đen (mean lum ~5.8): frame splash đen lúc cold-start.
- Batch `.ai-runs/20260903-192749` fail với `cohort-target-mismatch`, 0 swipes —
  đây là lỗi gate cohort, KHÔNG phải bằng chứng lỗi device (xem pitfall bên dưới).

## Root cause (code)
- `_is_startup_loading_retry_row()` trong
  `python_runner/flows/feed_swipe_smoke.py` gate `detected == unknown` bằng
  kích thước screenshot `0 < size < 80_000`.
- Row splash-focused + `detected unknown` + screenshot LỚN (stale launcher/
  wallpaper/black frame, XML none) bị loại khỏi retry → baseline dừng ngay sau
  1 attempt với `"unknown TikTok state"`, dù app đang launch dở và chỉ cần
  recapture bounded thêm là focus ổn định / launcher-recovery tiếp quản.
- Các path recovery sẵn có (`_is_launcher_focus_loss`,
  `_relaunch_and_poll_tiktok_focus`, baseline/before-swipe recapture) không bao
  giờ được tới vì đã fail-closed trước đó.

## Fix đã áp dụng (worktree, `git diff --check` sạch)
- Thêm `_is_splash_launch_focus(ctx, row)`: True khi đúng package TikTok +
  activity chứa `splash`.
- Thêm exemption HẸP trong `_is_startup_loading_retry_row()`, đặt TRƯỚC
  size-gate: splash-focused + unknown → retry bounded. Genuinely stuck splash
  vẫn fail sau hết retry; MainActivity + unknown + ảnh lớn vẫn fail-closed.
- Test trong `python_runner/tests/test_feed_session_smoke.py`:
  - `test_splash_focused_large_screenshot_unknown_is_launch_retry_not_unknown_stop`
    (Splash + 763708 bytes + unknown → retry True).
  - `test_non_splash_large_screenshot_unknown_stays_fail_closed`
    (MainActivity + cùng size → False).
- Kết quả: `pytest -k "startup_baseline_with_tiktok_focus or
  splash_focused_large or non_splash_large"` → **3 passed**.

## Pitfall: đừng nhầm lỗi gate cohort với lỗi device
- Lệnh `run-feed-session.ps1 -Machines 34 -Row 1 -RecoveryTestSwipes 2
  -SkipAccountWorkbookSync -Run` (không `-LocalRun`) đi path multi-machine
  cohort: env có `TIKTOK_FEED_WORKER_ID` + assignment manifest nhưng
  `TIKTOK_FEED_COHORT_ARTIFACT` rỗng → child config dính `_worker_id` và
  `_apply_cohort_identity()` fail-closed TRƯỚC khi chạm device:
  `"cohort artifact and assignment manifest are both required for a live
  cohort child"` (`cohort-target-mismatch`, 0 swipes).
- Cron production truyền `-CohortArtifact` theo từng row
  (`scripts/hermes_cron/tiktok_runner.py`) nên không gặp.
- Quy tắc: trước khi chạy wrapper, kiểm tra `TIKTOK_FEED_COHORT_ARTIFACT`;
  nếu rỗng thì hoặc xin artifact cohort row hiện hành, hoặc chạy canary direct
  `feed-session-smoke` single-machine theo `references/live-canary-after-fix.md`.
  Đọc per-machine `summary.txt`, đừng kết luận device-fail từ batch headline.
