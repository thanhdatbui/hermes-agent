# Kỹ thuật Phát hiện Acc Kí sinh & Can thiệp Hiện trường Máy Lỗi

## 1. Cạm bẫy TikTok Switcher: Active Profile Blind Spot
- **Hành vi thực tế của TikTok**: Khi người dùng hoặc script mở bottom-sheet "Chuyển đổi tài khoản" (Switcher), TikTok **CHỈ HIỂN THỊ CÁC TÀI KHOẢN PHỤ KHÁC**, tuyệt đối **KHÔNG** hiển thị tài khoản đang active hiện tại trên màn hình Profile chính.
- **Lỗ hổng False Positive**: Nếu script/watchdog (như `watchdog_idle_parasite_reconcile.py`) chỉ mở Switcher rồi quét XML/OCR tìm username tài khoản kí sinh, khi không thấy nick trong Switcher sẽ ngộ nhận là:
  > *"Nick đã không còn trong Switcher -> Đã logout sạch!"* (`return True`)
  Nhưng thực tế tài khoản kí sinh đó đang là **tài khoản Active trên Profile**!
- **Quy trình kiểm tra & dọn dẹp chuẩn 2 lớp (BẮT BUỘC)**:
  1. **Lớp 1 - Kiểm tra Active Profile**: Đọc username/handle ngay trên màn hình Profile chính (`@username`). Nếu chính là nick kí sinh -> Nick vẫn đang tồn tại trên máy!
  2. **Lớp 2 - Kiểm tra Switcher bottom-sheet**: Mở Switcher, cuộn hết danh sách để đối soát tất cả các tài khoản phụ còn lại.
  3. **Đăng xuất dứt điểm**:
     - Nếu nick kí sinh đang là Active Profile: BẮT BUỘC vào *Menu hồ sơ -> Cài đặt và quyền riêng tư -> Cuộn xuống đáy -> Đăng xuất* trực tiếp tài khoản active đó (hoặc switch sang nick chính chủ trước rồi mới đăng xuất).
     - Sau khi đăng xuất: Phải mở lại Switcher, cuộn xuống đáy xác nhận đã xuất hiện nút "+ Thêm tài khoản" hoặc danh sách chỉ còn các tài khoản chính chủ hợp lệ theo sổ cái.

---

## 2. Chỉ đạo "Giành lock xử lý máy lỗi" (Actionable Recovery)
Khi người dùng yêu cầu "giành lock xử lý máy lỗi":
- **CẤM** chỉ liệt kê danh sách file lock thụ động trong `~/.codex/device-locks`.
- **BẮT BUỘC chủ động**:
  1. Lấy ngay danh sách các máy báo fail/kẹt ở batch vừa chạy (qua log runtime hoặc manifest).
  2. Chiếm quyền điều khiển (lock lease) thiết bị để tránh xung đột với runner nền.
  3. Bật màn hình máy thật (`input keyevent 224`), dùng ADB + WinRT OCR kiểm tra hiện trạng thực tế.
  4. Phân biệt rõ lỗi thực tế vs False Alarm:
     - *False Alarm do popup*: PlayCore split APK / Google Play yêu cầu cập nhật làm mất focus TikTok tạm thời. Cách xử lý: force-stop app bên thứ 3, mở lại TikTok.
     - *False Alarm do video detail overlay*: Máy đang xem chi tiết video nên mất thanh điều hướng dưới đáy (không thấy nút Trang chủ). Cách xử lý: ấn Back hoặc tap Hộp thư trước khi về Profile/Home.
     - *Lỗi thực tế*: Thiếu nick chính chủ, dính nick kí sinh, app bị crash. Cách xử lý: nạp bù tài khoản bằng tool login v1, đăng xuất nick kí sinh.
  5. Chụp ảnh nghiệm thu thị giác (Gate 6 - WinRT OCR) đính kèm `MEDIA:<path_anh>`.
  6. Teardown đúng quy chuẩn: đưa máy về LauncherActivity, tắt màn hình dưỡng pin (`input keyevent 223`).
