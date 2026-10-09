# Auto-Advance Validation & Verification Rules

## 1. Nguy cơ khi dùng Substring check lỏng lẻo
- Khi kiểm tra kết quả upload trong `multi_machine_feed_session.py`, nếu chỉ kiểm tra `"[auto-advance]" in stdout` hoặc `"auto-advance" in stdout`:
  - Bất kỳ chuỗi log ngẫu nhiên nào chứa từ khóa "auto-advance" cũng khiến runner tin rằng đã auto-advance hợp lệ.
  - Video number trả về trong report (`report.json`) có thể là video rác hoặc sai lệch mà không được đối chiếu với video dự kiến ban đầu (`next_video`).

## 2. Quy chuẩn Regex Validation
Bắt buộc sử dụng regex chặt chẽ đối chiếu trực tiếp cấu trúc log phát ra từ `state_machine.py`:
```python
import re

auto_advance_matched = False
if actual_video_num is not None and actual_video_num > int(next_video):
    aa_match = re.search(
        r"\[AUTO-ADVANCE\]\s+Skipped\s+\d+\s+verified\s+video\(s\);\s+new_video_number=(\d+)\s+\(was\s+(\d+)\)",
        stdout,
    )
    if aa_match:
        aa_new, aa_was = int(aa_match.group(1)), int(aa_match.group(2))
        if aa_new == actual_video_num and aa_was == int(next_video):
            auto_advance_matched = True

is_video_num_valid = (
    actual_video_num is not None
    and (
        actual_video_num == int(next_video)
        or auto_advance_matched
    )
)
```

## 3. Tiêu chí Fail-Closed
- `aa_new` phải khớp tuyệt đối `actual_video_num`.
- `aa_was` phải khớp tuyệt đối `int(next_video)`.
- Nếu có bất kỳ sự sai lệch nào hoặc thiếu log chuẩn: Fail-closed ngay lập tức với `post_verification_failed`.
