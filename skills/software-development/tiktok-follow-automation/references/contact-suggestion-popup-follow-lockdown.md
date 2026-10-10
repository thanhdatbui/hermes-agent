# Khóa Tuyệt Đối Auto-Follow Từ Popup Gợi Ý Danh Bạ / Bạn Bè (Contact Suggestion Lockdown)

## Hiện tượng & Nguyên nhân gốc rễ
1. **Hiện tượng:**
   - Trên Dashboard, các tài khoản yếu (mới lập, chưa đủ 6 video, hoặc đang trong ngày nghỉ dưỡng sinh `organic-rest-day-pure-feed`) bất ngờ tăng lẻ 1 follow: `ĐÃ FOLLOW: X (+1)`, trong khi số follow nội bộ là `🔗 Nội bộ: +0`.
   - Kiểm tra log ca chạy thấy follow chéo bị skip hoặc `follow_rate_percent=0`.
2. **Nguyên nhân gốc rễ:**
   - Trong quá trình lướt Feed hoặc khởi động app, TikTok hiển thị popup gợi ý kết nối: *"Follow bạn bè của bạn"*, *"Bạn bè với X"*, *"Gợi ý follow"*, *"Mời bạn bè"*.
   - Trước đây trong `automation-core`, các hàm xử lý popup (`detect_contact_follow_suggestion` trong `benign_popup.py` và `_dismiss_follow_friends_popup` trong `tiktok_popup.py`) chứa cơ chế tự động tiện tay bấm nút "Follow" / "Follow lại" trước khi bấm đóng X.
   - Cơ chế này bypass toàn bộ chính sách nghỉ của nick, khiến nick yếu bị phát sinh follow ngẫu nhiên ngoài kiểm soát.

## Quy tắc thiết kế & Vận hành (Invariant)
1. **Khóa 100% việc bấm Follow từ Popup:**
   - Mọi popup gợi ý bạn bè, danh bạ, tài khoản quen biết BẮT BUỘC chỉ được thực hiện hành động **ĐÓNG / BỎ QUA** (`dismiss_not_interested_button` hoặc `dismiss_close_x`).
   - CẤM TUYỆT ĐỐI gán `pre_action="tap_follow_button"` hoặc return `follow_target` trong bộ nhận diện popup.
2. **Cơ chế Trust: Bỏ qua Popup vs Search Follow:**
   - **Bỏ qua popup:** Hành vi tự nhiên 100% của người dùng thật (thấy phiền khi bị ép kết nối danh bạ). Giúp nick tránh bị thuật toán TikTok gắn cờ bot clicker và tránh bị loãng niche sở thích.
   - **Tránh nhả follow (Drop Follow):** Bấm follow người lạ từ popup mà không có hành vi xem nội dung/tương tác trước đó rất dễ bị TikTok quét là follow ảo và âm thầm hủy follow sau vài giờ, gây tụt trust nghiêm trọng cho nick yếu.
   - **Follow chéo có kiểm soát:** Nick chỉ phát sinh lượt follow khi chạy đúng kịch bản `follow_runner` (Mode 1: Search username -> vào Profile xem video -> Follow; Mode 2: Mở danh sách follower của seed account -> Follow có giãn cách). Luồng này hoàn toàn độc lập và không phụ thuộc vào popup.
