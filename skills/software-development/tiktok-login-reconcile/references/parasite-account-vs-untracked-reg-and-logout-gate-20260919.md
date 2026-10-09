# Nick Ký Sinh vs Nick Reg Chưa Ghi Info & Quy Trình Logout Nghiệm Thu 2 Lớp (2026-09-19)

## 1. Phân biệt: Nick Ký Sinh vs Nick Reg Chưa Ghi Info (User Correction 2026-09-19)
- **Bối cảnh**: Khi phát hiện nick lạ trong Switcher hoặc máy chạm trần 8 nick (`MACHINE_FULL_8_ACCOUNTS`), CẤM vội kết luận là "nick rác" rồi đem đi logout.
- **Nguyên tắc cốt lõi**:
  - Mọi nick đang nằm trên máy đều là tài sản của farm.
  - **Nick ký sinh**: Là nick ĐÃ ĐƯỢC GHI NHẬN và thuộc quyền sở hữu của máy khác (ví dụ nick của M16 đi lạc sang M40, nick của M26 đi lạc sang M42). CHỈ ĐƯỢC LOGOUT khi xác minh nick đó đã tồn tại an toàn trên máy gốc.
  - **Nick reg chưa ghi info**: Là nick vừa được đăng ký thành công trên chính máy đó (hoặc từ đợt chạy trước bị văng ở bước cuối chưa kịp ghi vào file). BẮT BUỘC **bảo toàn tuyệt đối** và backfill ngay vào slot trống của máy đó trên Master DAT (`taikhoan_dat_v2_updated .xlsx`) và Safe (`taikhoan_run_safe.xlsx`).

---

## 2. Bẫy Tử Thần: Báo Cáo Ảo / Nghiệm Thu Dối Khi Logout Nick Ký Sinh
- **Triệu chứng**: Script chạy logout báo `DONE` nhưng thực tế nick vẫn nằm nguyên trong Switcher, khiến lần chạy reg tiếp theo tiếp tục bị văng `MACHINE_FULL_8_ACCOUNTS`.
- **Root Causes**:
  1. `uiautomator dump` trên Samsung S7 bị chết vĩnh viễn (Exit Code 137 / wedged). Nếu script gọi `subprocess.run(['adb', ...])` thiếu `timeout=15`, tiến trình sẽ treo vô hạn dẫn tới timeout 600s của subagent.
  2. Trang Cài đặt và quyền riêng tư (Settings and privacy) của TikTok trên Samsung S7 rất dài, vuốt thiếu lượt sẽ không thấy nút Đăng xuất.
  3. Popup *"Bạn có chắc chắn muốn đăng xuất không?"* hiển thị modal mới. Tap mù quáng hoặc tap trượt khiến dialog chưa xác nhận, nhưng script vẫn chụp ảnh rồi tự động ghi `DONE`.

---

## 3. Quy Trình Logout Chuẩn & Nghiệm Thu 2 Lớp Bằng OCR/Coordinates

1. **Không phụ thuộc `uiautomator dump`**: Sử dụng `screencap` + Windows native OCR (`do_ocr.ps1`) để định vị phần tử. Mọi lệnh ADB subprocess BẮT BUỘC có `timeout=15`.
2. **Quy trình thao tác chuẩn trên Samsung S7**:
   - Mở app TikTok -> vào tab Hồ sơ (`972, 1857`).
   - Mở Switcher (`540, 140` hoặc tap tên hiển thị).
   - Chuyển sang nick ký sinh cần logout. Chờ 5s.
   - Vào lại Hồ sơ (`972, 1857`) -> Menu 3 gạch (`1005, 150`).
   - Tap **Cài đặt và quyền riêng tư** (thường tại `540, 1250`).
   - Vuốt 5-6 lần xuống đáy trang: `input swipe 540 1600 540 300 250`.
   - Tap nút **Đăng xuất** ở đáy trang (thường tại `300, 1640`).
   - Khi popup xác nhận hiện ra: Tap nút **Đăng xuất** xác nhận (thường tại `540, 1640`). Chờ 5s.
3. **Nghiệm thu 2 lớp bắt buộc (Gate 6)**:
   - Mở lại app -> vào Hồ sơ -> mở Switcher.
   - Chụp ảnh screencap Switcher lưu vào `reports/m{machine_id}_verified_logout.png`.
   - Chạy OCR đối soát: **BẮT BUỘC** nick ký sinh đã biến mất hoàn toàn và nút *"Thêm tài khoản"* (Add account) đã xuất hiện trở lại.
   - Trả về `MEDIA:<path_ảnh>` cho user.
