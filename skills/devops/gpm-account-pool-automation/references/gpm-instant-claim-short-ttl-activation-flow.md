# GPM Instant Claim Flow & Live Gmail Resolution For Short-TTL Activation Links

## 1. Context & Business Problem
- **Short-TTL Activation Links (5–10 Minutes Warranty):** Gói nâng cấp (Google One, Gemini Pro 18M Family, YouTube Premium invite) từ các shop Telegram/API bên thứ 3 thường có thời hạn bảo hành cực ngắn (5–10 phút). Nếu thao tác thủ công (copy link -> tìm nick -> mở profile -> đăng nhập -> xác nhận), link sẽ hết hạn hoặc bị thu hồi dẫn đến mất tiền oan.
- **Yêu cầu đối soát tài khoản:** Link nâng cấp bắt buộc phải được kích hoạt trên một tài khoản Gmail sạch (chưa có gói active hoặc chưa dính family khác) và **đang có session Google Cookies sống khỏe 100% trong GPM** để không bị challenge (2FA/SMS/Password prompt) làm chậm trễ thời gian vàng.

## 2. Quy trình 3 Tầng Tìm Gmail Sống Khỏe Trong Pool GPM (Zero-Human Discovery)
Thực hiện thẩm định 3 tầng để lọc ra tài khoản sẵn sàng sử dụng:
1. **Tầng 1 (Master Workbook SSOT & DIE Exclusion):**
   - Đọc danh sách tài khoản từ `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (sheet `Gmail Accounts`).
   - Lọc bỏ ngay lập tức toàn bộ email nằm trong danh sách chết tổng `D:\OneDrive\TaadaaData\kibe\gmail_die_tong.txt`.
2. **Tầng 2 (Physical Storage & Active Cookies Inspection):**
   - Đọc danh sách profile từ SQLite `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`.
   - Mở SQLite read-only `file:<ProfilePath>/Default/Network/Cookies?mode=ro`.
   - Tính timestamp Chrome epoch: `now_chrome = int((time.time() + 11644473600) * 1000000)`.
   - Bắt buộc kiểm tra bộ ba cookie phiên Google cốt lõi: `SID`, `HSID`, `SSID` có `expires_utc == 0` hoặc `expires_utc > now_chrome`.
3. **Tầng 3 (GPM Local API & Proxy Liveness):**
   - Kiểm tra profile qua GPM Local API `http://127.0.0.1:19995/api/v3/profiles/{id}`.
   - Xác nhận `raw_proxy` (Mobile Proxy port) khả dụng, không bị xung đột với các tiến trình chạy ngầm khác.

## 3. Kiến Trúc Auto-Claim Dưới 10 Giây (Fast Activation Loop)
Ngay khi script sniper bắt được stock > 0 và mua thành công link:
1. **Trích xuất Link:** Parse URL kích hoạt (`activation_link`) từ response đơn hàng hoặc endpoint orders.
2. **Khởi động GPM Profile qua API:**
   ```python
   # Gọi GPM Local API bật profile đã chuẩn bị sẵn
   start_url = f"http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?skip_proxy_check=true"
   # Lấy remote_debugging_address từ response
   ```
3. **Điều hướng thẳng đến Link Kích hoạt qua CDP:**
   - Kết nối Playwright qua `connect_over_cdp`.
   - Mở page mới hoặc điều hướng tab chính đến `activation_link`.
   - Trình duyệt bật lên ngay trước mắt với session Google đã đăng nhập sẵn -> User chỉ cần click đúng nút "Chấp nhận" / "Tham gia" mà không cần gõ mật khẩu hay xác minh gì thêm.
4. **Báo động đa tầng:**
   - Phát âm thanh dồn dập qua loa Windows (`winsound.Beep`).
   - Bắn tin nhắn Telegram khẩn cấp về điện thoại kèm link kích hoạt để dự phòng khi user rời máy.
