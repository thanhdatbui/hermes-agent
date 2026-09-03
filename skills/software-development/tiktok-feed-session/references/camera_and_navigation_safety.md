# Camera & Navigation Coordinate Safety Rules

## 1. Tránh chạm trúng nút [+] Tạo video / Camera ở đáy màn hình
- **Nguyên nhân kẹt Camera:** Thanh điều hướng đáy của TikTok có nút `[+]` Tạo video tròn to ở giữa (`X=540, Y=1800+`).
- **Quy tắc tọa độ an toàn:**
  * **Lệnh swipe tắt notification shade / vuốt feed:** Bắt đầu từ `Y <= 1540` (ví dụ `[540, 1540, 540, 300]`), **TUYỆT ĐỐI CẤM** bắt đầu từ `Y >= 1800`.
  * **Lệnh tap popup fallback / OK:** Tọa độ tap fallback giữa màn hình phải đặt ở `Y <= 1400` (ví dụ `(540, 1200)`), **TUYỆT ĐỐI CẤM** fallback mù ở `Y >= 1700`.

## 2. Xử lý kẹt Camera trong các bước kiểm tra
- **AdbClient Interface Pitfall (CRITICAL):**
  * `AdbClient` của `automation-core` **chỉ có method `ctx.adb.shell(...)`** chứ không có `ctx.adb.keyevent(...)`.
  * **CẤM** viết `if hasattr(ctx.adb, 'keyevent'): ctx.adb.keyevent(4)` vì check này sẽ silently fail / false và không bao giờ gửi phím Back.
  * **BẮT BUỘC** dùng helper chuẩn hóa `send_device_back_key(ctx)` hoặc gọi trực tiếp `ctx.adb.shell(["input", "keyevent", "4"])`.
- **Dismiss Camera Creation Screen:**
  * Luôn ưu tiên dùng `iter_elements(xml)` tìm nút Close/Đóng ở phía trên màn hình (`bounds.top < 400`) để tap nút X trước.
  * Fallback bằng `send_device_back_key(ctx)` để thoát giao diện Camera về lại Feed.
- **Classifier Screen Detection:** `classify_tiktok_screen` phải nhận diện các từ khóa camera (`10 phút`, `60s`, `15s`, `ảnh`, `văn bản`, `đăng`, `tạo`) và gắn nhãn `GENERIC_POPUP_SCREEN` để trigger `benign_popup_registry` tự gửi `KEYCODE_BACK`.
- **Bước `_verify_profile_after_session`:**
  * Nếu màn hình lọt vào Camera Creation overlay (do tap nhầm hoặc overlay cũ), tự động gửi `KEYCODE_BACK` đóng camera.
  * Tap lại chuẩn góc Profile (`x=972, y=1856` tương ứng 90% width, 96.7% height) để đối soát username.
  * Không kết luận `profile account mismatch` khi màn hình không có username/@ (tránh báo động giả).
