# Case 80: Idempotency Post Scoping, UIAutomator Occlusion Recovery & Post Selectors

## 1. UIAutomator Helper Occlusion Recovery
Helper APK (`com.github.uiautomator`) có thể tự khởi chạy hoặc kẹt nền đè foreground của TikTok trong các state như `OPEN_TIKTOK`, `WAIT_FEED`, `ACCOUNT_SWITCHER`.
- **Triệu chứng:** Mất focus TikTok, timeout chờ feed hoặc account switcher do app helper chiếm màn hình.
- **Xử lý chuẩn:**
  1. Kiểm tra focused activity xem có chứa package `com.github.uiautomator` hay không.
  2. Gọi `adapter._adb.shell(["am", "force-stop", "com.github.uiautomator"], timeout=10, check=False)` để force-stop activity helper (không kill uiautomator server backend).
  3. Gọi `_bring_adapter_to_foreground` đưa TikTok trở lại foreground.

## 2. Idempotency Post Receipt Scoping (run_id + target_account)
- **Vấn đề:** Durable receipt từ phiên trước chứa `status: completed` hoặc `intent_pending` khiến lượt chạy mới trên cùng máy/account bị hiểu nhầm là đã post và từ chối tap (hoặc fail-closed exit 1).
- **Quy tắc scoping:**
  1. Nếu `status == "completed"` và `current_run_id` khác `receipt_run_id`, bỏ qua receipt cũ để cho phép phiên mới chạy.
  2. Khi có `target_account` cụ thể: `return bool(receipt_acc and receipt_acc == target_acc)` (loại trừ untagged receipts để tránh cross-blocking các account khác trên máy dùng chung).
  3. Khi không có `target_account` (rỗng): chấp nhận tất cả receipt machine-scoped.
  4. Giữ schema validation nghiêm ngặt trên `machine` và `video_number`.

## 3. Mở Rộng Selector Post & Camera LIVE Mode Switch
- **Post Button Selectors:** Thêm các resource-id mở rộng: `("sh8", "shd", "sox", "soz", "sp7", "rbp", "t66", "post_action", "post_button")`.
- **Caption Field:** Thêm `h3a`.
- **Camera LIVE mode switch:** Khi camera mở ở chế độ LIVE (chứa `text="Phát LIVE"`, `text="Trung tâm LIVE"`, `text="LIVE"`), tự động tap chuyển sang tab `ĐĂNG` hoặc `TẠO`.

## 4. Caption Truncation & Hashtag Verification (Pill UI)
- Tránh kiểm tra `any()` quá lỏng lẻo làm mất độ tin cậy của việc xác nhận caption.
- **Thứ tự kiểm tra an toàn:**
  1. So khớp toàn bộ chuỗi caption trong visible text.
  2. So khớp prefix (3-4 từ đầu tiên của caption).
  3. So khớp majority hashtags: với `<= 2` hashtags yêu cầu khớp 100%, với `> 2` hashtags yêu cầu khớp ít nhất `max(1, (len(hashtags) + 1) // 2)`.
