# VPN gate in `_handle_resolve_device` (Phương án A) — Tiktok-video 2026-08-15

Session detail behind `vpn-pattern.md` → "Worker-side fail-closed VPN gate".
Implements the user's APPROVED plan: live TikTok upload workers must fail closed
when the device has no VPN, at RESOLVE_DEVICE, before any serial/profile
resolution or TikTok UI action.

## Files touched (3)

| File | Where | What |
|---|---|---|
| `scripts/tiktok_workflow/state_machine.py` | `_handle_resolve_device`, L2012-2029 (first lines after `device_id = ...`) | fail-closed VPN gate |
| `docs/tiktok-ui-compatibility.md` | `COMPAT-VPN-GATE-001` before `## Checklist review selector/fallback` | registry entry |
| `tests/test_tiktok_workflow.py` | `TestStateMachine`, right after `test_acquire_lock_reconciles_stale_proxy_marker_with_live_vpn` | 3 regression tests |

Working tree was ALREADY dirty before the task (COMPAT-AVATAR-011 in
state_machine.py, plus ps1/py/JSON changes) — the VPN diff is only the
L2012-2029 hunk. Never `git add .`; coordinator stages scoped files.

## Exact code (final, verified)

```python
        device_id = self.context.config.get("device_id", "")

        # VPN gate (Phương án A): bắt buộc VPN CONNECTED trước khi resolve
        # serial/profile. Fail-closed — thiếu VPN => MANUAL_REVIEW.
        if not self.context.dry_run and device_id:
            adb_path = self.context.config.get("adb_path")
            adb_kwargs = {"serial": device_id}
            if adb_path:
                adb_kwargs["adb_path"] = str(adb_path)
            try:
                require_android_vpn(
                    AdbClient(**adb_kwargs),
                    required=True,
                )
            except Exception as e:
                raise WorkflowError(
                    WorkflowState.RESOLVE_DEVICE,
                    "VPN required before TikTok run",
                    "VPN_REQUIRED_NOT_CONNECTED",
                ) from e

        row_serial = str((self.context.account_row or {}).get("device ID") or "").strip()
```

`require_android_vpn` and `AdbClient` are already imported at the top of
state_machine.py (`from automation_core.adb import AdbClient`,
`from automation_core.preflight import require_android_vpn`). `WorkflowError`
takes `(state, message, error_code)`; `WorkflowState.RESOLVE_DEVICE`
transitions → MANUAL_REVIEW.

## Why RESOLVE_DEVICE, not ACQUIRE_LOCKS

`_handle_acquire_locks` in this repo is a lockless no-op ("bỏ hết cơ chế lock",
2026-08-14) that returns early — a VPN gate there would never run for live
workers. RESOLVE_DEVICE always runs for live uploads and sits before any
workbook/video/UI work.

## Regression tests (3, all PASS)

```python
def test_resolve_device_requires_vpn_when_ready_marker_exists(self, monkeypatch):
    # mock state_machine.AdbClient (capture kwargs) + state_machine.require_android_vpn
    # -> SimpleNamespace(allowed=True); StateContext(config={"device_id": "serial-8",
    # "adb_path": "custom-adb.exe"}, account_row={"device ID": "serial-8"}, dry_run=False)
    # assert _handle_resolve_device() is True; adb_kwargs == {"serial": "serial-8",
    # "adb_path": "custom-adb.exe"}; checkpoint["device_id"] == "serial-8"

def test_resolve_device_fails_closed_when_vpn_missing(self, monkeypatch):
    # from automation_core.preflight import ConsumerPreflightError  <-- NOT from state_machine
    # mock require_android_vpn to raise ConsumerPreflightError
    # with pytest.raises(WorkflowError) as e: handler
    # assert e.value.error_code == "VPN_REQUIRED_NOT_CONNECTED"
    # assert e.value.state == WorkflowState.RESOLVE_DEVICE

def test_resolve_device_skips_vpn_gate_on_dry_run(self, monkeypatch):
    # dry_run=True -> handler True, require_android_vpn NEVER called (calls == []),
    # checkpoint still set
```

Mock seam: `monkeypatch.setattr(state_machine, "require_android_vpn", ...)` and
`monkeypatch.setattr(state_machine, "AdbClient", FakeAdb)` — module-level, like
the `test_acquire_lock_reconciles_stale_proxy_marker_with_live_vpn` and
`_soft_reboot_recovery` tests.

## Verification (real runs)

- Targeted: `env -u PYTHONPATH -u PYTHONHOME python -m pytest tests/test_tiktok_workflow.py -q -k "resolve_device"` → `3 passed, 356 deselected, 1 warning in 0.84s`
- Full suite: `4 failed, 355 passed` (baseline before change was `4 failed, 352 passed`; the same 4 pre-existing lock-related failures — no new failures).
- `git diff --check` → exit 0.
- NO commit, NO git add (per task: coordinator verifies/audits/commits).

## Pitfalls hit

1. `search_files` tool fails on this host for `D:\...` paths (`IO error: The
   system cannot find the path specified`) — fall back to `cd /d/Taadaa/... &&
   grep -rn` / `sed` in terminal. Already documented in
   `tiktok-consumer-automation` ("Pitfall search_files không duyệt được drive D:").
2. `ConsumerPreflightError` is NOT importable from `tiktok_workflow.state_machine`
   — import from `automation_core.preflight`. First test run failed with
   ImportError; fixed by moving the import. This is the durable lesson (also in
   vpn-pattern.md).
3. CRLF everywhere: state_machine.py, tests, and docs are all CRLF. Use
   `io.open(path, "r", encoding="utf-8", newline="")` + count-assert +
   replace + write with `newline=""`, and write block strings with explicit
   `\r\n`. Never the `patch` tool for large CRLF insertions (known
   indentation-mangling pitfall in this repo).
4. `.pytest_cache` Permission-denied warning is benign and pre-existing; use
   `-p no:cacheprovider` or ignore.
5. Ad-hoc verification loop: system requires a `hermes-verify-*` tempfile probe
   under `%TEMP%` after edits — pattern in
   `tiktok-consumer-dev` → `references/ad-hoc-verify-script-pattern.md`. Run
   with clean env (`env -u PYTHONPATH -u PYTHONHOME`), `sys.path.insert` for
   `scripts/`, restore monkeypatched module attrs, delete the tempfile.
