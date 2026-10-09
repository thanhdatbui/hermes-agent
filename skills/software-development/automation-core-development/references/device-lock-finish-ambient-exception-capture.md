# Bẫy sys.exc_info() Dead Code trong DeviceLock.finish() & Giải Pháp Ambient Exception Capture (07/09/2026)

## 1. Bản chất sự cố (Claude Opus High Audit - Round 2 REJECTED)

Trong `src/automation_core/device_lock.py`, hàm `finish()` chịu trách nhiệm dọn dẹp hoặc chuyển trạng thái lease khi một tác vụ kết thúc. 
Khi triển khai cơ chế re-raise lỗi release nếu caller không có exception gốc, code ban đầu viết:

```python
# ❌ LỖI DEAD CODE — NUỐT LỖI RELEASE VÔ ĐIỀU KIỆN
except (OSError, DeviceLockReleaseError) as exc:
    log.warning("device lock release failed in finish: %s", exc)
    if sys.exc_info()[1] is None:
        raise
```

### Tại sao điều kiện `sys.exc_info()[1] is None` là DEAD CODE?
Theo đặc tả ngữ nghĩa chuẩn của Python:
- Bên trong một khối `except ... as exc:`, `sys.exc_info()[1]` **LUÔN LUÔN trả về chính exception đang được khối `except` xử lý** (ở đây là chính instance `exc` thuộc kiểu `OSError` hoặc `DeviceLockReleaseError`).
- `sys.exc_info()[1]` bên trong khối `except` **KHÔNG BAO GIỜ bằng `None`**.
- Do đó, điều kiện `if sys.exc_info()[1] is None:` không bao giờ thỏa mãn (`False` 100%), và câu lệnh `raise` trở thành **dead code hoàn toàn không thể chạm tới**.

### Hậu quả thực tế:
1. Khi `finish(succeeded=True)` được gọi trong luồng chạy thành công (caller không hề có lỗi), nếu `self.release()` gặp `OSError` (ví dụ trên Windows dính `WinError 32` file lock đang bị process khác giữ):
   - Khối `except` bắt được exception, ghi 1 dòng log warning, nhưng **KHÔNG raise** (do dead code).
   - Khối `finally` (hoặc code dọn dẹp sau đó) coi như đã release và clear bộ nhớ.
   - Nhưng **lock file vật lý vẫn mồ côi nằm trên đĩa**, và caller không hề nhận được bất kỳ exception nào.
2. **Mâu thuẫn với `__exit__`:** `DeviceLock.__exit__` surface lỗi release ầm ĩ khi thoát sạch (`exc_type is None`), trong khi `finish()` (entrypoint chính của legacy callers) lại âm thầm nuốt sạch lỗi.

---

## 2. Giải pháp Chuẩn: Chụp `ambient_exc` Trước Khối `try`

Để biết caller có đang trong quá trình unwind exception hay không, **BẮT BUỘC phải chụp exception của caller TRƯỚC KHI vào khối `try` nội bộ** (khi đó khối `except` nội bộ chưa active):

```python
# ✅ GIẢI PHÁP ĐÚNG CHUẨN (CLAUDE OPUS HIGH APPROVED)
def finish(self, *, succeeded: bool, failure_status: str = "handoff") -> None:
    if self.lease is None:
        return
    if not succeeded and self.status in {"recovery", "handoff", "blocked"}:
        return

    # Chụp exception "ambient" của caller TRƯỚC khi vào try nội bộ
    ambient_exc = sys.exc_info()[1]
    try:
        if self.lease is not None:
            self.lease.finish(succeeded=succeeded, failure_status=failure_status)
    except (OSError, DeviceLockReleaseError) as exc:
        log.warning("device lock release failed in finish: %s", exc)
        if ambient_exc is None:
            # Caller thoát sạch mà release bị lỗi -> BẮT BUỘC raise để surface lỗi
            raise
        return

    if self.lease is not None and self.lease.is_still_held():
        self.status = failure_status
        self.payload["status"] = failure_status
    else:
        self.lease = None
        self.acquired.clear()
```

---

## 3. Quy Tắc Khắc Cốt Ghi Tâm Cho Mọi Cleanup Method trong Python
- **Không bao giờ dùng `sys.exc_info()[1] is None` bên trong một khối `except`** với kỳ vọng kiểm tra "caller có lỗi không". Khối `except` kích hoạt đồng nghĩa `sys.exc_info()[1]` đã bị gán exception hiện tại.
- Mọi hàm cleanup / context manager / finish muốn phân biệt giữa "caller đang unwind exception" vs "caller thoát bình thường":
  1. `ambient_exc = sys.exc_info()[1]` đặt ở dòng đầu tiên trước bất kỳ khối `try` nào.
  2. Trong khối `except (CleanupError, ...):` kiểm tra `if ambient_exc is None: raise`.
- Viết unit test bắt buộc assert: khi gọi `finish(succeeded=True)` mà `release()` ném `OSError`, phương thức `finish()` PHẢI re-raise `OSError` chứ không được nuốt.
