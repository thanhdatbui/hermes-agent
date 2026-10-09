# UI automation branch probe

Use this recipe when a small Android/UI automation change has no existing focused test and live ADB verification is out of scope.

## Probe contract

1. Parse the source with `ast` and isolate the changed function.
2. Assert the localized selector labels exist in the function source, including the original Unicode text when applicable.
3. Assert branch ordering: the new UI transition occurs before secret lookup, retry loops, or the next state-specific operation.
4. Compile and execute only the isolated function with deterministic mocks for:
   - UI XML capture and state sequence;
   - text-selector tapping;
   - coordinate fallback;
   - sleeps/waits;
   - TOTP generation and code entry;
   - logging and result checks.
5. Assert the exact observable action order, required delays, successful continuation, and that coordinate fallback/live ADB is not called when the text selectors match.
6. Run `py_compile` and a scoped `git diff --check` separately.
7. Create the probe using `tempfile.NamedTemporaryFile(prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir(), delete=False)`, execute the literal path, then remove only the file created by this run and verify it is absent.

## Interpretation

This is **ad-hoc verification**, not suite-green. If a broad pytest invocation times out, call it inconclusive and report it separately; do not downgrade the offline behavior probe or static checks, and do not claim the suite passed. Preserve unrelated dirty paths and avoid live device/network actions.

## Common harness pitfall

When asserting source lines, test membership line-by-line or join the sliced lines into one string. Testing a multi-line list slice directly against a string always fails even when the source contains the requested label.
