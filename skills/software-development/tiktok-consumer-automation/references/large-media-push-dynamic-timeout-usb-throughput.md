# Large Media Push Dynamic Timeout & USB Throughput on Farm Devices

## 1. Context & Problem
Trên farm Android mật độ cao (30–60 devices kết nối qua nhiều tầng USB hub 2.0/3.0 tới một máy trạm):
- Băng thông thực tế khi `adb push` file media lớn (>100MB) thường dao động trong khoảng **1.5 MB/s – 2.5 MB/s** (đặc biệt khi có nhiều thiết bị đang sync hoặc hoạt động đồng thời trên bus).
- Timeout cố định cũ (ví dụ 120s) thường xuyên gây false-positive `MediaManagerError` hoặc abort giữa chừng khi đẩy video dài/dung lượng cao (150MB–200MB mất 75s–130s).
- Khi timeout xảy ra, file trên thiết bị bị dở dang (partial file), gây lỗi tiếp nối khi TikTok picker hoặc MediaStore quét media hỏng.

## 2. Dynamic Timeout Formula (MediaManager)
Để đảm bảo an toàn cho mọi kích thước file media:
```python
file_size_mb = local_path.stat().st_size / (1024 * 1024) if local_path.exists() else 0
# Đảm bảo timeout tối thiểu 180s, hoặc theo dung lượng file (ước lượng 0.8 MB/s + 60s buffer)
push_timeout = int(max(180, (file_size_mb / 0.8) + 60))
```
- **Hệ số an toàn**: Giả định tốc độ sàn 0.8 MB/s (dưới mức trung bình 2 MB/s của USB farm) cộng 60s overhead tạo buffer lớn, tránh đứt gãy khi bus bị nghẽn tức thời.
- **Min bound**: Tối thiểu 180s cho cả các file nhỏ để đề phòng ADB daemon wake-up latency.
- **Thực tế đo đạc (Máy 63 / ce091609dc2dc92804)**: File 160.4MB truyền mất 82.03s (~2.1 MB/s), nằm hoàn toàn an toàn trong ngưỡng dynamic timeout 260s.

## 3. Best Practices & Cleanup on Failure
- Khi `adb push` gặp lỗi hoặc không xác nhận được file tồn tại sau push, luôn phải thực hiện cleanup fail-safe:
  ```python
  self._adb.shell(["rm", "-f", remote_path], timeout=10, check=False)
  ```
  để tránh để lại file rác/hỏng trong `/sdcard/DCIM/Camera/` làm bẩn MediaStore.
- Luôn kiểm tra dung lượng trống trước khi push (`df /sdcard`) với buffer an toàn tối thiểu 20%.
