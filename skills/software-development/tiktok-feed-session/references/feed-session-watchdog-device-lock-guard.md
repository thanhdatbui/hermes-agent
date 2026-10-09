# Feed Session Watchdog: Device Lock Guard & Reporting Rules

## 1. Vai trò của feed_session_watchdog.py
Script `C:\Users\Kibe\AppData\Local\hermes\scripts\feed_session_watchdog.py` đóng vai trò giám sát và chốt báo cáo tự động cho các phiên nuôi feed TikTok (`D:\Taadaa\runtime\kibe\live\<YYYY-MM-DD>`).
Một ngày gồm 3 ca, mỗi ca 3 phiên:
- Ca 1: Phiên 1 (06:00-07:30), Phiên 2 (07:30-09:00), Phiên 3 (09:00-12:00 + Upload)
- Ca 2: Phiên 1 (12:00-13:40), Phiên 2 (13:40-15:15), Phiên 3 (15:15-18:30 + Upload)
- Ca 3: Phiên 1 (18:30-20:15), Phiên 2 (20:15-21:45), Phiên 3 (21:45-23:59 + Upload)

## 2. Cơ chế Device Lock Guard chống chốt phiên sớm

### Vấn đề:
Khi nhiều tiến trình hoặc job chạy song song, một số máy có thể bị khóa (`device-lock`, `skipped-device-locked`, hoặc `device lock active`).
Nếu watchdog coi các máy bị khóa là đã hoàn tất (`fail` hoặc `done`), nó sẽ tính đủ số lượng `expected_machines` và chốt báo cáo sớm trước khi phiên hết giờ, làm mất cơ hội chạy bù ở các tick cron tiếp theo trong cùng phiên.

### Giải pháp kỹ thuật chuẩn:
1. **Phát hiện máy bị skip do lock (`is_device_locked_skip`)**:
   - Kiểm tra `status == "skipped-device-locked"` hoặc reason chứa `"device-lock"` / `"device lock active"`.
2. **Quy tắc gộp kết quả máy qua nhiều lượt chạy (`merge_machine_result`)**:
   - `success` luôn được ưu tiên giữ nguyên.
   - Kết quả chạy thật (`real run` - success hoặc fail thật) luôn được ưu tiên hơn kết quả bị khóa (`skipped-device-locked`).
   - Nếu lượt 1 bị lock nhưng lượt 2 chạy thật -> giữ kết quả lượt 2.
   - Nếu lượt 1 chạy thật nhưng lượt 2 bị lock -> giữ kết quả lượt 1.
3. **Điều kiện chốt báo cáo (`can_report_session`)**:
   - `real_completed`: Chỉ tính máy đã chạy thực sự (bỏ qua máy chỉ có status lock).
   - `has_unattempted_locked`: Có bất kỳ máy nào trong danh sách dự kiến hiện CHỈ có trạng thái bị khóa.
   - **Chốt ngay khi hoàn tất**: Nếu toàn bộ máy dự kiến đã chạy thật xong (`completed_expected_count >= expected_count` và `not has_unattempted_locked`), chốt ngay lập tức kể cả khi runner còn đang busy.
   - **Chặn chốt sớm trong phiên**: Nếu `is_today` và `now_hm < window_end_hm`:
     - Nếu `runner_busy` hoặc `has_unattempted_locked` -> trả về `False`.
     - Ngược lại chỉ chốt khi `completed_expected_count >= expected_count`.
   - **Grace period 20 phút sau khi hết giờ phiên**: Khi `now_hm >= window_end_hm`:
     - Nếu runner vẫn đang chạy (`runner_busy`): cho phép gia hạn tối đa 20 phút (`grace_end_hm = window_end_hm + 20p`). Trong 20 phút này vẫn trả về `False` để đợi runner vét xong.
     - Sau 20 phút gia hạn hoặc khi runner đã dừng hẳn -> BẮT BUỘC chốt báo cáo ngay lập tức (không để sót hay trôi phiên).

## 3. Pitfall môi trường Windows: Python unittest qua khác ổ đĩa (Drive Mount)
- **Hiện tượng**: Chạy `python -m unittest C:\path\to\test.py` khi CWD đang ở ổ `D:\` sẽ văng lỗi:
  `ValueError: path is on mount 'C:', start on mount 'D:'`
- **Nguyên nhân**: Module `unittest` của Python cố gắng tính đường dẫn tương đối bằng `os.path.relpath(name, os.getcwd())`, hàm này trên Windows không hỗ trợ đường dẫn giữa hai ổ đĩa khác nhau (`C:` và `D:`).
- **Khắc phục**: Luôn đổi thư mục làm việc về cùng ổ đĩa với test file trước khi chạy:
  `cd /c/Users/Kibe/AppData/Local/hermes/scripts && python -m unittest test_feed_session_watchdog.py`
  hoặc chỉ định `workdir` trùng với thư mục chứa test.
