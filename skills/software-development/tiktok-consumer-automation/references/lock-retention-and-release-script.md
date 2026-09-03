# Lock retention khi FINAL_BLOCKED + release script (2026-08-06)

Repo: `D:\Taadaa\tiktok-luot nuoi acc` (consumer), core đọc-only.
Task spec: `tasks/2026-08-06-retain-lock-on-final-blocked.md`.

## Chuỗi root cause — vì sao máy fail không giữ lock

1. `multi_machine_feed_session.py::_run_child` `finally` block gọi
   `lease.finish(succeeded=goal_completed)` — fail → `DeviceLockLease.finish(False)`
   → `set_status("handoff")` (KHÔNG xóa file, owner_active=false).
2. Nhưng scheduler reserve mới (`status="queued"` + run_id mới) gặp lock cũ:
   `_queued_promotion_payload` (device_lock.py:565) cho claim lại khi cùng host +
   `owner_active=false` + status `queued` + **cùng run_id** — run_id mới ≠ cũ nên
   KHÔNG promote; `_takeover_payload` (dòng 585) chỉ claim khi `takeover_authorized`.
3. Thực tế lock file máy 60/63/74 mất hẳn (không còn trên đĩa) — vì
   `reservation.release()` ở dòng 1034 (khi `_prior_target_evidence` outcome ≠
   VERIFIED_SUCCESS → release reservation + skip). Đây là nơi scheduler chặn
   shift tới khi prior handoff không success — nhưng chỉ dựa trên handoff artifact,
   KHÔNG phải lock file.

Kết quả: `incident_key` = `schedule_day+shift+machine+account_row+failure_signature+artifact_dir`
→ shift kế tiếp key khác → `_is_terminal_incident` (recovery_runtime.py:629, chỉ check
`VERIFIED_SUCCESS`/`FINAL_BLOCKED` cùng key) = False → cày lại 7 slot → FINAL_BLOCKED → lặp vô hạn.

## Fix implement

### 1. Flow `finally` (multi_machine_feed_session.py ~880)

```python
finally:
    lease = lock_holder.get("lease")
    if lease is not None:
        # pre-guard viết trước (succeeded=False)
        _write_recovery_handoff_evidence(..., succeeded=False,
            final_status="handoff" if goal_completed else "blocked",
            lock_status="blocked" if not goal_completed else "handoff")
        if goal_completed:
            lease.finish(succeeded=True)
        else:
            # Retain lock as blocked — shift tới không re-run target fail
            # owner_active stays False; acquire_device_lock refuses blocked
            # without explicit takeover authorization.
            lease.set_status("blocked")
        _write_recovery_handoff_evidence(..., succeeded=goal_completed,
            final_status="success" if goal_completed else "blocked",
            lock_status="released" if goal_completed else "blocked")
```

### 2. `_write_recovery_handoff_evidence` — thêm `lock_status`

- Param mới `lock_status: str = "handoff"` — **default phải "handoff"** để test cũ
  `test_recovery_handoff_evidence_records_terminal_lock_state` (kỳ vọng `expected_terminal_status: handoff`
  khi fail không truyền lock_status) không vỡ. Đặt "released" → test cũ fail
  (`'released' != 'handoff'`).
- Evidence thêm `"lock_status": lock_status`; `"expected_terminal_status": "released" if succeeded else lock_status`.

### 3. Script release `python_runner/scripts/release-device-lock.py`

Flow logic:
1. `device_lock_paths(machine, serial, lock_root)` → 2 file (machine + serial).
2. Không có file → exit 0 "no lock file present".
3. File không đọc được (JSON hỏng) → exit 4.
4. 2 file không nhất quán → exit 4.
5. `owner_active is True` → exit 3 từ chối (đang chạy thật).
6. Host khác + PID không chết → exit 3 (không reclaim remote).
7. `blocked`/`handoff`/`temporarily_skipped`/`queued` → release được.
   `running`/`recovery` + PID chết (stale) → release được.
8. Release qua `_release_lease_paths(stub, strict=False)` với stub
   `{host, pid, lock_id, lock_paths}` — core check `_owner_matches_claim`.
9. Audit 1 dòng vào `runs/device-lock-release-audit.jsonl`.

Exit codes: 0 = released/nothing, 3 = refused (active/foreign/alive), 4 = unreadable/inconsistent.

## Pitfalls

- **Windows PID liveness**: `os.kill(pid, 0)` với PID không tồn tại (999999) trả
  `PermissionError` (coi alive) → từ chối release sai. Fix: `tasklist /FI "PID eq X" /NH`
  (subprocess, timeout 10) + check `str(pid) in stdout`.
- **Test host giả**: lock test dùng host `"DESKTOP-TEST"` ≠ host thật → script từ chối
  (`lock owned by host ... refusing`) vì host khác. Test phải dùng `socket.gethostname()`.
- **Import scripts/**: không có `__init__.py` → test dùng
  `importlib.util.spec_from_file_location` + `exec_module`.
- **CRLF editing**: `multi_machine_feed_session.py` là CRLF — patch tool (fuzzy match) có thể
  chuyển toàn file sang LF → diff phình 1165 dòng. Fix: revert `git checkout -- <file>` rồi sửa
  bằng python `io.open(path, 'r', newline='')` + replace chuỗi có `\r\n` (`NL = chr(13)+chr(10)`),
  ghi lại với `newline=''`. Kiểm tra `git diff --stat` chỉ +vài dòng.
- **Pre-existing test fails**: `test_device_lock.py` 4 fail là pre-existing (fail cả khi `git stash`)
  do pytest dùng `automation_core` cài trong hermes venv (`...\hermes-agent\venv\Lib\site-packages`)
  thay vì bản local — KHÔNG phải lỗi thay đổi. Luôn stash-verify trước khi kết luận.

## Verify

- Ad-hoc script `hermes-verify-lock-retention.py` (8 checks): handoff blocked status,
  flow có `set_status("blocked")` + `finish(True)` + không còn `finish(succeeded=goal_completed)`,
  release blocked exit0/xóa, release active exit3/giữ, dry-run giữ file.
- Smoke thật: lock giả blocked → release exit 0 + audit; active → exit 3 + file còn.
- `PYTHONPATH=python_runner:. python -m pytest python_runner/tests/test_lock_retention.py -p no:cacheprovider -q` → 8 passed.
