# Case 153: Enforce Force-Stop TikTok & Return Home Teardown across All Session Hooks

## 1. Context & Symptom
- **Triệu chứng:** Sau khi kết thúc phiên nuôi acc (ví dụ Ca 2 lúc 14:30), một loạt thiết bị điện thoại trên dàn farm vẫn dừng lại ở video feed đang phát, trang profile, hoặc thư viện gallery thay vì quay về màn hình chính (Android HOME Launcher).
- **Hậu quả:** Màn hình sáng ngâm lâu, tốn pin, máy nóng, và đặc biệt trông không tự nhiên, dễ bị phát hiện hành vi bot tự động.

## 2. Root Cause Analysis
1. **Lệch pha giữa Feed Session và các Hooks kế tiếp:**
   - Trong `feed_swipe_smoke.py`, hàm lướt feed đã có gọi `cleanup_close_all_after_session` để đóng app về HOME.
   - Tuy nhiên, trong `multi_machine_feed_session.py`, sau khi lướt feed xong thì runner gọi tiếp **Follow Hook** (`run_follow.py`) và **Upload Hook** (`Tiktok-video`). Cả 2 hook con này đều mở lại TikTok và Gallery.
2. **Hook kết thúc thiếu dọn dẹp:**
   - Khi hook chạy xong hoặc kết thúc do timeout / manual review, hook con không gửi lệnh đưa máy về HOME.
   - Tại dòng 2414 có lời gọi `_force_stop_tiktok_and_home(child_ctx, serial=account.serial)`, nhưng hàm này **chưa từng được định nghĩa** trong file, gây ra lỗi `NameError` và bị nuốt im lặng bởi khối `except Exception: pass`.
3. **Thiếu Teardown ở khối finally của máy:**
   - Khối `finally:` của `_run_child` trước khi nhả lease thiết bị không có bước dọn dẹp ứng dụng.

## 3. Solution Pattern
1. **Định nghĩa helper `_force_stop_tiktok_and_home` chuẩn xác:**
   - Lấy package đích từ `child_ctx.config.get("tiktok_package", "com.ss.android.ugc.trill")`.
   - Ưu tiên gọi qua `child_ctx.adb.shell(["am", "force-stop", target_package], timeout=15)` và `["input", "keyevent", "3"]`.
   - Fallback an toàn qua ADB subprocess với `serial` của máy khi context không có adb client.
   - Bọc riêng từng lệnh trong `try...except Exception: pass` độc lập để lệnh bấm HOME luôn chạy kể cả khi force-stop gặp lỗi.
2. **Bổ sung vào Teardown bắt buộc:**
   - Đặt lời gọi `_force_stop_tiktok_and_home` trong khối `finally:` của `_run_child` ngay trước khi nhả lease thiết bị (`lock_holder.get("lease")`).
   - Đảm bảo tính bất biến: Bất kể phiên nuôi thành công, thất bại hay gặp ngoại lệ, máy luôn được force-stop TikTok và quay về màn hình HOME 100%.

## 4. Verification Evidence
- Unit test `test_session_teardown_home.py` cover cả 2 nhánh (ADB client và Subprocess fallback) pass 100%.
- Kiểm tra toàn bộ 77 máy online: 100% máy được đưa về `com.sec.android.app.launcher.activities.LauncherActivity`.
