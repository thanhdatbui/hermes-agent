# Phân tích log Auto Schedule & Auto Recovery (tiktok-luot nuoi acc)

Khi user hỏi "kiểm tra log auto recovery / auto schedule hoạt động như nào", đây là
các file và quy trình chuẩn. **Mọi timestamp trong log đều UTC; giờ VN = UTC+7**
(morning 06:00 VN = 23:00 UTC hôm trước, noon 12:00 VN = 05:00 UTC, afternoon 17:00 VN = 10:00 UTC).

## Vị trí log (root = `D:\Taadaa\tiktok-luot nuoi acc`)

| File | Nội dung |
|---|---|
| `python_runner/runs/scheduler.jsonl` | 1 dòng/shift: status, exit_code, artifact_root, launcher_log |
| `python_runner/runs/scheduler-state.json` | Lịch sử đầy đủ các shift + shift tương lai (`planned`) |
| `python_runner/runs/launcher/<ts>-<pid>-row-N.log` | stdout/stderr launcher từng shift |
| `python_runner/runs/schedule-recovery-task.log` | Watch loop, JSONL mỗi ~16s: `observed_at` + `outcomes[]` (per-machine: `already-terminal` / `MANUAL_REQUIRED` / `FINAL_BLOCKED`) |
| `python_runner/runs/schedule-recovery-ledger.jsonl` | Chuỗi event đầy đủ từng incident (xem dưới) |
| `python_runner/runs/schedule-recovery-watch-lease.json` | Lease của watch process — kiểm tra `heartbeat_at` còn mới để biết watch còn sống |
| `.ai-runs/<run_id>/summary.txt` + `run_manifest.json` + `log.jsonl` | Chi tiết từng shift: `completed_steps`, `event_counts` (vd `manual-needed: 12` = 12 máy bị skip vì lock) |

## Status scheduler (từ scheduler.jsonl)

- `skipped-missed-window` — cửa sổ 1h trôi qua trước khi chạy (scheduler chậm/treo)
- `failed` (exit 1) — "completed with failed machine(s)": có máy fail trong batch
- `manual-needed` (exit 2) — "skipped locked machine(s)": máy bị lock (thường do recovery để lại MANUAL_REQUIRED/FINAL_BLOCKED)
- `planned` — shift chưa tới giờ

## Chuỗi event recovery (ledger)

Mỗi incident có `incident_key` chung; các event:
`DETECTED` → `CLASSIFIED` → `AUTO_RECOVERY_PENDING` → [`PATCH_ATTEMPT_RESERVED` /
`REPAIR_NOT_READY` / `ADVISOR_RESERVED` / `ADVISOR_NOT_READY`]* → `FINAL_BLOCKED` →
`MANUAL_REQUIRED` → `NOTIFICATION`.

Fields quan trọng: `machine`, `failure_signature`, `shift`, `classification_reason`,
`classification_evidence`, `slot`, `model`, `effort`, `lock_safe`.

## Pattern chẩn đoán chính (08-07-2026)

**Mass `MANUAL_REQUIRED` + `classification_reason = final:repair-ladder-exhausted-without-approved-patch`
= hạ tầng advisor hỏng, KHÔNG phải lỗi thiết bị.**

Chuỗi điển hình (máy 65, noon):
```
ADVISOR_RESERVED slot 5 (gpt-5.6-sol/high) → ADVISOR_NOT_READY reason=planner-process-failed
→ slot 6 (xhigh) → planner-process-failed
→ slot 7 (max) → max-advisor-prerequisite-not-ready
→ FINAL_BLOCKED reason=repair-ladder-exhausted-without-approved-patch
→ MANUAL_REQUIRED classification_reason=final:repair-ladder-exhausted-without-approved-patch
```

Hệ quả: không patch nào được duyệt → fail-closed đúng contract, nhưng máy giữ lock
blocked → shift kế tiếp `manual-needed`/exit 2. Cần xử lý advisor (Sol planner process
fail) TRƯỚC, gỡ lock tay chỉ là tạm thời.

`failure_signature` thường gặp: `CAPTURE_INVALID` (screen.png 12 bytes / file
`screen_invalid_capture_N.bin` — capture hỏng), `MANUAL_NEEDED_POPUP`,
`SCRIPT_BLOCKER`. `sensitive-manual:login` = loại nhạy cảm, bắt buộc xử lý tay.

## Quy trình phân tích nhanh (python)

```python
import json, collections, datetime
ledger = r"D:\Taadaa\tiktok-luot nuoi acc\python_runner\runs\schedule-recovery-ledger.jsonl"
entries = [json.loads(l) for l in open(ledger, encoding="utf-8", errors="replace") if l.strip()]
today = [e for e in entries if "2026-08-07" in e.get("observed_at", "")]
# 1. Counter(e.get("event")) — xem tổng quan (DETECTED vs FINAL_BLOCKED vs MANUAL_REQUIRED)
# 2. Group DETECTED/MANUAL_REQUIRED theo machine + failure_signature
# 3. Với 1 incident bất kỳ: lọc theo incident_key, in chuỗi event để xem advisor ladder
```

Tương tự cho `schedule-recovery-task.log`: parse JSONL, Counter outcomes, group theo giờ
(đổi sang UTC+7) để thấy tần suất watch và máy nào lặp lại MANUAL_REQUIRED mỗi 16s.

## Kiểm tra watch còn sống

```bash
# heartbeat_at trong lease phải gần thời điểm hiện tại (UTC)
cat "D:/Taadaa/tiktok-luot nuoi acc/python_runner/runs/schedule-recovery-watch-lease.json" | grep heartbeat
```
Nếu lease cũ mà process chết → recovery không chạy; kiểm tra script
`scripts/run-schedule-recovery-watch.ps1` (Task Scheduler) trước khi kết luận máy nào đó kẹt.
