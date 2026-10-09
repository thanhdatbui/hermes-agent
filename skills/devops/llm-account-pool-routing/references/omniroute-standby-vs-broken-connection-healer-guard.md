# Phân Biệt Standby (isActive=0) vs Broken Connection & Kỷ Luật Silent Healer Watchdog

## 1. Bối cảnh & Hiện tượng
Hệ thống watchdog tự động kiểm tra sức khỏe và hồi sinh tài khoản OmniRoute (`cron_chatgpt_web_pool_watchdog.py`) chạy lúc 05:00 sáng đã gặp 2 lỗi nghiêm trọng:
1. **Spam Telegram Farm Alert:** Bắn báo cáo và log debug mỗi sáng dù pool hoạt động bình thường, vi phạm tôn chỉ **Silent Watchdog (`no_agent: True`)**.
2. **Hiểu nhầm Standby thành Broken Connection:** Tự động lôi 10 tài khoản Antigravity đang tắt toggle (`isActive = 0`) ra để khởi động GPM Playwright nhằm OAuth lại, sau đó lại vấp phải van kiểm tra 7 ngày tuổi profile GPM (`is_profile_aged_7_days`) và spam 10 dòng báo lỗi.

---

## 2. Bản chất kỹ thuật trên OmniRoute (`:20129`)

### a) Phân biệt `isActive` vs `testStatus`
Trong bảng `provider_connections` (SQLite `C:\Users\Kibe\.omniroute\storage.sqlite`):
- `testStatus == 'active'`: Token OAuth (refresh token) vẫn hợp lệ, kết nối tới upstream Google hoàn toàn sống. OmniRoute vẫn thực hiện refresh access token ngầm bình thường (~1 giờ/lần).
- `isActive == 0` (hoặc `False`): Chỉ là công tắc gạt **BẬT/TẮT (Toggle Switch)** trên giao diện Admin để tạm dừng không định tuyến traffic vào tài khoản (thường dùng khi admin gạt tắt để làm dàn dự phòng sâu hoặc bảo toàn quota cho các acc Pro ở trên).

### b) Lỗi lọc sai trong Healer Script cũ
```python
# LỖI: Gom chung việc tắt công tắc với lỗi kết nối
ag_inactive = [c for c in ag_conns if not (c.get('isActive') and c.get('testStatus') == 'active')]
```
Biểu thức `not (A and B)` tương đương `(not A) or (not B)`. Do đó, khi `isActive == False` (dù `testStatus == 'active'`), script coi là tài khoản bị hỏng kết nối, đòi mở Playwright để cấp lại OAuth consent từ đầu.

---

## 3. Van 7 Ngày (Aged Profile): On-boarding vs Self-healing
- **Van 7 ngày (`is_profile_aged_7_days`):** CHỈ dùng cho khâu **On-boarding (Nạp mới tài khoản)** từ dàn Phone Farm lên GPMLogin để tránh Google phát hiện tài khoản mới tạo đã bị tự động hóa OAuth.
- **Đối với Self-healing (Hồi sinh / Sửa connection cũ):** Connection đã tồn tại trên OmniRoute và đã từng OAuth thành công. Khi cần làm tươi lại phiên, tuyệt đối **KHÔNG ĐƯỢC CHẶN BỞI VAN 7 NGÀY GPM**.
- Nếu connection chỉ bị `isActive == 0` nhưng `testStatus == 'active'` và đã có `refresh_token`: **CHỈ CẦN CẬP NHẬT SQL `UPDATE provider_connections SET is_active=1`**, tuyệt đối cấm mở GPM Playwright làm tốn tài nguyên và dễ dính checkpoint.

---

## 4. Kỷ Luật Silent Watchdog (`no_agent: True`)
Theo chuẩn Hermes Agent:
1. **stdout = Tin nhắn gửi cho User:** Với cronjob `no_agent: True`, bất kỳ ký tự nào in ra `sys.stdout` đều được gateway tự động gom và bắn thẳng về Telegram.
2. **Khi không có lỗi mới hoặc pool 100% khỏe mạnh:** `sys.stdout` BẮT BUỘC để **RỖNG (EMPTY)**. Hermes sẽ im lặng hoàn toàn, không gửi tin nhắn rác.
3. **Log debug:** Bắt buộc chuyển toàn bộ `print(...)` hoặc `log(...)` sang `sys.stderr.write(...)` để lưu vào cron log file mà không kích hoạt gửi Telegram.
4. **Cấm dùng thẻ raw HTML:** Telegram Gateway của Farm cấm các thẻ thô `<b>`, `<code>`, `<i>` trong script cron để tránh vỡ parse mode; phải dùng định dạng Markdown hoặc văn bản sạch.
