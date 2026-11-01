# Kỷ Luật Trích Xuất Avatar Không Dính Deadlock & Kiểm Soát Chặt Bảng Proposal Canvas

## 1. Cơ Chế Trích Xuất Frame An Toàn Tuyệt Đối (Zero Deadlock)

- **Cấm Tuyệt Đối:** CẤM gọi `cv2.VideoCapture(...)` trần trụi trong các script chạy terminal foreground hoặc inline code. Trên Windows, Media Foundation / DirectShow sẽ gây deadlock cứng tiến trình khi gặp tranh chấp tài nguyên hoặc codec lạ, dẫn đến việc ngậm terminal suốt 60 phút và nổ Gateway Timeout.
- **Bắt Buộc:** Phải sử dụng hàm an toàn đã được cô lập tiến trình trong `anti_hang_guard.py`:
  ```python
  import sys
  sys.path.insert(0, "D:/Taadaa/tools")
  from anti_hang_guard import safe_extract_video_frame

  # Trích xuất frame an toàn có hard-timeout 10s:
  frame = safe_extract_video_frame(video_path, timestamp_s=2.0, timeout_s=10.0)
  if frame is not None:
      # xử lý crop ảnh
  ```
- **Tầng Thực Thi Subprocess Cưỡng Chế:** Trong `run_safe_command` (`anti_hang_guard.py`), mọi lệnh chứa chuỗi `cv2.VideoCapture` hoặc `VideoCapture` chạy trực tiếp đều bị chặn đứng ngay lập tức (Exit code 1). Khi xảy ra timeout trên Windows, supervisor bắt buộc dùng `taskkill /F /T /PID` để diệt sạch cả cây tiến trình con (triệt tiêu orphan process).

---

## 2. Kỷ Luật Tạo Bảng Proposal Canvas (Chống Nhân Bản 1 Ảnh Thành 4)

- **Cấm Gian Dối Tái Sử Dụng:** Tuyệt đối không được lấy 1 file ảnh có sẵn (như `avatar.jpg`) rồi zoom nhẹ hoặc chỉnh sáng làm 4 lần để đối phó nộp cho xong chuyện.
- **Quy Chuẩn 4 Phương Án Thật:** Bảng Proposal Canvas 4 ô tròn bắt buộc phải đại diện cho **4 khoảnh khắc/góc quay hoàn toàn khác nhau** từ kho video thực tế của kênh.
- **Kiểm Chứng Vision Bắt Buộc:** Sau khi render bảng Proposal Canvas, Coordinator bắt buộc phải gọi `browser_navigate` và `browser_vision` để mắt thật của LLM kiểm tra từng ô tròn. Xác nhận 100% không dính ảnh người lạ, không dính chữ rác/watermark, và đúng nhân vật trước khi phát lệnh `MEDIA:`.

---

## 3. Quy Trình Đồng Bộ Kênh 5-in-1 Cho Máy Remote (Admin Farm >= 200)

Khi chuẩn hóa tài khoản trên máy Admin Remote (như Máy 274):
1. **Đồng bộ Avatar sang Admin PC:** Bắt buộc dùng `python D:/Taadaa/tools/sync_avatar_to_admin.py <local_avatar> <remote_avatar>` để đẩy sang `D:/TIKTOK-videonuoinick-admin/<folder>/avatar.jpg`.
2. **Cắm Marker Khóa Đa Tầng:**
   - Cắm `.manual_avatar_locked` và `.manual_hashtag_locked` trên cả thư mục local và remote.
   - Cập nhật 2 file registry: `D:/Taadaa/data/manual_avatar_protected_folders.json` và `manual_hashtag_protected_folders.json`.
3. **Cập Nhật Excel `Tik5.xlsx`:** Sửa cột Keyword và Hashtag Pool khớp với chủ đề thật, sau đó đồng bộ file Excel sang `D:/OneDrive/TaadaaData/admin/Tik5.xlsx`.
4. **Kích Hoạt Hàng Đợi Thiết Bị:** Set trạng thái `PENDING` trong bảng `avatar_replace_queue` (`tiktok_tracker.db`) để watchdog trên máy tự động đưa avatar lên app TikTok khi vào ca.
