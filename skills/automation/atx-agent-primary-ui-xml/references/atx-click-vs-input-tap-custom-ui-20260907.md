# ATX Click vs ADB Input Tap on Custom UI & Switcher Buttons (2026-09-07)

## Bối cảnh
Trên các phiên bản TikTok mới (46.2.3 đến 46.8.3 trên Máy 8, 46, 78, 79), nhiều button/container trong bottom-sheet (ví dụ `id/l9b`, `id/lkp`, `id/lpw` trong Account Switcher) thường xuyên gặp sự cố khi chuyển tài khoản qua ADB input tap.

## Nguyên nhân & Các bẫy đã chứng minh thực nghiệm

1. **0ms Touch Event vs Synthetic Click:**
   - `adb shell input tap` gửi `ACTION_DOWN` rồi `ACTION_UP` ngay lập tức (0ms). Nhiều UI component Material 3 / Jetpack Compose / WebView lọc bỏ các event này để chống chạm nhầm.
   - ATX JSON-RPC `click([x, y])` tương tác trực tiếp qua UiAutomation / AccessibilityNodeInfo, kích hoạt `performAction(ACTION_CLICK)` hoặc synthetic touch đáng tin cậy hơn nhiều so với ADB input tap.
   - Giải pháp fallback nhanh không cần ATX socket là dùng `input swipe {x} {y} {x} {y} 100` (duration 100ms..150ms).

2. **Bẫy tap vào Child TextView `clickable="false"` (Chứng minh trên Máy 8 & Máy 46):**
   - Container dòng tài khoản (`id/lpw` hoặc `id/lkp`) có `clickable="true"` (bounds `[0, 600][1080, 816]`).
   - Bên trong chứa child `TextView` `id/nba` (`clickable="false"`, bounds `[252, 678][542, 738]`, center `[397, 708]`).
   - **Cảnh báo Anti-pattern:** Nếu cố tình override tọa độ từ container cha sang center của TextView con `id/nba` (`x=397`), lệnh `input tap` sẽ chạm vào một View không nhận click (`clickable="false"`). Trên Samsung S7 / Android 7, sự kiện chạm không được dispatch lên container cha, khiến cú click bị nuốt hoàn toàn!
   - **Quy tắc:** Khi container cha là `clickable="true"`, phải tap vào container cha (hoặc dùng ATX click), tuyệt đối không gán tọa độ tap vào child view `clickable="false"`.

3. **Phản ứng khi tap vào tài khoản đang active (đã có `Dấu kiểm` `id/fmc`):**
   - Khi tap vào dòng tài khoản đã được chọn (nằm ở row 1 kèm `id/fmc` "Dấu kiểm"), TikTok **KHÔNG tự động đóng bottom sheet Switcher**.
   - Switcher tiếp tục mở và giữ nguyên màn hình. Runner không được nhầm lẫn đây là lỗi kẹt màn hình hay lỗi mismatch.
   - Để đóng switcher sau khi xác nhận tài khoản đã active, runner phải tap nút "Đóng" (`[936, 216][1056, 348]`) hoặc gửi phím `BACK`.
