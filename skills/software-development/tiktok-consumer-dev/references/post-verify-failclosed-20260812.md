# VERIFY_POST fail-closed: UNKNOWN submission + unreliable profile-grid increments (2026-08-12)

Repo: `D:\Taadaa\Tiktok-video` (upload consumer). Scope: `_handle_verify_post` +
`_verify_profile_post_increment` + `_recheck_ambiguous_post` in
`scripts/tiktok_workflow/state_machine.py`. Registry: `docs/tiktok-ui-compatibility.md`
entries `COMPAT-POST-VERIFY-004` (UNKNOWN) and `COMPAT-POST-VERIFY-005` (reliability).

## Incident (machine 74, video 7, folder 585)

- Run 23:55 (2026-08-11): POST tap ADB timeout → `post_submission_state=UNKNOWN`,
  verify lạc sang TIKTOK_LIVE_MOBILE_GAMING → MANUAL_REVIEW.
- Run 10:17 (2026-08-12): resumed the OLD receipt straight into VERIFY_POST, counted
  profile tiles 3→4 from ONE clipped viewport (`Không tìm thấy scroll container;
  dừng ở viewport 1`), logged `profile video tile increment confirmed` → wrote
  workbook `Video Đã Đăng=7` as SUCCESS. Real profile still had the same 5 old tiles
  (bếp/súp/trời/cửa hàng/cherry). Receipt had to be archived
  (`.bak-false-complete-20260812`) to retry.

## Rule 1 — UNKNOWN submission NEVER succeeds / writes workbook (COMPAT-POST-VERIFY-004)

`post_submission_state=UNKNOWN` = the tap outcome was never proven (ADB timeout, no
`post_tapped_at` / `post_submission_accepted_at`). Fail closed to MANUAL_REVIEW:
no `post_result=SUCCESS`, no `post_verified`, no UPDATE_WORKBOOK, no generic
verifier path. Implementation:

- `_post_submission_state_allows_success()` — gate in `_handle_verify_post` AFTER the
  LIVE-surface guard (safety ordering: live surface dismissed first, then gate).
- Gate blocks UNKNOWN **only when a Post attempt is evidenced**
  (`post_tap_attempted` / `post_submission_accepted` / receipt has
  `post_tapped_at|post_retry_tapped_at|post_intent_at|post_retry_intent_at`).
  A run that never tapped (generic verifier probe) still goes through the old
  `POST_VERIFY_PROOF_INSUFFICIENT` path — this keeps legacy suite tests green.
- Error code `POST_SUBMISSION_UNKNOWN`, `recovery_resume_state=MANUAL_REVIEW`,
  checkpoint `status=MANUAL_REVIEW`, receipt stays `status!=completed`.
- Legacy `verification_pending` receipts WITHOUT the durable field are routed as
  ACCEPTED by `_route_existing_post_receipt_to_verification` (existing behavior
  preserved); only explicit UNKNOWN is blocked.
- ACCEPTED + recheck UNAVAILABLE → treated as published is a SEPARATE documented
  path (COMPAT-POST-VERIFY-003, 2026-08-07 machines 10/22/30) — do not remove it.

## Rule 2 — tile-count increment needs reliable scans on BOTH sides (COMPAT-POST-VERIFY-005)

A count from a single clipped viewport (missing scroll container) is a LOWER BOUND
of an unknown grid, not the true count. Increment from such counts is not evidence.

- `_profile_scan_is_reliable(scan)` → `viewports >= 2` (scroll container found).
- Baseline scan metadata `pre_post_profile_grid_scan` persisted: recorded in
  ACCOUNT_READY (`_profile_grid_scan_reliability()`), written to receipt in
  `_record_post_intent`, restored in `_route_existing_post_receipt_to_verification`,
  and echoed into checkpoint.
- `_verify_profile_post_increment()`: returns False early when baseline scan is
  unreliable; current scan must ALSO be reliable before `current > baseline` is
  accepted. Warning: `không kết luận tăng`.
- `_recheck_ambiguous_post()`: `FOUND` only when baseline scan reliable AND current
  scan reliable; unreliable increment → warning + `stable_not_found=False` →
  `UNAVAILABLE` (blocks both blind success and blind retry).

## Tests (all in `tests/test_tiktok_workflow.py`, full suite 344 → 350 passed)

- `test_unknown_submission_never_advances_even_with_profile_increment`
- `test_unknown_submission_blocked_before_own_surface_evidence`
- `test_old_unknown_receipt_cannot_resume_into_success`
- `test_profile_increment_requires_same_method_reliable_baseline_and_current`
  (calls `_verify_profile_post_increment` directly — baseline unreliable → False,
  profile never opened)
- `test_profile_recheck_does_not_confirm_found_from_unreliable_increment`
- `test_profile_increment_accepted_when_baseline_and_current_reliable`
  (real increment path through `_handle_verify_post`, ACCEPTED → SUCCESS)

## Workflow pitfalls hit this session

- **patch tool mangled indentation 4+ times on `state_machine.py` (~12k lines,
  550KB)**: mode=replace re-indented whole inserted blocks (+4/+8/+12 spaces),
  breaking syntax; a failed `&&`-chained bash heredoc made things worse. Fixes that
  worked: (a) line-range dedent-by-4 via a small Python script (`for i in
  range(a-1, b): if lines[i].startswith("    "): lines[i] = lines[i][4:]`) then
  `py_compile`; (b) byte-exact string replace via a write_file'd Python script
  (never inline heredocs — git-bash `unexpected EOF` on quotes). After EVERY
  repair run `py_compile` before continuing.
- **Whitespace-only edits after the last suite run invalidate the evidence**: the
  dedent fix (semantically identical) landed after the 350-pass run → harness flags
  "unverified". Re-run the canonical suite on the FINAL state; do whitespace cleanup
  BEFORE the final suite run when possible.
- **Ad-hoc `hermes-verify-*.py` probes (see `ad-hoc-verify-script-pattern.md`)**:
  probe-script bugs are NOT code bugs — fix the script, not the code. Two traps hit:
  (1) capture state BEFORE mutating operations (the gate overwrote
  `recovery_resume_state` to MANUAL_REVIEW before the check read it — snapshot
  `route_resume` right after routing); (2) `**overrides` + explicit `dry_run=False`
  kwarg → duplicate keyword; pop defaults from overrides first. Clean up BOTH the
  script and any `tempfile.mkdtemp(prefix="hermes-verify-...")` dirs it created.
- **COMPAT numbering must be checked BEFORE writing code comments**: group numbers
  are sequential per group (POST-VERIFY already had 001-003) — code comments/log
  strings initially said `COMPAT-POST-VERIFY-001/002` and had to be renamed to
  004/005 to match the registry. `grep -nE '^### COMPAT' docs/tiktok-ui-compatibility.md`
  first, then reference the REAL entry IDs in code.
- Canonical suite for Tiktok-video upload repo:
  `PYTHONPATH=. "D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -m pytest tests/test_tiktok_workflow.py -q -p no:cacheprovider`
  (PROJECT_RULES.md COMMIT GATE: commit when suite green, no live-run needed).
