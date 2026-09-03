# Batch Reservation Lock Fault Isolation (Cô lập lỗi Lock/Guard từng máy trong Batch Runner)

## Bối cảnh & Hiện tượng (Sự cố sáng 29/08/2026)
- Khi chạy batch nuôi acc nhiều máy (`multi_machine_feed_session`), hệ thống có vòng lặp đặt trước quyền truy cập thiết bị (`acquire_device_lock` với `status="queued"` cho từng máy trong danh sách).
- Nếu trên 1 máy tồn tại file guard sót lại (ví dụ `.machine_1.lock.json.takeover.lock`) hoặc lỗi transaction, `automation-core` ném ra `DeviceLockTransactionError` (`DEVICE_LOCK_ACQUIRE_GUARD_UNAVAILABLE` hoặc `DEVICE_LOCK_ACQUIRE_GUARD_RELEASE_FAILED`) hoặc `DeviceLockReadinessError`.
- Các exception này kế thừa từ `RuntimeError`, không nằm trong `(DeviceLockUnavailable, DeviceLockNeedsUserDecision)`.
- **Hậu quả nếu không cô lập:** Khi quét đến máy bị lỗi guard, exception văng ra ngoài vòng lặp làm crash toàn bộ tiến trình batch runner, khiến tất cả các máy còn lại dù hoàn toàn rảnh rỗi cũng bị dừng và không thể khởi chạy.

## Quy tắc cốt lõi (Core Invariant)
> **Máy nào lỗi lock/guard thì chỉ skip riêng máy đó (`skipped-device-locked`), tuyệt đối không để 1 máy làm crash toàn bộ batch của farm.**

## Cách triển khai chuẩn
1. **Mở rộng phạm vi bắt Exception trong Reservation Loop:**
   ```python
   except (DeviceLockUnavailable, DeviceLockTransactionError, DeviceLockReadinessError) as exc:
       err_msg = exc.describe() if hasattr(exc, "describe") else str(exc)
       ctx.logger.log(
           device_id=account.serial,
           account=str(account.machine),
           step="reservation",
           action="acquire_device_lock",
           result="skipped-device-locked",
           error=err_msg,
       )
       skipped = _write_fallback_child_artifacts(
           ctx,
           account,
           resolved_adb or fallback_adb,
           message=f"[device-lock] SKIP machine {account.machine}: {err_msg}",
           stop_reason=err_msg,
           final_status="skipped-device-locked",
       )
       rows.append(skipped.as_dict())
   ```

2. **Đồng bộ trên các điểm Acquire khác:**
   - Trong `reacquire_recovery_lock` (khi cần lấy lại lock trong retry/recovery): bắt cả `(DeviceLockUnavailable, DeviceLockTransactionError, DeviceLockReadinessError)` trong vòng lặp retry.
   - Trong CLI single-machine `run_tiktok.py`: bắt đầy đủ để trả về `FlowResult` với `final_status="skipped-device-locked"`.

3. **Ghi nhận Case Catalog:**
   - Luôn cập nhật Case Fix & Anti-Pattern tương ứng (ví dụ `Case LOCK-04`) vào `docs/farm-automation-cases.md` theo Gate 0.5.
