# Canonical startup deadlines, verifier proof, and safe API probes

This reference records consumer-side lessons for public `automation-core` startup/capture/recovery APIs. It is deliberately version-aware: verify the exact pinned artifact rather than assuming the checked-out core source and installed runtime expose the same contract.

## 1. Inspect compatibility without mutating state

Use introspection against the exact wheel or source tree:

```bash
PYTHONPATH='D:/Taadaa/automation-core/dist/automation_core-X.Y.Z-py3-none-any.whl' \
  python scripts/inspect_core_contract.py \
  automation_core.device_lock:acquire_device_lock \
  automation_core.device_lock:DeviceLockLease.finish \
  automation_core.ui:capture_ui_xml
```

Record:

- imported module path (`module.__file__`)
- distribution version when available
- `inspect.signature` for every callable used
- explicit presence/absence of exceptions and kwargs

Do **not** test compatibility by calling `acquire_device_lock` on a made-up machine/serial. That creates real alias files in the shared lock root. If an acquisition integration test is necessary, pass a temporary `lock_root`, retain the returned lease, release it through the public ownership-aware API, and verify the temporary root is empty afterward.

### Version drift observed

A consumer pinned to wheel `0.4.44` was being verified in a runtime importing `0.4.45`/newer source. The newer contract accepted/exposed names that `0.4.44` did not, including a `user_authorized` acquisition kwarg and `DeviceLockNeedsUserDecision`. Tests using the ambient runtime were green while the pinned wheel rejected the production call. The fix is not to guess version numbers; run the same targeted tests with `PYTHONPATH` pointed at the pinned artifact and clear inherited `PYTHONPATH` when verifying the installed runtime.

## 2. One absolute monotonic deadline

When the consumer contract says “60-second non-destructive Splash guard inside a 90-second overall Feed deadline,” use two absolute clocks:

```python
started = monotonic()
feed_deadline = started + feed_timeout
splash_guard_deadline = min(started + splash_guard, feed_deadline)
```

Rules:

1. Initial shared TikTok preparation happens once.
2. Until `splash_guard_deadline`, Splash/loading, capture exceptions, absent focus, and wrong focus are observations only. No force-stop, relaunch, backend cleanup, or reboot.
3. Every recovery stage receives the same `feed_deadline` and derives `remaining = feed_deadline - monotonic()` immediately before starting and after returning.
4. Never start B1/B2/B3 when `remaining <= 0`. Bound stage timeouts by remaining budget where the API permits it.
5. B1 is one core-owned persistent-backend recovery plus recapture. B2 is at most one canonical TikTok relaunch. B3 is callback-aware core reboot only when explicitly enabled and eligible.
6. A stage does not get a new 60/90-second window. If a consumer needs a separate reboot budget, that must be an explicit contract/config field—not an accidental deadline reset.
7. Boundary tests must assert the action ledger: no recovery before 60.0, success at exactly the guard/deadline boundary, and no stage begins after the overall deadline.

A fake clock that jumps by 30/60 seconds per *read* can hide overshoot. Prefer a controllable clock advanced by the injected sleeper, and assert timestamps on each recovery action.

## 3. Feed proof must be exact

Core capture verification and app-specific Feed verification are separate gates.

A valid Feed proof requires all of:

- exact foreground package
- concrete non-Splash activity
- fresh, verified hierarchy from the structured capture result
- exact parsed semantic evidence, not `substring in xml`

The lightweight core capture path can treat absent foreground evidence as inconclusive and still return verified XML. Therefore the consumer must independently reject absent/wrong package or activity before declaring Feed success.

Do not use markers such as `"following" in xml`: unrelated text such as “Stop following this creator?” is a false positive. Parse nodes and compare normalized `text`/`content-desc` exactly. A stronger TikTok Feed proof can use a unique bottom navigation structure: selected Home, unselected Profile, one Search semantic, and no follower-list recycler.

## 4. Freshness tokens are capture-generation evidence

Do not use a screenshot pixel digest as a generic freshness token. A legitimate static Feed can render identical pixels across fresh captures; equality would incorrectly classify it as stale forever.

A valid freshness token should represent capture generation/provenance emitted by the same capture operation (for example a backend generation token or capture ID bound to the XML). If the pinned core artifact cannot expose such a token, fail closed or add the capability in shared core under its own contract and tests. Do not invent a consumer token whose equality means “screen content unchanged.”

The consumer still needs exact foreground + semantic verification; a changing token alone is never Feed proof.

## 5. Reboot callback roles

`reboot_and_restore` owns reboot, wait-for-device, boot completion, unlock, and rotation readiness. Consumer callbacks must preserve that ordering:

- `cleanup_before_reboot`: bounded app-specific cleanup only; no raw reboot, broad process kill, or attempt to prepare an unlocked post-boot UI.
- `recover_adb_after_reboot`: transport-only work that is valid before core unlock readiness; do not call a UI preparation routine here if it assumes an unlocked screen.
- `recover_post_reboot`: restore app/network state after core has proved unlock/readiness.
- `wait_for_proxy_ready_after_reboot`: prove readiness for the new boot identifier when a proxy marker/handshake exists.
- `verify_post_reboot`: exact final package/activity/semantic verifier; callback completion alone is not success.

Missing mandatory callbacks or readiness proof must fail closed. Never replace this with raw `adb reboot` plus a custom boot loop.

## 6. Safe startup-only production path

A startup/navigation-only verifier must branch before business construction:

- require explicit machine + serial target
- lazily import the business workbook loader only in normal mode
- validate only startup-safe config fields
- do not read mapping workbook, UID source, account identity, proxy credentials, or business state
- do not construct follow state, popup/input flow, switcher, or mode runner
- acquire only the exact device lease; never a workbook lease
- on success, write redacted PNG/XML/JSON evidence and release only the owned lease with release proof
- on failure, retain the owned failure lock according to the consumer/core policy

A dry-run and a startup-only run are different: dry-run must not touch the device; startup-only is a real, lock-protected device verification and therefore needs explicit live authorization.

## 7. Final verification matrix

Before release, run against the exact current tree and pinned artifact:

1. focused config/CLI/adapter/engine/lock tests
2. pinned-wheel focused tests with the artifact forced onto `PYTHONPATH`
3. full offline suite
4. compile/import checks
5. prohibited-pattern scan (`raw reboot`, direct ATX kill, raw subprocess transport, temporary production runner)
6. `git diff --check`, exact allowlist/status, and independent diff audit
7. only after approval and fresh authorization: production startup-only on one target with artifact readback and zero-Follow proof

Any source/test edit after a green command invalidates that command as final evidence for the current tree.