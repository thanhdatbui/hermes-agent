# TikTok Login with ID + Pass + TOTP (Bỏ qua Mail Pass) & Upload Avatar UI Mới (2026-09-24)

## 1. Nhận diện tài khoản Usable khi thiếu Mail Pass (`tiktok_login_v1.py`)
- **Vấn đề**: Trước đây hàm `load_tracking_accounts_for_stt` trong `tiktok_login_v1.py` yêu cầu bắt buộc phải có cả `mail_pass` mới đánh dấu tài khoản là `usable=True`. Các tài khoản có ID + Pass TikTok + mã 2FA TOTP (Authenticator App) nhưng không có mật khẩu hòm thư (ví dụ Hotmail chưa kịp đổi pass/không có pass) bị gắn cờ `[CHECK]` và từ chối đăng nhập.
- **Giải pháp**:
  ```python
  has_id_pass = bool(account["id"]) and bool(account["tiktok_pass"])
  has_mail_auth = bool(account["login_email"]) and bool(account["mail_pass"])
  account["usable"] = (
      (has_id_pass or has_mail_auth)
      and "email_invalid" not in account["issues"]
  )
  ```
- **Kết quả**: Tài khoản có ID + Pass đăng nhập thẳng qua form TikTok ID mà không cần phụ thuộc vào mật khẩu mail.

## 2. Bẫy mở "Sửa hồ sơ" trên TikTok 47.x (Samsung S7) khi Upload Avatar
- **Bẫy Story / Nhật ký**: Bấm vào vòng tròn avatar trên Profile trang cá nhân (`bounds=[708,300][1080,636]` hoặc `(540, 336)`) thường mở nhầm vào luồng **"Thêm vào Nhật ký" (Story Picker)** thay vì mở màn hình sửa ảnh.
- **Điểm neo chính xác (Icon Bút Chì góc trên bên trái)**:
  - Trên giao diện Profile TikTok mới (v47.x) của Samsung S7 (1080x1920), nút mở "Sửa hồ sơ" là icon ImageView nằm ở góc trên bên trái:
    `bounds="[24,96][126,204]"` (center: `x=75, y=150`).
  - Cần đưa điểm neo này vào `_find_profile_edit_button` và mở rộng dung sai của `_find_new_profile_pencil`:
    ```python
    0 <= left <= 100 and 60 <= top <= 220 and 60 <= (right - left) <= 160 and 60 <= (bottom - top) <= 160
    ```
  - Bấm vào đây sẽ mở trực tiếp màn hình "Sửa hồ sơ" (`Thay đổi ảnh` / `yxg`).

## 3. Quy tắc đổi nguồn video nuôi nick khi `Video Đã Đăng` > 0
- Khi đổi nguồn video cho một nick đã có video đăng trước đó (ví dụ `Video Đã Đăng = 3`):
  - **GIỮ NGUYÊN** giá trị `Video Đã Đăng = 3` trong Excel (CẤM reset về 0).
  - Kho video render ra (`D:/TIKTOK-videonuoinick/<folder>`) **BẮT BUỘC** đánh số bắt đầu từ video tiếp theo (ví dụ `4.mp4`, `5.mp4`... thông qua cờ `--start-seq 4`), không render lại từ file `1.mp4`.
  - Giúp bot upload tự động pick đúng video số 4 mà không bị lặp lại các video đã đăng.
