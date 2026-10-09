# Live Canary Fallback Verification & Timeout Alignment

## Bối cảnh & Bài học thực tế (05/10/2026)
Trong phiên kiểm nghiệm luồng Partial Fallback từ Mode 2 sang Mode 1 (`D:/Taadaa/tiktok-follow`), Coordinator đã phạm 2 lỗi nghiêm trọng bị User khiển trách:
1. **Lấy ảnh màn hình Home Launcher làm bằng chứng nghiệm thu:** Script chạy xong đã gọi `cleanup_after_result` đóng app về Launcher. Chụp ảnh Home không chứng minh được bất kỳ thao tác nào diễn ra trên TikTok.
2. **Ngộ nhận cờ chuyển nhánh (`fallback: true`) là Canary thành công:** Khi Mode 2 cạn anchor, cờ `mode2_fallback_to_mode1: true` được bật và runner trả về `status: OK`, nhưng thực tế `mode1_followed_count: 0` (Module 1 chưa hề follow được ai).

## Nguyên nhân gốc (Root Cause)
1. **Mismatch giữa Machine Config và Execution Deadline Guard:**
   - 16 file `config/machine*.yaml` lưu giá trị cũ: `feed_timeout_seconds: 90`.
   - Trong code `follow_engine.py` (dòng 876) và `mode1_search_follow.py` (dòng 51):
     - `has_time_for_next_action(reserve_seconds=120.0)`
     - `has_time_for_next_action(reserve_seconds=180.0)`
   - Công thức: `remaining = feed_timeout_seconds - elapsed`.
   - Khi `feed_timeout_seconds = 90`, ngay tại giây thứ 0 thì `remaining <= 90 < 120`. Hàm luôn trả `False`.
   - Module 1 bị deadline starvation chặn đứng ngay lập tức trước khi kịp mở tìm kiếm.
2. **Khắc phục chuẩn:**
   - Đồng bộ toàn bộ `machine*.yaml` về `feed_timeout_seconds: 1200` (20 phút chuẩn toàn farm).
   - Thêm regression test `test_config.py` kiểm tra `feed_timeout_seconds >= 1200.0`.

## Tiêu chí nghiệm thu Live Canary hợp lệ (Strict Canary Acceptance Gate)
1. **CẤM nghiệm thu bằng cờ trạng thái:** `mode2_fallback_to_mode1: true` chỉ chứng minh logic rẽ nhánh được gọi. Phải có `mode1_followed_count > 0` hoặc bằng chứng search UID thành công trên thiết bị mới được kết luận Module 1 hoạt động.
2. **CẤM nghiệm thu bằng ảnh Home/Teardown:**
   - Tuân thủ tuyệt đối quy tắc `CAPTURE-BEFORE-CLEANUP` (trong `taadaa-farm-ops-rules`).
   - Ảnh chụp phải ở màn hình TikTok (Search, Profile của đối tượng, hoặc danh sách Đang follow) TRƯỚC KHI app bị đóng.
3. **Phân biệt Exit 0 vs Task Completion:**
   - Exit code 0 của runner chỉ mang ý nghĩa script không bị crash unhandled exception.
   - Task chỉ thành công khi đạt số lượt follow mục tiêu (`followed_count > 0`). Nếu `followed_count == 0` sau fallback, phải coi là `CANARY_UNVERIFIED` hoặc `CANARY_FAILED` để điều tra tiếp.
