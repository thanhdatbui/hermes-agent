# ADB Device Global Proxy Preflight Probe Pattern

## 1. Bối cảnh & Vấn đề
Trong hệ thống tự động hoá Android farm (như `tiktok-luot nuoi acc` / `python_runner/core/vpn_preflight.py`):
- Trước đây `_proxy_server_live` chỉ đọc proxy mapping từ workbook Excel cố định (`get_default_proxy_mapping()`).
- **Bất cập**:
  - Khi thiết bị được gán proxy động qua router proxy hoặc ViChanger, file Excel mapping có thể chưa cập nhật kịp thời hoặc thiết bị đang trỏ sang port/proxy khác thực tế.
  - Kiểm tra host-side probe theo Excel có thể báo sai trạng thái hoặc probe sai port so với cấu hình thực tế trên thiết bị.

## 2. Giải pháp: Ưu tiên đọc `settings get global http_proxy` qua ADB

### Thứ tự ưu tiên (Precedence Order)
1. **Device-side probe qua ADB**:
   - Chạy lệnh ADB: `settings get global http_proxy` với timeout ngắn (`min(timeout, 3.0)`).
   - Kiểm tra giá trị trả về (`stdout`). Bỏ qua nếu rỗng hoặc rơi vào các giá trị mặc định của Android khi chưa gán proxy: `"null"`, `":0"`, `"none"`.
2. **Fallback Workbook**:
   - Nếu `adb is None` hoặc thiết bị trả về rỗng / `null`, fallback đọc từ workbook mapping `get_default_proxy_mapping()`.
3. **Fail-fast Socket Probe**:
   - Chuẩn hoá chuỗi proxy (strip `http://`, `https://`, trailing paths `/...`).
   - Tách `host:port` và gọi `socket.connect_ex((p_host, p_port))` với timeout ngắn (1.5s).
   - Nếu port bị closed/refused (`connect_ex != 0`), fail-fast ngay lập tức (`ConsumerPreflightError`) để unblock các workers khác, không phải chờ timeout dài trên device.

### Mẫu code triển khai chuẩn
```python
def _proxy_server_live(serial: str, timeout: float = 1.5, adb: AdbClient | None = None) -> bool | None:
    """Fast probe: check if the active proxy host/port is reachable from host."""
    try:
        import socket

        proxy_str = None
        if adb is not None:
            try:
                res = adb.shell(["settings", "get", "global", "http_proxy"], timeout=min(timeout, 3.0), check=False)
                val = str(getattr(res, "stdout", "") or "").strip()
                if val and val not in ("null", ":0", "none"):
                    proxy_str = val
            except Exception:
                pass

        if not proxy_str:
            from openpyxl import load_workbook

            mapping = get_default_proxy_mapping()
            if not mapping or not mapping.exists():
                return None
            wb = load_workbook(mapping, data_only=True)
            sheet = wb.active
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if len(row) >= 3 and str(row[1] or '').strip() == str(serial).strip():
                    if row[2] and str(row[2]).strip():
                        proxy_str = str(row[2]).strip()
                        break

        if not proxy_str:
            return None

        if "://" in proxy_str:
            proxy_str = proxy_str.split("://", 1)[1]

        parts = proxy_str.split(':')
        if len(parts) >= 2:
            p_host = parts[0].strip()
            port_str = parts[1].strip().split('/')[0]
            p_port = int(port_str)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            res = s.connect_ex((p_host, p_port))
            s.close()
            return res == 0
    except Exception:
        pass
    return None
```

### Điểm gọi trong Preflight (`require_proxy_connected`)
Bắt buộc truyền instance `adb` đã khởi tạo vào `_proxy_server_live`:
```python
server_alive = _proxy_server_live(serial, timeout=1.5, adb=adb)
if server_alive is False:
    raise ConsumerPreflightError(
        f"required Android VPN/proxy is unreachable: proxy server port is closed/refused for {serial}; "
        f"skipping recovery wait to unblock other machines immediately"
    )
```
