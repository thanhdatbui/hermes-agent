# Bẫy VACUUM Lên SQLite state.db Gây Nghẽn Hermes Gateway (Crash/Write Lock Trap)

## Hiện tượng & Lỗi thực tế
Khi chạy `VACUUM` hoặc script gom trang nén dung lượng (như `vacuum_to_d.py` chạy `VACUUM INTO ...`) trên cơ sở dữ liệu `state.db` của Hermes (~13.5 GB):
- Lệnh `VACUUM` chiếm **Exclusive Write Lock** trên file `state.db` kéo dài hàng trăm giây (thực tế chạy mất ~683s, hơn 11 phút).
- Trong lúc đó, Hermes Gateway vẫn đang chạy live và liên tục nhận tin nhắn từ người dùng, cố gắng ghi session mới vào `state.db`.
- Khi không lấy được write lock trong thời gian chờ (timeout SQLite), Gateway bị nghẽn và bắn ra thông báo:
  > `"No reply: the turn was stopped because session storage could not be written... This is often a full disk"`
- Người dùng thấy bot bị đứng hình, sập phiên và nghi ngờ đĩa C bị đầy dù kiểm tra ổ C vẫn còn 18–20 GB trống.

## Phân tích nguyên nhân kỹ thuật

### 1. Tại sao ổ C còn 18 GB mà SQLite/Hermes báo "database or disk is full"?
1. **Cơ chế VACUUM chuẩn của SQLite**: Yêu cầu tạo một bản sao cơ sở dữ liệu mới hoàn chỉnh cộng thêm rollback journal / WAL pages tạm trên cùng ổ đĩa C trước khi thay thế. File `state.db` gốc 13.5 GB đòi hỏi tối thiểu **1.5x đến 2x** dung lượng file (tức ~22 - 27 GB trống trên C).
2. Khi ổ C chỉ còn 18.7 GB (< 27 GB), SQLite chạm trần không thể cấp phát thêm trang đĩa tạm và ném ra lỗi mã chuẩn `SQLITE_FULL` (`database or disk is full`).

### 2. Tại sao `VACUUM INTO` sang ổ D vẫn làm sập Gateway?
- `VACUUM INTO 'D:/Taadaa/hermes_state_compact.db'` giải quyết được vấn đề thiếu chỗ trên ổ C, **nhưng nó vẫn giữ Exclusive Write Lock trên `state.db` trong suốt thời gian copy và nén**.
- Với DB 13 GB, tiến trình đọc và gom trang kéo dài >10 phút khiến Gateway bị đóng băng toàn bộ khả năng lưu trữ tin nhắn.

## Quy tắc cấm & Biện pháp an toàn tuyệt đối (Production Invariant)

1. **CẤM TUYỆT ĐỐI chạy VACUUM khi Hermes Gateway đang live**:
   - Không chạy `hermes sessions optimize` khi Gateway đang chạy.
   - Không viết script Python chạy `VACUUM` hoặc `VACUUM INTO` trên `state.db` khi các tiến trình Gateway (`hermes gateway`) chưa được dừng hoàn toàn.
2. **Quy trình dọn dẹp dung lượng an toàn (Online Pruning)**:
   - Dùng `hermes sessions prune --older-than <Nd> --include-archived --yes`.
   - Lệnh prune chỉ xóa hàng (DELETE messages/sessions), chỉ giữ write lock trong thời gian rất ngắn cho từng batch transaction, hoàn toàn an toàn khi Gateway đang online.
   - Các page được giải phóng sẽ trở thành **freelist pages**, SQLite sẽ tự động tái sử dụng cho các tin nhắn mới mà không cần shrink file vật lý.
3. **Quy trình Compact Offline (Nếu bắt buộc phải thu nhỏ file vật lý)**:
   - B1: Tắt hoàn toàn tất cả các tiến trình Gateway (`taskkill /F /IM python.exe` hoặc script stop gateway).
   - B2: Chạy VACUUM hoặc copy file đã compact (`hermes_state_compact.db`) đè lên `state.db`.
   - B3: Khởi động lại Gateway.
