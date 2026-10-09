# Simplified Cron Runner Architecture (2026-09-10)

## Context
Trước đây tiktok_runner.py phụ thuộc vào picker → manifest → cohort → spawn. Hệ thống này bị over-engineering và gây break farm khi expand từ 3 Ca lên 4 Ca (block 4 validation bug).

## Kiến trúc hiện tại (đã đơn giản hóa)
```
tiktok_runner.py (cron 15min)
  → _determine_row(now)     # giờ → Row từ _SCHEDULE dict
  → _already_ran(window)    # dedup bằng state file
  → _spawn_feed_session(row) # gọi PS1 trực tiếp
    → powershell run-feed-session.ps1 -Row N -Preset full -AccountWorkbook taikhoan_run_safe.xlsx
      → python run_tiktok.py --mode multi-machine-feed-session ...
```

## Schedule (_SCHEDULE dict)
| Hour | Chẵn (date%2==0) | Lẻ (date%2==1) |
|------|-------------------|-----------------|
| 06h  | Row 2             | Row 1           |
| 12h  | Row 4             | Row 3           |
| 18h  | Row 6             | Row 5           |
| 00h  | Row 8             | Row 7           |
| 02-05h | dead zone       | dead zone       |

## State dedup
- File: `D:/Taadaa/runtime/kibe/cron-state/runner_simple_state.json`
- Format: `{"last_row": 4, "last_window": "2026-09-10T12", "last_run_at": "..."}`
- window_key = `<date>T<hour>` — runner chỉ spawn 1 lần per window

## Key files
- Wrapper: `C:\Users\Kibe\AppData\Local\hermes\scripts\tiktok_runner.py`
- PS1 launcher: `D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1`
- Account workbook: `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`
- Permit: `D:\Taadaa\tiktok-luot nuoi acc\runtime\hermes-cron\permits\tiktok_runner.permit`

## Block 4 validation fix (commit 8155776)
- File: `python_runner/hermes_cron/cohort.py` line 108
- Changed: `block not in (1, 2, 3)` → `block not in (1, 2, 3, 4)`
- Bắt buộc khi expand farm sang 4 Ca (block 4 = Ca 4 = Row 8)

## ⛔ CẤM
- Worker subagent KHÔNG ĐƯỢC tự ý thêm picker/cohort/manifest layers trở lại
- User đã express frustration về hệ thống phức tạp: "Cohort lồn gì v, đến h ca nào thì lấy dữ liệu từ taikhoanrunsafe mà chạy"
- Luôn giữ runner đơn giản: giờ → Row → PS1 → chạy
