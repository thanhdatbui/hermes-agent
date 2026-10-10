# Quy trình Xử lý Tài khoản Dôi Dư / Bị Đá Ra và Nguyên tắc Ngâm Nguội (Displaced Account Cooldown & Re-allocation Protocol) (2026-10-10)

## 1. NGUYÊN CƠ PHÁT SINH TÀI KHOẢN DÔI DƯ (DISPLACED ACCOUNTS)
- Khi một tài khoản ký sinh (hoặc tài khoản reg bù tạm thời) chiếm nhầm slot trên thiết bị:
  - Ví dụ: Trên Máy 20, tài khoản `@javialdzxxj` (reg 26/08, 45 ngày tuổi, LIVE) chiếm slot 8 khiến nick chính chủ `@anhdo829` bị văng khỏi Switcher.
  - Khi Coordinator chạy script giải phóng slot và đăng xuất tài khoản ký sinh, tài khoản này trở thành **tài khoản dôi dư hợp lệ (valid displaced account)**: nick vẫn sống, có follower, có tuổi thọ cao (aged), là tài sản giá trị của Farm.

---

## 2. NGUYÊN TẮC NGÂM NGUỘI CHỐNG BẪY DEVICE HOPPING (BẮT BUỘC)
- **Câu hỏi nghiệp vụ**: *"Có nên kiếm máy trống login lên ngay không, hay ngâm vài ngày rồi mới login?"*
- **Quy tắc bất biến**: **BẮT BUỘC NGÂM NGUỘI 24H - 48H, CẤM LOGIN NGAY LẬP TỨC SANG MÁY KHÁC.**

### Lý do kỹ thuật:
1. **Thuật toán Device Hopping Detection của TikTok**:
   - Khi một tài khoản vừa được đăng xuất trên một thiết bị (ví dụ Samsung S7 Máy 20, fingerprint A, IP Proxy A):
   - Nếu trong vòng vài phút hoặc vài giờ mà tài khoản đó lại gửi request đăng nhập từ một thiết bị hoàn toàn khác (máy B, Android ID B, IP Proxy B):
   - Hệ thống chống gian lận (Anti-fraud) của TikTok lập tức cắm cờ bất thường:
     * Buộc giải Captcha khó hoặc văng lỗi xoay vòng.
     * Đòi mã OTP gửi về email (nếu email die hoặc chưa có 2FA thì nick bị kẹt chết).
     * Nguy hiểm nhất: TikTok cắm cờ ngầm tài khoản bị nghi ngờ mua bán / hack / chuyển nhượng ➔ **Shadowban vĩnh viễn (0 view khi đăng clip)**.
2. **Lợi ích của việc ngâm nguội 24h - 48h**:
   - Đảm bảo toàn bộ session, token cũ và cache kết nối trên server TikTok đã timeout hoàn toàn.
   - Khi đăng nhập lên máy mới sau 24h-48h qua đúng proxy của máy đó, TikTok coi đó là hành vi người dùng đổi điện thoại tự nhiên, tỷ lệ thành công 100% không bị challenge.

---

## 3. CHIẾN LƯỢC QUÂN DỰ BỊ VÀ QUY TRÌNH NẠP TRƯỚC SỔ CÁI (PRE-ALLOCATION)
Trong thời gian ngâm nguội 24-48h, Coordinator tiến hành quy trình xếp chỗ trước trên hệ thống sổ cái mà KHÔNG đụng vào thiết bị thật:

### Bước 1: Rà soát máy trống trên toàn Farm (Kibe & Admin)
- Kiểm tra các máy có số lượng tài khoản `< 8`:
  * Cụm Kibe (M01-M80): Nếu đã kín 640/640 slot thì tuyệt đối không nhồi thêm.
  * Cụm Admin (M201-M280): Rà soát các máy thiếu ở Row 2, Row 7, Row 8 (ví dụ Máy 255 chỉ mới có 1 acc ở Row 1).

### Bước 2: Gán slot và kho video chuẩn Invariant
- **Công thức slot cứng**: `slot = (folder - 1) % 8 + 1`.
  * Ví dụ nạp vào Máy 255 Ca Tik 2 (Slot 2) ➔ Folder Video = `434`.
  * Khảo sát kho video trên máy đích (`admin-farm` `D:\TIKTOK-videonuoinick-admin\434`) đảm bảo có đủ video sạch (tối thiểu 45 clip).
  * Set bộ đếm `Video Đã Đăng = 0` (đăng từ clip `1.mp4`).

### Bước 3: Đồng bộ cả 3 file Master Cụm Admin
1. **`admin/taikhoan_dat_v2_updated .xlsx`**:
   - Chèn dòng chuẩn vị trí (ví dụ sau dòng của Máy 254):
     `Máy 255 | Folder 434 | ID: javialdzxxj | Pass: <pass_tt> | Mail: <hotmail> | Pass mail: <pass_mail> | Device: <serial_m255>`
2. **`admin/Tik2.xlsx`**:
   - Dòng 56 (Máy 255): Gán `ID: javialdzxxj`, `Folder Video: 434`, `Video Đã Đăng: 0`, Niche `Yoga`.
3. **`admin/taikhoan_run_safe.xlsx`**:
   - Dòng 435 (Máy 255 - Slot 2): Cập nhật `javialdzxxj`.

### Bước 4: Kiểm định Invariant Rules bắt buộc
- Chạy kiểm tra:
  ```bash
  python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir "D:/OneDrive/TaadaaData/admin"
  ```
- Bắt buộc trả về `[RESULT] PASS 100% (0 cảnh báo)` trước khi kết thúc ca.
- Khi đủ 24-48h ngâm nguội, ca đăng nhập mới được kích hoạt qua `tiktok_login_v1.py 255 --email javialdzxxj`.
