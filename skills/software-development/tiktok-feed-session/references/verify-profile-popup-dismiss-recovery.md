# Verify Profile & Follow Friends Popup Dismiss Recovery (2026-08-25)

## 1. Hiện tượng & Hiện trường thực tế
- **Thiết bị:** Máy 48 (`device:59cef824b7`), chạy tài khoản `thanh.truc0366` lúc `00:24:21 25/08`.
- **Triệu chứng:** Hoàn thành 11/11 swipes lướt feed bình thường. Khi kết thúc phiên, flow gọi `verify_profile` để đối soát xem đúng nick không thì bị dừng với lỗi `profile verification mismatch: profile account mismatch`.
- **Nguyên nhân gốc rễ:**
  1. Khi script tap vào tab **Hồ sơ (Profile)** ở đáy, TikTok bung modal overlay **"Follow bạn bè của bạn"** (danh sách gợi ý kết bạn/follow từ danh bạ gồm avatar + nút Follow đỏ + icon `X` đóng ở góc phải trên).
  2. Popup này che khuất toàn bộ phần trên màn hình Profile, làm ẩn text `@username` (`@thanh.truc0366`).
  3. Bộ giải phóng popup tự động (`dismiss_tiktok_popups` / `dismiss_follow_friends_suggestion_popup`) vốn chỉ chạy trong vòng lặp sau mỗi cú swipe lướt feed, chưa được tích hợp vào đầu hàm đối soát cuối phiên `_verify_profile_after_session` (`feed_swipe_smoke.py`).
  4. Hàm `_verify_profile_after_session` trước đó mới chỉ có recovery cho màn hình Camera và Hộp thư, nên khi gặp popup gợi ý bạn bè thì coi như màn hình Profile không hợp lệ → báo mismatch sai lệch.

## 2. Quy tắc xử lý chuẩn (User chốt 25/08)
- **Quy tắc thao tác khi gặp popup "Follow bạn bè của bạn":**
  - **TUYỆT ĐỐI KHÔNG bấm đóng `✕` ngay lập tức**.
  - **Bắt buộc bấm nút `Follow` cho 1–2 nick** trong danh sách popup trước (mỗi lần bấm delay ~0.8s, recapture xác minh).
  - Quét rộng các nhãn nút: `"Follow"`, `"Follow lại"`, `"Follow back"`, `"Theo dõi"`.
  - Sau khi follow xong 1–2 nick, mới bấm nút `✕` (`com.ss.android.ugc.trill:id/e63` hoặc `content-desc="Đóng"`) để đóng giải phóng màn hình.
- **Kích hoạt ở TẤT CẢ các giai đoạn:**
  - **Trong lúc lướt Feed:** Kích hoạt qua `_maybe_dismiss_allowed_popup_after_swipe` và `BENIGN_POPUP_REGISTRY` (`follow_friends_suggestion_popup`).
  - **Trước khi lướt (Preflight / Switcher):** Kích hoạt qua `_maybe_dismiss_allowed_popup_row`.
  - **Sau khi lướt (`verify_profile`):** Đặt bộ quét và xử lý `dismiss_follow_friends_suggestion_popup` ngay đầu `_verify_profile_after_session` trước khi đọc `@username`.
