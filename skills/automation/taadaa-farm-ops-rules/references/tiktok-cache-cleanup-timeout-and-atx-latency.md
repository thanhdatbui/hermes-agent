# TikTok Cache Cleanup Timeout & ATX Latency Hardening

## Background & Problem
Cron task dọn dẹp cache TikTok (`cron_clear_tiktok_cache.py` và script nền tảng `clear-tiktok-cache.py`) gặp lỗi Timeout hàng loạt trên Phone Farm khi chạy tự động hoặc kiểm thử canary.

## 4 Root Causes & Architecture Solutions

### 1. Screen State Before Deep Link Launch (Root Cause 1)
- **Triệu chứng**: Khi cron dọn cache chạy vào ban đêm / dead-window, máy đang ở trạng thái màn hình tắt (`screen_state=OFF`) hoặc keyguard khóa. Lệnh `am start -a android.intent.action.VIEW -d 'snssdk1180://clean_cache'` gửi intent thành công nhưng UI không hiển thị lên foreground, khiến probe thất bại và ép script rơi vào Path 2 (In-App Settings navigation).
- **Quy tắc bắt buộc**: Phải luôn đánh thức màn hình và mở khóa keyguard ở đầu hàm `clear_cache`:
  ```python
  shell(serial, "input keyevent KEYCODE_WAKEUP")
  shell(serial, "wm dismiss-keyguard")
  time.sleep(0.5)
  ```

### 2. ATX Dump Latency & Shell Fallback (Root Cause 4)
- **Triệu chứng**: Trong `dump_ui`, nếu ATX agent (TCP port 7912) bị treo, chậm hoặc socket chưa sẵn sàng, chu kỳ retry cũ (3 lần 10s + reset 10s + 2 lần 12s = ~64s) đốt cháy toàn bộ ngân sách thời gian của mỗi bước duyệt UI.
- **Tối ưu hóa**: Rút ngắn chu kỳ thử ATX xuống mức tinh gọn (2 lần 6s, reset 5s, 1 lần 8s) để fallback sang shell `uiautomator dump` nhanh hơn:
  ```python
  for _ in range(2):
      atx = capture_atx_session_ui(client, timeout=6)
      if atx.xml and "<hierarchy" in atx.xml:
          return atx.xml
      time.sleep(0.3)
  reset_atx_agent(client, timeout=5)
  time.sleep(0.5)
  for _ in range(1):
      atx = capture_atx_session_ui(client, timeout=8, restart_attempts=1)
      if atx.xml and "<hierarchy" in atx.xml:
          return atx.xml
      time.sleep(0.5)
  # Legacy shell fallback:
  shell(serial, "uiautomator dump /sdcard/tt_cache_dump.xml >/dev/null 2>&1")
  ```

### 3. Subprocess Timeout Ceiling in Cron Wrappers (Root Cause 3)
- **Triệu chứng**: Trong `cron_clear_tiktok_cache.py`, lệnh `subprocess.run(cmd, ..., timeout=120)` đặt trần 120s quá sát. Với các máy chạy Path 2 (mở app, vào Profile, mở Menu 3 gạch, vào Cài đặt và quyền riêng tư, cuộn tìm Giải phóng dung lượng, xóa và xác minh), thời gian thực thi có thể mất 130s-180s. Hậu quả: tiến trình con bị SIGKILL bạo lực ở đúng giây 120 (`TimeoutExpired`).
- **Quy tắc bắt buộc (Case 91)**: Nâng `timeout=240` (hoặc 270) cho worker thread chạy mỗi máy trong `cron_clear_tiktok_cache.py`. Đồng thời đồng bộ cả 2 bản sao:
  - `C:/Users/Kibe/AppData/Local/hermes/scripts/cron_clear_tiktok_cache.py`
  - `D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_clear_tiktok_cache.py`
