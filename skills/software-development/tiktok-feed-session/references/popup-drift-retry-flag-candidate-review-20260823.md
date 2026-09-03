# Popup-drift recovery + retry-flag candidate review (2026-08-23)

Read-only closeout review of `python_runner/flows/feed_swipe_smoke.py` +
`python_runner/tests/test_feed_swipe_smoke.py` in `tiktok-luot nuoi acc`
(HEAD f76350a). Verdict: APPROVED for the exact-scope candidate; unrelated
same-file hunks preserved out-of-scope.

## Candidate composition (in scope)

1. **Deadline-starvation fix:** new `retry_after_initial_miss: bool = True`
   threaded through three layers —
   `_gem_blind_probe_rule_for_checkpoint` (~L3986),
   `_run_gemphonefarm_blind_popup_checkpoint` (~L4155→4195),
   `_maybe_run_gemphonefarm_blind_popup_checkpoint` (~L4361→4383).
   Initial-miss guard (~L4058) returns `(initial_xml_text, None)`
   immediately — no sleep, no recapture. Only the post-swipe call site
   (~L18359) opts out with `retry_after_initial_miss=False`; the other
   call sites (baseline, profile preflight, before, confirm ×2,
   retry-confirm, back-recheck) keep default True.
2. **Popup-drift recovery:** `_recover_popup_feed_tab_drift` (~L4661):
   guard chain = failed + reason `"feed not confirmed"` + `safety_status`
   ok + `_current_top_tab_from_row(row)` in `FEED_TYPES` ≠ expected +
   XML evidence (`xml_available` OR latest-attempt `xml_path` via
   `_latest_attempt`, ~L5062). Relabels DEGRADED and sets
   `popup_feed_tab_drift_recovered`, `feed_drift_from/to`. Wired at
   ~L18365–18370 BEFORE `_maybe_dismiss_verify_trap` and the BACK-recheck
   checkpoint, so those stages' `after_expected=_expected_feed_label(
   current_feed_type)` uses the recovered tab.

## Regression tests added (test_feed_swipe_smoke.py)

- `test_post_swipe_popup_checkpoint_does_not_retry_initial_rule_misses` —
  mocks `_run_gemphonefarm_blind_popup_checkpoint`, asserts
  `checkpoint.call_args.kwargs["retry_after_initial_miss"] is False`
  (reusable kwarg-threading assertion pattern).
- `test_popup_checkpoint_accepts_confirmed_feed_tab_drift` — positive path;
  asserts DEGRADED + all marker fields (`feed_drift_from/to`,
  `popup_feed_tab_drift_recovered`).
- `test_popup_checkpoint_drift_recovery_requires_xml_evidence` —
  fail-closed; row stays `failed`.

## Unrelated same-file dirty hunks (out of scope, preserved)

PNG chunk/CRC validation (`_is_valid_png` + `zlib`/`struct` imports),
legacy capture-metadata derivation (`artifact_path` → `ui.xml`/`screen.png`),
and profile username-anchor matching replacing any-text matching — plus
their fixture updates (hex-encoded minimal PNG fixtures). Internally
consistent, but outside the stated candidate scope: an exact-scope commit
must stage only candidate hunks (hunk-level selection), never whole-file
adds.

## Read-only review mechanics

- Artifact-free syntax gate:
  `python -c "import ast; ast.parse(open(f, encoding='utf-8').read())"`
  per dirty file (avoids writing `__pycache__`; `.gitignore` covered it
  here, but a review pass should not rely on that).
- Zero-mutation proof: `git status --porcelain` captured before and after
  the review — byte-identical (same 5 modified files, nothing staged or
  created).
- Report shape: `VERDICT:` / one-line `FINDINGS:` / one-line `SCOPE:`;
  unrelated dirty files (HANDOFF.md evidence-gate section, PROJECT_RULES.md
  global log+XML gate, multi_machine_feed_session.py follow-hook row 1/2
  gate) reported as preserved/out-of-scope, not blockers.
