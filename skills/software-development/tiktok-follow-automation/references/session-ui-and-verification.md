# Session UI and Verification Reference

## Known reproductions

- **Empty relation surface:** TikTok 46.x can expose `com.ss.android.ugc.trill:id/yx1` on an empty relation screen. The empty classification must still require the structural shell (relation ViewPager + expected non-clickable title + empty message); a selector alone is insufficient.
- **Search fallback:** The Top tab can contain only videos. After a bounded exact-result wait, detect an unselected `Người dùng`/`Users` tab in the upper tab strip, tap it, and re-run exact account-result extraction. Use the unique account handle field when available and reject video-only creator labels.
- **Header-scoped identity:** Suggested accounts create additional `@...` nodes. Validate the target only against a header-bounded `@` node and the profile identity helper's username; a matching suggestion is not proof of identity.
- **Zero Following:** A header label such as `0 Đang follow` is a valid exhausted anchor. Return to Feed and continue with the next anchor; do not enter a recovery ladder just because no relation list exists.

## Test execution recipe

```text
python -m pytest follow_runner/tests/test_mode2_follow_followers.py -q
python -m pytest follow_runner/tests/test_mode2_following.py -q
python -m pytest follow_runner/tests/test_cli.py -q
python -m pytest follow_runner/tests/ -q
python -m py_compile follow_runner/run_follow.py follow_runner/flows/mode1_search_follow.py follow_runner/flows/mode2_follow_followers.py
 git diff --check
```

Use the repository's configured automation Python interpreter when available. Treat a live device run as separate evidence: first perform a dry-run, then check the device/serial and current lock owner. Never interfere with an official farm owner process merely to force a canary.

## Pitfalls captured

- Do not add a global test fixture that disables production device locks; patch the lock/preflight boundary only in tests that need it, and preserve a regression test for lock refusal.
- Do not infer success from a partial/truncated pytest log or from a timed-out run. Re-run with a bounded focused target, then the full suite, and retain the actual pass count.
- Do not replace exact UI selectors with broad text-only matches. Every new locale/resource-id fallback needs a structural and coordinate/identity gate.
