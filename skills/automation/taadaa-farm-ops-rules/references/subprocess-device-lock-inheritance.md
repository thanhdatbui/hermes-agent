# Subprocess Device Lock Inheritance & Monkeypatch Pitfall

## Bối cảnh & Pattern lỗi
Khi một parent automation runner (ví dụ `multi_machine_feed_session.py` thuộc `tiktok-luot nuoi acc`) giữ `DeviceLock` trên thiết bị và gọi subprocess con (như `scripts.tiktok_workflow` trong `Tiktok-video`), subprocess con cố gắng gọi `acquire_device_lock(user_authorized=False)`.
Vì thiết bị đang bị lock bởi chính parent, `automation-core` văng ngoại lệ `DeviceLockNeedsUserDecision`, làm 100% các subprocess bị abort với `NEEDS_USER_DECISION`.

## Giải pháp chuẩn: Kế thừa Lock Fail-Closed
Trong state machine hoặc preflight gate của subprocess:
1. Bắt `DeviceLockNeedsUserDecision as e`.
2. Kiểm tra `parent_project = str((getattr(e, "owner", None) or {}).get("project") or "").strip().lower()`.
3. Chỉ kế thừa (`self.context.device_lease = None` và tiếp tục) nếu `parent_project` nằm trong danh sách allowlist cha hợp lệ:
   - `tiktok-luot nuoi acc`
   - `tiktok-feed`
   - `multi-machine-feed-session`
4. Nếu thuộc project khác hoặc user lock: Bắt buộc fail-closed bằng `WorkflowError(NEEDS_USER_DECISION)` để bảo vệ thiết bị.

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

## Pitfall: Monkeypatch Namespace khi Direct Import
Khi unit test một hàm được import trực tiếp (`from automation_core.device_lock import acquire_device_lock`), module mục tiêu đã giữ reference riêng đến hàm đó trong namespace của mình.
- ❌ **Sai:** `monkeypatch.setattr(automation_core.device_lock, "acquire_device_lock", mock_acquire)` -> Module mục tiêu vẫn gọi reference cũ, mock không được kích hoạt.
- ✅ **Đúng:** `monkeypatch.setattr(target_module, "acquire_device_lock", mock_acquire)` -> Thay thế chính xác reference trong namespace của module đang test.
