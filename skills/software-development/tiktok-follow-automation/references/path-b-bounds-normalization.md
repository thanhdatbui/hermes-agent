# Path B bounds normalization

## Failure pattern

A Path B verifier can reject a valid exact profile and return `MANUAL_REVIEW` when it compares the identity helper's username-element bounds directly with consumer parser bounds.

The two representations may describe the same rectangle with different conventions:

- `automation_core` UI elements: `(left, top, right, bottom)`
- consumer `parse_nodes()`: `(x, y, width, height)`

For example, the XML rectangle `[100,200][400,250]` can become `(100, 200, 400, 250)` in the core helper but `(100, 200, 300, 50)` in the consumer parser.

## Safe fix pattern

1. Convert both representations to one canonical rectangle, preferably `(left, top, right, bottom)`.
2. Enforce strict type validation: require exact `int` (exclude `bool`, `float`, and numeric strings). Return `None` (fail-closed) on any non-int, negative coordinates (`left < 0` or `top < 0`), non-positive size (`width <= 0` or `height <= 0`), or inverted bounds (`right <= left` or `bottom <= top`).
3. Compare the canonical rectangles only after exact normalized UID matching (supporting both `text` and `content_desc`).
4. Preserve the header-band constraint and require exactly one matching header handle.
5. Keep duplicate/suggested-card cases fail-closed; do not remove the identity-element binding check.
6. Add fixtures for:
   - equivalent helper/parser rectangles => accepted;
   - strict type rejection (floats, bools, strings) and negative/inverted coordinates => fail-closed (`None`);
   - wrong profile UID => rejected;
   - duplicate target handle in a suggested card => rejected;
   - missing or ambiguous action => manual.

## Verification

Run the focused Path B tests first, then the repository's canonical follow-runner suite. Report offline fixture results separately from any live canary; passing tests do not prove machine recovery.
