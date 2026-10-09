# Samsung S7 TikTok 47.x Profile Edit Pencil & Re-source Render Flow

## 1. Quy tắc đổi nguồn video nhưng giữ nguyên mốc đã đăng
- Khi đổi chủ đề video (ví dụ: chuyển từ chủ đề cũ sang Gái xinh) cho nick đang nuôi:
  - **GIỮ NGUYÊN `Video Đã Đăng` trong Excel** (ví dụ đang là 3 thì giữ nguyên 3, KHÔNG reset về 0).
  - Lý do: Bot upload lấy video tiếp theo bằng công thức `next_seq = video_da_dang + 1` (ví dụ `3 + 1 = 4`).
  - Thư mục render đầu ra (`D:/TIKTOK-videonuoinick/<folder>`) phải render và đánh số bắt đầu từ file `next_seq.mp4` (ví dụ: `4.mp4`, `5.mp4`, ..., `43.mp4`).
  - Xóa sạch các file cũ trước đó để tránh lẫn lộn nội dung cũ.

## 2. Quy tắc phân bổ video kênh gái xinh (Min 40, Max 45 & Gom video thừa)
- **Kênh Độc Quyền (Exclusive):**
  - Cắt lát lấy `min 40` đến `max 45` video đầu tiên (`vids[:45]`).
  - Toàn bộ video từ video thứ 46 trở đi (`vids[45:]`) tự động gom vào **Curated Pool** (bể gộp đa kênh) để tái sử dụng cho các nick Đa Kênh, không lãng phí video tải về.
  - Phải có cơ chế `gaixinh_claims.json` để khóa 1-1 kênh nguồn với folder gốc, chống trùng chéo trên toàn farm.

## 3. TikTok 47.x Profile Header Layout trên Samsung S7 (1080x1920)
- **Bẫy tap vào Circle Avatar / Ảnh hồ sơ:**
  - Trên giao diện TikTok mới (v47.x), nút avatar chính giữa `[708,300][1080,636]` (hoặc `bni`) khi tap vào sẽ mở popup **"Thêm vào Nhật ký" (Story Camera/Picker)** thay vì mở màn "Sửa hồ sơ".
  - Nếu lọt vào màn "Thêm vào Nhật ký", bot sẽ bị kẹt hoặc báo `SKIPPED_AVATAR_EDIT_UNAVAILABLE`.
- **Giải pháp chuẩn mở "Sửa hồ sơ":**
  - Trên Profile header, icon **Bút chì chỉnh sửa (Edit Pencil)** nằm ở góc trên bên trái:
    `bounds="[24,96][126,204]"` (class `android.widget.ImageView`).
  - Kích thước: `102x108 px`.
  - Tap trực tiếp vào tọa độ tâm `(75, 150)` này sẽ mở ngay màn hình **"Sửa hồ sơ"** (`Thay đổi ảnh`) chính thức.

## 4. Account Switcher & Missing Account Triage
- Nếu TikTok Switcher báo `ACCOUNT_VERIFY_MISMATCH`:
  - Kiểm tra xem nick đã đăng nhập trên máy chưa. Nếu thiếu nick trong switcher, chạy bù flow login:
    `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <ID/Email> --allow-parent-lock --ss`
  - Với tài khoản có sẵn ID + Password + 2FA TOTP trong tracking, script login không được chặn vì thiếu `mail_pass`.
