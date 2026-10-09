# Ensure Row Accounts: Telegram Alert & Log Parsing

- **Script**: `D:\Taadaa\tools\ensure_row_accounts.py <row>` (Row 1..8)
- **Mục đích**: On-demand provisioning tài khoản TikTok cho từng hàng trước khi chạy feed / nuoi acc. Tự động mua Hotmail OAuth2 nếu thiếu mail, gọi `_run_all_targets.py` để reg máy thiếu và đồng bộ tracking/safe workbook.

## Telegram Alert Target
- **Telegram Chat ID**: `-5373649734` (Farm Alert channel chung cho toàn bộ farm, không phân nhánh máy riêng lẻ).
- Token bot lấy từ file `.env` (`TELEGRAM_BOT_TOKEN`).

## Artifacts Log Directory Resolution & Error Parsing
- Thư mục chạy batch: `artifacts/runs/social-batch-all/<timestamp>/batch_*/`
- **STT Folder format**: Luôn kiểm tra định dạng padded 2 chữ số `stt_{int(m):02d}` (ví dụ `stt_02` thay vì `stt_2`), sau đó fallback về `stt_{m}`:
  ```python
  s_dir = b_dir / f"stt_{int(m):02d}"
  if not s_dir.is_dir():
      s_dir = b_dir / f"stt_{m}"
  ```
- **Error Extraction**:
  - Đọc ngược từ cuối `stderr.log` và `stdout.log`.
  - Bắt các tiền tố: `❌ [REGISTER ERROR]`, `RuntimeError:`, `Exception:`, `AdbCommandTimeout:`.
  - Phân loại lỗi người dùng (Lỗi mở account dropdown, DOB mismatch, OTP sai, Timeout cho login, ADB offline...).
