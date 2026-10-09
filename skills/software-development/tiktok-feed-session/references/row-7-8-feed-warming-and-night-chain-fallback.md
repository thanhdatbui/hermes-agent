# Row 7 & Row 8 Feed Warming & Night Chain Fallback Architecture

## 1. Bối cảnh & Điều kiện kích hoạt Fallback Ca đêm

Trong chuỗi ca đêm (`D:\Taadaa\Tiktok_Reg\scripts\run_night_chain_pipeline.py`):
- Phase 1: Reg Gmail
- Phase 2: Reg TikTok (`_run_all_targets.py` -> `_detect_clean.py`)
- Phase 3: Add 2FA TikTok

Khi toàn bộ máy trong farm đã đạt trần 8 tài khoản/máy (`max_accounts_per_machine = 8` trong `_detect_clean.py`) hoặc không còn email nguồn hợp lệ, `_detect_clean.py` trả về mảng rỗng `[]` (`Targets: 0`). Thay vì để máy nhàn rỗi trong ca đêm, hệ thống kích hoạt luồng fallback tự động lướt feed nuôi tài khoản **Row 7 hoặc Row 8**.

### Quy tắc phân bổ Row theo ngày:
```python
current_day = datetime.now().day
feed_row = 8 if (current_day % 2 == 0) else 7
```
- Ngày chẵn: Lướt feed nuôi Row 8.
- Ngày lẻ: Lướt feed nuôi Row 7.

---

## 2. Điểm nghẽn kỹ thuật & Điều kiện tiên quyết trong repo `tiktok-luot nuoi acc`

Khi gọi feed session cho Row 7 hoặc Row 8, có 2 điểm chặn cần lưu ý:

### A. Giới hạn tham số trong `run-feed-session.ps1`
- File: `D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1`
- Hiện trạng:
  ```powershell
  [Parameter(Mandatory = $true)]
  [ValidateRange(1, 6)]
  [int]$Row,
  ```
- Khắc phục: Cần nâng lên `[ValidateRange(1, 8)]` để PowerShell không chặn các ca chạy Row 7/8.

### B. Giới hạn số dòng trích xuất trong `sync-safe-workbook.py`
- File: `D:\Taadaa\tiktok-luot nuoi acc\scripts\sync-safe-workbook.py`
- Hiện trạng: Hardcode 6 dòng/máy:
  ```python
  while len(entries) < 6:
      entries.append((primary_serial, ""))
  for i, (serial, account_id) in enumerate(entries[:6]):
  ...
  for _ in range(6):
      rows.append((machine, serial, "", 0))
  ```
- Hệ quả: File `taikhoan_run_safe.xlsx` chỉ chứa 6 dòng cho mỗi máy. Khi `run-feed-session.ps1` gọi `core/feed_session_workbook.py` với `-Row 7` hoặc `-Row 8`, core sẽ ném lỗi:
  `account workbook does not have valid row 7 for machine {machine}` vì `len(rows) < row_index`.
- Khắc phục: Nâng số lượng trích xuất lên 8 dòng (`entries[:8]`, padding đến 8). 
- An toàn: Không làm thay đổi index hay dữ liệu của Row 1..6 ban ngày. Các máy chưa đăng ký đủ 8 nick sẽ có slot 7/8 trống và tự động được core skip an toàn (`account row X is empty, skipping`).

---

## 3. Lệnh thực thi Fallback từ Night Pipeline

Khi kích hoạt fallback nuôi feed từ `run_night_chain_pipeline.py`:
```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Row <7_or_8> -Preset full -LocalRun -RecoveryTestSwipes 2 -MaxWorkers 40
```
Timeout đề xuất: 3600s (60 phút). Báo cáo tổng kết gửi về Telegram dưới dạng `Phase 2 (Nuôi Feed Row X [Ngày chẵn/lẻ] - Code Y)`.
