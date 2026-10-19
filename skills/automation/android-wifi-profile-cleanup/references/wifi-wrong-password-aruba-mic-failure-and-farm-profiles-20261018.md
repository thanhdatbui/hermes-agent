# Bẫy Sai Mật Khẩu Wi-Fi Theo Nhóm Máy & Triệu Chứng Aruba MIC Failure (2026-10-18)

## 1. Hiện Tượng & Căn Nguyên
Khi cấu hình hoặc khôi phục Wi-Fi cho máy farm (đặc biệt cụm Kibe M1–M40), agent thường mắc bẫy phản xạ nhớ mật khẩu `19051995` (do dùng chung cho Web Ruijie, MikroTik, AP `kibe 2` và `admin 1-2`).
Tuy nhiên, quy hoạch Wi-Fi Farm quy định mật khẩu phân tầng riêng biệt:
- **M1–M40 (`kibe 1` - Ch36):** BẮT BUỘC dùng mật khẩu **`23102025`**.
- **M41–M80 (`kibe 2` - Ch52/100):** Dùng mật khẩu **`19051995`**.
- **M201–M240 (`admin 1` - Ch116):** Dùng mật khẩu **`19051995`**.
- **M241–M280 (`admin 2` - Ch116):** Dùng mật khẩu **`19051995`**.
Nguồn chân lý duy nhất (Single Source of Truth): `D:/Taadaa/machine-config/farm_wifi_profiles.json`.

## 2. Dấu Hiệu Nhận Biết Trên Log Aruba AP & Android
- **Log Aruba Virtual Controller (`show ap debug auth-trace-buf`):**
  Khi máy gửi EAPOL Message 2 nhưng AP từ chối tiếp nhận (do MIC mismatch - sai pass):
  ```text
  station-up        * | <MAC> | <BSSID> | - | - | wpa2 psk aes
  wpa2-key1        <- | <MAC> | <BSSID> | - | 117 | None
  wpa2-key1        <- | <MAC> | <BSSID> | - | 117 | None
  wpa2-key1        <- | <MAC> | <BSSID> | - | 117 | None
  ```
  AP liên tục retransmit `wpa2-key1` (Message 1) vì không chấp nhận Message 2 từ máy, sau đó ngắt kết nối.
- **Log Aruba Virtual Controller (`show log system`):**
  `cli: AP 192.168.110.253: Client <MAC>: authenticate fail because integrity check failure in encrypted message`
  Đây là lỗi Message Integrity Check (MIC) trong quá trình bắt tay 4 bước WPA2 (4-way handshake), chứng minh 100% là do **sai mật khẩu Wi-Fi**.
- **Logcat Android (`wpa_supplicant` / `WifiStateMachine`):**
  `CTRL-EVENT-ASSOC-REJECT bssid=... status_code=1`
  `wlan0: CTRL-EVENT-SSID-TEMP-DISABLED id=... ssid="kibe 1" auth_failures=1`
  `updateNetworkSelectionStatusForWrongPassword: configKey="kibe 1"WPA_PSK networkStatus=NETWORK_SELECTION_DISABLED_BY_WRONG_PASSWORD`
  Khi gặp cờ này, Android tự động cấm kết nối vào SSID mục tiêu và đẩy supplicant về trạng thái `UNINITIALIZED` hoặc `DISCONNECTED`.
- **Màn hình Cài đặt Wi-Fi (WinRT OCR / Visual Evidence):**
  Dưới tên SSID xuất hiện dòng chữ cảnh báo màu đỏ: **"Đã xảy ra lỗi xác thực"** (Authentication error occurred). CỜ NÀY LÀ KHÓA CỨNG, OS SẼ KHÔNG BAO GIỜ TỰ KẾT NỐI LẠI NẾU KHÔNG PURGE PROFILE VÀ NẠP LẠI MẬT KHẨU ĐÚNG. CẤM BẢO USER CHỜ SÁNG HÔM SAU TỰ KHỎI.

## 3. Cạm Bẫy Android 8 Samsung S7 (SM-G930F/S)
- **Lệnh `cmd wifi` không tồn tại:** Android 8.0 không hỗ trợ service command `cmd wifi connect-network` hay `cmd wifi set-wifi-enabled` (sẽ báo lỗi hoặc exit 1).
- **Cơ chế nạp chuẩn:**
  1. Xóa sạch các profile lỗi/sai pass: `service call wifi 14 i32 <net_id>` (vòng lặp Net ID 0..9).
  2. Bắt buộc nạp qua `com.steinwurf.adbjoinwifi`:
     `am start -S -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid "<SSID>" --es password_type WPA --es password "<PASS>"`
  3. Chờ 8–10 giây cho handshake WPA2 và DHCP lease negotiation.
  4. Đóng Activity bằng phím Home: `input keyevent 3`.

## 4. Module Path Chuẩn Của `operator_device_lock`
Khi viết script hoặc dispatch worker can thiệp thiết bị, `operator_device_lock` nằm tại:
```python
import sys
sys.path.insert(0, r"D:/Taadaa/automation-core/src")
from automation_core.device_lock import operator_device_lock

with operator_device_lock(machine=N, serial="<SERIAL>", timeout=120.0):
    # thực thi lệnh ADB với flag -s <SERIAL>
```
CẤM TUYỆT ĐỐI gửi lệnh ADB mà không kèm `-s <serial>` hoặc quên bọc qua `operator_device_lock`.
