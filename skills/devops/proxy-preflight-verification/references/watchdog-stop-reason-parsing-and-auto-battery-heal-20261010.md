# Watchdog Stop Reason Parsing & Auto Battery Healing (2026-10-10)

## 1. Bẫy Watchdog Phân Loại Sai: Nuốt mất `stop_reason` vì `final_status: blocked-proxy-vpn`

### Hiện tượng
Watchdog báo cáo feed session hiển thị một danh sách dài hàng chục máy bị dán nhãn:
`Lỗi cấu hình Proxy (N máy): M10, M35, M47, M210, M212, M217, M263, M265...`
khiến người vận hành hoang mang tưởng hạ tầng MikroTik hoặc cấu hình proxy bị sập hàng loạt. Trong khi thực tế hạ tầng proxy và Singbox hoàn toàn sống 100%.

### Bản chất kỹ thuật
1. Trong file `summary.txt` của mỗi máy bị chặn tại tiền kiểm preflight, runner luôn ghi:
   ```text
   status: fail
   final_status: blocked-proxy-vpn
   reason: [device-lock] machine N blocked by proxy VPN preflight
   stop_reason: device is offline or ADB/USB disconnected for ...
   ```
2. Trong hàm `parse_run_all` của `feed_session_watchdog.py`, đoạn code cũ đọc từng dòng:
   ```python
   for line in c.splitlines():
       if line.startswith("reason:") or line.startswith("final_status:"):
           val = line.split(":", 1)[1].strip()
           if val != "success":
               reason = val
               break
   ```
   Do `final_status: blocked-proxy-vpn` xuất hiện trước, biến `reason` lập tức bị gán thành `"blocked-proxy-vpn"` và ngắt vòng lặp (`break`), bỏ qua hoàn toàn dòng `stop_reason:` bên dưới.
3. Hàm `classify_feed_failure(reason)` thấy chuỗi `"proxy"` / `"vpn"` liền xếp vào nhóm `"Lỗi cấu hình Proxy"`.
4. Hậu quả: Các lỗi mất kết nối cáp USB (`device offline` / `device not found`) và rớt Wi-Fi AP (`dumpsys connectivity: Wi-Fi not connected`) đều bị ngộ nhận thành lỗi proxy.

### Giải pháp chuẩn hóa
Trích xuất `r_map = {k: v}` từ `summary.txt` và ưu tiên lấy `stop_reason` trước:
```python
r_map = {l.split(":", 1)[0].strip(): l.split(":", 1)[1].strip() for l in c.splitlines() if ":" in l}
stop_r = r_map.get("stop_reason", "")
reason = stop_r if (stop_r and stop_r != "None") else (r_map.get("reason") or r_map.get("final_status", ""))
```
Khi `reason` mang đúng nội dung `stop_reason`, bộ phân loại sẽ trả về chính xác:
- Mất kết nối ADB/USB
- Mất kết nối Wi-Fi (AP)
- Nghẽn đường truyền Proxy / 4G
- Chưa gán Proxy / Proxy :0

---

## 2. Cơ chế Bù Pin Tự Động Preflight (`ensure_safe_battery_level`) Cho Box Phone

### Bản chất trên Box Phone Farm
- Thiết bị Samsung S7 trong box phone farm được cấp nguồn trực tiếp qua mạch mod hoặc cáp USB từ bộ nguồn tập trung.
- Đôi khi hệ thống hiển thị mức pin bị tụt về mức kiệt (như M47 tụt về 2%).
- Khi mức pin `< 15%`, Samsung Android 8 tự động kích hoạt **Chế độ Tiết kiệm pin (Power Saving Mode)**:
  + Ngắt Wi-Fi nền khi màn hình tắt (`mWakefulness=Dozing`).
  + Hạ xung nhịp CPU, delay packet Cronet/TTNet.
  + Hiện pop-up cảnh báo pin yếu (`com.android.settings`), che khuất UI TikTok.

### Tại sao CẤM random mức pin nhảy cóc qua từng ca
- Telemetry AppLog SDK của TikTok ghi nhận `battery_level` cùng `uptimeMillis`.
- Nếu random pin qua mỗi ca (ví dụ 40% -> 85% -> 30%), TikTok phát hiện bất thường logic (nhảy pin phi vật lý khi máy đang cắm nguồn liên tục), rủi ro dính botnet flag.
- Đồng thời nếu random rơi vào mức `< 15%` sẽ gây ra chính lỗi tiết kiệm pin kể trên.

### Chuẩn hóa hàm tự kiểm tra & bù pin an toàn
Tích hợp vào đầu hàm `require_proxy_connected` trong `python_runner/core/vpn_preflight.py`:
```python
def ensure_safe_battery_level(adb: Any, serial: str, min_level: int = 20, target_level: int = 85) -> int | None:
    """Kiểm tra pin thiết bị, nếu thấp (< min_level) thì tự gán pin an toàn tránh popup pin yếu và sụt nguồn."""
    try:
        b_res = adb.shell(["dumpsys", "battery"], timeout=3.0, check=False)
        out = str(getattr(b_res, "stdout", "") or "")
        m = re.search(r"level:\s*(\d+)", out)
        if m:
            cur_lvl = int(m.group(1))
            if cur_lvl < min_level:
                adb.shell(["dumpsys", "battery", "set", "level", str(target_level)], timeout=3.0, check=False)
                adb.shell(["dumpsys", "battery", "set", "status", "2"], timeout=3.0, check=False)
                return target_level
            return cur_lvl
    except Exception:
        pass
    return None
```
- Ngưỡng kích hoạt: Chỉ can thiệp khi `level < 20%`. Mức bình thường (>=20%) giữ nguyên tự nhiên.
- Mức bù: `85% (Charging)` — mức tối ưu cho thiết bị cắm sạc liên tục.

---

## 3. Đồng bộ Code Sang Admin PC Qua SSH Base64 Stdin Pipe

### Cạm bẫy SCP & Git trên Windows Admin Host
- Lệnh `scp` từ Kibe sang Admin PC (`192.168.110.119`) đối với đường dẫn có dấu cách (`tiktok-luot nuoi acc`) thường bị lỗi `No such file or directory` do lớp shell Windows (PowerShell/CMD) giải mã nháy kép khác POSIX.
- `git pull` trên Admin PC có thể kẹt do thiếu Git credential helper / interactive prompt.

### Pattern đồng bộ 100% tin cậy
Đọc file local, encode Base64, pipe qua SSH stdin vào một dòng Python trên host remote:
```python
import base64, subprocess

rel_path = 'python_runner/core/vpn_preflight.py'
local_p = f'D:/Taadaa/tiktok-luot nuoi acc/{rel_path}'
with open(local_p, 'rb') as f:
    b64 = base64.b64encode(f.read())
remote_p = f'D:/Taadaa/tiktok-luot nuoi acc/{rel_path}'
cmd = ['ssh', 'admin-farm', 'python', '-c', f"\"import sys, base64; open(r'{remote_p}', 'wb').write(base64.b64decode(sys.stdin.read()))\""]
subprocess.run(cmd, input=b64, check=True)
```
Không phụ thuộc vào SCP syntax, an toàn tuyệt đối với mọi khoảng trắng và ký tự đặc biệt trong đường dẫn.
