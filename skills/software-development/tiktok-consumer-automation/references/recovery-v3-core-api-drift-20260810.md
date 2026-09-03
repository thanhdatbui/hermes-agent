# Recovery v3 core-API drift: B3 soft reboot blocked by consumer↔core mismatch (2026-08-10)

Evidence from live recovery v3 on Tik1 machines 5/35/70 (HEAD `9301585`).

## Symptom (log, machine 5, right at the B3 stage)

```
=== SOFT REBOOT RECOVERY (AUTOMATION-CORE) ===
[ERROR] tiktok_workflow.state_machine: [REBOOT] Guarded reboot recovery failed:
  reboot_and_restore() got an unexpected keyword argument 'wait_for_proxy_ready_before_post_reboot'
[OPEN_TIKTOK] Ladder cạn (relaunch x2 + soft-reboot đã thử); thử tầng cuối coordinate fallback theo visual evidence
```

Result: machine falls through to coordinate fallback → FINAL_BLOCKED → MANUAL_REVIEW.
`--allow-device-reboot-recovery` was present, so the flag was NOT the problem — the
installed core simply does not have the parameter the consumer passes.

## Root cause

- HEAD `9301585` ("B3 soft reboot: bo qua DEVICE_LOCK_PROXY_HANDOFF_UNSUPPORTED khi
  gan-proxy watcher quan ly") bypasses the proxy-handoff fail-closed path when the
  watcher runs, then calls `reboot_and_restore(..., wait_for_proxy_ready_before_post_reboot=...)`.
- venv-core024 has automation-core **0.4.40**, whose `reboot_and_restore` parameter is
  named `wait_for_proxy_ready_after_reboot` (rename happened in a later core).
- Every machine reaching B3 dies with the same TypeError. This is a **new failure
  signature** → per policy: do NOT hot-edit consumer code; report and reconcile the
  core pin before retrying.

## Venv probe that catches this BEFORE launch (mandatory guard)

Hermes terminal shell exports PYTHONPATH/PYTHONHOME, so a bare `python -c "import
automation_core"` (even via the venv interpreter) resolves automation-core from the
hermes-agent venv (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`)
and gives a FALSE signature. Probe must strip env and verify `__file__`:

```bash
env -u PYTHONPATH -u PYTHONHOME "/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -c \
  "import automation_core, inspect; from automation_core.device_recovery import reboot_and_restore; \
   print(automation_core.__file__); print(list(inspect.signature(reboot_and_restore).parameters))"
```

Observed (correct venv):
- `core_file D:\CodexRuntime\tiktok-video\venv-core024\Lib\site-packages\automation_core\__init__.py`
- params include `wait_for_proxy_ready_after_reboot` (NOT `..._before_post_reboot`)

Version check: `import importlib.metadata as m; m.version("automation_core")` → `0.4.40`;
dist-info `automation_core-0.4.40.dist-info`. Repo pin file `requirements-automation-core.txt`
may point at a DIFFERENT wheel (e.g. 0.4.35) — pin file ≠ installed venv; always probe the venv.

## Expected watcher-managed B3 markers (HEAD 9301585, what SUCCESS of the bypass looks like)

1. `_reserve_proxy_recovery_handoff` returns `DEVICE_LOCK_PROXY_HANDOFF_UNSUPPORTED`
2. Bypass logs: `reason="proxy_handoff_skipped_watcher_managed"`, `proxy_handoff_state="OWNER_PAUSE_SKIPPED"`
3. `=== SOFT REBOOT RECOVERY (AUTOMATION-CORE) ===` then `[REBOOT] ...` outcome
4. Post-reboot readiness: `wait_for_proxy_ready(serial, post_boot_id, timeout=90, poll_interval=30)`
   with context `after reboot (watcher-managed)` (gan-proxy watcher polls 30s, re-assigns VPN, publishes proxy_ready)
5. `require_android_vpn(adb, required=True)` passes

## Ladder log-claim pitfall (read the real markers, not the wording)

- v2 run (HEAD 6ad3cfd) printed `Ladder cạn (relaunch x2 + soft-reboot đã thử)` with
  **zero** actual reboot markers in the whole log — the wording fired while the soft
  reboot had silently failed/skipped earlier.
- Rule: only count B3 as exercised when `=== SOFT REBOOT RECOVERY (AUTOMATION-CORE) ===`
  and a `[REBOOT]` result line appear. Same discipline applies to ATX-kill
  (`uiautomator dump fail liên tiếp; đã ATX-kill recovery (ladder bước 1)`) and relaunch
  (`Force-stop + relaunch N/2` + `[TIKTOK_STARTUP] force_stop_app: success`).

## Guard checklist before launching a full-ladder recovery

1. `git rev-parse --short HEAD`; read the HEAD commit message — does it touch
   `reboot_and_restore` / proxy-handoff / ladder? If yes, run the venv probe.
2. Probe venv signature with `env -u PYTHONPATH -u PYTHONHOME`; compare every
   keyword the consumer passes (grep `reboot_and_restore(` in `state_machine.py`).
3. Mismatch → stop, report signature + this reference, do not hot-edit.
4. Only after params line up, archive stale locks and launch workers.
