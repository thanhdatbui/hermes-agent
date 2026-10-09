# Watchdog & Device Lock Lease Release Contract

## 1. Phân định ranh giới kiến trúc (Architecture Boundaries)
- `feed_swipe_smoke.py`: Chỉ phụ trách flow swipe/interact trên thiết bị. Tuyệt đối KHÔNG chứa code quản lý `device_lock`, `lease`, `reservation` hay `watchdog`.
- `multi_machine_feed_session.py`: Là nơi duy nhất quản lý vòng đời device lease (`acquire_device_lock`), timeout watchdog thread, atomic publication fencing, và handoff evidence.

## 2. Các hàm cốt lõi & Race Condition Pitfalls

### `_watchdog_deadline_expired(timing)`
- Kiểm tra: `time.monotonic() >= float(timing["deadline_mono"])`.
- **Pitfall**: Nếu worker đã hoàn thành đủ số lượt swipe (`goal_completed = True`), nhưng thời gian chạy chạm ngưỡng deadline trong lúc chạy hooks/teardown, việc check deadline trước khi nhả lock có thể chặn worker hoàn tất release sạch sẽ.

### `_claim_success_release(timing)` vs `_claim_watchdog_terminal(timing)`
- Worker gọi `_claim_success_release` để đặt `timing["success_release_started"] = True`.
- **Pitfall quan trọng về Interleaving & Hard Deadline (test_watchdog_interleaving_with_success_release)**:
  - Nếu worker đã hoàn tất release thành công (`success_release_completed == True`), watchdog TUYỆT ĐỐI KHÔNG ĐƯỢC cướp quyền (`return False`).
  - Nhưng nếu worker chỉ mới `success_release_started == True` mà **deadline đã quá hạn** (`time.monotonic() >= deadline`) hoặc `force=True` (worker bị kẹt/treo quá hard deadline trong lúc release), Watchdog BẮT BUỘC PHẢI cướp quyền terminal (`terminalized = True`, `publication_owner = "watchdog"`) để fail-closed, tránh treo lease vô tận.
  - CẤM chặn vô điều kiện `if timing.get("success_release_started"): return False` trong `_claim_watchdog_terminal`, vì điều này sẽ phá vỡ test interleaving và làm tê liệt cơ chế fail-safe của watchdog khi worker bị hang trong bước teardown.

### Nghịch lý trong `_release_under_lock()`
- Khi worker gọi:
  ```python
  lease.finish(succeeded=True)  # Lock đã thực sự được release
  ```
  Nhưng ngay sau đó:
  ```python
  def _record_completion():
      if now >= float(timing.get("deadline_mono", 0)) or timing.get("terminalized") or timing.get("publication_owner") != "worker":
          return False
      ...
  ```
  Nếu `_record_completion()` trả về `False`, `_release_under_lock()` sẽ trả về `False`.
- **Hậu quả**:
  1. `goal_completed` bị lật ngược thành `False`.
  2. `lease_release_failed = True`.
  3. Session thành công bị ghi đè thành `final_status = "failed"`, `blocker_type = "lease-finish-failed"`, `stop_reason = "lease release or handoff failed"`.
  4. Script cố gắng gọi `lease.set_status("blocked")` lên một lease đã được release.

## 3. Quy tắc Patch Contract chuẩn
1. **Watchdog tôn trọng release thành công, nhưng fail-closed khi quá hạn**:
   Trong `_claim_watchdog_terminal`:
   - Nếu `timing.get("success_release_completed")` là `True`, watchdog KHÔNG ĐƯỢC cướp quyền terminal (`return False`).
   - Nếu `timing.get("success_release_started")` là `True` nhưng `now < deadline` và không `force`: watchdog không cướp quyền để worker tiếp tục teardown.
   - Nhưng nếu `timing.get("success_release_started")` là `True` mà `now >= deadline` (hoặc `force=True`) và chưa `success_release_completed`: watchdog PHẢI cướp quyền terminal (`return True`) để bảo vệ barrier và pass `test_watchdog_interleaving_with_success_release`.
2. **Không biến thành công thành thất bại sau khi `lease.finish()`**:
   Một khi `lease.finish(succeeded=True)` đã hoàn tất thành công, `_release_under_lock` BẮT BUỘC phải ghi nhận `success_release_completed = True` và trả về `True`, không được phép fail chỉ vì `now >= deadline_mono`.
3. **Ưu tiên teardown sạch sẽ**:
   Khi worker đã đạt goal (`goal_completed == True`), teardown phải được ưu tiên giải phóng lock sạch sẽ thay vì đánh dấu kẹt blocked.
