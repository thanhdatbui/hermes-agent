# Chống Bốc Lại Email Đã Đăng Ký TikTok & Kỷ Luật Điều Phối Batch

## 1. Nguyên nhân cốt lõi lỗi "Email đã có tài khoản TikTok"
- Bên bán KHÔNG bán mail bẩn hay mail đã đăng ký.
- Lỗi phát sinh hoàn toàn do hệ thống Farm:
  1. Trong quá trình reg các đợt trước, script đã tạo tài khoản TikTok thành công nhưng ghi nhận vào sổ cái `taikhoan_dat_v2_updated .xlsx` bị chậm/bị lỗi (do OneDrive lock file dwShareMode=0).
  2. Khi `_detect_clean.py` / `tiktok_target_eligibility.py` quét tìm mail sạch, những mail đã reg này không nằm trong sổ cái nên bị coi là "mail chưa dùng" và cấp lại cho máy.
  3. Khi nhập mail trên app TikTok, TikTok phát hiện mail đã liên kết -> văng màn hình đăng nhập/OTP verify và báo lỗi `[07]`.

## 2. Kiến trúc giải pháp triệt để 3 lớp:
1. **Persistent Blacklist (`data/registered_emails_blacklist.json`)**:
   - Lưu trữ danh sách email chuẩn hóa (strip, lower) đã từng có tài khoản TikTok hoặc gặp màn hình verify/OTP.
   - Luôn tồn tại độc lập với file Excel, không bị ảnh hưởng bởi lỗi lock file của OneDrive.
2. **Preflight Exclusion (`tiktok_target_eligibility.py` & `_detect_clean.py`)**:
   - `load_registered_mailboxes` nạp đồng thời:
     - Sổ cái chính `taikhoan_dat_v2_updated .xlsx`.
     - Danh sách `registered_emails_blacklist.json`.
     - Toàn bộ kết quả `tracking_result_*.json` thành công trong các thư mục artifacts runs gần nhất.
   - Loại trừ 100% email đã có TikTok ngay từ bước chọn target.
3. **Runtime Auto-Record (`social_reg_v1.py`)**:
   - Khi hàm `detect_after_continue` trả về `registered` hoặc `registered_otp`, script lập tức gọi:
     ```python
     record_registered_email_blacklist(em)
     ```
   - Ghi đè ngay email đó vào blacklist để chặn mọi máy khác trong farm bốc lại.

## 3. Khắc phục lỗi Bottom-sheet 7 tài khoản & Bộ đếm acc
- **Hiện tượng**: Khi máy đã có 7 acc, nút "Thêm tài khoản" bị tràn xuống dưới đáy bottom sheet. Script không tìm thấy nút và bộ đếm đếm cả container rỗng (`.../lli`) -> báo sai lỗi `MACHINE_FULL_8_ACCOUNTS`.
- **Giải pháp**:
  - `tap_add_account`: Tự động vuốt màn hình lên (`swipe up`) khi chưa thấy nút "Thêm tài khoản".
  - `_acc_count`: Chỉ đếm các text node username hợp lệ, loại trừ nhãn điều hướng và container rỗng.

## 4. Kỷ luật Yield Cadence khi Coordinator chạy batch dài:
- **Phong cách User**: User chỉ quan tâm KẾT QUẢ CUỐI CÙNG và BẰNG CHỨNG THẬT (Visual MEDIA:, số liệu thực tế), không đọc log/quá trình làm việc chi tiết.
- **Kỷ luật tương tác**:
  - Tuyệt đối KHÔNG im lặng trong bóng tối quá 2-3 phút khi chạy chuỗi tool calls lớn.
  - Phải ngắt lượt (yield text) gửi 1 dòng trạng thái ngắn gọn qua Telegram: "Hệ thống đang chạy ngầm batch..., sẽ báo cáo ngay khi xong".
  - Sau khi batch hoàn tất, tổng hợp báo cáo trực diện: Máy nào xong (kèm ảnh MEDIA:), máy nào lỗi (lý do cụ thể).
