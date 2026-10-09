# Lock Release Policy in multi_machine_feed_session.py

## Quy tắc xử lý Lease / Lock khi Feed gặp lỗi hoặc dừng sớm
- **Không giữ lock ở trạng thái `blocked`**:
  - Không gọi `lease.set_status("blocked")` hoặc ghi handoff `final_status="blocked"`, `lock_status="blocked"`, `succeeded=False`.
  - Giữ lock `blocked` sẽ làm tắc các đợt chạy kế tiếp của thiết bị/tài khoản.
- **Luôn release lock sau phiên**:
  - Ghi nhận recovery handoff: `succeeded=True`, `final_status="released"`, `lock_status="released"`.
  - Kết thúc lease bằng: `lease.finish(succeeded=True)`.
  - Áp dụng cả trong `_run_child` (khối cleanup / `_write_blocked`) và `_write_mapping_source_child_artifacts`.
