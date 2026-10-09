# Pitfalls: Watchdog Session Reporting & Safe-Skip Classification

## 1. Follow Mode 2: Anchor thiếu video là SKIPPED, cấm MANUAL_REVIEW
- **Hiện tượng**: Báo cáo watchdog tổng kết ca nuôi hiển thị hàng chục máy (20-35 máy) bị gom vào `Lỗi script/xác minh`.
- **Nguyên nhân**: Trong `mode2_follow_followers.py`, khi anchor không có video (`reason: anchor @... không có video — back ra bỏ qua`), runner trả về `res.status = "MANUAL_REVIEW"` và `res.failed = True`.
- **Hệ quả**: Watchdog kiểm tra nếu `status != "SKIPPED"` và `status != "FOLLOW_FAILED"` thì tự động đẩy vào danh sách `fl_error` (Lỗi script/xác minh), gây sai lệch số liệu vận hành và báo động giả.
- **Quy tắc**: Khi anchor thiếu video hoặc không tìm thấy video hợp lệ, flow đã back ra an toàn thì BẮT BUỘC gán `res.status = "SKIPPED"` và `res.failed = False`.

## 2. Watchdog Upload Hook: Race Condition chốt sớm khi video đang upload nền
- **Hiện tượng**: Báo cáo phiên ghi nhận 27 máy "Lỗi script/xác minh" ở mục Đăng Video, nhưng chỉ 5-10 phút sau kiểm tra thực tế thì số máy upload thành công tăng từ 46 lên 62+.
- **Nguyên nhân**:
  - Watchdog kiểm tra điều kiện chốt phiên dựa trên tiến trình Feed runner (`is_feed_runner_active()`).
  - Khi Feed runner hoàn tất lượt swipe và nhả quyền, các subprocess upload hook nền (`run_post.py` / video upload pipeline) của một số máy vẫn đang chạy hoặc đang chờ ghi `upload_result.json`.
  - Logic fallback của watchdog: nếu máy có Feed `success` nhưng chưa có file `upload_result.json` tại thời điểm quét thì tự động xem là upload lỗi (`up_error.append(m)`).
- **Quy tắc chốt phiên an toàn**:
  - Watchdog phải kiểm tra process upload nền (`run_post` / `upload_worker`) hoặc kiểm tra timestamp run manifest.
  - Phải có grace period (5-10 phút) chờ upload hook hoàn tất trước khi chốt hạ số liệu đăng video của phiên.
