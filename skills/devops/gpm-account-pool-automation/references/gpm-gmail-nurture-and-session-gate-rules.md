# Quy tắc Nuôi Profile Gmail trên GPM & Phân loại Profile Hợp lệ

## 1. Nguyên tắc Tối thượng: LOẠI TRỪ TUYỆT ĐỐI Profile Chưa Login
- **Không nuôi profile vãng lai (Guest/Anonymous)**: Khi YouTube hoặc Google hiển thị nút "Đăng nhập" (Sign in), toàn bộ hành vi duyệt web (xem video, lướt tin tức Google News, tìm kiếm) chỉ ghi nhận vào cookie tạm thời của khách vãng lai. Tài khoản Gmail hoàn toàn KHÔNG được hưởng trust score, không hỗ trợ vượt checkpoint, và gây lãng phí nghiêm trọng tài nguyên:
  + Tốn dung lượng / băng thông Proxy 4G chuyên dụng.
  + Chiếm dụng slot chạy của các profile Gmail đang cần nuôi thực sự trên trạm Dual Xeon.
  + Làm sai lệch bức tranh sức khỏe tài khoản (profile chưa login thuộc về pipeline Login/Recovery, không thuộc pipeline Nurture).
- **Hành động bắt buộc**: Phải loại trừ profile chưa login ngay từ bước preflight; nếu phát hiện trong runtime thì đánh dấu trạng thái `NEEDS_LOGIN` để bàn giao cho bot login.

## 2. Kiến trúc Kiểm định Session Google 2 Tầng (Two-Tier Session Gate)

### Tầng 1: Preflight Offline Scan qua SQLite Cookies O(1)
- Trước khi khởi động trình duyệt hoặc cấp phát proxy, mở trực tiếp tệp SQLite Cookie của profile:
  + Đường dẫn: `<ProfilePath>/Default/Network/Cookies` (hoặc `<ProfilePath>/Default/Cookies`).
  + Mở với cờ Read-Only (`file:<path>?mode=ro`) để chống tranh chấp lock.
- **Tiêu chuẩn session hợp lệ**:
  ```sql
  SELECT count(*) FROM cookies 
  WHERE host_key LIKE '%google.com' 
    AND name IN ('SID', 'SSID', 'HSID', 'SAPISID');
  ```
- **Điều kiện Pass**: Đếm được `>= 2` token. Nếu `< 2`, loại ngay lập tức khỏi danh sách candidates của phiên nuôi. Quét toàn bộ hàng trăm profile chỉ mất ~0.1s.

### Tầng 2: Fail-Fast Live Check khi kết nối CDP Playwright
- Ngay sau khi Playwright gắn vào cổng CDP (`connect_over_cdp`), kiểm tra cookie live trong context:
  ```python
  live_cookies = context.cookies(["https://accounts.google.com", "https://www.youtube.com", "https://google.com"])
  found_session = {c.get("name") for c in live_cookies if c.get("name") in ('SID', 'SSID', 'HSID', 'SAPISID')}
  if len(found_session) < 2:
      logger.warning(f"[{email}] Mất session Google live! Dừng nuôi ngay lập tức.")
      update_state(email, status="NEEDS_LOGIN")
      browser.close()
      stop_gpm_profile(profile_id)
      return False
  ```

## 3. Kỷ luật Báo cáo Cron & Cấu hình `deliver: "local"` (CẤM SPAM Farm Alert)
- **Cấm bắn ảnh định kỳ**: Cron job nuôi định kỳ tuyệt đối KHÔNG in tiền tố `MEDIA:<path>` ra stdout/Telegram.
  + Việc tự động đẩy screenshot mỗi 2 tiếng gây rác kênh Telegram của user.
  + Mọi ảnh chụp screenshot nghiệm thu/debug (`nurture_{email}.png`) chỉ được lưu cục bộ tại `D:\Taadaa\GPM auto\debug_screenshots` để tra cứu theo yêu cầu O(1).
- **Khóa họng Farm Alert (`deliver: "local"`):**
  + Job cron `gpm-gmail-nurture-watchdog` BẮT BUỘC phải đặt `deliver: "local"`.
  + Tuyệt đối CẤM trỏ `deliver: "telegram:-5373649734"`. Kênh Farm Alert là kênh vận hành thiết bị nghiêm ngặt, cấm spam mọi output/log/summary của các cron nuôi chạy trên PC.

## 4. Kỷ luật Chụp ảnh Nghiệm thu YouTube
- **Tránh chụp lúc Preroll Ad**: YouTube bắt buộc phát quảng cáo tối thiểu 5s trước khi hiển thị nút "Bỏ qua quảng cáo" (Skip Ad). Chụp ở giây 1–2 sẽ chụp trúng màn hình quảng cáo hoặc spinner loading, gây hiểu nhầm code không bỏ qua quảng cáo.
- **Quy tắc thời điểm chụp**:
  + Chụp ảnh debug khi video chính đã phát ổn định từ giây thứ 25 trở đi (`elapsed >= 25`).
  + Hoặc chụp ngay sau khi sự kiện click "Bỏ qua quảng cáo" thành công.
