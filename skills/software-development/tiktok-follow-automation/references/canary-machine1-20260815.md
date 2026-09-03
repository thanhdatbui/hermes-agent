# Live canary evidence — máy 1 (2026-08-15)

## Mode 1 (follow 1 UID qua Search) — OK
- Run `20260815-104427`: `FOLLOW_RESULT {"status":"OK","followed":["charakrh768"]}`,
  exit 0. State: BUDGET_USED=1, FOLLOWED_COUNT 1→2, post-UI `CLASS=followed`.
- Vòng sửa trước khi OK:
  1. Search autocomplete không submit → `_unique_search_submit`
     (Button `id/tv_search_textview`).
  2. Backend ATX 502 + shell dump timeout → B1 hardkill + warmup recapture
     verified (`pkill -9 atx-agent/uiautomator` + `am force-stop com.github.uiautomator`
     + `uiautomator quit`, rồi `capture_persistent_ui` restart_attempts 1→0).
  3. "không thấy đúng một nút Follow" → nút là TextView `id/fds` clickable=false;
     `classify_button` ưu tiên node action `id/fds` hơn label thống kê `id/sdn`.

## Mode 2 (follow follower list của nick) — OK
- Run `20260815-120223`: `FOLLOW_RESULT {"status":"OK","followed":["hoangthiennguyen_34"]}`,
  exit 0. State: FOLLOWED_COUNT 2→3, BUDGET_USED=2.
- Vòng sửa:
  1. `_back_to_feed` fail "không quay về được feed" — UI đang ở Search history
     fullscreen (không bottom-nav). Thêm `_is_search_history_screen`
     (`tv_search_textview` + recent `Thời gian`/`Đóng` + không nav) → 1 Back về
     Feed. Lưu ý: pycache cũ khiến code mới không load — xóa `__pycache__`.
  2. Path B sample fail "row nói followed nhưng profile manual" —
     `_classify_profile_action` chỉ nhận node clickable → delegate
     `classify_button` (verify_follow) xử lý `id/fds`.

## Follow 7 người — FOLLOW_FAILED (chặn thật, từng gọi FOLLOW_BLOCKED)
- Run `20260815-125726`: `FOLLOW_RESULT {"status":"FOLLOW_FAILED",
  "followed":["hakha18062003"], "failed":true}`. Budget 7, row 1 (lipsellczaw).
- Follow được 1 (`hakha18062003`), UID kế `@lamnhu3003`: tap Follow → nút đỏ
  "Follow" (`id/fds`) không đổi sau reload, không popup → TikTok chặn follow
  thật. State giữ failed vĩnh viễn (fail-closed đúng), cần user xác nhận mở.
- **Rename 2026-08-15 (commit 5b8c1ac):** user yêu cầu bỏ từ "block" (đọc như
  lỗi script) → `FOLLOW_BLOCKED`→`FOLLOW_FAILED`, `follow_blocked`→`follow_failed`,
  `SessionResult.blocked`→`failed`, outcome `"blocked"`→`"failed"`, state JSON
  field `follow_failed` (đọc cả `follow_blocked` cũ để migrate). Reason:
  `"TikTok không nhận follow sau reload — dừng session"`.

## Lockless (device-busy guard removed, commit 5aad6b8)
- Đã xóa `device_busy` / `_video_process_busy` / `busy_check` /
  `STATE_SKIPPED_BUSY` khỏi engine + CLI + tests (guard `tiktok_workflow
  --machine N`). FOLLOW_FAILED GIỮ NGUYÊN.

## Interactive-run pitfall
- `python -m follow_runner.run_follow` không `--account-row-index` → `input()`
  prompt. Terminal tool pipe → `EOFError`. Giải pháp: dùng `clarify` hỏi user
  acc row, rồi chạy với `--account-row-index N --order random|sequential`.

## CLI flags thêm (commit 251ebbe / 6ad9e98)
- `--order random|sequential`: shuffle UID chỉ khi random (config `order` + validate).
- Prompt chọn row: liệt kê `get_all_by_machine(machine)` (row hợp lệ máy đó,
  account_row_index = thứ tự row), default row 1, invalid → exit 2.
- Máy 1 có 4 rows: lipsellczaw, duongkien1202, tranngan767, ginnyhanstei80.
