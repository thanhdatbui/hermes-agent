# Bẫy Parse `summary.txt` Nuốt `stop_reason` Gây Báo Sai Hàng Loạt 'Lỗi cấu hình Proxy' (2026-10-10)

## Hiện tượng thực tế
Trên báo cáo tổng kết nuôi acc (`tiktok-feed-session-watchdog`), danh sách máy lỗi hiển thị hàng loạt:
- Farm Kibe: `- Lỗi cấu hình Proxy (3): M10, M35, M47` (trước đó M7, M10, M35).
- Farm Admin: `- Lỗi cấu hình Proxy (36): M210, M212, M217, M236.. M280` (sau giảm còn 8 máy ở Phiên 2).

Người vận hành thắc mắc: *"Lỗi cấu hình proxy lắm thế"* vì tưởng hệ thống proxy MikroTik / Singbox bị sập hoặc cấu hình sai.

## Nguyên nhân kỹ thuật gốc (Root Cause)
1. **Thứ tự các trường trong `summary.txt`:**
   Khi một máy bị chặn fail-closed tại tiền kiểm `vpn_preflight`, file `summary.txt` được ghi ra có cấu trúc:
   ```text
   status: fail
   final_status: blocked-proxy-vpn
   message: [device-lock] machine 10 blocked by proxy VPN preflight
   reason: [device-lock] machine 10 blocked by proxy VPN preflight
   stop_reason: device is offline or ADB/USB disconnected for 988627464e374e3234: adb.exe: device '988627464e374e3234' not found
   ```
2. **Lỗi logic vòng lặp parse cũ:**
   Trong `feed_session_watchdog.py` (`parse_run_all`):
   ```python
   reason = ""
   for line in c.splitlines():
       if line.startswith("reason:") or line.startswith("final_status:"):
           val = line.split(":", 1)[1].strip()
           if val != "success":
               reason = val
               break
   ```
   Do `final_status: blocked-proxy-vpn` xuất hiện ở dòng 2 trước `stop_reason:`, vòng lặp bắt trúng `final_status` và lập tức `break`. Kết quả: `reason` nhận giá trị `"blocked-proxy-vpn"`.
3. **Phân loại sai nhãn trong `classify_feed_failure`:**
   ```python
   def classify_feed_failure(reason: Any) -> str:
       r = str(reason or "").lower()
       if any(k in r for k in ("device not found", "device offline", "adb/usb", ...)):
           return "Mất kết nối ADB/USB"
       if any(k in r for k in ("wi-fi not connected", "wifi not connected", ...)):
           return "Mất kết nối Wi-Fi (AP)"
       if any(k in r for k in ("missing or :0", ...)):
           return "Chưa gán Proxy / Proxy :0"
       if any(k in r for k in ("proxy is unreachable", ...)):
           return "Nghẽn đường truyền Proxy / 4G"
       if any(k in r for k in ("proxy", "vpn")):
           return "Lỗi cấu hình Proxy"
       return "Lỗi App TikTok/Script"
   ```
   Vì `reason = "blocked-proxy-vpn"`, nó không chứa từ khóa ADB hay Wi-Fi, nhưng lại chứa `"proxy"` và `"vpn"`. Kết quả: 100% máy bị chặn ở preflight đều bị phân loại thành **"Lỗi cấu hình Proxy"**.

## Bóc tách hiện trường thực tế
Đối soát từng máy trong `D:/Taadaa/runtime/kibe` và `D:/Taadaa/runtime/admin` tại Ca 1 (Row 2, 2026-10-10):
- **M10 (Kibe):** `stop_reason: device is offline or ADB/USB disconnected for 988627464e374e3234: adb.exe: device '988627464e374e3234' not found` ➔ **Mất kết nối ADB/USB** (lỏng cáp).
- **M35 (Kibe):** `stop_reason: device is offline or ADB/USB disconnected for ce061606c3322c1603: adb.exe: device offline` ➔ **Mất kết nối ADB/USB** (lỏng cáp/transport hang).
- **M47 (Kibe):** `stop_reason: required router proxy is unreachable for ce11160bd0119a1203: dumpsys connectivity: Wi-Fi not connected` ➔ **Mất kết nối Wi-Fi (AP)** (máy pin 2%, đang cắm sạc).
- **M263, M265, M270, M274, M275 (Admin):** `stop_reason: device is offline or ADB/USB disconnected` ➔ **Mất kết nối ADB/USB**.
- **M210, M212, M217 (Admin):** `stop_reason: dumpsys connectivity: Wi-Fi not connected` ➔ **Mất kết nối Wi-Fi (AP)**.

Thực tế: **0 máy nào bị lỗi cấu hình Proxy.**

## Giải pháp chuẩn hóa (Stop-Reason Priority)
Cập nhật parser `summary.txt` trong `feed_session_watchdog.py`:
```python
st = "success" if "final_status: success" in c else "fail"
r_map = {l.split(":", 1)[0].strip(): l.split(":", 1)[1].strip() for l in c.splitlines() if ":" in l}
stop_r = r_map.get("stop_reason", "")
reason = stop_r if (stop_r and stop_r != "None") else (r_map.get("reason") or r_map.get("final_status", ""))
if any(k in reason.lower() for k in ("is empty (no username)", "does not have valid row")):
    st = "skipped-empty"
```

Unit test kiểm chứng:
`tests/test_feed_session_watchdog.py::test_parse_run_all_extracts_stop_reason_priority` mô phỏng `summary.txt` có `final_status: blocked-proxy-vpn` và `stop_reason: device is offline...` đảm bảo trả về đúng phân loại `"Mất kết nối ADB/USB"`.
