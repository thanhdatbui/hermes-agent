# Chẩn đoán lỗi "Chưa render/thiếu video" (video_not_rendered) khi folder đã có hàng chục video

## Hiện tượng (Symptom)
- Watchdog (`feed_session_watchdog.py`) hoặc Upload runner báo:
  `skipped: video_not_rendered` (hoặc `Chưa render/thiếu video (N)`).
- Kiểm tra thư mục đích `D:\TIKTOK-videonuoinick\<Folder Video>`: Đã có đầy đủ từ 30-45 video MP4, không hề bị rỗng hay chưa render.

## Nguyên nhân gốc rễ (Root Cause)
1. **Quy tắc tính số thứ tự cứng (Hardcoded Sequential Matching):**
   - Trong `multi_machine_feed_session.py`:
     ```python
     next_video = machine_row.get("posted_count", 0) + 1
     video_file = media_root / folder_video / f"{next_video}.mp4"
     ```
   - Trong `run_post.py`:
     ```python
     video_number = video_number or next_video_number(row) # posted_count + 1
     video_path = resolve_video_path(..., folder_video, video_number)
     ```
2. **Khoảng trống dãy số (Gap numbering):**
   - Nếu tài khoản có `Video Đã Đăng = 0` nhưng folder MP4 chỉ có `2.mp4, 3.mp4, ...` (thiếu `1.mp4`).
   - Hoặc tài khoản có `Video Đã Đăng = 1` nhưng folder MP4 chỉ có `1.mp4, 3.mp4, ...` (thiếu `2.mp4`).
   - Runner đòi đúng `(posted_count + 1).mp4`, gặp gap numbering sẽ lập tức skip với lý do `video_not_rendered` thay vì bốc video có sẵn tiếp theo.

## Cách chẩn đoán nhanh O(1)
Chạy script kiểm tra gap numbering:
```python
import os
from pathlib import Path
p = Path(r"D:\TIKTOK-videonuoinick\<folder_id>")
mp4s = sorted([int(Path(f).stem) for f in os.listdir(p) if f.endswith('.mp4') and Path(f).stem.isdigit()])
expected = posted_count + 1
print(f"Expected: {expected}.mp4 | Available: {mp4s[:10]}")
```

## Giải pháp xử lý
1. **Khắc phục nóng (Workaround tức thời):**
   - Tạo symlink / copy 1 video có sẵn trong folder thành `{expected}.mp4`.
2. **Khắc phục cấu trúc (Structural Fix):**
   - Cải tiến resolver: Khi `(posted_count + 1).mp4` không tồn tại, kiểm tra danh sách file MP4 đã sort trong folder và lấy file nhỏ nhất chưa đăng thay vì hardcode crash/skip.
