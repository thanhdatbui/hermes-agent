# Direct Feed Session Launch (bypass picker/cohort)

**User preference (2026-09-10):** Đơn giản — đến ca nào thì lấy Row từ `taikhoan_run_safe.xlsx` chạy thẳng. CẤM phức tạp hóa picker/cohort/manifest. "Đến h ca nào thì lấy dữ liệu từ taikhoanrunsafe mà chạy."

## Row mapping theo ngày

- **Ngày chẵn (2,4,6,8,10...)**: 06:00→Row 2, 12:00→Row 4, 18:00→Row 6, 00:00→Row 8
- **Ngày lẻ (1,3,5,7,9...)**: 06:00→Row 1, 12:00→Row 3, 18:00→Row 5, 00:00→Row 7

## Cách 1: PowerShell wrapper

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run-feed-session.ps1 `
  -Row <ROW_INDEX> -Preset full `
  -AccountWorkbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" `
  -SkipAccountWorkbookSync -LocalRun `
  -MachineStartStaggerMs "2000,8000" -RandomizeMachineOrder -Run
```

- `-LocalRun` BẮT BUỘC khi dispatch trực tiếp (bypass picker/cohort gate).
- Timeout PS1 ~300s nhưng python child detach chạy tiếp nền — bình thường.

## Cách 2: Python trực tiếp

```bash
TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/kibe.yaml" \
PYTHONPATH="D:/Taadaa/tiktok-luot nuoi acc" \
"D:/Taadaa/python-envs/automation/Scripts/python.exe" \
  python_runner/run_tiktok.py \
  --mode multi-machine-feed-session \
  --machines 1,2,3,...,80 \
  --account-workbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" \
  --account-row-index <ROW> --max-workers 40 \
  --config python_runner/config.example.yaml \
  --artifact-root "D:\Taadaa\runtime\kibe\live\<DATE>\row-<ROW>-<HHMM>" \
  --allow-navigation-only --allow-feed-swipe --allow-benign-popup-dismiss \
  --prepare-tiktok --machine-start-stagger-ms 2000,8000 --randomize-machine-order
```

⚠️ **BẮT BUỘC** dùng `D:/Taadaa/python-envs/automation/Scripts/python.exe`. Hermes venv → `ImportError: cannot import name '_imaging' from 'PIL'`.

## Kiểm tra trạng thái

```bash
wmic process where "name='python.exe' and commandline like '%run_tiktok%'" get ProcessId,CommandLine
tail -20 "D:/Taadaa/runtime/kibe/live/<DATE>/row-<N>-<HHMM>/<TS>/log.jsonl"
```

## Pitfalls

1. **Cron `tiktok_runner.py` dies vì block_index:** `cohort.py` L108 hard-reject block > 3, farm 4 Ca → "active manifest has no valid cohort" → im lặng. **Fix:** dispatch trực tiếp bằng PS1/Python.
2. **Stale device lock:** Kill process → lock giữ ở `~/.codex/device-locks/`. `reap-dead-owner-locks` dọn sau ~15 phút.
3. **Zombie Row 8:** Picker dispatch Row 8 lúc ban ngày (deadline sai) → kill process cũ trước khi chạy Row đúng.
