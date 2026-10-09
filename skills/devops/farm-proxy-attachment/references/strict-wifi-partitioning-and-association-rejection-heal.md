# Quy Hoạch Cứng Phân Vùng Wi-Fi & Xử Lý Bẫy Association Rejection trên Android 8 Farm

## 1. User Correction Cốt Tử: Cấm Tuyệt Đối Nhảy SSID Vãng Lai (Mạng "Dat")
- **Hiện tượng / Sai lầm cũ:** Khi máy S7 bị AP chính (`kibe 1`) từ chối kết nối (`ASSOCIATION_REJECTION`), script cứu hộ tự động nhảy sang SSID dự phòng `Dat`.
- **Cảnh báo từ User:** *"nhảy qua cái Dat thì có fake proxy k hay lộ mẹ ip direct"*.
- **Bản chất rủi ro kỹ thuật:**
  1. **Lệch Subnet & Routing LAN:** Mạng `Dat` cấp dải IP `192.168.10.x` (Gateway `192.168.10.254` hoặc router khác). Trong khi đó, toàn bộ hạ tầng Sing-box Inbound (`20001..20080`) và MikroTik firewall `FPT_LAN` được tối ưu trên dải LAN `192.168.110.0/24`. Khi máy bị kéo sang dải `192.168.10.x`, các kết nối TCP tới `192.168.110.2:2000N` có thể bị timeout, bất đối xứng định tuyến hoặc drop gói.
  2. **Vi phạm quy hoạch cách ly mạng:** Mỗi cụm máy được phân bổ chính xác vào từng AP Aruba tương ứng để cân bằng tải vô tuyến (RF balance). Việc nhảy dồn sang SSID khác sẽ phá vỡ quy hoạch tải của farm.
  3. **Nguy cơ an toàn IP:** Dù `vpn_preflight.py` có Fail-Closed Shield chặn `:0`, việc cho máy bắt SSID không thuộc farm là hành vi rủi ro nghiêm trọng.

## 2. Bảng Quy Hoạch Cứng SSID & Mật Khẩu (Bất Khả Xâm Phạm)
Mỗi máy **BẮT BUỘC CỐ ĐỊNH** duy nhất 1 SSID theo phân vùng máy, tuyệt đối không fallback sang bất kỳ mạng nào khác:

| Dải Máy | Cụm | SSID Cố Định | Mật Khẩu Chuẩn | AP Phụ Trách | Channel / Band |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Máy 01 – 40** | Kibe Trên | `kibe 1` | `23102025` | `192.168.110.253` (AP-325) | 36E (5GHz 80MHz) |
| **Máy 41 – 80** | Kibe Dưới | `kibe 2` | `19051995` | `192.168.110.252` (AP-325) | 100E (5GHz 80MHz) |
| **Máy 201 – 240** | Admin 1 | `admin 1` | `19051995` | `192.168.110.251` (IAP-315) | 116 (5GHz) |
| **Máy 241 – 280** | Admin 2 | `admin 2` | `19051995` | `192.168.110.250` (IAP-315) | 116 (5GHz) |

*Nguyên tắc:* Nếu máy không kết nối được SSID chính của nó sau 2 cấp cứu hộ, **giữ nguyên trạng thái lỗi và báo cáo hiện trường** (qua Watchdog) để kỹ thuật viên kiểm tra AP. CẤM tự ý đổi sang SSID khác.

## 3. Bản Chất Bẫy `ASSOCIATION_REJECTION` trên Android 8 (Galaxy S7)
1. **Nguyên nhân kích hoạt:** Khi máy S7 tắt màn hình sleep, AP Aruba gửi deauth dọn session (`Sapcp Ageout`). Khi máy thức dậy gửi `assoc-req`, nếu AP trả về mã lỗi 802.11 `status 1: UNSPECIFIED_FAILURE` liên tiếp 2-3 lần:
2. **Cái bẫy hệ thống:** `WifiConfigManager` của Android 8 tự động đưa BSSID vào BSSID Blocklist nội bộ và khóa mạng lại:
   ```text
   NETWORK_SELECTION_TEMPORARY_DISABLED disableReason=NETWORK_SELECTION_DISABLED_ASSOCIATION_REJECTION
   ```
3. **Tại sao toggle Wi-Fi hay reboot không hết:** Lệnh `svc wifi disable` ➔ `svc wifi enable` hoặc reboot máy không xóa được cờ này vì Android lưu trạng thái vào file `WifiConfigStore.xml` trên đĩa. Máy sẽ chủ động bỏ qua SSID đó trong mọi chu kỳ quét.

## 4. Quy Trình Cứu Hộ Chuẩn O(1) Bằng `adb-join-wifi.apk`
- Dùng công cụ `D:\Taadaa\AI-Tools\tools\adb-join-wifi.apk` gọi trực tiếp Java API `WifiManager.enableNetwork(netId, true)` từ tầng hệ điều hành Android:
  ```bash
  adb -s <SERIAL> install -r -g "D:\Taadaa\AI-Tools\tools\adb-join-wifi.apk"
  adb -s <SERIAL> shell "am start -n com.steinwurf.adbjoinwifi/.MainActivity -e ssid '<SSID_CHÍNH>' -e password_type 'WPA' -e password '<PASS_CHUẨN>'"
  ```
- **BẪY THAM SỐ CẦN TRÁNH:**
  Mã nguồn Java của `adb-join-wifi` đã tự động bọc dấu ngoặc kép:
  `conf.SSID = "\"" + ssid + "\"";`
  Do đó, khi truyền tham số qua `-e ssid` và `-e password`, **TUYỆT ĐỐI KHÔNG truyền thêm dấu ngoặc kép bên trong chuỗi** (ví dụ `-e ssid '"kibe 1"'` sẽ bị biến thành `""kibe 1""` gây lỗi không tìm thấy SSID).
- **Dọn sạch mạng rác đã lưu:**
  Nếu máy bị lưu nhiều SSID lạ (như `Dat`), phải vào Settings Wi-Fi bấm "QUÊN" (Forget) để tránh Android AutoJoin tự động chuyển mạng.
  Trên popup dialog của Samsung S7 (1080x1920):
  * Nút "QUÊN" nằm ở tọa độ: `x ~ 200, y ~ 1100`.
