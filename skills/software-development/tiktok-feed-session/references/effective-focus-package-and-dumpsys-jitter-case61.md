# Case 61: Effective Focus Package & Dumpsys Jitter Handling

## Bối cảnh & Hiện tượng (Máy 23)
Khi chạy `multi-machine-feed-session` hoặc `feed_session_smoke`, máy báo dừng phiên với lỗi:
- `TikTok focus lost`
- Hiện trường máy thật: Ứng dụng TikTok vẫn đang mở và hiển thị Feed video bình thường (tab "Đã follow" hoặc "Đề xuất", các nút tim, comment, share, mua sắm đầy đủ).

## Nguyên nhân cốt lõi (Anti-Pattern)
1. **Dumpsys Jitter / Transient System Focus:**
   - Lệnh `dumpsys window` trả về package hệ thống tạm thời (`com.android.systemui` hoặc `com.sec.android.inputmethod`) do thông báo VPN/ViChanger hoặc bàn phím ngầm chớp trong tích tắc.
2. **Bỏ qua kết quả chuẩn hoá của Safety Check:**
   - Trong `feed_swipe_smoke.py`, hàm `safety_check_attempt` đã kiểm tra XML và xác thực màn hình là Feed TikTok hợp lệ (`for-you`, `following`, `friends`, `profile`, `home`), đồng thời chuẩn hoá `safety.focus_package = expected_package` và `safety.status = "ok"`.
   - Tuy nhiên, trong `_row_from_attempt`, script lại kiểm tra trực tiếp biến thô `if focused_package != expected_package:`, bỏ qua kết quả đã chuẩn hoá của `safety` và gán trạng thái `failed` kèm lý do `TikTok focus lost`.

## Giải pháp chuẩn (Case Fix)
1. **Sử dụng `effective_focus_package` trong `_row_from_attempt`:**
   ```python
   effective_focus_package = safety.focus_package or focused_package
   effective_focus_activity = safety.focus_activity or focused_activity

   if effective_focus_package != expected_package:
       return build_step(
           step,
           action,
           expected,
           effective_focus_package or detected,
           "failed",
           "TikTok focus lost",
           ...
       )
   ```
2. **Đồng bộ tham số sang `build_step`:**
   - Truyền `effective_focus_package` và `effective_focus_activity` vào mọi lệnh gọi `build_step` trong `_row_from_attempt` để các bộ thu thập kết quả và logger nhận diện đúng trạng thái TikTok foreground khi Feed đã được XML xác thực.
