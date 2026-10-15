# Manual Reboot vs Scheduled Reboot Auto-Resume Mechanics

## 1. BỐI CẢNH & VẤN ĐỀ
- **Scheduled Reboot (Tự động 3 ca 05:20, 11:20, 17:20)**:
  - Chạy qua script điều phối `farm_preflight_daily_reset.py`.
  - Hàm `preserve_in_flight_sessions(lookback_minutes=60)` chủ động quét bảng `gateway_routing` trong SQLite của Hermes.
  - Nếu session có tin nhắn cuối cùng là `user` hoặc `tool` (tác vụ đang dang dở, chưa có câu kết thúc của assistant) $\rightarrow$ ghi nhận `resume_pending = True`.
  - Khi Hermes Gateway boot lại, nó tự động bốc cờ này và inject wake-up turn đánh thức session tiếp tục xử lý.

- **Manual Reboot (User tự bấm Restart Windows, sập nguồn, BSOD)**:
  - Script điều phối `farm_preflight_daily_reset.py` KHÔNG được gọi.
  - Windows shutdown đột ngột mà không kịp gắn cờ `resume_pending`.
  - Kết quả: Khi Gateway khởi động lại, các session đang chạy dở bị "bỏ rơi" trong SQLite, Coordinator không tự thức dậy cho đến khi User phải nhắn tin nhắc ("Resume máy vừa reboot").

## 2. GIẢI PHÁP STARTUP HEURISTIC (CHẤP MỌI LOẠI REBOOT)
Thay vì phụ thuộc vào hook lúc tắt máy (vốn dễ xịt khi tắt nóng/cúp điện), triển khai hook **quét dọn lúc khởi động** (Startup Hook):
1. Đặt một script Python nhỏ chạy trong chuỗi khởi động Windows Startup (`Startup` folder) **ngay trước khi** `Hermes_Gateway.vbs` chạy.
2. Logic kiểm tra trong `storage.sqlite`:
   ```python
   # Quét các session trong vòng 60 phút gần nhất
   # Nếu tin nhắn cuối cùng là 'user' hoặc 'tool' -> bật resume_pending = True
   cutoff = datetime.now() - timedelta(minutes=60)
   # Đánh dấu resume_pending = True và resume_reason = "cold_boot_recovery"
   ```
3. Khi Gateway kết nối Telegram thành công, nó sẽ tự động đánh thức mọi session bị đứt quãng giữa chừng mà không cần user phải gõ lệnh thủ công.
