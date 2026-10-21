# Flash Link Sniper, GPM CDP Claiming & Cross-Host Alarm Protocol

## Bối cảnh & Yêu cầu nghiệp vụ
- Khi mua các gói link kích hoạt flash (ví dụ: `Link Gemini Pro 18M` trên SumiStore/Telegram shop) có thời gian bảo hành cực ngắn (5 - 10 phút kể từ lúc mua) và số lượng tồn kho hiếm (`stock = 0`, cần canh nhồi hàng).
- Thách thức:
  1. Cần công cụ bắn lệnh mua tức thì khi có hàng (đo bằng ms, hỗ trợ HMAC-SHA256 signature).
  2. Cần chuẩn bị sẵn 1 tài khoản Gmail sống khỏe trong GPM pool để nhận link kích hoạt.
  3. Cần cơ chế thông báo báo động đa tầng không thể bỏ lỡ: hú còi liên tục trên máy phụ (Admin-PC `192.168.110.119`) cho tới khi người dùng chủ động tắt, đồng thời tự động bung tab kích hoạt trên GPM profile đã đăng nhập sẵn.

---

## 1. Chuẩn Hóa Lọc Tài Khoản Gmail Sống Khỏe 3 Tầng (Preflight Session Audit)
Trước khi khởi chạy bot sniper, bắt buộc chọn sẵn tài khoản nhận link:
1. **Lọc Blacklist DIE:** Đọc `D:\OneDrive\TaadaaData\kibe\gmail_die_tong.txt` để loại bỏ các nick đã chết.
2. **Đối soát Master Excel:** Đọc `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` lấy thông tin mật khẩu dự phòng, mã 2FA TOTP, mail khôi phục.
3. **Thẩm định SQLite Cookies vật lý:**
   - Đọc `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\<ProfilePath>\Default\Network\Cookies` (hoặc `Default\Cookies`).
   - Kiểm tra Chrome 1601 Epoch timestamp:
     `now_chrome = int((time.time() + 11644473600) * 1000000)`
   - Xác nhận có đủ bộ ba session cookie Google còn hạn: `{'SID', 'HSID', 'SSID'}`.

---

## 2. Kỹ Thuật Ký HMAC-SHA256 & Bắn Lệnh Mua (SumiStore API)
Endpoint mua hàng: `POST https://sumistore.me/api/tele-product/buy`
- Header bắt buộc:
  - `X-Tele-API-ID`: API key của bot.
  - `X-Timestamp`: Unix timestamp (giây).
  - `X-Nonce`: Chuỗi UUID ngẫu nhiên.
  - `X-Signature`: `hmac.new(API_ID, f"{t}|{nonce}|{body}", sha256).hexdigest().lower()`.
- Payload: `{"id": PRODUCT_ID, "quantity": 1}`.

---

## 3. Khởi Động GPM Profile & Mở Link Kích Hoạt Tức Thì (O(1))
Thay vì mở Playwright cồng kềnh mất nhiều giây, sử dụng trực tiếp HTTP endpoint của GPM Local API và CDP:
1. Bật profile GPM:
   ```text
   GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?skip_proxy_check=true
   ```
2. Lấy `remote_debugging_address` từ response.
3. Gửi lệnh tạo tab mới qua CDP REST endpoint (thực thi dưới 50ms):
   ```text
   PUT http://{remote_debugging_address}/json/new?{activation_link}
   ```
Trình duyệt GPM của profile đã đăng nhập sẵn Google sẽ lập tức bung tab chứa link mời Family / Google One trước mắt người dùng.

---

## 4. Báo Động Xuyên Máy (Cross-Host Continuous Alarm)
Để người dùng không bỏ lỡ hạn 5 phút kể cả khi rời bàn làm việc:
1. **Triển khai còi hú sang Admin-PC:**
   - Dùng `D:\Taadaa\tools\admin_ssh.py` đẩy script còi hú `admin_alarm.py` sang Admin-PC (`192.168.110.119`).
   - Khi mua thành công, gọi lệnh chạy ngầm không chặn:
     ```powershell
     Start-Process python -ArgumentList 'D:\Taadaa\tools\admin_alarm.py' -WindowStyle Hidden
     ```
2. **Kỷ luật còi hú liên tục:**
   - Script chạy vòng lặp vô tận `winsound.Beep(1200, 250)` và `winsound.Beep(1800, 300)`.
   - Chỉ dừng khi phát hiện file cờ `D:\Taadaa\tools\stop_alarm.flag` hoặc nhận lệnh `pkill -f admin_alarm.py`.
   - Kết hợp bíp loa máy Kibe cục bộ để báo động đa điểm.
