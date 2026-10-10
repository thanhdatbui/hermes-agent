# Kỷ Luật Độc Lập Credential Giữa Các Dịch Vụ: Hotmail vs ChatGPT vs TikTok

## 1. Bản chất sự cố
Khi tiến hành khôi phục hoặc cập nhật thông tin xác thực (`PASS MAIL`) cho các tài khoản Hotmail (qua GPM, tool đổi pass hoặc tra soát đơn hàng sàn BoxTaiKhoan), Coordinator đã tự ý đồng bộ mật khẩu mới của Hotmail sang cột `PASS CHATGPT` trong Master Excel (`taikhoan_dat_v2_updated .xlsx`) và supervisor state JSON với suy luận sai lầm: "hai cột trước đó mang giá trị giống nhau thì khi đổi một bên sẽ đổi luôn bên kia".

## 2. Invariant Cấm Kỵ Tuyệt Đối
- **Độc lập dịch vụ:** Hotmail, ChatGPT, và TikTok là 3 hệ thống/dịch vụ độc lập hoàn toàn. Mỗi dịch vụ có tài khoản và mật khẩu riêng.
- **CẤM TỰ TIỆN SUY DIỄN:** Dù trong quá khứ 2 cột có cùng mang một giá trị thì khi cập nhật một cột mục tiêu, TUYỆT ĐỐI CẤM tự ý ghi đè hay đồng bộ sang cột khác.
- **Phân định rõ ràng các cột trên Master Excel (`taikhoan_dat_v2_updated .xlsx`):**
  * **Cột 4 (`PASS`):** Mật khẩu tài khoản TikTok.
  * **Cột 7 (`PASS MAIL`):** Mật khẩu hòm thư Hotmail/Gmail.
  * **Cột 12 (`PASS CHATGPT`):** Mật khẩu tài khoản ChatGPT.

## 3. Quy tắc cập nhật an toàn
1. Khi có task về Hotmail (khôi phục pass, đổi pass, tra soát đơn): **CHỈ ĐƯỢC PHÉP CHẠM VÀO CỘT 7 (`PASS MAIL`)**.
2. Nghiêm cấm mọi hành vi gán `ws.cell(row=r, column=12).value = new_pass` hoặc `chatgpt_password = mail_password` trừ khi có lệnh bằng chữ rõ ràng từ User yêu cầu đổi/cập nhật mật khẩu ChatGPT.
3. Khi cập nhật supervisor state (`batch_gpm_5profiles_supervisor_state.json`), trường `mail_password` và `chatgpt_password` phải được nạp độc lập từ đúng cột tương ứng của Master Excel.
