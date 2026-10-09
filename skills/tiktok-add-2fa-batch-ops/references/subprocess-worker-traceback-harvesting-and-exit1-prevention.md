# Subprocess Worker Traceback Harvesting & WORKER_EXIT_1 Prevention

Đúc kết từ bài toán vận hành batch Phase 3 (Add 2FA TikTok) trên đàn 40 máy ngày 08/09/2026: 11/40 máy (27.5%) gặp lỗi generic `WORKER_EXIT_1`.

---

## 1. Cơ chế phát sinh hiện tượng "Mù lỗi WORKER_EXIT_1"
1. **Thiếu Catch-All Exception tại entrypoint subprocess con:**
   - Trong `python_runner/run_capture_phase_b.py`, hàm `main()` chỉ có các khối `except`:
     - `UIDumpError`
     - `AccountPreflightError`
     - `LiveAdapterError`
     - `(OSError, RuntimeError)`
   - Khi gặp các exception như `ConsumerPreflightError` (từ `automation_core.preflight` khi VPN Vichanger chưa up/live-ip không đạt), `AdbError`, `KeyError`, `ValueError`, tiến trình con bị unhandled exception $\rightarrow$ in traceback ra stderr và thoát với returncode 1 mà không in dòng JSON kết quả.
2. **Hàm bóc tách của parent runner chỉ quét JSON:**
   - Trong `run_batch_live_2fa.py`, hàm `_parse_worker_output(output, returncode)` duyệt ngược các dòng trong `output` để tìm `json.loads(line)`.
   - Nếu worker con crash do unhandled exception, không có dòng JSON nào được in ra $\rightarrow$ hàm fallback về `"failed", f"WORKER_EXIT_{returncode}"`.
   - Toàn bộ nội dung stdout/stderr chứa traceback thực tế bị nuốt mất, khiến báo cáo cuối batch hiển thị một danh sách dài `WORKER_EXIT_1` mà không rõ nguyên nhân.

---

## 2. Giải pháp 2 tầng bắt buộc

### Tầng 1: Worker con luôn xuất JSON kết quả (Catch-All Exception)
Tại cuối chuỗi `except` trong `run_capture_phase_b.py`:
```python
except Exception as exc:
    print(json.dumps({
        "status": "failed",
        "reason": f"{type(exc).__name__}: {str(exc)[:120]}"
    }, ensure_ascii=False))
    return 1
```

### Tầng 2: Parent runner bóc tách lỗi thật từ stdout/stderr khi thiếu JSON
Tại `_parse_worker_output` trong `run_batch_live_2fa.py`:
```python
def _parse_worker_output(output: str, returncode: int) -> tuple[str, str]:
    # 1. Tìm JSON payload hợp lệ
    for line in reversed(output.splitlines()):
        try:
            payload = json.loads(line)
            if isinstance(payload, dict) and payload.get("status"):
                return str(payload["status"]), str(payload.get("reason") or "")
        except (TypeError, json.JSONDecodeError):
            continue

    # 2. Fallback khi worker crash (không có JSON): Bóc tách lỗi thực tế từ output
    extracted_error = ""
    lines = [l.strip() for l in output.splitlines() if l.strip()]
    for line in reversed(lines):
        if any(marker in line for marker in ("Error:", "Exception:", "Traceback", "FAILED")):
            extracted_error = line
            break
    if not extracted_error and lines:
        extracted_error = lines[-1]

    clean_reason = f"WORKER_CRASH: {extracted_error[:80]}" if extracted_error else f"WORKER_EXIT_{returncode}"
    return "failed", clean_reason
```
Nhờ đó, mã lỗi generic `WORKER_EXIT_1` được chuyển thành lỗi tường minh (ví dụ: `WORKER_CRASH: ConsumerPreflightError: Vichanger VPN not connected`).
