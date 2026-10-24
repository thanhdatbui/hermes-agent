# Quy Tắc Điều Phối & Tự Cứu Hạ Tầng Farm (ADB, XiaoWei, Auto-Healer)

## 1. Kỷ Luật Rà Soát Cronjob / Script Hạ Tầng Hiện Hữu (Chống Vẽ Script Mới Rác)
- Khi gặp sự cố hạ tầng farm (ADB offline, kẹt socket, rớt WiFi, XiaoWei văng cam, màn hình không tắt, lock treo) hoặc khi User yêu cầu "tự fix bằng phần mềm":
- **CẤM TUYỆT ĐỐI** tự ý viết script mới từ đầu.
- **BẮT BUỘC** chạy `cronjob action='list'` rà soát các watchdog hạ tầng đã được đăng ký và vận hành trên farm:
  * `farm-adb-transport-healer` (`farm_adb_transport_auto_healer.py`, chạy mỗi 3 phút): Chuyên xử lý kẹt socket USB ADB transport, phục hồi XiaoWei stream, đánh thức màn hình và auto-reconnect.
  * `farm-wifi-auto-healer` (`farm_wifi_auto_healer.py`, chạy mỗi 5 phút): Tự động toggle Wi-Fi radio khi máy mất dải IP nội bộ `192.168.110.x`.
  * `farm-idle-screen-and-app-healer` (`farm_idle_screen_and_app_healer.py`, chạy mỗi 15 phút): Chuẩn hóa timeout tắt màn hình 10 phút, am force-stop TikTok và đưa về HOME khi máy nhàn rỗi.
  * `reap-dead-owner-locks` (`reap-dead-owner-locks-wrapper.py`, chạy mỗi 5 phút): Quét và dọn sạch lock file của các tiến trình cha đã chết trong `~/.codex/device-locks/`.
  * `farm-app-provision-watchdog` (`farm_app_provision_watchdog.py`, chạy 04:00 hàng ngày): Bù đủ 4 app chuẩn farm và nạp dynamic split APKs.
- Mọi cải tiến, vá lỗi hoặc nâng cấp phải thực hiện trực tiếp trên các file script hiện hữu tại `C:\Users\Kibe\AppData\Local\hermes\scripts\` và đồng bộ sang `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\`.

## 2. Bẫy Báo Cáo Ảo Trong Auto-Healer & Quy Tắc Two-Phase Verification Gate
- **Hiện tượng**: Auto-healer chạy định kỳ thấy máy `offline`, gửi lệnh `adb reconnect offline` rồi lập tức ghi nhận `healed_list.append("M... (offline -> reconnect)")` và báo cáo đã "cứu sống" thành công trên log/telemetry. Thực tế thiết bị vẫn `offline` do kẹt phần cứng Hub USB.
- **Căn nguyên**: Thiếu bước kiểm tra hậu kỳ (Verification Gate). Sau khi phát lệnh `reconnect`, script không đọc lại trạng thái thực tế từ ADB daemon.
- **Quy tắc Two-Phase Verification bắt buộc**:
  1. **Phase 1 (Pre-condition & Action)**: Phát hiện máy `offline` hoặc `HUNG` (>2.5s) trên máy không bị lock bởi active PID. Phát lệnh `adb reconnect`.
  2. **Phase 2 (Post-Verification Gate)**: Chờ 1.0s, chạy lại `adb devices` và lệnh shell ping `adb shell echo 1` (timeout 2.5s).
     * **PASS**: Chỉ khi thiết bị hiển thị `device` trong `adb devices` VÀ shell ping trả về `"1"` mới được ghi nhận là `HEALED`.
     * **FAIL**: Nếu thiết bị vẫn `offline` hoặc không phản hồi, KHÔNG được ghi vào `healed_list`. Đánh dấu `HARDWARE_BLOCKED` (lỗi phần cứng Hub USB: Port Reset Failed / Descriptor Failed / sụt nguồn), thông báo rõ ràng cho người vận hành thao tác vật lý tại dàn máy.

## 3. Quy Chuẩn Đồng Bộ ADB Binary Với XiaoWei Port 5037
- Trên máy Kibe Local, ứng dụng chiếu màn hình XiaoWei (`xiaowei.exe`) khởi động và sở hữu ADB daemon server trên port 5037 bằng binary:
  `C:\Program Files (x86)\xiaowei\tools\adb.exe` (ADB v34.x).
- Trong hệ thống còn tồn tại binary khác của GemPhoneFarm (`C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe` - ADB v35.x).
- **Nguy cơ**: Nếu script watchdog gọi ADB v35 kết nối vào ADB daemon v34 của XiaoWei, các gói tin handshake hoặc lệnh `reconnect` có thể bị lệch phiên bản, dẫn đến mất kết nối hoặc reset nhầm daemon.
- **Quy chuẩn**: Mọi script điều phối, watchdog và healer BẮT BUỘC ưu tiên sử dụng `C:\Program Files (x86)\xiaowei\tools\adb.exe` làm binary ADB mặc định khi tương tác với local host Kibe.
