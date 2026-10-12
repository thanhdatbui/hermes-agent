# Watchdog Report Sanitization & Error Reason Cleaning

## 1. Nguyên Tắc Cốt Lõi: Chống Leak Stacktrace & HTTP Dump Vào Telegram
- **Vấn đề thực tế (Sự cố 2026-10-12):**
  - Khi preflight test kết nối mạng/proxy (`goreq.go`, `curl.go` gọi `http://ifconfig.me/ip`), nếu proxy timeout hoặc fail-closed, raw error message trả về chứa toàn bộ HTTP headers (`Host: ifconfig.me`, `GET /ip HTTP/1.1`) và stacktrace nhiều dòng.
  - Tương tự, khi ADB timeout trên máy bị rớt USB, chuỗi lỗi chứa đường dẫn file Windows tuyệt đối (`'C:\Program Files (x86)\xiaowei\tools\adb.exe'`).
  - Nếu đưa trực tiếp `reason` thô vào tin nhắn Telegram report, báo cáo bị rác, vỡ layout và gây hoang mang cho người vận hành.

## 2. Quy Chuẩn Hàm `classify_error_reason(reason: Any) -> str`
Bất kỳ script watchdog nào tổng hợp báo cáo (Feed, Follow, Upload, Reg...) BẮT BUỘC phải chuẩn hóa chuỗi lỗi qua bộ lọc:

```python
def classify_error_reason(reason: Any) -> str:
    """Làm sạch và phân loại chuỗi lỗi kỹ thuật thô thành nhãn 1 dòng ngắn gọn cho báo cáo."""
    r = str(reason or "").strip()
    if not r:
        return "Lỗi không xác định"
    r_lower = r.lower()
    
    # 1. Nhóm lỗi ADB / USB
    if any(k in r_lower for k in ("device not found", "device offline", "not found in adb", "transport", "adb/usb", "adb.exe", "adb command timed out")):
        return "Mất kết nối ADB/USB"
        
    # 2. Nhóm lỗi Wi-Fi / AP
    if any(k in r_lower for k in ("wi-fi", "wifi", "wlan0 down", "no-carrier", "association_rejection")):
        return "Mất kết nối Wi-Fi (AP)"
        
    # 3. Nhóm lỗi Nghẽn mạng / Egress Proxy / Timeout kiểm tra IP
    if any(k in r_lower for k in ("ifconfig", "egress ip", "context deadline", "awaiting headers", "deadline exceeded", "proxy timeout", "proxy is unreachable")):
        return "Nghẽn đường truyền Proxy / 4G"
        
    # 4. Nhóm lỗi Cấu hình Proxy / VPN nói chung
    if any(k in r_lower for k in ("vpn", "proxy")):
        return "Lỗi kết nối VPN/Proxy"
        
    # 5. Nhóm UI / Lock
    if "unexpected popup" in r_lower or "dialog" in r_lower:
        return "Popup/Dialog bất thường"
    if "device-lock" in r_lower or "lock" in r_lower:
        return "Kẹt Device Lock"
        
    # 6. Fallback làm sạch chuỗi: Cắt dòng đầu, bỏ Windows path, giới hạn <= 60 chars
    first = r.splitlines()[0].strip()
    if ":" in first:
        first = first.split(":")[-1].strip() or first.split(":")[0].strip()
    first = re.sub(r"[A-Za-z]:\\[^\s]+", "", first)
    first = re.sub(r"\s+", " ", first).strip()
    return first[:60] if first else "Lỗi script/xác minh"
```

## 3. Checklist Kiểm Chứng Khi Thêm Báo Cáo Mới
- [ ] KHÔNG đưa raw string của exception / subprocess stderr trực tiếp vào message template.
- [ ] Test case kiểm tra sanitize: Truyền chuỗi chứa `\n\nHost: ifconfig.me` và chuỗi chứa `C:\...\adb.exe`, khẳng định kết quả trả về không chứa ký tự xuống dòng (`\n`), không chứa HTTP headers và không chứa đường dẫn file nhị phân.
