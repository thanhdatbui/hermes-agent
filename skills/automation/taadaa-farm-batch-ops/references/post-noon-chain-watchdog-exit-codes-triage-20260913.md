# Sự cố Chuỗi Sau Ca Trưa (Post-Noon Chain Watchdog) Thoát Sớm 1 Phút (13/09/2026)

## Hiện trường & Triệu chứng
Cron watchdog `post-noon-chain-watchdog` (chạy script `post_noon_chain_watchdog.py`) lúc 16:00 ngày 13/09/2026 hoàn thành sau đúng 1 phút với kết quả rỗng (0 máy chạy):
- `Phase 1 (Reg Gmail - Code 1)`: Tổng máy 0, Success 0, Fail 0.
- `Phase 2 (Add 2FA TikTok - Code 2)`: Tổng máy 0, Success 0, Fail 0.

## Root Cause 1 (Phase 1 Reg Gmail: Exit Code 1)
- **Cơ chế phát sinh:**
  Trong file `D:\Taadaa\tiktok-luot nuoi acc\scripts\sync-safe-workbook.py`, commit trưa 13/09 (`85980f9c`) bổ sung logic quét fallback serial trên từng dòng Excel nguồn khi cột Device ID (`serial_col`) chứa ngày tháng:
  ```python
  if not SERIAL_PATTERN.fullmatch(raw_serial) or re.match(r"^\d{2,4}[/-]\d{2}[/-]\d{2,4}", raw_serial):
      found_serial = ""
      for c_idx, cell_val in enumerate(row):
          if c_idx + 1 in (machine_col, id_col):
              continue
          c_str = str(cell_val or "").strip().lstrip("'")
          if SERIAL_PATTERN.fullmatch(c_str) and not re.match(r"^\d{2,4}[/-]\d{2}[/-]\d{2,4}", c_str):
              found_serial = c_str
              break
  ```
- **Hậu quả bốc nhầm Pass Mail:**
  Loop trên chỉ loại trừ `machine_col` và `id_col`, nhưng **KHÔNG LOẠI TRỪ** cột PASS MAIL (Cột 7 trong `taikhoan_dat_v2_updated .xlsx`). Các mật khẩu như `Emma2004wOjd`, `d93310aa`... thỏa mãn regex `SERIAL_PATTERN` (`^[A-Za-z0-9._:-]{4,80}$`), dẫn đến việc script bốc mật khẩu gán làm device serial và ghi vào `taikhoan_run_safe.xlsx`.
- **Hệ quả liên hoàn:**
  File `taikhoan_run_safe.xlsx` bị ghi đè dữ liệu rác, mỗi máy có 2 serial khác nhau (serial thật và mật khẩu mail). Khi `run_all.ps1` gọi `gmail_reg_v10.py` nạp device map qua `load_device_map_from_excel()`, hàm phát hiện:
  ```text
  RuntimeError: Device map has conflicting valid serials for machine(s): 1, 2, 3, ... 80
  ```
  Quá trình ném ngoại lệ dừng ngay lập tức khiến Phase 1 trả exit code 1.

## Root Cause 2 (Phase 2 Add 2FA TikTok: Exit Code 2)
- **Cơ chế phát sinh:**
  Trong `post_noon_chain_watchdog.py`, hàm `run_tiktok_2fa_batch()` gọi CLI:
  ```python
  cmd = [PYTHON_EXE, str(runner_script), "--all-online", "--workers", "10"]
  ```
- **Hậu quả sai tham số CLI:**
  Entrypoint `D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner\run_batch_live_2fa.py` sử dụng `argparse` chuẩn với các cờ:
  - `--live` (bắt buộc khi chạy máy thật).
  - `--max-workers <N>` (mặc định 40, tối đa 40).
  Script **hoàn toàn không hỗ trợ** `--all-online` và `--workers`.
- Khi gọi sai tham số, `argparse` in `unrecognized arguments: --all-online --workers 10` và thoát ngay lập tức với **Exit Code 2**.

## Khắc phục & Tiêu chuẩn điều phối
1. **Sửa `sync-safe-workbook.py`:**
   - Khi tìm serial thay thế trong dòng Excel, bắt buộc loại trừ tường minh các cột nhạy cảm: `id_col`, `pass_col`, `2fa_col`, `mail_col`, `pass_mail_col`, `dob_col`.
   - Ưu tiên bốc đúng cột device ID (Cột 10 hoặc Cột 11 nếu bị lệch do chèn ngày tạo), hoặc tra trực tiếp từ `series.txt` / `PROXYgandienthoai.xlsx`.
   - Sau khi sửa, chạy `hermes_taikhoan_sync_cron.py` để ghi lại `taikhoan_run_safe.xlsx` sạch sẽ.
2. **Sửa `post_noon_chain_watchdog.py`:**
   - Cập nhật đúng CLI call:
     ```python
     cmd = [PYTHON_EXE, str(runner_script), "--live", "--max-workers", "10"]
     ```
3. **Reset State:**
   - Xóa `last_success_date` trong `D:/Taadaa/runtime/kibe/cron-state/post_noon_chain_state.json` để chuỗi có thể kích hoạt lại theo đúng lịch.
