# Profile verification identity + popup import regression

## Scope

Offline regression pattern for `multi-machine-feed-session` / `feed_swipe_smoke` when a Farm Alert reports both:

- `ACCOUNT_UPDATE_PROMPT_SCREEN is not defined`
- `profile verification navigation failed: TikTok focus lost`

Do not use this recipe to authorize live-device interaction. Reproduce with fixtures and focused tests first.

## Root causes

### 1. Undefined popup symbol
A constant defined in `core.benign_popup` is not automatically available in `flows.benign_popup`. The consumer must import the symbol explicitly. Verify both the definition and the consumer import, then execute the handler test that references the symbol.

### 2. False-positive profile identity
A username-like node (`@name`) can exist in stale, overlay, switcher, or non-Profile XML. A successful tap return is also not proof that TikTok changed screens. The safe predicate is:

```text
selected Profile tab marker + exact normalized username match
```

If either part is missing, return manual-needed/mismatch and leave identity fields empty as appropriate.

## Minimal fixture rules

Success fixture must contain a selected Profile tab node in the same XML capture as the username, for example:

```xml
<node text="@expected_user" bounds="[10,490][210,540]" />
<node text="Hồ sơ" selected="true" bounds="[864,1794][1080,1920]" />
```

A fixture with only `@expected_user` is intentionally insufficient. It should exercise the fail-closed path. A fixture with `Message`, Inbox, or another unrelated first text must not populate `display_name` from `texts[0]`.

For account-switcher flows, do not consume switcher XML as profile identity. Titleless switcher detection may use multiple account-like rows, but a single username-like row must not prove Profile navigation.

## Regression sequence

1. Search the definition and all call-chain consumers of the reported symbol.
2. Run the smallest red test for the popup handler and the smallest profile verification test.
3. Patch only the missing consumer import and the profile predicate/retry path.
4. Update success fixtures to include the selected Profile marker; update negative assertions when the old test expected unsafe username extraction.
5. Run focused profile/capture tests, then the consumer popup + feed-smoke regression set.
6. Run the full `test_feed_session_smoke.py` suite when it is part of the acceptance contract.
7. Verify `compileall`, `git diff --check`, and a symbol search. Do not touch ADB/live devices for this offline fix.

## Evidence and acceptance

Profile capture artifacts must be persisted before identity parsing/classification: exact `ui.xml` and matching `screen.png` in the attempt artifact. An artifact directory name or `xml_available=true` field alone is not evidence.

Minimum acceptance evidence from the reference session:

- focused profile subset: `39 passed, 132 deselected`;
- popup/feed-smoke regression: `169 passed, 10 skipped, 4 subtests passed`;
- full feed-session suite: `170 passed, 1 skipped, 4 subtests passed`;
- `compileall`: pass;
- `git diff --check`: pass;
- symbol search shows the constant definition and explicit consumer import.

These counts are historical examples; always report fresh output from the current worktree.

## Pitfalls

- Do not treat a repository-wide symbol hit as proof that the consumer can resolve it.
- Do not weaken the Profile predicate to satisfy an old fixture that lacks the selected-tab marker.
- Do not add a fallback retry that accepts `@username` without Profile confirmation.
- Do not report `TikTok focus lost` as fixed from a test that never asserts the post-navigation screen.
- Do not claim live recovery from offline tests; no device action is part of this recipe.
