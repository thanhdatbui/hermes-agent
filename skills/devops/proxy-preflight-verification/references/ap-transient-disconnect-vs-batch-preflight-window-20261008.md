# AP Wi-Fi Transient Disconnect vs Batch Preflight Concurrency Window

## Tình huống thực tế (08/10/2026)
- **Cảnh báo từ Watchdog:** Ca 2 - Phiên 2/2 (Chiều, Row 4) báo 78/80 máy Farm Kibe đồng loạt thất bại với lý do: `Mất Wi-Fi/Proxy (78)`.
- **Hiện trường kiểm tra:**
  * Toàn bộ 78 máy đều có `final_status: blocked-proxy-vpn`.
  * `total_swipes_completed: 0`.
  * `stop_reason: required router proxy is unreachable for <serial> (kill switch active or no connection): dumpsys connectivity: Wi-Fi not connected`.

## Phân tích nguyên nhân gốc rễ
1. **Mốc thời gian ngắt kết nối vs thời gian tiền kiểm:**
   - Tại `14:03:00.607`: AP Wi-Fi (`kibe 1`, BSSID `b0:b8:67:5b:f8:b0`) bị rớt sóng chớp nhoáng:
     `rec[405]: time=10-08 14:03:00.607 ... SSID: kibe 1 BSSID: 00:00:00:00:00:00 nid: -1 state: DISCONNECTED`
   - Tại `14:03:05.349`: Tiến trình batch runner `multi-machine-feed-session` chạy tiền kiểm `vpn_preflight.py` đồng loạt trên 80 máy.
   - Tại đúng tích tắc này, `dumpsys connectivity` trả về `Wi-Fi not connected`.
   - Cơ chế Kill-Switch kích hoạt đúng thiết kế, dừng phiên ngay lập tức để ngăn ngừa lộ IP WAN direct FPT.
2. **Thời gian tái kết nối:**
   - Tại `14:03:06.259`: Thiết bị bắt đầu `ASSOCIATING` với AP.
   - Tại `14:03:06.447`: Kết nối hoàn tất (`state: COMPLETED`).
   - Tổng thời gian mất kết nối thực tế chỉ kéo dài **~5.8 giây**. Do tiền kiểm batch diễn ra đúng trong 5.8 giây đó, 78 máy bị ngắt phiên hàng loạt.

## Phương pháp đối soát & Triển khai phục hồi
1. **Trích xuất đối soát lịch sử sự kiện Wi-Fi:**
   ```bash
   adb -s <serial> shell "dumpsys wifi | grep -E 'SUPPLICANT_STATE_CHANGE_EVENT' | tail -n 10"
   ```
   Nếu sau sự kiện `DISCONNECTED` xuất hiện `COMPLETED` trong vòng vài giây $\rightarrow$ Khẳng định là rớt sóng tức thời (transient AP drop).

2. **Rà soát proxy sau khi máy/router reboot:**
   - Khi máy hoặc router khởi động lại, kiểm tra cấu hình proxy trên từng thiết bị qua:
     ```bash
     adb shell settings get global http_proxy
     ```
   - Nếu trả về `:0` hoặc rỗng:
     * Kibe Farm: `python D:/Taadaa/AI-Tools/scripts/set_proxy_farm_adb.py`
     * Admin Farm: `ssh admin-farm "powershell -Command \"python -u D:/Taadaa/AI-Tools/scripts/set_proxy_farm_admin_adb.py\""`
