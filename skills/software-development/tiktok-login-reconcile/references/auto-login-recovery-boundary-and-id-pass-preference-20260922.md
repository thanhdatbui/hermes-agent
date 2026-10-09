# Kiến Trúc Tách Biệt Ca Nuôi vs Auto-Login & Cơ Chế Login Ưu Tiên TikTok ID (2026-09-22)

## 1. Tại Sao Khi Văng Nick Ca Nuôi Không Tự Động Gọi Hàm Login?

### A. Ranh Giới Kiến Trúc (Architecture Boundary)
- **Ca Nuôi (Feed Runner / Follow Runner)**:
  - Budget thời gian cố định rất chặt: **10–15 phút/batch/máy**.
  - Giữ `device_lock` độc quyền trong suốt ca.
  - Mục tiêu duy nhất: hoàn thành swipe video / follow theo kế hoạch.
- **Rủi ro nếu chen ngang hàm Login vào Ca Nuôi**:
  - Quá trình login tốn từ 2–5 phút/nick (mở form, nhập liệu, xử lý 2FA/OTP, kiểm tra UI).
  - Nếu gặp nick cần OTP email hoặc trễ mạng, toàn bộ batch nuôi sẽ bị quá hạn (timeout).
  - Kéo dài thời gian chiếm `device_lock`, gây xung đột khóa (deadlock / `SKIPPED_LOCKED`) với các ca chạy kế tiếp của thiết bị đó.
- **Quy tắc chuẩn hóa của Farm**:
  - **Ca Nuôi**: Chỉ chạy trên các nick đang active/có sẵn trong Switcher của máy. Nếu thiếu nick trong ca, runner ghi nhận `SKIPPED` và tiếp tục các nick khác, tuyệt đối không tự ý bung flow login.
  - **Ca Phục Hồi (Reconcile / Auto-Login)**: Chạy qua công cụ chuyên biệt (`reconcile_tiktok_accounts.py` hoặc `tiktok_login_v1.py`) vào khung giờ nghỉ an toàn giữa các ca.

---

## 2. Nút Thắt Kỹ Thuật Khiến Hàm Login Cũ Bị "Tắc Giữa Chừng" & Bản Vá (Commit 466103d)

### A. Bẫy Login Bằng Email (Email-First Flow)
- **Hành vi cũ**: `tiktok_login_v1.py` mặc định điền `account["login_email"]` vào form đăng nhập TikTok.
- **Hậu quả**:
  1. TikTok lập tức gửi mã OTP 6 số về hòm thư Gmail/Hotmail thay vì cho nhập mật khẩu.
  2. Script phải mở ứng dụng Gmail/Outlook trên điện thoại để tìm thư đọc OTP.
  3. Nếu máy chưa đăng nhập email đó, việc thêm Google account vào máy sẽ bị Google kích hoạt bảo mật: **bắt giải reCAPTCHA hình ảnh** (xe buýt, vạch qua đường, trụ cứu hỏa).
  4. Tool automation trên điện thoại không vượt qua được reCAPTCHA hình ảnh của Google, dẫn đến dừng với mã:
     `STOPPED: [7c] Không lấy được OTP từ <email>`.

### B. Bản Vá Chuẩn Hóa: Ưu Tiên TikTok ID + Pass + TOTP
- **Nguyên lý**: Khi tài khoản đã có sẵn TikTok ID (`id`) và TikTok Password (`tiktok_pass`), điền trực tiếp `login_target = account["id"]`.
- **Hiệu quả**:
  - TikTok nhận diện tài khoản qua username $\rightarrow$ chuyển thẳng sang màn hình **"Nhập mật khẩu"**.
  - Nhập mật khẩu TikTok từ Excel.
  - Nếu có 2FA Authenticator: sinh mã TOTP 6 số từ secret key (`pyotp`) điền vào.
  - **Vào thẳng TikTok 100%**, không cần mở app Gmail/Outlook, né triệt để bẫy OTP mail và reCAPTCHA Google.

```python
# Code chuẩn trong tiktok_login_v1.py (login_one_account):
ensure_login_entry_screen(device_id, stt=stt)
choose_email_login(device_id)
login_target = (account.get("id") or "").strip() if (account.get("id") and account.get("tiktok_pass")) else account["login_email"]
fill_existing_email_and_continue(device_id, login_target, stt=stt)
drive_login_screens(device_id, account, stt=stt)
```

---

## 3. Quy Trình Đối Soát Tránh Bẫy Báo Cáo Ảo "Văng Hết Nick"

1. **Không đối soát qua menu Cài đặt**:
   - Menu Cài đặt $\rightarrow$ Chuyển đổi tài khoản chỉ hiển thị 2 dòng đầu trước khi cuộn, dễ gây nhận định sai lầm là máy chỉ còn 2 nick.
2. **Bung Switcher từ Header Hồ sơ**:
   - Từ tab Hồ sơ, tap trực tiếp vào tên/username ở header trên cùng: `(500, 290)`.
   - Bottom sheet `rid='psy'` bung lên đầy đủ toàn bộ danh sách tài khoản.
   - Dump XML tìm toàn bộ node `rid='ndk'` để đếm chính xác số lượng nick đang đăng nhập (tối đa 8 nick).
