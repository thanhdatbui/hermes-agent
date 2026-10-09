# Case LOCK-05: Kế Thừa Device Lock Giữa Parent Feed Runner và Child Upload Workflow

## 1. Hiện Tượng & Triệu Chứng
- Khi chạy ca nuôi acc kết hợp đăng video (ví dụ Ca 1 - Phiên 1, Row 1 ngày 25/09/2026):
  - Lướt feed hoàn tất thành công (62-67 máy).
  - Bước đăng video: **100% 50 máy đều bị fail đồng loạt** (0 video được đăng).
- Chi tiết lỗi trong `upload_result.json` và `log.jsonl` tại artifact từng máy:
  ```text
  status: "failed"
  reason: "[FAILED] [NEEDS_USER_DECISION] ACQUIRE_LOCKS: Cần user quyết định cho device lock: device needs user decision (locked by another owner): path=C:\Users\Kibe\.codex\device-locks\machine_N.lock.json pid=... host=... project=tiktok-luot nuoi acc machine=N serial=... status=running"
  ```

## 2. Nguyên Nhân Gốc Rễ
- Tiến trình cha `multi_machine_feed_session.py` (project `tiktok-luot nuoi acc`) khởi tạo và acquire device lock trên thiết bị trong suốt ca nuôi.
- Khi chuyển sang bước hook upload, tiến trình con `scripts.tiktok_workflow` (`Tiktok-video`) được khởi động và chạy hàm `_handle_acquire_locks()` trong `state_machine.py`.
- Tại đây, uploader gọi `acquire_device_lock(user_authorized=False)`. Thư viện `automation-core` phát hiện lock đang bị chiếm bởi một tiến trình đang chạy (`status="running"`, `project="tiktok-luot nuoi acc"`), nên ném ngoại lệ `DeviceLockNeedsUserDecision`.
- Do `state_machine.py` trước đó chỉ bắt và re-raise `WorkflowError(..., "NEEDS_USER_DECISION")`, toàn bộ tiến trình upload con tự hủy fail-closed mà không thực hiện được bất kỳ thao tác nào trên TikTok.

## 3. Giải Pháp Kỹ Thuật Chuẩn (Patch Contract)
Trong `D:/Taadaa/Tiktok-video/scripts/tiktok_workflow/state_machine.py`, cập nhật khối xử lý `except DeviceLockNeedsUserDecision as e`:
```python
        except DeviceLockNeedsUserDecision as e:
            parent_project = str((getattr(e, "owner", None) or {}).get("project") or "").strip().lower()
            if parent_project in ("tiktok-luot nuoi acc", "tiktok-feed", "multi-machine-feed-session"):
                logger.info(
                    "[LOCK-INHERIT] Kế thừa device lock từ parent project '%s' (pid=%s) cho machine=%s, serial=%s",
                    parent_project,
                    (getattr(e, "owner", None) or {}).get("pid"),
                    machine,
                    device_id,
                )
                self.context.device_lease = None
            else:
                raise WorkflowError(
                    WorkflowState.ACQUIRE_LOCKS,
                    f"Cần user quyết định cho device lock: {e.describe()}",
                    "NEEDS_USER_DECISION",
                )
```

## 4. Kỷ Luật Kiểm Thử Bắt Buộc (Test Evidence)
- **Tách File Test Focused**: TUYỆT ĐỐI KHÔNG thêm test vào file monolith lớn `tests/test_tiktok_workflow.py` (tránh dính legacy failures và timeout 60s làm fail Closeout Gate).
- Tạo file riêng `tests/test_lock_inheritance.py` bao phủ đầy đủ:
  1. `test_acquire_lock_inherits_parent_feed_session_lock`: Kế thừa thành công từ parent `tiktok-luot nuoi acc` (trả về `True`, `device_lease=None`).
  2. `test_acquire_lock_inherits_feed_alias_projects`: Kế thừa thành công từ các alias `tiktok-feed`, `multi-machine-feed-session`.
  3. `test_acquire_lock_other_parent_raises_needs_user_decision`: Bị từ chối fail-closed (ném `WorkflowError` mã `NEEDS_USER_DECISION`) khi project lạ chiếm lock.
  4. `test_acquire_lock_normal_success`: Chế độ acquire bình thường khi không xung đột lock.
  5. `test_acquire_lock_dry_run`: Chế độ dry run không acquire lock.
- **Canary Live Verification**:
  - Dùng máy rảnh (ví dụ Máy 2), acquire parent lock giả lập `project="tiktok-luot nuoi acc"`.
  - Khởi tạo StateMachine con chạy `_handle_acquire_locks()` -> assert `res is True` và `device_lease is None`.
  - Giải phóng parent lock an toàn ngay sau test.
