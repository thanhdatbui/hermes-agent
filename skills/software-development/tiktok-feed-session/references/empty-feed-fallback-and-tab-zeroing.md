# Empty Feed Fallback & Tab Zeroing Pattern

## 1. Triệu chứng màn gợi ý rỗng
Khi tài khoản chuyển qua tab `Bạn bè` (`friends`) hoặc `Đang follow` (`following`), nếu tài khoản mới hoặc chưa có quan hệ follow/bạn bè, TikTok sẽ không hiển thị video feed bình thường mà đưa ra màn hình gợi ý rỗng.
Các dấu hiệu nhận diện đặc trưng trong UI XML / Content terms (`_FRIENDS_FEED_CONTENT_TERMS`):
- `"Hãy follow bạn bè"`
- `"Nhật ký"`
- `"Tác giả nổi bật"`
- `"bạn sẽ nhận thấy họ ở đây"`
- `"xem video mới nhất của họ tại đây"`
- `"Khi bạn Follow"`

## 2. Quy trình Fallback & Skip Tab trong Phiên
1. **Fallback về For You**:
   - Khi `_has_friends_feed_content(after)` trả về `True` trong khi đang ở tab `friends` hoặc `following`:
   - Lập tức điều hướng quay lại `for-you` qua `tap_navigation_target(ctx, _top_tab_target(FEED_TYPE_FOR_YOU), ...)`.
   - Ghi nhận `ctx.logger.log` với step `empty_feed_fallback_<swipe_count>`, action `fallback_to_for_you`.
   - Cập nhật state nội bộ: `current_feed_type = FEED_TYPE_FOR_YOU`, `after["feed_type"] = FEED_TYPE_FOR_YOU`.

2. **Triệt tiêu tab rỗng (Distribution Zeroing)**:
   - Nếu để nguyên `feed_distribution`, các nhịp đổi tab ngẫu nhiên kế tiếp (`_weighted_feed_choice`) sẽ tiếp tục bốc lại tab rỗng này, gây lãng phí swipe và navigation loop.
   - Cơ chế skip: Ngay tại thời điểm fallback, set trọng số của tab đó về 0:
     ```python
     feed_distribution[current_feed_type] = 0.0
     ```
   - Nhờ đó, các lần chọn tab tiếp theo trong phiên tự động loại bỏ tab rỗng này.

## 3. Quy chuẩn Format Patch trong repo `tiktok-luot nuoi acc`
- File `python_runner/flows/feed_swipe_smoke.py` có đặc trưng formatting với các blank lines mở rộng giữa các phần tử dict/tuple/hàm.
- Khi chỉnh sửa file:
  - Giữ nguyên cấu trúc dòng và khoảng cách dòng gốc.
  - Tuyệt đối không làm dính dòng lệnh (ví dụ `break`) vào dòng comment hoặc cấu trúc rẽ nhánh bên dưới.
  - Chạy `python -m py_compile python_runner/flows/feed_swipe_smoke.py` để đảm bảo tính toàn vẹn cú pháp trước khi commit hoặc chạy canary.

## 4. Standalone Probe Test Pattern (Xác minh trực tiếp trên máy đơn)
Khi cần chạy probe test cô lập logic empty feed fallback trên 1 máy cụ thể (ví dụ Máy 66):
- **Python Environment**: Dùng `C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe` hoặc `D:/Taadaa/python-envs/automation/Scripts/python.exe`. Xóa sạch `PYTHONPATH`/`VIRTUAL_ENV` của Hermes venv để tránh lỗi `_imaging` từ PIL.
- **Import rules**:
  - `DeviceContext` từ `core.device` (thuộc `automation-core`), `ArtifactCollector` từ `core.artifacts`.
  - Tuyệt đối không import `core.config` (không tồn tại trong module tree).
- **Luồng Probe Test**:
  1. Kiểm tra serial qua `adb devices` và xác nhận TikTok đang chạy hoặc mở bằng `monkey` / `am start`.
  2. Bấm thẳng vào tab Bạn bè: gọi `tap_navigation_target(ctx, _top_tab_target(FEED_TYPE_FRIENDS))`.
  3. Lấy attempt/XML hiện tại, chạy `_has_friends_feed_content(after)` kiểm tra các marker gợi ý rỗng (`Hãy follow bạn bè`, `Nhật ký`, v.v.).
  4. Nếu phát hiện rỗng, kích hoạt fallback: `tap_navigation_target(ctx, _top_tab_target(FEED_TYPE_FOR_YOU))`.
  5. Chụp ảnh màn hình bằng chứng qua `adb exec-out screencap -p > <output_path>.png` và xuất kết quả `MEDIA:<path>`.
