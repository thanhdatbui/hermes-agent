# Audit & Chẩn Đoán Lỗi Thiếu Video / Chưa Render (Video Sequence Gaps)

## 1. Bản chất & Nguyên nhân gốc rễ
- Runner khi chạy ca nuôi acc (upload hook) luôn tìm video kế tiếp theo công thức:
  `expected_video = D:\TIKTOK-videonuoinick\<folder_id>\<Video_Đã_Đăng + 1>.mp4`
- Trạng thái `skipped: video_not_rendered` xuất hiện khi file video kế tiếp không tồn tại trong thư mục, dù trong thư mục có thể có rất nhiều video số lớn hơn (ví dụ: có từ `12.mp4` đến `83.mp4` nhưng thiếu `1.mp4` hay `2.mp4`).
- Thường gặp khi:
  1. Render bị gián đoạn I/O hoặc copy thiếu các video số nhỏ đầu chuỗi.
  2. Batch render chạy trước đây không tuần tự tuyệt đối hoặc nhảy số.

## 2. Quy trình kiểm tra & Đối soát nhanh O(1)
Khi user hỏi hoặc watchdog báo `Chưa render/thiếu video (N)`:

1. **Truy vết machine và folder từ run artifact**:
   - Mở folder run tương ứng trong `D:\Taadaa\runtime\kibe\live\<YYYY-MM-DD>\<row-X-HHMMSS>\...`
   - Đọc `upload_result.json` của các máy để xác định chính xác `machine`, `row`, `expected_video`, và `workbook`.
2. **Kiểm tra file thực tế trên đĩa**:
   - Kiểm tra `os.path.exists(expected_video)`. Lưu ý xem file đã được fix/bổ sung sau thời điểm chạy hay chưa (so sánh mtime/ctime với timestamp của log run).
3. **Quét cảnh báo sớm (Upcoming Gaps Scan)**:
   - Thay vì chỉ nhìn vào 1 video kế tiếp (`posted + 1`), quét trước 3-5 video tiếp theo (`range(posted + 1, posted + 6)`) đối soát với danh sách file thực tế trong folder để phát hiện sớm các folder nhảy cóc số (ví dụ: có 1, nhảy cóc lên 4, thiếu 2 và 3).
   - Công thức kiểm tra:
     ```python
     for v in range(posted_count + 1, posted_count + 6):
         if v not in existing_numbers:
             # Cảnh báo gap sắp tới
     ```

## 3. Khắc phục chuẩn
- Tuyệt đối không sửa runner bỏ qua số video (heuristic nhảy cóc gây sai lệch kế toán đối soát).
- Bổ sung file khuyết số thứ tự vào folder `D:\TIKTOK-videonuoinick\<folder_id>` (hoặc render bù đúng số thứ tự còn thiếu).
