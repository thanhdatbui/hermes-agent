# Chẩn đoán lỗi Treo Hệ Thống do Tràn Ổ Đĩa (Disk Full 100%)

## Bối cảnh sự cố (2026-09-24 Incident)
- **Hiện tượng**: User nhắn tin trên Telegram không có phản hồi, OmniRoute dashboard hoàn toàn trống trơn 0 request suốt 6–10 phút dù có 10–18 session đang chạy song song.
- **Dấu hiệu sai lệch**: Dễ bị chẩn đoán nhầm thành "Telegram rớt mạng", "OmniRoute bị nghẽn", hoặc "LLM bị đơ".
- **Log báo lỗi thật sự** (`C:\Users\Kibe\AppData\Local\hermes\logs\gateway.log`):
  ```text
  WARNING gateway.channel_directory: Channel directory: failed to write: [Errno 28] No space left on device
  ERROR gateway.run: kanban dispatcher: tick failed on board default (No space left on device)
  ```

## Bản chất kỹ thuật
Khi ổ C: cạn kiệt dung lượng (< 200MB):
1. Hệ điều hành Windows rơi vào tình trạng I/O lock.
2. Mọi syscall đồng bộ hoặc bất đồng bộ gọi `open('w')`, `write()`, `db.commit()` của SQLite (`state.db`, `storage.sqlite`) bị treo cứng ở tầng OS Kernel.
3. Tiến trình Hermes Gateway bị đóng băng ngay trước khi kịp mở kết nối HTTP gửi request sang OmniRoute $\rightarrow$ OmniRoute nhận được 0 request!

## Thủ phạm điển hình
Thư mục `C:\Users\<User>\.omniroute\db_backups` chứa hàng trăm bản backup SQLite (`storage.sqlite`, mỗi bản 2.7GB) được sinh ra sau mỗi lần watchdog khởi động lại mà không được dọn dẹp (tích tụ 140+ GB).

## Quy trình xử lý O(1)
1. **Kiểm tra nhanh dung lượng**:
   ```bash
   df -h
   ```
2. **Dọn sạch các bản backup cũ (chỉ giữ 5 bản mới nhất)**:
   ```powershell
   $files = Get-ChildItem -Path 'C:\Users\Kibe\.omniroute\db_backups' -File | Sort-Object LastWriteTime -Descending
   $files | Select-Object -Skip 5 | Remove-Item -Force
   Get-ChildItem -Path 'C:\Users\Kibe\.omniroute' -Filter '*bak*' | Remove-Item -Force
   ```
3. **Kiểm tra hồi sinh**: Dung lượng ổ C: giải phóng 100–140 GB, Gateway hoạt động bình thường ngay lập tức mà không cần cài đặt lại.
