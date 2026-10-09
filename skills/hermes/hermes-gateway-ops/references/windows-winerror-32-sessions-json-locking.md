# Windows [WinError 32] sessions.json Locking Collision

## Triệu chứng
Gateway trên Windows ném ngoại lệ PermissionError:
```text
Sorry, I encountered an error (PermissionError). [WinError 32] The process cannot access the file because it is being used by another process: 'C:\Users\<user>\AppData\Local\hermes\sessions\.sessions_xxx.tmp' -> 'C:\Users\<user>\AppData\Local\hermes\sessions\sessions.json'
Try again or use /reset to start a fresh session.
```

## Nguyên nhân gốc rễ
1. `sessions.json` chỉ là file **legacy mirror** định tuyến từ các phiên bản Hermes cũ. Nguồn dữ liệu chính thức và duy nhất của toàn bộ chat surfaces hiện tại là SQLite `state.db` (chạy chế độ đa luồng WAL).
2. Khi có tin nhắn đến trên messaging platform (Telegram/Discord/...), gateway thực hiện `_save_sessions_json(data)` bằng cách tạo file tạm `.sessions_xxx.tmp` và gọi `atomic_replace` đè lên `sessions.json`.
3. Trên Windows NTFS, nếu file `sessions.json` đang được một tiến trình khác (antivirus, Windows Search indexer, hoặc thread đọc đồng thời) giữ handle, hàm `os.replace` sẽ bị từ chối với mã lỗi hệ thống Windows `ERROR_SHARING_VIOLATION` (`[WinError 32]`).

## Cách khắc phục triệt để

### 1. Tắt cơ chế ghi mirror legacy trong config (Khuyên dùng - 100% hiệu quả)
Chạy lệnh CLI chính thức của Hermes:
```bash
hermes config set gateway.write_sessions_json false
```
Lệnh này thêm cấu hình vào `config.yaml`:
```yaml
gateway:
  write_sessions_json: false
```
Khi flag này là `false`, gateway ngừng hoàn toàn việc ghi `sessions.json` sau mỗi lượt trao đổi, triệt tiêu 100% rủi ro xung đột khóa file. Toàn bộ session state vẫn được lưu nguyên vẹn trong `state.db`.

### 2. Dọn dẹp file tạm bị kẹt
Xóa các file tạm `.sessions_*.tmp` bị sót lại sau sự cố:
```bash
rm -f ~/AppData/Local/hermes/sessions/.sessions_*.tmp
```
