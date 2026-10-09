# Cạm bẫy `follow_friends_popup_no_close_control`, False-Positive Profile/Feed và Cơ chế Phục hồi

**Ngày ghi nhận:** 06/09/2026 (Case Máy 54 - `maclam1001`)

---

## 1. Hiện tượng & Triệu chứng
Khi chạy nuôi acc / lướt feed (`feed-session-smoke` hoặc `multi-machine-feed-session`), runner dừng đột ngột trước khi điều hướng trang với lỗi:
```text
NavigationResult(ok=False, status='fail', reason='failed_dismiss_overlay_before_navigation: follow_friends_popup_no_close_control')
```

---

## 2. Nguyên nhân gốc rễ (Root Cause)

1. **False-Positive trong Detector (`_detect_follow_friends` & `detect_follow_friends_suggestion_popup`):**
   - Các từ khóa nhận diện ("Tìm bạn bè", "Mời bạn bè", "Bạn bè với", "Follow bạn bè của bạn") quá lỏng lẻo.
   - Khi TikTok đang ở màn hình Profile cá nhân (có nút "Tìm bạn bè", "Mời bạn bè", "Sửa hồ sơ") hoặc màn hình Main Feed (có tab "Bạn bè" ở bottom nav), detector kích hoạt nhầm nhận diện đây là popup gợi ý kết bạn (`follow_friends_suggestion_popup`), dù không có bất kỳ dialog modal hay card popup nào che khuất giao diện.

2. **Cơ chế Fail-Closed lỗi thời trong Dismisser (`dismiss_follow_friends_suggestion_popup`):**
   - Khi `_find_follow_friends_semantic_close_control(current_root)` không tìm thấy nút đóng dạng X hay nút "Không quan tâm", hàm thực hiện fallback gửi phím Back (`send_device_back_key`).
   - Tuy nhiên, sau khi gửi Back và capture fresh root (`after_root`), biến `current_root` **không được cập nhật** bằng `after_root`.
   - Khối logic sau đó tiếp tục kiểm tra trên `current_root` cũ:
     ```python
     elif _find_follow_friends_semantic_close_control(current_root) is None:
         reason = "follow_friends_popup_no_close_control"
     ```
   - Kết quả: hàm trả về `dismissed=False` với lý do `follow_friends_popup_no_close_control`, khiến bộ điều hướng `calibrate_screens.py` fail cứng toàn bộ phiên chạy.

---

## 3. Giải pháp khắc phục chuẩn hóa

1. **Bổ sung Profile & Main Feed Guard (Chặn False-Positive):**
   - Thêm helper nhận diện màn hình Profile (`sửa hồ sơ`, `edit profile`, `đang follow`, `follower`, `thêm tiểu sử`) và Main Feed (`đề xuất`, `dành cho bạn`, `for you`, tương tác video).
   - Nếu màn hình là Profile hoặc Main Feed mà KHÔNG có modal popup thực sự (`android.app.Dialog` hoặc dialog card kèm semantic close control), trả về `False` ngay lập tức.

2. **Hoàn thiện Navigation Fallback trong Dismisser:**
   - Khi không có nút đóng X:
     a. Tìm nút quay lại/back trên header (kết thúc bằng `:id/back`, `:id/bq7`, `/back`, `/btn_back` hoặc text/desc "quay lại", "back", "trở về") và tap.
     b. Nếu không có hoặc tap không đóng được: gửi phím Back thiết bị (`send_device_back_key(ctx)`).
     c. Sau khi Back/tap: sleep 1.0s, recapture fresh root và **cập nhật `current_root = after_root`**.
     d. Nếu sau khi Back mà popup đã biến mất (`not detect_follow_friends_suggestion_popup(after_root)`) hoặc màn hình đã trở về Main Feed / Profile hợp lệ: đánh dấu `closed = True`, `reason = f"followed_{followed_count}_friends_and_dismissed_via_back"`.
   - Tuyệt đối không fail cứng `follow_friends_popup_no_close_control` nếu đã thoát thành công về Feed/Profile.

---

## 4. Lệnh Canary Kiểm Chứng
```bash
env -u PYTHONPATH powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 54 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```
*Yêu cầu kết quả:* `final_status: success`, `total_swipes_completed >= 2`, không còn kẹt tại bước `dismiss_overlay_before_navigation`.
