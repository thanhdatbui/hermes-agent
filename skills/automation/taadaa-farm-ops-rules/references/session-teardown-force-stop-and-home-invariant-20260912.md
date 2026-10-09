# Bắt Buộc Force-stop TikTok & Đưa Máy Về HOME Khi Kết Thúc Phiên (Chốt 12/09/2026)

## 1. Bối Cảnh & Vấn Đề
- Sau khi hoàn tất phiên nuôi acc (Ca 2 kết thúc lúc 14:30), màn hình nhiều máy vẫn dừng lại ở video Feed, trang Profile hoặc thư viện ảnh/Gallery.
- Hành vi dừng ngâm ở màn hình Feed/Profile khiến thiết bị sáng màn hình liên tục, dễ bị hệ thống TikTok nhận diện bot và gây nóng máy/chai pin.
- **Quy tắc thiết kế tối cao của User**: Xong phiên bắt buộc phải close TikTok và đưa thiết bị về màn hình HOME, tuyệt đối cấm dừng ở trang Feed/Gallery.

## 2. Nguyên Nhân Gốc (Root Cause)
1. **Thứ tự thực thi luồng**:
   - `feed_session_smoke` có gọi `cleanup_close_all_after_session(child_ctx)` về HOME sau khi lướt feed.
   - Nhưng sau đó, runner `multi_machine_feed_session.py` chạy tiếp các hook phụ trợ:
     - `_run_follow_hook` (chạy `run_follow.py`): Mở lại TikTok để verify identity / follow. Khi gặp `MANUAL_REVIEW` hoặc timeout, nó không đưa máy về HOME.
     - `_run_upload_hook` (chạy `Tiktok-video`): Mở TikTok và Gallery để upload.
2. **Lỗi nuốt exception hàm thiếu**:
   - Dòng 2414 của `multi_machine_feed_session.py` có gọi `_force_stop_tiktok_and_home(child_ctx, serial=account.serial)`.
   - Tuy nhiên hàm `_force_stop_tiktok_and_home` chưa từng được định nghĩa trong file, dẫn đến việc bắn `NameError` và bị khối `except Exception: pass` nuốt im lặng.
3. **Thiếu Teardown ở cấp độ Machine Session**:
   - Trong khối `finally:` của `_run_child`, runner chỉ kiểm tra clear cache và nhả lease, hoàn toàn thiếu bước dọn dẹp cuối cùng để force-stop TikTok và bấm phím Home.

## 3. Quy Chuẩn Kỹ Thuật Bắt Buộc (Code Invariant)

1. **Định nghĩa chuẩn `_force_stop_tiktok_and_home`**:
   - Bắt buộc hỗ trợ cả `child_ctx.adb` lẫn fallback qua ADB subprocess theo serial:
   ```python
   def _force_stop_tiktok_and_home(
       child_ctx: Any | None = None,
       *,
       serial: str | None = None,
       adb_path: str | None = None,
   ) -> None:
       """Force-stop TikTok package and return device to Android Home screen."""
       target_package = "com.ss.android.ugc.trill"
       if child_ctx is not None and hasattr(child_ctx, "config") and isinstance(child_ctx.config, dict):
           target_package = str(child_ctx.config.get("tiktok_package", target_package))

       # 1. Via child_ctx.adb
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
           resolved_adb = adb_path or r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
           try:
               subprocess.run([resolved_adb, "-s", serial, "shell", "am", "force-stop", target_package], timeout=15, capture_output=True)
           except Exception:
               pass
           try:
               subprocess.run([resolved_adb, "-s", serial, "shell", "input", "keyevent", "3"], timeout=15, capture_output=True)
           except Exception:
               pass
   ```

2. **Gọi bắt buộc trong `finally:` của `_run_child`**:
   - Trước khi release device lock lease, phải bọc `try: _force_stop_tiktok_and_home(child_ctx, serial=account.serial) except Exception: pass`.
   - Đảm bảo bất kể phiên thành công, thất bại, skip hay timeout ở bất kỳ hook nào, máy luôn được trả về màn hình chính (Android Launcher Home).
