# Gmail 2FA Post-Reg Fresh-Account Delay & Cron Deferral Policy (12/09/2026)

## 1. Bản Chất Hiện Tượng & Cơ Chế Phòng Thủ Của Google (Root Cause)
Khi tài khoản Gmail vừa tạo thành công trên thiết bị Android Samsung S7 (Fresh Account):
- Nếu tiến hành mở Cài đặt Bảo mật (Security) -> Bật 2FA (2-Step Verification) hoặc Thêm Email khôi phục (Recovery Email) ngay lập tức:
  * **Trường hợp Bật 2FA**: Google bật màn hình WebView yêu cầu xác minh danh tính ("Để tiếp tục, trước tiên hãy xác minh danh tính của bạn"). Khi nhập đúng mật khẩu vừa tạo, hệ thống **không báo lỗi** mà rơi vào **vòng lặp xác minh vô tận (Loop Verification)** — tự động xóa trắng form và load lại đúng trang đó, ngăn chặn bot kích hoạt 2FA liên hoàn.
  * **Trường hợp Thêm Email khôi phục**: Sau khi xác minh mật khẩu, Google ép buộc người dùng quay video selfie khuôn mặt nhiều góc ("Lưu video selfie dùng để đăng nhập"). Nếu chọn "Để sau", Google redirect văng sang trang quảng cáo Google One AI và đóng luồng.
- **Quy luật:** Google kích hoạt cờ **Fresh Account Security Delay** trong vòng 24h - 48h đầu trên tài khoản mới tạo. Mọi nỗ lực can thiệp bảo mật cấp cao ngay trong phiên reg đều thất bại và gây trust penalty.

## 2. Chính Sách Điều Phối & Tách Rời (Decoupling Policy)
- **Tách rời tuyệt đối (Decouple):**
  * Script `gmail_reg_v10.py` **CẤM** gọi bật 2FA nối tiếp ngay sau khi reg. Mặc định `ENABLE_POST_REG_2FA=0`.
  * Sau khi reg thành công trên OS Android: Lưu chắc chắn 100% Email + Mật khẩu + Ngày sinh vào `gmail_clean_v2.xlsx` (có fallback atomic lock `single_writer_workbook_update`), sau đó đưa máy về Home an toàn và kết thúc phiên reg.
- **Hoãn bật 2FA qua Cron Watchdog (Chạy Sau Ca Trưa & Chỉ Lọc Acc Ngâm >= 48h):**
  * **Khung giờ tối ưu:** Xếp lịch chạy vào **`15:00` hàng ngày** (ngay sau khi Ca Trưa 12:00 - 14:00 kết thúc hoàn toàn và máy đã làm mát).
  * **Tránh giờ buổi tối / ban đêm:** Tuyệt đối **CẤM** chạy bật 2FA vào buổi tối (`18:00 - 23:00`) hoặc nửa đêm (`00:00 - 02:00`) để tránh xung đột với ca nuôi tối và chuỗi reg Gmail/TikTok ban đêm (`night-chain-reg-pipeline` lúc 01:00).
  * **Bộ lọc tuổi ngâm khắt khe:** Chỉ chọn các tài khoản Gmail **đã ngâm $\ge 48$ giờ** (`days_ago >= 2`), đảm bảo tài khoản đã hết sạch cờ Fresh Account Security Delay của Google.

## 3. Chốt Chặn An Toàn 3 Tầng Tránh Xung Đột Cron Nuôi Acc (TikTok Feed)
Kịch bản cron bật 2FA sau 24-48h BẮT BUỘC tuân thủ 3 tầng bảo vệ trước khi chạm thiết bị:
1. **Tầng 1 (Manifest Calendar Gate):** Đọc trực tiếp manifest lịch nuôi acc `hermes_cron_source_config.json`. Bỏ qua toàn bộ các máy đang trong ca nuôi hoặc sắp tới ca nuôi trong vòng **< 60 phút** (`buffer_minutes = 60`).
2. **Tầng 2 (Physical Device-Lock Gate):** Quét thư mục `~/.codex/device-locks/machine_<M>.lock.json`. Bỏ qua ngay các máy đang có lock `active`, `running`, `queued`, `blocked`.
3. **Tầng 3 (Lock-Aware Acquisition):** Tự acquire lock độc quyền `project="gmail-2fa-aged"` trước khi chạy ADB. Nếu runner nuôi acc kích hoạt đột xuất gặp lock này sẽ tự động lùi bước `SKIPPED_DEVICE_LOCKED`, không bao giờ xảy ra tình trạng 2 tiến trình giành giật màn hình cùng lúc.

## 4. Kỷ Luật Triển Khai On-Device 2FA & Chặn Stub Report Ảo (16/09/2026)
- **Tình trạng mã nguồn & Hiện trạng Repo Farm:**
  * Toàn bộ farm **CHƯA CÓ repo độc lập cho Add 2FA Gmail** (`D:\Taadaa\tiktok-add-bao-mat-f2a` là dành cho TikTok 2FA; `add mail khoi phuc` dành cho thêm email khôi phục).
  * Mã nguồn `D:\Taadaa\tools\enable_gmail_2fa_device.py` chỉ là code stub điều hướng đến tab Bảo mật (`SECURITY_NAVIGATED`) rồi trả về `status: "SUCCESS"` ảo mà chưa hề thực thi các bước bật 2FA cốt lõi.

## 5. Hiện Thực Kỹ Thuật: Web Playwright + S7 Security Code vs On-Device Webview (16/09/2026)
- **Tại sao On-Device Pure ADB (màn hình S7) bất khả thi?**
  * Khi bấm vào *Xác minh 2 bước* hoặc *Authenticator* trong Cài đặt Google Play Services trên Android 8 S7, hệ thống khởi chạy Webview nội bộ (`Octarine Webview`).
  * Webview này lập tức challenge password. Ngay sau khi nhập đúng password, Google bật cơ chế chống bot bằng **ReCAPTCHA hình ảnh ("Tôi không phải là người máy")** ngay trong Webview của thiết bị.
  * Việc giải reCAPTCHA bằng ADB thuần trên màn hình S7 là mong manh, dễ bị loop và tỉ lệ thất bại cực cao.
- **Kiến trúc Chuẩn Đã Được Chứng Minh Thực Tế (Proven Architecture trong `GPM auto`):**
  * Toàn bộ 71 Gmail có 2FA trong `gmail_clean_v2.xlsx` được tạo thành công thông qua engine `run_batch_2fa_kibe_pool.py` / `run_full_pipeline_2fa_and_oauth.py`:
    1. **Client Headless/Playwright:** Chạy Chromium trên PC gắn proxy đúng port Sing-box/Mobi của máy đó (`192.168.110.2:200xx`).
    2. Vào thẳng: `https://myaccount.google.com/two-step-verification/authenticator`.
    3. **Vượt Challenge bằng S7 ADB Bridge:** Khi web Google hỏi xác minh danh tính:
       - Nếu hiện **Google Prompt** (số PIN): Script ADB điều khiển S7 bấm đúng số PIN (`approve_s7_google_prompt`).
       - Nếu hiện **Mã bảo mật (Security Code)**: Script ADB mở `GoogleSettingsLink` -> *Tài khoản Google* -> *Bảo mật* -> *Mã bảo mật* để đọc mã 10 số (dùng ATX-agent port `17000+M` hoặc uiautomator dump) rồi điền vào web (`get_s7_security_code`).
    4. **Bóc tách Secret Key & Verify:** Bấm *"Không thể quét mã QR"* -> trích xuất chuỗi **Base32 32 ký tự** -> dùng `pyotp.TOTP(key).now()` điền mã 6 số xác nhận -> ghi vào cột 4 (`2fa`) của Excel.

## 6. Quy Tắc Kiểm Định Bật 2FA Thực Sự (Anti-Stub Invariant)
- Script/Worker chỉ được phép ghi nhận `SUCCESS` khi và chỉ khi:
  1. Đã vượt qua form xác nhận mật khẩu (nếu Google yêu cầu).
  2. Đã vào mục *Ứng dụng Authenticator* -> Bấm *Thiết lập* -> Chọn *Không thể quét mã QR* để trích xuất được chuỗi **Secret Key (Base32 32 ký tự)**.
  3. Dùng `pyotp.TOTP(secret).now()` sinh mã 6 số nhập vào form xác nhận và nhận diện màn hình kích hoạt thành công.
  4. Ghi nhận `secret_key` vào Cột 4 (`2fa`) của `gmail_clean_v2.xlsx` và kiểm tra lại giá trị ô Excel khác `None`/rỗng.
- CẤM TUYỆT ĐỐI các hàm chỉ điều hướng vào trang/tab Bảo mật mà trả về `status: "SUCCESS"`.

## 7. Kỷ Luật Silent Watchdog cho Cron `no_agent=True`
- Với cronjob có `no_agent: true`, Hermes gom toàn bộ `stdout` để deliver về Telegram.
- Toàn bộ log chi tiết từng bước điều hướng (`[serial] Bắt đầu quy trình...`, `Đã điều hướng...`) trong tool con BẮT BUỘC ghi vào `sys.stderr` hoặc file log riêng, TUYỆT ĐỐI KHÔNG `print` ra `stdout`.
- `stdout` CHỈ ĐƯỢC PHÉP in ra bảng tổng kết duy nhất `[BÁO CÁO 2FA GMAIL SAU CA SÁNG]` khi toàn bộ batch hoàn tất.
- Nếu không có máy nào đủ điều kiện hoặc máy đang bận: script BẮT BUỘC `return 0` hoàn toàn im lặng (stdout rỗng), chấm dứt triệt để việc spam tin nhắn rác lên nhóm Farm Alert.
