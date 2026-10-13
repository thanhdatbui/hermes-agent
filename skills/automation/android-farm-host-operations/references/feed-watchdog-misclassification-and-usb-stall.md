# Feed Session Watchdog Misclassification & USB Pipe Stall Investigation

## 1. Hiện Tượng (Incident 2026-10-13)
Báo cáo watchdog Ca 3 Phiên 2 (Row 3):
- Kibe: 32 Success, 48 Fail (34 Mất kết nối ADB/USB, 14 Lỗi App TikTok/Script).
- Admin: 20 Success, 59 Fail (44 Mất kết nối ADB/USB, 15 Lỗi App TikTok/Script).
- Tổng cộng 29 máy bị gán nhãn "Lỗi App TikTok/Script".

## 2. Bẫy Code trong `feed_session_watchdog.py`
Hàm `classify_feed_failure(reason)`:
```python
def classify_feed_failure(reason: Any) -> str:
    r = str(reason or "").lower()
    if any(k in r for k in ("device not found", "device offline", "not found in adb", "no-run-recorded", "unauthorized", "transport", "adb/usb")):
        return "Mất kết nối ADB/USB"
    if any(k in r for k in ("wi-fi not connected", ...)):
        return "Mất kết nối Wi-Fi (AP)"
    if any(k in r for k in ("missing or :0", ...)):
        return "Chưa gán Proxy / Proxy :0"
    if any(k in r for k in ("proxy is unreachable", ...)):
        return "Nghẽn đường truyền Proxy / 4G"
    if any(k in r for k in ("proxy", "vpn")):
        return "Lỗi cấu hình Proxy"
    return "Lỗi App TikTok/Script"  # <-- FALLBACK CHO TẤT CẢ CÁC LỖI CÒN LẠI
```

Khi máy bị đơ ADB trong lúc mở TikTok:
- `get_focused_activity` gọi `dumpsys window` hoặc ATX XML bị timeout/null.
- Runner ghi log: `prepare-tiktok failed to focus TikTok after launch`.
- Watchdog không thấy keyword "adb/usb" nên phân loại thành "Lỗi App TikTok/Script".

## 3. Quy Trình Kiểm Chứng Hiện Trường Thực Tế O(1)
1. **Đọc run summary:**
   `D:\Taadaa\runtime\kibe\live\<date>\<session>\<timestamp>\summary.txt`
   Bảng `multi_machine_summary` ghi rõ `stop_reason` của từng máy.
2. **Kiểm tra máy trực tiếp bằng `inspect_machine.py`:**
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <N>
   ```
   Nếu trả về `device not found` hoặc lệnh adb shell treo >15s -> chứng minh thiết bị đã mất ADB/treo pipe.
3. **Kiểm tra máy đang có trong `adb devices`:**
   Nhiều máy (như M2) vẫn còn serial trong `adb devices` nhưng pipe USB Linux kernel `/dev/android_adb` bị kẹt cứng, gõ lệnh shell treo vô hạn.
4. **Kết luận dứt khoát:**
   Không có lỗi app TikTok hay lỗi logic nào. Nguyên nhân là sập cụm USB EHCI sau thời gian dài chạy tải.
   Giải pháp duy nhất: Reboot PC để reset phần cứng EHCI controller.
