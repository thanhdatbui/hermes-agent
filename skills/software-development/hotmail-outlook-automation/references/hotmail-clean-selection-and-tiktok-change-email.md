# Hotmail Clean Selection Invariants & TikTok Change Linked Email

> **Bài học từ chỉ trích của User**: *"Ủa sao lúc change hotmail lại đi bốc các hotmail đã reg r. Chưa hiểu"*.

---

## 1. Cạm bẫy đối soát không toàn diện
- **Căn bệnh**: Chỉ kiểm tra email có trong `taikhoan_dat_v2_updated .xlsx` hay không rồi tự ý coi các email còn lại trong `hotmail_input.txt` hay `latest_bought_70.txt` là "mail sạch".
- **Hậu quả**:
  - Hầu hết các mail trong các tệp tạm trên đã từng được nạp vào các đợt chạy reg TikTok trước đó và đã có nick TikTok liên kết.
  - Khi đem nhập vào màn hình `Thay đổi email` của TikTok trên app điện thoại, TikTok báo lỗi:
    > `com.ss.android.ugc.trill:id/icn | text="Email này đã được sử dụng"`
  - Hoặc mail đó đã được phân bổ cho máy khác trong `gmail_clean_v2.xlsx`, nếu lấy dùng sẽ gây chồng chéo tài nguyên.

---

## 2. Kỷ luật chuẩn hóa khi cần Hotmail thay thế
1. **Mua mới 100% bằng tool canonical**:
   - Chạy lệnh: `python D:/Taadaa/tools/buy_hotmail.py --buy 1 --target-file <path>`
   - Ưu tiên BoxTaiKhoan, tự động fallback sang CloneFBIG (hàng ngàn acc có sẵn, số dư luôn được nạp đầy đủ).
2. **Kiểm tra Graph API inbox trước khi gán**:
   - Query danh sách thư trong hộp thư qua endpoint `https://graph.microsoft.com/v1.0/me/messages`.
   - BẮT BUỘC xác nhận hộp thư chưa từng nhận thư từ TikTok (`là mã gồm 6 chữ số của bạn` hoặc `là mã TikTok của bạn`).
3. **Đồng bộ trạng thái 3 nơi ngay sau khi đổi thành công**:
   - Master Excel (`taikhoan_dat_v2_updated .xlsx`): Cột F (Email) & Cột G (Pass Mail).
   - GPM Supervisor State (`batch_gpm_5profiles_supervisor_state.json`): Cập nhật key `M<n>:<email>`, đổi status `PENDING`, stage `HOTMAIL_LOGIN`.
   - File token cache (`D:/Taadaa/Hotmail/hotmail_input.txt`): Lưu dòng chuỗi token để các tiến trình tự động sau này đọc được OTP.
