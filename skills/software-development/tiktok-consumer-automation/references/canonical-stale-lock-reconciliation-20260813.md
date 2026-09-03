# Canonical stale-lock reconciliation (2026-08-13)

(Full content preserved in prior version — summary + new cross-link below.)

## Incident pattern

A canonical Tik2 batch launched many workers, then failed/was interrupted. The next batch reported `SKIPPED_LOCKED` for 37 machines. Inspection showed two lock classes:

- `tiktok-upload` locks with dead owner PIDs, including payloads still showing `status=running` and `owner_active=true`, plus inactive `handoff` locks.
- Foreign locks from other consumers/workflows, which must remain untouched.

The stale `owner_active` flag is not authoritative after a worker/launcher crash. Determine liveness with the core PID probe (`owner_process_alive` / Windows `tasklist` equivalent), not the persisted boolean alone.

## Correct canonical sequence

1. Run read-only inventory against the selected TikN workbook.
2. Build reconciliation candidates from eligible machines plus `SKIPPED_LOCKED` machines.
3. Reconcile only exact candidates through the guarded core API.
4. Re-run the same inventory after reconciliation; launch only from this fresh admission snapshot.
5. Stamp one batch ID into reconciliation, child environment (`CODEX_DEVICE_LOCK_RUN_ID`), lock payload, logs, and audit artifacts.
6. Wait for workers in background with completion notification; never use a foreground timeout for a long batch.

A reconcile operation after inventory but without a second inventory is ineffective: the stale first snapshot still carries the machines as skipped.

## Guarded reclaim contract

Reclaim only when all are true:

- project is exactly `tiktok-upload`;
- machine is in the current canonical candidate list;
- owner PID is independently proven dead;
- lock is not foreign, active, or an explicitly retained terminal/recovery lock;
- command metadata does not identify avatar smoke/targeted avatar, profile/account smoke, post/video recovery, preflight, or another consumer.

Use `acquire_device_lock(..., allow_takeover=True, takeover_scope=SAME_PROJECT_RECOVERY, takeover_authorized=True, takeover_reason=<batch-specific reason>, run_id=<batch_id>)`, then owner-matched `release_with_audit`. Never `Remove-Item`, `rm`, or broad glob deletion. Preserve machine and serial aliases as one transaction and verify the audit/released paths.

`automation-core 0.4.40` may not expose a public `inspect_device_lock`. Use its `device_lock_paths` for alias resolution and a read-only JSON inspection helper; keep mutation exclusively in the guarded acquire/release API. Do not assume an `open_failed_locked_lock` or `inspect_device_lock` symbol exists just because a newer core version has it.

## Preservation and evidence

Preserve foreign projects such as `tiktok-luot nuoi acc`, registration/login consumers, and unrelated avatar workflows. Preserve active PIDs and retained `blocked`/`failed_locked` states unless the operator explicitly authorizes a separate recovery action. Record target list, excluded list, PID liveness result, project/status, takeover reason, released aliases, and post-reconcile verification in a redacted audit artifact.

A worker failure should finalize its owned lock to inactive `handoff` rather than leave `running + owner_active=true`; successful workers release both aliases. A batch summary or exit code is not upload proof—independently verify report, accepted post evidence, and final lock state.

## Regression gates

Before live retry:

- focused lock/reconcile tests pass;
- full consumer suite passes or unrelated pre-existing failures are explicitly classified;
- Python compiles and PowerShell parses;
- dry reconcile/report-only path works;
- no real TikTok worker is running unexpectedly;
- `git diff --check` passes;
- no live run occurs until the canonical launcher, not a one-off Tik2 launcher, is verified.

---

## Lớp 2 — DEFERRED_LOCKED handoff-evidence gate (cross-link, 2026-08-13)

Dọn lock file (lớp 1 ở trên) **VẪN CHƯA ĐỦ** khi batch feed-session báo `skipped-device-locked` hàng loạt. Còn một gate fail-closed khác trong `python_runner/flows/multi_machine_feed_session.py`:

- `_prior_target_evidence()` `root.rglob("recovery_lock_handoff.json")` quét TOÀN BỘ artifact root (`.ai-runs`) — bất kể tuổi/run đã chết.
- Handoff payload `finish_succeeded != True` → `deferred-locked` → máy bị skip VĨNH VIỄN kể cả khi lock file đã sạch.
- Verify-success handoff (`finish_succeeded=true` + `expected_terminal_status=released` + lock release proof + run manifest success + swipes>0) KHÔNG chặn.

**Dọn đúng**: `scripts/reap-stale-handoff-evidence.py` (mỗi repo) move handoff `finish_succeeded != true` sang quarantine, GIỮ verified-success.

Chi tiết cơ chế + script + cron reaper + env checklist + thứ tự chẩn đoán skip-lock:
**`references/deferred-locked-handoff-gate-20260813.md` (skill `tiktok-feed-session`)**.
Reaper lock chuẩn: `scripts/reap-dead-owner-locks.py` (dùng `owner_process_alive`, move sang quarantine, idempotent; cron Hermes mỗi 30p).
