# Lease Release Resilience & Anti-Fail Override

## Bối cảnh & Hiện tượng (Case: lease_release_failed)
Trong `multi_machine_feed_session.py`, worker thực thi phiên lướt feed (`feed_session_smoke`) và các hook liên quan (upload hook, clear cache hook). 
Khi phiên lướt hoàn thành xuất sắc (`initial_goal_completed = True` và child flow status là `success`), luồng vào khối `finally` để giải phóng lease / device lock.

Trước đây, nếu quá trình giải phóng lease gặp trục trặc (`lease_release_failed = True` hoặc deadline publication bị ngắt giữa chừng), code sẽ nhảy vào khối `if not goal_completed:` hoặc `if lease_release_failed or (initial_goal_completed and not goal_completed):` và:
1. Đánh dấu lease thành `blocked`.
2. Ghi đè kết quả `child_result` thành `final_status="failed"` với `blocker_type="lease-finish-failed"`.
Điều này dẫn đến false alarm: phiên nuôi/lướt thực tế đã thành công mỹ mãn nhưng cả batch lại báo fail và chặn các vòng sau.

## Nguyên tắc xử lý chuẩn (Đã áp dụng trong multi_machine_feed_session.py)
1. **Bảo toàn trạng thái thành công (`initial_goal_completed == True`):**
   - Không được phép ghi đè kết quả thành công sang `failed` chỉ vì bước cleanup/release lease gặp warning/lỗi nhỏ.
   - Không đánh dấu lease thành `blocked` nếu session feed vốn dĩ đã hoàn thành tốt.
2. **Graceful Lease Cleanup & Logging:**
   - Log `[WARN]` cảnh báo để dev/operator nắm được hiện tượng giật lag lease release mà không gây fail session.
   - Thử gọi `lease.finish(succeeded=True)`, nếu vấp tiếp thì fallback gọi `lease.set_status("released")` để trả lock máy cho các tiến trình kế tiếp.
   - Giữ nguyên `goal_completed = True` và bảo lưu `child_result` thành công.
3. **Quy trình Canary Test B4 xác nhận:**
   - Sau khi sửa logic lease / multi-machine flow, BẮT BUỘC chạy Canary Test B4 với 1 máy (ví dụ Máy 51):
     ```powershell
     powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 51 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
     ```
   - Chụp screencap hiện trường sau khi chạy:
     ```bash
     adb -s <serial> exec-out screencap -p > "D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/screencap_m<N>.png"
     ```
   - Kiểm tra exit code = 0, `Status: success`, và ảnh chụp máy hiển thị trạng thái feed TikTok bình thường.
