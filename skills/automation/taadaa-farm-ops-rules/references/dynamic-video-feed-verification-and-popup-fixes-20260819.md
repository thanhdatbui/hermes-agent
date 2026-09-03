# Bài Học Vận Hành & Khắc Phục Lỗi: Dynamic Video Feed Verification & Popup TikTok Shop

## 1. Pitfall: So Khớp Ảnh pHash/dHash Trên Video Đang Chạy (Anti-Pattern)
- **Hiện tượng**: Khi xây dựng AI Auto-Recovery, nếu sử dụng thuật toán băm ảnh trực quan (`pHash` / `dHash` với Hamming distance) để so sánh ảnh chụp lúc alert và ảnh chụp live khi bắt đầu recovery, hệ thống sẽ liên tục báo lỗi `phash_mismatch (dist=28 stale_alert_skipped)` và tự động bỏ qua không xử lý.
- **Nguyên nhân**: Trên TikTok Feed, các video ca nhạc, livestream và quảng cáo được render động liên tục từng frame (nhân vật cử động, ánh sáng thay đổi). Hai ảnh chụp cách nhau 1-2 giây chắc chắn có hash khác nhau.
- **Giải pháp chuẩn**:
  - TUYỆT ĐỐI KHÔNG dùng so khớp pixel / hash ảnh trên màn hình video feed động.
  - Chỉ kiểm tra thiết bị còn online (`adb_screencap` thành công và `focused_package` hợp lệ) ➔ Lập tức chuyển ảnh live và UI XML cho Vision AI (`ag/claude-opus-4-6-thinking`) phân tích và gỡ rối.

---

## 2. Xử Lý Popup Quảng Cáo TikTok Shop: "Thêm vào giỏ hàng" Kèm Nút "Đóng"
- **Hiện tượng**: Khi lướt feed gặp video quảng cáo tài trợ (Sponsored Ad / Closeup), TikTok hiển thị một popup overlay đè giữa màn hình với nút đỏ lớn *"Thêm vào giỏ hàng"* và nút text *"Đóng"* ngay bên dưới.
- **Xử lý chuẩn trong `feed_swipe_smoke.py` (`learn_more_dialog_dismiss`)**:
  - **Detector XPath**:
    `//node[@text="Tìm hiểu thêm" or @content-desc="Tìm hiểu thêm" or contains(@text, "Tìm hiểu thêm") or contains(@text, "Thêm vào giỏ hàng") or @text="Thêm vào giỏ hàng"]`
  - **Action Target**:
    `//node[@text="Đóng" or @content-desc="Đóng" or @resource-id="com.ss.android.ugc.trill:id/tv_close" or @resource-id="com.ss.android.ugc.trill:id/close_btn"]`
  - **Action**: `tap` vào tâm nút *"Đóng"* `(540, 1070)` trên màn hình 1080x1920 để đóng popup và tiếp tục lướt feed bình thường.

---

## 3. Phân Vai Model Trong Hệ Thống AI Autonomous Recovery
- **Thợ code (Coding Worker - Claude Code CLI / Sonnet)**: Dùng để dựng khung module, viết code patch, viết test suite `pytest`.
- **Kỹ sư thẩm định (Plan-Review Gate - Opus/Terra/Plan-Review max)**: Bắt buộc thẩm định `git diff` độc lập trước khi patch và commit để tránh lỗi đảo ngược quy trình (bắn ADB trước khi patch code) hoặc hardcode fallback ẩu.
- **Thực thi trên thiết bị**: Luôn tuân thủ trật tự: Phân tích & Patch code vào repo trước ➔ Kích hoạt chính logic vừa code chạy test trên máy đang kẹt tại hiện trường ➔ Verify màn hình giải phóng ➔ Commit & Push Git.
