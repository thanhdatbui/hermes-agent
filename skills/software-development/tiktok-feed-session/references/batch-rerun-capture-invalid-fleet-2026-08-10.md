# Batch rerun của 5 máy capture-invalid sau khi fix ladder break sớm (2026-08-10)

Chuỗi validation ở fleet scale cho fix `terminal_capture_recovery` break sớm (§9c2):
5 máy từng FINAL_BLOCKED vì capture-invalid (M6/M20/M24/M50/M60) → chạy lại sau fix.

## Kết quả cuối (run `.ai-runs/20260810-181918`)

| Máy | Serial | Kết quả | Swipes |
|-----|--------|---------|--------|
| M6  | 9885e64c484c544d32 | ✅ success | 20 |
| M20 | ce0318237dec1ce60c | ✅ success (sau transient) | success |
| M24 | ce0117112b2a0e3a04 | ✅ success | 23 |
| M50 | ce091609dd78991305 | ✅ success | 21 |
| M60 | ce09160963abd20e02 | ❌ fail `capture_deadline_exceeded` (prepare_tiktok) → B1 ATX-kill → retry success |

## Lệnh chạy lại (bản cuối đúng)

```bash
export PATH="/c/Program Files (x86)/xiaowei/tools:$PATH"
PYTHONPATH= "D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -u python_runner/run_tiktok.py \
  --mode multi-machine-feed-session \
  --machines "6,20,24,50,60" \
  --account-workbook "D:\Taadaa\tiktok-luot nuoi acc\data\taikhoan_run_safe.xlsx" \
  --account-row-index 1 \
  --max-workers 5 --max-swipes 5 \
  --allow-navigation-only --allow-feed-swipe \
  --allow-benign-popup-dismiss --allow-coordinate-swipe-recovery \
  --full-scope-takeover \
  --prepare-tiktok \
  --config python_runner\config.example.yaml \
  --artifact-root "D:\Taadaa\tiktok-luot nuoi acc\.ai-runs"
```

## 3 cú vấp khi chạy lại (theo thứ tự xảy ra)

1. **`skipped locked machine(s)` (exit 2, Status: manual-needed)** — lock file máy đã xóa
   nhưng còn **serial alias** `serial_<serial>.lock.json` (PID 70996 chết từ batch cũ).
   → Xóa CẢ `machine_N.lock.json` LẪN `serial_<serial>.lock.json`:
   ```bash
   mkdir -p "C:/Users/Kibe/.codex/device-locks/backup-<ts>"
   cd "C:/Users/Kibe/.codex/device-locks"
   for f in machine_6 machine_20 machine_24 machine_50 machine_60 \
            serial_9885e64c484c544d32 serial_ce0318237dec1ce60c \
            serial_ce091609dd78991305 serial_ce09160963abd20e02; do
     [ -f "$f.lock.json" ] && cp "$f.lock.json" backup-<ts>/ && rm "$f.lock.json"
   done
   ```

2. **`DEFERRED_LOCKED: prior target handoff/non-success`** — release-device-lock.py chỉ xóa
   lock file nhưng `multi_machine_feed_session._prior_target_evidence` còn quét
   `recovery_lock_handoff.json` trong artifact cũ (M20/M24: `.ai-runs/20260809-120007/...`,
   M50: `.ai-runs/20260807-120020/...`) → prior handoff không `VERIFIED_SUCCESS` → skip.
   → Thêm `--full-scope-takeover` (bypass prior-handoff check; user đã authorize rerun).

3. **M60 `capture_deadline_exceeded` ngay `prepare_tiktok/close_all_apps_start`** — dù đã
   reboot trước đó. B2/B3 đã dùng hết budget turn → **chỉ B1 ATX-kill rồi retry**:
   ```bash
   adb -s ce09160963abd20e02 shell "pkill -f atx-agent; pkill -f uiautomator; pkill -f minicap; pkill -f minitouch; am force-stop com.github.uiautomator; am force-stop io.appium.settings"
   # verify dump hồi phục:
   adb -s ce09160963abd20e02 shell "uiautomator dump /sdcard/_m60.xml"   # → UI hierchary dumped, len 20937
   ```
   → retry `feed-session-smoke --machine 60 --account iyoqytawkzq --max-swipes 5` → success.
   **Xác nhận rule:** B1 (ATX-kill) chạy được mọi lỗi không giới hạn; B2/B3 mỗi 1 lần/turn/máy
   — không cần relaunch/reboot lần nữa khi ATX-kill đã hồi phục capture.

## Đọc kết quả per-machine sau batch

```bash
for m in 6 20 24 50 60; do
  s=$(find .ai-runs/<run>/machines/machine_$m -name summary.txt | head -1)
  [ -n "$s" ] && grep -E "status:|final_status:|total_swipes_completed:" "$s" | head -3
done
```
- `Status: fail` ở batch-level = "completed with failed machine(s)" — đọc từng máy, không coi
  exit≠0 là fail toàn cục.
- Account per-machine: `data/taikhoan_run_safe.xlsx` sheet `Accounts`, cột A = máy, cột C = ID
  (dùng ID đầu tiên cho `--account-row-index 1`).
