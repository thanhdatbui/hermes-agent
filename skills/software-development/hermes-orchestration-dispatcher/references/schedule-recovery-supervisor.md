# Schedule Recovery Supervisor — system map & audit findings

Trạng thái: 2026-08-04. Repo: `D:\Taadaa\tiktok-luot nuoi acc` (TikTok consumer).
Hệ thống tự recovery schedule đã build (các file dưới chưa commit/untracked tại thời điểm map này viết). Task `TikTokScheduleRecovery` hiện **Disabled** (xác minh bằng `schtasks /query /tn ... /fo LIST /v` → Status: Disabled) — action args `-Dispatch -EnableLiveRecovery` chỉ là action, KHÔNG phải trạng thái enabled.

## Files & vai trò

| File | Vai trò |
|---|---|
| `python_runner/scheduler/recovery_supervisor.py` | State machine `DETECTED → CLASSIFIED → RECOVERY_RESERVED → RECOVERING → RECAPTURED → RETRYING → VERIFIED_SUCCESS/FINAL_BLOCKED`. Ladder Luna/high ×5, advisor Terra/Sol read-only. |
| `python_runner/scheduler/recovery_runtime.py` | Watcher `--watch --poll 15s`; `ScheduleRecoveryRuntime.run_once()`; executor adapters (repair/advisor/audit/live); `verify_recovery_artifact()`. |
| `python_runner/core/capture_recovery.py` | Handler registry capture/ADB/reboot recovery (8k+ dòng, consumer-local, không đụng automation-core). |
| `scripts/run-schedule-recovery-watch.ps1` | Wrapper → `python -m scheduler.recovery_runtime --watch --dispatch [--enable-live-recovery]`. |
| `scripts/register-scheduler-task.ps1` | Đăng ký task `TikTokScheduleRecovery` (AtLogOn; `-EnableAutonomousRecovery` → `-Dispatch -EnableLiveRecovery`). |
| `tasks/2026-08-04-autonomous-schedule-recovery.md` | Spec offline-first: 3 shift 06:00/12:00/17:00, cap 6 meaningful (1 detect + 5 live), verifier proof, audit gate. |
| `reports/hermes-recovery-review.md` | Review tổng (verdict, điểm hở, workflow 7 live retry đề xuất). |

## Paths & proof chain

- Ledger: `python_runner/runs/schedule-recovery-ledger.jsonl` — event có `incident_key` dedup; `meaningful_attempts()` đếm `LIVE_RETRY` theo machine+failure_signature; cap bền qua restart (đọc lại ledger mỗi slot).
- State/log: `python_runner/runs/scheduler-state.json` + `scheduler.jsonl` (JSONL per-line; record có `artifact_root`, `account_row`, `multi_machine_summary`).
- Proof chain: `recovery_lock_handoff.json` (schema `tiktok-consumer-lock-handoff-v1`) do `python_runner/flows/multi_machine_feed_session.py` viết sau lock finalization → `verify_recovery_artifact()` đòi: `finish_succeeded=true`, `final_status=success`, summary `total_swipes_completed` 1-3, `lock_paths` present=false hết. Chỉ bind `machine`, KHÔNG bind `account_row` (xem blocker #3).
- Audit routing: `D:\Taadaa\tools\invoke-opencode-audit.ps1` → `OPENCODE_AUDIT`; fallback Codex Sol read-only → `CODEX_FALLBACK_AUDIT`. Claude chỉ hard-trigger quota-gated (`claude-quota-preflight.ps1`), không gọi trực tiếp.
- Task đang chạy: `TikTokScheduleRecovery` với `-Dispatch -EnableLiveRecovery` (autonomous recovery active).

## Codex fallback audit 2026-08-04 — 3 blocker chưa fix (chặn merge)

Nguồn: `reports/codex-fallback-audit/recovery-final-audit-readable.txt` (bản `-readable` có file:line — giá trị hơn bản raw `.txt` cùng thư mục; bản raw chỉ REJECT do thiếu bằng chứng, không có lỗi cụ thể).

1. **Crash window trước khi ghi ledger**: `live_executor` chạy tại `recovery_runtime.py:394`, `LIVE_RETRY` ghi sau tại :403 → process chết giữa 2 dòng thì restart chạy lại slot đã dùng, vượt 5 live. Test restart chỉ giả lập LIVE_RETRY đã ghi hoàn chỉnh (`test_recovery_supervisor.py:286`) nên không bắt được. Fix: ghi LIVE_RETRY/state atomic TRƯỚC live side effect.
2. **PATCH_READY không cưỡng chế ở mọi live-capable boundary**: runtime tổng quát và `RecoverySupervisor.run()` chỉ tin `patched=True` (`recovery_runtime.py:369`, `recovery_supervisor.py:372`); executor tùy biến có thể đưa tới live mà không có `decision == PATCH_READY`.
3. **Verifier bypass + thiếu bind account_row**: `RecoverySupervisor.run()` chấp nhận `bool(live["verified"])` thay vì artifact verifier (`recovery_supervisor.py:387`); verifier chuẩn chỉ bind `machine` (`recovery_runtime.py:137`) → target identity proof chưa đủ.

## Kiến trúc CHỐT (sau phản biện Codex vòng 2, 2026-08-04)

Hermes ban đầu đề xuất hybrid (Task Scheduler nền + Hermes cron supervisor). Codex phản biện → **Hermes rút lại, chốt**:

- **Windows Task Scheduler = control plane DUY NHẤT** (tránh split-brain lock/cap/verifier). Watcher `recovery_runtime.py --watch --poll 15s` làm phát hiện/ladder/audit/live verify.
- **Hermes chỉ review/report**: đọc ledger → viết `reports/*.md` / dashboard / notification. KHÔNG cron supervisor poll state, KHÔNG gọi live runner, KHÔNG Claude escalation mặc định khi FINAL_BLOCKED (Claude chỉ qua quota-gated wrapper khi hard trigger parent policy).
- **Distinct-evidence gate** (slot ≥6): advisor trả JSON `evidence, hypothesis, action, verifier, strategy_id`; fingerprint canonical mới + evidence recapture manifest/hash gắn target. KHÔNG dùng mtime đơn thuần (log chép lại làm mtime đổi), KHÔNG yêu cầu audit label khác lần trước (provider audit có thể vẫn là OpenCode).
- **Heartbeat**: KHÔNG đặt `ExecutionTimeLimit` ngắn (ladder 7 lượt + audit hợp lệ lâu). Thêm health task Windows riêng, rẻ, chỉ đọc heartbeat/PID → restart watcher khi stale; health task không đọc/ghi incident ledger và không gọi live runner nên không thành control plane thứ hai.
- **Ladder 7 theo user**: `Luna direct → Terra/high → Terra/xhigh → Terra/max → Sol/high → Sol/xhigh → Sol/max`. Luna/high luôn implement + live; Terra/Sol advisor read-only. Không duplicate Sol/xhigh, không dùng ultra. Offline revisions (≤3/strategy) không tiêu live attempt.
- Thứ tự build: fix C1-C3 + regression tests → nâng policy/constants/ladder/tests 5→7 live → canonical strategy/evidence manifest gate + Windows health task → focused tests/compile/diff + independent read-only audit → CHỈ khi pass mới enable/start-test `TikTokScheduleRecovery`.

## Shared review-file rebuttal loop (Codex ↔ Hermes)

- Codex tự append "Phản hồi Codex" vào cùng `reports/*.md` (không tạo file mới). Hermes phải **đọc lại file trước mỗi patch** (file bị sửa ngoài phiên → `_warning: modified since last read`; bỏ qua sẽ patch nhầm/sót).
- Phản biện phải **evidence-backed từng luận điểm** (bảng "Luận điểm Codex | Quan điểm sau phân tích | Quyết định"), thừa nhận sai khi Codex đúng (vd: đòi "audit label khác" là sai; distinct-evidence dùng fingerprint). User yêu cầu ghi phản biện luôn vào file, không chỉ trả lời chat.
- Cẩn thận patch giữa bảng: replace mất header section (`## 2.` bị nuốt) — kiểm tra lại grep `^## ` sau mỗi patch.

## Vận hành 2026-08-06 (sau khi orphan fix runtime-confirmed)

- **Sau reboot mọi task tự bật là ĐÚNG thiết kế** — tất cả TikTok tasks (`TikTokScheduler`, `TikTokScheduleRecovery`, `TikTokScheduleRecoveryHealth`, `TikTokSchedulerTray`, `TikTokAllSchedulerTray`, `TikTokSchedulerWake`) cấu hình trigger **AtLogOn + StartWhenAvailable**. User chốt: **giữ nguyên, KHÔNG tắt** sau reboot (đã hỏi trực tiếp). Watcher recovery tự start thế hệ lease mới sau reboot, không cần tay — xác nhận bằng `wmic os get lastbootuptime` + lease mới (lease_id khác, heartbeat đều).
- **Device locks** ở `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json` + `serial_<serial>.lock.json` (cùng lock_id). Target `MANUAL_REQUIRED`/`FINAL_BLOCKED` thường có `recovery_lock_handoff.json` ghi `owner_active: false` → lock bị **xóa khỏi đĩa** → máy KHÔNG bị khóa, vòng feed tới tự nhặt lại. Lock còn active thật = `owner_active: true` + PID còn sống (vd `machine_1`). Đừng kết luận "đang bị khóa" từ handoff file cũ — check đĩa.
- **Tray `scheduler-tray.ps1` KHÔNG quản lý `TikTokScheduleRecovery`/`TikTokScheduleRecoveryHealth`** (grep toàn file rỗng) — chỉ quản lý TikTokScheduler + Wake + proxy. User đang cân nhắc tích hợp recovery vào tray feed (chưa chốt 2026-08-06). Nếu tích hợp: giữ fail-closed — "Dừng tất cả" nên hỏi riêng trước khi tắt lớp recovery.
- Các scheduler consumer khác (`Tiktok_Reg`, `tiktok-log-in`, `tiktok-add-bao-mat-f2a`, `add mail khoi phuc`) cũng tự bật `--live` sau reboot — mỗi cái có task riêng, không nằm trong tray feed.

## Pitfall

- **Task Scheduler state ≠ action args**: đọc trạng thái task bằng `schtasks /query /tn '<task>' /fo LIST /v` → `Status:`/`Scheduled Task State:` (Disabled/Ready/Running) hoặc XML `<Enabled>`. Action args (`-Dispatch -EnableLiveRecovery`) chỉ là lệnh chạy, KHÔNG cho biết task có enabled hay không — đã nhầm lẫn ở session 2026-08-04 (tưởng "đang live" nhưng thực tế Disabled).
- Khi user nói "đọc phản hồi codex trong file": audit output ở `reports/codex-fallback-audit/` (và `reports/opencode-audit/` jsonl). Ưu tiên bản `*-readable.txt` — có file:line, đọc được verdict + findings; bản raw `.txt` có thể chỉ là REJECT do thiếu bằng chứng.
- Audit tĩnh Codex không chạy test và không thấy vấn đề vận hành (watcher chết, dedup, heartbeat) — nên đối chiếu findings của nó với review vận hành của Hermes trước khi kết luận.
