# UI Detector Extraction Reference

## Contract

For a repeated Playwright detection block, extract two responsibilities:

- `detect_*_options(page, ...)` performs selector lookup and visibility checks.
- The orchestration loop classifies the ordered availability flags, logs the
  selected route, clicks the selected locator, and controls retry/continue.

A practical return contract is:

```python
available, locators = detect_challenge_options(page, totp_secret, has_phone)
choice = classify_s7_challenge_selection(*available)
if choice and locators.get(choice):
    locators[choice].click()
```

The tuple preserves compatibility with an existing priority classifier while the
map keeps the selected locator explicit and avoids recomputing selectors in the
caller.

## Focused fake-page test

Use a minimal fake that mirrors only the Playwright surface the helper needs:

```python
class FakeLocator:
    @property
    def first(self):
        return self

    def count(self):
        return 1

    def is_visible(self):
        return True

class FakePage:
    def locator(self, selector):
        return FakeLocator()
```

Assert the full ordered tuple, exact option keys, and that every available map
entry is an actionable fake locator. This catches missing `.first`, wrong
selector wiring, and accidental boolean-only returns.

## Verification sequence

1. Add/import the focused test and run it once to establish RED when the helper is
   absent or the fake contract is incomplete.
2. Implement the smallest extraction preserving selectors and priority.
3. Run the entire affected test module.
4. Run import/compile and `git diff --check`.
5. If the test fixture or implementation changes after a green run, rerun the
   focused test and affected module; earlier output is historical.

Warnings from unrelated optional dependencies should be reported separately from
exit status and test counts.
