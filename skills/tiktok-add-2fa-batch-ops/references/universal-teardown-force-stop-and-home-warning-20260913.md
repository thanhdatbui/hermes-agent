# Case 55: Universal Teardown Force-Stop TikTok & Return Home Trong Khối Finally Của Entrypoint Phase B

## Metadata
- **Thời gian xử lý:** 13/09/2026
- **Vị trí áp dụng:** `python_runner/run_capture_phase_b.py` trong hàm `main()`.
- **Docs liên quan:** `docs/farm-automation-cases.md`, `docs/uiautomator.md`.

## Bối cảnh & Hiện tượng thực tế (Anti-Pattern)
1. Trong entrypoint chạy live Phase B (`run_capture_phase_b.py`), khối `finally:` ban đầu chỉ gọi duy nhất `lease.finish(succeeded=goal_completed)`.
2. Hoàn toàn không có lệnh đóng app TikTok hay đưa màn hình thiết bị về Home khi kết thúc hoặc khi gặp ngoại lệ (`AccountPreflightError`, `LiveAdapterError`, `UIDumpError`...).
3. Hậu quả: Sau mỗi ca chạy 2FA (dù thành công hay thất bại), ứng dụng TikTok vẫn bị treo lơ lửng trên foreground màn hình máy thật. Điều này gây xung đột với các ca nuôi cron kế tiếp (đặc biệt khi cron feed session kiểm tra màn hình hoặc kiểm soát focus).
4. Anti-Pattern khi vá teardown: Teardown câm lặng (`check=False` kèm `except: pass`) khiến lỗi ADB hoặc ngoại lệ khi force-stop/về Home bị nuốt chửng, không có tín hiệu chẩn đoán nào trên log.

## Giải pháp chuẩn (Case Fix)
Tách logic teardown thành hàm riêng biệt `teardown_app_to_home(adapter, tiktok_package: str) -> bool` có guard `adapter is None`, thực hiện đóng app TikTok và đưa máy về Home bằng `input keyevent 3`. Đồng thời log cảnh báo ra `sys.stderr` nếu lệnh shell không thành công hoặc xảy ra ngoại lệ, nhưng luôn đảm bảo giải phóng device lock trong khối `finally:`:

```python
def teardown_app_to_home(adapter, tiktok_package: str) -> bool:
    """Best-effort teardown: force-stop TikTok and send KEYCODE_HOME.
    Returns True if both shell commands succeeded, False if any failed or raised.
    """
    if adapter is None or getattr(adapter, "adb", None) is None:
        return False
    try:
        res1 = adapter.adb.shell(["am", "force-stop", tiktok_package], check=False)
        res2 = adapter.adb.shell(["input", "keyevent", "3"], check=False)
        ok = bool(getattr(res1, "ok", True) and getattr(res2, "ok", True))
        if not ok:
            sys.stderr.write(f"[TEARDOWN_WARN] force-stop or home failed: {getattr(res1, 'error', '')} {getattr(res2, 'error', '')}\n")
        return ok
    except Exception as _td_exc:
        sys.stderr.write(f"[TEARDOWN_WARN] exception during teardown: {_td_exc}\n")
        return False
```

Trong khối `finally:` của `run_capture_phase_b.py`:
```python
        finally:
            teardown_app_to_home(adapter, cfg.tiktok_package)
            lease.finish(succeeded=goal_completed)
```

## Kiểm Thử & Quy Tắc Tài Liệu
- **Bắt buộc viết Unit Test:** Module `python_runner/tests/test_run_capture_phase_b.py` kiểm thử đủ 3 nhánh:
  1. `test_teardown_app_to_home_success`: ADB thực thi thành công trả về `True` và gọi đủ `force-stop` + `keyevent 3`.
  2. `test_teardown_app_to_home_adb_failure`: ADB trả về `ok=False` (ví dụ device offline) ghi log warning, trả về `False` fail-safe.
  3. `test_teardown_app_to_home_exception`: ADB văng `RuntimeError` bắt trọn ngoại lệ, ghi log warning và trả về `False`.
- **Chuẩn hóa tài liệu hóa:** Tránh dùng các khẳng định tuyệt đối chưa qua kiểm chứng ("đảm bảo 100% app luôn đóng"); dùng thuật ngữ chuẩn "Best-effort & fail-safe teardown" kèm dẫn chứng unit test thực tế.
- Giữ vững kỷ luật: teardown có logging rõ ràng (`[TEARDOWN_WARN]`), không swallow lỗi ADB trong im lặng nhưng tuyệt đối không được để lỗi teardown chặn việc nhả device lock lease.
