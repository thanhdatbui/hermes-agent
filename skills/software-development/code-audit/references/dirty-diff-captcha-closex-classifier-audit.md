# Dirty-Diff Captcha Close-X Classifier Audit — Fail-Closed Verification Matrix

Read-only verification matrix for a scoped fix that classifies a drag-piece
**captcha puzzle with a real close-X** as a recoverable `manual-needed:popup`
(→ existing typed dismiss handler taps the X) while keeping a **captcha without
close-X** fail-closed as `manual_challenge` / restart.

Worked on `D:\Taadaa\tiktok-luot nuoi acc` (2026-08-22). The detector lives in
the shared-core wheel `automation_core.tiktok.benign_popup`:

- `detect_captcha_puzzle_close(root)` — requires `_CAPTCHA_PUZZLE_TEXT_TERMS`
  (`captcha`, `kéo mảnh ghép`, `xác minh để tiếp tục`) AND a top-right/X-labeled
  clickable close, **excluding** `verify-bar-close` (the GemPhoneFarm banner-close
  does NOT clear the puzzle).
- `detect_captcha_puzzle_needs_restart(root)` — captcha text present, no close-X →
  caller force-stops/relaunches.
- Action mapping: `captcha_puzzle` → `_dismiss_action` → default `"dismiss_close_x"`
  (`_action_match` at benign_popup.py:1673-1675; `_dismiss_action` falls through to
  `"dismiss_close_x"` at the end of its if-chain).

The consumer classifier (`python_runner/core/classifier.py`) adds an early-return
before the `verify-bar-close` manual_challenge block:

```
# classifier.py ~419
if detect_captcha_puzzle_close(root) is not None:
    return ScreenClassification(
        screen="manual-needed:popup",
        confidence=0.98,
        reasons=["dismissable captcha puzzle with close-X"],
        manual_needed=True,
    )
```

## The five-case matrix (run via a disposable `python` probe, not grep)

Feed each XML to `classify_tiktok_screen` and assert the screen + fail-closed
behavior. This is the executable contract for the fix.

| # | Scenario | XML signature | Expected `screen` | Why |
|---|----------|---------------|-------------------|-----|
| A | captcha + close-X + verify-bar-close | `verify-bar-close` (clickable) + `CAPTCHA`/`Xác minh để tiếp tục`/`Kéo mảnh ghép` + `com.ss.android.ugc.trill:id/close` ImageView top-right | `manual-needed:popup` | Real X found → recoverable |
| B | captcha, NO X, but verify-bar-close | `verify-bar-close` + `CAPTCHA`, no close-X | `manual-needed:manual_challenge` | No X → can't dismiss → fail-closed |
| C | pure captcha text, NO verify-bar-close, NO `xác minh`, NO X | `CAPTCHA` + `Kéo mảnh ghép` only | stays challenge-ish (NOT auto-dismissable) | No X nor banner → never `manual-needed:popup` |
| D | close-X but NO captcha text | other modal + `:id/close` | NOT a captcha popup | Close-X alone can't trigger captcha branch |
| E | verify-bar-close + close-X but NO captcha term | `verify-bar-close` + `Xác minh để tiếp tục` + `:id/close`, but no `CAPTCHA`/`kéo mảnh ghép` | governed by the non-captcha path (verify-bar-close branch), NOT the captcha popup branch | captcha detector requires its own text terms |

Cases A–B are the core requirement (recoverable vs fail-closed). Cases C–E are the
regression guards proving the close-X / verify-bar-close are **not** over-matched.

### Geometry caveat (case A test fixture)
`_find_captcha_puzzle_close_x` uses `in_top_right` = `cx >= 0.55*right_max AND
cy <= 0.45*bottom_max`. A fixture whose close-X is at `[980,280][1056,356]`
(right_max ~1080) passes (cx=1018 ≥ 594, cy=318 ≤ 486). Verify the fixture's X is
actually in the top-right quadrant or the positive test will silently fail.

## Minimum regression tests to require before APPROVED

1. Positive: `manual-needed:popup` + reason contains `"close-X"` when captcha text
   + real `:id/close` present (covers requirement 1).
2. Negative/fail-closed: an existing pre-existing test
   (`test_manual_challenge_manual_needed_with_captcha_text`) already covers captcha
   WITHOUT a close-X → `manual_challenge`. **Flag if this is the ONLY fail-closed
   guard** — prefer a test colocated with the feature asserting
   `result.screen != "manual-needed:popup"` for the no-X case (avoid relying on an
   unrelated test for a new invariant).

## Out-of-allowlist dirty files (scope discipline)

The task may name only the classifier + test files, but `git status` can show a
THIRD dirty file that is unrelated (e.g. a follow-friends popup rewrite in
`flows/benign_popup.py`, mtime *after* the captcha edits, zero captcha references).
Preserve it, flag it as a separate finding, and do NOT fold it into the closeout
commit. The user's stated file count is a hypothesis; `git status` is the ground
truth. Re-capture `git status --short` immediately before the verdict (time-of-check
vs time-of-use) because the worktree is a live surface.
