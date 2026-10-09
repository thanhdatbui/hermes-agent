# Device Lock Auto-Reap vs Watchdog Alert Threshold & Universal Teardown Home Invariant

## 1. Vấn Đề: Race Condition giữa Auto-Reap và Watchdog Alert
- **Hiện tượng:** Khi máy bị lock trạng thái `blocked` (lỗi cần giữ hiện trường cho operator), TTL lock là 60 phút (3600s). Khi chạm mốc 60 phút, script `reap-dead-owner-locks` chuẩn bị tự động dọn dẹp và nhả lock, nhưng watchdog `watch_device_locks` lại chạy và bắn cảnh báo Telegram ngay mốc 60p: *"Tổng số máy giữ lock: N | Quá hạn (>60p): M"*. Chỉ 1-2 phút sau, cron Reaper chạy dọn sạch sẽ, biến cảnh báo Telegram thành tin rác / báo ảo gây phiền operator ("sắp được quét nhả lock mà tự nhiên còn báo").
- **Nguyên lý chuẩn hóa (Separation of Concerns):**
  1. **Tự động dọn âm thầm (Self-healing Reaper):** Cứ lock hết hạn TTL (60p cho blocked) hoặc dead process, Reaper chạy định kỳ 5 phút/lần (`*/5 * * * *`) tự động đưa vào quarantine, force-stop app và đưa về HOME sạch sẽ mà KHÔNG spam Telegram.
  2. **Watchdog chỉ báo lỗi kẹt thực sự (Fail-safe Watchdog):** Nâng ngưỡng cảnh báo Telegram của watchdog lên **90 phút** (hoặc 120 phút). Khi máy đã qua 60 phút mà Reaper quét nhiều vòng vẫn không dọn được (ví dụ do lỗi filesystem, tiến trình bất tử không thể kill), lúc đó mới kích hoạt cảnh báo khẩn cấp lên Telegram.

## 2. Invariant: Bằng Chứng Số Hóa (XML + Screencap) vs Giữ Màn Hình Máy Thật
- **Câu hỏi nghiệp vụ:** Khi máy lỗi, có cần giữ nguyên màn hình máy thật để fix không, hay đọc dump XML + Screencap + log là đủ?
- **Quy tắc vàng:**
  - **95% trường hợp fix bug:** Bộ đôi **Dump UI XML + Screencap ảnh + Log** tại thời điểm lỗi là bằng chứng đầy đủ 100% để phân tích root cause, viết selector, và viết unit test mock.
  - **Màn hình máy thật chỉ có giá trị duy nhất:** Chạy Live Canary ngay sau khi fix xong.
  - **Rủi ro ngâm máy thật:** Để app TikTok/Gmail ngâm màn hình >15-30 phút thường tự động bị timeout reload, khóa màn hình hoặc OS kill ngầm làm mất hiện trường, đồng thời làm nghẽn máy, trễ ca của đàn tài khoản phía sau.
  - **Kết luận:** Ngay khi gặp lỗi, lưu hiện trường số hóa (ảnh + xml) ra artifact/evidence root. Mọi script kết thúc (dù thành công hay lỗi) BẮT BUỘC phải dọn app đưa về HOME, không ngâm màn hình.

## 3. Universal Teardown: Đóng App & Đưa Về HOME Khi Kết Thúc
- Mọi script chạy trên thiết bị (Feed, Reg, Follow, Upload, 2FA, Gmail...) dù kết thúc thành công (`success`) hay thất bại (`failed`, `exception`, `manual-review`):
  - **BẮT BUỘC** nằm trong khối `finally:` thực thi:
    ```python
    try:
        shell(device, "am", "force-stop", package_name)
        shell(device, "input", "keyevent", "3")  # KEYCODE_HOME
    except Exception:
        pass
    ```
  - Tuyệt đối cấm logic cố tình bỏ qua cleanup khi failure để "giữ màn hình" (anti-pattern gây nghẽn đàn và làm gãy batch kế tiếp).
