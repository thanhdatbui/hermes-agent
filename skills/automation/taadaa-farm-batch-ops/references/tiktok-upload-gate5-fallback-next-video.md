# TikTok Upload Gate 5: Khuyết Số Video & Cơ Chế Auto-Fallback Next Video

## 1. Bối cảnh & Hiện tượng (Incident chungan981 - 10/2026)
- **Tài khoản:** `@chungan981` (Máy 33, Slot 5, Tik 5, folder video `261`).
- **Hiện tượng:** Tài khoản đã đăng 4 video liên tiếp (19/09 -> 25/09/2026), sau đó **ngưng đăng hơn 1 tuần** dù máy vẫn chạy feed đều đặn.
- **Root Cause:**
  - Logic cũ của Gate 5 trong `_run_upload_hook` (`multi_machine_feed_session.py`):
    `next_video = posted_count + 1` -> tìm cứng `media_root / folder_video / f"{next_video}.mp4"`.
  - Trong folder `261`, các file clip sau khi render giữ nguyên số hiệu gốc thay vì liên tục:
    `1.mp4, 2.mp4, 3.mp4, 4.mp4, 6.mp4, 7.mp4...` (KHÔNG CÓ `5.mp4`).
  - Preflight Gate kiểm tra thấy thiếu file `5.mp4` nên kích hoạt **Safe-Skip** (`reason: "video_not_rendered"`).
  - Vì đây là safe-skip (không báo lỗi đỏ crash), hệ thống âm thầm bỏ qua tài khoản ở mọi ca tối, khiến nick bị treo vĩnh viễn dù trong kho vẫn còn 42 clip đã render sẵn (`6.mp4` trở đi).

---

## 2. Quy Tắc Bắt Buộc (User Directive)
> **"Từ giờ nếu không tìm ra file video thì tự đăng video tiếp theo!"**

- CẤM TUYỆT ĐỐI dừng/skip chỉ vì thiếu đúng số thứ tự `posted_count + 1`.
- Nếu file `next_video.mp4` không tồn tại hoặc rỗng (0 bytes):
  - Hệ thống BẮT BUỘC quét toàn bộ folder video của nick để tìm danh sách các file `{N}.mp4` hợp lệ có `N > posted_count` (hoặc `N >= next_video`).
  - Chọn file có số nhỏ nhất trong danh sách đó (`min(candidates)`) làm `next_video` để tiến hành upload.
  - Cập nhật số video đã đăng vào sổ cái / workbook tương ứng theo số video thực tế đăng.
  - CHỈ ĐƯỢC PHÉP skip `video_not_rendered` khi toàn bộ folder video thực sự không còn bất kỳ video nào lớn hơn `posted_count`.

---

## 3. Implementation Chuẩn Tại Gate 5 (`multi_machine_feed_session.py`)

```python
# Gate 5: Check next video render with auto-fallback
next_video = machine_row.get("posted_count", 0) + 1
media_root = Path(ctx.config.get("media_source_root") or host_paths["media_source_root"])
f_dir = media_root / folder_video

# Auto-fallback: nếu thiếu đúng số next_video, chọn số nhỏ nhất còn tồn tại >= next_video
rem = [
    int(f.stem) for f in f_dir.glob("*.mp4")
    if f.stem.isdigit() and f.stat().st_size > 0 and int(f.stem) >= next_video
] if f_dir.is_dir() else []

if rem:
    next_video = min(rem)

video_file = f_dir / f"{next_video}.mp4"

if not video_file.is_file() or video_file.stat().st_size == 0:
    payload = {
        "machine": account.machine,
        "row": account.account_row_index,
        "status": "skipped",
        "reason": "video_not_rendered",
        "expected_video": str(video_file),
        "workbook": workbook_path.name,
    }
    _write_upload_result(child_ctx, payload)
    return payload
```

---

## 4. Xử Lý Hiện Trường Khi Gặp Folder Khuyết Số (Emergency / Fix)
1. **Phương án nhanh:** Copy clip kế tiếp (ví dụ `6.mp4`) thành file bị khuyết (`5.mp4`) để thỏa mãn preflight ngay lập tức mà không làm gián đoạn ca chạy hiện tại.
2. **Chuẩn hóa dài hạn:** Đổi tên toàn bộ các file còn lại trong folder thành chuỗi số thứ tự liên tục `(posted_count + 1).mp4` đến `total.mp4`.
