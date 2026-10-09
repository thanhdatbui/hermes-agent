# Xử lý Nhận diện Máy Trống Slot / Chưa Có Nick trong Watchdog qua run_manifest.json

## Vấn đề thực tế
- Khi runner chạy một ca/phiên nuôi (ví dụ: Row 8 chỉ có 58 máy có nick trên tổng số 80 máy fleet), runner sẽ safe-skip 22 máy trống nick (`account row X is empty (no username) for machine Y, skipping`).
- Việc safe-skip diễn ra ngay trước khi khởi tạo device runner nên:
  - KHÔNG tạo thư mục `machines/machine_Y/`
  - KHÔNG tạo file `machines/machine_Y/summary.txt`
  - Danh sách đầy đủ 80 máy (kèm kết quả thành công, lỗi, hoặc safe-skip) chỉ được runner lưu tập trung tại:
    - Root file `run_manifest.json` (mục `multi_machine_summary`)
    - Root file `summary.txt`

## Hậu quả nếu Watchdog chỉ quét machines/
- Nếu `parse_run_all(run_dir)` trong `feed_session_watchdog.py` chỉ tìm kiếm `machines/machine_*/summary.txt`, toàn bộ các máy trống slot sẽ bị rơi rớt khỏi `all_machines`.
- Báo cáo watchdog tổng kết phiên sẽ hiển thị sai lệch:
  - `Tổng máy xử lý: 58 máy`
  - `Trống slot/chưa có nick (0): Không có`
  -> Người vận hành hiểu nhầm là toàn bộ fleet chỉ có 58 máy hoặc 0 máy nào trống slot.

## Nguyên tắc xử lý chuẩn
1. **Luôn parse `run_manifest.json` tại root `run_dir`:**
   - Đọc key `multi_machine_summary` (dạng list các dict).
   - Duyệt từng item:
     - Nếu `expected_username == "account:empty"` hoặc `"is empty (no username)" in str(item.get("stop_reason", "")).lower()`:
       Đánh dấu máy với `status = "skipped-empty"` và `reason = item.get("stop_reason")`.
     - Nếu `final_status == "success"`: ghi nhận `status = "success"`.
     - Nếu `final_status == "config-error"` và không phải empty: ghi nhận `status = "fail"`.
2. **Merge thông minh với `machines/machine_*/summary.txt`:**
   - Thông tin chi tiết từ file summary của từng máy (likes, swipes, feed_counts, comment_peeks) luôn có độ ưu tiên cao để làm phong phú dữ liệu thống kê.
3. **Báo cáo trung thực quy mô fleet:**
   - Tổng máy xử lý phải phản ánh đúng quy mô fleet đã đối soát (80 máy).
   - Nhóm `Trống slot/chưa có nick` hiển thị đầy đủ danh sách và số lượng các máy bị trống slot ở row tương ứng thay vì báo 0 máy.
