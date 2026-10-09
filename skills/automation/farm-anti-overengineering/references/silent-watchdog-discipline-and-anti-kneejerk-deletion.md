# Silent Watchdog Discipline & Anti-Kneejerk Deletion Safeguards

## 1. Bản chất sự cố (Root Cause)
1. **Lỗi báo cáo rỗng trên Cron `no_agent=True`**:
   - Khi cronjob có `no_agent=True` và đích gửi `deliver: telegram:...`, scheduler của Hermes tự động coi mọi ký tự in ra `stdout` (`sys.stdout`) là nội dung báo cáo cần gửi tới người dùng.
   - Nếu script gặp trường hợp không có dữ liệu cần xử lý (ví dụ: `Tổng máy đủ điều kiện: 0`, `candidates = []`, hoặc chưa đến điều kiện kích hoạt) mà vẫn `print()` template báo cáo ra stdout, Hermes sẽ chuyển tiếp tin nhắn rỗng lên Telegram gây spam định kỳ (mỗi 2-5 phút).
2. **Sai lầm tâm lý vội vàng (Knee-jerk Reaction)**:
   - Khi người dùng gửi lại tin nhắn báo cáo kèm biểu hiện bực bội hoặc hỏi lí do lỗi, Coordinator suy diễn hấp tấp là người dùng muốn xóa bỏ cronjob đó, dẫn đến hành động xóa nhầm (`cronjob remove`) tính năng cốt lõi của hệ thống thay vì đi tìm nguyên nhân tại sao kết quả lại ra 0.

## 2. Quy tắc bắt buộc cho Silent Watchdog (Silent-by-Default)
- **Chuẩn im lặng tuyệt đối khi không có hành động**:
  - Khi chưa tới khung giờ, chưa kết thúc ca nuôi feed, các máy đang bận lock, hoặc danh sách ứng viên/thiết bị cần xử lý là rỗng (`len(candidates) == 0` / `len(eligible) == 0`):
  - **BẮT BUỘC thoát ngay bằng `return 0` hoặc `sys.exit(0)` mà KHÔNG `print()` bất kỳ ký tự nào ra `stdout`**.
  - Toàn bộ log tiến trình, debug hoặc cảnh báo trung gian PHẢI ghi ra `sys.stderr` (`sys.stderr.write(...)`), tuyệt đối không dùng `print()`.
- **Chỉ in ra stdout khi có kết quả thực thi thật**:
  - Chỉ khi có ít nhất 1 thiết bị/tài khoản thực sự được xử lý (`len(success_list) > 0 or len(fail_list) > 0`), script mới được phép `print()` bảng tổng kết ra `stdout` để chuyển tiếp Telegram.

## 3. Quy tắc thẩm định trước khi thao tác Cronjob (Anti-Kneejerk Rule)
- Khi người dùng quote/forward lại một bản tin báo cáo lỗi hoặc báo cáo rỗng:
  - **CẤM TUYỆT ĐỐI tự ý gọi `cronjob remove`** khi người dùng chưa ra lệnh rõ ràng bằng các từ khóa tường minh ("xóa cron X", "tắt vĩnh viễn job Y").
  - Phải phân tích đúng bản chất: Người dùng đang chất vấn về **NỘI DUNG BÁO CÁO** (tại sao ra 0 máy, tại sao lỗi), chứ không phải yêu cầu xóa bỏ hệ thống giám sát.
- **Xác định đường dẫn nhị phân thiết bị (ADB Path Isolation)**:
  - Trong các script chạy ngầm qua cron/scheduler, `PATH` môi trường có thể bị sanitized hoặc trỏ vào binary ADB rác.
  - BẮT BUỘC sử dụng đường dẫn nhị phân tuyệt đối đã kiểm chứng: `C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe` thay vì gọi `adb` trần qua shell.
