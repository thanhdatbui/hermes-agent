# Case UI-52: Following Tab Render Latency, Loading Animation, and Polling Deadline Timeout

## 1. Triệu chứng & Bối cảnh
- **Incident**: Farm Alert Máy 13 (Anchor `duonguyen1202`, Row 2).
- **Log artifact**: `D:/Taadaa/runtime/kibe/live/<date>/row-2-<time>/<run_id>/machines/machine_13/<run_id>/follow_result.json`
- **Error payload**:
  ```json
  {
    "machine": 13,
    "row": 2,
    "exit_code": 1,
    "status": "MANUAL_REVIEW",
    "reason": "MANUAL_REVIEW: mở tab Đã follow fail cho duonguyen1202 sau ladder (lần 2)"
  }
  ```

## 2. Root Cause Analysis
1. **Trạng thái UI**:
   - Runner đã search thành công anchor `duonguyen1202`, verify exact normalized header handle.
   - Hàm `_open_following_tab` xác định đúng tab "Đã follow" (Following tab) và thực hiện `tap_center(adapter, node)`.
   - Sau khi tap, tab "Đã follow" đã chuyển sang trạng thái active / selected (`selected="true"`).
   - Tuy nhiên, do proxy mạng chậm hoặc thiết bị tải data trễ, TikTok hiển thị animation loading 2 chấm tròn (cyan + magenta) ở giữa màn hình thay vì hiển thị ngay RecyclerView danh sách người dùng.
2. **Cơ chế timeout quá chặt (10s deadline)**:
   - Trong `mode2_follow_followers.py`:
     ```python
     deadline = time.time() + 10
     while time.time() < deadline:
         nodes = _parse_mode2_nodes(adapter.dump_ui())
         if _on_follower_list(nodes):
             return True
         ...
         time.sleep(1.5)
     ```
   - Với chu kỳ dump UI và `time.sleep(1.5)`, vòng lặp chỉ kiểm tra được khoảng 3-4 lần dump.
   - Khi mạng proxy trễ hơn 10s, `_on_follower_list(nodes)` không thấy bất kỳ item username row nào -> hàm trả về `False`.
   - `run_mode2` coi đây là lỗi kẹt UI nghiêm trọng, kích hoạt Recovery Ladder rồi retry `_open_following_tab` lần 2. Lần 2 tiếp tục gặp mạng trễ quá 10s -> fail -> dừng phiên với Farm Alert giữ hiện trường.

## 3. Quy tắc khắc phục & Kiến trúc triển khai chuẩn
1. **Helper nhận diện trạng thái `_is_following_tab_selected_or_loading(nodes: list[dict]) -> bool`**:
   - **Cạm bẫy Type Coercion (`bool("false") is True`):** Trong UiAutomator XML và dict nodes, thuộc tính `selected` có thể là boolean `True`/`False` hoặc string `"true"`/`"false"`. Trong Python, `bool("false")` luôn trả về `True`, còn `"true" == True` trả về `False`. BẮT BUỘC dùng guard 2 tầng an toàn:
     ```python
     selected_val = node.get("selected")
     is_selected = selected_val is True or str(selected_val or "").strip().lower() == "true"
     ```
   - Tab "Đã follow" / "Following" đang selected (`is_selected` kèm khớp nhãn `FOLLOWING_TAB_TEXT` hoặc `_FOLLOWER_HEADER_RE`).
   - Hoặc có animation loading / progress bar / lottie (`class` chứa ProgressBar/Lottie/Loading, `resource_id` chứa loading/progress/anim, hoặc text/content-desc "loading"/"đang tải").
2. **Nâng polling deadline cơ sở & cơ chế Dynamic Extension**:
   - Base deadline khởi tạo: `deadline = start_time + 25.0` (thay vì 10s cố định).
   - Hard cap an toàn: `max_deadline = start_time + 35.0`.
   - Dynamic Extension: Trong vòng lặp polling, nếu phát hiện `_is_following_tab_selected_or_loading(nodes)` và thời gian còn lại `< 8.0s`, tự động gia hạn `deadline = min(deadline + 6.0, max_deadline)`.
3. **Bảo toàn Fast-Path & Phân biệt Zero-Following**:
   - Nếu `_on_follower_list(nodes)` trả về True: return `True` ngay lập tức (không delay thêm).
   - Nếu phát hiện 0-following (`_is_zero_following_screen_or_profile` liên tiếp 2 lần): return `False` với outcome `zero_following` ngay (không chờ hết timeout).
   - Kiểm tra phòng vệ: Trên UI dump cuối cùng (`current_nodes`), kiểm tra lại `_on_follower_list(current_nodes)` trước khi kết luận fail.

## 4. Quy trình Canary Test
- Chạy canary chuẩn theo script runner của repo:
  ```powershell
  powershell.exe -ExecutionPolicy Bypass -File D:/Taadaa/tiktok-follow/scripts/run-follow.ps1 -Machine 13 -AccountRowIndex 2 -ForcePreempt
  ```
- Kiểm tra kết quả `FOLLOW_RESULT` JSON trên stdout với status `OK` và danh sách followed accounts.
