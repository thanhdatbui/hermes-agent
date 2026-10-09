# Race Condition 'lease release or handoff failed' in multi_machine_feed_session

## 1. Hiện tượng & Triệu chứng
Khi chạy `multi-machine-feed-session` (hoặc canary test qua `run-feed-session.ps1`), một số máy hoàn thành đủ số lượt swipe (ví dụ 2/2 hoặc 10/10) nhưng kết quả trả về bị chuyển thành `failed`:
- `final_status`: `"failed"`
- `blocker_type`: `"lease-finish-failed"`
- `stop_reason`: `"lease release or handoff failed"`
- File `run_manifest.json` và log summary bị ghi đè sang trạng thái thất bại dù trước đó task feed đã thành công.

## 2. Nguyên nhân gốc rễ (Root Cause)
Vị trí: `python_runner/flows/multi_machine_feed_session.py` trong khối teardown `finally:` của hàm `_run_child`.

1. **Tranh chấp quyền kết thúc giữa Worker và Watchdog:**
   - Worker hoàn thành feed session, đặt `initial_goal_completed = True`.
   - Worker bước vào teardown để giải phóng `device_lock` qua `_release_under_lock()`.
   - `_release_under_lock()` kiểm tra:
     ```python
     if _watchdog_deadline_expired(timing) or not _claim_success_release(timing):
         return False
     ```
   - Nếu thời gian chạy sát ngưỡng hard timeout (`deadline_mono`) hoặc watchdog thread đồng thời claim quyền terminalize (`_claim_watchdog_terminal`), worker không claim được `success_release`.
2. **Kích hoạt logic ghi đè lỗi:**
   - Khi `_release_under_lock()` trả về `False` hoặc ném ngoại lệ transient lúc `lease.finish(succeeded=True)`:
     ```python
     goal_completed = False
     lease_release_failed = True
     ```
   - Đoạn code sau đó kiểm tra:
     ```python
     if lease_release_failed or (initial_goal_completed and not goal_completed):
         failed_result = _child_flow_result(
             ExitStatus.FAIL,
             "lease release or handoff failed",
             stop_reason="lease release or handoff failed",
             final_status="failed",
             ...
         )
     ```
   - Dẫn đến việc đè bẹp kết quả hợp lệ thành failure và mark lock thành `handoff`/`blocked`.

## 3. Hướng khắc phục chuẩn (Standard Resolution)
1. **Phân tách rạch ròi Work Completion vs Lease Cleanup:**
   - Nếu session đã đạt `initial_goal_completed == True` (đã swipe đủ target), không bao giờ được cưỡng bức đổi `final_status` thành hard failure chỉ vì watchdog đã hết hạn trong lúc dọn lock.
   - Thử fallback giải phóng an toàn `lease.release()` trong khối `try...except` để tránh bỏ rơi lock mồ côi (`device_lock`) trên ổ đĩa.
2. **Đồng bộ hóa State Lock:**
   - Đảm bảo việc cập nhật `timing["success_release_completed"] = True` và kiểm tra `_watchdog_deadline_expired` diễn ra nguyên tử dưới `state_lock` hoặc có grace period nhỏ (ví dụ 5-10s) cho thao tác I/O giải phóng lease sau khi feed hoàn tất.
3. **Canary Verification:**
   - Chạy kiểm chứng trên 1 máy (ví dụ Máy 51) với `run-feed-session.ps1 -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`.
   - Chụp ảnh màn hình nghiệm thu màn hình TikTok Feed để xác nhận máy không bị kẹt lock và trạng thái feed hiển thị đúng.
