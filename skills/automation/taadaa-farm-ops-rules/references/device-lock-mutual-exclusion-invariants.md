# Hard Invariant: Device Lock Mutual Exclusion & Hands-off Policy (2026-09-21)

## 1. Bản chất sự cố Máy 42 (Root Cause)
- Khi một máy đang chạy flow khác (ví dụ: `tiktok-add-bao-mat-f2a` đang ở màn hình "Thiết lập xác minh 2 bước" Authenticator App), Coordinator tự tiện phán đoán là "màn hình kẹt" rồi ra lệnh `force-stop` và bấm `HOME`.
- Đồng thời Coordinator tự ý giải phóng `release_machine_reg_reservation` bẻ gãy cơ chế lock mà user thiết kế.

## 2. Nguyên tắc bất khả xâm phạm (Hands-off Invariant)
1. **Lock là tường lửa tuyệt đối:**
   - Máy đang có lock active (`machine_<N>.lock.json` hoặc đang trong flow của script khác) $\rightarrow$ **CẤM TUYỆT ĐỐI** Coordinator/Worker gửi bất kỳ lệnh can thiệp nào (`am force-stop`, `tap`, `swipe`, `keyevent`, `release_lock`).
   - Process nào tạo lock thì chỉ DUY NHẤT process đó (PID đó) mới có quyền release khi hoàn tất.
2. **Màn hình lạ ≠ Treo/Kẹt:**
   - Thấy màn hình không thuộc flow hiện tại: BẮT BUỘC DỪNG LẠI (`Freeze → Report → Wait`), cấm tự ý dọn dẹp hoặc kill app.
3. **Cơ chế Reaper Cron 1h:**
   - Hệ thống đã có script reaper (`reap-dead-owner-locks.py`, TTL 3600s). Nếu máy thật sự bị treo hoặc process chết quá 1 tiếng, reaper cron sẽ tự động dọn dẹp và đưa máy về Home an toàn.
   - Coordinator/Worker không được tự ý can thiệp tranh quyền của Reaper.
4. **Vá lỗ hổng cờ `DEVICE_LOCK_ENABLED` trong `social_reg_v1.py`:**
   - `social_reg_v1.py` không được phép dùng cờ opt-in `os.environ.get("DEVICE_LOCK_ENABLED")` để bypass lock.
   - Mọi lần khởi chạy `social_reg_v1.py` (kể cả chạy lệnh CLI đơn lẻ) BẮT BUỘC phải acquire `device_lock` của `automation-core`. Nếu máy bị khóa bởi tiến trình khác $\rightarrow$ Safe-Skip dừng ngay lập tức.
