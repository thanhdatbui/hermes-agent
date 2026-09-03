# Recovery ladder + splash-stuck — code map (state_machine.py, commit 6ad3cfd 2026-08-10)

Code hiện thực của "RULE 3 bước fix lỗi UI" trong
`D:\Taadaa\Tiktok-video\scripts\tiktok_workflow\state_machine.py`. Dùng khi debug/sửa
tiếp recovery của OPEN_TIKTOK / WAIT_FEED / DISMISS_POPUPS.

## Ladder 3 bước — `_run_ui_failure_ladder(include_relaunch=True)`
- B1: `_recover_uiautomator(adb, timeout=10, attempts=[], label="ui_failure_ladder_atx_kill")`
- B2: `prepare_app_for_automation(adb, package, focus_reader=..., desired_free_space="5G",
  focus_attempts=10, focus_retry_delay=1.5)` → `_wait_for_feed(adapter, feed_indicators,
  timeout=feed_timeout)`; feed OK → `is_ui_unavailable=False`, `error=None`,
  `recovery_resume_state=WorkflowState.OPEN_TIKTOK.value`, return True (resume từ OPEN_TIKTOK).
- B3: `_maybe_soft_reboot_recovery()` — signature-bounded:
  `soft_reboot_recovery_attempts[signature]` max 1/lần, run cap `SOFT_REBOOT_MAX_TOTAL=3`;
  cần adapter + adb_client + device_transport + `_capture_soft_reboot_artifact` (screenshot).
- Return True nếu ≥1 bước chạy → caller `return False` khỏi handler (để `_run_states`
  consume `recovery_resume_state`); False nếu cạn → MANUAL_REVIEW.

Call sites (thay cho chỗ dừng sớm MANUAL_REVIEW cũ):
- DISMISS_POPUPS: dump-fail đầu (`[UI_DUMP_FAILED]` / `uiautomator_idle_state_error`),
  popup-loop dump-fail, `_recover_video_pick_shop_replay_card` fail sau Back →
  `_run_ui_failure_ladder()` (đủ B1+B2+B3).
- OPEN_TIKTOK classified-fail (`is_ui_unavailable and error`) →
  `_run_ui_failure_ladder(include_relaunch=False)` — B2 đã là vòng lặp
  `APP_RELAUNCH_MAX_ATTEMPTS=2` phía trên. Bug cũ: early-return
  "Classified recovery stopped before generic retry" = bỏ qua B3, dừng sớm.

## Splash-stuck — `_recover_splash_stuck(adapter, package)`
- Evidence máy 5/35: splash đen 100% sau wait-feed timeout
  (file `coordinate-fallback-open_tiktok-before.png`).
- Flow: `close_all_recent_apps(adb, timeout=20)` (+ xác minh
  `_recents_empty_via_dumpsys` / `_verify_localized_empty_recents` nếu
  `step.result != "success"`) → `adapter.launch_app(package)` → quay lại wait feed.
- Budget riêng: `SPLASH_STUCK_RECOVERY_MAX = 2`, checkpoint `splash_stuck_recovery_used`.
  KHÔNG dùng `prepare_app_for_automation` → không nhầm ladder B2 (test phân biệt bằng
  assert `prepare == 0`).
- Kích hoạt từ WAIT_FEED: (1) nhánh launcher-underlay ổn định ≥2 polls — trước đây
  `return True` (nhận splash làm feed = bug máy 5/35); (2) timeout hết mà
  `_package_is_foreground(adapter, package) is True` → `deadline = time.time() + timeout;
  continue`.

## Retry budget (rule)
- Cùng chỗ = cùng signature `{state}:{error_code}` (từ `_soft_reboot_failure_signature`);
  B1/B2 vẫn thử lại, B3 cạn sau 1 lần → dừng. Khác chỗ → B3 mới được dùng.
- Test: `test_ui_failure_ladder_retry_budget_three_steps_then_stop_same_place`.

## Tests + TDD notes
- Test mới ở `tests/test_tiktok_workflow.py` (class TestPipelineIntegration):
  `test_wait_for_feed_splash_stuck_closes_recents_and_relaunches_bounded`,
  `test_dismiss_popups_replay_card_failure_routes_into_ladder`,
  `test_open_tiktok_classified_failure_still_runs_ladder_b3`,
  `test_ui_failure_ladder_retry_budget_three_steps_then_stop_same_place`,
  `test_wait_for_feed_no_longer_accepts_stuck_splash_under_launcher`
  (đổi expectation cũ True → False).
- RED hợp lệ khi feature chưa tồn tại: `AttributeError: no attribute '_run_ui_failure_ladder'`.
- Full suite: `python -m pytest tests/ -q -p no:cacheprovider` (~73s) → 364 passed.
  Pre-existing fail KHÔNG liên quan: `test_machine_inventory.py` version gate đòi
  `0.4.35` trong khi `run_tiktok_upload_batch.ps1` đang `0.4.40` (cả ở HEAD). Xác minh
  pre-existing bằng `git show HEAD:<file> | grep <chuỗi>` trước khi đổ lỗi cho thay đổi.

## CRLF byte-safe splice (bắt buộc cho repo này)
- `state_machine.py` (~11k dòng, 494KB) và `tests/test_tiktok_workflow.py` đều CRLF
  (verify: `b.count(b'\r\n') == b.count(b'\n') == b.count(b'\r')`).
- KHÔNG dùng patch tool — có thể phá EOL. Dùng script Python: đọc `decode('utf-8')`,
  helper `cr(s) = s.replace('\n','\r\n')`, mọi anchor `assert text.count(a) == 1`,
  ghi `encode('utf-8')`, sau đó kiểm tra lại CRLF/LF count + `ast.parse` OK.
- Pitfall: heredoc bash DÀI trong git-bash fail `unexpected EOF while looking for
  matching '` — viết script vào file tạm bằng write_file rồi `python file.py`,
  không nhúng inline trong terminal.
- Commit: chỉ add 2 file code (state_machine.py + test); KHÔNG add docs
  (PROJECT_RULES.md / HANDOFF.md / AGENTS.md là session khác quản lý).
