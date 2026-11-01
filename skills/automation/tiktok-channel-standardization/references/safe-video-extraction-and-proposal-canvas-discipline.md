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

## 2. Kỷ Luật Trích Xuất Bố Cục Avatar & Chống Bẫy Micro-Crop Phóng To Vỡ Hạt

- **Bẫy Tự Bịa "Cận Cảnh":** Người dùng không hề yêu cầu dí sát vào lỗ mũi hay mảng lông. Cắt một góc 180x180 px từ ảnh 512x512 rồi phóng to lên 512x512 sẽ biến avatar thành "cục lông bầy hầy", nhòe nát.
- **Kỷ Luật Độ Phân Giải (Floor >= 350px):** Vùng crop phải $\ge 350\times 350$ px và $\ge 70\%$ diện tích khung hình gốc. Nếu không có góc cận cảnh gốc Full HD, **BẮT BUỘC giữ nguyên khung hình toàn thân / bán thân tự nhiên**, bố cục đẹp và sắc nét gấp 1000 lần ảnh zoom vỡ hạt.
- **Trích Xuất Từ Video Thương Hiệu Của Kênh:** Khi kho video gốc hỗn tạp nhiều chủ đề, **BẮT BUỘC** trích frame từ video đang có view / video nhận diện trên profile kênh (ví dụ: video 1 cún múa bụng đeo khăn chuông tím).
- **Quy Chuẩn Bảng So Sánh 2 Options (Gọn Gàng):**
  - Option 1: Ảnh tĩnh nguyên bản bố cục đẹp, sắc nét trên thảm/nền.
  - Option 2: Khoảnh khắc nhận diện đặc trưng trích từ video có view.
  - Cả 2 được bo tròn viền xanh TikTok và soi mắt thật trước khi gửi.

---

## 3. Quy Trình Đồng Bộ Kênh 5-in-1 Cho Máy Remote (Admin Farm >= 200)

Khi chuẩn hóa tài khoản trên máy Admin Remote (như Máy 274):
1. **Đồng bộ Avatar sang Admin PC:** Bắt buộc dùng `python D:/Taadaa/tools/sync_avatar_to_admin.py <local_avatar> <remote_avatar>` để đẩy sang `D:/TIKTOK-videonuoinick-admin/<folder>/avatar.jpg`.
2. **Cắm Marker Khóa Đa Tầng:**
   - Cắm `.manual_avatar_locked` và `.manual_hashtag_locked` trên cả thư mục local và remote.
   - Cập nhật 2 file registry: `D:/Taadaa/data/manual_avatar_protected_folders.json` và `manual_hashtag_protected_folders.json`.
3. **Cập Nhật Excel `Tik5.xlsx`:** Sửa cột Keyword và Hashtag Pool khớp với chủ đề thật, sau đó đồng bộ file Excel sang `D:/OneDrive/TaadaaData/admin/Tik5.xlsx`.
4. **Kích Hoạt Hàng Đợi Thiết Bị:** Set trạng thái `PENDING` trong bảng `avatar_replace_queue` (`tiktok_tracker.db`) để watchdog trên máy tự động đưa avatar lên app TikTok khi vào ca.
