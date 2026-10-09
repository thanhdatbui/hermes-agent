# Profile Switcher Retrying Settle & Network Error Recovery

## Context & Pitfall
Khi switch profile tài khoản TikTok trong flow `feed_swipe_smoke.py`:
- Sau khi click row tài khoản mong muốn (`selected_account_by_exact_switcher = True`), TikTok điều hướng sang màn hình Profile.
- Tuy nhiên, trong 2-5 giây đầu:
  1. Profile XML có thể vẫn cache username của nick cũ (ví dụ: đang switch sang `phanlan097`, nhưng XML vẫn hiển thị handle `lebaothao8787`).
  2. Màn hình Profile có thể gặp lỗi mạng/tải dữ liệu và hiển thị nút "Thử lại" (`com.ss.android.ugc.trill:id/dcj` hoặc text "Thử lại", "Đã xảy ra lỗi").
- Nếu script kiểm tra ngay và thấy `recaptured_username` có giá trị nhưng không khớp `expected`, điều kiện `verified` lập tức fail (`False`) và script đánh giá sai là switch thất bại / username mismatched.

## Pattern / Solution
1. **Kiểm tra Retry UI:**
   Nếu `not verified` và `selected_account_by_exact_switcher`:
   - Quét `recaptured_xml` tìm nút retry (`id/dcj` hoặc text "Thử lại" / "Đã xảy ra lỗi").
   - Nếu có, tap nút retry và chờ ~2.5s.
2. **Settle Retry:**
   - Sleep 3.0s để Profile render hoàn tất danh tính mới.
   - Gọi lại `_read_profile_identity_with_add_phone_guard(...)` để lấy `latest_identity` mới nhất.
   - Re-evaluate lại `recaptured_username`, `username_matches`, `display_name_matches`, và `verified`.
3. **Verify:**
   - Cú pháp: `python -m py_compile "D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py"`
   - Canary: Chạy `run-feed-session.ps1` trên 1 máy (ví dụ máy 33) với `-RecoveryTestSwipes 2` để kiểm chứng.
