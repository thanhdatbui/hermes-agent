# Hotmail Replacement for TikTok Accounts with Dead Gmail & Dual Cleanup Protocol

## 1. Ngữ Cảnh & Triệu Chứng
- Các tài khoản TikTok "cựu binh" / "nick già" trước đây liên kết bằng Gmail.
- Khi Gmail bị Google vô hiệu hóa (DIE), người vận hành lưu vào sheet `Gmail_DIE_Archive` trong `master_gmail_manager.xlsx`.
- **Rào chắn an toàn lịch sử:** Script dọn dẹp tài khoản Android (`preflight_s7_rolling_cleanup.py`) có cơ chế an toàn: cấm gỡ Gmail khỏi điện thoại nếu email đó vẫn đang nằm trong `tiktok_bound_emails` (tránh mất dấu liên kết tài khoản).
- Hậu quả: Nhiều tài khoản TikTok trên farm bị "kẹt", vẫn mang email Gmail DIE trên app TikTok, CSDL SQLite `farm_master.db`, và file Excel.

## 2. Quy Trình Thay Thế Hotmail Trên S7 Native (100% Thành Công, Không Cần Pass Gmail Cũ)
Khi tài khoản TikTok đang có session đăng nhập trên app native điện thoại S7:
1. **Bung Switcher & chọn đúng nick:** 
   - Vuốt nhẹ header profile để cố định sticky header -> Tap header display name / ID -> Chọn đúng nick trong switcher bottom sheet.
2. **Mở Cài đặt tài khoản:**
   - Tap *Menu hồ sơ* (hamburger 3 gạch góc trên phải: bounds `[954,96][1056,204]`).
   - Tap *Cài đặt và quyền riêng tư* (bounds `[204,1176][1038,1320]`).
   - Tap *Tài khoản* (bounds `[24,1722][1056,1899]`).
   - Tap *Thông tin tài khoản* (bounds `[24,246][1056,402]`).
3. **Thao tác Đổi Email:**
   - Tap mục *Email* (bounds `[24,402][1056,558]`).
   - Popup hiện ra gồm 2 lựa chọn: *Thay đổi email* và *Hủy liên kết email*.
   - **BẮT BUỘC chọn "Thay đổi email"** (Không bấm "Hủy liên kết email" vì TikTok có thể chặn hủy nếu chưa có SĐT).
   - Nếu có dialog cảnh báo *"Thay đổi email? Email mới cũng sẽ dùng cho xác minh 2 bước"*, bấm **"Tiếp tục"** (bounds `[541,1212][960,1355]`).
4. **Nhập Hotmail mới & Bóc OTP qua Graph API:**
   - Nhập prefix username của Hotmail mới (từ kho phôi có sẵn `oauth_refresh_token`).
   - Tap nút gợi ý `@hotmail.com` (bounds `[809,927][1080,1011]`) để điền nhanh và chuẩn xác.
   - Bấm **"Tiếp tục"** (bounds `[96,735][984,891]`) -> TikTok gửi mã OTP 6 số đến Hotmail và bắt đầu đếm ngược 60s.
   - Gọi **Microsoft Graph API** (`https://graph.microsoft.com/v1.0/me/messages?$top=5`) bóc mã OTP từ sender `register@account.tiktok.com` trong vòng 1-2 giây.
   - Nhập 6 số OTP bằng `pressKeyCode` vào app TikTok -> Màn hình tự động cập nhật về `Thông tin tài khoản` với email mới dạng `x***y@hotmail.com`.

## 3. Đồng Bộ Dữ Liệu 3 Tầng (Write-Through Architecture)
Sau khi TikTok đã nhận Hotmail mới:
1. **Tầng 1 - SQLite Cố định (`farm_master.db` - SSOT):**
   - Gọi DAL: `farm_db.update_tiktok_credentials(username, email=new_email)`.
   - CSDL ghi nhận email mới tức thì, các cronjob và dashboard `:1905` đồng bộ ngay lập tức.
2. **Tầng 2 - Master Excel Mirror Backup (`taikhoan_dat_v2_updated .xlsx`):**
   - Cập nhật Cột F (`GMAIL`) = Hotmail mới, Cột G (`PASS MAIL`) = Pass Hotmail.
   - Giữ tính toàn vẹn song song giữa SQLite và Excel.
3. **Dọn dẹp thiết bị S7 & Mailbox Archive:**
   - Lúc này, Gmail cũ đã thoát khỏi danh sách `tiktok_bound_emails`.
   - Tiến hành gỡ bỏ tài khoản Google DIE khỏi máy S7 (`dumpsys account` / `preflight_s7_rolling_cleanup.py`) mà không sợ vi phạm rào chắn bảo vệ.

## 4. Cạm Bẫy & Kỹ Thuật Chạy Batch Song Song (Parallel Execution Pitfalls)
Khi triển khai chạy song song hàng loạt (ví dụ: ThreadPoolExecutor với 10-15 workers):
1. **Lỗi `Current profile: @None` / Splash Lag:**
   - Khi khởi động TikTok bằng `monkey` đồng loạt trên nhiều máy, tải ADB và I/O thiết bị tăng đột biến. Lệnh click Profile tab nếu bắn quá sớm (sleep cứng 2-3s) sẽ rơi vào màn hình Splash hoặc Home chưa render xong.
   - **Giải pháp:** Bắt buộc cài đặt vòng lặp thăm dò `wait_for_profile_ready(timeout=10)` kiểm tra sự hiện diện của node Profile/Username trước khi thao tác tiếp.
2. **Lỗi `502 Bad Gateway` từ `atx-agent`:**
   - Tiến trình uiautomator stub ngầm có thể bị crash hoặc timeout khi nhận nhiều RPC dồn dập.
   - **Giải pháp:** Mỗi worker trước khi thực thi cần gửi health-check nhanh `GET /info`. Nếu không phản hồi hoặc 502, lập tức chạy lệnh khởi động lại:
     `adb -s <serial> shell "killall atx-agent 2>/dev/null; /data/local/tmp/atx-agent server -d"` kèm delay 1s trước khi gọi RPC.
3. **Màn hình Camera / LIVE Popup Che Khuất:**
   - Một số nick khi mở app hoặc sau khi thoát modal xác minh có thể bị rơi vào màn hình LIVE/Tạo video (`CAMERA`, `TẠO`, `LIVE`).
   - Nút đóng của màn hình LIVE nằm ở góc trên bên trái `[18,72][150,204]` (center: `(84, 138)`). Worker cần kiểm tra nếu thấy chữ `Trung tâm LIVE` hoặc `Kiểm tra quyền truy cập LIVE` thì bấm tọa độ này để thoát ra màn hình chính.
