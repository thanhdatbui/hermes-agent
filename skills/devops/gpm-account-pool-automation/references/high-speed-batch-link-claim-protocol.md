# High-Speed Batch Link Claiming & Google Activation Protocol

## 1. Bản chất và Thách thức
- **Loại tác vụ:** Săn link khuyến mãi/ưu đãi kích hoạt giới hạn số lượng (`serviceactivation.google.com`, Google One / AI Premium invite, Family group...).
- **Đặc thù thời gian:** Link thường bốc hơi trong vòng 3 - 5 phút ("cháy hàng", giật cô hồn).
- **Rủi ro lớn nhất:** 
  1. Dùng nhầm profile GPM chưa login, session hết hạn hoặc đang dính cooldown 7 ngày -> văng màn hình Sign-in, lãng phí link.
  2. Bị nghẽn do chạy tuần tự hoặc preflight check quá lâu lúc sự kiện đang diễn ra.

---

## 2. Quy tắc Bất Biến (Invariants)
1. **Tuyệt đối không preflight kiểm tra live lúc xả link:** Preflight tốn thời gian khiến link bị claim hết. Bắt buộc phải phân tách sẵn Group từ trước.
2. **Cấu trúc Group chuẩn trên GPMLogin:**
   - `Google_Live_Ready` (Group ID 10): Chỉ chứa các profile có session Google LIVE 100%, cookie còn hạn, đã verify OAuth/2FA.
   - `Google_Cooldown_Error` (Group ID 11): Cách ly các profile dính cooldown 7 ngày (`signin/rejected?rrk=77`), sai pass, dính checkpoint hoặc proxy chết.
3. **Gọi trực tiếp qua Group ID:**
   ```python
   # Lấy ngay danh sách profile sẵn sàng trong 0.05s
   resp = requests.get("http://127.0.0.1:19995/api/v3/profiles?group_id=10").json()
   ready_profiles = resp.get("data", [])
   ```
4. **Async Playwright CDP Concurrency (5-10 workers):**
   - Kết nối trực tiếp vào `remote_debugging_address` của Chrome GPM qua WebSocket.
   - Điều hướng với `wait_until="domcontentloaded"` (không chờ asset nặng / ảnh / tracker).
   - Inject click trực tiếp nút nhận qua DOM locator.
   - Khối `finally` bắt buộc gọi `/api/v3/profiles/stop/{id}` để đóng sạch Chrome, không để rò rỉ tiến trình.
