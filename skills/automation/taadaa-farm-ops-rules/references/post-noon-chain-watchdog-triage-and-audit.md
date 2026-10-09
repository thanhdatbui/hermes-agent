# Post-Noon Chain Watchdog Triage & Verification Patterns

## Ngữ cảnh & Mục tiêu
Chuỗi tự động chạy sau ca trưa: `post_noon_chain_watchdog.py` phối hợp tuần tự 2 Phase:
1. **Phase 1: Reg Gmail** (`run_all.ps1` -> `run_parallel.ps1` -> `gmail_reg_v10.py`)
2. **Phase 2: TikTok Add 2FA** (`run_batch_live_2fa.py` -> `run_capture_phase_b.py`)

## 1. Tránh False Reporting Do Regex Parse Trống (Exit Code != 0)
- `post_noon_chain_watchdog.py` dùng regex `TOTAL=(\d+) SUCCESS=(\d+) FAILED=(\d+)` để đọc stdout từ subprocess.
- **Hiện tượng**: Khi batch runner hoàn tất nhưng stdout in định dạng khác hoặc có warning/stderr xen vào, hàm parse có thể fallback trả về `(0, 0, 0)` dù thực tế có máy thành công hoặc ghi workbook.
- **Khai thác chân lý O(1)**:
  - Phase 1 (Reg Gmail): Kiểm tra thư mục kết quả `results/` trong thư mục log runtime mới nhất (`D:\CodexRuntime\codex_gmail_debug-register-gmail\logs_parallel_<timestamp>\results\*.success.json`).
  - Phase 2 (TikTok 2FA): Kiểm tra file diff giữa workbook hiện tại (`D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`) và file backup gần nhất vừa sinh ra trong `workbook-backups` (`C:\Users\Kibe\AppData\Local\codex_gmail_debug-tiktok-add-bao-mat-f2a\workbook-backups\*.backup.xlsx`), hoặc kiểm tra các file nhật ký DPAPI trong `journals/`.

## 2. Giám sát & Quản lý vòng đời tiến trình dài hạn
- Watchdog chuỗi có thể chạy 30 - 60 phút khi có nhiều máy chạy song song (15 máy Gmail, 40 workers TikTok 2FA).
- Trong session cron job hoặc subagent:
  - Luôn dispatch background với generous timeout (`terminal(background=True, notify_on_complete=True)`).
  - Không kill tiến trình khi timeout của một lệnh `process(action='wait')` đơn lẻ đạt giới hạn (180s/clamp), mà tiếp tục poll bằng `Get-CimInstance Win32_Process` để nắm trạng thái worker con.
  - Khi hoàn tất, luôn nghiệm thu MEDIA: screencap thực tế từ máy đăng ký thành công (`C:\Users\Kibe\AppData\Local\register-gmail\screenshots\*_final_*.png`) theo đúng Gate 6.
