# TikTok 46.x Account Switcher Latency & Recovery Guide

## Hiện tượng & Nguyên nhân
- **Mã lỗi:** `manual-needed:account-switcher-not-open: profile screen remained after switch-anchor tap`
- **Cơ chế:** Khi feed session chuyển sang tài khoản mới trong profile preflight, script tap vào anchor tên tài khoản `(540, 522)` (hoặc header sau scroll).
- **Điểm nghẽn:** TikTok 46.x mở Account Switcher dạng Bottom Sheet trượt từ dưới lên, cần 1.0 - 2.0s để hoàn tất render XML cây UI. Việc dump XML quá sớm khi chưa có title "Chuyển đổi tài khoản" dễ kích hoạt nhầm cơ chế ấn `Back` (keyevent 4) làm đóng luôn switcher và báo dừng phiên.

## Bài học chẩn đoán & Khắc phục
1. Tên nick ở giữa màn hình Profile TikTok 46.x khi tap trực tiếp `(540, 522)` vẫn mở được bảng "Chuyển đổi tài khoản" mà không cần scroll nếu trang profile ngắn.
2. Khi gặp lỗi dừng phiên `account-switcher-not-open`, luôn chụp screencap để đối chiếu xem bảng switcher thực tế đã mở hay chưa trước khi kết luận nick chưa đăng nhập.
3. Trong script, tăng delay sau khi tap switch_anchor lên tối thiểu 1.5s - 2.0s và kiểm tra thêm các node tài khoản con / nút "Thêm tài khoản" trước khi gửi Back recovery.
