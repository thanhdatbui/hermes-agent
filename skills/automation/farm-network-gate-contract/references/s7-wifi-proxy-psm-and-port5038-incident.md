# Samsung S7 Wi-Fi / Proxy Probe Flapping, Thermal Throttling & Port 5038 Incident Runbook

## 1. Context & Incident Overview (Máy 7 Farm Case Study)

During network gate deployment on Máy 7 (serial `9885f63030454d3055`), the device experienced recurring flapping between `NOOP_HEALTHY` / `APPLIED` (Exit 0) and `L4_PROXY_DOWN` / `L3_NO_IP`, culminating in a sudden fleet-wide `device not found` on ADB port 5037.

---

## 2. Core Lessons & Root Causes

### A. Power Save Mode (PSM) Idle Timeout vs L4 Probe Tuning
- **Symptom:** Máy vừa nhận IP xong nhưng lệnh probe L4 liên tục trả về `ret=1 err=nc: Timeout` hoặc `No route to host`.
- **Root Cause:** Khi máy ở Launcher, chip Wi-Fi Broadcom tự động kích hoạt IEEE 802.11 Power Save Mode (PSM) để giảm nhiệt. Lệnh probe `toybox nc -w 3 -W 3` quá ngắn (3s) nên bị timeout trong chu kỳ ngủ của radio.
- **Remediation:** 
  1. Tăng timeout của `_nc_probe` lên 6s (`-w 6 -W 6`).
  2. Bọc vòng lặp retry 3 lần kèm sleep 1.0s.
  3. Sửa assert tương ứng trong test suite (`test_farm_network_gate.py`).

---

### B. `adbjoinwifi` Background Timer Interference
- **Symptom:** Máy đang kết nối Wi-Fi ổn định thì vài giây sau bị rớt kết nối đột ngột hoặc mất default route.
- **Root Cause:** App `com.steinwurf.adbjoinwifi` sau khi kích hoạt intent không tự thoát, timer nội bộ của app tự động gọi lại mỗi 4–5s với `CMD_ENABLE_NETWORK <net_id> true (disableOthers=true)`, làm đứt ngang quá trình đàm phán DHCP và route của Android 8.
- **Remediation:** Bắt buộc bổ sung `_adb_shell(serial, "am force-stop com.steinwurf.adbjoinwifi")` ngay trước khi return trong `_join_wifi`.

---

### C. `ECONNABORTED` ("Software caused connection abort") & Thermal Radio Throttling
- **Symptom:** Lệnh `nc` ra proxy `:20007` trả về `ret=1 err=nc: connect: Software caused connection abort`.
- **Root Cause:** Việc toggle Wi-Fi liên tục kết hợp sạc pin khiến chip Broadcom bị quá nhiệt, PMIC của Samsung S7 ngắt kết nối socket TCP đột ngột để bảo vệ phần cứng.
- **Remediation:** Dừng ngay việc spam lệnh ADB/join Wi-Fi, để máy nghỉ ngơi 5–10 phút để hạ nhiệt.

---

### D. Bẫy WinUSB Exclusive Hijacking trên ADB Port 5038 (Tiểu Vi Ghost Process)
- **Symptom:** `inspect_machine.py` hoặc `adb devices` trên port 5037 đột ngột báo `device not found` trên toàn bộ 77 máy dù không có ai rút cáp hay sập nguồn.
- **Root Cause:** Khi phần mềm Tiểu Vi (`xiaowei.exe`) mở lên, nó spawn một tiến trình ADB độc quyền trên cổng 5038 (`-P 5038`). Driver WinUSB của Windows chuyển toàn bộ endpoints sang server 5038, khiến server chính 5037 bị rỗng (`devices: ''`).
- **Remediation:**
  1. Kiểm tra tiến trình chiếm cổng 5038: `netstat -ano | findstr :5038`.
  2. Diệt dứt điểm tiến trình ADB 5038 mồ côi: `taskkill /F /PID <pid>`.
  3. Cổng 5037 lập tức nhận lại đủ 77 máy bình thường trong 1 giây.
