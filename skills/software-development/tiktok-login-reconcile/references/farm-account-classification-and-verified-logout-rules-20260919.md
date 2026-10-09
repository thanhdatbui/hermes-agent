# Quy Trình Đối Soát Tài Khoản Farm & Bẫy Logout/Phân Loại Nick Rác vs Ký Sinh (2026-09-19)

## 1. Định Nghĩa & Quy Tắc Phân Loại Tài Khoản Tuyệt Đối (User Directive)
- **TẤT CẢ nick xuất hiện trên thiết bị farm đều là tài sản của farm.** Không có khái niệm "nick rác vu vơ ngoài luồng đem vứt bỏ".
- Phân loại rõ ràng 2 nhóm:
  1. **Nick Ký Sinh (Parasite Accounts)**: Là nick chính chủ của máy khác trong farm (ví dụ nick của M16 đi lạc sang M40, nick của M26 đi lạc sang M42).
     - **Điều kiện xử lý**: CHỈ ĐƯỢC PHÉP ĐĂNG XUẤT (logout) khi đã xác minh rõ ràng nick này đã tồn tại và được quản lý trên máy chủ gốc của nó.
  2. **Nick Reg Chưa Ghi Info / Uncommitted Reg**: Là nick do chính máy đó (hoặc farm) vừa đăng ký thành công qua mail được cấp, nhưng tiến trình reg bị văng/timeout ở bước cuối nên chưa kịp ghi thông tin vào Excel.
     - **Điều kiện xử lý**: TUYỆT ĐỐI CẤM LOGOUT / XÓA. BẮT BUỘC phải tra cứu log reg và kho mail (`gmail_clean_v2.xlsx`) để **backfill** ngay lập tức vào đúng slot trống của máy đó trên cả Master Excel (`taikhoan_dat_v2_updated .xlsx`) và Runtime Safe (`taikhoan_run_safe.xlsx`).

---

## 2. Bẫy Tử Thần: Báo Cáo Ảo / Script Logout Tự Động Fail Thầm Lặng
- **Triệu chứng**: Script chạy qua các bước Settings -> Logout, ghi nhận `DONE` vào state JSON, chụp ảnh màn hình báo cáo hoàn tất. Nhưng thực tế khi đối soát lại, nick ký sinh VẪN NẰM NGUYÊN trên app, thiết bị vẫn bị trần 8 nick (`MACHINE_FULL_8_ACCOUNTS`).
- **Nguyên nhân cốt lõi**:
  1. Trang Settings của TikTok Android phiên bản mới rất dài, lệnh swipe hardcode không cuộn tới được nút *"Đăng xuất"*.
  2. Popup xác nhận đăng xuất (`"Bạn có chắc chắn muốn đăng xuất không?"`) hiển thị dạng modal sheet mới (`fdu`, `button1`), các lệnh tap tọa độ cũ bị trượt.
  3. Script không kiểm tra lại kết quả thực tế (Không có verification gate).

---

## 3. Quy Chuẩn Nghiệm Thu 2 Lớp (Two-Layer Verification Gate)
Bất kỳ tác vụ logout nick ký sinh nào BẮT BUỘC phải tuân thủ:
1. **Lớp 1 - Dump UI XML Kiểm Tra Hậu Hành Động**:
   - Sau khi bấm xác nhận đăng xuất, mở lại Switcher và dump XML.
   - Quét tìm `content-desc` hoặc `text` của username vừa logout:
     - Nếu username VẪN CÒN: Đánh dấu `FAILED_LOGOUT_STILL_PRESENT`, dừng ngay lập tức, không được ghi `DONE`.
2. **Lớp 2 - Nghiệm Thu Bằng Chứng Ảnh Thật (OCR Verified)**:
   - Chụp screencap Switcher thật.
   - Dùng OCR đọc nội dung ảnh:
     - Xác nhận số lượng tài khoản giảm về $\le 7$.
     - Xác nhận nút **"Thêm tài khoản"** (Add account) đã xuất hiện trở lại trên màn hình.
