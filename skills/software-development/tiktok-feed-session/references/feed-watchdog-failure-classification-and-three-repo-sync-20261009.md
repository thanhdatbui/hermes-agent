# Feed Watchdog Failure Classification & Three-Repo Sync (2026-10-09)

## 1. Bối cảnh & Hiện tượng
Trong báo cáo của `feed_session_watchdog.py`, trước đây toàn bộ máy thất bại ở mục Lướt Feed bị gom chung vào nhãn gây hiểu nhầm:
```text
+ Fail (11): M7, M10, M20, M30, M63, M64, M67, M72, M73, M74, M76
  - Mất Wi-Fi/Proxy (7): M7, M10, M63, M64, M67, M74, M76
  - Lỗi App TikTok/Script (4): M20, M30, M72, M73
```
Thực tế:
- M74, M76: Proxy chưa được gán (`http_proxy is missing or :0`).
- M7, M10, M63: Mất kết nối Wi-Fi tại tầng Access Point (`ASSOCIATION_REJECTION` / `wlan0 down`).
- Một số máy: Rớt cáp USB / transport ADB chết (`device offline` / `not found in adb`).
Việc gom chung khiến Operator không thể phân biệt được nguyên nhân do hạ tầng mạng, do proxy, do phần cứng cáp, hay do lỗi app TikTok.

---

## 2. Thứ tự ưu tiên phân loại lỗi (Priority Classification Hierarchy)
Hàm helper `classify_feed_failure(reason: Any) -> str` bắt buộc tuân thủ thứ tự ưu tiên:
1. **Mất kết nối ADB/USB:**
   - Từ khóa: `device not found`, `device offline`, `not found in adb`, `no-run-recorded`, `unauthorized`, `transport`, `adb/usb`.
2. **Mất kết nối Wi-Fi (AP):**
   - Từ khóa: `wi-fi not connected`, `wifi not connected`, `association_rejection`, `no-carrier`, `dormant`, `wlan0 down`, `network disconnected`.
3. **Chưa gán Proxy / Proxy :0:**
   - Từ khóa: `missing or :0`, `http_proxy is missing`, `:0`, `proxy is not set on device`, `missing proxy`, `no proxy`.
4. **Nghẽn đường truyền Proxy / 4G:**
   - Từ khóa: `proxy is unreachable`, `proxy readiness timed out`, `connection refused`, `context deadline exceeded`, `proxy timeout`.
5. **Lỗi cấu hình Proxy chung:**
   - Từ khóa: `proxy`, `vpn`.
6. **Mặc định:**
   - `Lỗi App TikTok/Script` (áp dụng cho crash TikTok, crash uiautomator, script exception).

*Lưu ý:* Xét ADB và Wi-Fi trước Proxy để tránh trường hợp thông báo lỗi mạng chung (như connection timeout qua proxy) làm sai lệch bản chất rớt Wi-Fi hay tuột cáp.

---

## 3. Cấu trúc hiển thị chuẩn hóa trong Báo cáo Feed
Ngay sau dòng tổng kết `+ Fail (N): M...`, hiển thị chi tiết các nhóm con:
```text
• Lướt Feed:
  + Success (69): 1, 2, 3...
  + Fail (11): M7, M10, M20, M30, M63, M64, M67, M72, M73, M74, M76
    - Mất kết nối Wi-Fi (AP) (5): M7, M10, M63, M64, M67
    - Chưa gán Proxy / Proxy :0 (2): M74, M76
    - Lỗi App TikTok/Script (4): M20, M30, M72, M73
  + Trống slot/chưa có nick (0): Không có
```

---

## 4. Kỷ luật đồng bộ SHA256 Tam Giác (Three-Repo Sync)
Khi sửa đổi `feed_session_watchdog.py`, BẮT BUỘC phải đồng bộ khớp mã băm SHA256 trên cả 3 vị trí:
1. **Repo gốc vận hành:** `D:\Taadaa\tiktok-luot nuoi acc\scripts\feed_session_watchdog.py`
2. **Repo triển khai Hermes:** `D:\Taadaa\Hermes\deploy\hermes-home\scripts\feed_session_watchdog.py`
3. **Runtime live daemon:** `C:\Users\Kibe\AppData\Local\hermes\scripts\feed_session_watchdog.py`

Kiểm tra bằng:
```bash
python -c "
import hashlib
for p in [
    r'D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py',
    r'D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py',
    r'C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py'
]:
    with open(p, 'rb') as f:
        print(hashlib.sha256(f.read()).hexdigest(), p)
"
```
Đồng thời chạy `py_compile` và unit test trên cả 2 repo để đảm bảo 100% tests PASS (38/38 tests trên `tiktok-luot nuoi acc`, 10/10 tests trên `Hermes`).
