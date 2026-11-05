---
name: google-account-trust-and-subscription-audit
description: "Kỷ luật đối soát gói Google One / Gemini Pro thực tế và phân định cấp độ Trust Score giữa Gmail Farm Batch vs Gmail Ngoại Cổ (Aged 5-6 năm)."
---
# Google Account Trust & Subscription Audit

## 1. Cạm Bẫy Kiểm Tra Gói Google One / Gemini Pro (Anti-False Assumption)
* **Bẫy sai sót:** Chỉ truy vấn bảng `provider_connections` với điều kiện `provider = 'gemini-web'` trong CSDL OmniRoute (`storage.sqlite`) rồi vội vàng kết luận tài khoản "chưa có gói Pro".
* **Bản chất thực tế:**
  - Các tài khoản được kích hoạt gói **Google AI Pro (5 TB / 2 TB)** trong farm còn được dùng làm nguồn tài nguyên cho nhánh `antigravity` (Google Cloud Code / Vertex AI OAuth) hoặc `codex`.
  - Có những tài khoản đã nhận thư "Chào mừng đến với Google AI Pro" từ Google One nhưng chưa được cấu hình vào OmniRoute.
* **Quy chuẩn kiểm tra Ground Truth:**
  - Tuyệt đối không suy diễn từ bảng cấu hình proxy/gateway.
  - **Cách 1 (Trực tiếp qua CDP/Browser):** Mở `https://one.google.com/storage`. Xác nhận bằng chứng dung lượng thực tế:
    - `0 GB/5 GB` hoặc `0 GB/15 GB` kèm nút mời chào nâng cấp (`Nâng cấp lên 30 GB...`) -> **100% Sạch gói (Free)**.
    - Huy hiệu `Pro`, dung lượng `2 TB` hoặc `5 TB` -> **Đã có gói Pro**.
  - **Cách 2 (Offline qua CSDL History của GPM Profile):** Quét file SQLite `Default/History` của profile trong thư mục GPM:
    - Nếu có bản ghi `one.google.com/activate-plan` hoặc `one.google.com/celebration` -> **Đã từng kích hoạt gói Pro**.

## 2. Phân Biệt Danh Tính: Gmail Farm Batch vs Gmail Ngoại Cổ (Aged 5-6 Năm)
* **Nhóm 1: Gmail Farm Batch (Nội bộ farm reg tháng 6 - 8/2026):**
  - Đặc điểm nhận diện: Email dạng `tên + ngày tháng năm sinh@gmail.com` (ví dụ: `dinhlan24072000`, `ninhy05102002`), mật khẩu có đuôi `...Ks`, mail khôi phục chung `thanhdatbui1995@gmail.com`.
  - Đặc tính: Được reg theo lô qua proxy/mạng farm, chủ yếu chạy background sync. Khi đem sang thiết bị lạ (Pixel / IP mới) để Fresh Sign-in, Google Risk Engine sẽ kích hoạt cơ chế thử thách **Robot Captcha / Bot Challenge**.
* **Nhóm 2: Gmail Ngoại Cổ (Aged Accounts 5 - 6 năm):**
  - Đặc điểm nhận diện: Tên tiếng Anh/ngoại quốc (`nathan.yabsley1990@gmail.com`, `marcusephillips...`, `allison...`), mật khẩu đặc trưng (như `n0spam@@`, `Btmyclrlw`), tuổi đời 5-6 năm từ trước khi nhập về farm.
  - Đặc tính: Độ Trust Score của Google đối với tuổi đời tài khoản rất cao, khả năng bị ăn Captcha bot check thấp hơn nhiều so với dàn mail batch.

## 3. Triage & Xử Lý Khi Gian Thương Báo "Dính Bot / Đòi Captcha" Khi Kích Gói Pixel
* **Nguyên nhân gốc rễ:**
  - Tool tự động hóa hoặc quy trình add gói của gian thương chạy trên máy Pixel / IP datacenter lạ.
  - Khi Google nhảy Captcha hình ảnh, tool của họ không tự giải được nên đẩy lỗi về phía người mua ("dính bot, dính mạng public").
* **Quy tắc giải quyết:**
  - Không vội vàng kết luận acc bị die hay bị checkpoint số điện thoại.
  - Yêu cầu bên bán mở trình duyệt gõ tay giải Captcha 1 lần trên thiết bị Pixel, nhập mã 6 số từ chuỗi 2FA Secret Key (TOTP) là đăng nhập thành công.
  - Nếu bên bán bắt buộc acc "trơn tru không Captcha", ưu tiên chọn dàn **Gmail Ngoại Cổ** hoặc mail cá nhân thật có phát sinh tương tác web thường nhật.

## 4. Bẫy "Chưa Bật 2FA" Dù Trong Sổ Cái Đã Lưu Chuỗi Secret Key & Quy Trình Bật Phối Hợp S7 + GPM
* **Hiện tượng:** Cột `twofa_secret` trong `farm_master.db` hoặc Excel lưu sẵn chuỗi Secret Key (32 ký tự Base32), nhưng khi bên bán đăng nhập thì Google báo "Bác bật 2FA lên nhe bác".
* **Bản chất kỹ thuật:** 
  - Tính năng `2-Step Verification` trên tài khoản Google thực tế **vẫn đang TẮT (Off)**. Tài khoản trước đó chỉ dùng xác thực một lớp hoặc qua Google Prompt/Số điện thoại. Chuỗi secret trong sổ cái là chuỗi cũ chưa được kích hoạt thành công trên Google Server.
  - Khi 2FA chưa bật, việc nhập secret key vào `2fa.live` là vô nghĩa vì Google Server không bao giờ hỏi OTP Authenticator khi đăng nhập.
* **Quy trình chuẩn kích hoạt 2FA Google Authenticator (Phối hợp S7 + GPM):**
  1. **Khởi động GPM qua CDP:** Gán proxy sống của máy S7 (tránh bị Google chặn IP lạ).
  2. **Vào trang 2FA:** Điều hướng tới `https://myaccount.google.com/signinoptions/two-step-verification?hl=vi`.
  3. **Vượt Google Prompt trên máy S7 thật:**
     - Khi Google gửi thông báo xác minh chọn số (ví dụ: số 53, 71) về điện thoại Samsung S7:
     - Giữ device lock qua `python D:/Taadaa/tools/with_device_lock.py --machine <N>`.
     - Bật sáng màn hình S7 (`input keyevent 224`), chụp màn hình qua ADB, chạy WinRT OCR nhận diện số cần bấm.
     - Bấm nút xác nhận "Có, chọn số trùng khớp" trên S7 (`input tap <x> <y>`) rồi bấm số tương ứng.
  4. **Bật 2FA:** Trên GPM, bấm nút "Bật tính năng Xác minh 2 bước".
  5. **Bóc Secret Key Authenticator:**
     - Vào `https://myaccount.google.com/two-step-verification/authenticator?hl=vi`.
     - Bấm "Thiết lập ứng dụng xác thực" -> "Không thể quét mã?".
     - **Cạm bẫy Base32:** Chữ cái `l` thường trong chuỗi hiển thị của Google khi đọc qua OCR thực chất là chữ `L` hoa (không phải số 1). Chuỗi chuẩn luôn gồm 32 ký tự Base32 (`A-Z`, `2-7`).
  6. **Hoàn tất xác minh OTP:**
     - Bấm "Tiếp theo", tính toán mã OTP 6 số qua `pyotp.TOTP(secret_key).now()`.
     - Điền mã OTP vào ô xác minh -> Bấm "Xác minh".
     - Chụp ảnh màn hình bằng chứng xác nhận `Authenticator | Đã thêm vừa xong`.
  7. **Đồng bộ Sổ Cái:** Cập nhật ngay chuỗi `twofa_secret` mới vào `farm_master.db` (bảng `mailboxes` & `tiktok_accounts`) và file Excel master.
