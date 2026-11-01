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
   - Gọi DAL: `farm_db.update_tiktok_credentials(username, email=new_email)`. Hàm DAL đã hỗ trợ tham số `email` để cập nhật trực tiếp vào bảng `tiktok_accounts`.
   - CSDL ghi nhận email mới tức thì, các cronjob và dashboard `:1905` đồng bộ ngay lập tức.
2. **Tầng 2 - Master Excel Mirror Backup (`taikhoan_dat_v2_updated .xlsx`):**
   - Cập nhật Cột F (`GMAIL`) = Hotmail mới, Cột G (`PASS MAIL`) = Pass Hotmail.
   - Giữ tính toàn vẹn song song giữa SQLite và Excel.
3. **Dọn dẹp thiết bị S7 & Mailbox Archive:**
   - Lúc này, Gmail cũ đã thoát khỏi danh sách `tiktok_bound_emails`.
   - Tiến hành gỡ bỏ tài khoản Google DIE khỏi máy S7 (`dumpsys account` / `preflight_s7_rolling_cleanup.py`) mà không sợ vi phạm rào chắn bảo vệ.

## 4. Cạm Bẫy & Kỹ Thuật Chạy Batch Song Song (Parallel Execution Pitfalls)
Khi triển khai chạy song song hàng loạt:
1. **Tránh Xung Đột Với Ca Nuôi Acc (Feed Session Lock Check):**
   - Farm có cronjob định kỳ chạy `multi-machine-feed-session` (ví dụ ca 2 lúc 14:00+).
   - Trước khi dispatch worker can thiệp thiết bị, BẮT BUỘC kiểm tra file lock `C:/Users/Kibe/.codex/device-locks/machine_{m_id}.lock.json`. Nếu `status == 'running'`, thiết bị đang trong ca nuôi độc quyền -> BỎ QUA hoặc chờ nhả lock, TUYỆT ĐỐI CẤM tranh chấp UI làm văng phiên feed.
2. **Hạn Chế Ngân Sách Workers (Throttling 4-5 Workers Thay Vì 15):**
   - Đẩy 15 workers đồng thời dễ làm nghẽn daemon USB ADB, gây timeout hoặc lỗi `getaddrinfo failed`.
   - Mức concurrency tối ưu là **4-5 workers**, kết hợp vòng lặp poll `/info` (thử tối đa 8 lần, delay 1s) sau khi khởi động stub để triệt tiêu lỗi `502 Bad Gateway`.
3. **Màn hình Tạo Video / Camera & LIVE Che Khuất (Tránh Báo Nhầm Captcha):**
   - TikTok thường lưu state mở thẳng vào màn hình quay camera/LIVE (`10 phút`, `60s`, `15s`, `ẢNH`, `VĂN BẢN`, `CAMERA`, `TẠO`, `LIVE`, `resource-id` kết thúc bằng `e1n` / `twt`).
   - CẤM nhận diện nhầm đây là popup Captcha/bảo mật. Nút đóng `X` nằm ở góc trên bên trái: bounds `[36,108][168,240]` (center `[102, 174]`). Bấm tọa độ này để thoát ra Home/Profile.
4. **Cuộn Tìm Tài Khoản Trong Switcher (Account Switcher Scrolling):**
   - Danh sách Switcher ban đầu chỉ hiển thị 3-4 nick. Các nick ở slot sâu hơn không có trong hierarchy ban đầu.
   - Khi `target_pt` trả về `None`, thực hiện vuốt cuộn xuống `atx_rpc(base_url, 'swipe', [540, 1400, 540, 500, 30])` rồi dump lại hierarchy để click đúng nick.
5. **Lỗi `Current profile: @None` / Splash Lag:**
   - Khi khởi động TikTok bằng `monkey` đồng loạt, bắt buộc cài đặt vòng lặp thăm dò `wait_for_profile_ready(timeout=10)` kiểm tra sự hiện diện của node Profile/Username trước khi thao tác tiếp.
