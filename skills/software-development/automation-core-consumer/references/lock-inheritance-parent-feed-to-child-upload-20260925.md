# Case LOCK-05: Kế Thừa Device Lock Từ Parent Feed Session Sang Child Upload/Follow Runner

## 1. Hiện tượng & Triệu chứng Hiện trường
Khi runner nuôi feed cha (`multi_machine_feed_session.py`, project `tiktok-luot nuoi acc`) gọi hook tiến trình con (`scripts.tiktok_workflow` upload video hoặc `tiktok-follow` follow chéo):
- Toàn bộ các máy được kích hoạt hook đồng loạt fail với lỗi:
  ```text
  status: "failed"
  reason: "[FAILED] [NEEDS_USER_DECISION] ACQUIRE_LOCKS: Cần user quyết định cho device lock: device needs user decision (locked by another owner): path=...machine_N.lock.json pid=XXXX project=tiktok-luot nuoi acc status=running"
  ```
- **Bản chất lỗi:**
  - Luồng cha đang giữ device lock hợp lệ cho thiết bị `machine_N`.
  - Tiến trình con khi khởi động gọi `acquire_device_lock(user_authorized=False)`.
  - `automation_core.device_lock` phát hiện thiết bị đang có owner khác (`tiktok-luot nuoi acc`), raise ngoại lệ `DeviceLockNeedsUserDecision`.
  - Tiến trình con không bắt ngoại lệ để nhận diện context kế thừa, tự fail-closed ném `WorkflowError` và hủy 100% lượt chạy.

---

## 2. Giải pháp Chuẩn (Lock Inheritance Contract)
Bắt ngoại lệ `DeviceLockNeedsUserDecision` trong bước `ACQUIRE_LOCKS` (`_handle_acquire_locks` trong `state_machine.py` hoặc tương đương). Nếu owner của lock thuộc nhóm parent feed session:
1. Ghi log rõ ràng `[LOCK-INHERIT] Kế thừa device lock từ parent project '<project>' (pid=<pid>) cho machine=<machine>, serial=<serial>`.
2. Gán `self.context.device_lease = None` (để khi teardown child không vô tình release nhầm lease của parent).
3. Cho phép workflow tiếp tục (`return True`).
4. Với mọi owner khác ngoài danh sách hợp lệ: vẫn raise `DeviceLockNeedsUserDecision` / `WorkflowError` (bảo vệ an toàn fail-closed).

### Danh sách Parent Projects hợp lệ:
- `"tiktok-luot nuoi acc"`
- `"tiktok-feed"`
- `"multi-machine-feed-session"`

---

## 3. Code Mẫu Chuẩn (State Machine / Consumer)

```python
from automation_core.device_lock import DeviceLockNeedsUserDecision

# ...
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

---

## 4. Kiểm Thử Độc Lập (Unit Test & Live Canary)
- **Unit Test (Monkeypatch namespace):** Lưu ý import trong module test phải patch đúng namespace của module chứa hàm gọi (ví dụ `state_machine.acquire_device_lock` thay vì patch `automation_core.device_lock.acquire_device_lock` nếu đã dùng `from ... import acquire_device_lock`).
- **Live Canary Test:**
  1. Acquire parent lock với `bypass_proxy_readiness=True`, `project="tiktok-luot nuoi acc"`.
  2. Khởi tạo StateMachine con và gọi `_handle_acquire_locks()`.
  3. Xác nhận `res is True` và `machine.context.device_lease is None`.
  4. Release parent lock an toàn trong `finally:`.
