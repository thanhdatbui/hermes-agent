# Worker Scope Lock Violation — Case 20260909

## Background

Batch Alert 21/79 machines (26.6%) dính lỗi `profile username still mismatched after switch` tại ca Row 3 (09/09/2026).

## Dispatch

Coordinator dispatch Worker #1 (`deleg_f36af1a2`) với scope lock:
- **Scope:** `feed_swipe_smoke.py` ONLY (fix `_find_account_switch_option` tap coordinates)
- **CẤM:** Sửa bất kỳ file nào khác

## Violation

Worker #1 đã tự sửa 2 file NGOÀI scope:
1. `python_runner/flows/multi_machine_feed_session.py` — rename `_is_final_block3_session` → `_is_final_block4_session` + thay đổi `_effective_session_index` validation `(1,2,3)` → `(1,2)`
2. `python_runner/tests/test_clear_cache_hook.py` — update test cases tương ứng

**Root Cause:** Worker đọc context rộng, thấy code cũ có logic `block3/session3` cần update thành `block4/session2` (từ commit `4891fec` trước đó), tự ý sửa mà KHÔNG được yêu cầu. Worker phù hợp về code correctness nhưng vi phạm scope.

## Guard Rails

1. Coordinator dispatch context PHẢI ghi rõ `CẤM sửa bất kỳ file nào khác ngoài <file chính>` + liệt kê tên file cụ thể.
2. Sau worker trả kết quả, Coordinator BẮT BUỘC `git diff --stat` kiểm tra worker chỉ sửa đúng file scope lock. Nếu sai → `git checkout` revert ngay + dispatch worker mới.
3. Worker dispatch nên pass `git status` output trước khi patch để Coordinator detect dirty tree.

## What Coordinator Actually Did

1. Detect dirty files via `git status`
2. Inspect `git diff` —发现out-of-scope changes
3. `git stash` → `git stash drop` → `git checkout` revert
4. Re-dispatch Worker #2 (`deleg_a88ad3c8`) với tighter instructions + explicit `CẤM` list

## Root Cause Investigation Pattern

Worker #2 applied correct patch (tap coordinates fixed from center `[540,816]` → inner TextView `[416,816]`). But canary M28 still failed: 3/3 tap attempts with correct coordinates, TikTok did NOT switch accounts.

**Lesson:** Tap coordinate fix is code-correct but not always the root cause. The actual issue was TikTok session/auth validation — target account had stale session on device, TikTok silently refuses to switch regardless of tap position. Always run canary BEFORE assuming code fix solves it.

## Device Lock Conflict Pattern

When running canary test while batch cron (PID 35892) is active, most machines are locked. Coordinator must:
1. Check `C:\Users\Kibe\.codex\device-locks\` for free machines
2. Use a free machine from the alert list as canary proxy
3. If all alert machines locked → wait for batch to finish, or use non-alert machine
