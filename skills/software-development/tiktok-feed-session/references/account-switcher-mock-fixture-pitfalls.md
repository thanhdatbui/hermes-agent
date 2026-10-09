# Account Switcher Mock & Fixture Pitfalls in Feed Session Tests

## Context
When writing or maintaining offline unit tests for `verify_and_switch_profile` in `python_runner/flows/feed_swipe_smoke.py` (tested via `python_runner/tests/test_feed_session_smoke.py`), tests mock UI captures via `_capture_step` and `_capture_xml_text`.

## Pitfall 1: StopIteration on `_capture_xml_text` Mock Exhaustion
- **Symptom:** `StopIteration` raised in `_capture_profile_switcher_xml_with_add_phone_guard` when executing `candidate_xml = _capture_xml_text(ctx, f"profile_switcher_{attempt}")`.
- **Cause:** `_capture_profile_switcher_xml_with_add_phone_guard` executes a retry loop over switcher attempts (up to 3 attempts). A test supplying only 3 items in `side_effect=[profile_xml, switcher_xml_1, switcher_xml_2]` runs out of items if an initial check + 3 attempts (or re-check) consumes 4+ calls.
- **Resolution:** Ensure the `side_effect` iterable contains sufficient mock XML returns for all retry attempts, or use a callable side effect that provides a fallback XML rather than a strictly bound finite list.

## Pitfall 2: Premature Exit with `account-switcher-not-open: screen after re-navigation is not profile root`
- **Symptom:** Test expecting `account-switcher-missing-expected` fails assertion because `stop_reason` is `manual-needed:account-switcher-not-open: screen after re-navigation is not profile root`.
- **Cause:** When an account is missing from the switcher or the switcher fails to open, the flow attempts re-navigation back to profile root. During this re-navigation, `_capture_step` and `_capture_xml_text` are consulted to confirm the screen returned to `profile`. If `fake_capture` unconditionally returns `manual-needed:login` for the switch anchor step or returns an unexpected screen, the preflight concludes the switcher never opened because the screen is not profile root before it ever inspects the account list in the switcher.
- **Resolution:** In the test's `fake_capture`, only return `manual-needed` for the specific switcher open guard step (e.g. `profile_preflight_switcher_1_guard`), and allow re-navigation / profile root checks to return `"profile"` / `"success"` so execution reaches switcher missing verification.

## Tooling Pitfall: Windows MSYS Path with `git -C`
- **Symptom:** `git -C "/d/Taadaa/repo" status` returns `fatal: cannot change to '/d/Taadaa/repo': No such file or directory`.
- **Cause:** Windows-native `git.exe` called from Git Bash (MSYS) does not translate `/d/...` paths passed directly to `-C`.
- **Resolution:** Use `cd "/d/Taadaa/repo" && git <command>` or pass Windows-style path `git -C "D:/Taadaa/repo" <command>`.
