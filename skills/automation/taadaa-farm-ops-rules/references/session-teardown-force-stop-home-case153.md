# Teardown Force-Stop TikTok Về HOME Toàn Diện Cho Multi-Machine Feed Session (Case 153 - 12/09/2026)

## 1. Bối Cảnh & Vấn Đề Thực Tế
- Sau khi kết thúc phiên nuôi acc (Ca 2 chiều 12/09), quan sát màn hình nhiều máy vẫn hiển thị video đang phát trên feed, trang profile cá nhân hoặc thư viện gallery thay vì quay về màn hình HOME.
- Việc để app TikTok/thư viện ngâm trên màn hình sau phiên:
  - Khiến TikTok dễ phát hiện hành vi bot treo màn hình bất thường.
  - Sáng màn hình liên tục làm nóng máy, chai pin trên dàn máy farm.
  - Vi phạm nguyên tắc: **Kết thúc phiên nuôi bắt buộc phải force-stop TikTok và đưa máy về HOME**.

## 2. Nguyên Nhân Kỹ Thuật (Anti-Pattern)
1. **Lệch pha giữa Feed Session và Subprocess Hook**:
   - `feed_session_smoke` trong `feed_swipe_smoke.py` có gọi `cleanup_close_all_after_session(child_ctx)` về HOME.
   - Nhưng ngay sau đó, `multi_machine_feed_session.py` tiếp tục gọi `_run_follow_hook` và `_run_upload_hook`. Cả 2 hook này đều kích hoạt lại app TikTok / gallery.
   - Khi hook chạy xong (hoặc gặp manual review / lỗi script / skipped), không có bước dọn dẹp app.
2. **Missing Function Call (Nuốt ngoại lệ NameError)**:
   - Dòng 2414 trong `_run_follow_hook` có gọi:
     ```python
     _force_stop_tiktok_and_home(child_ctx, serial=account.serial)
     ```
     nhưng hàm này **chưa từng được định nghĩa** trong file! Do nằm trong khối `try...except Exception: pass`, lỗi `NameError` bị nuốt im lặng hoàn toàn.
3. **Thiếu Teardown trong khối `finally:`**:
   - Khối `finally:` ở cuối `_run_child` trước khi nhả lease thiết bị hoàn toàn không có bước dọn dẹp màn hình.

## 3. Quy Chuẩn Kỹ Thuật Triển Khai (Case 153)

### A. Định Nghĩa Hàm `_force_stop_tiktok_and_home`
```python
def _force_stop_tiktok_and_home(
    child_ctx: Any | None = None,
    *,
    serial: str | None = None,
    adb_path: str | None = None,
) -> None:
    """Force-stop TikTok package and return device to Android Home screen.

    Prevents devices from sitting on feed/profile/gallery screens after session ends.
    """
    target_package = "com.ss.android.ugc.trill"
    if child_ctx is not None and hasattr(child_ctx, "config") and isinstance(child_ctx.config, dict):
        target_package = str(child_ctx.config.get("tiktok_package", target_package))

    # 1. Via child_ctx.adb if available
    adb_client = getattr(child_ctx, "adb", None) if child_ctx is not None else None
    if adb_client is not None and hasattr(adb_client, "shell"):
        try:
            adb_client.shell(["am", "force-stop", target_package], timeout=15)
        except Exception:
            pass
        try:
            adb_client.shell(["input", "keyevent", "3"], timeout=15)
        except Exception:
            pass
        return

    # 2. Fallback via serial and adb subprocess
    if serial:
        resolved_adb = adb_path or r"C:/Program Files (x86)/xiaowei/tools/adb.exe"
        try:
            subprocess.run([resolved_adb, "-s", serial, "shell", "am", "force-stop", target_package], timeout=15, capture_output=True)
        except Exception:
            pass
        try:
            subprocess.run([resolved_adb, "-s", serial, "shell", "input", "keyevent", "3"], timeout=15, capture_output=True)
        except Exception:
            pass
```

### B. Chèn Teardown Bắt Buộc Trong `_run_child`
Tại khối `finally:` của `_run_child` (ngay trước khi nhả lease thiết bị):
```python
    finally:
        # Teardown safety: Clear cache hook
        ...
        # Teardown: Force-stop TikTok and return device to HOME screen
        try:
            _force_stop_tiktok_and_home(child_ctx, serial=account.serial)
        except Exception:
            pass

        lease = lock_holder.get("lease")
```

### C. Lưu Ý Khi Viết Patch Raw String
- Khi patch file có chuỗi raw string Windows path (như `r"D:\Taadaa\..."`), một số công cụ patch có thể escape `\r` thành ký tự xuống dòng gây `SyntaxError`.
- Giải pháp: Thu hẹp anchor để không đụng vào các dòng raw string không liên quan, hoặc dùng các dòng context liền kề không chứa raw string path.
