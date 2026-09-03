# Mode 1 Search-Follow Read-Only Audit — 2026-08-15

Read-only audit of canonical Mode 1 TikTok Follow (repo `D:\Taadaa\tiktok-follow`).
No files modified, no live device actions. Findings are the fix contract for the
next worker round; the 5 failing tests in the dirty working tree encode exactly
these invariants.

## Baseline evidence

`python -m pytest follow_runner/tests/test_verify_follow.py follow_runner/tests/test_mode1_search_follow.py -q`
→ **5 failed / 37 passed**. The failures are NEW tests from parent in-progress
(uncommitted) edits — treat them as the contract spec, not regressions:
- `test_verify_follow.py::test_classify_follower_label_is_not_a_follow_action`
- `test_verify_follow.py::test_verify_uses_supplied_identity_bound_classifier`
- `test_mode1_search_follow.py::test_follow_one_uid_rejects_wrong_exact_profile_before_follow_tap`
- `test_mode1_search_follow.py::test_tap_follow_button_ignores_follower_label`
- `test_mode1_search_follow.py::test_tap_follow_button_rejects_ambiguous_exact_actions`

## Findings (prioritized, file:line on working-tree bytes)

### P1 — Mode 1 skips profile-identity verification before tapping Follow
- `follow_runner/flows/mode1_search_follow.py:84-97` (`follow_one_uid`): after
  `_nav_search` only `dump_ui()` → `classify_button()` → tap Follow. No handle
  comparison — wrong profile can be followed.
- **Mode 2 already has the gate**: `mode2_follow_followers.py:214-259`
  (`_open_follower_tab`) requires `profile_identity_from_xml` + exactly one
  `id/sf5` node + normalized handle == uid, else fail-closed. Mode 1 must mirror it.
- Minimal patch: in `follow_one_uid`, before classify/tap, verify
  `profile_identity_from_xml(profile_xml)` — username present, exactly one node
  whose resource_id ends `id/sf5`, `_normalize_handle(username) == _normalize_handle(uid)`;
  mismatch → `("manual", "MANUAL_REVIEW: profile identity mismatch ...")`, no tap.
  Re-verify identity after `_reload_profile` too.

### P1 — Self-target not excluded (follow own account risk)
- `follow_engine.py:336-342` `follow_uids()` returns `uid_source_mapping.tik_ids()`
  = every UID in the safe workbook, with no exclusion of the active account.
- **Green-for-wrong-reason test**: `test_follow_engine.py:557-579`
  `test_follow_uids_come_from_full_safe_mapping_but_exclude_active_account` sets
  `eng.active_account_handle = "@UID_B"` and expects `["uid_a","uid_c"]`, but
  `FollowEngine.__init__` never creates `active_account_handle` and `follow_uids()`
  never reads it → the exclusion gate does not exist in production.
- Minimal patch: store the active handle in `__init__` (from
  `mapping.get_by_machine(machine).tik_id` or the verified handle);
  `follow_uids()` filters out normalized-equal entries.

### P1 — Substring marker matching → "Follower" treated as a Follow action
- `verify_follow.py:35-45` `classify_button`: `any(m.lower() in v ...)` with
  marker `"follow"` → node text "Follower" (tab) matches → wrong classification.
- `mode1_search_follow.py:287-299` `_tap_follow_button`:
  `find_node(text="Follow")` is substring → can tap the Follower tab instead of
  the real button.
- Minimal patch: exact match (casefold + strip); exclude nodes whose resource_id
  ends `id/sdn` (Follower tab) and `id/sf5` (handle); tap only when exactly ONE
  candidate; `classify_button` returns `unknown` when candidates != 1.

### P2 — `verify_after_tap` is whole-screen, not identity-bound
- `verify_follow.py:82-113`: scans the entire dump — any "Đã follow" node
  anywhere (popup, another profile card, tab) → `success` immediately; no
  identity check on the fresh post-tap dump, no binding to the button just tapped.
- Minimal patch: `verify_after_tap(..., classify_fn=None)` — default to an
  identity-bound classifier reusing the P1 gate; each fresh dump must prove
  profile identity == uid before reading button state; unknown → manual, never
  silent success.

### P2 — `_wait_search_result` matches text only, not account identity
- `mode1_search_follow.py:158-231`: identities filtered on `text == uid`
  (non-input, bounded) with no resource-id/profile check; `:228` returns the
  nearest bounded clickable ancestor without verifying it is an account card.
  Two accounts sharing display text → tree-order pick. Mitigated downstream by
  the P1 gate; prefer candidates with account-profile resource-id when fixing.

### P3 — shuffle + non-atomic mark/consume
- `mode1_search_follow.py:32` `random.shuffle(uids)` hurts traceability;
  `run_mode1:45-49` calls `state.mark` then `consume_budget` — a `_save()` failure
  between them skews followed/budget. Consider shuffle-with-seed logged in
  details, and atomic mark+consume.

## Reusable audit probes used
1. **Dirty-tree failing tests = contract spec**: `git status --short` first;
   new failing tests in uncommitted parent edits define the intended invariants —
   align findings with them instead of treating them as source regressions.
2. **Green-for-wrong-reason**: a test that sets an attribute on the engine
   (`active_account_handle`) and asserts exclusion, while production `__init__`
   never creates that attribute, is NOT evidence the gate exists — verify the
   production symbol/setter exists before trusting the test.
3. **Cross-mode asymmetry probe**: Mode 2 (`_open_follower_tab`) has the sf5
   identity gate; Mode 1 (`follow_one_uid`) does not. Comparing sibling flows in
   the same repo surfaces missing gates fast.
