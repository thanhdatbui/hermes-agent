# Concurrent ADB Proxy Healing & Farm AP Balancing (2026-10-09)

## 1. Bối cảnh & Hiện tượng (Sự cố "Mạng cả đống sao báo lỗi Wi-Fi")
- **Hiện tượng:** Watchdog/Cronjob cảnh báo hàng loạt máy (10-20 máy) dính lỗi `Mất Wi-Fi/Proxy`. Người dùng thắc mắc vì hạ tầng mạng, AP và Internet vẫn hoạt động bình thường cho phần lớn farm.
- **Nguyên nhân cốt lõi & Bóc tách nhãn lỗi:**
  1. Watchdog cũ gom tất cả lỗi chứa `wifi`, `proxy`, `wlan0`, `network` vào chung một nhãn `Mất Wi-Fi/Proxy`. Phải bóc tách thành 5 nhóm độc lập:
     - `Mất kết nối ADB/USB` (offline, unauthorized).
     - `Mất kết nối Wi-Fi (AP)` (mất link layer wlan0, AP từ chối association).
     - `Chưa gán Proxy / Proxy :0` (kích hoạt Fail-Closed Shield).
     - `Nghẽn đường truyền Proxy / 4G` (proxy port timeout / connection refused).
     - `Lỗi App TikTok/Script` (app crash, UI mismatch).
  2. Phần lớn máy thực chất **không hề mất Wi-Fi**, mà bị mất biến toàn cục Android `settings global http_proxy` (bị reset về null hoặc `:0` do máy vừa reboot hoặc lỏng cáp), kích hoạt Fail-Closed Shield của preflight.
  3. Một số ít máy bị lỗi bắt tay Wi-Fi cục bộ (`ASSOCIATION_REJECTION`) do AP Aruba 5GHz quá tải slot client hoặc kẹt session BSSID.

---

## 2. Kỹ thuật Gán Proxy Đa Luồng Toàn Farm (Concurrent ADB Healing O(1))
### ⚠️ Cạm bẫy của lệnh tuần tự (`set_proxy_farm_adb.py` mặc định):
- Lệnh gán proxy mặc định chạy vòng lặp tuần tự (sequential) qua 80 máy.
- Khi có 5–10 máy bị rớt cáp USB (`offline` hoặc `device not found`), mỗi lệnh `adb shell` sẽ chờ timeout 5–10s $\rightarrow$ toàn bộ script bị nghẽn và timeout (>45s - 60s), không thể hoàn thành việc gán proxy cho các máy đang online.

### ✅ Giải pháp chuẩn: `ThreadPoolExecutor` với Bounded Timeout:
Sử dụng script Python đa luồng với worker pool (20-30 workers) và giới hạn timeout cứng `1.5s - 2.0s` cho mỗi thiết bị:

```python
import subprocess
from concurrent.futures import ThreadPoolExecutor
import openpyxl

def bulk_set_proxy_kibe():
    wb = openpyxl.load_workbook(r'D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx', data_only=True)
    ws = wb.active
    targets = []
    for r in ws.iter_rows(min_row=2, max_row=81, values_only=True):
        if not r or not r[0] or not r[1]: continue
        m, serial = r[0], str(r[1]).strip()
        if serial != 'None' and serial:
            targets.append((m, serial, f'192.168.110.2:{20000 + m}'))

    def set_one(item):
        m, serial, proxy = item
        try:
            cmd = ['adb', '-s', serial, 'shell', 'settings', 'put', 'global', 'http_proxy', proxy]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=1.5)
            return m, res.returncode == 0
        except Exception:
            return m, False

    with ThreadPoolExecutor(max_workers=20) as ex:
        results = list(ex.map(set_one, targets))

    success = [m for m, ok in results if ok]
    fail = [m for m, ok in results if not ok]
    print(f"Kibe: Success {len(success)}/80 | Fail/Offline {len(fail)}/80")
    return success, fail
```

> **Hiệu năng:** Phủ lại proxy cho toàn bộ 72-75 máy online trong vòng **dưới 8 giây**, không bị chặn bởi các máy offline.

---

## 3. Quy Tắc Invariant Wi-Fi Farm & CẤM TUYỆT ĐỐI Fallback SSID Ngoài Luồng (User Invariant)
### 🚨 CẢNH BÁO NGUY HIỂM — CẤM NHẢY SANG SSID LẠ / SSID "Dat":
- **Triệu chứng & Cạm bẫy:** Khi máy gặp lỗi bắt tay Wi-Fi (`ASSOCIATION_REJECTION`), tuyệt đối **KHÔNG ĐƯỢC TỰ Ý CHO MÁY BẮT SANG SSID VÃNG LAI NHƯ "Dat" HAY MẠNG CÁ NHÂN**.
- **Hậu quả khôn lường:**
  1. **Lệch Subnet & Sập Proxy:** Mạng ngoài (như `Dat`) cấp dải IP khác (ví dụ `192.168.10.x` thay vì `192.168.110.x`). Khi lệch subnet, kết nối từ máy đến container Singbox `192.168.110.2:2000N` bị timeout, app TikTok không thể tải mạng.
  2. **Rủi ro Direct IP Leak:** Nếu máy bị rớt proxy toàn cục hoặc ứng dụng có luồng bypass, toàn bộ lưu lượng sẽ đi thẳng ra IP Internet FPT của mạng cá nhân, làm cháy cụm nick.
- **Quy hoạch SSID & Mật khẩu Bất Khả Xâm Phạm:**
  * **Máy 01 – 40:** Cố định **`kibe 1`** — Mật khẩu: **`23102025`**.
  * **Máy 41 – 80:** Cố định **`kibe 2`** — Mật khẩu: **`19051995`**.
  * **Máy 201 – 240:** Cố định **`admin 1`** — Mật khẩu: **`19051995`**.
  * **Máy 241 – 280:** Cố định **`admin 2`** — Mật khẩu: **`19051995`**.

---

## 4. Xử Lý Bẫy `ASSOCIATION_REJECTION` & BSSID Blocklist Trên Android 8
### Bản chất kỹ thuật:
- Khi AP Aruba gửi gói từ chối kết nối (do kẹt session cũ hoặc vượt ngưỡng client), Android 8 tự động đánh dấu:
  `networkStatus=NETWORK_SELECTION_TEMPORARY_DISABLED disableReason=NETWORK_SELECTION_DISABLED_ASSOCIATION_REJECTION`
- Lệnh `svc wifi disable` / `enable` thông thường **KHÔNG XÓA ĐƯỢC CỜ NÀY**. Máy sẽ chủ động bỏ qua SSID đó dù sóng mạnh full vạch.

### Cách xử lý chuẩn:
1. **Dùng công cụ `adb-join-wifi.apk` với đúng SSID và Password của máy:**
   ```bash
   adb -s <serial> install -r -g "D:\Taadaa\AI-Tools\tools\adb-join-wifi.apk"
   adb -s <serial> shell "am force-stop com.steinwurf.adbjoinwifi && am start -n com.steinwurf.adbjoinwifi/.MainActivity -e ssid '<SSID_CHÍNH>' -e password_type 'WPA' -e password '<PASS_CHUẨN>'"
   ```
   *Lệnh này gọi trực tiếp API `WifiManager.enableNetwork(netId, true)` từ tầng Java của Android để xóa sạch cờ disableReason và ép bắt tay lại.*
2. **Cân tải sang SSID Farm nội bộ (Internal Farm Re-balancing):**
   Nếu AP chính (`kibe 1`) kẹt cứng chưa nhả session, chỉ được phép failover sang AP farm song hành:
   - Máy cụm 1 (M1-M40) kẹt `kibe 1` $\rightarrow$ tạm thời bắt sang **`kibe 2`** (Pass: `19051995`).
   - Cả 2 SSID này đều thuộc cụm farm, cùng VLAN 1, cùng trỏ gateway `192.168.110.2` thông mượt với container Singbox.
   - **Tuyệt đối cấm** nhảy ra ngoài danh sách 4 SSID farm (`kibe 1`, `kibe 2`, `admin 1`, `admin 2`).
