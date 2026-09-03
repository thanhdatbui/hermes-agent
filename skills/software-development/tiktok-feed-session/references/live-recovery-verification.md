# Live recovery verification recipe

Use this after a consumer-local popup/recovery change. The key rule is **offline green is not completion**: run the affected machines and verify their final state.

## Bounded sequence

1. Run the focused + full offline suite, `py_compile`, and `git diff --check`.
2. Inspect target machine and serial locks. Preserve JSON evidence. Do not touch `running` or `recovery` locks.
3. If the user authorized the exact rerun and a target is `blocked`/`handoff` with `owner_active=false`, use the runner's guarded `--full-scope-takeover` for only those machines. Do not delete lock files manually.
4. On Windows Git Bash, prevent path conversion and verify the intended shared core before launch:

```bash
MSYS_NO_PATHCONV=1 \
PYTHONPATH='D:\\Taadaa\\automation-core\\src' \
D:/CodexRuntime/tiktok74-core0411-venv/Scripts/python.exe -c \
'import automation_core; from automation_core.device_lock import FULL_SCOPE_TAKEOVER; print(automation_core.__file__, FULL_SCOPE_TAKEOVER)'
```

5. Use a bounded recovery smoke, normally `--recovery-test-swipes 1..3`, `--max-workers` limited to the named targets, and the explicit safety flags. Avoid like/follow unless requested.
6. Inspect every target independently:
   - `summary.txt`: key/value text, not JSON; require `final_status: success`, expected swipe count, and no unresolved stop reason.
   - `run_manifest.json`: blocker taxonomy and final per-target status.
   - `log.jsonl`: capture/focus/feed evidence, recovery ladder actions, popup handler order, and any transient degraded/manual events.
   - `recovery_lock_handoff.json`: `finish_succeeded=true`, `final_status=success`, and both machine and serial lock paths absent.
7. Scan source and artifacts for forbidden stale selectors. A dynamic handler that still emits an old literal in rule metadata/logs is not complete.

## CTA-specific evidence

For TikTok Shop CTA:

- `drain_known_popups` must run before the blind checkpoint and attempt the bounded swipe first.
- Swipe success requires recapture evidence: TikTok focus, known feed, no sensitive marker, and neither fullscreen Shop nor exact `Mua ngay` + `Đóng` remains.
- Only the fallback may call `detect_tiktok_shop_cta_popup` and use its current `close_element`; it must never tap `Mua ngay`.
- Test at least the observed dynamic pairs (`hyq`/`hyw` and `hwh`/`hwn`) and assert no old hardcoded ID remains in production rule metadata.

## Evidence from the 2026-08-09 scoped run

The run used the named machines 4, 7, and 19 with three recovery-test swipes. Batch exit was success and each handoff recorded released machine+serial locks. Machine 4 and machine 19 had transient capture/degraded events but reached final feed success; machine 7 reached feed success. This illustrates why the per-machine artifact review is mandatory rather than relying on the batch exit line alone.

## Common launch blocker

If the runner fails before device work with an import such as `FULL_SCOPE_TAKEOVER` missing, stop and fix the Python import path/version first. Do not retry the same command; the consumer venv may contain an older core while the repository source has the required lock API.
