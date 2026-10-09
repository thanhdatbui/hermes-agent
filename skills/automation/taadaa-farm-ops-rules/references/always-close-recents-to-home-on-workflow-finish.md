# Quy tắc đóng Recent Apps đưa thiết bị về Home khi kết thúc Workflow

## Bối cảnh & Nguyên tắc
Trên farm Android (đặc biệt là Samsung Galaxy S7 / J7 / thiết bị cũ), khi các workflow automation (upload, login, reg, feed...) kết thúc:
- **Dù THÀNH CÔNG hay LỖI/CHƯA ĐẠT DONE**, bắt buộc phải đóng recent apps và đưa thiết bị về màn hình HOME (`close_all_recent_apps` / `_close_recent_apps()`).
- Tuyệt đối không để app treo ở màn hình lỗi, dialog báo lỗi hoặc màn hình dở dang, vì sẽ làm bẩn UI surface cho các worker, batch hoặc cron session tiếp theo mượn máy.

## Triển khai trong Tiktok-video (`state_machine.py`)
Tại khối teardown / finalization trong `StateMachine.execute(context)`:
1. Khi `completed is True`: dọn dẹp media tạm thời (`_cleanup_transient_media`), gọi `_close_recent_apps()`, sau đó nhả lease (`_release_leases`).
2. Khi `completed is False` (failure / retry limit exhausted / exception):
   - Đảm bảo giữ rotation portrait (`_enforce_portrait_rotation()`).
   - BẮT BUỘC gọi `_close_recent_apps()` (bọc `try...except` log warning để không chặn luồng recovery lock).
   - Giữ lease cho recovery (`_hold_leases_for_recovery()`).

## Cập nhật Unit Test
Khi sửa đổi logic teardown trong failure path:
- File test liên quan: `tests/test_tiktok_workflow.py` (`test_execute_keeps_failure_surface_and_holds_device_lease_for_recovery`).
- Mock calls kỳ vọng sẽ ghi nhận cả `recent` thay vì chỉ có `portrait`:
  `assert calls == ["portrait", "recent"]`.
