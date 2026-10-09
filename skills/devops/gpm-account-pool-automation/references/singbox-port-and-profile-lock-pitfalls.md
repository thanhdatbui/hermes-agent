# Singbox Port Mapping & Chromium Profile Lock Pitfalls

## 1. Singbox Port Mapping trong Pipeline OAuth (`run_oauth_s7_pipeline.py`)

Khi script nhận cấu hình account hoặc port từ runner/inventory, port có thể đến từ nhiều nguồn khác nhau:
- Port dải `5100..5199` (proxy local gốc, ví dụ `5105` tương ứng máy 5 -> port Singbox là `20005`).
- Port dải `10000..10999` (proxy forward cũ).
- Port cố định `16002` (cần mapping sang `20000 + mid`).
- Port đã là Singbox port sẵn trong dải `20000..20999` (ví dụ `20005` cho máy 5).

### Pitfall
Nếu dùng biểu thức rút gọn:
```python
singbox_port = acc.get("singbox_port") or (20000 + mid if port == 16002 else (20000 + (port - 5100) if 5000 < port < 6000 else 20000 + (port - 10000)))
```
Khi `port = 20005`, điều kiện `5000 < port < 6000` là `False`, script rơi vào nhánh `20000 + (port - 10000) = 20000 + 10005 = 30005` -> sai port proxy Singbox khiến Playwright bị treo timeout kết nối proxy.

### Giải pháp chuẩn
```python
if acc.get("singbox_port"):
    singbox_port = acc["singbox_port"]
elif port and 20000 <= port < 21000:
    singbox_port = port
elif port == 16002:
    singbox_port = 20000 + mid
elif port and 5000 < port < 6000:
    singbox_port = 20000 + (port - 5100)
elif port and 10000 <= port < 11000:
    singbox_port = 20000 + (port - 10000)
else:
    singbox_port = 20000 + mid
```

---

## 2. Chromium User Data Dir Lock (`Opening in existing browser session`)

### Triệu chứng
Playwright gọi `launch_persistent_context` ném ngoại lệ:
```
BrowserType.launch_persistent_context: Opening in existing browser session. This usually means that the profile is already in use by another instance of Chromium.
```

### Nguyên nhân
Một tiến trình Chrome trước đó dùng profile GPM (`C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\<profile_id>`) chưa thoát hẳn hoặc bị treo ngầm.

### Cách xử lý nhanh
Dùng PowerShell định danh đúng tiến trình Chrome đang khóa profile để kill triệt để trước khi mở lại:
```powershell
Get-CimInstance Win32_Process -Filter "name = 'chrome.exe'" | Where-Object { $_.CommandLine -like '*<profile_id>*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```
