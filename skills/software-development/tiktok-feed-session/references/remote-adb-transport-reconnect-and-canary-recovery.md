# Remote ADB Transport Reconnect & Canary Recovery

## Hiện tượng lỗi (Symptoms)
Khi chạy `python D:/Taadaa/tools/inspect_machine.py <N>` để kiểm tra hiện trường máy báo alert:
Lệnh bị timeout sau 10.0 giây với thông báo:
```
ERROR: Command '['C:\\Program Files (x86)\\xiaowei\\tools\\adb.exe', '-H', '192.168.110.119', '-P', '5037', '-s', '<serial>', 'shell', 'getprop', 'ro.product.model']' timed out after 10.0 seconds | Pin: ?% (Not charging) | Màn hình: UNKNOWN
• Current Focus: None
```

## Nguyên nhân gốc rễ (Root Cause)
Trên cụm Farm có máy chủ ADB Remote (ví dụ Admin Remote `192.168.110.119:5037` cho các máy N >= 200), một số thiết bị sau các phiên chạy dài hoặc khi màn hình tắt/AOD có thể bị nghẽn socket transport adb giữa adb server và adbd trên thiết bị (dù lệnh `adb devices` vẫn báo trạng thái `device`).

## Quy trình phục hồi O(1) an toàn (Targeted O(1) Reconnect)
- ❌ **CẤM TUYỆT ĐỐI:** Restart toàn bộ ADB server (`adb kill-server`) trên host remote — việc này sẽ làm đứt kết nối và hỏng phiên chạy của 79 máy còn lại trong fleet.
- ❌ **CẤM TUYỆT ĐỐI:** Khởi động lại thiết bị (reboot) hoặc can thiệp bằng tay khi chưa thử reconnect.
- ✅ **Lệnh phục hồi chuẩn O(1):**
  1. Với cụm Admin Remote (Máy N >= 200, serial tra cứu từ `D:/OneDrive/TaadaaData/admin/PROXYgandienthoai.xlsx`):
     ```bash
     "C:/Program Files (x86)/xiaowei/tools/adb.exe" -H 192.168.110.119 -P 5037 -s <serial> reconnect
     ```
  2. Với cụm Kibe Local (Máy N < 200):
     ```bash
     "C:/Program Files (x86)/xiaowei/tools/adb.exe" -s <serial> reconnect
     ```
  3. Ngay sau khi reconnect thành công (`reconnecting <serial> [device]`), chạy lại ngay lệnh trích xuất:
     ```bash
     python D:/Taadaa/tools/inspect_machine.py <N>
     ```
  4. Lệnh sẽ trả về tức thì thông tin Model, Pin, Màn hình, Focus Activity mà không còn timeout.

## Bẫy Báo Động Giả Captcha / Xác Minh do Profile Verification
- **Hiện tượng:** Bot Telegram báo `[CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]: Phát hiện 1 máy gặp captcha/xác minh (chưa mất phiên): Máy M239: profile verification navigation-failed: focused package unavailable`.
- **Bản chất:** Máy đã hoàn thành 100% video swipes (ví dụ 18/18). Sau khi swipe xong, runner chuyển sang bước `verify_profile` (hậu swipe) để đọc chỉ số follower. Lúc này adb transport bị timeout khiến `get_focused_activity` trả về None.
- **Bẫy false-positive:** Bộ lọc cảnh báo (`batch_aggregator.py`) trước đây quét từ khóa `verification` trong cụm từ `profile verification` nên phân loại nhầm thành lỗi Captcha/xác minh.
- **Quy tắc đối soát:** Luôn kiểm tra `total_swipes_completed` trong `summary.txt` hoặc `run_manifest.json`. Nếu `swipes_completed == swipes_requested`, tài khoản không hề bị văng nick hay dính captcha.
