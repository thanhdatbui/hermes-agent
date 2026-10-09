# Media Push Dynamic Timeout & Partial Cleanup

## Context & Symptoms
Trong quy trình đăng video TikTok (`Tiktok-video`), bước `MEDIA_PUSH` đẩy file video/ảnh từ PC lên thiết bị Android qua ADB:
```
[MANUAL_REVIEW] [MEDIA_PUSH_FAILED] MEDIA_PUSH: Push failed: adb command timed out: ('adb.exe', '-s', '<serial>', 'push', '<local_path>', '<remote_path>')
```

## Root Cause
1. **Hardcoded ADB Timeout:**
   Hàm `push_video()` trong `media_manager.py` thường cấu hình timeout cố định (ví dụ `timeout=120`).
2. **File dung lượng lớn trên Farm USB Hub:**
   Tốc độ truyền ADB qua hub chia cổng/cáp dài trên farm thường dao động từ **0.8 MB/s đến 1.5 MB/s**.
   Một video 160 MB cần tối thiểu 107 - 200 giây để hoàn tất truyền tải. Với timeout 120s, lệnh `adb push` chắc chắn bị timeout và bị kill giữa chừng.
3. **Cơ chế retry trong AdbClient:**
   `automation-core.adb.AdbClient` mặc định retry kết nối 3 lần (`connection_retry_attempts = 3`). Khi timeout xảy ra, nó reconnect và chạy lại 3 lần với cùng mức timeout 120s, làm lãng phí 6+ phút và đều thất bại.
4. **Hành vi ném ngoại lệ của AdbClient:**
   Ngay cả khi gọi `_adb.run(..., check=False)`, nếu tiến trình con bị `subprocess.TimeoutExpired`, `AdbClient._execute` vẫn ném `ADBError: adb command timed out` thay vì trả về `AdbResult(ok=False)`.

## Giải Pháp Chuẩn Hóa

### 1. Tính Dynamic Timeout theo dung lượng file
Không dùng timeout cố định. Cần tính toán dựa trên dung lượng thực tế của file:
```python
file_size_mb = local_path.stat().st_size / (1024 * 1024)
# Dự trù tốc độ tối thiểu 0.8 MB/s trên hub tải cao + 60s buffer cho handshake/fsync
min_timeout = int(self.config.get("media_push_min_timeout", 180))
calculated_timeout = int((file_size_mb / 0.8) + 60)
push_timeout = max(min_timeout, calculated_timeout)
```

### 2. Dọn dẹp file dang dở khi thất bại / trước khi retry
Khi `adb push` bị ngắt nửa chừng, file trên `/sdcard/DCIM/...` có thể ở trạng thái hỏng/cắt cụt:
- Phải gọi `self._adb.shell(["rm", "-f", remote_path], timeout=15, check=False)` trước khi retry hoặc khi push thất bại.
- Tránh để MediaStore quét trúng file cụt gây lỗi đen màn hình hoặc lỗi load video trong picker.

### 3. Bắt ngoại lệ ADBError an toàn
Bọc cuộc gọi `self._adb.run(["push", ...], timeout=push_timeout, check=False)` trong khối `try...except ADBError` để ghi log rõ ràng file size, timeout đã dùng và dọn dẹp artifact dở dang.
