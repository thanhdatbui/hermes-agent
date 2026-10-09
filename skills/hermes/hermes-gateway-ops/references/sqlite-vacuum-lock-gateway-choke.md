# Hermes Gateway: SQLite VACUUM Lock & Disk Full Pitfall

## Triệu chứng & Nguyên nhân
- Khi thực thi lệnh `VACUUM` hoặc `hermes sessions optimize` trên database `state.db` lớn (> 10GB):
  1. SQLite tự động tạo file journal/shadow tạm trên cùng volume ổ đĩa (mặc định là ổ `C:`).
  2. Dung lượng ổ đĩa cần tối thiểu 1.5x đến 2x kích thước DB. Nếu ổ C còn < 20GB cho DB 13GB, SQLite sẽ văng lỗi `SQLITE_FULL` (`database or disk is full`).
  3. Lệnh `VACUUM` chiếm giữ **EXCLUSIVE write lock** trong toàn bộ thời gian chạy (có thể kéo dài 5 - 15 phút).
  4. Trong thời gian này, Gateway Hermes tiếp nhận tin nhắn từ Telegram/Discord không thể ghi vào `state.db` (vượt quá 5s lock timeout), dẫn đến session bị ngắt ngang và báo lỗi: `"No reply: the turn was stopped because session storage could not be written"`.

## Quy tắc vận hành bắt buộc
1. **Tuyệt đối cấm chạy `VACUUM` / `VACUUM INTO` / `sessions optimize` khi Gateway đang live.**
2. **Dọn dẹp an toàn:** Dùng `hermes sessions prune --older-than <N>d` để giải phóng các dòng tin nhắn cũ. Dữ liệu xóa sẽ chuyển vào SQLite `freelist` và được tái sử dụng ngay cho các session mới mà không gây lock kéo dài.
3. **Quy trình compact DB an toàn khi cần thiết:**
   - Dừng toàn bộ Gateway processes (`Stop-Process -Name hermes, python`).
   - Chạy `VACUUM INTO` sang ổ đĩa thứ hai có dung lượng lớn (`D:\`).
   - Swap file đã compact vào `state.db`.
   - Khởi động lại Gateway.
