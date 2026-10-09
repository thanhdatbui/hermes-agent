# Network Cold-Start Postcondition & Switcher Prose Isolation (2026-10-05)

## 1. Bản Chất Sự Cố & Bài Học Điều Phối
- **Hiện tượng:**
  - Alert `[MÁY 7]` dừng tại baseline do màn hình lỗi mạng tạm thời lúc cold-start (`id/dd9`, `ze3`, `message_tv`).
  - Worker subagent sửa dở dang (sửa được handler nhưng chưa hoàn tất test suite), Coordinator vội vàng kết luận `BLOCKED có evidence` khiến user phản ứng gắt gao: *"Khóc xong đéo chịu làm, hở tý là bảo blocked"*.
- **Kỷ luật Proactiveness:**
  - Khi worker hết iteration mà diff đã đi đúng hướng và chỉ còn thiếu vài dòng code/test nhỏ lẻ trong ngân sách O(1): Coordinator BẮT BUỘC dùng quyền **L2 Emergency Surgery** để tự tay hoàn thiện, chạy test và kích hoạt ngay Canary nghiệm thu, cấm ngồi báo cáo than vãn hay hở tý là dừng ở L3 BLOCKED.

## 2. Kỹ Thuật Sửa Lỗi Tự Động
- **Chống Vuốt Mù Trên Giao Diện Mất Mạng:**
  - Màn hình lỗi mạng không thể hồi phục bằng `swipe_recovery`. Bắt buộc loại trừ `NETWORK_RETRY_SCREENS` khỏi điều kiện gọi `_swipe_recovery_on_stuck`.
  - Bật `allow_network_force_stop_recovery = True` để tự động relaunch app sạch nếu tap nút `"Thử lại"` (`dd9`) mà hậu kiểm vẫn dính lỗi mạng.
- **Cách Ly SystemUI Prose Trên Roster 8 Tài Khoản:**
  - Khi thiết bị chứa đủ 8 tài khoản, nút `"Thêm tài khoản"` bị đẩy ra khỏi màn hình (off-screen).
  - XML chứa chuỗi thông báo SystemUI (`"thông báo của dịch vụ google play..."`, `"đang sạc pin..."`) hoặc tên hiển thị có khoảng trắng dễ làm `has_profile_prose` kích hoạt `True` và loại nhầm Switcher thật.
  - Sửa chuẩn: Khi đã có tiêu đề thuộc `_ACCOUNT_SWITCHER_TITLES` (`"Chuyển đổi tài khoản"`) và có danh sách `account_rows`, công nhận ngay đây là Switcher hợp lệ.
