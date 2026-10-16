# Farm Alert Triage: Workbook Header Drift, Admin LAN Proxy Loopback, Milestone Popups & Watcher Recovery (2026-10-17)

## 1. Workbook Header Drift (Parenthesized Column Variants)

### Triệu chứng & Log:
```
Workflow target error: Missing required fields: Folder Video
Đọc workbook lần 1/5 thất bại: Missing required fields: Folder Video. Thử lại sau 0.5s...
```

### Nguyên nhân:
Workbook quản lý farm (`Tik1.xlsx` .. `Tik8.xlsx`) thường xuất hiện các biến thể tiêu đề do cập nhật mô tả quy trình:
- `Folder Video (Render Dich)` hoặc `Folder Video Render Dich` thay vì thuần `Folder Video`.
- `Video Goc (Nguon Cao)` hoặc `Video Goc Nguon Cao` thay vì thuần `video gốc`.

Nếu `CANONICAL_HEADERS` trong `account_source.py` chỉ đối soát exact token cơ bản, hàm đọc hàng của workbook sẽ báo thiếu trường bắt buộc dù cột dữ liệu thực tế vẫn tồn tại.

### Khắc phục & Tiêu chuẩn:
Bổ sung các biến thể ngoặc đơn vào bảng tra `CANONICAL_HEADERS` trong `account_source.py`:
```python
"Folder Video": {
    "folder video",
    "video folder",
    "folder video (render dich)",
    "folder video render dich",
    "sttvideo",
},
"video gốc": {
    "video goc",
    "video source",
    "source video",
    "video goc (nguon cao)",
    "video goc nguon cao",
},
```
- Chuẩn hóa CRLF về LF trước khi commit để giữ diff sạch.
- Chạy `pytest tests/test_account_source_concurrency.py` verify không hồi quy.
- Sync sang host phụ (Admin-farm) để giữ nhất quán.

---

## 2. Admin Downloader 502 Bad Gateway (Loopback NAT vs LAN IP)

### Triệu chứng:
Log `download_admin_p10.log` trên host Admin văng lỗi:
```
ProxyError: ('Unable to connect to proxy', OSError('Tunnel connection failed: 502 Bad Gateway'))
```

### Căn nguyên:
- File proxy trên máy Admin (`proxy_pool_69.txt`) cấu hình domain WAN `mirotik1.taadaa.click:10001..10035`.
- Khi máy Admin (`192.168.110.119`) nằm trong mạng LAN gọi vòng (loopback) ra domain ngoài thì bị router chặn hoặc báo 502.
- Kết nối thẳng vào IP LAN MikroTik `192.168.110.2:10001..10035` hoàn toàn thông suốt (`TcpTestSucceeded : True`).
- **Lưu ý bộ nhớ:** Tiến trình cào `download_by_niche.py` đọc toàn bộ danh sách proxy vào RAM khi khởi động. Sau khi sửa file trên đĩa, bắt buộc phải kill tiến trình Python cũ để service tự khởi động lại tiến trình mới nạp cấu hình mới.

---

## 3. TikTok Milestone Popup: 'Tổng lượt thích' che Profile Switcher

### Triệu chứng & Hiện trường:
- Khi runner mở profile để chuyển tài khoản (switcher), xuất hiện popup chúc mừng:
  - Tiêu đề: *"Tổng lượt thích"*
  - Nội dung: *"twohavqyd8g đã nhận tổng cộng 359 lượt thích cho tất cả video"*
  - Nút bấm: `[OK]` nằm ở vùng giữa dưới màn hình (`x=540, y=1400` trên độ phân giải 1080x1920).
- Popup này che toàn bộ màn hình hồ sơ khiến script không bấm được vào thanh Switcher, văng lỗi `SWITCHER_NOT_CONFIRMED` rồi chuyển sang soft reboot recovery.

### Khắc phục:
1. **Trong `adapter.py` (`prepare_switcher_anchor`):**
   - Kiểm tra `if any(m in lowered for m in ("tổng lượt thích", "tổng số lượt thích")):`
   - Dò nút theo text/desc `("OK", "ok", "Đóng", "Close", "Xong")`.
   - Nếu không dò ra element, fallback tap thẳng vào tâm nút `(540, 1400)`.
   - Cho phép chọn ứng viên đầu tiên sau khi sắp xếp theo `y` thay vì yêu cầu `len(candidates) == 1`.
2. **Trong `state_machine.py` (`_dismiss_simple_close_popup`):**
   - Hỗ trợ thêm `content_desc=label` trong `_tap_if_found`.
   - Bổ sung fallback `adapter.tap(540, 1400)` nếu phát hiện chuỗi "tổng lượt thích" trước khi trả về `True`.

---

## 4. Soft Reboot Recovery kẹt ở 'proxy watcher did not publish post-reboot readiness'

### Triệu chứng:
Khi runner upload gặp lỗi UI và kích hoạt `SOFT REBOOT RECOVERY`, sau khi reboot máy văng lỗi:
```
Guarded reboot recovery failed: proxy watcher did not publish post-reboot readiness after reboot: proxy readiness timed out for <serial>
```

### Căn nguyên:
- Scheduled Task `GanProxyWatcherTray` trên Windows bị chuyển sang trạng thái `Disabled`.
- Không có tiến trình `gan_proxy_fleet.py watch` chạy ngầm để giám sát reconnect event của điện thoại và tự động khởi động app ViChanger cấp VPN card `tun0`.

### Khắc phục:
- Bật lại task qua PowerShell:
  `Enable-ScheduledTask -TaskName GanProxyWatcherTray; Start-ScheduledTask -TaskName GanProxyWatcherTray`
- Kiểm tra tiến trình: `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*gan_proxy_fleet*' }` phải có ít nhất 2 tiến trình (parent automation venv + child Python312).
- Kiểm tra log `watcher-logs\proxy-watcher-*.stdout.log` và xác nhận event `WATCH_EVENT_VERIFIED_SUCCESS` xuất hiện trong `watch-events.jsonl` của máy sau reboot.
