# Upload Hook: Kế thừa Device Lock từ Parent Feed Session (Case LOCK-05)

## Bối cảnh
Khi `multi_machine_feed_session.py` giữ device lock (`project="tiktok-luot nuoi acc"`) rồi gọi subprocess upload (`scripts.tiktok_workflow`), tiến trình con chạy `_handle_acquire_locks()` trong `state_machine.py`. Do thiết bị đang bị lock bởi parent, `automation_core` văng `DeviceLockNeedsUserDecision`, dẫn đến 100% upload fail với `NEEDS_USER_DECISION`.

## Root Cause Pattern
Đây là biến thể upload của Case LOCK-05 (đã có trong tiktok-follow). Uploader cần được phép kế thừa lock khi parent là feed session hợp lệ.

## Fix chuẩn (state_machine.py `_handle_acquire_locks`)
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

## Pitfall: Monkeypatch namespace
Test kế thừa PHẢI monkeypatch `tiktok_workflow.state_machine.acquire_device_lock`, KHÔNG patch `automation_core.device_lock.acquire_device_lock`. Direct import trong state_machine.py tạo reference riêng; patch sai namespace khiến mock không bao giờ được gọi.

```python
# ✅ ĐÚNG
from tiktok_workflow import state_machine
monkeypatch.setattr(state_machine, "acquire_device_lock", mock_acquire)

# ❌ SAI — mock không được gọi
import automation_core.device_lock
monkeypatch.setattr(automation_core.device_lock, "acquire_device_lock", mock_acquire)
```

## Focused Tests sau khi fix
```
pytest tests/test_tiktok_workflow.py::TestStateMachine::test_acquire_lock_reconciles_stale_proxy_marker_with_live_vpn
pytest tests/test_tiktok_workflow.py::TestStateMachine::test_acquire_lock_inherits_parent_feed_session_lock
pytest tests/test_tiktok_workflow.py::TestStateMachine::test_recovery_mode_allows_explicit_dead_owner_takeover
```
Yêu cầu: 3/3 PASSED + `py_compile` sạch.

## Allowlist project (kế thừa lock an toàn)
- `tiktok-luot nuoi acc`
- `tiktok-feed`
- `multi-machine-feed-session`

Project ngoài danh sách → vẫn fail-closed `NEEDS_USER_DECISION`.

## Verification sau fix (2026-09-25)
- Bằng chứng thực tế: 50/80 máy Farm Kibe gặp lỗi upload đúng pattern này trong Ca 1
- 3/3 focused tests PASSED trong 24.05s
- `py_compile` OK
- Chưa commit/push theo user policy
