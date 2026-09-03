# Fail-Closed Live Proxy IP & Mapping Verification for TikTok Reg

## Bối cảnh & Root Cause (Incident 24/08/2026 máy 75)

Khi upstream proxy chết hoặc timeout (vd: port proxy sập, SIM 4G mất mạng), Android VpnService của ViChanger vẫn giữ interface `tun0` ở trạng thái `UP` và dumpsys connectivity vẫn báo `CONNECTED`. 
Khi đó:
1. TikTok app sẽ tự động bypass tunnel và fallback ra Direct Wi-Fi IP của farm, gây lộ footprint hàng loạt tài khoản trên cùng 1 IP gốc.
2. Script reg cũ tự đọc mapping cứng qua `iter_rows` (`r[1]`, `r[2]`) thay vì `serial_is_mapped_in_workbook`, dẫn đến nguy cơ lệch cột làm `vpn_required=False`.
3. Script cũ đọc biến môi trường `TIKTOK_REG_VERIFY_LIVE_IP` cho phép bypass live IP check.
4. Gate chỉ kiểm tra `status_res in ("OK", "PASSED", "CONNECTED", "BYPASSED_UNMAPPED")` mà không kiểm tra chặt `proxy_ip` khác rỗng.

## Quy tắc Gate Preflight bắt buộc trong `social_reg_v1.py`

### 1. Phân giải Mapping bằng Header
Mapping proxy bắt buộc dùng hàm chuẩn của `automation_core`:
```python
vpn_required = serial_is_mapped_in_workbook(
    mapping_path,
    device_id,
    serial_headers=("phoneId", "deviceId", "serial"),
)
```
Không tự parse hàng/cột cứng bằng `iter_rows`.

### 2. Ép cứng `verify_live_ip=True`
Tuyệt đối không cho phép env variable tắt live IP check trong luồng đăng ký:
```python
vpn_status = require_android_vpn(
    AdbClient(adb_path=ADB_PATH, serial=device_id, default_timeout=20),
    required=vpn_required,
    verify_live_ip=True,
)
```

### 3. Fail-Closed 3 điều kiện
Với máy có gán proxy (`vpn_required=True`), bắt buộc:
1. `vpn_status.allowed == True`
2. `vpn_status.connected == True`
3. `proxy_ip` trích xuất được từ broadcast `vn.vichanger.app.GET_IP` phải khác rỗng.

Nếu thiếu bất kỳ điều kiện nào (ví dụ broadcast trả `result=0` do proxy chết) $\rightarrow$ raise `ConsumerPreflightError` để script log `BLOCK VPN_PREFLIGHT_BLOCKED` và dừng ngay trước `[init]`, tuyệt đối không mở TikTok.

## Chẩn đoán nhanh khi máy báo `VPN_PREFLIGHT_BLOCKED`

1. Kiểm tra liveness của proxy upstream bên ngoài host:
   `curl -x http://user:pass@host:port https://api.ipify.org`
2. Kiểm tra broadcast trực tiếp trên thiết bị:
   `adb -s <serial> shell am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller`
   - `result=200, data="<IP>"`: Proxy sống, IP hợp lệ.
   - `result=0`: Upstream proxy sập / chết port $\rightarrow$ Báo user kiểm tra box/SIM hoặc gán lại proxy, không sửa code hạ gate.
