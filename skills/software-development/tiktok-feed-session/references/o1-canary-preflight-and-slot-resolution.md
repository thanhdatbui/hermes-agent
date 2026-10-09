# O(1) Canary Preflight & Slot Resolution Playbook

## 1. Mục đích
Tránh lỗi nghiêm trọng: lãng phí tool calls vào các lệnh quét đĩa đệ quy (`glob.glob('D:/Taadaa/**', recursive=True)`, `find`, `grep -rn`) dẫn đến timeout (180s/call) và cạn kiệt budget lượt gọi tool trước khi kịp thực thi lệnh runner canary.

## 2. Các điểm chốt O(1) bắt buộc

### A. Kiểm tra Device Lock (O(1))
- **Vị trí duy nhất chứa lock:**
  `~/.codex/device-locks/machine_<N>.lock.json`
  `~/.codex/device-locks/<serial>.lock.json`
- **Cách kiểm tra tức thì qua Python:**
  ```python
  import os
  lock_dir = os.path.expanduser('~/.codex/device-locks')
  m_lock = os.path.join(lock_dir, f'machine_{N}.lock.json')
  s_lock = os.path.join(lock_dir, f'{serial}.lock.json')
  exists = os.path.exists(m_lock) or os.path.exists(s_lock)
  ```
- **CẤM TUYỆT ĐỐI:** Quét đệ quy toàn bộ thư mục `D:/Taadaa` hay `C:/Users` để tìm file `.lock`.

### B. Tra cứu Slot Schedule & Trạng thái Ca (O(1))
- **Lịch 4 Ca / Ngày theo Parity (Ngày chẵn vs Ngày lẻ):**
  - **Ngày chẵn (day % 2 == 0):** Row 8 (00h/01h30), Row 2 (06h/08h), Row 4 (12h/14h), Row 6 (18h/20h).
  - **Ngày lẻ (day % 2 == 1):** Row 7 (00h/01h30), Row 1 (06h/08h), Row 3 (12h/14h), Row 5 (18h/20h).
- **Lịch sử ca gần nhất:**
  Đọc file JSON đơn giản:
  `D:/Taadaa/runtime/kibe/cron-state/runner_simple_state.json`
  (Chứa `last_row`, `last_window`, `last_run_at`).
- **Tra cứu tài khoản của slot:**
  `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` hoặc `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx` theo `(machine, row)`.
- **Assignment Manifest:**
  `C:/Users/Kibe/AppData/Local/automation-core/assignments/tiktok-feed.json`.

### C. Lệnh Official Runner (Chạy duy nhất 1 lần)
- **Lệnh PowerShell chuẩn:**
  ```powershell
  powershell.exe -ExecutionPolicy Bypass -File "D:/Taadaa/tiktok-luot nuoi acc/scripts/run-feed-session.ps1" -Machines <N> -Row <slot> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
  ```
- **Quy tắc thực thi:**
  - Thực thi trực tiếp ngay sau khi preflight máy (`inspect_machine.py <N>`) và lock check O(1) pass.
  - Thu thập kết quả: exit code, `final_status`, switcher verification, đường dẫn artifacts (screenshot/XML/log), và trạng thái lock hậu kiểm.
