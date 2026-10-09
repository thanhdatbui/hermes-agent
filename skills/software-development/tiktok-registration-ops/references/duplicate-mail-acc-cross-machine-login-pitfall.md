# Pitfall: Trùng Mail Hotmail / Gmail Giữa Các Máy Gây Ra Hiện Tượng Đăng Nhập Nhầm Acc Lạ

## 1. Hiện tượng thực tế (Case study 2026-09-14 Máy 19 vs Máy 40)
- Khi chạy script kiểm tra hoặc reg bù tài khoản (`ensure_row_accounts.py`), máy báo thiếu acc ở Row N (ví dụ Máy 19 trống Row 6).
- Tuy nhiên khi runner khởi động vào bước `[04_add_account]`, script báo lỗi:
  `RuntimeError: [04_add_account] Không tìm thấy: ('Thêm tài khoản', 'Add account', ...)`
- Kiểm tra danh sách tài khoản thực tế trong app TikTok trên máy thì thấy đã có đủ **8/8 tài khoản** (chạm kịch trần cho phép của app TikTok).
- Trong 8 tài khoản này, phát hiện 1 nick **lạ** (ví dụ `gabruync3o9`) không nằm trong danh sách mapping 8 nick của máy đó trong workbook `taikhoan_dat_v2_updated .xlsx`, mà thuộc sở hữu của máy khác (Máy 40).

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Trùng email trong kho nguồn cấp (`gmail_clean_v2.xlsx`):**
   - Khi nạp hoặc mua tài khoản (Hotmail/Gmail), có trường hợp cùng 1 địa chỉ email được gán trùng cho 2 STT máy khác nhau trong kho nguồn (ví dụ STT 19 và STT 40 cùng mang email `gabrundozarache@hotmail.com`).
2. **Cơ chế Fallback từ Register sang Login của TikTok Runner:**
   - Khi Máy 40 chạy reg trước: Email được đăng ký thành công thành nick TikTok `gabruync3o9`.
   - Khi Máy 19 chạy reg sau: Runner gõ email vào form đăng ký. Vì email này **vừa mới được reg ở máy 40**, TikTok phát hiện email đã tồn tại và tự động chuyển màn hình sang **Đăng nhập (OTP / Xác minh Email)**.
   - Script reg của farm (như `social_reg_v1.py`) được thiết kế linh hoạt tự động fetch OTP/Graph API để hoàn tất -> **Vô tình ĐĂNG NHẬP nick của Máy 40 vào Máy 19**.
3. **Ẩn nút Thêm tài khoản khi đủ 8 nick:**
   - App TikTok phiên bản Android có giới hạn tối đa 8 tài khoản đăng nhập đồng thời trên 1 app. Khi đã đủ 8 nick, nút "Thêm tài khoản" ở dưới sheet dropdown sẽ bị ẩn hoàn toàn.
   - Điều này làm hỏng flow reg bù của các phiên sau vì máy không thể mở thêm form nhập tài khoản mới.

## 3. Quy trình chẩn đoán & Khắc phục chuẩn
1. **Kiểm tra hiện trường UI & Danh sách nick trong app:**
   - Dump UI XML hoặc chụp screencap màn hình account switcher:
     Kiểm tra các node `<node desc="..." resource-id="com.ss.android.ugc.trill:id/lpw">` xem app đang có bao nhiêu nick và gồm những nick nào.
2. **Đối chiếu Workbook:**
   - Lấy danh sách nick từ UI đối chiếu với `taikhoan_dat_v2_updated .xlsx` / `taikhoan_run_safe.xlsx` của STT máy đó.
   - Nếu phát hiện nick lạ không thuộc máy: Tìm kiếm toàn bộ workbook xem nick lạ thuộc STT máy nào.
3. **Đăng xuất (Log out) nick lạc để giải phóng slot:**
   - Dùng script login/switcher hoặc thao tác chuẩn chuyển sang nick lạ -> vào Cài đặt và quyền riêng tư -> Đăng xuất nick lạ ra khỏi máy hiện tại.
   - Tuyệt đối KHÔNG xóa dữ liệu app (`pm clear`) vì sẽ làm mất 7 nick hợp lệ còn lại đang hoạt động tốt.
4. **Kiểm tra và khử trùng kho mail:**
   - Quét file `gmail_clean_v2.xlsx` xem có email nào bị trùng lặp giữa các máy để loại bỏ, tránh việc runner sau này lặp lại lỗi đăng nhập nhầm.
