# Quy Tắc Kho Gmail Sạch: Chỉ Lưu Gmail Live & Cơ Chế Xóa Sổ Tài Khoản DIE

**Thời điểm ban hành:** 2026-10-04  
**Phạm vi áp dụng:** Hệ thống Farm Samsung Galaxy S7, các scripts trong `D:/Taadaa/register gmail`, `D:/Taadaa/tools`, `ensure_row_accounts.py`, và toàn bộ quy trình vận hành workbook Excel Farm.

---

## 1. Nguyên Tắc Cốt Lõi: `gmail_clean_v2.xlsx` CHỈ LƯU TÀI SẢN LIVE
- **Định danh kho:** File `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx` là **kho tài sản sạch** phục vụ cấp phát tài khoản Gmail sống cho các quy trình: nuôi YouTube, cấp cho GPMLogin PC, xác thực 2FA.
- **Kỷ luật triệt để:** 
  - Tuyệt đối **KHÔNG ĐƯỢC PHÉP** giữ lại các dòng tài khoản đã chết, bị khóa hay dính xác minh số điện thoại rồi chỉ ghi chú nhãn `"DIE"` ở Cột 11.
  - Khi một tài khoản được xác nhận DIE: **BẮT BUỘC XÓA DÒNG HOÀN TOÀN** (`ws.delete_rows(row_idx, 1)`). Sau khi dọn dẹp, toàn bộ các dòng trong file phải là tài khoản hoạt động bình thường.

---

## 2. Nơi Lưu Vết Duy Nhất Cho Tài Khoản DIE: `gmail_die_tong.txt`
- Khi xóa bỏ tài khoản DIE khỏi `gmail_clean_v2.xlsx` hoặc `master_gmail_manager.xlsx`, toàn bộ thông tin đối soát bắt buộc phải được ghi nối tiếp vào:
  📁 `D:/OneDrive/TaadaaData/kibe/gmail_die_tong.txt`
- **Định dạng ghi vết:**
  ```text
  <email>    <LÝ_DO_DIE>    <MÁY_S7_LIÊN_QUAN>    <TIMESTAMP>
  ```
  *Ví dụ:* `an.nhuan.work64541@gmail.com    DIE_CHALLENGE_PHONE    M3    2026-10-04 16:48:00`

---

## 3. Cạm Bẫy Kỹ Thuật: SMTP LIVE vs GOOGLE LOGIN DIE
- **Bản chất công cụ `checkmail.live` / `check_gmail_live_fast.py`:**
  - Kiểm tra trạng thái SMTP handshake / probe nhận thư từ bên ngoài.
  - Khi Google khóa tài khoản ở trạng thái thử thách số điện thoại (`challenge/iap`: *"Do có hoạt động bất thường, bạn cần xác minh danh tính qua số điện thoại để tiếp tục đăng nhập"*), hòm thư **vẫn có thể nhận thư đến**, do đó `checkmail.live` vẫn trả về tag `[LIVE]`.
- **Thực tế vận hành:**
  - Chiều đăng nhập (Web/App Login) đã bị Google chặn hoàn toàn.
  - Không thể tự giải quyết bằng mật khẩu hay 2FA TOTP (đòi hỏi mã SMS tốn phí).
  - **Quy chuẩn phân loại:** Bất kỳ tài khoản nào khi đưa vào thiết bị S7 hoặc GPM bị Google bật màn hình `challenge/iap` đòi hỏi SĐT thì **coi như DIE ngay lập tức**. Không tin tưởng mù quáng vào kết quả `LIVE` của SMTP checker.

---

## 4. Quy Trình Dọn Dẹp & Cấp Bù Slot Farm (TikTok / Device Slot)
Khi một tài khoản Gmail DIE làm kẹt quy trình đăng nhập TikTok trên máy Farm (do nick TikTok không có mật khẩu riêng, phụ thuộc vào OTP Gmail đã mất):
1. **Dọn sạch Gmail:**
   - Xóa dòng khỏi `gmail_clean_v2.xlsx`.
   - Ghi vết vào `gmail_die_tong.txt`.
   - Nếu tài khoản còn lưu phiên trên S7, thực thi gỡ bỏ qua `remove_device_google_account.py`.
2. **Dọn sạch Slot TikTok trên thiết bị:**
   - Trong `taikhoan_run_safe.xlsx`: Xóa rỗng ô TikTok ID tại hàng/slot tương ứng (`tiktok_id = ""`, `video_count = None`, `created_date = None`).
   - Trong `taikhoan_dat_v2_updated .xlsx`: Đổi tên nick thành `<tiktok_id>_DIE` hoặc ghi chú `REPLACED`.
3. **Kích hoạt quy trình cấp bù tự động:**
   - Chạy `ensure_row_accounts.py --row <N> --machines <M>` để hệ thống phát hiện slot trống và tự động nạp mail mới (ưu tiên Hotmail/Outlook có mật khẩu độc lập) để reg tài khoản TikTok mới bù vào.
