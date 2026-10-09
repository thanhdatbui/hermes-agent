# Hướng Dẫn Điều Tra & Quét Lỗ Hổng Chuỗi Video (Render Sequence Gaps Triage)

## 1. Bản chất sự cố
Khi ca nuôi acc chạy tới phiên đăng video (upload hook trong feed runner hoặc batch upload):
- Script upload tính toán video tiếp theo theo công thức bất biến:
  `expected_video = D:\TIKTOK-videonuoinick\<folder_id>\<Video_Đã_Đăng + 1>.mp4`
- Nếu file này không tồn tại, trạng thái `skipped` sẽ được ghi nhận với reason `video_not_rendered`.
- Điều này xảy ra ngay cả khi thư mục có rất nhiều video số cao hơn (ví dụ: folder 405 có 46 video từ `12.mp4` đến `83.mp4` nhưng lại thiếu `1.mp4`).

## 2. Quy trình điều tra O(1) khi nhận cảnh báo "Chưa render/thiếu video"
1. **Trích xuất thông tin máy và folder bị skip**:
   - Đọc `upload_result.json` trong thư mục run tương ứng:
     `D:\Taadaa\runtime\kibe\live\<date>\<run-name>\machines\machine_<N>\<run-name>\upload_result.json`
   - Xác định rõ: `machine`, `row`, `expected_video`, và `workbook`.
2. **Kiểm tra trạng thái file hiện tại trên đĩa**:
   - Kiểm tra `os.path.exists(expected_video)`.
   - So sánh thời gian tạo/sửa file (`ctime`, `mtime`) với thời điểm runner chạy để biết file đã được fix sau đó hay chưa.
3. **Phân tích nguyên nhân đứt gãy chuỗi số**:
   - Liệt kê toàn bộ file `.mp4` trong `D:\TIKTOK-videonuoinick\<folder_id>`.
   - Kiểm tra xem folder bắt đầu từ số mấy và bị đứt ở số nào.

## 3. Kỹ thuật Quét Cảnh Báo Sớm (Upcoming Gaps Scan)
Để không bị động ở các ca kế tiếp, thay vì chỉ kiểm tra đúng 1 video kế tiếp (`posted + 1`), quét trước một cửa sổ 3-5 video tiếp theo:
```python
for v in range(posted_count + 1, posted_count + 6):
    if v not in existing_numbers_in_folder:
        # Cảnh báo: Folder này sắp thiếu video ở lượt v
```

## 4. Nguyên tắc khắc phục
- **Tuyệt đối không sửa runner bỏ qua số video**: Việc nhảy cóc số thứ tự làm sai lệch đối soát kế toán giữa `Video Đã Đăng` và kho video trên đĩa.
- **Khắc phục ở tầng dữ liệu**: Render bù hoặc bổ sung file vào đúng vị trí số khuyết trong folder `D:\TIKTOK-videonuoinick\<folder_id>`.
