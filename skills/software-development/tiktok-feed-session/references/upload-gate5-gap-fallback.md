# Upload Gate 5: Video Gap & Auto-Fallback Protocol

## Bối cảnh & Nguyên nhân gốc (Root Cause)
- Khi nick nuôi đạt nhịp đăng (mỗi 48h/ca), hệ thống tính `next_video = posted_count + 1`.
- Thư mục video nuôi nick (`D:\TIKTOK-videonuoinick\<folder_id>\`) đôi khi bị **khuyết số / nhảy cóc số** (ví dụ: `1, 2, 3, 4, 6, 7, 11...` - không có `5.mp4` do render giữ nguyên tên video gốc thay vì liên tục).
- Gate 5 cũ kiểm tra `video_file = media_root / folder_video / f"{next_video}.mp4"`. Nếu không có file `5.mp4`, nó kích hoạt Safe-Skip (`status: skipped, reason: video_not_rendered`).
- Do đây là safe-skip nên hệ thống không báo alert đỏ, dẫn đến tài khoản bị ngưng đăng suốt nhiều ngày/tuần (ví dụ case `@chungan981` Máy 33 ngưng 8 ngày).

## Quy tắc vận hành (User chốt 2026-10-04)
> **"Từ giờ nếu không tìm ra file video thì tự đăng video tiếp theo"**

### 1. Logic Auto-Fallback trong Gate 5 (`multi_machine_feed_session.py`)
Khi `next_video = posted_count + 1` không tồn tại hoặc có kích thước 0 byte:
- Không được skip ngay.
- Tự động quét thư mục `f_dir = media_root / folder_video`.
- Tìm danh sách các file `.mp4` hợp lệ có số nguyên `> posted_count` (hoặc `>= next_video`):
  ```python
  candidates = [
      int(f.stem) for f in f_dir.glob("*.mp4")
      if f.stem.isdigit() and f.stat().st_size > 0 and int(f.stem) >= next_video
  ]
  if candidates:
      next_video = min(candidates)
  ```
- Lấy file có số nhỏ nhất tiếp theo làm `next_video` và truyền `--video-number <next_video>` vào lệnh `scripts.tiktok_workflow`.
- Khi đăng thành công, `UPDATE_WORKBOOK` sẽ cập nhật `Video Đã Đăng` bằng đúng số video thực tế đã đăng (ví dụ `6` thay vì `5`), đảm bảo các lần sau tiếp tục tăng tiến mà không bị lùi lại.
- Chỉ khi toàn bộ thư mục thực sự không còn video nào có số `>= next_video` thì mới ghi nhận skip `video_not_rendered`.

### 2. Cứu cấp hiện trường khi nick bị kẹt video
- Nếu phát hiện nick bị kẹt do thiếu đúng 1 file số tiếp theo (ví dụ thiếu `5.mp4` trong khi có `6.mp4`):
  - Có thể copy file tiếp theo vào số bị thiếu:
    `cp "D:/TIKTOK-videonuoinick/<folder>/6.mp4" "D:/TIKTOK-videonuoinick/<folder>/5.mp4"`
  - Hoặc để Gate 5 auto-fallback tự chọn `6.mp4` và nhảy số.
