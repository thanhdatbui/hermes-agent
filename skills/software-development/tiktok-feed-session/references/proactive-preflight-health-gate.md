# Proactive Pre-Flight Health Gate & In-Flight Self-Healing

## 1. Bối Cảnh & Kỷ Luật Vận Hành (User Directive 2026-10-17)
- **Tử huyệt "Chữa cháy sau ca" (Reactive Repair):**
  * Tình trạng: Để ca nuôi tự động chạy mù, 10–40 máy fail (do mất Wi-Fi, rớt USB, văng app, timeout ADB, slot rỗng), sau đó Coordinator mới vào gõ lệnh inspect/recover từng máy.
  * User chỉnh đốn dứt khoát: *"Tìm cách để phiên chạy k lỗi nữa đi chứ chạy xong ms fix đc thì ns gì"*.
  * **Kỷ luật cốt lõi:** BẮT BUỘC chuyển dịch 100% sang kiến trúc **Phòng vệ tiền trạm (Pre-flight Gate)** và **Tự hồi sinh nội phiên (In-flight Self-Healing)**. Không được để các lỗi đã biết lặp lại trong các ca tiếp theo.

## 2. Phân Loại 4 Nhóm Gốc Rễ Gây Fail Phiên
1. **Máy offline phần cứng (USB / Cáp / Cổng Hub) & Rớt Wi-Fi trước giờ G:**
   - Cáp lỏng, cổng USB hub chập chờn (M10, M30, M50).
   - M7 rớt sóng Wi-Fi AP Aruba 5GHz (-72 dBm), supplicant uninitialized.
   - Hậu quả: Nạp vào threadpool ngâm 3000s, chiếm worker của máy khác, báo fail phiên.
2. **Slot trống trong Excel bị tính nhầm thành Lỗi Script:**
   - Cụm Admin có các slot chưa nạp nick (như M255 row 6 rỗng).
   - Script văng `config-error: account row 6 is empty (no username)`, watchdog tính nhầm máy này vào danh sách Fail.
3. **Quá tải Socket ADB Remote trên Cụm Admin (MaxWorkers = 25):**
   - Cụm Admin chạy remote qua LAN `192.168.110.119:5037`.
   - 25 worker đồng loạt gửi lệnh `input swipe`, `screencap` làm nghẽn socket ADB daemon -> hàng loạt máy dính `adb command timed out` (M234, M245, M250, M262, M268, M272).
4. **App crash hoặc mất Focus / ATX-Agent chết giữa phiên:**
   - TikTok văng về launcher (`com.sec.android.app.launcher` như M44, M269, M274).
   - Tiến trình `atx-agent` (port 7912) bị Android OOM-killer dọn dẹp gây `ATX_SESSION_UNAVAILABLE` (M66, M74).

## 3. Kiến Trúc 4 Tầng Phòng Vệ & Tự Hồi Phục (Proactive 4-Gate Architecture)

### Tầng 1: Pre-flight Auto-Heal & Hardware Standby Filter (T-10 phút trước giờ G)
- **Soft Slate Reset:** Chạy batch `recover_stuck_s7.py` mức Soft cho toàn bộ 80 máy:
  * Force-stop TikTok cũ còn sót từ ca trước.
  * Đánh thức màn hình (Wake & Unlock).
  * Dọn sạch Recent Apps, đưa thiết bị về Launcher sạch.
- **Wi-Fi Preflight & Auto-Heal:**
  * Quét nhanh `ip addr show wlan0` và SSID.
  * Nếu mất IP hoặc sai profile: Kích hoạt ngay script kết nối lại đúng SSID (`kibe 1`, `kibe 2`, `admin 1`, `admin 2`).
- **Hardware Standby Isolation (Lọc máy hỏng vật lý):**
  * Nếu máy offline ADB hoặc sau 2 lần heal Wi-Fi vẫn không có IP: Đánh dấu `HARDWARE_STANDBY` và **LOẠI BỎ KHỎI DANH SÁCH BATCH CỦA CA ĐÓ**.
  * Tuyệt đối không nạp máy mất kết nối vật lý vào runner để tránh nghẽn threadpool và báo fail ảo.

### Tầng 2: Data Sanitization (Lọc slot trống trước khi nạp runner)
- Quét đối soát `taikhoan_run_safe.xlsx` theo Row của ca nuôi:
  * Nếu slot có `username` rỗng/None (như M255 row 6): Đánh dấu `STANDBY_NO_ACCOUNT`.
  * Không phân bổ slot rỗng vào danh sách máy chạy; triệt tiêu 100% mã lỗi `config-error`.

### Tầng 3: Điều Tiết Tải Concurrency Cụm Admin (Remote ADB Throttle)
- **Hạ MaxWorkers:** Giảm từ 25 xuống **12–15 workers** trên Cụm Admin để bảo vệ daemon ADB trên host remote `192.168.110.119`.
- **In-flight Stagger:** Bắt buộc áp dụng `-MachineStartStaggerMs "2000,8000"` giãn cách khởi động giữa các máy từ 2s đến 8s, triệt tiêu đỉnh sóng IO socket.

### Tầng 4: In-flight Self-Healing (Tự hồi sinh tại chỗ khi đang chạy)
- **ATX-Agent Auto-Revive:** Khi bắt gặp `ATX_SESSION_UNAVAILABLE`, runner tự động gọi lệnh `/data/local/tmp/atx-agent server -d` khởi động lại daemon trong 3 giây và retry dump UI, cấm ngắt phiên ngay lập tức.
- **Auto-Relaunch on Focus Lost:** Khi phát hiện package bị văng về Launcher:
  * Force-stop package -> Clear cache nhẹ -> Relaunch TikTok (cho phép tối đa 2 lần retry).
- **Safe Tap Dismiss Blocker:** Khi tap vào switch-anchor mà không mở được switcher (popup che), runner tự động tap vào vùng an toàn `(540, 1400)` để giải phóng màn hình rồi tap lại.
