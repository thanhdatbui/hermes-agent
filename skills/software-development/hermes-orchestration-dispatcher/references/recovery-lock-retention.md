# Recovery lock retention & classification semantics (TikTok consumer)

Session 2026-08-06 — user chốt quyết định: **giữ lock khi MANUAL_REQUIRED/FINAL_BLOCKED** (chặn shift mới nhặt lại máy lỗi; phải can thiệp tay mới mở). **CHƯA implement** — là task COMPLEX (đụng core + flow + recovery + tests), cần plan (v4-pro) → Sol audit → implement (Luna/high hoặc session worker).

## Classification (`recovery_supervisor.py` `classify_incident` ~L1123)

3 nhánh:

| Nhánh | Điều kiện | `lock_safe` |
|---|---|---|
| DEFERRED_LOCKED | lock ACTIVE/FOREIGN/BUSY/UNVERIFIABLE (`lock_state` không thuộc `_SAFE_LOCK_STATES`, hoặc marker `_DEFERRED_LOCK_MARKERS` trong failure_signature/terminal_code) | False |
| MANUAL_REQUIRED | sensitive marker (`_SENSITIVE_MARKERS`: OTP/2FA/account/mailbox/captcha/workbook...) HOẶC final marker (`_FINAL_MANUAL_MARKERS`: FINAL_EXHAUSTED, LADDER_EXHAUSTED, ATTEMPT_CAP, UNKNOWN_CRASH, NO_HANDLER_IMPLEMENTED, LIVE_ATTEMPT_LEASE_MISMATCH...) | True |
| AUTO_RECOVERY_PENDING | lỗi thường (CAPTURE_INVALID, ADB, network, proxy...) | True |

- **`lock_safe=True` ≠ "giữ lock"** — nghĩa là không có lock active đang giữ máy; MANUAL_REQUIRED thả lock (để người can thiệp + vòng feed thử lại).
- `_lock_classification` (~L1102): lock uncertainty luôn thắng → DEFERRED_LOCKED, không caller nào reclaim được qua classification.
- Hằng số: `_SAFE_LOCK_STATES`, `_DEFERRED_LOCK_MARKERS`, `_SENSITIVE_MARKERS`, `_FINAL_MANUAL_MARKERS` (L1061-1082). `is_terminal_shift_status` (L106): status ∈ TERMINAL_SHIFT_STATUSES hoặc `skipped-*`/`unverified` = terminal.

## Ai sở hữu lock?

- **Flow** (`multi_machine_feed_session.py`) acquire/release — **recovery runtime CHỈ ĐỌC lock state, không acquire** (grep recovery_runtime/supervisor → 0 chỗ gọi `acquire_device_lock`).
- `_run_child` (~L725): `lock_holder = {"lease": device_lock}`; `release_recovery_lock()` → `lease.release()`; `reacquire_recovery_lock()` → `acquire_device_lock(status="running", bypass_proxy_readiness=True)` cho recovery-handoff.
- `recovery_lock_handoff.json` (flow viết, schema `tiktok-consumer-lock-handoff-v1`): `finish_succeeded`, `final_status`, `lock_paths` (present/status/owner_active/lock_id), `expected_terminal_status: released|handoff`.
- Lock file: `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json` + `serial_<serial>.lock.json`.

## Cross-shift re-pickup gap (lỗ hổng user phát hiện — lý do quyết định giữ lock)

- `RecoveryIncident.incident_key` (recovery_supervisor.py ~L1020) = `source? + schedule_day + shift + machine + account_row + failure_signature + artifact_dir`.
- `_is_terminal_incident` (recovery_runtime.py ~L629) = ledger có `VERIFIED_SUCCESS`/`FINAL_BLOCKED` cho **CÙNG incident_key**.
- → FINAL_BLOCKED chỉ terminal **TRONG CÙNG SHIFT**; shift kế tiếp (key khác vì shift/artifact khác) → `_is_terminal_incident`=False → **nhặt lại máy y hệt → thử lại 7 slot → lại FINAL_BLOCKED → lỗi không bao giờ tự sửa, tốn quota mỗi shift**. `already-terminal` trong log chỉ chặn trong shift (runtime quét nhiều vòng cùng shift).
- Trạng thái thực tế quan sát: máy 60/63/74 (`CAPTURE_INVALID` = lỗi thường → AUTO_RECOVERY_PENDING → 7 slot đều không sẵn sàng do hết quota → FINAL_BLOCKED → MANUAL_REQUIRED, `lock_safe=True`, lock trên đĩa KHÔNG TỒN TẠI).

## Hướng implement giữ lock (chưa làm — cần audit trước)

1. Core `device_lock.py` đã có status `blocked` trong `_DEVICE_LOCK_STATUSES` nhưng KHÔNG thuộc `_ACTIVE_DEVICE_LOCK_STATUSES` (`{"queued","running","recovery"}`) → `owner_active=False`. Cần cơ chế "blocked chặn shift tới" không chỉ dựa owner_active.
2. Flow: khi `finish_succeeded=False` → `set_status("blocked")` thay vì release hẳn (giữ marker), hoặc release nhưng để lại marker blocked.
3. Recovery `_block()` (FINAL_BLOCKED, recovery_runtime.py ~L2043): acquire lock `status="blocked"` nếu chưa có.
4. Shift mới `acquire_device_lock` phải TỪ CHỐI khi blocked, trừ `takeover_authorized=True` (can thiệp tay).
5. Fail-closed: blocked không tồn tại vô hạn (cần cách mở tay / thời hạn); `DeviceLockLease.release()` xóa file — cần path giữ marker.
6. Đụng core + flow + recovery + tests → COMPLEX: backup → v4-pro plan → **Sol audit (gate)** → implement → verify.

## Device-lock core semantics (`automation_core/device_lock.py`) — kiểm chứng 2026-08-06

- `_DEVICE_LOCK_STATUSES = {queued, running, recovery, handoff, blocked, temporarily_skipped}`; ACTIVE = `{queued, running, recovery}` → chỉ các status này `owner_active=true`.
- `DeviceLockLease.finish(succeeded=False)` → `set_status("handoff")`: **GIỮ file**, chỉ đổi status. Chỉ `release()` / `release_with_audit()` mới **XÓA file** (`_release_lease_paths` unlink + rollback). `release_with_audit(reason=...)` trả `DeviceLockReleaseAudit` (paths đã xóa).
- `skip_device(lease, reason=...)` (core ~L537): `set_status("temporarily_skipped")` + release_with_audit + artifact `device_skip.json` — pattern mẫu skip có audit.
- `acquire_device_lock(status="queued")` reservation: `_queued_promotion_payload` (~L565) claim lại chỉ khi cùng host + `owner_active=false` + status `queued` + **CÙNG run_id**; `_takeover_payload` (~L585) từ chối `temporarily_skipped`, reclaim blocked/handoff chỉ khi `takeover_authorized=True` + scope (`SAME_PROJECT_RECOVERY`/`FULL_SCOPE_TAKEOVER`) → **fail-closed tự nhiên cho "giữ lock blocked": shift tới không authorize → `DeviceLockUnavailable` → skip, không bao giờ tự reclaim**.
- **Vì sao máy fail bị MẤT lock** (nhầm lẫn trong session): `DeviceLockLease.finish(succeeded=False)` GIỮ file, nhưng scheduler skip path `multi_machine_feed_session.py:~1034` reserve xong thấy `_prior_target_evidence` outcome ≠ VERIFIED_SUCCESS → `reservation.release()` (**XÓA file**) + skip. `_prior_target_evidence` (~L293) đọc `recovery_lock_handoff.json` trong artifact dir, **KHÔNG đọc lock file trực tiếp** — lock còn mà handoff fail vẫn bị release.
- `recovery_lock_handoff.json` schema `tiktok-consumer-lock-handoff-v1`: `machine, account_row, handoff_required, finish_succeeded, final_status, lock_paths{path:{present,status,owner_active,lock_id}}, expected_terminal_status`.
- Pitfall Windows/git-bash: `tasklist //FI "PID eq N"` trả RỖNG dù process sống → dùng `wmic process where "ProcessId=N"`; `schtasks /query /tn <task> /xml` — `<Arguments>` escape `&amp;`, đọc bằng regex `<Arguments>(.*?)</Arguments>`; LastResult `267009`=đang chạy, `-2147020576`=task đã chạy (refused); lock file mất ≠ code lỗi (có thể do `reservation.release()` xóa).

## Tray integration (quyết định chờ user)

- `scheduler-tray.ps1` (TikTok feed) hiện KHÔNG quản lý `TikTokScheduleRecovery`/`TikTokScheduleRecoveryHealth` (grep 0 hit) — chỉ quản lý TikTokScheduler + Wake + proxy.
- 3 tray đang chạy: `scheduler-tray.ps1` (feed), `tiktok-scheduler-tray.ps1` (TikTok All/proxy, trong automation-core), `gmail-scheduler-tray.ps1` (register gmail). Các scheduler consumer khác (Tiktok_Reg, tiktok-log-in...) chạy `--live` không có tray riêng.
- Đề xuất (chờ user duyệt): tích hợp recovery vào `scheduler-tray.ps1` — cùng phạm vi, ít icon; menu "Dừng tất cả" nên hỏi riêng trước khi tắt recovery (lớp an toàn cuối).

## Runtime confirm orphan (đã chạy thành công 2026-08-06)

Lease cũ: parent 2476 dead, child 52164 alive, state=running, identity match 100% (start time/executable/binding/commandline/ppid). Trigger task `TikTokScheduleRecovery` → orphan bị dọn, watcher mới tự start (parent/child mới, lease mới), heartbeat 15s đều. Trigger lần 2 → từ chối (`-2147020576` = task đang chạy) — không double-run. Watcher tự đổi thế hệ sau khi child exit (task tự start lại) = hành vi chuẩn, không cần tay.
