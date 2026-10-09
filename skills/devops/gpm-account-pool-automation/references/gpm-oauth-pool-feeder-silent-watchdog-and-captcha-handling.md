# GPM OAuth Pool Feeder: Silent Watchdog Discipline & reCAPTCHA Leak Prevention

## 1. Bối cảnh & Vai trò của Job Feeder
Job `gpm-oauth-full-pool-feeder` (chạy định kỳ qua Hermes cron `*/30 * * * *`, `no_agent=True` cuốn chiếu cả ngày đến khi cạn quota proxy, kết hợp watchdog báo cáo `cron_gpm_oauth_pool_6h_report.py` mỗi 6h `0 */6 * * *`):
- Tự động quét các profile GPM đã đăng nhập Google nhưng chưa có trên OmniRoute (`:20129`).
- Chạy song song tối đa 5 workers (`ThreadPoolExecutor(max_workers=5)`).
- Ràng buộc an toàn: Tối đa 1 account / 1 proxy port / 1 ngày.
- Phân loại lỗi proxy chuẩn Farm: Lỗi Nền Tảng (reCAPTCHA, Google Checkpoint) -> khóa IP cả ngày; Lỗi Script (GPM start timeout, thiếu pass Excel) -> giữ nguyên IP cho acc khác.
- Loại trừ 100% tài khoản dính `khoaleemagic`, sai pass (`wrong_password_or_checkpoint`), hoặc đang trong cooldown 7 ngày.
- Nạp OAuth Antigravity, gán proxy 1:1 và kích hoạt `sync-models`.

---

## 2. Giải phẫu lỗi rò rỉ log ra Telegram (Root Cause Anatomy)
Trong mô hình Hermes cron `no_agent=True`:
- **Stdout rỗng (0 bytes)**: Scheduler coi là ca chạy im lặng (Silent Run) -> **Không gửi tin nhắn**.
- **Stdout có dữ liệu (> 0 bytes)**: Scheduler coi toàn bộ nội dung stdout là thông điệp báo cáo -> **Chuyển tiếp nguyên văn vào Telegram**.

### Điểm hở phát sinh:
1. Script `cron_gpm_oauth_full_pool.py` import module tiện ích:
   ```python
   from add_oauth_omniroute import solve_recaptcha_audio, CredentialLookup
   ```
2. Trong `add_oauth_omniroute.py` (hoặc module liên quan như `run_batch_12_untouched_proxies.py`), cấu hình logging cấp module gán `StreamHandler(sys.stdout)` vào Root Logger:
   ```python
   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s [%(levelname)s] %(message)s",
       handlers=[
           logging.FileHandler(LOG_FILE, encoding="utf-8"),
           logging.StreamHandler(sys.stdout),  # <-- NGUYÊN NHÂN GỐC RỄ
       ],
   )
   ```
3. Khi 5 profile mở Google OAuth cùng lúc, Google nghi ngờ hành vi tự động hóa và bật **reCAPTCHA challenge**.
4. Khi Playwright cố giải audio captcha, Google phát hiện và hủy context/frame (`Frame was detached` / `Target page, context or browser has been closed`).
5. Hàm `solve_recaptcha_audio` gọi:
   ```python
   logger.info("Clicking reCAPTCHA checkbox...")
   logger.warning("No reCAPTCHA bframe found after clicking anchor.")
   logger.error(f"Error solving reCAPTCHA audio: {e}")
   ```
   Do `StreamHandler(sys.stdout)` gắn trên Root Logger, toàn bộ các dòng log này bị tống thẳng ra `sys.stdout` thay vì `sys.stderr`.
6. Hermes scheduler thấy stdout có dữ liệu, ngỡ là báo cáo thành công nên bắn toàn bộ hàng chục dòng log kỹ thuật vào Telegram của User.

---

## 3. Quy chuẩn vá & Cô lập Logger (The Isolation Pattern)

Ngay sau các dòng import helper scripts có nguy cơ gây ô nhiễm Root Logger, **BẮT BUỘC** thực hiện đoạn tẩy uế và chuyển hướng:

```python
sys.path.insert(0, r"D:\Taadaa\GPM auto\scripts")
try:
    from add_oauth_omniroute import solve_recaptcha_audio, CredentialLookup
except Exception:
    solve_recaptcha_audio = None
    CredentialLookup = None

# TẨY UẾ ROOT LOGGER & TRIỆT TIÊU STDOUT LEAK
import logging
logging.basicConfig(stream=sys.stderr, level=logging.WARNING, force=True)

# 1. Quét và loại bỏ tất cả handlers đang trỏ vào stdout
for _h in list(logging.root.handlers):
    if getattr(_h, "stream", None) == sys.stdout:
        logging.root.removeHandler(_h)

# 2. Xóa sạch handlers của các module bên thứ ba / helper
for _name in ("add_oauth_omniroute", "Batch12Untouched", "playwright", "urllib3"):
    logging.getLogger(_name).handlers.clear()
```

---

## 4. Kỷ luật Silent Watchdog khi kết thúc ca

1. **Khi không có tài khoản nào được nạp thành công (`success_count == 0`):**
   - Chỉ log ra `sys.stderr`:
     ```python
     log(f"Kết thúc ca: Không nạp thêm acc nào ({fail_count} thử nghiệm thất bại/skip).")
     ```
   - **CẤM TUYỆT ĐỐI** gọi `print(...)` ra `sys.stdout`. `sys.stdout` phải đạt 0 bytes.
2. **Chỉ gửi báo cáo khi có kết quả thực sự (`success_count > 0`):**
   - In đúng 1 khối markdown tóm tắt phân tách 3 nhóm chuẩn:
     ```python
     if success_count > 0:
         msg = (
             f"[GPM OAUTH FEEDER - TỔNG KẾT CA]\n"
             f"• Nạp mới thành công: ✓ {success_count} accounts\n"
             f"• Lỗi nền tảng (Đã khóa IP): 🛑 {fail_platform_count} accounts\n"
             f"• Lỗi script (IP được giữ): ⚠️ {fail_script_count} accounts\n"
             f"• Ràng buộc: 1 acc / 1 IP (proxy) / 1 ngày | 5 workers\n"
             f"• Antigravity Pool hiện tại: {len(live_anti)} accounts LIVE trên OmniRoute (:20129)\n"
             f"• Danh sách nạp: {', '.join(added_emails)}"
         )
         print(msg)
     ```

---

## 5. Quy trình Kiểm chứng & Đồng bộ (Verification & Multi-Location Sync)

1. **Kiểm tra rò rỉ stdout bằng lệnh test độc lập:**
   ```bash
   /c/Users/Kibe/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -c "
   import sys
   sys.path.insert(0, r'C:\Users\Kibe\AppData\Local\hermes\scripts')
   import cron_gpm_oauth_full_pool
   from add_oauth_omniroute import logger
   logger.info('TEST_INFO')
   logger.warning('TEST_WARNING')
   " 1>out.txt 2>err.txt
   # Xác nhận: wc -c < out.txt == 0
   ```
2. **Đồng bộ bắt buộc qua 4 vị trí:**
   - `%LOCALAPPDATA%\hermes\scripts\cron_gpm_oauth_full_pool.py`
   - `D:\Taadaa\GPM auto\scripts\cron_gpm_oauth_full_pool.py`
   - `D:\Taadaa\Hermes\deploy\hermes-home\scripts\cron_gpm_oauth_full_pool.py`
   - `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\cron_gpm_oauth_full_pool.py`
3. Chạy lệnh:
   ```bash
   python3 "C:/Users/Kibe/AppData/Local/hermes/scripts/cron_sync_watchdog.py" --force
   ```
