# Vận Hành Follow Khi 1 Row Chỉ Chạy 1 Ca/Ngày & Đối Soát Nick-by-Nick Hồi Phục Sau 48h

## 1. Cấu Trúc Ca & Điều Chỉnh Follow Budget
- **Cấu trúc ca farm mới (3 ca / 6 row):**
  - Ca 1: Row 1 (ngày lẻ) / Row 2 (ngày chẵn)
  - Ca 2: Row 3 (ngày lẻ) / Row 4 (ngày chẵn)
  - Ca 3: Row 5 (ngày lẻ) / Row 6 (ngày chẵn)
- **Tác động lên Follow Runner:**
  - Trước đây 1 row chạy nhiều ca trong ngày $\rightarrow$ cấu hình budget 4–6 follow/phiên để đạt quota 20–30 follow/ngày.
  - Hiện tại mỗi row chỉ chạy **1 ca duy nhất / ngày** $\rightarrow$ nếu giữ 4–6 follow/phiên thì mỗi ngày nick chỉ follow được 4–6 bạn bè.
  - Cần nâng `budget_per_session` lên mức 15–20 hoặc 20–25 follow/phiên, duy trì `inter_follow_delay` (30–60s) và verify pull-to-refresh sau mỗi lượt follow.

## 2. Đối Soát Thực Tế Theo Từng Nick: Hồi Phục Sau 48h vs Số Lượng Video
- **Nick đã có $\ge 5$ video (Row 1):**
  - Khi dính rate-limit (`FOLLOW_FAILED`) trong ngày, hệ thống lưu cooldown `follow_failed: true` và `follow_failed_date: YYYY-MM-DD`.
  - Sau chu kỳ nghỉ 24h–48h (vẫn duy trì lướt feed + up video), cờ tự động reset và nick follow lại bình thường (đối soát thực tế ngày 31/08 đạt 1.934 follow trên 58 máy, 01/09 đạt 1.120 follow).
- **Nick chưa có video / 0 video (Row 2/3/4/5/6 mới):**
  - Dù nghỉ 48h hay 96h, khi chạy lại vẫn bị nhả follow ngay lượt đầu hoặc sau 1–2 lượt do TikTok xếp vào nhóm clone/bot rác.
  - Gate an toàn bắt buộc: Nick $< 5$ video tự động khóa `budget = 0`, chỉ cho phép nuôi feed và up video ở ca tối cho đến khi đạt đủ $\ge 5$ video.

## 3. Cơ Chế Avatar Kèm Video #1
- Trong repo `Tiktok-video` (`state_machine.py`), khi `video_number == 1` (`_force_avatar_upload_allowed()`), hệ thống tự động kích hoạt `ENSURE_AVATAR` để lấy ảnh từ thư mục source, vào *Sửa hồ sơ* $\rightarrow$ *Thay đổi ảnh* $\rightarrow$ crop và lưu avatar trước khi post video.
