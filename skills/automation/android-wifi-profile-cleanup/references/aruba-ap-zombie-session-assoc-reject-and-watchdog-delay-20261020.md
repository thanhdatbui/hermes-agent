# Aruba AP Zombie Session (Association Rejection status_code=1) & Watchdog Timing Triage

> Ref: Root-cause triage on Taadaa Farm Machine 7 (SM-G930F | Serial: 9885f63030454d3055) - 2026-10-20.

## 1. Triệu Chứng Hiện Trường: Aruba Association Rejection status_code=1

Khi thiết bị Android (Samsung S7) xin kết nối vào AP farm chuẩn (`kibe 1` trên AP Aruba `.253`, băng tần 5GHz 5180MHz):
```text
wpa_supplicant: Trying to associate with B0.F8.B0 (SSID='kibe 1' freq=5180 MHz)
wpa_supplicant: CTRL-EVENT-ASSOC-REJECT bssid=B0.F8.B0 status_code=1 assoc_reject.status 1
wpa_supplicant: wlan0: CTRL-EVENT-SSID-TEMP-DISABLED id=0 ssid="kibe 1" auth_failures=2 duration=20 reason=CONN_FAILED
WifiStateMachine: Assocation Rejection event: bssid=b0:b8:67:5b:f8:b0 reason code=1 timedOut=false
```

### Cơ chế & Phân lập phía AP vs Phía Thiết bị:
1. **Phía điện thoại đã sạch 100%:** Sau khi chạy Level 2 reboot phần cứng (`recover_stuck_s7.py --reboot`), chip Broadcom và Android OS khởi động lại từ đầu, xóa sạch cờ phạt in-memory.
2. **AP chủ động từ chối ngay từ khung Association Frame:** Quá trình bắt tay 802.11 không thể đi tới bước 4-Way Handshake WPA2. AP Aruba lập tức gửi Association Response với `status_code=1 (UNSPECIFIED_FAILURE)`.
3. **Bản chất phía AP:** Bảng Client Table trên AP Aruba Instant Controller vẫn lưu bản ghi cũ của thiết bị ở trạng thái treo (`0.0.0.0 NOFP` hoặc cờ Blacklist/Client-Match kẹt). Do đó, mọi nỗ lực kết nối từ MAC của thiết bị đều bị AP chặn ở tầng vật lý/MAC.
4. **Hành động sai lầm cần tránh:** Tiếp tục reboot điện thoại hoặc loop reconnect qua `adbjoinwifi`. Điều này chỉ làm tăng counter từ chối phía Android (`NETWORK_SELECTION_DISABLED_ASSOCIATION_REJECTION counter:8`).
5. **Giải pháp chuẩn xác:** Khởi động lại chính Access Point (reboot AP qua cổng PoE hoặc qua Instant AP Virtual Controller Web UI) để xả sạch bảng MAC/client session kẹt.

---

## 2. Bẫy Báo Cáo Chậm Của Watchdog (Watchdog Delayed Aggregation Trap)

### Hiện tượng:
Người vận hành thắc mắc: *"Ủa tao fix Wi-Fi rồi mà sao watchdog vẫn báo lỗi Mất kết nối Wi-Fi?"*

### Cơ chế:
1. Các ca nuôi (Ví dụ: Ca 1 - Phiên 1/2 sáng) bắt đầu từ rất sớm (ví dụ `06:03:13 AM`).
2. Tại thời điểm 06:03 AM, thiết bị thực sự chưa có Wi-Fi (`dumpsys connectivity: Wi-Fi not connected`).
3. Bộ tiền kiểm an toàn (Fail-Closed Shield) chặn đứng tác vụ nuôi của máy đó để bảo vệ tài khoản không bị lộ IP gốc.
4. Watchdog (`feed_session_watchdog.py`) chỉ tổng hợp và gửi báo cáo khi **toàn bộ 80-160 máy hoàn tất ca nuôi** (vài tiếng sau đó, ví dụ 10:45 AM).
5. Do đó, nội dung báo cáo của Watchdog phản ánh **kết quả tại thời điểm phiên nuôi bắt đầu**, không phải trạng thái thời gian thực lúc nhận được tin nhắn.
6. **Kỷ luật điều phối:** Bắt buộc kiểm tra dấu thời gian trong `run_manifest.json` và thư mục `runtime/<cluster>/live/<date>/row-<N>-<timestamp>` trước khi trả lời người vận hành để giải thích rõ timeline.
