# Cạm Bẫy Đăng Nhập Trùng Nick Chéo Máy (Cross-Device Account Overlap) & Lệch Đồng Hồ Điều Phối

## 1. Hiện Tượng Nick Trùng Chéo Nhiều Thiết Bị (Cross-Device Collision)
- **Cơ chế phát sinh:**
  - Lịch sử nạp mail/Hotmail trước khi có chốt chặn độc quyền đã phân bổ cùng 1 email cho nhiều máy khác nhau trong kho `gmail_clean_v2.xlsx`.
  - Khi các máy độc lập chạy flow login hoặc reg TikTok, chúng đã đăng nhập chung vào cùng 1 tài khoản TikTok trên nhiều thiết bị thực tế.
  - **Triệu chứng nhận diện:**
    - App TikTok trên máy phụ (ký sinh) chạm trần cứng 8 tài khoản, nút "Thêm tài khoản" (Add account) biến mất hoàn toàn, gây lỗi `RuntimeError: [04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)`.
    - Bảng tính Excel (`taikhoan_dat_v2_updated .xlsx` hoặc `taikhoan_run_safe.xlsx`) hiển thị máy đó còn trống Slot 7 hoặc Slot 8 (`None`), kích hoạt cron reg bù vô ích.
    - Trong UI dump của Switcher xuất hiện các username thuộc quyền sở hữu của máy khác (ví dụ `thleyzilkva` thuộc M37 lại xuất hiện trên M13; `jomegbym8n8` thuộc M51 lại xuất hiện trên M24).

- **Quy trình xử lý an toàn:**
  1. Dùng XML Dump của Account Switcher đối soát ngược với danh sách tài khoản chính thức của từng máy trong `taikhoan_run_safe.xlsx`.
  2. Xác định rõ "máy chính chủ" (được ghi nhận trong Excel) và "máy ký sinh" (bị log nhầm).
  3. BẮT BUỘC chỉ thực hiện **Log out (Đăng xuất)** tài khoản khỏi máy ký sinh, tuyệt đối không bấm xóa tài khoản trên máy chính chủ.
  4. Sau khi đăng xuất, kiểm tra số lượng tài khoản trên máy ký sinh giảm về <= 7 và nút "Thêm tài khoản" xuất hiện trở lại trước khi cho phép reg bù.

---

## 2. Kỷ Luật Đồng Hồ Điều Phối & Khung Giờ Chạy Farm (Strict Clock-Check Invariant)
- **Cảnh giác sai lầm chí mạng (Anti-Insanity):**
  - CẤM TUYỆT ĐỐI Coordinator nhìn vào log cũ của Phiên 1 mà suy diễn rằng "máy vừa chạy xong và hiện đang rảnh rỗi".
  - BẮT BUỘC kiểm tra giờ hiện tại của hệ thống (`date`) trước khi đưa ra bất kỳ nhận định hay quyết định điều phối nào.
- **Bản đồ khung giờ farm cấm xâm phạm (Forbidden Windows):**
  - **12:00 - 13:00:** Ca trưa Phiên 1 (Nuôi feed Row 3/4).
  - **13:00 - 13:50:** Khung giờ nghỉ trưa tĩnh (Dead-window giữa 2 phiên) -> Có thể can thiệp nếu 100% lock đã nhả.
  - **14:00 - 15:00:** Ca trưa Phiên 2 (Nuôi feed + Upload video).
  - **14:00 - 18:00:** Chuỗi cron cuốn chiếu Ca chiều (`post-noon-chain-watchdog`: Reg Gmail -> Add 2FA TikTok `run_batch_live_2fa.py`).
- **Quy tắc bất khả xâm phạm:**
  - Trong khung giờ 14:00 - 18:00, các máy farm liên tục nhận lệnh làm 2FA và nhận mã OTP.
  - CẤM TUYỆT ĐỐI Coordinator dispatch worker, chạy script adb, uiautomator, test hàm hay can thiệp vào điện thoại trong khung giờ 14:00 - 18:00 vì sẽ gây xung đột device-lock, cướp luồng ADB/MobiProxy và phá vỡ tiến trình 2FA của farm.
  - Mọi tác vụ sửa lỗi, logout hay audit sâu phải được dời về khung giờ rảnh hoàn toàn hoặc sau khi chuỗi chiều kết thúc.
