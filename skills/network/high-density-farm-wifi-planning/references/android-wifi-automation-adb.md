# Android Fleet Wi-Fi Automation & Troubleshooting via ADB

When configuring, recovering, or verifying Wi-Fi connections across large Android phone farms (80–160+ devices, Samsung S7 Android 8):

---

## 🛑 BẮT BUỘC: QUY TẮC AN TOÀN HẠ TẦNG (CẤM TỰ SỬA AP KHI FIX ĐIỆN THOẠI)
* **Chỉ thao tác trên máy đích:** Khi nhận task kết nối, đổi mật khẩu hoặc sửa Wi-Fi cho một máy cụ thể (ví dụ: *\"vào máy 7 xóa quên wifi admin rồi connect wifi kibe1\"*), **CHỈ ĐƯỢC THAO TÁC TRÊN ĐIỆN THOẠI ĐÓ** qua ADB / UI Settings.
* **CẤM TUYỆT ĐỐI tự ý gọi API Aruba (`swarm.cgi`), đổi passphrase, thay đổi cấu hình SSID, hoặc reboot/reload AP:** 
  - Mỗi AP gánh từ 35–40 điện thoại chạy automation liên tục.
  - Việc tự ý reload AP hoặc đổi passphrase trên AP sẽ làm toàn bộ 40 máy cùng Rack bị rớt mạng ngay lập tức (`dumpsys connectivity: Wi-Fi not connected`), kích hoạt kill switch khiến cả ca chạy farm (hàng chục máy) bị dừng khẩn cấp và fail hàng loạt với lỗi `blocked-proxy-vpn`.
  - Mọi can thiệp hạ tầng mạng tập trung (Aruba, MikroTik, Switch PoE) BẮT BUỘC phải có lệnh chỉ định rõ ràng từ User.
* **Quy hoạch phân bổ 40 máy/AP:**
  - Rack 1 (M1 – M40): Chỉ kết nối `kibe 1` (AP .253).
  - Rack 2 (M41 – M80): Chỉ kết nối `kibe 2` (AP .252).
  - Admin (M201 – M240): `admin 1` (AP .208).
  - Admin (M241 – M280): `admin 2` (AP .124).
  - Nếu máy tầng dưới bắt nhầm vào SSID tầng trên, AP sẽ đầy 40 slot và từ chối các máy còn lại của rack.

---

## 1. Zero-UI Wi-Fi Association via `adb-join-wifi.apk`

Interacting with Android Wi-Fi settings UI via ADB taps or UIAutomator is brittle in dense farms (soft keyboard covers buttons, scanned networks list shifts dynamically, auth dialogs mis-tap).

Use the headless helper tool located at `D:/Taadaa/AI-Tools/tools/adb-join-wifi.apk`:

### A. One-Step Connect Command
> **Lưu ý cú pháp bắt buộc:** BẮT BUỘC dùng cờ `--es` cho tất cả chuỗi (đặc biệt là SSID có khoảng trắng như `"kibe 1"`). Nếu dùng `-e ssid 'kibe 1'`, shell Android sẽ cắt chuỗi tại dấu cách và chỉ truyền `"kibe"`, khiến hàng loạt máy quét vô vọng và mất mạng! Phải có `--es password_type WPA` (hoặc WEP).

```bash
# 1. Install helper APK (idempotent, stream install)
adb -s <SERIAL> install -r "D:/Taadaa/AI-Tools/tools/adb-join-wifi.apk"

# 2. Trigger automated WPA2 association (BẮT BUỘC dùng --es cho chuỗi có khoảng trắng và cờ -S để force-stop tái khởi động Activity)
adb -s <SERIAL> shell 'am force-stop com.steinwurf.adbjoinwifi && am start -S -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid "<SSID>" --es password_type WPA --es password "<PASSWORD>"'

# 3. Bounce Wi-Fi radio to force clean DHCP lease & route table assignment
adb -s <SERIAL> shell "svc wifi disable; sleep 1; svc wifi enable; sleep 3"
```

### B. Giới hạn quyền của `adbjoinwifi` trên Android 8+ (Pitfall & Clean Slate Wipe)
* **Lỗi `App does not have admin access`:** Nếu profile Wi-Fi của SSID đó đã được lưu từ trước bởi Android System Settings (`cuid=1000 / android.uid.system:1000`), `adbjoinwifi` chạy dưới UID thường (shell/app) sẽ **KHÔNG THỂ GHI ĐÈ MẬT KHẨU MỚI** và âm thầm dùng lại thông tin xác thực cũ:
  ```text
  W adbjoinwifi: wifi network already exists.
  W adbjoinwifi: App does not have admin access, unable to modify a wifi network created by another app
  ```
* **Cách xử lý chuẩn khi đổi mật khẩu:**
  1. Bắt buộc phải **xóa/quên mạng cũ (Forget Network)** trước trong Cài đặt hệ thống để giải phóng Network ID khỏi `ConfiguredNetworks`.
  2. Sau khi đã quên mạng cũ, gọi `adbjoinwifi` để tạo profile mới từ đầu (sẽ cấp Network ID mới và áp dụng mật khẩu mới thành công).
  3. Hoặc dùng ATX-Agent / UI Automator mở form nhập mật khẩu trên System Settings để nhập mật khẩu mới và bấm `LƯU` / `KẾT NỐI`.

---

## 2. Xử Lý Lỗi Xác Thực & Treo Driver Wi-Fi (Samsung S7 Android 8)

### A. Bẫy giao diện sửa mật khẩu: `(chưa thay đổi)`
* Trên Samsung Android 8, khi mở form sửa mật khẩu mạng Wi-Fi đã lưu (`Quản lý cài đặt mạng`), trường mật khẩu hiển thị chuỗi giữ chỗ `(chưa thay đổi)`.
* Nếu chỉ gọi `input text <PASSWORD>` mà không focus hoặc không xóa chữ cũ, Android giữ nguyên mật khẩu cũ và bấm `LƯU` vô tác dụng.
* **Khắc phục:** Tốt nhất luôn chọn **Quên mạng (Forget)** để xóa trắng profile mạng đó rồi kết nối lại từ danh sách quét, hoặc dùng tính năng Reset cài đặt mạng bên dưới.

### B. Phục hồi Driver Wi-Fi bị đơ bằng "Khôi phục cài đặt mạng"
Khi máy dính lỗi lặp kết nối, `wpa_supplicant` có thể đưa mạng vào trạng thái:
`NETWORK_SELECTION_TEMPORARY_DISABLED` do `ASSOCIATION_REJECTION counter >= 8` hoặc driver bị rớt cờ carrier (`ifconfig wlan0` báo `UP BROADCAST MULTICAST` nhưng mất cờ `RUNNING`, `RX packets: 0`).

Trong tình huống này, lệnh `svc wifi disable/enable` hay `reboot` có thể không giải phóng hết lỗi cache mạng. Thực hiện quy trình Reset Cài đặt mạng qua UI:
1. Mở Cài đặt: `adb shell "am start -a android.intent.action.MAIN -c android.intent.category.HOME"`
2. Vào `Quản lý chung` -> `Đặt lại` -> `Khôi phục cài đặt mạng` (Reset network settings).
3. Bấm `XÓA CÁC CÀI ĐẶT`.
4. Bật lại Wi-Fi: `adb shell "svc wifi enable"`.
5. Quét và kết nối lại mạng mới: Thao tác này xóa trắng toàn bộ cache cấu hình Wi-Fi/Bluetooth bị lỗi mà hoàn toàn không ảnh hưởng tới dữ liệu hay ứng dụng trên máy.

### C. Phân biệt lỗi bắt tay WPA2 vs lỗi từ chối AP
* **`ASSOC-REJECT status_code=1` (diễn ra trong <5ms trên logcat):** Thường là do driver nội bộ của điện thoại tự reject do profile mạng bị disable tạm thời hoặc radio AP đầy tải (chạm mốc 40 máy).
* **`MIC failed in WPA2 Key Message 2` (trên log security của AP):** Bắt tay 4-way handshake thất bại do **SAI MẬT KHẨU WPA2-PSK**. Điện thoại sẽ hiện thông báo *"Đã xảy ra lỗi xác thực"*.
* **`Sapcp Ageout (internal ageout) & Bẫy Ghost Association / BssidBlocklistMonitor trên Android 8`:**
  - **Cơ chế:** Khi điện thoại reboot hoặc rớt mạng đột ngột, AP Aruba vẫn giữ entry MAC cũ trong bảng client (`Sapcp Ageout` sequence). Khi máy gửi lại gói `assoc-req`, hoặc khi máy nghe thấy BSSID của AP khác cùng phòng nhưng khác zone (ví dụ máy M1–40 nghe thấy BSSID của `kibe 2` trên AP `.252`) và gửi nhầm request, AP phản hồi `status=1: UNSPECIFIED_FAILURE` (`ASSOCIATION_REJECTION_EVENT`).
  - **Bẫy BssidBlocklistMonitor & Khóa Cứng Cấu Hình:** 
    Khi Android nhận `status=1` liên tiếp (≥ 4 lần), hai tầng khóa sẽ được kích hoạt cùng lúc:
    1. Tầng Driver/BSSID: `trackBssid: disable <BSSID> reason code 1` đưa địa chỉ MAC của AP vào blacklist quét.
    2. Tầng WifiConfigStore: `networkStatus=NETWORK_SELECTION_TEMPORARY_DISABLED disableReason=NETWORK_SELECTION_DISABLED_ASSOCIATION_REJECTION`.
    * **Tại sao `svc wifi` và `reboot` vô tác dụng:** Lệnh `svc wifi disable && svc wifi enable` chỉ restart stack radio tạm thời nhưng không xóa cờ phạt trong `WifiConfigManager`. Kể cả reboot máy, Android nạp lại `WifiConfigStore.xml` từ đĩa và vẫn giữ nguyên trạng thái DISABLED. Điện thoại sẽ **bỏ qua hoàn toàn SSID đó trong mọi chu kỳ quét tiếp theo**, nằm trơ ở trạng thái DISCONNECTED.
  - **Quy trình Phục Hồi 2 Tầng Chuẩn Hóa (Anti-Desync & Strict AP Isolation):**
    1. **Tầng 1 (Nhẹ):** Toggle `svc wifi disable` ➔ sleep 1 ➔ `svc wifi enable` ➔ sleep 3 (giải phóng treo carrier / DORMANT thông thường).
    2. **Tầng 2 (Bẻ khóa BSSID Blocklist bằng adb-join-wifi):** Nếu sau Tầng 1 vẫn không nhận IP (dính `ASSOCIATION_REJECTION`), bắt buộc gọi `adb-join-wifi.apk` qua intent với cờ `--es`:
       ```bash
       adb -s <SERIAL> shell 'am force-stop com.steinwurf.adbjoinwifi && am start -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid "<SSID>" --es password_type WPA --es password "<PASSWORD>"'
       ```
       Lệnh này kích hoạt Java API `WifiManager.enableNetwork(netId, true)` — cơ chế duy nhất xóa trắng cờ `NETWORK_SELECTION_TEMPORARY_DISABLED` và giải phóng BSSID blocklist qua ADB mà không cần chạm tay vào màn hình.
    3. **🛑 CẤM TUYỆT ĐỐI ĐỀ XUẤT NHẢY CHÉO AP ĐỂ TRỐN LỖI HOẶC FALLBACK SANG SSID NGOÀI (`Dat`):**
       - M1–M40: BẮT BUỘC duy trì `kibe 1` (AP .253, pass `23102025`).
       - M41–M80: BẮT BUỘC duy trì `kibe 2` (AP .252, pass `19051995`).
       - M201–M240: BẮT BUỘC duy trì `admin 1` (AP .251, pass `19051995`).
       - M241–M280: BẮT BUỘC duy trì `admin 2` (AP .250, pass `19051995`).
       - **CẤM ĐỀ XUẤT DỒN MÁY:** Khi một AP bị kẹt bắt tay, CẤM đề xuất chuyển máy sang AP khác (ví dụ M7 chuyển sang `kibe 2`) để né lỗi. Việc này phá vỡ hạn mức 40 máy/AP, gây quá tải bộ nhớ và radio AP đích.
       - Nếu AP bị kẹt radio phần cứng hoặc bão hòa session (`Sapcp Ageout`), SSH vào AP đó gửi lệnh `reload` (hoặc `disconnect-user` / khởi động lại sạch) để dọn sạch session kẹt.
       - CẤM TUYỆT ĐỐI fallback sang SSID ngoài quy hoạch như `Dat` (lệch subnet và nguy cơ lộ Direct IP).
       - **Cú pháp Intent bắt buộc:** Khi gọi `adb-join-wifi.apk`, BẮT BUỘC dùng `--es ssid "kibe 1"` thay vì `-e ssid 'kibe 1'`. Nếu dùng `-e`, shell Android sẽ cắt chuỗi tại khoảng trắng thành `ssid="kibe"`, làm máy quét vô tận và rớt mạng toàn cụm.
* **`Wlan driver excessive tx fail quick kickout` (trên log AP):** Do công suất phát AP quá mạnh (ví dụ đặt 15 dBm trên kệ sắt) gây phản xạ kim loại và bão hòa bộ thu máy, hoặc do can nhiễu kênh. Khắc phục: hạ công suất về 6–9 dBm (tối đa 12 dBm) và chuyển sang kênh UNII-1 thấp (kênh 36E).

### D. Treo Driver Broadcom DHD PCIe (state DORMANT / NO-CARRIER) trên S7
* **Triệu chứng:** Biểu tượng Wi-Fi biến mất trên thanh trạng thái, `dumpsys wifi` báo `Wi-Fi is enabled` nhưng `mWifiInfo: [SSID: <unknown ssid>, Supplicant state: DISCONNECTED/UNINITIALIZED, RSSI: -127]`.
* **Hiện trường mạng:** Kiểm tra qua `adb shell "ip addr show wlan0"` thấy:
  `wlan0: <NO-CARRIER,BROADCAST,MULTICAST,UP,LOWER_UP> ... state DORMANT`, `RX packets: 0`.
* **Nguyên nhân gốc rễ:** Chip Wi-Fi Broadcom trên Samsung Exynos có tính năng Runtime PM (`dhd_runtimepm_state: DHD Idle state!! -> dhdpcie_bus_suspend: Entering suspend state -> D3 Ack`). Khi máy idle hoặc tắt màn hình, Android mặc định kích hoạt Suspend Optimization, đẩy bus Broadcom DHD PCIe vào chế độ ngủ sâu D3. Khi thức dậy bị lỗi ring buffer (`Bus is in power save state. Skip processing rest of ring buffers`), rớt cờ carrier khiến `wpa_supplicant` kẹt cứng ở `DisconnectedState` và Android 8 không tự kích hoạt lại.
* **Xử lý nhanh O(1):** Reset stack radio để đánh thức PCIe bus và khởi động lại supplicant:
  ```bash
  adb -s <SERIAL> shell "svc wifi disable && sleep 1 && svc wifi enable"
  ```
* **Bộ 3 lệnh Hardening chống rớt Wi-Fi vĩnh viễn (chạy qua ADB):**
  ```bash
  # 1. Tắt Suspend Optimization để Broadcom DHD không đưa PCIe bus vào D3 suspend khi màn hình tắt/idle
  adb -s <SERIAL> shell "settings put global wifi_suspend_optimizations_enabled 0"

  # 2. Bật quét Wi-Fi nền liên tục để OS luôn chủ động tìm và re-associate AP khi có gián đoạn
  adb -s <SERIAL> shell "settings put global wifi_scan_always_enabled 1"

  # 3. Tắt Wi-Fi Watchdog mặc định của Android (tránh tự ngắt khi có dao động tín hiệu tạm thời)
  adb -s <SERIAL> shell "settings put global wifi_watchdog_on 0"
  ```
* **Cơ chế Watchdog tự phục hồi cấp Farm:** 
  Triển khai script `farm_wifi_auto_healer.py` chạy qua Cron (`*/5 * * * *`, `no_agent: true`). Nếu phát hiện máy nào mất IP hoặc kẹt `state DORMANT`, watchdog tự động chạy toggle radio phục hồi trong 3–5 giây hoàn toàn im lặng.
* **Lưu ý cự ly vật lý:** Tránh đặt điện thoại áp sát trực tiếp mặt phát AP (< 0.5m) gây bão hòa bộ thu (RSSI vọt lên đỉnh `-30 dBm` gây kickout đột ngột). Tối ưu ở mức `-50 dBm` đến `-65 dBm`.

### E. Bẫy Nhiễm Độc Profile Wi-Fi Đã Lưu (Saved SSID Poisoning) & Máy Tự Nhảy Sang SSID Ngoài Quy Hoạch
* **Bản chất lỗi & Triệu chứng:**
  - Một số máy trong Farm bất ngờ tự động kết nối sang SSID ngoài quy hoạch (ví dụ SSID `Dat`) dù trong mã nguồn script hiện tại hoàn toàn không có lệnh kết nối đến SSID đó.
  - Sau khi `svc wifi disable && svc wifi enable` (radio bounce) hoặc khi AP chính (`admin 1` / `kibe 1`) bị gián đoạn bắt tay, điện thoại lập tức nhảy sang SSID `Dat`.
* **Nguyên nhân gốc rễ (Root Cause):**
  1. Khi một script cứu hộ (như phiên bản cũ của `farm_wifi_auto_healer`) hoặc thao tác thủ công từng kích hoạt `adbjoinwifi` với SSID ngoài quy hoạch (`Dat`), Android OS **tự động lưu mạng đó vào bộ nhớ cấu hình vĩnh viễn (`WifiConfigStore.xml` / `wpa_supplicant.conf`)** với trạng thái `status: ENABLED` và độ ưu tiên ngang hàng (`PRIO: 100`).
  2. **Bẫy "Chỉ dọn code trên máy tính nhưng bỏ quên điện thoại":** Khi phát hiện sai lầm, việc xóa đoạn code fallback `Dat` trong script Python trên host PC là **hoàn toàn vô nghĩa với phần cứng điện thoại**. Profile mạng `Dat` vẫn nằm nguyên vẹn trong ROM của các thiết bị Android thật.
  3. Khi AP chính bị nghẽn, từ chối kết nối hoặc khi stack radio bị khởi động lại, bộ điều khiển tự động của Android (`WifiAutoJoinController`) quét thấy SSID `Dat` phát sóng mạnh gần đó (-46 dBm) sẽ **tự động kết nối ngay lập tức ở tầng OS**.
* **Quy trình Audit & Thanh Trừng Profile Wi-Fi Rác:**
  1. **Audit kiểm tra mạng đã lưu qua ADB:**
     ```bash
     adb -s <SERIAL> shell "dumpsys wifi | grep -E 'ID: [0-9]+ SSID: '"
     ```
     Nếu thấy bất kỳ SSID nào ngoài 4 SSID quy hoạch (`kibe 1`, `kibe 2`, `admin 1`, `admin 2`), máy đã bị nhiễm profile rác.
  2. **Biện pháp xử lý triệt để:**
     - Phải thực hiện lệnh quên mạng (Forget Network) hoặc chạy quy trình **Khôi phục cài đặt mạng (Reset Network Settings)** trên thiết bị để xóa sạch cache cấu hình Wi-Fi đã lưu.
     - Sau khi xóa sạch, dùng `adbjoinwifi` nạp lại **DUY NHẤT 1 SSID quy hoạch chuẩn** tương ứng với số thứ tự của máy đó. Tuyệt đối không để máy tồn tại nhiều profile Wi-Fi cùng lúc.

### F. Chuẩn Hóa Phân Loại Lỗi Báo Cáo Farm (Error Classification Hierarchy)
Tuyệt đối không gom chung lỗi mạng vào một nhãn mơ hồ `Mất Wi-Fi/Proxy`. Bắt buộc phân tách thành 5 nhánh độc lập:
1. **`Mất kết nối ADB/USB`:** Cáp lỏng, offline, unauthorized, không thấy serial trong `adb devices`.
2. **`Mất kết nối Wi-Fi (AP)`:** Mất link layer vật lý (`wlan0` down, `NO-CARRIER`, `ASSOCIATION_REJECTION`, Wi-Fi disconnected).
3. **`Chưa gán Proxy / Proxy :0`:** Cơ chế Fail-Closed Shield kích hoạt (`settings global http_proxy` thiếu hoặc rớt về `:0`). Máy vẫn có Wi-Fi nhưng bị chặn khẩn cấp để chống lộ IP FPT.
4. **`Nghẽn đường truyền Proxy / 4G`:** Cổng proxy Singbox / MikroTik bị timeout, connection refused lúc preflight test ra internet.
5. **`Lỗi App TikTok/Script`:** Văng app TikTok, kẹt popup hệ thống (`Tùy chọn thiết bị`), lệch tài khoản switcher.

---

## 3. Fast Parallel Farm Wi-Fi & Proxy Verification Script

Run this script to inspect all online devices concurrently (<10s for 80 phones):

```python
import subprocess, re, openpyxl, os
from concurrent.futures import ThreadPoolExecutor

ADB_PATH = r'C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe'
EXCEL_PATH = r'D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx'

# Map serial -> machine index
serial_to_m = {}
if os.path.exists(EXCEL_PATH):
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws = wb['Proxy'] if 'Proxy' in wb.sheetnames else wb.active
    for r in range(2, ws.max_row + 1):
        m = ws.cell(r, 1).value
        s = str(ws.cell(r, 2).value).strip() if ws.cell(r, 2).value else ''
        if m and s:
            try:
                serial_to_m[s] = int(m)
            except:
                pass

res = subprocess.run([ADB_PATH, 'devices'], capture_output=True, text=True)
devices = [l.split('\t')[0].strip() for l in res.stdout.strip().split('\n')[1:] if '\tdevice' in l]

def check_device(s):
    m_num = serial_to_m.get(s, '?')
    try:
        out = subprocess.run([ADB_PATH, '-s', s, 'shell', 'ip addr show wlan0; dumpsys wifi | grep mWifiInfo'], capture_output=True, text=True, timeout=8).stdout
        m_ip = re.search(r'inet\s+([0-9.]+)/', out)
        ip = m_ip.group(1) if m_ip else 'NO_IP'
        
        m_ssid = re.search(r'SSID:\s*([^,]+)', out)
        ssid = m_ssid.group(1).strip() if m_ssid else 'NONE'
        
        m_spd = re.search(r'Link speed:\s*([0-9]+Mbps)', out)
        spd = m_spd.group(1) if m_spd else '?'
        
        m_freq = re.search(r'Frequency:\s*([0-9]+MHz)', out)
        freq = m_freq.group(1) if m_freq else '?'
        
        m_rssi = re.search(r'RSSI:\s*(-?[0-9]+)', out)
        rssi = m_rssi.group(1) if m_rssi else '?'
        
        proxy_ok = False
        if isinstance(m_num, int):
            port = 20000 + m_num
            p_test = subprocess.run([ADB_PATH, '-s', s, 'shell', f'printf \"GET / HTTP/1.0\\r\\n\\r\\n\" | toybox nc -w 2 -W 2 -q 1 192.168.110.2 {port}'], capture_output=True, text=True, timeout=5).stdout
            if 'HTTP' in p_test or p_test.strip():
                proxy_ok = True

        return {
            'serial': s, 'machine': m_num, 'ip': ip, 'ssid': ssid,
            'spd': spd, 'freq': freq, 'rssi': rssi, 'proxy_ok': proxy_ok,
            'status': 'OK' if (ip != 'NO_IP' and proxy_ok) else 'FAIL'
        }
    except Exception as e:
        return {'serial': s, 'machine': m_num, 'error': str(e), 'status': 'TIMEOUT'}

with ThreadPoolExecutor(max_workers=30) as ex:
    results = list(ex.map(check_device, devices))

results.sort(key=lambda x: (isinstance(x['machine'], str), x['machine']))
ok = [r for r in results if r['status'] == 'OK']
fail = [r for r in results if r['status'] != 'OK']

print(f'Total: {len(devices)} | OK: {len(ok)} | FAIL: {len(fail)}')
for f in fail:
    print(f"  FAIL: Machine {f['machine']} ({f['serial']}): IP={f.get('ip')} | SSID={f.get('ssid')} | ProxyOK={f.get('proxy_ok')}")
```

---

## 4. Phòng Ngừa Rogue DHCP & Nghẽn USB Khi Kiểm Tra Diện Rộng

### A. Bẫy Rogue DHCP Pool Trên Aruba Virtual Controller
* Trên Master AP (ví dụ `192.168.110.251`), nếu có cấu hình DHCP nội bộ (như `ip dhcp kibe_dhcp subnet 192.168.10.0/24`), AP sẽ cướp quyền cấp IP của router gateway MikroTik (`192.168.110.2`).
* Triệu chứng: Máy nhận IP `192.168.10.x`, mất gateway, báo lỗi `connect: Network is unreachable` khi gọi proxy.
* Xử lý triệt để: SSH vào Master AP (`admin:n0spam@@`), vào `conf t` chạy lệnh `no ip dhcp kibe_dhcp` rồi `commit apply`.

### B. Giới hạn luồng (Concurrency Cap) khi ADB đo kiểm 70+ máy
* Không bao giờ dùng `max_workers > 10` để chạy lệnh `ip addr show` đồng thời trên toàn bộ máy qua 1 host USB.
* Tràn queue ADB server sẽ gây timeout hàng loạt (`subprocess.TimeoutExpired`), dẫn đến chẩn đoán sai rằng máy "mất mạng / mất wifi". Giữ `max_workers = 6` và timeout `12s` để có kết quả đo chính xác 100%.

### C. Chuẩn Mực Triển Khai Script Cứu Hộ Wi-Fi (`farm_wifi_auto_healer.py`)
Khi thiết kế watchdog / healer tự động khắc phục Wi-Fi cho farm:
1. **Kiểm tra đúng subnet mục tiêu:** Không kiểm tra lỏng lẻo `192.168.`, mà phải bắt đúng subnet chuẩn của Farm (`192.168.110.`). Nếu máy nhận dải `192.168.10.` do rogue DHCP thì vẫn tính là lỗi và kích hoạt recovery.
2. **Không nuốt ngoại lệ (Anti-Swallowing):** Tuyệt đối không dùng `except Exception: pass`. Phải log đầy đủ `logger.warning` / `logger.error` khi ADB command fail, load mapping fail hoặc force join timeout.
3. **Telemetry & Observability:** Bắt buộc ghi nhận thời gian chạy (`elapsed`), tổng số máy quét (`scanned_devices`), số máy heal thành công (`healed_count`), và nguyên nhân thất bại của từng thiết bị.
4. **Tránh kẹt UI:** Sau khi launch `adb-join-wifi.apk`, gửi lệnh `input keyevent KEYCODE_HOME` (hoặc phím số 3) để đưa màn hình về Home, không để treo giao diện app trên màn hình điện thoại.

