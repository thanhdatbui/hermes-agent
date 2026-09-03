---
name: tiktok-follow-automation
description: "Canonical TikTok Follow runner: Mode 1/2, video gate, Path B, UI evidence, and fail-closed farm operations."
---

# TikTok Follow Automation

Use this skill for developing, debugging, testing, verifying, or safely operating the canonical TikTok follow runner. It covers Mode 1 search-follow, Mode 2 anchor/follower follow, video gates, identity verification, UI selector drift, state/budget semantics, cleanup, and live-canary discipline.

## Non-negotiable operating rules

- Treat `taikhoan_run_safe.xlsx` / the configured safe workbook as the only UID mapping source. Do not read credential columns or substitute a legacy UID source.
- A fix for a live machine incident means a source-code patch in the consumer repository, deterministic regression tests, updated case documentation, and a canary when the device is available. Manual ADB interaction alone is evidence, not a fix.
- Preserve fail-closed behavior: never tap an ambiguous account, relationship action, tab, or row. Require exact identity and row-scoped action binding.
- Keep live evidence separate from offline evidence. A blocked live canary is not a passing canary.
- Live canary fidelity: When an incident occurs in `tiktok-follow` (reported via Farm Alert `• Script: tiktok-follow`), the verification live canary MUST execute `follow_runner/run_follow.py` with the exact machine number and `--account-row-index` matching the incident slot. Never rerun `multi-machine-feed-session` or a generic feed script as a substitute canary for a follow runner incident.
- Never kill an official farm owner, release its lock, restart ADB, clear package state, or stop cron to force a test.

## Parent Feed Session Follow Hook Gating (`multi_machine_feed_session.py`)

Before the standalone `follow_runner` is even invoked, the parent feed session (`python_runner/flows/multi_machine_feed_session.py` → `_run_follow_hook`) enforces **four mandatory gates**. If any gate fails, the follow hook is **skipped entirely** (clean `status: "skipped"`, `failed: 0`, no subprocess spawned):

1. **Video Gate ≥ 5 (lines 1939–1967)**: `video_count < 5` (0..4, `None`, empty) → skip with reason `under-5-videos-follow-disabled`. Nick chưa đủ trust score, follow sẽ bị nhả 100%.
2. **Warmup Phase Row 3–6 (lines 1969–1989)**: `account_row_index in (3, 4, 5, 6)` → skip with reason `tik{row}-warmup-feed-only`. Chỉ Row 1/2 (đã qua warmup) được chạy follow hook.
3. **Feed Session Allowlist (lines 2002–2039)**: Chỉ cho phép khi feed session `status ∈ {success, degraded}` **hoặc** fail do hết swipe/timeout (`feed_swipe_limit_reached`, `swipe_timeout`, `feed_session_limit_reached`, `max_swipes_completed`). Fail do popup login, account error, recovery kẹt → skip.
4. **Per-Nick Cooldown Check (lines 2041+)**: Đọc `follow_state_<machine>_row_<index>.json`; nếu nick dính `follow_failed: true` hôm nay → chặn riêng nick đó, nick khác trên máy vẫn chạy.

**Quan trọng:** Đây là fail-closed gating ở tầng feed session — không phải logic bên trong `follow_runner`. `follow_runner` chỉ được spawn khi **tất cả 4 gate đều pass**.

---

## Triage: Máy Không Chạy / Màn Hình Bị Khóa

### Pattern 1: blocked-vichanger-vpn → Keyguard
Khi máy bị khóa màn hình, không thấy chạy, và lock tồn tại `status: blocked`:
1. `python D:/Taadaa/tools/inspect_machine.py <N>` → kiểm tra `Keyguard showing=true`.
2. Đọc `machine_<N>.lock.json`: `status: blocked`, `owner_active: false`.
3. Đọc `machines/machine_<N>/<run>/summary.txt` trong artifact → `final_status: blocked-vichanger-vpn`.
4. Xác nhận WiFi: `adb -s <serial> shell "dumpsys wifi | grep mWifiInfo | head -2"` → `DISCONNECTED`.
5. Fix: `adb -s <serial> shell svc wifi enable` → chờ 10-15s.

Xem chi tiết: `references/wifi-disconnect-keyguard-blocked-vichanger-vpn.md`

### Pattern 2: Lock Stale vs Lock Đang Sống
```python
import psutil
try:
    p = psutil.Process(<pid_from_lock>)
    print(p.name(), p.cmdline())  # còn sống → BLOCKED thật
except psutil.NoSuchProcess:
    print("PID dead — lock stale")  # lock có thể clear
```

### Artifact Root cho Run Hiện Tại (Hermes Cron)
Run artifact không nằm trong `.ai-runs/` mặc định mà theo path từ `--artifact-root`:
`D:/Taadaa/runtime/kibe/live/<date>/row-<N>-<time>/<run_id>/machines/machine_<N>/`

1. Prove the current UI is Feed before searching. If `_back_to_feed` fails (e.g. nested Search stack or Samsung soft keyboard), invoke the recovery ladder (`engine.recover_ui()`) to restore Feed cleanly before raising `MANUAL_REVIEW`.
2. Open Search, bind the input semantically, type the exact UID, and submit.
   - **Search Submit & Keyboard Occlusion (Case UI-29)**: `_unique_search_submit` must support both `Button` and `TextView` (`class in ("android.widget.Button", "android.widget.TextView")`) while filtering out non-TikTok packages. If `_unique_search_submit` returns `None` (e.g. submit button occluded by soft keyboard), dispatch `adapter.keyevent(66)` (`KEYCODE_ENTER`) as an immediate fallback before waiting for search results to avoid getting stuck on the autocomplete suggestions screen. Details in `references/search-submit-enter-fallback-and-ime-occlusion.md`.
3. Prefer an exact account result. If Top contains only video-grid results (no direct user row found), detect an unselected `Người dùng`/`Users` tab in the bounded tab strip (`bounds[1] < 450` and `(y + h) < 600`), tap it, and re-scan.
   - **Search Card Avatar Touch Target & Follow Timeout (Case UI-38)**: In TikTok 46.x Top search results, account cards (`id/v09`) may omit child `ImageView` nodes. If `avatar_targets` is empty and the card is wide (`w > h * 1.5`), `_exact_search_result_from_xml` must adjust target bounds to the left avatar square `(x, y, min(w, h), h)` rather than returning full card bounds `(0, y, 1080, h)` which taps inert center whitespace `(540, y)` and triggers follow timeout loops. Details in `references/search-card-avatar-bounds-and-follow-timeout.md`.
4. On Users results, prefer the unique account handle node such as `tv_aweme_id`; reject video-only creator labels and display-name-only matches (`tv_username`).
5. Open the profile and verify the header UID exactly before tapping Follow.
6. Verify the relationship action after the tap and record state only after the result is proven.

## Mode 2: anchor/follower workflow

1. Select only eligible internal anchor UIDs from the safe mapping, respecting the configured anchor cap (max 3 anchors per session, selected randomly from Tik1/Tik2 pool) and order.
2. Hybrid execution order: Mode 2 runs first (following-list internal). If Mode 2 finishes/exhausts anchors with remaining session budget, the runner automatically chains into Mode 1 (`run_mode1`) to search direct UIDs from workbook to fulfill the quota.
3. Daily budget cap & zero-follow completion: If a machine already reached its daily limit (`budget_used >= budget_per_day`, default 60), the runner exits cleanly with `status: "OK"`, `followed: []`, `failed: 0`. This is a normal business completion, not a script error. Per-session budget is 15-20 follow/session (for 1 ca / 3 sessions schedule per row).
4. Treat a single `invalid` follower-surface classification during RecyclerView/header re-render as transient. Re-capture and reclassify within a bounded retry budget before emitting `MANUAL_REVIEW: rời khỏi màn follower list giữa chừng`; if the surface remains invalid due to being stranded on a Profile or sub-screen, invoke active Back recovery (`_recover_follower_list`, bounded to 2 attempts) to restore the follower list before escalating. In Path B verification (`_path_b_verify`), multi-attempt Back retries must be re-issued if the first Back does not immediately restore the follower list. Details in `references/follower-surface-transient-recovery.md` and `references/follower-list-profile-screen-recovery.md`.
5. Prove Feed before every seed search; swipe context only when configured and only through the bounded swipe helper. Search-screen detection (`_is_search_history_screen`) must strictly enforce TikTok package ownership (`is_tiktok_package`), requiring both a search submit identifier (`id/tv_search_textview`, `id/search_input`, `id/ho3`, etc.) and a search input/history marker ("Bạn có thể thích", "Tìm kiếm gần đây", `id/tvl_his`, `id/tvl_view_more`, header EditText) without bottom nav. If fullscreen Search is proven, use the top-left Back button (`x < 250, y < 250`, supporting `id/bow`, `id/bqp`, `id/bq8`, `id/bq7`, `id/bq9`, `id/bqc`, `id/bqe`, `id/bqq`, `id/back_btn`, `id/back`, `id/btn_back`, `id/iv_back`, `id/left_icon`, `id/action_bar_left_action` or `content_desc in {"Quay lại", "Back"}`) with TikTok package verification before `press_back()`. On Profile root, allow up to 2 semantic Home taps. If `_back_to_feed` fails before seed search, invoke the recovery ladder (`engine.recover_ui() and _back_to_feed(engine)`) before raising `MANUAL_REVIEW`.
6. Search the anchor, verify the profile header identity, and open the correct Following/Follower relation surface.
7. Bind each follower row by exact handle and same-row relationship button. Do not pair a button from a neighboring row.
8. Use Path B sampling as configured: open the followed profile, verify header identity and relationship state, then return to the list with a fresh UI proof.
9. Apply video-count/session-budget gates and persist state only after a verified outcome.

### Zero-Following anchors

Treat an explicitly verified `0 Đang follow`, `0 Đã follow`, or `0 Following` header on either the Profile screen or the opened Relation screen as exhausted business input, not a UI incident. Do not tap the relation control, follow the anchor, or consume budget. Return to a proven Feed and continue with the next anchor. Escalate only if Feed cannot be re-proven after bounded recovery. Separate `0` from an unrelated statistic: a bare zero without a Following label is not sufficient proof.

For a live incident, do not stop at the first `open_ok=False` branch: the retry/fallback branch must preserve the same zero-following classification. After both the first attempt and any retry, re-probe the current screen and require exact target-header identity plus a header-scoped Following count before skipping. If the proof is absent, retain fail-closed `MANUAL_REVIEW`; never infer zero Following from a suggested-account card, a bare `0`, or a generic `Follow` button.

When opening the Following tab on a 0-following anchor (e.g. Case UI-26 / Machine 21 `ngoc.phan39`), ensure `_open_following_tab` classifies the empty relation screen (`Đã follow 0`) during polling (requiring 2 consecutive positive checks to handle stale post-tap dumps) and sets `engine._last_anchor_follow_outcome = "zero_following"` to prevent the recovery ladder from re-searching the same anchor a second time. Details are in `references/zero-following-relation-screen-and-retry-prevention.md`.

- **Stat Counter `id/svu` & Zero-Following Header Detection (Case UI-40)**: On TikTok 46.x profile headers, stat count numbers render with `id/svu` while stat labels render with `id/svt`. `_STAT_COUNTER_IDS` and `_is_zero_following_profile` must include `id/svu` in stat counter suffixes so vertical column alignment recognizes `0 Đã follow` / `0 Following`, marking `_last_anchor_follow_outcome = "zero_following"` and skipping to Feed immediately to prevent follow-timeout recovery loops. Details in `references/zero-following-svu-stat-counter-and-timeout.md`.

#### Adversarial proof requirements

A known profile-stat resource ID is supporting evidence, not sufficient evidence by itself. A combined `0 Following` value is valid only when the node's semantic label is an exact Following variant and the node is in the verified profile-header stat region. When TikTok splits the number and label into separate nodes, require an unambiguous same-stat relationship: exact label, same visual stat cell/parent when available, tight alignment/adjacency, and no competing Followers/Friends/Likes zero counter that could satisfy the same geometry. If more than one plausible pairing remains, return `MANUAL_REVIEW` rather than skipping. Add negative fixtures for `0 Followers + nonzero Following`, a bare `0`, nearby counters, duplicated target handles in suggestions, and suggestion content inside the header cutoff. The review finding and fixture matrix are in `references/zero-following-review-adversarial-cases.md`.

Never treat a runtime marker, a passing offline test, or a source module path as proof that a particular physical machine executed the new code. These prove source/import provenance only; live behavior requires a fresh official-runner artifact. Keep `source verified`, `runtime loaded`, and `live behavior verified` as separate statuses.

### Runtime loading, pre-existing patches, and dirty-worktree checks

A pre-existing staged/unstaged patch is not a completed fix. When the operator says `fix`, continue from the current tree: resolve the exact live failure, map it to the owning source path, add or update the regression case, and verify the candidate. Do not report “đã fix” merely because a related patch exists, a build marker is present, or offline tests pass.

When a machine still emits the old `mở tab Đã follow fail ... (lần 2)` message after a source patch, verify the runtime boundary before changing selectors again:

### Shared-worktree and fresh-evidence concordance

A focused test result is final evidence only when the verifier subprocess and the
canonical direct command agree on the same current bytes. Dirty status alone is
not a blocker: unrelated staged/unstaged changes must be preserved and work may
continue inside the approved scope.

1. Re-read the changed region and snapshot staged/unstaged path sets plus hashes
   before the final verification window.
2. Use line-level overlap, not path-level dirtiness, to decide ownership. If a
   sibling/concurrent writer changed a different region of the same file, keep
   working and verify the exact hunks independently. Stop source edits only when
   the writer overlaps the region being changed or makes attribution impossible;
   then report `SCOPE_CONFLICT` and do not overwrite, reset, unstage, or reconstruct
   the patch from memory.
3. Run the temporary verifier and the direct canonical pytest command in one
   invocation. If either fails, or their results differ, invalidate both results
   as final evidence and report `CURRENT_TREE_DRIFT`/`SCOPE_CONFLICT` until a
   stable rerun agrees.
4. Keep the verifier under the OS temp directory with a `hermes-verify-` prefix,
   isolate `PYTHONPYCACHEPREFIX`, and delete only artifacts created by that run.

Do not turn an unrelated dirty file, trailing whitespace in another candidate,
old staged work, or a test change outside the edited hunk into a stop condition.
Never clean, revert, reset, or whole-file overwrite merely to make the worktree
look clean.

A green direct rerun cannot override a failing verifier from the same evidence
window. This is especially important for Path B identity regressions, where a
partially landed normalization helper can make valid profiles pass in one import
process and return `MANUAL_REVIEW` in another.

### Coordinate representation boundary

Profile identity helpers and consumer XML parsers may represent the same UI bounds differently. Before comparing an identity helper's `username_element.bounds` with a parsed-node bound, normalize both to one canonical representation. In particular, `automation_core` UI elements commonly expose `(left, top, right, bottom)`, while this consumer's `parse_nodes()` exposes `(x, y, width, height)`.

**Strict type and bounds validation contract:**
Helper normalization (such as `_bounds_rect`) must fail-closed (returning `None`) when receiving malformed inputs:
- Reject non-integer types strictly: `float` (e.g. `100.5`), `bool` (`True`/`False`), numeric strings, or objects with `__int__` coercion without explicit conversion.
- Require exactly 4 elements: non-negative coordinates (`left >= 0, top >= 0`), positive dimensions for size form (`width > 0, height > 0`), and strictly valid positive area for rect form (`right > left, bottom > top`). Inverted or degenerate boxes must return `None`.

**Center calculation pitfall:** When calculating the horizontal or vertical center of a node from `parse_nodes()` bounds `(x, y, w, h)`, center X is `x + w / 2.0` and center Y is `y + h / 2.0`. Never use `(x + right) / 2.0` or `left + right / 2.0` without unpacking, as `bounds[2]` is width, not the right coordinate. An incorrect formula shifts centers for differing-width nodes (e.g. a wide label vs narrow counter) and causes false misalignments or false column matches.

A direct equality check can reject a valid exact UID and surface as `MANUAL_REVIEW` even when the profile is correct. Use a named conversion/helper, then keep the existing exact header UID, uniqueness, and identity-element binding gates; never fix this by dropping the bounds/identity check. Add a regression fixture that passes with equivalent rectangles and fails closed for a wrong or duplicate header. See `references/path-b-bounds-normalization.md`.

1. Inspect both staged and unstaged diffs. A concurrent worker can leave the working tree with an older retry branch even when focused tests previously passed.
2. Verify the production invocation uses the canonical repo as `cwd` and imports the module with `python -m follow_runner.run_follow`; inspect `module.__file__`/`inspect.getsourcefile()` from the same interpreter.
3. Add or inspect a harmless result/details build marker (for example `mode2_zero_following_fix`) so the child process proves which source revision it loaded. A passing unit test alone does not prove the live machine loaded the patch.
4. Do not use stale screenshots or an old run timestamp to claim the new code was active. Separate `source verified`, `runtime loaded`, and `live behavior verified`.

The focused reproduction and runtime-loading checklist are in `references/zero-following-runtime-loading-and-retry.md`. The Search input variant and semantic Back regression are documented in `references/search-back-button-and-feed-return-rules.md`.

### Reporting style for this user

Use concise Vietnamese reporting in the order `Mục đích → Kết quả → Bằng chứng → Blocker`. Do not narrate progress or pad the answer with unrelated farm processes. State clearly whether the live result is confirmed, excluded, or unproven; do not call a unit-test pass a live canary.

### Empty relation surfaces and selector drift

TikTok 46.x may use `com.ss.android.ugc.trill:id/yx1` (or normalized `:id/yx1` / `id/yx1`) for the title on an empty relation surface. Add new IDs to the selector family, but accept the surface only with structural proof: exactly one relation ViewPager, the expected non-clickable empty-title Button, the empty-message node, and the correct selected relation header. A selector alone must never turn an arbitrary screen into `empty`.

### Suggested accounts and header identity

Suggested-account cards can add multiple `@` nodes across the full XML dump. Do NOT use global checks like `len(at_nodes) == 1` which falsely reject valid profiles. Scope identity validation strictly to the header region (`y < 650`), require that matching header `@`-nodes normalize exactly to the target UID (`_normalize_handle(node.text) == target_normalized`), and reject when no header handle matches or when handles below header mismatch.

### Dual structural identity gate and fail-closed navigation

- **Path B Follower List Restore & Over-Back Prevention (Case UI-41)**: In `_path_b_verify`, after verifying profile status, returning to the follower list must use screen-aware back navigation. Allow multiple UI dump polls (settling delay) for RecyclerView re-rendering before retrying back. Crucially, only issue a secondary `back()` or top-left back tap if the UI is still proven to be on the Profile screen (`_find_header_handle_node` / profile elements present). Never issue a blind secondary back if the UI has already left the profile (e.g. stranded on Search Results), preventing cascading double-backs and false `MANUAL_REVIEW: Path B fail`. Details in `references/path-b-restore-over-back-prevention.md`.
- **Path B Over-Back Guard with Polling & Profile-Verified Retry (Case UI-44)**: In `_path_b_verify`, after the initial `adapter.back()` from Profile, poll twice (1.5s then 1.0s) to allow RecyclerView render lag to resolve before concluding the follower list isn't restored. ONLY issue a retry back (tap top-left back button or `adapter.back()`) if the UI dump proves the screen is **still on the target Profile** (`_find_header_handle_node(restore_nodes, uid)[0] is not None` AND `not _is_search_history_screen(restore_nodes)`). If the screen has already exited the profile (e.g. Search Results, Feed, or popup), **never** issue a secondary back — fail-closed to `manual`. Extended `_find_top_left_back_button` and `_is_search_history_screen` with additional resource-id suffixes and content-desc/text variants for robust detection. Added regression tests: `test_path_b_verify_skips_retry_back_when_on_search_results_preventing_over_back` and `test_path_b_verify_delayed_follower_list_render_polls_twice_without_retry_back`. Plan-review APPROVED (9Router plan-review). Canary live on Machine 10 (anhtruong840) passed 600s+ with 93 followed, 0 failed. Details in `references/path-b-over-back-guard-polling-ui44.md`.
- **Keyboard Candidate Strip & Search Submit (Case UI-27, UI-29)**: When typing UID in Search, predictive candidate strips on Samsung Keypad (`com.sec.android.inputmethod:id/candidate_layout`) or Gboard display the typed UID text. Selectors in `_exact_search_result_from_xml`, `_unique_search_submit`, `_find_header_handle_node`, and `_is_profile_action_node` MUST explicitly filter out non-TikTok packages (`com.sec.android.inputmethod`, `com.google.android.inputmethod.latin`, `com.android.systemui`, `com.sec.android.app.launcher`, etc.) and require valid TikTok packages (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.zhiliaoapp.musically.go`, `com.ss.android.ugc.aweme`, `com.ss.android.ugc.aweme.lite`).
- **Package Inheritance & Resource-ID Inference Precedence in `parse_nodes`**: When XML nodes omit the `package` attribute, `parse_nodes()` must resolve package with strict precedence: (1) explicit `package` attribute on the element -> (2) inherited parent package -> (3) fallback to prefix in `resource-id` (`com.pkg:id/...`) ONLY when both (1) and (2) are empty. This prevents child elements under an IME/System UI parent from spoofing a TikTok package via a crafted `resource-id`.
- **Strict 5-Package Allowlist (Case UI-27 & Package Governance)**: Hệ thống chỉ chấp nhận ĐÚNG 5 package TikTok chính thức: `com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.zhiliaoapp.musically.go`, `com.ss.android.ugc.aweme`, `com.ss.android.ugc.aweme.lite`. Tuyệt đối không dùng prefix lỏng lẻo (`startswith`) hoặc allowlist mở rộng sang package hệ thống/bàn phím.
- **Fail-Closed KEYCODE_ENTER Fallback**: In `_nav_search`, fallback `adapter.keyevent(66)` is only permitted when UI dump proves an `EditText` belonging to a valid TikTok package has `focused=True` (accepting both Python bool `True` and string `"true"` from XML parsers) and normalized text matching target `@uid`. If `keyevent(66)` returns `False`, or if dump fails with an exception, or if focus/text cannot be proven, the runner MUST fail closed immediately (`return False`) without proceeding to `_wait_search_result` to prevent accepting stale/race UI results.
- **Identity Element Package Provenance in Path B**: Package extraction for `identity_element` must use `_extract_identity_package(element)` to strictly check the element's own attributes across 3 layers (`attrib["package"]` / `attrib["resource-id"]` / `attrib["resource_id"]`, `dict node`, and object attributes `package` / `resource_id`), handling `UIElement` with empty `attrib={}` but valid `resource_id`. It must never borrow package provenance from an unverified disjoint header node. Packageless identity elements must fail closed to `manual`.
- **Follow Concurrency Throttling & Soft Deadline Budgeting (Follow Timeout Farm Fix):**
  - **Cross-process Follow Concurrency Lease:** Follow hook in the parent feed runner (`multi_machine_feed_session.py`) MUST be throttled by `_FOLLOW_CONCURRENCY = BoundedSemaphore(20)` with OS file slot locks (`slot-0.lock`..`slot-19.lock`) under `~/.codex/follow-concurrency-locks`, preventing ADB server (port 5037) congestion from 40 simultaneous uiautomator dumps.
  - **Test Isolation State Directory:** `_run_follow_hook` must accept `follow_state_dir` from `ctx.config` (defaulting to `D:/Taadaa/tiktok-follow/runs/state`), preventing offline unit tests with `machine=1` from falsely reading live cooldown state files from disk.
  - **Soft Deadline Guard:** `FollowEngine.has_time_for_next_action(reserve_seconds=60.0)` must be checked at the top of follow loops in `run_mode1` (UID loop) and `run_mode2` (anchor loop, follower scroll while loop, and follower row loop) using duck-typed safety (`callable(getattr(engine, "has_time_for_next_action", None))`). If time remaining is < 60s, break gracefully and return clean `status="OK"` with all followed accounts saved, rather than risking dirty `follow-timeout` termination. Details in `references/follow-timeout-and-farm-concurrency.md`.
  - **Search Autocomplete Suggestion Filtering (Case UI-43)**: In `_exact_search_result_from_xml`, suggestions and dropdown nodes (`id/tvl_unified_sug`, `id/tvl_sug`, `id/tvl_his`, `id/tvl_recent_search`, `id/tv_search_sug_word`, `id/zsc`, `id/candidate_layout`, `id/bdu`, etc.) must be filtered out so that typing UID in Search triggers explicit submit tap or ENTER fallback rather than mistaking a suggestion node for an exact search result card.
  - **Root cause pattern**: Typing UID in Search triggers autocomplete dropdown with `tvl_unified_sug`/`tvl_sug`/`tvl_his` nodes containing the same UID text. Previously these were in `account_card_suffixes` or passed the `len(identities) == 1` branch, causing `_exact_search_result_from_xml` to return the suggestion node as "exact result". `_nav_search` then skipped submit (no "Tìm kiếm" button tap, no KEYCODE_ENTER) and tapped the suggestion (clickable=false, occluded by keyboard) → navigation failed → screen stayed on Search → identity verification read empty username → `hồ sơ identity mismatch: expected @uid got ` → Farm Alert.
  - **Fix**: Add `excluded_suffixes` tuple filtering in `identities` list comprehension; remove suggestion IDs from `account_card_suffixes`; enforce `_nav_search` always submits via `_unique_search_submit` or `KEYCODE_ENTER` before waiting for results.
  - **New regression tests**: `test_exact_search_result_rejects_autocomplete_suggestions_in_dropdown`, `test_nav_search_submits_search_when_autocomplete_dropdown_present` in `test_mode1_search_follow.py`.
  - **Docs**: Case UI-43 added to `docs/farm-automation-cases.md` and `docs/uiautomator.md`.
- **State Persistence Failure Preservation (Mode 1 & Mode 2)**: If `state.set_follow_failed()` raises an exception (e.g. disk/IO/db lock error), catch with `logger.exception(...)` and preserve `MANUAL_REVIEW` / `failed=True` (dirty technical failure) with `res.details["state_error"]`. The cleanup ladder (`_cleanup_follow_failed`) must close apps to Home and record `res.details["cleanup_errors"]`, but NEVER downgrade a dirty failure to clean `failed=False` / `FOLLOW_FAILED`.
- **Fail-Closed Parsing Error Handling**: Mọi hàm trích xuất selector/node từ XML uiautomator (`_exact_search_result_from_xml`, `_unique_search_submit`) phải bọc `except (ET.ParseError, Exception): return None` kèm `logger.exception`, đảm bảo bất kỳ lỗi layout/node tree bất thường nào cũng trả về `None` fail-closed thay vì crash unhandled exception qua khỏi recovery ladder.
- **Fail-Closed Safe Back in Mode 2 Path B**:
  1. Chỉ được phép bỏ qua `adapter.back()` khi và chỉ khi đã **chứng minh độc lập qua UI dump thực tế** rằng màn hình **chưa từng rời khỏi follower list** trong suốt quá trình kiểm tra (`left_follower_list=False, dump_ok=False`) VÀ **không có bất kỳ dump exception/timeout nào** (`not had_dump_exception`).
  2. Nếu có bất kỳ lần dump nào rời khỏi follower list, hoặc dump bị exception/timeout, hoặc rơi vào màn hình không xác định (`unproven profile`/popup/feed), `adapter.back()` BẮT BUỘC phải được thực thi an toàn để thoát màn hình con, tránh để app mắc kẹt làm nhiễm state cho các UID tiếp theo.
- **TOCTOU Back Safety in Mode 2 Path B**: Không bấm Back tùy tiện khi màn hình hiện tại chưa từng rời khỏi follower list.
- **Dual Structural Identity Gate**: Bắt buộc đồng thời: (1) `handle_node is not None` & `status == "ok"` (`y < 650`), (2) `identity_element is not None` từ `profile_identity_from_xml`, (3) `is_tiktok_package(identity_pkg)` hợp lệ, và (4) `_normalize_handle(profile_handle) == target_normalized`. Không cho phép phân loại hành động nếu thiếu bất kỳ điều kiện nào.
- **Unicode Bidi / Isolate Character Stripping (Case UI-34 & Path B Handle Regex)**: TikTok injects invisible Unicode formatting/bidi control characters (`\u200e`, `\u200f`, `\u2066`..`\u2069`, `\u202a`..`\u202e`, `\ufeff`, `\u061c`, `\u2060`) into handle text and XML dumps. Raw regex matches like `r"^@[a-zA-Z0-9_.]+$"` in `_find_header_handle_node` or `_extract_row_handle` will fail if evaluated on raw strings. All handle extraction, header regex verification, and XML profile identity extractions MUST sanitize these characters (`_clean_handle_text` / `_clean_xml_format_chars`) before evaluation or parsing. Details in `references/profile-identity-unicode-normalization.md`.
- **Git Workspace Operational Discipline**: CẤM tự ý chạy `git reset --hard` hoặc thao tác destructive git trên live workspace/farm repos. Khi phát hiện nhánh diverged hoặc conflict rebase, luôn kiểm tra diff, giữ an toàn mã nguồn và xin ý kiến user trước khi thực hiện các lệnh tác động lịch sử git.
- **Self-Account Exclusion in Follower List (Case UI-32, UI-40)**: When traversing an anchor's follower/following list in Mode 2, the currently active account on the device (`active_account`, resolved via fallback chain `getattr(engine, "account_id", "") or getattr(engine, "active_account", "") or getattr(engine, "active_account_handle", "") or getattr(cfg, "account_id", "")`) may appear in the list. TikTok never shows a relationship action button for the logged-in user (`r["follow_button"] is None`, rendering a chevron `>` or non-interactive row instead). `FollowEngine` must maintain `self.active_account_handle` along with `self.active_account` and `self.account_id` aliases, and `mode2_follow_followers.py` must exclude rows matching `active_account` from both `missing_button_rows` and `pending` rows to prevent false alarms for `MANUAL_REVIEW: follower row không có nút follow semantic`. Details in `references/self-account-exclusion-and-engine-handle-fallback.md`.
- **Bottom-Cutoff Follower Row Exclusion (Case UI-39 & missing_button_rows)**: Follower rows partially clipped at the bottom screen edge (`cluster_y[1] >= bottom_cutoff_y` where `bottom_cutoff_y = max_screen_y - 180`) often have their follow button node outside the rendered XML. `missing_button_rows` must ignore rows at or below the bottom cutoff (`cluster_y[1] < bottom_cutoff_y and cluster_y[0] < bottom_cutoff_y - 70`), allowing the runner to follow visible rows and scroll down to fully render the clipped row on the next dump. Details in `references/bottom-cutoff-follower-row-and-missing-button.md`.
- **Search Not Found vs Navigation Failure (Case UI-33)**: When a target UID or anchor does not exist on TikTok or search results omit the exact account, `_wait_search_result` returns `None`. Use `_is_search_screen_or_results(xml_text)` to distinguish a completed search showing results/tabs (`not_found`) from a real navigation crash (`nav_error`). On `not_found`, restore Feed via `_back_to_feed(engine)` and non-fatally skip to the next UID/anchor without triggering ladder `MANUAL_REVIEW`.
- **Search History & Back Navigation (Case UI-31)**: Fullscreen Search history detection (`_is_search_history_screen`) must verify top search input/back belonging to TikTok (`y < 350`), search context/history markers, and absence of bottom navigation bar. Top-left back tap supports expanded resource-ids (`id/ho3`, `id/bqq`, `id/bqp`, `id/bq8`, `id/back_btn`, `id/iv_back`, `id/left_icon`). In Mode 2, allow 2 Home taps on Profile root and trigger `engine.recover_ui() and _back_to_feed(engine)` recovery ladder before seed search before escalating to `MANUAL_REVIEW`.
- **State Persistence Failure Preservation**: If `state.set_follow_failed()` raises an exception (e.g. disk/IO error), preserve `MANUAL_REVIEW` / `failed=True` (dirty technical failure). The cleanup ladder (`_cleanup_follow_failed`) must close apps to Home but NEVER downgrade a dirty failure to clean `failed=False` / `FOLLOW_FAILED`.
- **Fail-Closed Navigation**: In `_back_to_feed` and recovery helpers, any exception during `tap_center` (e.g. Home tap or Search history Back icon tap) must fail closed immediately (`return False`) and NEVER fall through to `adapter.press_back()`. Blind fallback inputs after an unconfirmed tap attempt risk double navigation or accidental app exit.
- **Zero Silent Failures in Recovery**: Recovery ladders and exception blocks must use `logger.exception(...)` including anchor UID context and propagate error details into `res.reason`.

## Result and cleanup semantics

- `FOLLOW_FAILED` means Path B proved TikTok released the relationship (shadow drop / rate-limit). Stop the current session immediately, persist the per-account/per-day cooldown, close TikTok through the canonical cleanup method (`close_all_recent_apps`), and expose `follow_failed=true` in the result payload.
- **Progressive Backoff Cooldown (Case UI-37)**: When an account hits `FOLLOW_FAILED`, `FollowState.set_follow_failed()` enforces progressive backoff using exact UTC ISO timestamps (`cooldown_until_at`): Streak 1 (+48h to probe early recovery), Streak 2 (+96h / 4 days to skip 1 shift), Streak >= 3 (+168h / 7 days full rest). Duplicate callbacks during active cooldown are idempotent; success resets only clear failure state when causally newer than `last_failed_at`; malformed/naive timestamps fail closed; hard-block `follow_blocked` is preserved across expiration. Details in `references/progressive-backoff-cooldown-and-utc-timestamp-enforcement.md`.
- In hybrid mode (`both`), if Mode 2 triggers `follow_failed`, runner MUST short-circuit and run cleanup immediately before attempting Mode 1, preventing unwanted follow attempts after rate-limit or shadow drop.
- Cleanup ladder independence: `_cleanup_follow_failed` must try each fallback independently (`close_all_recent_apps` -> `close_all_apps` -> `home` -> `press_home`). If `home()` fails or returns `False`, it MUST still fallback to `press_home()` before declaring `CLEANUP_FAILED`.
- For this runner, a clean `FOLLOW_FAILED` is a handled business outcome: require `status == "FOLLOW_FAILED"` plus incoming clean state (`failed is False` or `type(failed) is int and failed == 0`), successful cleanup, subprocess exit code `0`, `failed=False`, and `follow_failed=True`. In this clean case, do not send a Telegram `DỪNG PHIÊN`/`GIỮ HIỆN TRƯỜNG` alert or retain an incident lock.
- Contract consistency: A result with `status == "OK"` and `follow_failed is True` is an invalid state; `cleanup_after_result` must convert it to `status="CONTRACT_ERROR"`, mark `failed=True`, attach an explanatory reason, and skip app cleanup.
- Fail-closed alert suppression contract: In the parent feed session (`multi_machine_feed_session.py`), Telegram alert suppression is strictly gated on `is_clean_follow_failed` (`status == "FOLLOW_FAILED" and proc.returncode == 0 and follow_failed is True and (failed is False or failed == 0)`), and requires valid canonical payload with exact `machine` matching (`type(machine) is int and type(machine) is not bool and machine == account.machine`).
- A `follow_failed=true` flag alone is never enough to suppress an alert. `CLEANUP_FAILED`, missing/failed cleanup, subprocess failure, nonzero exit code, `failed=True/1`, `MANUAL_REVIEW`, `TIMEOUT`, launch error, and malformed results remain nonzero/fail-closed and MUST trigger the red `GIỮ HIỆN TRƯỜNG` farm alert and retain incident lock.
- Attempt cleanup only for strictly clean `OK` and `FOLLOW_FAILED` (`failed is False` or `type(failed) is int and failed == 0`). If the result is already dirty (`failed=True`), skip cleanup to preserve the live UI for operator inspection (TTL 90m).
- If the real adapter cleanup call raises or returns `False`, promote to `CLEANUP_FAILED`, mark `failed=True`, preserve the underlying `follow_failed` marker (both on the result object and `_result_payload` for forensic evidence), and return `exit 1`. The parent runner will trigger an alert because `status == "CLEANUP_FAILED"` and `failed=1`.
- Timeout scene preservation: On `subprocess.TimeoutExpired` during follow-hook, do NOT force-stop TikTok or send Home keyguard; kill only the hung python process and retain the device UI scene for the Farm Alert.
- Mode 2 Identity Re-validation: In `mode2_follow_followers.py`, identity validation on header `@uid` (`y < 650`, checking both `text` and `content_desc`) must enforce exact match and uniqueness (`len(at_nodes) == 1`). If `_ensure_anchor_followed` reloads XML, runner MUST re-validate the profile identity before proceeding to tap Following. All recovery ladders and `_back_to_feed` calls must be exception-wrapped to fail-closed into `MANUAL_REVIEW`.

### Session-close scope and review discipline

- When the operator says `chốt phiên`, reconstruct the current deliverable before reading old handoffs or broad dirty status. Stage only the exact follow/parent-hook/docs/tests candidate; preserve unrelated historical or concurrent dirty files untouched.
- Review and test the exact candidate bytes/tree that will be committed. A reviewer that cannot inspect the supplied candidate is not an approval; do not commit, rebase, or push until a fresh parseable verdict is obtained. Keep the final report short: purpose, result, blocker, remote.
- For a dirty worktree with unrelated staged/unstaged changes, prefer a clean temporary clone from the current remote base. Apply only the allowlisted patch there, run the focused tests, and review the complete `origin/master..candidate-commit` delta—not merely a staged working-tree diff. If a fixture or test hunk changes after review, rerun tests and request a fresh review; prior approval is stale.
- A plan-review prompt containing only tree hashes or a large mixed diff is insufficient. Paste the exact relevant production delta plus the unchanged baseline context that proves pre-existing state persistence/detection, and include the exact test counts and tree/commit IDs. Treat a reviewer rejection that demonstrably ignores pasted/baseline context as a failed review attempt, not as permission to push; retry with a compact, context-first request.
- Keep test doubles faithful to the production contract: if production cleanup is fail-closed when `close_all_recent_apps` is missing, every successful-path adapter double must implement that method, while `FollowState` doubles must remain state doubles. Never mass-replace `object()` fixtures across unrelated constructor types.

The exact clean-clone, candidate-commit, baseline-context review recipe is in `references/session-close-exact-candidate-review.md`.

## Development and verification workflow

1. Read repository instructions, relevant case documentation, the current source, and the complete staged plus unstaged diff before editing.
2. Confirm the live XML/screenshot evidence and identify the smallest selector/state boundary responsible for the failure.
3. Add a deterministic fixture reproducing the exact layout or state transition. For runtime import boundaries, monkeypatch the symbol where production code resolves it; for example, patch `automation_core.persistent_ui.capture_atx_session_ui` if the adapter imports it there.
4. Patch the source narrowly. Avoid broad text matches, global substring checks, and hardcoded machine-specific IDs without a structural/identity gate.
5. Run focused tests for the changed flow, then the complete `follow_runner/tests/` suite. A timeout or truncated log is not a pass; diagnose fixture queues, deadlines, or retries before rerunning.
6. Run syntax checks (`py_compile` or the project equivalent) and `git diff --check`.
7. For live validation: dry-run first, inspect device/serial and lock owner, capture fresh UI/XML evidence, then run only the approved canary. If an official farm process owns the device, do not delete lock files or kill the owner. When the user explicitly authorizes preemption, use the shared `automation_core.device_lock` operator-preempt/takeover API with a documented reason and exact machine+serial scope; create the canary lease before any runner action, verify both machine and serial aliases point to the canary lease, and release only that lease after terminal cleanup. If preemption cannot be proven atomically, remain `BLOCKED`.
- A live canary must execute the official repo runner (`D:\\\\Taadaa\\\\tiktok-follow\\\\follow_runner\\\\run_follow.py`), not a one-off tap/ADB workaround and NEVER the parent feed runner (`run_tiktok.py` / `multi-machine-feed-session`). When an incident is triggered in `tiktok-follow`, re-running feed session is invalid; always run `python follow_runner/run_follow.py --machine <M> --mode <1|2> --config <config.yaml> --account-row-index <slot>` for the exact machine and slot.
   - **Kiểm tra lock trước khi từ chối canary (BẮT BUỘC):** Trước khi kết luận "BLOCKED do lock", kiểm tra PID trong lock file còn sống thật bằng `psutil.Process(pid).is_running()`. Alert `GIỮ HIỆN TRƯỜNG` đồng nghĩa tiến trình farm đã dừng → lock thường là stale. Chỉ báo BLOCKED khi PID còn sống thật. Xem chi tiết: `references/live-unlock-rerun-and-concise-report.md § Stale lock detection`.
   - **Force Preempt for Canary (KHI CẦN OVERRIDE LOCK "blocked"):** Nếu operator yêu cầu chạy canary ngay dù lock status="blocked" (PID chết, TTL chưa hết), dùng `acquire_device_lock(..., force_preempt=True)` để ghi đè lock cũ. Lock mới sẽ có status="running". Sau canary pass, operator gõ "Mở khóa máy N" để clear lock cho cron batch tiếp theo.
   - **Cooldown State Reset for Live Canary:** If the target account previously hit `FOLLOW_FAILED` today, `runs/state/follow_state_<M>_row_<slot>.json` holds `follow_failed: true` and `follow_failed_date: today`. Running `run_follow.py` directly will short-circuit at startup without touching the device. For an explicit live canary test on the physical device, inspect and reset `follow_failed: false` in the state JSON prior to the run so the runner actually exercises the live follow path.
   - **Execute Immediately:** When instructed to run a canary, execute the runner command immediately in the same turn—do not stop at presenting the command string or plan. Keep it bounded to the named machine/account row; do not expand to another machine or batch. Report the actual terminal status and exit code; unit-test success is not live proof.
9. If a canary reaches `MANUAL_REVIEW`, preserve fresh failure evidence and stop. Do not patch or rerun from the live scene unless the user explicitly authorizes the next fix/retry. Always verify the canary lock aliases are gone after termination.
10. Report purpose → result → blocker, with real command output and exact pass counts. Do not claim a live canary when it was blocked.

For the exact operator-preempt sequence and post-run alias verification, use `references/live-unlock-rerun-and-concise-report.md`.

## Incident triage and evidence boundaries

### Telegram incident screenshot is not the attempt artifact

A Telegram alert screenshot can identify the reported machine/account and failure signature, but it is not proof that the attached TikTok UI is the exact attempt artifact. Treat it as incident metadata until the corresponding run ID, timestamp, `log.jsonl`, `ui.xml`, and matching screenshot are resolved. If those artifacts are absent, report the live root cause as `UNPROVEN`; do not infer the exact XML state from the Telegram rendering or claim the live machine is fixed from offline tests.

### Dirty-tree and test-result boundary

Before relying on a regression result, inspect staged and unstaged diffs separately. A focused test pass proves only the selected tests; a full relevant suite must still be run and any failure must remain visible in the final verdict. A test command that deselects everything (`pytest` exit 5 / `no tests ran`) is not a pass. A full-suite failure caused by an outdated event-order expectation is still a verification blocker until the test or implementation contract is reconciled. Do not report “fixed” or “full suite pass” while that blocker remains.

- A screenshot is an incident signal, not a complete reproduction. Before editing or running a canary, resolve the exact repository, machine/serial, run ID, timestamp, artifact root, and failure signature. If the screenshot does not identify the target, classify live causality as `UNPROVEN`; never assign a machine from historical configs, nearby artifacts, or repository naming.
- Read the exact attempt's log window and open the matching `ui.xml` and screenshot before concluding that the failure is a Following-tab, selector, upload, or account problem. A stale `MANUAL_REVIEW` log from account-ready, an audit prompt, or another run is not evidence for the current screenshot.
- Separate follow-runner failures from upload/feed-hook failures. `upload_subprocess_nonzero` is only a wrapper status until the child command, stderr/exit status, and owning repository are proven. Do not patch `tiktok-follow` for an upload error without proving that this runner owns the failing subprocess.
- When the repository is dirty, inspect staged and unstaged diffs separately before writing. Preserve pre-existing staged work; never reset, clean, whole-file stage, or overwrite a file with overlapping unstaged edits. If ownership of the same region cannot be separated, stop with `SCOPE_CONFLICT` and perform evidence-only verification at most.
- Use the repository's canonical test path. A command returning `no tests ran` / exit 5 is not a full-suite pass. Report focused regression, actual repository suite, syntax compilation, and `git diff --check` as separate evidence.
- Unit tests and offline fixtures prove code behavior, not machine recovery. A live canary is `SUCCESS` only after the official runner completes the approved target end-to-end with fresh post-action evidence. Missing target resolution or matching live artifacts means `BLOCKED`/`NOT RUN`, not live verification.

## Reporting style for incident fixes

Use a concise Vietnamese report in this order:

- `Mục đích`
- `Kết quả`
- `Bằng chứng` — exact command, pass count, artifact path, and target identity when proven
- `Confirmed / Excluded / Unproven`
- `Blocker`

Do not pad the report with unrelated processes, old runs, or speculative causes. State plainly when the current evidence proves only an offline code fix and not a live fix.

## Evidence checklist

- Root cause tied to a concrete XML node/resource-id/state transition.
- Source files and tests changed are listed.
- Focused test result and full-suite result are both fresh.
- Syntax and whitespace checks pass.
- Live device result is explicitly `SUCCESS`, `BLOCKED`, or `NOT RUN`; never infer it from unit tests.

## References

- `references/device-lock-blocked-state-and-canary-discipline.md` — Device Lock "blocked" state semantics, TTL retention, stale lock detection, and canary preemption protocol.
- `references/lock-force-preempt-canary-protocol.md` — Force preempt protocol for live canary when lock status="blocked" but PID is dead (stale lock).
- `references/self-account-handle-alias-sync-and-case40.md` — Case UI-40: Self-Account Exclusion Fallback Chain & FollowEngine Alias Synchronization (`active_account_handle` vs `active_account`/`account_id`).
- `references/follower-list-profile-recovery-and-bottom-cutoff.md` — Cases UI-38, UI-39, UI-40: Follower list active recovery from profile screen (_recover_follower_list), bottom cutoff row clipping tolerance (_missing_button_rows margin), and FollowEngine account alias synchronization.
- `references/zero-following-stat-counter-ids-and-case-ui40.md` — Case UI-40: Zero-following detection with TikTok 46.x stat counter resource-ids (`id/svu` & `id/svt`), split counter/label column alignment, and skip-to-feed rules.
- `references/progressive-backoff-cooldown-and-utc-timestamp-enforcement.md` — Case UI-37: Progressive Backoff Cooldown (48h / 96h / 7 ngày), UTC offset-aware timestamp gating, idempotent failure callbacks, causal success resets, and legacy state migration.
- `references/follow-drop-recovery-patterns-and-48h-cooldown-rules.md` — Phân tích bản chất 2 nhóm nhả follow (transient threshold vs persistent shadowban), thống kê tỷ lệ hồi phục 25%–50% sau 48h cooldown và chiến lược backoff.
- `references/follow-drop-diagnostics-and-historical-cycle-audit.md` — Chẩn đoán chi tiết lỗi nhả follow (số lượng follow trước khi dừng, anchor UID), quy tắc đối soát lịch sử chu kỳ ngày Chẵn/Lẻ (Row 2 vs Row 1) và cơ chế báo cáo của Feed Session Watchdog.
- `references/follow-shift-budget-and-avatar-video-lifecycle-20260901.md` — 1 Ca = 3 Phiên follow budget (15–20/phiên, max 60/ngày) & quy trình video #1 auto-avatar vs video #2+ skip avatar.
- `references/shift-structure-session-budget-and-avatar-failure-handling.md` — Farm shift structure (1 Ca = 3 Phiên), follow session budget math, and avatar upload failure recovery mechanics in `Tiktok-video`.
- `references/search-not-found-and-skip-semantics.md` — Case UI-33: Search Not Found vs Navigation Failure differentiation, non-fatal skip semantics for Mode 1 & Mode 2, and clean feed restoration.
- `references/search-history-back-recovery-and-home-tab.md` — Case UI-31: Search history layout detection, Back icon selectors, in-app Home tab retry, and Feed recovery ladder before seed search in Mode 2.
- `references/search-history-variants-and-mode2-recovery-ladder.md` — Case UI-31: Search history screen detection with modern input IDs (id/ho3), expanded search Back suffixes (id/bqq, id/bqp, id/bq8), Profile root 2-tap Home retry, and Mode 2 pre-search recovery ladder.
- `references/follow-timeout-and-farm-concurrency.md` — Follow hook 1200s timeout synchronization, 40-worker feed/follow concurrency vs 20-worker upload semaphore throttling, and ADB/USB bus bottleneck rules.
- `references/follow-concurrency-throttling-and-soft-deadline-budgeting.md` — Follow hook 20-worker concurrency throttling (_FollowConcurrencyLease cross-process slots) and FollowEngine soft deadline budgeting (has_time_for_next_action graceful 60s completion).
- `references/follow-concurrency-throttling-and-soft-deadline.md` — Session-specific details on ADB saturation vs feed swipe, uiautomator dump storms, and soft deadline budgeting.
- `references/enter-fallback-provenance-and-cleanup-contracts.md` — Mode 1 KEYCODE_ENTER focused checks, Path B identity element package provenance order, strict cleanup return value verification, and state persistence error handling.
- `references/follow-hook-timeout-and-subsequent-batch-triage.md` — Triage recipe for follow-hook subprocess timeout, subsequent batch outcome verification, and device state recovery.
- `references/safe-back-strict-package-and-clean-follow-failed.md` — Case UI-28: Clean FOLLOW_FAILED exit contract, fail-closed Safe Back in Mode 2 Path B with sticky exception tracking, and strict 4-package allowlist governance.
- `references/mode1-search-avatar-bounds-adjustment.md` — Mode 1 Search Result Avatar Bounds Adjustment `(x, y, min(w, h), h)` for wide horizontal account cards (`w > h * 1.5`) without clickable ImageView descendants.
- `references/search-card-avatar-bounds-and-follow-timeout.md` — Case UI-38: Search card avatar touch target bounds calculation `(x, y, min(w, h), h)` for TikTok 46.x card layouts without ImageView nodes, preventing inert center whitespace taps and follow timeout cascade loops.
- `references/search-history-back-recovery-and-home-tab.md`
- `references/search-submit-enter-fallback-and-ime-occlusion.md` — Case UI-29: Search submit fallback to KEYCODE_ENTER (keyevent 66) and widget class/package handling when soft keyboard is open.
- `references/header-ambiguity-and-defensive-bounds.md` — Defensive bounds component-wise validation (NaN/inf/overflow/dict), distinct header handles vs duplicate representations, safe string list payload extraction with exact type guards and contract error escalation, zero-following consecutive dump verification, and traceback observability.
- `references/dual-identity-gate-and-fail-closed-navigation.md` — Dual structural profile identity validation vs bio/promotional imposters, fail-closed navigation on tap exceptions, and Case 49 contract error handling.
- `references/header-handle-isolation-and-case49-cleanup.md` — Header handle isolation scoping (`y < 650`) vs suggested accounts, modern empty surface title selector `id/yx1`, and Case 49 cleanup failure promotion contract.
- `references/stat-column-isolation-and-content-desc-handle.md` — Stat column center alignment isolation for zero-following detection, `content_desc` header handle extraction, and compact relation header count formats.
- `references/follow-incident-routing-and-canary.md` — Hard routing from `Script: tiktok-follow` alert to canonical follow runner and slot state.
- `references/path-b-restore-over-back-prevention.md` — Case UI-41: Path B follower list restore screen-aware back navigation, settling delay polling, and over-back double-navigation prevention.
- `references/path-b-bounds-normalization.md` — Bounds representation normalization between automation-core and consumer parse_nodes.
- `references/zero-following-and-clean-follow-failed.md` — zero-following and follow-failure regression details.
- `references/session-ui-and-verification.md` — UI selector drift, Users-tab fallback, header identity, cleanup, and verification recipes.
- `references/search-history-keyboard-and-feed-recovery.md` — Search history layout detection, soft keyboard dismissal, top-left back button variants, feed recovery ladder, and test speed optimization.
- `references/search-uid-not-found-exact-reason-reporting.md` — Search UID not found exact reason reporting.
- `references/self-account-exclusion-and-engine-handle-fallback.md` — Case UI-32: Self-Account exclusion in follower list, active_account fallback resolution chain, and FollowEngine alias synchronization.
- `references/session-close-exact-candidate-review.md` — Session-close clean clone review workflow.
- `references/1-shift-per-day-budget-and-video-gate-audit.md` — Vận hành follow khi 1 row chỉ chạy 1 ca/ngày, đối soát từng nick hồi phục sau 48h và cơ chế ép avatar video #1.
- `references/closeout-waiver-and-suggested-recycler.md` — explicit canary-waiver handling, unrelated-dirty preservation, and Path B suggested-RecyclerView regression evidence.
- `references/search-autocomplete-suggestion-filtering.md` — Case UI-43: Search autocomplete suggestion filtering & mandatory submit before profile open.
- `references/wifi-disconnect-keyguard-and-alert-claims-dedup.md` — Wi-Fi disconnect preflight block (`blocked-vichanger-vpn`), 600s screen timeout keyguard lockout, and 1-alert-per-session claim de-duplication mechanics.
- `references/wifi-disconnect-keyguard-blocked-vichanger-vpn.md` — Pattern: WiFi mất kết nối → blocked-vichanger-vpn → Keyguard lock. Root cause chain, xác nhận nhanh qua ADB, fix bằng `svc wifi enable`, phân biệt stale lock vs lock còn sống.

## Triage: Máy Không Chạy / Màn Hình Bị Khóa

### Pattern 1: blocked-vichanger-vpn → Keyguard
Khi máy bị khóa màn hình, không thấy chạy, và lock tồn tại `status: blocked`:
1. `python D:/Taadaa/tools/inspect_machine.py <N>` → kiểm tra `Keyguard showing=true`.
2. Đọc `machine_<N>.lock.json`: `status: blocked`, `owner_active: false`.
3. Đọc `machines/machine_<N>/<run>/summary.txt` trong artifact → `final_status: blocked-vichanger-vpn`.
4. Xác nhận WiFi: `adb -s <serial> shell "dumpsys wifi | grep mWifiInfo | head -2"` → `DISCONNECTED`.
5. Fix: `adb -s <serial> shell svc wifi enable` → chờ 10-15s.

Xem chi tiết: `references/wifi-disconnect-keyguard-blocked-vichanger-vpn.md`

### Pattern 2: Lock Stale vs Lock Đang Sống
```python
import psutil
try:
    p = psutil.Process(<pid_from_lock>)
    print(p.name(), p.cmdline())  # còn sống → BLOCKED thật
except psutil.NoSuchProcess:
    print("PID dead — lock stale")  # lock có thể clear
```

### Artifact Root cho Run Hiện Tại (Hermes Cron)
Run artifact không nằm trong `.ai-runs/` mặc định mà theo path từ `--artifact-root`:
`D:/Taadaa/runtime/kibe/live/<date>/row-<N>-<time>/<run_id>/machines/machine_<N>/`
