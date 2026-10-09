# ADB transport healer: two-phase verification probe

Use this recipe for offline/hung ADB watchdog changes and synchronized mirror copies.

## Contract

- Offline recovery is successful only if `reconnect offline` is followed by `devices` reporting the same serial as `device`.
- Hung recovery is successful only if reconnect + wake is followed by a bounded health check (`shell echo 1`) containing `1`.
- A failed second observation must not produce a healed item.
- When a source and mirror are changed, assert both contain the new terminal-state strings and the same recovery markers.
- Assert binary precedence separately: XiaoWei's ADB path must be considered before the GemPhoneFarm fallback.

## Probe shape

Use `tempfile.NamedTemporaryFile(prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir(), delete=False)` to create the probe. Import the changed source by absolute path, patch `subp_run` and sleep, and feed ordered mock responses for:

1. initial offline/device listing;
2. reconnect action;
3. post-action device listing;
4. hung recovery action sequence;
5. post-action health probe.

Execute the exact literal generated path in a separate top-level command. Remove only that owned file and verify it no longer exists. Preserve any pre-existing `hermes-verify-*.py` files. Label the result **ad-hoc verification**; it is not a replacement for the canonical unit-test suite.
