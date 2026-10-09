# Quy Trình Xử Lý Popup Voucher & Thoát TikTok LIVE PK Stream (Case 90)

## 1. Bối cảnh & Hiện tượng
Khi nuôi nick hoặc lướt feed, thiết bị có thể trôi vào các phòng TikTok LIVE PK split-screen và xuất hiện modal popup "Nhận voucher giảm giá" (ví dụ: Giảm 60K đ). Modal này che khuất toàn bộ bottom navigation bar (Trang chủ / Hồ sơ) khiến các bước `tap_navigation_target` hoặc `_verify_profile_after_session` báo lỗi `navigation target profile not found in XML`.

## 2. Quy tắc xử lý an toàn (Invariants)
1. **Không click toạ độ mù:** Tuyệt đối không dùng toạ độ hardcoded để tap nút đóng (X). Cần phân tích cây XML để lấy đúng bounds của nút đóng (`[✕]`, `Đóng`, `close_btn`). Nếu không tìm thấy, lập tức fallback sang phím `KEYCODE_BACK`.
2. **Cơ chế BACK 2 tầng (Multi-layer Back Recovery):**
   - **BACK 1:** Đóng modal popup voucher giảm giá, lộ màn hình LIVE.
   - **BACK 2:** Thoát khỏi phòng LIVE PK quay về Feed video chính (For You) nơi navigation bar xuất hiện đầy đủ.
3. **Post-condition Fail-Closed:**
   - Dismicer bắt buộc phải capture `fresh_xml` để đối chiếu detector xem popup / phòng live đã thực sự đóng hay chưa.
   - Nếu sau thao tác tap/back mà popup vẫn còn trên màn hình, bắt buộc trả về `dismissed=False` (`reason="<popup>_still_present"`) để trigger các cơ chế retry/relaunch cấp cao hơn.
4. **Synchronous Selector on Dismiss:**
   - Mọi `PopupDismissResult(dismissed=True, ...)` bắt buộc phải populate `selector={"action": "allowlist_dismiss", "popup_type": "<popup_name>"}`.
5. **Strictly Unique Priorities in Registry:**
   - Tất cả các entry trong `BENIGN_POPUP_REGISTRY` phải có priority nguyên duy nhất không trùng lặp, đảm bảo thứ tự quét chính xác và ổn định.
