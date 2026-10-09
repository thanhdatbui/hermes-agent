# Debugging & Root Cause: "lease release or handoff failed"

## 1. Hiện tượng & Triệu chứng
- Máy (ví dụ Máy 51, serial `ce0616063df1094004`) thực tế đã lướt feed thành công (hoặc hoàn tất goal ban đầu), nhưng kết quả cuối cùng bị ghi đè:
  - `final_status`: `"failed"`
  - `blocker_type`: `"lease-finish-failed"`
  - `stop_reason`: `"lease release or handoff failed"`

## 2. Vị trí mã nguồn phụ trách (Đích danh - CẤM quét đĩa)
- **File:** `D:\Taadaa\tiktok-luot nuoi acc\python_runner\flows\multi_machine_feed_session.py`
- **Hàm chính:**
  - `_run_child()`: Đoạn teardown trong khối `finally:` (khoảng dòng 4920-5065).
  - `_release_under_lock()`: Thực hiện giải phóng lease dưới quyền của publication lock.
  - `_claim_success_release(timing)`: Kiểm tra điều kiện worker có quyền publish kết quả thành công so với watchdog (kiểm tra `publication_owner == "worker"`, `terminalized`, `deadline_mono`).

## 3. Cơ chế phát sinh lỗi (Root Cause)
1. Sau khi `feed_session_smoke` chạy xong và xác nhận thành công (`initial_goal_completed = True`), execution flow đi vào khối `finally:` của `_run_child` để giải phóng device lease (`device_lock`).
2. Trong khối `finally:`, code gọi `_release_under_lock()`:
   ```python
   def _release_under_lock() -> bool:
       if _watchdog_deadline_expired(timing) or not _claim_success_release(timing):
           return False
       ...
       lease.finish(succeeded=True)
       ...
   ```
3. Nếu xảy ra tranh chấp thời gian (watchdog deadline chạm ngưỡng, hoặc `_claim_success_release` từ chối vì watchdog đã can thiệp, hoặc ngoại lệ khi gọi `lease.finish`), hàm trả về `False` hoặc ném `Exception`.
4. Logic xử lý fail-safe hiện tại:
   ```python
   if not _release_under_lock():
       goal_completed = False
       lease_release_failed = True
   ```
   Và sau đó:
   ```python
   if lease_release_failed or (initial_goal_completed and not goal_completed):
       child_result = replace(
           child_result,
           final_status="failed",
           blocker_type="lease-finish-failed",
           stop_reason="lease release or handoff failed",
       )
   ```
   Dẫn đến kết quả thành công bị đảo ngược hoàn toàn thành lỗi fail do handoff/release.

## 4. Nguyên tắc xử lý (Scope Lock & Safe Release)
- **Scope Lock:** Phải phân định rõ ràng giữa việc hoàn thành nghiệp vụ (child session status) và việc dọn dẹp hạ tầng (lease release).
- **Graceful Release:** Khi session con đã thành công (`initial_goal_completed = True`), worker cần cố gắng release lease mà không để race condition với watchdog timing làm mất đi trạng thái thành công thực tế của thiết bị, trừ phi thật sự vi phạm hard boundary không thể cứu vãn.
- **Tránh recursive scan:** Khi gặp alert về lỗi này, mở trực tiếp `multi_machine_feed_session.py`, tuyệt đối không dùng `os.walk` hay `grep -rn` quét `.ai-runs` vì dung lượng cực lớn sẽ gây timeout 900s.
