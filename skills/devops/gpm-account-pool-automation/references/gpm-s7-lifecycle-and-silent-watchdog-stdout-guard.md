# GPM & S7 Lifecycle Watchdog: Kỷ Luật Silent Watchdog & Chống Rò Rỉ Log ra Farm Alert

## 1. Bối cảnh & Hiện tượng lỗi (Incident Context)
Khi chạy cronjob `gpm-lifecycle-sync-watchdog` (chế độ `no_agent: true`), hệ thống liên tục spam các dòng log chi tiết vào Telegram Farm Alert mỗi chu kỳ 15 phút:
```text
2026-09-22 07:15:27,745 [INFO] [Machine 05 | 9885e64b4a434a3037] Tiến hành gỡ tài khoản thachkieu2409200505@gmail.com qua Android OS (skip_lock=True)...
2026-09-22 07:15:27,774 [INFO] AdbClient initialized with remote host=localhost:5037 for serial=9885e64b4a434a3037
2026-09-22 07:16:03,372 [INFO] Máy M07 đang trong slot feed, bỏ qua.
```

### Nguyên nhân gốc rễ:
1. **Cơ chế `no_agent: true` của Hermes Cron**:
   - `stdout` **rỗng** -> SILENT (im lặng, không gửi tin nhắn, đúng chuẩn watchdog).
   - `stdout` **có dữ liệu** -> Bốc toàn bộ nội dung gửi nguyên văn về channel đích (`Farm Alert`).
2. **Cấu hình Logger sai nguyên tắc**:
   - Helper script `preflight_s7_rolling_cleanup.py` đã cấu hình `logging.basicConfig(handlers=[logging.StreamHandler(sys.stdout)])` ngay ở module-level.
   - Khi `sync_gpm_lifecycle.py` import helper này, root logger bị gán StreamHandler trỏ vào `sys.stdout`.
   - Kết quả: Mọi log từ `automation_core.adb` (`AdbClient initialized...`), log kiểm tra slot feed, log ADB dumpsys đều bị tuồn ra `sys.stdout` và bắn thẳng lên Telegram Farm Alert.

---

## 2. Quy tắc Bất biến cho Silent Watchdog & Helper Script

### Rule 1: CẤM gán `StreamHandler(sys.stdout)` ở Module-Level
- Mọi module helper, utility, adapter (đặc biệt trong `GPM auto/scripts/`) **TUYỆT ĐỐI CẤM** gọi `logging.basicConfig(handlers=[StreamHandler(sys.stdout)])` hoặc gắn handler trỏ vào `sys.stdout` ở phạm vi toàn cục.
- Cấu hình logger chuẩn cho helper:
  ```python
  LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
  os.makedirs(LOG_DIR, exist_ok=True)
  logger = logging.getLogger("ModuleName")
  logger.setLevel(logging.INFO)
  logger.propagate = False
  if not logger.handlers:
      _fh = logging.FileHandler(os.path.join(LOG_DIR, "module_name.log"), encoding="utf-8")
      _fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
      logger.addHandler(_fh)
  ```
- Nếu script có hỗ trợ chạy tay CLI (`if __name__ == "__main__":`), chỉ thêm StreamHandler vào `sys.stderr`, không ghi đè vào `sys.stdout`:
  ```python
  if __name__ == "__main__":
      sh = logging.StreamHandler(sys.stderr)
      sh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
      logger.addHandler(sh)
  ```

### Rule 2: Hard Guard Lọc Handler `sys.stdout` trong Watchdog Caller
Trong các cron watchdog script (như `sync_gpm_lifecycle.py`, `cron_chatgpt_web_pool_watchdog.py`), luôn cài đặt Hard Guard chủ động tước bỏ mọi StreamHandler trỏ vào `sys.stdout` trước và sau khi import thư viện thứ ba:
```python
# Tước bỏ handler stdout khỏi root logger
for _h in list(logging.getLogger().handlers):
    if isinstance(_h, logging.StreamHandler) and getattr(_h, "stream", None) in (sys.stdout, sys.__stdout__):
        logging.getLogger().removeHandler(_h)
```

### Rule 3: Semantics Báo cáo Watchdog (Chỉ in khi có biến động thực tế)
- **Khi không có thay đổi** (ví dụ: máy bận nuôi TikTok, không có nick DIE nào thỏa mãn gỡ): Giữ `sys.stdout` **rỗng 100%**.
- **Khi có kết quả thực tế**: Chỉ in đúng 1 dòng tóm tắt duy nhất vào cuối hàm `main`:
  ```python
  if created_cnt > 0 or cleaned_cnt > 0:
      parts = []
      if created_cnt > 0:
          parts.append(f"Tạo mới {created_cnt} profile LIVE")
      if cleaned_cnt > 0:
          parts.append(f"Đã dọn {cleaned_cnt} tài khoản DIE trên S7")
      print(f"[GPM & S7 LIFECYCLE] {' | '.join(parts)}")
  ```

---

## 3. Quy tắc Vận hành Dọn dẹp Tài khoản DIE trên Thiết bị S7

1. **Khung giờ cuốn chiếu**: Chỉ kích hoạt trong khung giờ sáng (`07:15 - 08:45 HCM`) khi máy ít tải.
2. **Feed Slot Protection**: Trước khi đụng vào máy, bắt buộc kiểm tra manifest slot nuôi (`is_machine_in_feed_slot(mid)`). Nếu máy đang trong slot hoặc sắp nuôi trong 30 phút tới -> **BỎ QUA NGAY**, không được chiếm quyền máy.
3. **Device Lock An Toàn**: Dùng `acquire_device_lock` với cơ chế non-blocking: nếu máy đang bận giữ lock bởi tiến trình khác -> bỏ qua sang máy tiếp theo, không block treo watchdog.
4. **Bảo toàn Profile GPM**:
   - **CHỈ GỠ TRÊN S7**: Gỡ tài khoản DIE khỏi Android OS để lấy chỗ đăng ký/nuôi tài khoản mới.
   - **CẤM XÓA PROFILE GPM**: Profile GPM của tài khoản DIE vẫn phải giữ nguyên vì có thể đang chứa session OpenAI / Codex / dịch vụ bên ngoài đã verify số điện thoại (tài sản farm).
