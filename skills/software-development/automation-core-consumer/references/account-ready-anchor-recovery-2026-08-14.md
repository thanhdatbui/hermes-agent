# ACCOUNT_READY-only failure: SWITCHER_ANCHOR_AMBIGUOUS masks ADB transport failure (2026-08-14, tiktok-follow máy 1)

## Sequence (user-authorized, no Follow)
1. Guarded FULL_SCOPE_TAKEOVER of the dead retained lock (protocol v2, `owner_active=false`) via `acquire_device_lock` + `release_with_audit` — both aliases rewritten with `takeover_from` provenance, then absent (recipe: `stale-lock-takeover-startup-only-2026-08-14.md`; re-ran cleanly a second time).
2. Canonical run: `follow_runner.run_follow --machine 1 --config follow_runner/config.example.yaml --account-ready-only --account-row-index 1` (pinned wheel PYTHONPATH, no workbook lock).
3. Result (twice — runs `follow-1-8e236b4ce294`, `follow-1-df42727ac4ee`): `MANUAL_REVIEW`, `details.account_ready_error = {type: AccountSwitcherError, code: SWITCHER_ANCHOR_AMBIGUOUS}`, `followed=[]`, lock retained `retained_handoff`/`blocked`, no success artifact.

## Root cause — the surfaced code is NOT the real cause
- Persistent-capture evidence in `%TEMP%\automation-core-ui-capture\`:
  `ui_capture_ad158…` VERIFIED_SUCCESS 11 nodes (Feed) → `ui_capture_ce1b0c…` VERIFIED_SUCCESS 20 nodes (Profile) → `ui_dump_error_170c…` FINAL_BLOCKED `ADB_TRANSPORT_LOST_AFTER_VERIFIED_PERSISTENT_CAPTURE` (transport_failure_signature `ADB_TRANSPORT_TIMEOUT`).
- The machine DID reach Profile; the switcher-open dump then timed out at the ADB transport level. Core `account_switcher._dump()` catches and re-raises `AccountSwitcherError(UI_DUMP_FAILED)`; `open_switcher` finds no anchor → `SWITCHER_ANCHOR_AMBIGUOUS`. Post-failure screencap: TikTok Feed `Đề xuất`, switcher closed, no login/OTP/CAPTCHA — machine healthy.
- **Consumer masking**: `FollowAdapter.dump_ui()` wraps capture exceptions into a *codeless* `FollowAdapterError("structured UI capture failed: TimeoutError")`, so the run result only ever shows core's `SWITCHER_ANCHOR_AMBIGUOUS`. Always read the `ui_dump_error_*.json` artifacts to get the true signature.

## Artifact facts (so future probes don't re-derive them)
- `ui_capture_*.json` = event traces only (outcome, xml_bytes, node_count under `attempts[]`); raw XML is NOT persisted in them.
- `ui_dump_error_*.json` carries `failure_signature` + `transport_failure_signature` — this is where ADB transport truth lives.
- The capture dir is shared by ALL concurrent sessions (thousands of files/minute); isolate a run by lock JSON `started_at` (UTC) mapped to local (+7) plus the run_id in FOLLOW_RESULT.
- `runs/account-ready/live-machine-1-slot-1-*.log` holds only FOLLOW_PLAN/FOLLOW_RESULT; no step log. Failure runs write no success artifact (by design).

## Fix (consumer-only, in scope)
`follow_engine.py::FollowEngine._canonical_switch_verify`:
```python
try:
    return _run_chain()
except AccountSwitcherError as exc:
    if exc.code != "SWITCHER_ANCHOR_AMBIGUOUS":
        raise
    if not self._run_recovery_ladder():   # B1 persistent + B2 relaunch; no reboot, no coordinate tap
        raise                             # ladder fail = terminal, re-raise original signature
    return _run_chain()                   # exactly ONE canonical retry
```
- Only the single ambiguous-anchor signature triggers the ladder; every other `AccountSwitcherError` code re-raises untouched (no blind-retry loop).
- Docs record `tiktok-switcher-anchor-bounded-recovery-20260814` in `docs/ui-compatibility.md`; regression test `test_switch_anchor_ambiguous_runs_bounded_ladder_once_then_canonical_retry` in `test_follow_engine.py`. Full consumer suite 233 passed.

## TDD test pitfalls (all hit in the wild)
- Patch `automation_core.tiktok.account_switcher` module attrs (open/select/verify) keeping the REAL `verify_selected_account` against a fake post-select XML; count ladder via monkeypatched `FollowEngine._run_recovery_ladder`.
- "Fail once then succeed" fake: a closure capturing a module-level `switcher_failures` counter is SHARED across engine instances — the second engine's run sees failures already exhausted. Reset `calls` AND the counter (or make it per-engine) before each sub-case.
- The first FAILING `open_account_switcher` call is still recorded, so the GREEN call trace is `[open(fail), open(ok), select, verify]`, NOT `[open, select, verify]`.
- Ladder-fail case asserts `calls == ["open"]` (no retry after a failed ladder) and `ladder_calls == ["ladder"]`.

## Revalidation (status at session end)
- Second live run after the fix still returned `SWITCHER_ANCHOR_AMBIGUOUS`. Per repo contract: NO blind retry. Next step is fresh `ui_dump_error_*.json` evidence around the run window (23:42–23:53 local) to decide whether the ladder ran and failed again on transport, or the anchor genuinely cannot resolve on this device's Profile; keep the retained `blocked` lock until a decision. Do not patch further without new evidence.
