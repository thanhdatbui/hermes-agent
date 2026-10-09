# Per-Machine Rolling Chaining vs Farm-Level Static Windows

Cập nhật: 16/09/2026.

## 1. Vấn Đề Thiết Kế Cũ (Farm-Level Static Window & All-Done Block)
Trong các watchdog sau ca (điển hình là Ca 3 Tối):
- **Bị khóa giờ cứng:** Ép khung giờ tĩnh kiểu `21:00 - 23:30` (Up avatar) hoặc `21:30 - 23:45` (Login GPM).
- **Cản trở cuốn chiếu toàn farm:** Script GPM bắt buộc `is_avatar_done(today_str)` trả về `True` (chờ toàn bộ farm hoàn tất avatar hoặc hết giờ fallback). Điều này làm tê liệt khả năng tận dụng thời gian rảnh: các máy xong Phiên 1 sớm (18:45) hoặc các máy vốn đã có avatar sẵn từ trước vẫn phải ngồi chờ đến tận 22:00 mới được login GPM.
- **Lãng phí cửa sổ tài nguyên:** Sau Phiên 2 (20:15), máy rảnh tới 3.5 tiếng trước Ca 4 đêm nhưng bị dồn ứ lại sát giờ đêm mới chạy, dễ chạm trần proxy limit.

## 2. Kiến Trúc Cuốn Chiếu Theo Từng Máy (Per-Machine Rolling Pipeline)
Chuyển đổi hoàn toàn sang mô hình **Event-Driven & Machine-Level Ready**:

```
[Phiên nuôi hoàn tất (P1 ~18:45 hoặc P2 ~20:15)]
                      │
                      ▼
[Máy nhả device-lock vật lý (~/.codex/device-locks)]
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
[Acc CHƯA có Avatar]        [Acc ĐÃ có Avatar]
        │                           │
        ▼                           │
[post-evening-avatar-watchdog]      │
• Up avatar ngay cho máy đó         │
• Xong -> Ghi nhận Avatar OK        │
        │                           │
        └─────────────┬─────────────┘
                      │
                      ▼
[post-evening-gpm-login-watchdog]
• Kiểm tra is_machine_avatar_ready(mid)
• Login GPM & nạp Dual OAuth (ChatGPT-Web & Codex)
• Giải phóng lock máy & sync Group 10
```

## 3. Quy Chuẩn Triển Khai
1. **Cron Trigger thường trực:** Cấu hình polling tần suất cao `*/5 18,19,20,21,22,23 * * *` cho cả Avatar và GPM watchdog, bắt đầu quét ngay từ 18:45 sau Phiên 1.
2. **Loại bỏ chặn giờ cục bộ:** Xóa bỏ hoàn toàn các hàm `is_within_time_window()` chặn sau 21:30; chỉ duy trì chặn an toàn trước Ca 4 đêm (trước 23:45).
3. **Bỏ phụ thuộc all-done:** Trong `post_evening_gpm_login_watchdog.py`, hàm `is_avatar_done()` trả về `True` để nhường quyền kiểm tra cho `is_machine_avatar_ready(mid)`:
   - Đọc trực tiếp trạng thái avatar của nick tương ứng trên các workbook `Tik5..Tik8, Tik3, Tik4`.
   - Nếu nick đã có avatar (`OK`, `present`, `true`) $\rightarrow$ đủ điều kiện login GPM ngay.
   - Nếu nick chưa có avatar $\rightarrow$ nhường cho `post-evening-avatar-watchdog` xử lý trước, watchdog tick tiếp theo sẽ bốc lên khi avatar đã xong.
4. **Dọn dẹp One-Shot Cron:** Các cron tác vụ dọn dẹp hoặc reconcile chạy 1 lần (ví dụ dọn nick ký sinh) sau khi hoàn thành nhiệm vụ BẮT BUỘC gỡ bỏ ngay (`cronjob action='remove'`), không để chạy lặp lại vô ích trong scheduler.
