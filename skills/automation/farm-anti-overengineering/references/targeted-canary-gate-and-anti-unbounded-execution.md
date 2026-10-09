# TARGETED-CANARY-GATE & Kỷ luật Kiểm chứng Máy thật Bounded (< 60s)

## 1. Bối cảnh & Bài học xương máu (Sự cố Canary chụp ảnh non 14/09/2026)
- **Triệu chứng**: Sau khi sửa selector mở tab quan hệ (`_open_following_tab`), Coordinator dispatch worker chạy canary máy thật trên M10.
- **Sai lầm chết người**:
  - Worker gọi lệnh full pipeline: `python -m follow_runner.run_follow --machine 10 --account-row-index 2 --mode 2`.
  - Lệnh này khởi chạy toàn bộ chu trình nuôi tài khoản: budget mặc định 15–18 follows, xem video lướt feed, random delay người dùng.
  - Hậu quả: Quá trình chạy ngốn hơn 10 phút, chạm trần timeout 360s của tool. Worker cạn iterations, vội vàng chụp màn hình lúc TikTok mới chỉ kịp mở ô tìm kiếm (`Search landing`, chưa vào profile anchor).
  - User chấn chỉnh gay gắt: *"Hình m gửi là trang tìm kiếm nick mà... Đm lần sau chạy canary thì chạy nhắm đúng cái hàm vừa sửa thôi. Lưu rule này lại..."*

## 2. Quy tắc Invariant: TARGETED-CANARY-GATE

### Điều cấm tuyệt đối (Anti-Unbounded Execution)
1. **CẤM TUYỆT ĐỐI chạy full session / pipeline nuôi acc khi làm Canary**:
   - Khi kiểm chứng một bản vá cục bộ (sửa selector, sửa hook, đổi regex, đóng popup), CẤM chạy `run_session` với budget mặc định 15–18 follows.
   - Việc chạy full session gây timeout tool, cạn kiệt budget lượt gọi, lãng phí thời gian và chụp ảnh non sai hiện trường.

### Tiêu chuẩn Canary chuẩn (< 60 giây)
1. **Entrypoint phải nhắm đúng hàm vừa sửa**:
   - Sử dụng các cờ targeted canary chuyên biệt (ví dụ `--canary-hook <tên_hàm>`, `--canary-target <uid>`).
   - Budget cưỡng chế = 1, thời gian thực thi < 60s.
   - Không chạy các bước đệm thừa (không lướt 15 video, không chờ delay ngẫu nhiên).
2. **Nghiệm thu ảnh tại đúng đích (Media Evidence Gate)**:
   - Ảnh chụp screencap nghiệm thu BẮT BUỘC chụp tại khoảnh khắc hàm vừa hoàn thành nhiệm vụ (ví dụ: danh sách Following đã render đầy đủ, hoặc popup đã được đóng thành công).
   - CẤM chụp ảnh khi thiết bị còn ở màn hình tìm kiếm, màn hình Home, hoặc đang chuyển cảnh dở dang.
3. **Teardown an toàn ngay sau Canary**:
   - BẮT BUỘC force-stop app mục tiêu, nhấn phím HOME (keyevent 3) và tắt màn hình (keyevent 26) để bảo vệ thiết bị farm.

## 3. Chốt chặn Farm Alert diện rộng (> 10 máy lỗi)
- Nếu bất kỳ khâu nào (Feed, Follow hook, Upload hook) có **> 10 máy** gặp sự cố trong một phiên:
- Watchdog BẮT BUỘC gửi thông báo đỏ `🚨 [FARM ALERT] PHÁT HIỆN LỖI DIỆN RỘNG (>10 MÁY)` trực tiếp về Telegram nhóm Farm Alert (`-5373649734`) kèm bóc tách mã lỗi chi tiết.
