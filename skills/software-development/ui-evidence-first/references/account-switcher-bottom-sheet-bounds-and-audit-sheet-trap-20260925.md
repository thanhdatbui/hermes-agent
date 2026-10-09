# Account Switcher Bottom Sheet Bounds & Audit Sheet Trap (25/09/2026)

> **Mục tiêu**: Hướng dẫn điều tra, chẩn đoán và khắc phục sự cố cứu hộ đăng nhập TikTok khi Account Switcher Sheet gần đầy (7/8 tài khoản) và bẫy nạp nhầm sheet audit trong Excel tracking.

---

## 1. BẪY DUYỆT SHEET AUDIT TRONG TRACKING WORKBOOK

### 1.1. Hiện tượng thực tế (Incident Máy 72 - 25/09/2026)
- Khi tiến trình nuôi acc phát hiện thiếu nick `@m.ngc4624` trong switcher của Máy 72, runner gọi auto-login:
  ```bash
  python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py 72 --email m.ngc4624 --ss --allow-parent-lock
  ```
- Script lập tức ném lỗi và dừng lại:
  ```text
  STOPPED: Khong tim thay Gmail live tren may khop local-part 'duongthimyngoc190320011903' de xac nhan domain
  ```
- Mâu thuẫn: Trong sheet `Tài Khoản` chính chủ, nick `@m.ngc4624` có đầy đủ email `duongthimyngoc190320011903@gmail.com`, mật khẩu và 2FA key TOTP.

### 1.2. Nguyên nhân
- Trong `taikhoan_dat_v2_updated .xlsx`, ngoài sheet chính `Tài Khoản`, tồn tại các sheet lịch sử: `Khong Co Trong GmailClean`, `Audit Pending`, `Máy Thiếu Acc`...
- Sheet `Khong Co Trong GmailClean` lưu giá trị cụt `duongthimyngoc190320011903` (không có đuôi domain `@gmail.com`).
- Hàm `load_tracking_accounts_for_stt()` lặp qua mọi worksheet trong workbook (`wb.worksheets`), dẫn đến việc nạp cả dòng nháp vào bộ nhớ và gán nhầm issue `email_missing_domain`.
- Hàm `resolve_missing_domains_from_device()` bị kích hoạt kiểm tra Gmail app trên thiết bị thật, không thấy Gmail live tương ứng nên crash toàn bộ luồng cứu hộ.

### 1.3. Quy tắc khắc phục
1. **Chỉ đọc sheet canonical**: Giới hạn đọc sheet `Tài Khoản` hoặc `Accounts`, bỏ qua các sheet audit/nháp.
2. **Ưu tiên record không có issue**: Khi lọc tài khoản theo email/ID, ưu tiên record từ sheet chính và không có issue thiếu domain.
3. **Fallback ID + Password**: Nếu tài khoản có sẵn TikTok ID và Password, tự động suy luận domain `@gmail.com` để tiến hành login form thay vì crash.

---

## 2. BẪY TỌA ĐỘ VÙNG ĐÁY MÀN HÌNH (NAVIGATION BOUNDS TRAP) TRÊN GALAXY S7

### 2.1. Hiện tượng
- Khi máy đã có 7 tài khoản trong TikTok app, danh sách switcher đẩy nút **"Thêm tài khoản"** (`com.ss.android.ugc.trill:id/luu`) xuống sát đáy màn hình.
- Node bounds: `[0, 1788][1080, 1920]`.
- Nếu lấy tâm hình học `center_y = (1788 + 1920) // 2 = 1854`, vị trí tap `(540, 1854)` nằm quá sát đáy (cách mép đáy chỉ 66px), rơi vào vùng đệm navigation bar / gesture của Android Samsung.
- Thao tác tap bằng `input tap` hoặc click thông thường bị hệ điều hành nuốt hoặc TikTok không nhận được sự kiện, dẫn đến timeout 300s tại bước tìm/bấm nút thêm tài khoản.

### 2.2. Quy tắc an toàn
- Khi tap vào node hàng đáy (`bounds[3] >= 1900` trên màn hình 1080x1920):
  - Lệch điểm tap lên 30-35% chiều cao của node tính từ đỉnh:
    ```python
    x = (bounds[0] + bounds[2]) // 2  # 540
    y = bounds[1] + int((bounds[3] - bounds[1]) * 0.35)  # ~1834px
    ```
  - Hoặc áp dụng hard clamp: `y = min(y, 1835)`.
  - Giữ khoảng cách an toàn ít nhất 85px so với mép đáy 1920px.
