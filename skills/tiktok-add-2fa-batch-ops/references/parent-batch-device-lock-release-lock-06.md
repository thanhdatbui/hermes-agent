# Cơ Chế Giải Phóng Device Lock Trong Batch Cha-Con (Case LOCK-06) (2026-09-07)

## 1. Hiện Tượng & Triệu Chứng Lỗi
- Khi chạy batch runner cha (như `run_batch_live_2fa.py`) điều phối song song nhiều thiết bị:
  + Runner cha gọi `acquire_device_lock` để cấp phát trước reservation locks cho danh sách máy.
  + Runner spawn các worker con (`run_capture_phase_b.py`) qua `ThreadPoolExecutor`.
  + Các worker con thực thi trên thiết bị thật, tiếp quản lock (`takeover`) hoặc giải phóng lock qua `lease.finish(succeeded=...)`.
- Tại khối `finally:` hoặc các khối `except` preflight của runner cha:
  ```python
  finally:
      for reservation in reservations:
          reservation.release()
  ```
- **Lỗi văng ra:**
  `automation_core.device_lock.DeviceLockReleaseError: DEVICE_LOCK_RELEASE_OWNERSHIP_MISMATCH`
  (hoặc `DEVICE_LOCK_RELEASE_PATH_MISSING`).
- Hậu quả: Dù các máy con đã chạy xong và hoàn tất công việc, ngoại lệ này làm sập toàn bộ runner cha ở phút chót, không in được bảng kết quả tổng hợp `_print_results`, exit code văng 1 và kích hoạt cảnh báo lỗi giả.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
- Trong `automation_core.device_lock`, phương thức `reservation.release()` mặc định gọi `_release_lease_paths(strict=True)`.
- Khi `strict=True`:
  + Hàm kiểm tra từng file lock path xem còn thuộc quyền sở hữu của lease hiện tại hay không.
  + Nếu worker con đã takeover (lock file mang PID/run_id mới) hoặc đã xóa file lock, `_release_lease_paths` ném ngoại lệ `DeviceLockReleaseError`.

## 3. Quy Chuẩn Khắc Phục Chuẩn (Standard Fix)
1. **Sử dụng `release_with_audit` với `strict=False`:**
   Runner cha BẮT BUỘC sử dụng phương thức `reservation.release_with_audit(reason=...)`. Hàm này chạy với `strict=False`, chỉ giải phóng các file lock mà runner cha vẫn thực sự nắm giữ và bỏ qua an toàn các file đã được tiến trình con tiếp quản hoặc hoàn tất.
2. **Bọc an toàn trong `try...except`:**
   ```python
   # Trong finally: và các khối except dọn dẹp reservation
   for reservation in reservations:
       try:
           if hasattr(reservation, "release_with_audit"):
               reservation.release_with_audit(reason="batch-complete")
           else:
               reservation.release()
       except Exception:
           pass
   ```
3. **Thứ tự Mapping Reservation Dict:**
   Khi tạo dict mapping `reservations_by_machine`, BẮT BUỘC tạo TRƯỚC khi gán lại hoặc re-order `reserved_targets` theo `launch_plan.order` để không bị nhầm lẫn handle lock giữa các máy.
