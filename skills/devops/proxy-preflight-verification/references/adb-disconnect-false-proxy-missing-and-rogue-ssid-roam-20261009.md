# ADB Disconnect False-Positive Proxy Missing & Rogue SSID Roaming Triage (2026-10-09)

## 1. Cạm bẫy: Mất ADB/USB bị báo nhầm thành "Proxy is missing or :0"

### Hiện tượng
Hàng loạt máy farm (ví dụ M10, M63, M64, M67, M74, M76) dừng ngay từ preflight với thông báo lỗi:
`required Android VPN/proxy is not set on device: settings global http_proxy is missing or :0 for <serial>`

### Phân tích hiện trường O(1)
Khi điều tra thực tế qua ADB host (`adb devices`):
- Các thiết bị này thực chất đang bị **rớt kết nối USB / rớt khỏi `adb devices`** (`device '<serial>' not found` hoặc `ce06... offline`).
- Khi preflight chạy lệnh:
  `p_out = adb.shell(["settings", "get", "global", "http_proxy"], timeout=3.0, check=False)`
  Vì thiết bị đã rớt kết nối, lệnh ADB thất bại và trả về `stdout = ""`, `stderr = "adb.exe: device '<serial>' not found"`, `returncode = 1`.
- Nếu logic preflight chỉ kiểm tra:
  ```python
  p_val = str(getattr(p_out, "stdout", "") or "").strip()
  if not p_val or p_val.lower() in ("null", ":0", "none"):
      raise ConsumerPreflightError(f"settings global http_proxy is missing or :0 for {serial}")
  ```
  Hệ thống sẽ ngộ nhận chuỗi rỗng do lỗi transport thành "máy chưa cài proxy", che giấu hoàn toàn lỗi phần cứng lỏng cáp/hub USB.

### Quy tắc chuẩn hóa
Trước khi kiểm tra giá trị của `p_out.stdout`:
1. BẮT BUỘC kiểm tra `p_out.ok` / `p_out.returncode == 0` và hàm `is_connection_lost(p_out.stderr)`.
2. Nếu `stderr` chứa `device not found`, `device offline`, `error: closed`, `timeout`:
   Lập tức fail-fast với mã lỗi:
   `device is offline or ADB/USB disconnected for {serial}: {stderr}`
   TUYỆT ĐỐI KHÔNG để lỗi transport lọt xuống nhánh kiểm tra cấu hình proxy.

---

## 2. Chu kỳ Roam SSID Rác & Trôi Wi-Fi 10–15 Giây

### Hiện tượng
Các máy đang chạy bình thường đột ngột báo `dumpsys connectivity: Wi-Fi not connected` đồng loạt trong 1–2 phút (ví dụ lúc 08:11 sáng trên M5, M7, M28, M52, M55, M69), nhưng ngay sau phiên kiểm tra lại thì Wi-Fi và Proxy đều đang LIVE 100%.

### Bằng chứng trích xuất từ `dumpsys wifi`
```text
time=10-09 08:11:37: SSID: kibe 1 ... state: DISCONNECTED
time=10-09 08:11:42: SSID: VIETTEL_9rXX3G ... state: ASSOCIATING
time=10-09 08:11:46: SSID: VIETTEL_9rXX3G ... AUTHENTICATION_FAILURE_EVENT: reason=3:ERROR_AUTH_FAILURE_WRONG_PSWD -> DISCONNECTED
time=10-09 08:11:50: SSID: kibe 1 ... state: ASSOCIATING -> FOUR_WAY_HANDSHAKE -> COMPLETED
```

### Bản chất kỹ thuật
1. Khi sóng AP chính (`kibe 1`) bị chớp sóng (jitter/transient flutter), Android tự động quét các mạng Wi-Fi đã từng lưu trong máy (`Configured networks`).
2. Nếu máy còn lưu SSID rác/lạ (như `VIETTEL_9rXX3G`), Android sẽ cố gắng nhảy sang kết nối.
3. Khi bị lỗi mật khẩu (`ERROR_AUTH_FAILURE_WRONG_PSWD`), Supplicant mất từ 10–15 giây ngắt kết nối (`DISCONNECTED`) rồi mới thử quay lại AP chính `kibe 1`.
4. Nếu batch feed session chạy đúng vào khoảng trống 10–15 giây này, preflight bắt trúng trạng thái `Wi-Fi not connected` và kích hoạt Kill-Switch an toàn fail-closed.

### Giải pháp xử lý
1. Quét và quên toàn bộ SSID rác trên máy farm: chỉ giữ duy nhất SSID chuẩn của farm (`kibe 1` hoặc `admin 2`).
2. Khi gặp alert hàng loạt `Wi-Fi not connected` nhưng kiểm tra lại thấy sống ngay: đọc `dumpsys wifi` trích xuất `AUTHENTICATION_FAILURE_EVENT` để xác định ngay SSID rác đang gây nhiễu roam.
