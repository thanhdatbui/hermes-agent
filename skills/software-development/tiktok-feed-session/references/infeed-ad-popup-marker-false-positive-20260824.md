# In-Feed Ad Popup Marker False Positive & Speculation vs Evidence

## Bối cảnh & Hiện tượng
- Khi TikTok hiển thị video quảng cáo có nút tương tác (CTA) như "Tìm hiểu thêm", "Thêm vào giỏ hàng" kèm chữ "Đóng" trên feed For You (`com.ss.android.ugc.trill`).
- Bot dừng phiên với alert: `unexpected popup/dialog marker detected` (trạng thái `GIỮ HIỆN TRƯỜNG`).
- User thắc mắc tại sao không vuốt lướt qua được và tại sao cơ chế fallback `_swipe_recovery_on_stuck` không được áp dụng.

## Nguyên nhân gốc (Root Cause)
1. **False-positive trong Classifier:**
   - Chữ `"Đóng"` trong video ad nằm trong `popup_terms` của `classifier.py`.
   - Mặc dù màn hình có đầy đủ header feed (Đề xuất / Trang chủ), classifier bị kích hoạt rule generic popup và trả về `screen="manual-needed:popup"` (reason: `popup/dialog marker present`).
2. **Safety Guard ngắt phiên trước khi kịp vuốt:**
   - Trong `_feed_session_flow`, `_safety_from_row(ctx, row)` và `manual_guard` phát hiện `manual-needed:popup`.
   - Vòng lặp dừng khẩn cấp trước khi kịp thực hiện lệnh `swipe` thông thường hoặc đi vào nhánh cứu kẹt `_swipe_recovery_on_stuck`.
3. **Bài học về suy đoán vô căn cứ:**
   - Tuyệt đối không suy diễn "quảng cáo dạng modal overlay chặn gesture swipe" khi chưa có bằng chứng thực nghiệm hoặc log tái hiện cử chỉ vuốt bị chặn.
   - Luôn kiểm tra call chain thực tế trong code xem lệnh swipe đã từng được gửi xuống thiết bị hay bị chặn ngay từ lớp classifier/safety.

## Giải pháp chuẩn
1. **Phân loại In-Feed Ad là Feed hợp lệ:**
   - Khi màn hình có context feed đầy đủ (`Trang chủ`, `Đề xuất`, `ViewPager`), các nhãn CTA quảng cáo ("Tìm hiểu thêm", "Đóng" của ad) không được coi là blocker popup mà phải coi là feed bình thường (`for-you`).
2. **Fail-safe cho `_swipe_recovery_on_stuck`:**
   - Đảm bảo các màn hình feed chứa ad không bị `manual_guard` chặn sớm trước khi swipe recovery có cơ hội lướt qua.
