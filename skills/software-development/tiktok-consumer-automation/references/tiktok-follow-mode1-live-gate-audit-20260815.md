# tiktok-follow Mode 1 — Vòng 3 audit gate pre-live (2026-08-15)

Kết quả: **APPROVED** — candidate pre-live cho máy 1 Mode 1 Follow, sau vòng 1 (findings) và vòng 2 (fix APPROVED). Vòng này là gate đọc-only trước live: không edit, không ADB, không đọc workbook/live.

## Phạm vi & evidence

- Repo: `D:\Taadaa\tiktok-follow`, branch master, baseline `07b23a1`; worktree dirty (24 file M + 3 untracked: `NUL`, `uids.txt`, `follow_runner/tests/test_adapter.py`).
- Đã đọc: AGENTS.md, PROJECT_RULES.md, HANDOFF.md, README, docs/ui-compatibility.md, docs/ai/tiktok-follow-development-guide.md, toàn bộ diff (`git diff HEAD`), file exact: follow_engine.py, mode1_search_follow.py, verify_follow.py, mode2_follow_followers.py, adapter.py, config.py, workbook.py, follow_state.py, popup.py, selectors.py, run_follow.py, toàn bộ tests.
- API contract đối chiếu với **wheel pin 0.4.44** (giải nén `D:\Taadaa\automation-core\dist\automation_core-0.4.44-py3-none-any.whl` vào temp) chứ KHÔNG phải site-packages đang cài (runtime = 0.4.43).

## Verification offline

- `python -m pytest follow_runner/tests/ -q` → **244 passed in 147.30s**.
- `py_compile` tất cả core/flows/run_follow → PASS.
- `git diff --check` → PASS (chỉ warning LF→CRLF, không whitespace lỗi).
- Không đọc `uids.txt`/`NUL`; không chạm live/workbook.

## Xác minh từng yêu cầu user (file:line)

1. **Reuse core account open/select/verify**: `follow_engine.py:218-287` `_core_switcher`/`_canonical_switch_verify` gọi `open_account_switcher` → `select_exact_account` → `verify_selected_account` (core 0.4.44, attempt pin profile=1/switcher=1/load=1); adapter chỉ wrap (`adapter.py`), không tự viết switcher. Ladder B1→B2→B3 chỉ khi capture-backend signature (`recoverable_codes` line 258-262).
2. **Prove Feed trước Search**: `follow_engine.py:337-348` `ensure_feed_for_follow` = `mode2_follow_followers._back_to_feed` (bounded ≤4 Back + ≤1 Home semantic; yêu cầu đúng 1 Search/Home/Profile, Home selected, Profile unselected, không follower recycler — mode2:295-362). Gọi **mỗi UID** trong `run_mode1` (mode1:43-46; test `feed_checks == 2`).
3. **Exact Search UID**: `mode1:194-267` `_wait_search_result`: đúng 1 node exact-normalized, non-EditText, non-editable, có bounds; avatar semantic (1 clickable descendant bọc 1 ImageView cùng bounds); `tvl_unified_sug` continuation đúng 1 lần.
4. **Đúng 1 Profile identity `id/sf5`**: `mode1:172-191` `_classify_exact_profile_action`: `len(identity_nodes)==1`, `username_element.resource_id` kết thúc `id/sf5`, normalized == UID; sai/trùng → `identity_mismatch` TRƯỚC tap.
5. **Đúng 1 clickable Follow**: `mode1:323-344` `_tap_follow_button`: exact marker set (không substring), clickable + bounds, `len(matches)==1`; `Follower` không match; ambiguous/non-clickable → False.
6. **Fresh identity-bound verify**: `verify_follow.py:57-131` `verify_after_tap`: dump MỚI sau tap (adapter reject capture_id lặp — adapter.py:137-138), mọi reload re-bind `classify_fn`; identity mismatch sau tap/reload → MANUAL_REVIEW; hết `verify_reload_retries` not_followed → FOLLOW_BLOCKED dừng session.
7. **Loại active account**: `follow_engine.py:350-362` `follow_uids()` lọc theo `lstrip("@").casefold()` ≠ `active_account_handle` (set tại run_session:649).
8. **Budget/state fail-closed**: run_mode1 budget = min(session, remaining); consume/mark chỉ khi "followed"; manual không ghi skipped; `FOLLOW_BLOCKED` persist + short-circuit run_session:625-629; `SKIPPED_BUSY` qua process guard regex chính xác `--machine N` (follow_engine.py:82-98); lockless hoàn toàn (không `acquire_device_lock`/`SKIPPED_LOCKED`).

## Findings

- **NIT (vận hành, không phải lỗi code)**: runtime `pip show automation-core` = **0.4.43**, trong khi pin/dự kiến production = 0.4.44. API 0.4.44 đối chiếu từ chính wheel khớp mọi signature (`open_account_switcher`, `select_exact_account`, `verify_selected_account`, `profile_identity_from_xml`, `capture_ui_xml`, `prepare_*`, `reboot_and_restore`, `AdbClient`); nhưng trước live máy 1 phải cài đúng 0.4.44 (hoặc probe interpreter sẽ chạy live) để khớp contract đã audit. Lỗi tương tự class "pin ≠ runtime" đã dính ở recovery-v3 (venv 0.4.40 vs pin mới).
- **NIT doc**: HANDOFF.md:58 ghi "full 233 passed" nhưng suite hiện tại 244 passed — số liệu cũ, chỉ doc.
- **NIT code**: `mode1:264` `_wait_search_result` khi `len(elements) != len(nodes)` trả `identity` raw (bounded) thay vì bounce loop — an toàn vì profile identity gate `id/sf5` chặn mọi profile sai trước tap Follow; không có hậu quả follow nhầm.
- `NUL` + `uids.txt` untracked giữ nguyên (HANDOFF chỉ đạo không chạm) — không nằm trong diff candidate.

## Kết luận

Candidate đáp ứng đủ chuỗi máy-1 Mode-1: startup core → switcher core → verify identity → `_back_to_feed` bounded → exact Search UID → 1 profile `id/sf5` → 1 clickable Follow → fresh identity-bound verify; loại active account; budget/state fail-closed; lockless `SKIPPED_BUSY`. APPROVED cho pre-live; bước live là của operator (nhớ xác nhận runtime core 0.4.44).
