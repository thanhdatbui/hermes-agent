# Quy trình khôi phục tài khoản bị văng / mồ côi chiếm slot trần 8 (2026-09-17)

## 1. Bản chất sự cố trần 8 tài khoản & Nick mồ côi (Parasite)
- Switcher của TikTok App giới hạn tối đa đúng **8 tài khoản** đăng nhập đồng thời trên một thiết bị.
- Khi reg dồn hoặc nạp nick mới bù slot vào máy mà không logout nick cũ trên máy thật:
  - Máy thật chạm trần 8 nick. Nút `"Thêm tài khoản"` biến mất.
  - Nick cũ hơn bị đẩy văng khỏi Switcher, nhưng **vẫn lưu cache trong mục 'Chào mừng bạn trở lại' (Fast Login)**.
  - Xuất hiện tình trạng lệch pha nguy hiểm: **Excel ghi nick A, nhưng trên máy thật nick B (mồ côi) lại ngồi chiếm slot**.

## 2. Quy trình xử lý chuẩn Farm Safety (Không mất nick)
1. **Kiểm tra thực tế số nick trên Switcher máy thật**:
   - Dùng ATX hoặc dump XML để đếm chính xác số lượng item `resource-id` của switcher (`["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"]` — lưu ý TikTok build mới thêm `ndk` như trên M27, M37).
   - Kiểm tra xem có nút `"Thêm tài khoản"` hay không (`HAS "Thêm tài khoản"`). Nếu đếm đủ 8 item mà mất nút Thêm tài khoản -> ném lỗi `MACHINE_FULL_8_ACCOUNTS`.
2. **Nếu máy còn slot (< 8 nick)**:
   - Bấm nút `"Thêm tài khoản"`.
   - Kiểm tra danh sách Fast Login: nếu nick cần tìm có trong danh sách, bấm vào để khôi phục session ngay.
   - Nhập OTP từ Outlook/Gmail hoặc TOTP sinh từ secret trong Master DAT để hoàn tất khôi phục.
3. **Nếu máy kẹt đủ 8 nick (chạm trần)**:
   - **Xác định nick mồ côi (parasite)**: So sánh 8 nick trên Switcher thật với 8 nick trong `taikhoan_run_safe.xlsx`. Nick nào có trên máy thật nhưng KHÔNG có trong Excel chính là nick mồ côi chiếm chỗ.
   - **Bảo lưu thông tin**: Đối soát lại backup Master DAT, trích xuất đầy đủ credentials (User, Pass TikTok, Mail, Pass Mail, 2FA) của nick mồ côi trước khi can thiệp.
   - **Đăng xuất đơn lẻ trong Settings**:
     - Chuyển sang nick mồ côi trên Switcher.
     - Vào `Menu hồ sơ (3 gạch)` -> `Cài đặt và quyền riêng tư` -> Cuộn xuống đáy -> Chọn `Đăng xuất` -> Xác nhận popup.
     - TUYỆT ĐỐI KHÔNG dùng `pm clear` hay logout hàng loạt làm mất session các nick khác!
   - **Khôi phục nick chính chủ**: Sau khi logout nick mồ côi, Switcher xuất hiện lại nút `"Thêm tài khoản"` -> Bấm chọn nick chính từ Fast Login -> Đăng nhập thành công -> Switcher đủ 8 nick chuẩn 100% khớp Excel.
   - **Bảo toàn nick mồ côi**: Lưu hồ sơ nick mồ côi vào danh sách chờ hoặc nạp sang các máy đang thực sự còn trống slot (< 8 nick) như M20, M22.
