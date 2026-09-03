# Case UI-10 & Flow: Xử lý Popup "Trạng thái tài khoản" / "Tài khoản của bạn đã bị đăng xuất"

## Bối cảnh & Hiện tượng
- Khi tài khoản TikTok bị out phiên hoặc hệ thống TikTok đẩy thông báo hết hạn phiên, TikTok hiển thị dialog modal ở giữa màn hình:
  - **Tiêu đề:** `Trạng thái tài khoản` (hoặc `Account status`)
  - **Nội dung:** `Tài khoản của bạn đã bị đăng xuất. Hãy thử đăng nhập lại.` (hoặc `Your account was logged out. Please try logging in again.`)
  - **Nút hành động:** `OK` (thuộc package `com.ss.android.ugc.trill` hoặc package TikTok tương ứng)

## Anti-Pattern Cần Tránh
1. **Tự ý đưa Logged-out Dialog vào `benign_popup_registry` làm generic dismisser:**
   - Đóng thông báo logout trên UI không đồng nghĩa với việc tài khoản đã sẵn sàng để feed/swipe tiếp.
   - Nếu đăng ký `account_logged_out_popup` vào registry popup thông thường với `dismissed=True`, caller sẽ tiếp tục thực hiện vuốt (swipe) và follow trên màn hình chưa đăng nhập, gây lãng phí swipe budget và vi phạm rule fail-closed.
2. **Sai lầm chuyển màn hình về `GENERIC_POPUP_SCREEN` trong classifier:**
   - Trong `classifier.py`, màn hình này bắt buộc phải trả về `manual-needed:login` (quarantine state).
   - Tuyệt đối không phân loại nó thành `GENERIC_POPUP_SCREEN` (`manual-needed:popup`) vì sẽ làm lộ luồng vuốt generic cho tài khoản đã mất phiên.

## Quy tắc Thiết kế & Triển khai An toàn (Fail-Closed & Terminal Quarantine)
1. **Phân loại màn hình (Classification):**
   - Luôn giữ `detect_account_logged_out_popup(root)` trong `classifier.py` để map về `screen="manual-needed:login", manual_needed=True`.
2. **Cách ly phiên (Quarantine):**
   - Khi phát hiện `account_logged_out_popup`, worker dừng phiên ngay lập tức, giải phóng thiết bị mà không chạy swipe loop.
   - Luồng re-login và reconcile (`tiktok-log-in`) sẽ chịu trách nhiệm xử lý đăng nhập lại cho tài khoản này.
3. **Độ nghiêm ngặt của XML Matcher nếu kiểm tra Modal:**
   - Bắt buộc container phải là modal dialog có kích thước giới hạn (không phải full-screen/hierarchy root).
   - Toàn bộ node con (tiêu đề, nội dung, nút OK) phải có package TikTok hợp lệ (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`), loại trừ tuyệt đối System UI, Launcher và Google Play Services.
   - Nút `OK` phải có `clickable="true"`, `enabled="true"` và bounds nằm hoàn toàn bên trong modal container.
