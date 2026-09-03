# Status Bar Notification False-Positive & Sensitive Keyword Scoping (Case 55)

## 1. Hiện tượng & Nguyên nhân gốc rễ
- Trong luồng vuốt nuôi Feed (`_swipe_recovery_on_stuck` / fallback swipe), khi màn hình gặp tình trạng kẹt hoặc lạ, script có cơ chế kiểm tra an toàn `_is_sensitive` để tránh vuốt bừa trên màn hình Login, OTP, Captcha, Checkpoint.
- **Lỗi False-Positive:** Nếu status bar hệ thống (`com.android.systemui`) có notification chạy nền từ Google Play ("Dịch vụ Google Play: Yêu cầu đăng nhập"), việc quét từ khóa thô ("đăng nhập", "login", "mã xác minh") trên toàn bộ XML hoặc OCR dump mà không lọc package sẽ khớp trúng notification này.
- **Hậu quả:** Hàm `_is_sensitive` trả về `True` $\rightarrow$ script ngộ nhận là màn Login TikTok thật và abort fail-closed $\rightarrow$ chặn đứng cơ chế vuốt fallback 2 lần của farm.

## 2. Quy tắc xử lý chuẩn (Canonical Pattern)
1. **Lọc XML theo Package Context:**
   - Chỉ trích xuất text/content-desc từ các node thuộc package TikTok (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`).
   - Loại trừ hoàn toàn các node thuộc vùng Status Bar hệ thống (bounds bottom $\le 120$ hoặc package `com.android.systemui`, `com.google.android.gms`).
   - **Fail-Closed khi XML hỏng:** Nếu XML không thể parse được, bắt buộc trả về `True` (nhạy cảm) để bảo vệ tài khoản, không được fail-open.
2. **Loại trừ Notification Header trên OCR text:**
   - Dùng regex chính xác để bóc tách/loại bỏ header notification Google Play trước khi kiểm tra từ khóa nhạy cảm:
     ```python
     filtered_ocr = re.sub(
         r"(?i)\b(dịch vụ google play|google play services)\s*(notification)?\s*:?\s*(yêu cầu đăng nhập|sign in required)\b",
         "",
         filtered_ocr,
     )
     ```
3. **Bổ sung ID vào Blind Popup Rules:**
   - Khi TikTok Feature Promo xuất hiện dialog "Tìm hiểu thêm" / "Thêm vào giỏ hàng", thêm resource-id `com.ss.android.ugc.trill:id/i2y` vào rule `learn_more_dialog_dismiss` để tap nút Đóng tự động.
