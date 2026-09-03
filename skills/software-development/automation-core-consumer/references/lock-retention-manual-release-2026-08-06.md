# Lock Retention + Manual Release — 2026-08-06

Repo `D:\Taadaa\tiktok-luot nuoi acc` (consumer). User: "nếu t không can thiệp thì lỗi đó chạy qua phiên mới, không bao giờ sửa được" → giữ lock khi FINAL_BLOCKED/MANUAL_REQUIRED.

## Vấn đề gốc

Trước fix: máy fail (CAPTURE_INVALID = lỗi thường → AUTO_RECOVERY_PENDING, lock_safe=True) → thử ladder 7 slot → hết slot → FINAL_BLOCKED → MANUAL_REQUIRED → **thả lock**. Vì `incident_key` bao gồm shift/artifact, shift hôm sau tạo key mới → `_is_terminal_incident` = False → nhặt lại y hệt → cày lại 7 slot, tốn quota, không bao giờ tự sửa.

Nguyên nhân: `lock_safe=True` (không lock đang giữ) bị hiểu nhầm là "an toàn để chạy" — nhưng thực ra nó chỉ nghĩa là không ai đang giữ máy. MANUAL_REQUIRED không giữ lock (để người can thiệp + vòng feed thử lại), nhưng không có cơ chế "đừng chạm lại máy này".

## Fix (consumer-scoped, không đụng core)

`python_runner/flows/multi_machine_feed_session.py`:
- `finally` block: `lease.finish(succeeded=goal_completed)` → tách nhánh:
  - success → `lease.finish(succeeded=True)` (release như cũ)
  - fail → `lease.set_status("blocked")` (giữ lock file, owner_active=false)
- `_write_recovery_handoff_evidence` thêm param `lock_status` (default "handoff" — giữ hành vi cũ khi không truyền).

Vì `blocked` không thuộc `_ACTIVE_DEVICE_LOCK_STATUSES` → `_queued_promotion_payload` = None → `acquire_device_lock` không takeover (trừ `takeover_authorized=True` từ user) → shift mới bị `DeviceLockUnavailable` → máy skip, không cày lại.

## Script release-device-lock.py

```bash
PYTHONPATH=python_runner:. python python_runner/scripts/release-device-lock.py --machine 60
PYTHONPATH=python_runner:. python python_runner/scripts/release-device-lock.py --machine 60 --dry-run
PYTHONPATH=python_runner:. python python_runner/scripts/release-device-lock.py --machine 60 --serial <serial> --lock-root <path>
```

Exit codes:
- `0` — released (blocked/handoff/temporarily_skipped/queued, hoặc stale running với PID chết); hoặc không có lock.
- `3` — từ chối: active lock (`owner_active=true`), hoặc host khác + PID alive/unknown.
- `4` — lock payload unreadable / 2 lock files inconsistent / status unknown / release exception.

Audit: `python_runner/runs/device-lock-release-audit.jsonl` (event, machine, status, pid, host, reason, released_paths).

## Windows PID check — tasklist

```python
# os.kill(pid,0) KHÔNG đáng tin trên Windows: PID không tồn tại vẫn có thể
# raise PermissionError (coi alive sai) -> fail-closed sai, không release được
# lock stale. Dùng tasklist:
subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, timeout=10)
alive = str(pid) in (result.stdout or "")
```

## Core API đã dùng (đọc-only, không sửa core)

- `device_lock_paths(machine=, serial=, lock_root=)` → list[Path] (machine + serial alias)
- `_safe_read_json(path)` → dict | None
- `_release_lease_paths(lease, strict=False)` → (released_paths, payload) — yêu cầu lease có `host/pid/lock_id/lock_paths`. Dùng stub class, KHÔNG xóa file tay.
- `_DEVICE_LOCK_STATUSES` — set status hợp lệ; `_RETAINED_STATUSES = {blocked, handoff, temporarily_skipped, queued}`.

## Tests (`python_runner/tests/test_lock_retention.py`, 8 tests)

- handoff evidence ghi `expected_terminal_status=blocked` + `lock_status=blocked` khi fail; `released` khi success
- release script: blocked → exit 0 + xóa file; active → exit 3 + giữ file; dry-run → giữ file; unreadable → exit 4; stale running dead-PID → exit 0
- Test dùng `importlib.util.spec_from_file_location` load script (scripts/ không phải package — không import được qua `from scripts.x import y`)
- Mock host = `socket.gethostname()` thật (host khác bị từ chối)

## Verify

- `PYTHONPATH=python_runner:. python -m pytest python_runner/tests/test_lock_retention.py python_runner/tests/test_multi_machine_feed_session.py -p no:cacheprovider -q` → 9 passed
- Ad-hoc verify script (`hermes-verify-*.py` trong Temp): 8/8 checks
- Smoke: blocked lock → release exit 0 + audit; active lock → từ chối exit 3 + file còn nguyên
- 4 fail `test_device_lock.py` là **pre-existing** (fail cả khi stash — venv hermes-agent site-packages có automation_core cũ shadow bản local)

## Lưu ý

- Lock file dùng CRLF — sửa bằng python `io.open(newline='')` + `NL='\r\n'`, match đúng (patch tool đổi LF→CRLF làm diff phình cả file).
- Test cũ `test_recovery_handoff_evidence_records_terminal_lock_state` kỳ vọng `expected_terminal_status="handoff"` — giữ default `lock_status="handoff"` để không phá.
- `scripts/` không có `__init__.py` — test load script qua spec, không import package.
