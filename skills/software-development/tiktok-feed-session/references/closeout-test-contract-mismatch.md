# Closeout/Test Contract Mismatch

Use this reference before running the closeout gate when a feed-session production change modifies result semantics.

## Structural mismatch pattern

A production change may intentionally alter terminal result fields.
Example: for `FOLLOW_FAILED`, the new contract resets `followed`, `followed_count`,
`mode1_followed_count`, and `mode2_followed_count` to zero. A paired test still
expecting old module counts can fail with `AssertionError: 0 != 2`.

This is a structural contract mismatch, not a flaky test or a reason to retry unchanged.

## Diagnosis

Look for this pattern in pytest output:
```
FAILED ::TestFeedSessionWatchdogLockGuard::test_merge_follow_result_module_counts
AssertionError: 0 != 2
```

The failing assertion is in `python_runner/tests/test_feed_session_watchdog.py` — the small
paired test for `scripts/feed_session_watchdog.py` (runs in <6s).

## Bounded procedure

1. Read the production diff and identify the new terminal post-condition
   (search diff for `followed_count`, `mode1_followed_count`, `mode2_followed_count`).
2. Run the paired small test BEFORE the closeout gate:
   ```bash
   python -m pytest python_runner/tests/test_feed_session_watchdog.py --tb=short -q
   ```
3. If the assertion reflects the old contract, update it only when the incident/production
   diff proves the new behavior is intended. Otherwise mark BLOCKED.
4. Check ALL downstream consumers of every reset field before changing assertions —
   `merge_follow_result` output is consumed by the watchdog aggregator and Telegram alert
   body; resetting `followed` to `[]` changes the final follow-count report.
5. After paired test passes, run the closeout gate with exact-scope staging so that
   `test_feed_session_smoke.py` (184 tests) is NOT selected as a direct_test.

Never change an assertion merely to make the gate green without first validating the
behavioral change and its downstream effects.

## Exact-scope staging to avoid monolithic test selection

```bash
# Stage ONLY the safe candidate files
git add -- \
  scripts/feed_session_watchdog.py \
  python_runner/flows/multi_machine_feed_session.py \
  python_runner/flows/feed_swipe_smoke.py \
  python_runner/tests/test_feed_session_watchdog.py   # small paired test only

# Gate selects from staged diff only → picks test_feed_session_watchdog.py, NOT smoke
python D:/Taadaa/tools/closeout_gate.py \
  --repo "D:/Taadaa/tiktok-luot nuoi acc" \
  --base origin/master \
  --json-output

# Restore working tree to unstaged state (fully reversible)
git reset HEAD -- \
  scripts/feed_session_watchdog.py \
  python_runner/flows/multi_machine_feed_session.py \
  python_runner/flows/feed_swipe_smoke.py \
  python_runner/tests/test_feed_session_watchdog.py
```
