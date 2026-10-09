# Post-Noon Watchdog Triage & Runner Exit Code 4 vs Dry-run Flags (16/09/2026)

## Hiện tượng thực tế (16/09/2026)
Vào lúc 14:50 - 15:31 ngày 16/09/2026, cron watchdog `post_noon_chain_watchdog.py` kích hoạt sau Ca 2:
1. **Phase 1 (Reg Gmail):** Chạy script `run_all.ps1` thành công 10/15 máy (lưu kết quả vào `gmail_clean_v2.xlsx`), nhưng trả exit code 1 do bước verify hash workbook `WORKBOOK_VERIFY_ROLLBACK_FAILED`.
2. **Phase 2 (TikTok Add 2FA):** Gọi `run_batch_live_2fa.py --live --max-workers 40`, runner kết thúc với **Exit Code 4** và watchdog báo cáo:
   `- Phase 2 (Add 2FA TikTok - Code 4): LỖI KHỞI ĐỘNG RUNNER`
   khiến user nghi ngờ chuỗi 2FA chưa chạy hoặc hỏng hóc.

## Cơ chế phát sinh Exit Code trong `run_batch_live_2fa.py`
Trong `python_runner/run_batch_live_2fa.py`:
- `exit code 0`: Tất cả targets trong batch hoàn thành với status `success` hoặc `skipped` (hoặc dry-run hợp lệ / `NO_ELIGIBLE_TARGETS`).
- `exit code 2`: Lỗi tham số dòng lệnh CLI (argparse `unrecognized arguments`, ví dụ truyền nhầm `--dry-run`, `--all-online`).
- `exit code 3`: Lỗi config validation (file workbook không tồn tại, limit/max_workers ngoài 1..80).
- `exit code 4`: **BẮT BUỘC LƯU Ý**: Exit code 4 **KHÔNG PHẢI LÀ LỖI KHỞI ĐỘNG RUNNER (RUNNER LAUNCH ERROR)**. Runner đã khởi động bình thường, freeze targets thành công và đã hoàn tất chạy batch, nhưng trong số các kết quả có ít nhất 1 target có status là `failed` (ví dụ do UI timeout, OTP không vào, hoặc phone verify). Dòng return cuối cùng của script:
  ```python
  return 0 if all(item.status in ("success", "skipped") for item in results) else 4
  ```
- `exit code 5`: Lỗi freeze target / đọc workbook ban đầu.

## Pitfall trong Watchdog Reporting
- `post_noon_chain_watchdog.py` kiểm tra `if t2fa_code != 0:` và lập tức gắn nhãn `- Phase 2 (Add 2FA TikTok - Code 4): LỖI KHỞI ĐỘNG RUNNER` kèm reset counts về `(0, 0, 0)`.
- **Hệ quả:** Làm nuốt chửng toàn bộ kết quả chạy thật của các workers, tạo báo cáo rác gây hoang mang cho Operator.
- **Quy tắc sửa / Triage chuẩn:**
  1. Exit Code 4 từ `run_batch_live_2fa.py` nghĩa là **Batch đã chạy thực tế**, cần parse bảng kết quả (`machine | source_row | username | status | reason`) từ `proc.stdout` thay vì coi là lỗi khởi động.
  2. Chỉ coi là lỗi khởi động khi code là `1`, `2`, `3` hoặc không có bảng kết quả output.
  3. Khi test kiểm tra cú pháp dòng lệnh CLI của `run_batch_live_2fa.py`, **CẤM dùng `--dry-run`** (runner không có cờ `--dry-run`, truyền vào sẽ văng Code 2). Để chạy dry-run preview an toàn, chỉ cần gọi script **KHÔNG CÓ cờ `--live`** (mặc định runner chạy dry-run đóng băng danh sách và exit 0).
