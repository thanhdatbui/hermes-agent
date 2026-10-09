# Teardown & Failure Surface Safety Invariants (Dry-run & ADB Client Guards)

## Vấn đề thực tế
Khi thêm hoặc chỉnh sửa logic dọn dẹp thiết bị (như đóng Recent Apps, ép rotation portrait, đưa về Home screen) trong teardown của workflow (đặc biệt tại nhánh `else:` khi workflow thất bại hoặc rơi vào `MANUAL_REVIEW`):
- Nếu gọi trực tiếp `self._close_recent_apps()` hoặc các thao tác ADB khác mà không kiểm tra trạng thái run, workflow sẽ crash hoặc gọi nhầm ADB trong các ca test mock, dry-run, hoặc khi `adb_client` chưa được khởi tạo.

## Quy tắc thiết kế bắt buộc
1. **Guard `not dry_run and adb_client is not None`**:
   Mọi thao tác can thiệp thiết bị thật trong teardown (kể cả teardown khi failure) phải nằm trọn vẹn bên trong khối điều kiện:
   ```python
   if not getattr(self.context, "dry_run", True) and getattr(self.context, "adb_client", None) is not None:
       try:
           self._enforce_portrait_rotation()
       except Exception as exc:
           logger.error(...)
       try:
           self._close_recent_apps()
       except Exception as exc:
           logger.warning("Đóng recent apps về Home khi failure thất bại: %s", exc)
   ```
2. **Bảo tồn Lease cho Recovery**:
   Thao tác giữ lease thiết bị (`self._hold_leases_for_recovery()`) phải nằm ngoài guard để đảm bảo lease luôn được quản lý đúng kể cả khi mock/dry-run.
3. **Bộ đôi Unit Test bắt buộc**:
   - Test 1 (Live/Device run): Verify `execute()` khi fail gọi đúng trình tự teardown (vd: `calls == ["portrait", "recent"]`) và giữ lease `handoff`.
   - Test 2 (Dry-run): Verify `execute()` với `dry_run=True` và `adb_client=None` KHÔNG gọi `_close_recent_apps()`, nhưng vẫn gọi `_hold_leases_for_recovery()`.
