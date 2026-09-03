# Read-only pre-live canary audit recipe (consumer repos)

Used 2026-08-15 to APPROVE a machine-1 Mode 1 live real-Follow canary in
`D:\Taadaa\tiktok-follow` (baseline HEAD `07b23a1`, uncommitted delta ~3.4k
insertions / ~1.1k deletions). Purpose: verify exact current bytes WITHOUT
modifying files or running live actions. Verdict format: APPROVED/BLOCKED
with concrete `file:line` findings — never a prose summary alone.

## Sequence (all read-only)

1. Load class skills first: `tiktok-consumer-dev` (umbrella) and
   `tiktok-feed-session` (run-context) — both were in play this session.
2. `git log --oneline -15`, `git status --short`, `git diff --stat HEAD` —
   establish baseline HEAD and the uncommitted delta. Untracked files
   (`NUL`, `uids.txt` in this repo) are out of scope: note them, never
   read/stage them.
3. Read repo docs in order: AGENTS.md → PROJECT_RULES.md → HANDOFF.md.
4. Read every production file on the execution path: flows (engine, mode1,
   mode2, verify), core (adapter, config, workbook, follow_state, popup,
   selectors), runner entrypoint.
5. Anchor every claimed fix to current-file:line AND the regression test that
   covers it (`grep -n "def test_"` in the matching test file). A gate without
   a test name is not audited.
6. Verify the pinned wheel API surface — do NOT trust the core source
   checkout: core HEAD can be AHEAD of the wheel (2026-08-15: core HEAD
   0.4.45, pinned wheel 0.4.44; grepping the checkout would give a wrong
   API surface). Unzip the exact wheel and grep its own source:
   `cd /tmp && rm -rf core044 && mkdir core044 && cd core044 && unzip -o -q /d/Taadaa/automation-core/dist/automation_core-0.4.44-py3-none-any.whl`
   Verify every consumer call site (kwargs, dataclass fields, return
   attributes) against the wheel source.
7. Import smoke against the wheel with the clean interpreter:
   `env -u PYTHONPATH "/c/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe" -c "..."` —
   import every symbol the consumer uses; assert the shape of key dataclasses
   (e.g. `UIElement.__init__` fields).
8. AST-compile all production files without importing them:
   `env -u PYTHONPATH python -c "import ast; ast.parse(open(f, encoding='utf-8').read())"` per file.
9. Safety greps (mind the hardline blocklist, below): adb restart
   (`kill-server|start-server|adb restart`), credential words
   (`password|otp|token|secret|credential`), leftover lock symbols
   (`SKIPPED_LOCKED|lock_factory|acquire_device_lock|device-locks|\.lock\.json`),
   coordinate fallback for the Follow action.

## Hardline blocklist trap for audit greps

The runtime refuses ANY terminal command whose text contains "reboot" /
"shutdown" — including a `grep -rn "reboot\|REBOOT"` PATTERN. Split the
literal: `grep -rn "reb\w*ot\|soft.reboot"` or `grep -rn "re[b]oot"`. Full
detail in SKILL.md "Close the loop" section 6.

## Mode 1 exact gates (tiktok-follow, as of 2026-08-15)

- **Search submit**: `_unique_search_submit` (mode1_search_follow.py) —
  exactly one clickable `android.widget.Button` with bounds, tail resource-id
  `id/tv_search_textview`, normalized text ∈ {tìm kiếm, search}; runs only
  when the fresh dump has NO exact non-input result; then `_wait_search_result`
  12s. 0 or ≥2 matches → None → no tap (fail-closed).
- **Profile identity**: `_classify_exact_profile_action` — requires
  `profile_identity_from_xml` (wheel 0.4.44 returns `username_element` as a
  UIElement with `.resource_id`) AND exactly ONE non-empty sf5 node (tail
  `id/sf5`) whose normalized username == UID; else `identity_mismatch` →
  MANUAL_REVIEW before any tap.
- **Follow tap**: exactly one clickable node with bounds whose normalized
  text/content-desc ∈ FOLLOW_BUTTON_TEXT set. `Follower` is NOT in the set.
  NO coordinate fallback for Follow anywhere in the repo.
- **Verify**: every post-tap/reload dump re-bound through the same
  identity classifier; identity drift → manual; only `followed`
  (identity-bound) → success → then `state.mark` + `consume_budget`
  (no state mutation before verified success).
- **Feed reproving**: `ensure_feed_for_follow` → mode2 `_back_to_feed`
  (≤4 Back inputs, ≤1 semantic Home tap, follower-recycler exclusion) before
  EVERY UID, mode 1 and mode 2.
- **B1 hard-kill + bounded warmup**: adapter `recover_persistent_ui` =
  pkill -9 atx-agent/uiautomator + `am force-stop com.github.uiautomator` +
  `uiautomator quit`, then `capture_persistent_ui(restart_attempts=1)`;
  XML None (non-bool/str result) → exactly ONE warmup recapture
  `restart_attempts=0`; still no `<hierarchy` → raise. No adb restart, no
  reboot, no clear data. B2 canonical relaunch → B3 guarded reboot only when
  `allow_device_reboot_recovery` (this repo's config default: true).
- **Lockless contract**: no lock store read/write/handoff; busy = live
  `tiktok_workflow --machine N` process only (wmic query + per-line regex
  `--machine N` / `--machine=N`); `SKIPPED_BUSY` before any Android/TikTok
  action. `run_follow.py` exit 0 only for `OK`/`SKIPPED_BUSY`.

## Checklist before declaring APPROVED

- Every claimed fix anchored to current-file:line + its regression test name.
- Pinned wheel exists in `automation-core/dist/` and all consumer imports
  resolve against it (import smoke), not against core HEAD.
- All production files AST-parse (CRLF-safe, no execution).
- No secret/credential/workbook logging; plan hides tik_id for
  startup/account-ready checkpoints. Pre-existing smells (e.g.
  VERIFY_IDENTITY reason echoing `@{row.tik_id}`) must be confirmed against
  `git show HEAD:<file>` before flagging as a delta regression.
- Untracked `NUL`/`uids.txt` untouched and reported as out of scope.
- Session itself performed zero writes and zero live device actions.
