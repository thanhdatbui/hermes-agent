# Quy tắc Follow Độc Lập Khỏi Trạng Thái Feed & Video Gate >= 5

1. **Gate Video >= 5:**
   - Nick TikTok phải đạt tối thiểu >= 5 video đã đăng mới được kích hoạt Follow hook.
   - Nick < 5 video tự động Safe-Skip `under-5-videos-follow-disabled` (budget = 0) để bảo vệ nick khỏi bị nhả follow ngầm.

2. **Follow Độc Lập Khỏi Trạng Thái Feed:**
   - Kể cả khi phiên lướt Feed gặp lỗi (swipe limit, timeout, drift...), máy vẫn được phép chuyển sang hook Follow chéo `_run_follow_hook` nếu tài khoản thỏa mãn Gate >= 5 video và không bị cooldown.

3. **Phân loại Watchdog chuẩn:**
   - Watchdog chỉ tính lỗi Follow (`fl_error`) khi máy đã hoàn tất bước Feed thành công (`status == "success"`) mà hook bị lỗi.
   - Các máy fail ở Feed / bị lock thiết bị không có kết quả follow tuyệt đối không được gán là lỗi script follow.
