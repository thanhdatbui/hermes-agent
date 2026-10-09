# Quy chuẩn Session Teardown & Farm Screen Timeout Hygiene

## Bối cảnh & Nguyên nhân gốc
Trong quá trình vận hành automation (`python_runner`, uiautomator stubs, appium, adb), các thư viện thường đặt thuộc tính màn hình điện thoại thành không bao giờ tắt:
- `settings put system screen_off_timeout 2147483647` (Integer.MAX_VALUE)
- `svc power stayon true` hoặc `settings put global stay_on_while_plugged_in 3` (hoặc 7)

Hậu quả: Sau khi phiên kết thúc hoặc bị timeout/bỏ dở, thiết bị farm (cả Local và Remote Admin) tiếp tục sáng màn hình vĩnh viễn ở giao diện feed/profile/gallery, gây quá nhiệt, chai pin và dễ bị TikTok phát hiện bất thường làm nhả follow.

## Quy chuẩn Teardown (`_force_stop_tiktok_and_home`)
Tại flow `flows/multi_machine_feed_session.py` (và các flow tương đương):
1. **Force-stop app:** `am force-stop <target_package>`
2. **Về Home:** `input keyevent 3`
3. **Tắt stayon:** `svc power stayon false`
4. **Tắt stay_on_while_plugged_in:** `settings put global stay_on_while_plugged_in 0`
5. **Khôi phục timeout màn hình về 10 phút:** `settings put system screen_off_timeout 600000`

## Quy tắc Routing Máy Remote Admin
- Khi `machine >= 200` hoặc biến môi trường `ADB_SERVER_SOCKET` được set:
  Mọi lệnh gọi subprocess ADB fallback BẮT BUỘC phải đi kèm cờ:
  `-H 192.168.110.119 -P 5037`
- Không được gọi `adb -s <serial>` trần vì máy Local Kibe không thấy serial của cụm Admin.

## Watchdog & Healer toàn Farm (`farm_idle_screen_and_app_healer.py`)
- Định kỳ hoặc khi dọn dẹp hiện trường:
  - Quét mapping từ cả 2 file `PROXYgandienthoai.xlsx` (Local & Admin).
  - Kiểm tra lock trong `C:/Users/Kibe/.codex/device-locks/`. Nếu máy đang có lock với PID còn sống -> BỎ QUA không can thiệp.
  - Với máy rảnh: khôi phục power/timeout và kiểm tra `dumpsys window | grep mCurrentFocus` để kill TikTok về Home nếu bị treo.
