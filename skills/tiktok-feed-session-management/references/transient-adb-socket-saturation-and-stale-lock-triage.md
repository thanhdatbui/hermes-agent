# Transient ADB Socket Saturation & Stale Blocked Locks Triage

## 1. Triệu chứng & Nguyên nhân cốt lõi

### Hiện tượng 1: Cụm máy rớt "not found in adb devices" ảo hàng loạt
- **Triệu chứng:** Runner báo 10-17 máy rớt trạng thái `config-error` với stop_reason `Device serial ... was not found in adb devices`, trong khi kiểm tra ADB thực tế ngay sau đó thì phần lớn các máy đó vẫn đang `device` online.
- **Nguyên nhân cốt lõi:** Khi runner spawn đồng loạt nhiều worker luồng con (ví dụ 10-20 workers), các luồng này cùng lúc thực thi `adb.list_devices()` (hoặc `adb devices`) trong phạm vi vài chục đến vài trăm mili-giây. Điều này làm tràn socket buffer của ADB daemon hoặc gây timeout nghẽn tạm thời. Nếu script kiểm tra validation chỉ retry 2 lần liên tiếp không kèm exponential backoff (`ADB_ONLINE_ATTEMPTS = 2`), runner sẽ kết luận nhầm là thiết bị mất kết nối vật lý.
- **Quy tắc kiểm tra O(1) của Coordinator:**
  1. Kiểm tra kernel USB host:
     ```powershell
     powershell.exe -NoProfile -Command 'Get-PnpDevice -PresentOnly | Where-Object { $_.FriendlyName -like "*Descriptor Request Failed*" -or $_.FriendlyName -like "*Port Reset Failed*" } | Measure-Object | Select-Object -ExpandProperty Count'
     ```
     Nếu bằng 0: phần cứng/hub USB hoàn toàn bình thường, rớt kết nối chỉ là do socket saturation.
  2. So sánh danh sách `adb devices` hiện tại với danh sách máy bị báo fail để bóc tách máy offline thật sự vs máy bị rớt ảo.

---

### Hiện tượng 2: "Lock ngu" vướng phiên nuôi sau do crash / preserve_blocker_screen
- **Triệu chứng:** Một máy ở phiên trước gặp lỗi popup lạ, runner kích hoạt `preserve_blocker_screen: true` và kết thúc với `lock_status: "blocked"`, không teardown về HOME hay gỡ lock. File lock `C:\Users\Kibe\.codex\device-locks\serial_<serial>.lock.json` vẫn nằm trên đĩa dù tiến trình chính đã thoát (dead PID).
- **Hậu quả:** Sang phiên nuôi kế tiếp, runner kiểm tra thấy file lock còn tồn tại nên bỏ qua máy với lý do `skipped-device-locked`.
- **Quy trình xử lý:**
  - Nhận diện đúng PID cũ trong lock log và kiểm tra xem PID đó còn sống không (`psutil.pid_exists(pid)`).
  - Đảm bảo cronjob dọn lock mồ côi (`reap-dead-owner-locks`) chạy định kỳ hoặc chạy dọn trực tiếp các lock có dead PID trước khi kích hoạt lại runner.
