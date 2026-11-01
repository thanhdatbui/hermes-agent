# TikTok Email Replacement at Scale (Farm S7) & Concurrency Guard

## 1. Bản Chất Kỹ Thuật Đổi Email Trên App TikTok S7
- **Không đòi OTP Gmail cũ bị DIE:** Khi vào `Settings & Privacy > Account > Account Information > Email > Change Email`, app TikTok trên phiên bản Android S7 KHÔNG yêu cầu xác thực OTP từ Gmail cũ nếu session tài khoản đang sống trên app.
- Form sẽ mở thẳng ra ô `Nhập email` mới.
- Sau khi điền Hotmail mới có Microsoft Graph API, TikTok gửi mã OTP 6 số về Hotmail.
- Hệ thống bốc mã OTP qua Graph API (`login.live.com/oauth20_token.srf` + `graph.microsoft.com/v1.0/me/messages?$top=5`) và điền vào app TikTok trong vòng 2-3 giây.

## 2. Pitfalls Khi Đẩy Workers Song Song (Batch Concurrency Pitfall)
- **Bẫy Ảo Giác "Captcha" Từ Màn Hình Camera/LIVE Overlay:**
  - Khi TikTok mở app hoặc kết thúc ca trước, app thường dừng ở màn hình **Tạo video / Camera & LIVE** với các text `CAMERA`, `LIVE`, `ẢNH`, `15s`, `60s`.
  - **CẢNH BÁO:** Không được nhầm các nhãn này thành Captcha hay Security Challenge! Bấm nút `X` đóng Camera ở góc trên bên trái `[36,108][168,240]` (click `(102, 174)`) để đưa giao diện trở lại tab Hồ sơ.
- **Cuộn Switcher Tìm Nick Nửa Dưới (Scroll Down in Switcher):**
  - Màn hình Switcher chỉ hiển thị ~4-5 tài khoản đầu tiên.
  - Khi `target_pt is None`, BẮT BUỘC thực hiện một cú swipe cuộn xuống: `atx_rpc(base_url, 'swipe', [540, 1400, 540, 500, 30])`, sau đó re-dump XML để tìm các nick nằm ở nửa dưới danh sách (từ slot 5 đến 8). CẤM báo `ACCOUNT_NOT_FOUND` khi chưa vuốt cuộn.
- **Cấm đẩy quá cao (> 5 workers đồng thời):** Khi đẩy worker lên 15 luồng đồng loạt gửi request đổi email:
  1. TikTok backend kích hoạt ngay **Captcha trượt hình ảnh (Slide to complete the puzzle)** làm che khuất nút Tiếp tục $\rightarrow$ TikTok không gửi OTP $\rightarrow$ Timeout fail hàng loạt.
  2. Mạng Wi-Fi và ADB daemon quá tải làm app TikTok load chậm $\rightarrow$ tap Profile trượt vào màn Splash/Home (`Current profile: @None`).
- **Khuyến nghị an toàn:** Chỉ chạy song song từ 3 đến 5 workers kèm stagger 5-10s giữa các máy.
- **BẪY CHÍ MẠNG: BẤM ĐÓNG CAPTCHA LÀM TRIỆT TIÊU OTP (Captcha Dismiss Trap):**
  - Khi TikTok bật popup WebView "Xác minh để tiếp tục" (Puzzle Slider), yêu cầu gửi OTP chỉ được phát đi KHI VÀ CHỈ KHI vượt qua Captcha.
  - **CẤM TUYỆT ĐỐI** tự động bấm nút `X` (`verify-bar-close` hoặc text `Đóng`) để tắt popup rồi tiếp tục chờ OTP! Bấm tắt popup đồng nghĩa với việc TikTok **hủy yêu cầu đổi email ngay lập tức và KHÔNG gửi bất kỳ mã OTP nào về hòm thư** $\rightarrow$ Dẫn đến lỗi chờ OTP timeout 100%.
  - Khi gặp Puzzle Slider: Phải giải slider hoặc giữ hiện trường giải quyết, không được dismiss rồi poll OTP mù.

## 3. Phân Lập Kho Mail Theo Owner (`owner = 'kibe'` vs `'admin'`)
- Trong SQLite `farm_master.db`, bảng `mailboxes` phân tách rõ ràng theo `owner`:
  - `owner = 'kibe'`: Chứa các Hotmail sạch dành riêng cho cụm farm Kibe, token Microsoft Graph API sống 100% để bóc mã từ `register@account.tiktok.com`.
  - `owner = 'admin'`: Kho mail của Admin, nhiều mail hết hạn token (`401 Unauthorized`) hoặc đang dùng cho mục đích khác (ChatGPT OpenAI).
- **Quy tắc bắt buộc:** Khi query Hotmail thay thế cho cụm Kibe, câu SQL BẮT BUỘC phải có điều kiện `AND mb.owner = 'kibe'`. Tuyệt đối không query chung chung làm tràn sang kho `admin`. Kiểm tra tồn kho `kibe` trước khi nạp batch.

## 4. Tránh Xung Đột Ca Nuôi & Thiết Kế Watchdog Canh Máy
- **Xung đột ca feed (`multi-machine-feed-session`):** Trong các khung giờ nuôi acc (ví dụ Ca 2), toàn bộ máy bị khóa độc quyền bởi `operator_device_lock` (`C:/Users/Kibe/.codex/device-locks/machine_<id>.lock.json`).
- Thao tác đổi email trên UI app trong lúc ca feed đang chạy sẽ gây xung đột chiếm quyền, app bị crash, dính lỗi `502 Bad Gateway` hoặc văng ca nuôi.
- **Watchdog Pattern (`watchdog_hotmail_replacer.py`):**
  - Watchdog kiểm tra tiến trình `run_tiktok.py` qua `psutil` và kiểm tra device locks.
  - Chỉ khi ca feed hoàn tất (`is_feed_session_active() == False` và `get_active_feed_locks_count() == 0`), watchdog mới cho máy nghỉ 15s rồi tự động kích hoạt batch đổi email.

## 5. Quy Tắc Điều Khiển atx-agent & uiautomator Stub Trên S7
- **Deterministic Port Forward:** Dùng `zlib.crc32(serial.encode('utf-8')) % 800 + 17900` để map local port riêng cho từng máy, cấm dùng `hash(serial)` tránh collision.
- **Fix lỗi HTTP 502 Bad Gateway bằng Readiness Poll:** Trước khi tương tác, dọn sạch zombie và kích hoạt stub bằng pattern chuẩn:
  ```bash
  am force-stop com.github.uiautomator 2>/dev/null; killall atx-agent 2>/dev/null; /data/local/tmp/atx-agent server -d --addr 127.0.0.1:7912; monkey -p com.github.uiautomator 1 >/dev/null 2>&1 &
  ```
  Sau khi chạy lệnh trên, **CẤM dùng `time.sleep(2)` cố định**. Bắt buộc poll endpoint `http://127.0.0.1:{local_port}/info` (tối đa 8 lần, interval 1s) cho đến khi trả về HTTP 200 mới bắt đầu gửi RPC commands.

## 6. Dọn Dẹp Gmail DIE Ba Tầng (Three-Tier Cleanup)
1. **Tầng 1 (Android S7):** Mở khóa `tiktok_bound_emails` sau khi đổi Hotmail thành công $\rightarrow$ gọi `remove_account_adb()` gỡ sạch Gmail DIE khỏi Cài đặt tài khoản thiết bị.
2. **Tầng 2 (SQLite SSOT):** Cập nhật `email = <hotmail_mới>` vào bảng `tiktok_accounts` qua `farm_db.update_tiktok_credentials(username, email=...)`.
3. **Tầng 3 (Master Excel Mirror):** Cập nhật cột GMAIL và PASS MAIL trên `taikhoan_dat_v2_updated .xlsx` để dữ liệu backup đồng nhất 100%.
