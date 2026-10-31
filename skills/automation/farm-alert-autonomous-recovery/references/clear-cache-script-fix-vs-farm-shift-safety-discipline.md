# Clear Cache Script Fix vs Farm Shift Safety Discipline

> Ref: `scripts/clear-tiktok-cache.py`, `cron_clear_tiktok_cache.py`, `unified_patch_pipeline.py`.

## 1. Phân định "Fix Script" vs "Can thiệp máy sống" (Chống phá ca nuôi)
- **Bối cảnh**: Sau khi cronjob dọn cache cuối ngày hoàn tất và xuất báo cáo có máy lỗi/timeout, User lệnh: *"Fix đi" / "Sửa đi"*.
- **CẤM TUYỆT ĐỐI**: Không được nhảy vào chạy các script can thiệp thiết bị (`recover_stuck_s7.py`, `am force-stop`, reboot) khi máy đang trong ca chạy nuôi feed (`máy đang ca chạy`). Việc tự ý kill app hay can thiệp máy sống sẽ phá hỏng phiên tương tác feed của tài khoản.
- **Hành động đúng**: "Fix đi" trong ngữ cảnh này là **SỬA CODE SCRIPT** gốc (`scripts/clear-tiktok-cache.py` trong repo `D:/Taadaa/automation-core`). BẮT BUỘC kích hoạt `unified_patch_pipeline.py`.

## 2. Kỷ luật `--no-canary` khi Farm đang chạy ca
- Khi kích hoạt `unified_patch_pipeline.py` cho các repo farm automation (`automation-core`) vào khung giờ máy đang chạy ca:
  - BẮT BUỘC dùng cờ `--no-canary --no-canary-reason "Máy farm đang trong ca chạy nuôi feed, kiểm chứng an toàn qua focused mock pytest"`.
  - Tuyệt đối không để pipeline chiếm thiết bị thật chạy Canary làm ngắt quãng phiên nuôi TikTok.
  - Sử dụng focused pytest (ví dụ: `pytest tests/test_clear_tiktok_cache.py -q`) để kiểm chứng logic delta O(1).

## 3. Preflight Wake-up cho Deep Link (Anti-Timeout & Anti-WIDGET_MISS)
- **Cơ chế lỗi**: Ban đêm máy ở trạng thái ngủ sâu (`Dozing / Screen OFF`). Intent Deep Link (`snssdk1180://clean_cache`) gửi tới màn hình tắt sẽ không bung được activity "Giải phóng dung lượng".
- **Hậu quả**: Script fallback sang Path 2 (In-App Settings qua Profile -> Menu -> Cài đặt), thực hiện 10–15 lần `dump_ui`. Trên mạng Network ADB (Farm Admin), mỗi lần dump mất 15–20s khiến tổng thời gian vượt quá 240s -> gây ra Timeout và WIDGET_MISS hàng loạt.
- **Quy chuẩn fix O(1)**: Bắt buộc gửi lệnh đánh thức và mở khóa trước khi bắn intent:
  ```python
  shell(serial, "input keyevent KEYCODE_WAKEUP")
  shell(serial, "wm dismiss-keyguard")
  time.sleep(0.8)
  # Sau đó mới gọi intent deep link Path 1
  ```
  Nhờ đó Path 1 kích hoạt trúng đích tức thì trong < 2 giây, triệt tiêu hoàn toàn fallback dump UI nặng nề.
