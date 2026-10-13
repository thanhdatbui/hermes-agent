# Farm Idle Screen & Lingering App Healing Patterns

## 1. Bản chất sự cố TikTok chạy thâu đêm trên farm
Khi một ca nuôi acc (feed/reconcile/follow) bị lỗi ADB timeout hoặc socket nghẽn giữa chừng:
- Tiến trình runner có thể crash hoặc thoát ngang xương mà không kịp chạy teardown (`cleanup_close_all_after_session`).
- TikTok bị bỏ quên ở foreground và tiếp tục tự động phát video/livestream thâu đêm.
- **Bẫy WakeLock (`FLAG_KEEP_SCREEN_ON`):** Android có cấu hình `screen_off_timeout = 600000` (10 phút), nhưng vì TikTok đang phát video, cờ WakeLock luôn được giữ $\rightarrow$ Bộ đếm 10 phút của Android **không bao giờ được kích hoạt**, màn hình sáng và nóng máy suốt đêm.

## 2. Xiaowei (Phóng Vệ) vs ADB Socket Disconnect
- **Xiaowei / Cửu Vệ / Tiểu Vi:** Sử dụng driver stream hình ảnh (minicap/framebuffer socket) riêng. Khi bus USB bắt đầu nghẽn, stream hình vẫn hiển thị màn hình mượt mà (chỉ máy mất kết nối vật lý hoàn toàn mới hiện ô cam).
- **ADB Command Shell:** Các lệnh `adb shell` (`settings get`, `dumpsys`, `input swipe`) bị nghẽn buffer trên USB 2.0 EHCI, dẫn đến timeout > 25s.
- **Hậu quả:** Nhìn trên màn hình quản lý tưởng máy vẫn bình thường và tưởng có "ca đêm" đang chạy, nhưng thực chất là app bị bỏ rơi sau khi ADB shell bị treo.

## 3. Tối ưu hóa lệnh kiểm tra App & Màn hình nhàn rỗi (O(1))
### A. Kiểm tra TikTok đang chạy (Tránh `dumpsys window`)
- **Sai lầm:** Dùng `dumpsys window` với timeout 3-4s. Trên Samsung Galaxy S7 (Android 8.0), `dumpsys window` xả ra hàng megabytes dữ liệu, gây nghẽn USB 2.0 và timeout âm thầm.
- **Chuẩn O(1):** Dùng lệnh Linux `pidof`:
  ```bash
  pidof com.ss.android.ugc.trill com.zhiliaoapp.musically
  ```
  Lệnh trả về PID trong `< 0.1s`. Nếu trả về PID trên máy không có device-lock $\rightarrow$ lập tức `am force-stop` và bấm Home (`keyevent 3`).

### B. Tắt màn hình an toàn (Tránh nút Power `keyevent 26`)
- **Sai lầm:** Gọi mù `input keyevent 26` (KEYCODE_POWER). Lệnh này là công tắc đảo (toggle) — nếu màn hình đang tắt, nó sẽ **bật sáng màn hình lên**!
- **Chuẩn O(1) Idempotent:** 
  1. Kiểm tra trạng thái nguồn siêu nhẹ qua `dumpsys power` (< 2KB):
     ```bash
     dumpsys power | grep -E "mWakefulness|Display Power:"
     ```
     - Sáng: `mWakefulness=Awake` hoặc `Display Power: state=ON`.
     - Ngủ: `mWakefulness=Asleep` hoặc `mWakefulness=Dozing`.
  2. Gửi lệnh ngủ chuyên biệt:
     ```bash
     input keyevent 223   # KEYCODE_SLEEP
     ```
     `keyevent 223` có tính chất lũy đẳng (idempotent): Nếu màn hình đang sáng $\rightarrow$ tắt về sleep; nếu đã tắt sẵn $\rightarrow$ giữ nguyên tắt, không bao giờ đánh thức máy.

## 4. Chuẩn hóa cài đặt Idle cho Dual-Cluster Farm
Trên mọi máy S7 cắm sạc USB 24/7, luôn chuẩn hóa:
```bash
settings put system screen_off_timeout 600000          # 10 phút
settings put global stay_on_while_plugged_in 0         # Tắt chế độ luôn sáng khi sạc
svc power stayon false
```
Khi máy rảnh và TikTok đã được đóng về Home, sau đúng 10 phút Android sẽ tự tắt màn hình ngay cả khi watchdog chưa kịp quét tới.
