# TikTok Clear Cache: Screen-Off Deep Link Wakeup & Canary Reproduction Discipline

> Ref: `scripts/clear-tiktok-cache.py`, `cron_clear_tiktok_cache.py`, Case 83/91.

## 1. Deep Link Intent vs Screen-Off (Dozing State)
- **Cơ chế:** TikTok Farm dọn cache bằng Deep Link Intent O(1):
  ```bash
  am start -a android.intent.action.VIEW -d "snssdk1180://clean_cache" com.ss.android.ugc.trill
  ```
  Lệnh này mở thẳng vào giao diện "Giải phóng dung lượng" trong <= 1.5 giây, triệt tiêu việc duyệt UI menu.
- **Nguyên nhân lỗi đêm:** Vào ban đêm (`03:00 - 05:00`), thiết bị ở trạng thái ngủ sâu (`Screen OFF / Dozing`). Intent VIEW gửi tới màn hình tắt sẽ bị Android hoãn hoặc không khởi chạy Activity đích lên foreground, dẫn tới Path 1 rớt và fallback sang vòng lặp dump XML nặng nề gây Timeout.
- **Giải pháp bắt buộc:** Bổ sung preflight wake-up trước khi bắn Intent:
  ```python
  shell(serial, "input keyevent KEYCODE_WAKEUP")
  shell(serial, "wm dismiss-keyguard")
  time.sleep(0.8)
  ```

---

## 2. Kỷ Luật Tái Hiện Hiện Trường Khi Canary (Screen-Off Reproduction)
- **Không test trên màn hình đang sáng:** Nếu màn hình đang bật sáng sẵn, deep link intent luôn hoạt động tốt, làm kết quả Canary bị ảo giác (False Positive).
- **Quy trình tái hiện chuẩn:**
  1. Đảm bảo thiết bị ở đúng trạng thái lỗi: kiểm tra `inspect_machine.py <N>` xác nhận `Màn hình: OFF (Sleep/Dozing)`.
  2. Chạy script dưới `operator_device_lock`:
     ```bash
     python D:/Taadaa/tools/with_device_lock.py --machine <N> -- python D:/Taadaa/automation-core/scripts/clear-tiktok-cache.py --machine <N> --serial <SERIAL>
     ```
  3. Kiểm chứng script tự đánh thức màn hình sáng lên (`ON (Awake)`), kích hoạt deep link, xóa cache về `0,0MB`.
  4. Chụp ảnh nghiệm thu trước khi teardown (`m<N>_cache_cleared.png`), soi mắt qua `browser_vision` xác nhận đúng số liệu `0,0MB`.
  5. Đưa thiết bị về lại trạng thái nghỉ pin (`Screen OFF`) để không ảnh hưởng đến ca chạy tiếp theo.

---

## 3. Phân Biệt Fix Script vs Phá Ca Chạy Của Thiết Bị
- Khi người dùng phản hồi sau báo cáo cronjob kèm lệnh "Fix đi":
  - **Mục tiêu ưu tiên số 1:** Fix lỗi trong codebase/script thông qua `unified_patch_pipeline.py`.
  - **CẤM:** Tự tiện bắn lệnh cứu hộ hàng loạt (`am force-stop`, reboot) lên các máy khi chưa đối soát lịch ca chạy (Ca 1 06:00, Gap A 06:50-08:00, Phiên 2 08:00...).
  - Không tự ý giải thích lan man về uiautomator thô khi hạ tầng chạy ATX-Agent / Deep Link.
