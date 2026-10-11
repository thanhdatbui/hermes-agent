# Parallel Feed-Alert Fix Contract

## Use case
A single farm run can surface two different defects at once: the watchdog may collapse distinct failure causes into one report label while the feed runner stops on a benign TikTok popup. Treat these as independent code-fix branches.

## Closed branch contract

For each branch record:

- absolute production file path;
- optional exact test file path;
- unique `OLD_STRING`/anchor and bounded replacement;
- one focused offline command (`python -m pytest <file.py>::<test_name> -q` or `python -m py_compile <file.py>`);
- forbidden side effects: no device taps, no live ADB, no broad scan, no unrelated cleanup.

The watchdog branch should add specific signatures in precedence order and keep the catch-all label last. The popup branch should use captured UI XML as the fixture source, extend the existing safe selector/registry, and add a regression test for the observed resource ID. Do not dismiss commerce controls by coordinate or add a broad `popup` handler without an allowlisted selector.

## Acceptance matrix

| Branch | Evidence required |
|---|---|
| Watchdog taxonomy | focused classifier test, compile, representative strings for ATX/switcher/focus/popup/timeout/retry, runtime-copy parity if a separate AppData copy is loaded |
| Popup handling | focused fixture test for the real selector, compile, no live-device action |
| Shared workspace | path-scoped diff/numstat, unrelated dirty/generated artifacts preserved and reported |

A green worker self-report is not sufficient: independently inspect the exact path, diff, and fresh command output before reporting completion.
