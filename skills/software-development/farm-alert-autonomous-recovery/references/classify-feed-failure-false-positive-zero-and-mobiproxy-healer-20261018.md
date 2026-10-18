# Phân Tích Sự Cố Báo Cáo Nhầm "Chưa Gán Proxy / Proxy :0" Do Timestamp & Cơ Chế Auto-Heal MobiProxy 4G (18/10/2026)

## 1. Bản chất sự cố false-positive ":0" trong classify_feed_failure
- **Vị trí lỗi:** `scripts/watchdog/formatters.py` (hàm `classify_feed_failure`).
- **Nguyên nhân:** Danh sách từ khóa nhận diện `"Chưa gán Proxy / Proxy :0"` chứa substring trần `":0"`.
- **Hệ quả false-positive diện rộng:** Mọi chuỗi lỗi hoặc stop_reason chứa timestamp giờ:phút:giây có phút hoặc giây từ 00 đến 09 (ví dụ `13:00:30`, `18:02:19`, `20:01:51`, hoặc timezone `+00:00`) đều bị khớp chuỗi `":0"` và bị ép vào nhãn `"Chưa gán Proxy / Proxy :0"`.
  * **Máy 7:** Bị giữ lock bởi `farm_network_gate.py` với `started_at=2026-10-18T13:00:30` -> Bị báo nhầm là chưa gán proxy dù máy đang được gán `192.168.110.2:20007`.
  * **Máy 69:** Bị rớt mạng proxy do cổng MobiProxy 4G 5137 bị dead modem lúc `18:02:19` -> Khớp `":0"` trong `18:02:19` và bị báo nhầm là chưa gán proxy dù máy đang gán `192.168.110.2:20069`.
- **Quy chuẩn sửa mã nguồn:**
  * CẤM DÙNG SUBSTRING TRẦN `":0"`. Bắt buộc thay bằng token chuẩn `empty_or_zero` / `empty or zero`.
  * Bổ sung nhận diện `device lock active`, `device-lock` trả về đúng danh mục **`Kẹt Device Lock`**.
  * Bổ sung `egress ip`, `unreachable` vào danh mục **`Nghẽn đường truyền Proxy / 4G`**.

## 2. Invariant Quy Hoạch Mạng Farm: 100% Proxy, CẤM Direct
- Toàn bộ máy Farm (Kibe M1–M80: ports 20001–20080; Admin M201–M280: ports 10008–10035) BẮT BUỘC chạy qua Proxy Singbox/3proxy trên `192.168.110.2`.
- **CẤM TUYỆT ĐỐI** kết luận máy chạy Direct hoặc bypass proxy. Cơ chế Preflight fail-closed ngắt phiên ngay lập tức nếu máy mất proxy để chống rò rỉ IP nhà mạng.
- Khi một máy bị báo lỗi mạng hoặc timeout: Đối soát liveness cổng proxy bằng TCP connect và HTTP egress (`http://ifconfig.me/ip`).

## 3. Khôi phục Modem 4G Cụm MobiProxy Bằng Tool Auto-Healer
- Khi phát hiện cổng proxy Singbox trả về `WinError 10054` hoặc `HTTP Error 502 Bad Gateway`:
  * Chạy công cụ kiểm tra và tự phục hồi: `python D:/Taadaa/AI-Tools/scripts/mobiproxy_auto_healer.py --check-and-heal`.
  * Script tự động gọi API `/proxy_recreat` tới cụm `test.taadaa.click` để redial modem 4G và cấp lại IP mới trong 15s.
  * Đảm bảo cronjob `mobiproxy-auto-healer-watchdog` (`7e5e3980dde1`) luôn ở trạng thái enabled/scheduled (chu kỳ 5 phút).

## 4. Ranh Giới Thiết Bị Offline PnP vs Kẹt Socket EHCI USB 2.0
- Khi ADB báo thiết bị `offline` hoặc `not found` sau ca nuôi:
  * Kiểm tra tầng Windows PnP (`Get-PnpDevice` qua `admin_ssh.py` hoặc local): Nếu thiết bị vẫn báo `Status: OK` ở lớp `SAMSUNG Mobile USB Composite Device`, cáp vật lý vẫn còn nguyên vẹn.
  * Nguyên nhân do đứt pipe `/dev/android_adb` trên kernel Linux của điện thoại khi bus USB 2.0 EHCI bị spike tải cao. Do chân sạc VBUS 5V vẫn duy trì, điện thoại không tự nhận uevent để restart daemon `adbd`.
  * **CẤM TUYỆT ĐỐI BẮT USER ĐI RÚT CÁP THỦ CÔNG.**
  * Khởi động lại Host PC (Reboot) gửi xung System Bus Reset từ BIOS sẽ ngắt VBUS tạm thời, đưa 100% thiết bị về lại trạng thái xanh (`device`).
- **Quy chuẩn lịch Reboot:** Giữ vững 3 mốc trước 3 ca chính (05:20, 11:20, 17:20 với 40p đệm). Tuyệt đối không reboot theo phiên lẻ (chu kỳ 2 tiếng) vì gây lãng phí 40p đệm boot, còi hú quạt ồn và ngắt quãng các batch-job cào/render/2FA.
