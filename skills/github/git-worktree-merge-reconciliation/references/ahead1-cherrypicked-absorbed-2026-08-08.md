# Ahead=1 branches đã cherry-pick hết — case 2026-08-08 (tiktok-luot nuoi acc)

Repo `D:\Taadaa\tiktok-luot nuoi acc`, 3 remote branches ahead=1 so master. Cả 3 verdict: ABSORBED/SUPERSEDED → xoá, KHÔNG merge nào. Merge-tree báo conflict cả 3 dù KHÔNG branch nào còn nội dung mới.

| Branch | Commit | Bằng chứng absorbed | Conflict merge-tree (exit 1) |
|---|---|---|---|
| `codex/ui-capture-030-20260729` | bd8a5c5 | Counterpart master = **e496dd7** cùng message "feat: adopt persistent UI capture 0.3.0", diff patch rỗng (identical). Master đi xa hơn: pin `automation-core 0.4.18` (branch pin 0.3.0 = CŨ hơn), `core/ui_capture.py` ~290 dòng (`_CaptureProbes`, `capture_required_ui_result`) vs branch 28 dòng. | 6 file: docs/ui-compatibility.md, core/ui_capture.py (add/add), flows/calibrate_screens.py, flows/feed_swipe_smoke.py, tests/test_ui_dump.py, requirements-automation-core.txt |
| `opencode/curious-forest` | 1a1ffe2 | Master refactor **55582fa "centralize tiktok startup recovery"**: `detect_startup_ad_splash` bị xoá khỏi `image_navigation.py` → logic ở `startup_signals.py` (`STARTUP_RETRY_XML_ERRORS` chứa `uiautomator_idle_state_error` + `is_retryable_startup_loading_state`) + recheck 0.5s trong `_capture_step` (feed_swipe_smoke.py:2717-2737) = đúng 2 lớp bảo vệ của branch. | 2 file: core/image_navigation.py, flows/feed_swipe_smoke.py |
| `opencode/neon-falcon` | 7d0c4eb | Counterpart master = **b8493db** "(#1)" — `--stat` IDENTICAL (5 files, +206/-84). Working tree có đủ symbol: `detect_allowed_generic_popup` TRƯỚC `popup_terms` (classifier.py:196, 481, 601), `PACKAGEINSTALLER_DIALOG_SCREEN` (14), `dismiss_allowed_generic_popup` (3), `_maybe_dismiss_packageinstaller_baseline` (feed_swipe_smoke.py:5526+). | 5 file: core/benign_popup.py, core/classifier.py, flows/benign_popup.py, flows/feed_swipe_smoke.py, tests/test_classifier.py |

## Trình tự xác minh đã dùng

1. `git fetch origin --prune` + `git log --oneline master..origin/<b>` — xác nhận ahead=1.
2. `git cherry -v master origin/<b>` — cả 3 ra dấu `-` (đã merge/cherry-pick).
3. Tìm counterpart: `git log --oneline -S "<symbol độc nhất>" master -- <file>` hoặc `git log --all --oneline -S "<error-term>" master` (vd `uiautomator_idle_state_error`).
4. Diff patch identical: `diff <(git show <branch> | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' | sort) <(git show <counterpart> | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' | sort)` → rỗng.
5. Symbol-level trong working tree: `grep -c "<symbol>" <file>` — đối chiếu từng symbol branch thêm với working tree (vd neon-falcon: 4/4 symbol có).
6. Pin so sánh: `git show master:requirements-automation-core.txt | grep automation-core` vs branch vs working tree — branch 0.3.0 < master 0.4.18 = stale.

## Pitfall trung tâm

`git merge-tree --write-tree master <branch>` exit 1 KHÔNG có nghĩa branch còn nội dung mới — master refactor sau cherry-pick (đổi import `automation_core.ui` → `core.ui_dump`, bỏ SystemUI filter khỏi `classify_tiktok_screen`, chuyển startup logic sang `startup_signals.py`) làm 3-way diverge ở commit level. Bằng chứng quyết định = cherry `-` + symbol đã có trong working tree.

## File rác untracked phát hiện

- `python_runner/python_runner/tests/test_scratch_mapping_diag.py` — thư mục lồng trùng tên package, biến thể scratch diag (`test_scratch_exact_assert` + print DEBUG), KHÁC bản với file ở `python_runner/tests/` → RÁC, xoá thư mục.
- `python_runner/tests/test_scratch_mapping_diag.py` (48 dòng) — scratch diag (mock VPN lỗi + print DIAG), 0 importer (`grep -rn "test_scratch_mapping_diag" --include="*.py"` rỗng ngoài chính nó) → KHÔNG commit.
- `.dispatch/hermes-json-parse-fix.spec.md` (4KB) — dispatch spec ĐÃ HOÀN THÀNH (fix đã nằm trong working tree dirty: recovery_runtime.py + test_recovery_runtime_hermes_parser.py) → KHÔNG commit; xoá hoặc `.gitignore` `.dispatch/`.
- Code THẬT phải commit: `flows/recovery_handlers.py` (233 dòng, bounded recovery handlers, evidence MANUAL_NEEDED_POPUP) + `tests/test_chain_recovery_handlers.py` (540) + `tests/test_loading_recovery_handlers.py` (160).

## Plan đề xuất (đã giao, không thực thi trong phiên phân tích)

- Commit working tree 3 nhóm riêng (KHÔNG `git add -A`):
  - C1: scheduler/recovery_runtime.py + test_recovery_runtime_hermes_parser.py + HANDOFF.md
  - C2: recovery_supervisor.py + flows/recovery_handlers.py + 4 test recovery + tasks/*.md + docs guide + AGENTS.md
  - C3: benign_popup (core+flows) + calibrate_screens + feed_swipe_smoke + 3 test ui + docs/ui-compatibility.md
- Audit APPROVED TRƯỚC khi xoá (truyền cherry `-` + merge-tree đầy đủ + diff bằng chứng 2 cặp commit).
- Xoá 7 nhánh: 3 absorbed + 4 ahead=0 (codex/tiktok-shared-popup-extraction-20260731, codex/ui-capture-041-validation-20260731, opencode/calm-cactus, worktree/opencode/nimble-lagoon).
- AGENTS.md dirty có 3 bullet full_scope takeover authorization — nhạy cảm, kiểm tra không miss rule củ; giữ EOL gốc khi commit (warning LF→CRLF).
