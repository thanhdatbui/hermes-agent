# Sự Cố Lệch Profile Sau Switch Account (Feed Drift) & Kỷ Luật Zero-Delay Dispatch

## 1. Bối cảnh & Hiện tượng (Sự cố 06/09/2026 - Máy 79 & Hàng loạt máy)
- **Cảnh báo từ người dùng:** *"Ms sửa hàm gì gây lỗi này hàng loạt máy r đó"* và *"Điều tra lâu thế, đang delegate hay tự làm ở session chính đấy"*.
- **Triệu chứng:** Sau khi hoàn tất đổi nick trong Account Switcher, hàng loạt máy dừng phiên với lỗi `profile username still mismatched after switch` (Nick dự kiến: `ruffumyxkvv`, nick đọc được: `@creator` của video trên feed như `@Linhnguyen1707`).

## 2. Nguyên nhân kỹ thuật cốt lõi (Technical Root Cause)
1. **TikTok Feed Default Navigation:** Khi chọn tài khoản trong Account Switcher bottom sheet, TikTok khởi tạo lại session và tự động đưa app về trang Home / For You feed.
2. **Dropped Navigation Tap:** Cú tap tab Hồ sơ (`tap_navigation_target(_profile_target())`) ngay sau đó bị trễ nhịp animation hoặc uiautomator settle khiến tap bị nuốt, app vẫn ở lại Feed.
3. **Flawed Drift Detection (Regression do điều kiện phụ):**
   Hàm `_profile_guard_drifted_from_profile` trong `python_runner/flows/feed_swipe_smoke.py` kiểm tra:
   ```python
   # ❌ LỖI LOGIC:
   if "keyboard cleanup" in reason:
       return True
   return xml_error in FEED_CONFIRMED_XML_DEGRADED_ERRORS
   ```
   Khi UI XML dump sạch (`xml_error == ""`), hàm trả về `False` dù màn hình đang rõ ràng là `home` hoặc `for-you`!
4. **False Identity Parsing:** Do tưởng nhầm là màn hình Profile chuẩn, hàm `read_profile_identity()` parse caption video trên For You feed, trích xuất handle `@creator` làm username của máy, so sánh lệch với expected và kích hoạt fail-closed `profile username still mismatched after switch`.

## 3. Giải pháp chuẩn (Standard Fix)
1. **Strict Positive Drift Detection:**
   Trong `_profile_guard_drifted_from_profile`: Khi `detected in {"home", FEED_TYPE_FOR_YOU, FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS}`, bắt buộc trả về `True` vô điều kiện:
   ```python
   if detected in {"home", FEED_TYPE_FOR_YOU, FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS}:
       return True
   ```
2. **Re-tap Recovery:**
   Trong `_read_profile_identity_with_add_phone_guard`: Khi phát hiện drift về Feed, kích hoạt `_try_profile_retap_on_drift` để re-tap tab Hồ sơ kéo app trở về đúng màn hình Profile trước khi đọc identity.

## 4. Kỷ luật Zero-Delay Dispatch cho Coordinator
- **Ngăn chặn câu hỏi nghi vấn:** *"Điều tra lâu thế, đang delegate hay tự làm ở session chính đấy"*.
- **Quy tắc:**
  1. Khi nhận alert đã có triệu chứng rõ ràng (`profile username still mismatched after switch`), Coordinator chỉ inspect O(1) để xác thực màn hình hiện tại (`home`/`feed` hay `profile`).
  2. Dùng `git log -n 5 --oneline` để xác định nhanh hàm nào vừa bị chạm vào gần nhất.
  3. Soạn ngay Patch Contract (file, vị trí dòng, old/new string logic) và dispatch Worker Subagent bằng `delegate_task` ngay lập tức.
  4. Tuyệt đối không nán lại session chính để chạy các lệnh đọc file / test mò lặp đi lặp lại.
