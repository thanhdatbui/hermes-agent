# Dynamic Popup Selector Regression

Use this pattern when a popup's safe action button changes resource IDs across app builds.

## Required fixture evidence

Build XML nodes with the attributes used by the authoritative detector:

- exact `text` for both the risky CTA and safe close action;
- TikTok `package`;
- button-like `class`;
- `clickable="true"`;
- distinct `resource-id` values and explicit `bounds`.

Cover multiple observed ID pairs in one focused test. Assert the exact ADB tap center, the selected element's dynamic resource ID/bounds, and that the obsolete static ID is absent from the recorded action selector.

## Why the negative selector assertion matters

Some lightweight XPath-like test helpers evaluate predicates permissively (for example, returning a node when any predicate matches rather than requiring all predicates). A stale static XPath can therefore still tap a dynamic close node because its text matches. A tap-only assertion will miss the bug; assert selector evidence as well.

## Production shape

When the detector initially matches the CTA:

1. Parse the same XML once more through the authoritative core detector.
2. Require its full contextual match (both exact CTA and close text in TikTok package, clickable button nodes).
3. Pass the detector's returned safe `close_element` into the existing tap primitive.
4. Build an evidence-rich selector from the returned element: text, dynamic resource ID, package, class, clickable state, and bounds.
5. If the core detector returns no match or XML parsing fails, return failure without any tap. Never tap the `Mua ngay` CTA and do not add a coordinate-only swipe in this handler when another bounded fullscreen-shop handler owns that action.

## Verification

Run the new focused test before the production edit and confirm the expected RED failure. After the minimal fix, run the focused test(s), then the exact requested static checks (for example `py_compile` for changed files and `git diff --check`). Report command lines and unabridged pass/fail output. Keep the diff limited to the production flow, focused test, and an indispensable direct import adjustment.
