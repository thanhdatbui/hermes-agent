# Quy Tắc & Kinh Nghiệm Đăng Ký TikTok Farm (Cập nhật 23/08/2026)

## 1. QUY TẮC ĐẶT TÊN HIỂN THỊ (DISPLAY NAME / BIỆT DANH) — BẮT BUỘC
- **Luôn đặt tên tiếng Việt:** Khi gặp màn hình đặt Tên / Tạo biệt danh sau khi đăng ký (hoặc cập nhật profile), BẮT BUỘC dùng tên tiếng Việt chuẩn (viết hoa chữ cái đầu, có nghĩa như: An, Hà, Linh, Minh, Vy, Trang, Tuấn, Dũng, Kiều Lâm, v.v.).
- Tuyệt đối không đặt tên tiếng Anh thô hay chuỗi ngẫu nhiên không có nghĩa.

## 2. QUY TẮC KHO MAIL `gmail_clean_v2.xlsx` & TRACKING
- `gmail_clean_v2.xlsx` là **KHO MAIL LIVE**, không tự ý xóa mail chỉ vì đã reg xong.
- Khi chạy check-live / dọn mail die:
  - Nếu mail die và **CHƯA có ID TikTok** trong tracking `taikhoan_dat_v2_updated .xlsx` ➔ **ĐƯỢC XÓA** khỏi `gmail_clean_v2.xlsx`.
  - Nếu mail **ĐÃ có ID TikTok** trong tracking ➔ **CẤM XÓA** khỏi `gmail_clean_v2.xlsx` (để giữ đối chiếu và phục vụ nuôi/reconcile).
- **Cột Mật khẩu:** 
  - TikTok flow hiện nay nhiều acc qua OTP là vào thẳng profile (không bắt tạo pass hoặc có nút Bỏ qua) ➔ Cột `PASS` TikTok để trống `None`.
  - Cột `PASS MAIL` (cột 7/G) BẮT BUỘC luôn giữ đầy đủ mật khẩu email gốc.

## 3. KỸ THUẬT & TRÁNH BẪY LỖI ĐÃ KIỂM NGHIỆM
1. **Lọc Package XML (`com.ss.android.ugc.trill`):**
   - Luôn lọc node theo package TikTok khi kiểm tra text/UI XML để tránh parser nhận nhầm notification từ Android System UI (`com.android.systemui` như thông báo Google Play, SIM, VPN).
2. **Xử lý One-Tap / Fast Login ("Tiếp tục với tên..."):**
   - Khi gặp màn hình gợi ý đăng nhập nhanh nick cũ trên máy, luôn tap *"Sử dụng tài khoản khác"* ➔ *"Tiếp tục với email/tên người dùng"* để mở form nhập mail reg mới.
3. **Phân biệt Mail đã reg vs Chưa reg:**
   - Nếu nghi ngờ email đã tồn tại hay chưa, test qua tính năng "Quên mật khẩu / Đặt lại bằng email"; nếu hiện *"Địa chỉ email chưa được đăng ký"* ➔ mail đó 100% chưa từng reg TikTok.
4. **Preflight Concurrency Gate:**
   - Regex nhận diện tiến trình con của `social_reg_v1.py` phải match cả 2 dạng: `social_reg_v1.py <stt>` và `social_reg_v1.py <serial> <stt>` để tránh các tiến trình con chặn chéo nhau báo lỗi `TRACKING_WRITER_UNKNOWN`.
