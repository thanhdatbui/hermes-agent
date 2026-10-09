# Upload Hook Gate 5: Video Render & Gap Numbering Fallback

## Vị trí & Trách nhiệm
- **File:** `D:\Taadaa\tiktok-luot nuoi acc\python_runner\flows\multi_machine_feed_session.py`
- **Hàm:** `_run_upload_hook`
- **Gate 5:** Kiểm tra sự tồn tại của file video MP4 tiếp theo để chuẩn bị gọi subprocess workflow đăng video.

## Cơ chế xử lý Gap Numbering
Mặc định:
`next_video = machine_row.get("posted_count", 0) + 1`
Khi render video hoặc biên tập có khoảng trống số thứ tự (ví dụ: máy đã đăng 2 video -> `next_video = 3`, nhưng thư mục video bị thiếu số 3, 4 mà có sẵn số 5):
- Nếu chỉ kiểm tra tĩnh `video_file = video_folder / f"{next_video}.mp4"`, upload hook sẽ ngộ nhận video chưa render (`video_not_rendered`) và skip upload toàn bộ các phiên tiếp theo.
- **Fallback logic:**
  1. Kiểm tra `video_file` trực tiếp (`next_video.mp4`). Nếu file tồn tại và dung lượng > 0, dùng luôn.
  2. Nếu không tồn tại / rỗng, duyệt toàn bộ thư mục `video_folder`:
     - Lọc các file có đuôi `.mp4` và `stat().st_size > 0`.
     - Chuyển `stem` sang `int` (bỏ qua các file không phải số như `preview.mp4`).
     - Sắp xếp tăng dần theo số thứ tự.
     - Lọc các candidate có `num >= next_video`.
     - Lấy candidate nhỏ nhất thỏa mãn (`ge_candidates[0]`).
  3. Nếu không có candidate nào `>= next_video` (hoặc tất cả đều `< next_video`), trả về `skipped` với `"reason": "video_not_rendered"`.

## Focused Test
Khi chỉnh sửa upload hook hoặc Gate 5, chạy test focused:
```bash
python -m pytest "D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_upload_hook.py" -k "test_upload_hook_gate5"
```
