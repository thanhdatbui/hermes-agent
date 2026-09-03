# Recovery watch liveness diagnosis & restart (2026-08-08)

Khi nghi ngờ auto recovery chết / không xử lý shift: recipe kiểm tra 4 tầng + restart + verify.
Đây là task ops lặp lại — user hỏi "auto recovery ms chạy có hoạt động cho schedule after noon k".

## Bối cảnh sự cố (2026-08-08)

- Watch khởi động lúc logon 09:46 VN, xử lý incidents morning (máy 15 VICHANGER_VPN → Hermes fallback slot 1-5).
- Noon shift (12:00–12:29 VN) fail (exit 4294967295 = -1) → watch còn sống, detect: `SCHEDULE_TERMINAL` + `FINAL_BLOCKED NO_HANDLER_IMPLEMENTED` (12:29 VN).
- **~15:00 VN watch CHẾT** (heartbeat cuối `2026-08-08T08:00:31Z` = 15:00:31 VN; PID 49348/25208 không tồn tại; task Status `Ready`; Last Result -1).
- Afternoon shift 17:00–17:29 VN chạy bình thường (27 máy manual-needed + 2 failed + 19 success, artifact `.ai-runs/20260808-170012`) — NHƯNG ledger **0 event `2026_08_08_AFTERNOON`** vì watch đã chết.
- Restart 17:45 VN → watch sống lại nhưng activation baseline mới ĐÃ chụp `2026-08-08:afternoon` → shift đó không được auto-recover nữa.

## Checklist 4 tầng

### 1. Task Windows (nhanh nhất)
```bash
export MSYS_NO_PATHCONV=1
schtasks /query /TN TikTokScheduleRecovery /FO LIST /V | grep -iE "Status|Last Run Time|Last Result|Schedule Type|Next Run"
```
- Status `Running` = task đang chạy.
- Status `Ready` + `Last Result: -1` + `Next Run Time: N/A` + `Schedule Type: At logon time` = **watch đã chết và sẽ KHÔNG tự restart giữa ngày** (trigger chỉ At logon; health-watch ps1 có thể vẫn còn process nhưng không restart được task đã exit).

### 2. Process
```bash
wmic process where "name='python.exe'" get ProcessId,CommandLine | grep recovery_runtime
```
Phải thấy `python.exe -m scheduler.recovery_runtime --watch --dispatch --enable-live-recovery`.
Lưu ý: lọc `name like '%python%'` trên toàn bộ wmic dễ bị output khổng lồ truncate giữa chừng (thấy scheduler khác nhưng "mất" dòng recovery) — lọc `name='python.exe'` trước cho gọn.

### 3. Lease heartbeat
```bash
python -c "import json; d=json.load(open(r'D:\Taadaa\tiktok-luot nuoi acc\python_runner\runs\schedule-recovery-watch-lease.json',encoding='utf-8')); print(d.get('heartbeat_at'), d.get('state'), d.get('pid'), d.get('child_pid'))"
```
- `heartbeat_at` = UTC → VN = +7h. Watch poll ~15-16s nên heartbeat phải cách hiện tại < vài phút.
- `state: running` + heartbeat stale 2h+ = chết. Xác nhận: `tasklist //FI "PID eq <pid>"` (với MSYS_NO_PATHCONV=1) — không ra dòng nào = PID đã mất.
- Lease cũng ghi `parent_pid` (wrapper ps1) + `child_pid` (recovery_runtime) — check cả 2.

### 4. Ledger
```bash
cd "/d/Taadaa/tiktok-luot nuoi acc/python_runner/runs"
tail -3 schedule-recovery-ledger.jsonl                          # event mới nhất
grep -c "2026_08_08_AFTERNOON" schedule-recovery-ledger.jsonl   # 0 = shift không được xử lý
grep -oE '"observed_at":"2026-08-08T[0-9]{2}' schedule-recovery-ledger.jsonl | sort | uniq -c
```
- `observed_at` = UTC (suffix Z). Count theo giờ cho biết watch im lặng từ khi nào.
- Event cuối cách đây nhiều giờ = watch chết (hoặc không có incident mới — phân biệt qua lọc noise `already-terminal`).

## Restart + verify

```bash
export MSYS_NO_PATHCONV=1
schtasks /run /TN TikTokScheduleRecovery
sleep 25
schtasks /query /TN TikTokScheduleRecovery /FO LIST | grep Status        # phải Running
wmic process where "name='python.exe'" get ProcessId,CommandLine | grep recovery_runtime   # PID mới
python -c "import json; d=json.load(open(r'...\schedule-recovery-watch-lease.json',encoding='utf-8')); print(d.get('heartbeat_at'), d.get('pid'), d.get('child_pid'))"  # heartbeat mới
```
- Activation mới: `runs/schedule-recovery-activation.json` → `activated_at` (UTC) đổi mới.
- Watch poll ~16s; sau restart ledger có thể im lặng vài phút rồi mới có event — đừng vội kết luận.

## PITFALL: baseline nuốt shift đã kết thúc

Restart watch SAU khi shift đã kết thúc → activation mới chụp baseline lúc restart (hash mọi shift trong scheduler-state, kể cả shift vừa fail) → watch coi shift đó đã terminal → **KHÔNG tạo incident cho shift đó dù có máy fail**. Kiểm tra: `schedule-recovery-activation.json` → `baseline` có key `2026-08-08:afternoon` = đã bị nuốt.
Hậu quả: máy fail/manual-needed của shift đó chỉ xử lý được bằng tay (recovery bằng tay) hoặc shift kế tiếp.
**KHÔNG xóa baseline/activation để ép watch nhận lại shift cũ** (risk double-process/recover máy đang chạy).

## Thời gian — quy đổi

- `date` (git-bash, không set TZ) in giờ local đúng: SEAST = +0700 = VN.
- **`TZ=Asia/Ho_Chi_Minh date` TRONG git-bash ra giờ UTC lệch 7h** — tzdata MSYS không resolve; không dùng.
- Cross-check an toàn: ledger suffix `Z` = UTC; `scheduler.jsonl`/`scheduler-state.json` = giờ local VN; artifact dir `.ai-runs/20260808-170012` = local VN.

## Đếm máy fail/shift (chuẩn bị xử lý tay)

```bash
head -40 .ai-runs/20260808-170012/summary.txt   # event_counts: manual-needed/failed/success + total_swipes_completed
ls .ai-runs/20260808-170012/machines/           # danh sách từng máy
python -c "
import json,glob
for p in sorted(glob.glob(r'C:\Users\Kibe\.codex\device-locks\machine_*.lock.json')):
    d=json.load(open(p,encoding='utf-8'))
    print(p.split('machine_')[1][:12], d.get('status'), 'owner_active=', d.get('owner_active'), 'pid=', d.get('pid'))"
```
- Lock `blocked` + `owner_active=False` + PID chết = FINAL_BLOCKED/MANUAL_REQUIRED — giữ, gỡ tay có backup + báo user.
