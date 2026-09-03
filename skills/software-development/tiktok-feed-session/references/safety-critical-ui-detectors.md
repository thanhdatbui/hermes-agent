# Safety-Critical UI Detectors: Story Reply / Quick Reaction

## Why this class matters
A popup detector that dispatches `BACK`, tap, or navigation is an action gate. A false positive can close a DM/comment/share composer or another sensitive screen; a false negative can leave a blocking overlay in place. Treat detector precision and scope correlation as safety properties.

## Evidence contract
Use two separate evidence classes:

- **Ownership:** Story-specific resource/container ID or another explicit scope anchor.
- **Transient state:** focused Story input, keyboard, quick-reaction tray/control, or verified overlay marker.

A generic label (`Reply to`, `Send a message`), global IME presence, or emoji in caption/content is not ownership evidence.

## Bounded-scope algorithm
1. Parse XML fail-closed; malformed/empty XML must not dispatch an action.
2. Find the smallest candidate containing the Story-specific input/anchor and composer marker.
3. If the reaction tray is a sibling, use the immediate common parent of the anchored input, marker, and tray—not the whole XML root or a broad host.
4. For initial routing, require transient evidence:
   - keyboard + the Story input is `focused="true"`, with no different foreground input also focused; or
   - an explicit reaction-tray resource/control in the same bounded scope.
5. For post-BACK residual checks, require the same Story anchor and a surviving input/placeholder. A generic residual label without the anchor is ambiguous and must return false.
6. OCR-only generic wording is insufficient for action dispatch; prefer a fresh XML hierarchy or return no match.

## Required negative cases
- Ordinary DM/share/comment composer with `Send a message...` and Gboard.
- Story background bar plus a different foreground focused input.
- Caption containing `❤️`, `🔥`, or multiple emojis without a tray/control.
- Generic `emoji_tray` or `quick_reaction` control outside the Story composer.
- `search_history`/`watch history` text that contains the substring `story`.
- OTP/password/settings UI with an EditText and keyboard.

## Required positive cases
- Story-specific input + direct marker + focused keyboard.
- Story-specific container with a reaction tray and no keyboard.
- Marker/input/tray siblings under an opaque but immediate common parent.
- After first BACK, anchored composer remains with placeholder or input; only then is a second BACK eligible.

## Review and verification
Use RED→GREEN fixtures for every reviewer finding. Run, in order:

```bash
PYTHONPATH="python_runner;.;D:/Taadaa/automation-core/src" python -m pytest -q -p no:cacheprovider python_runner/tests/test_benign_popup_registry.py
PYTHONPATH="python_runner;.;D:/Taadaa/automation-core/src" python -m pytest -q -p no:cacheprovider python_runner/tests/test_benign_popup_registry.py python_runner/tests/test_classifier.py python_runner/tests/test_benign_popup.py python_runner/tests/test_safety.py
python -m py_compile python_runner/flows/benign_popup_registry.py python_runner/core/classifier.py
 git diff --check
```

Do not use a green focused suite as proof that a broad substring detector is safe. Independently inspect whether marker, input, keyboard, and reaction evidence can come from unrelated scopes. If successive patches trade false positives for false negatives, stop broadening markers and tighten the ownership contract.

## Session-derived pitfalls
- A function named `is_*_remaining()` that re-detects any matching UI after `BACK` does not preserve identity of the original overlay. Where possible, carry an anchor/signature from pre-action to post-action.
- A `story_reply_*` host resource ID does not prove every descendant EditText belongs to the Story composer; require the Story-specific input or bounded relationship.
- Counting two emoji characters is not a reaction panel; use explicit tray/control evidence or structured sibling controls.
- A review that repeatedly rejects scope correlation is signaling an architectural boundary problem, not a need for more marker strings.
