# Quy chuẩn Định danh Quy trình trên Farm Alert & Xử lý Kẹt Màn hình Phụ (2026-09-03)

## 1. Bối cảnh & Nguyên nhân sự cố
Khi hệ thống chạy các quy trình độc lập như Upload Avatar (`Tiktok-video` / `run_tiktok_upload_avatar.ps1`) hoặc Đăng ký TikTok (`Tiktok_Reg`), nếu gặp sự cố UI dẫn đến dừng máy, Telegram Farm Alert trước đây lại bắn ra thông tin:
- File flow phụ trách: `feed_swipe_smoke.py`
- File log run: `.ai-runs/latest/summary.txt`
- Lệnh canary test: `run-feed-session.ps1 -Row 1 ...`

Điều này gây hiểu lầm nghiêm trọng cho người vận hành rằng phiên nuôi acc (feed session) bị lỗi, trong khi thực tế máy đang chạy quy trình Upload Avatar.

## 2. Kiến trúc Alert Đa Quy Trình (`automation-core.alerts`)
1. **Dynamic Metadata Resolver (`_SCRIPT_METADATA`):**
   - Ánh xạ tự động các alias của `script_name`:
     - `feed` (`multi-machine-feed-session`, `feed-session-smoke`, `tiktok-feed`...) -> Nuôi Acc / Lướt Feed
     - `avatar` (`tiktok-upload-avatar`, `avatar-upload`, `run_tiktok_upload_avatar`...) -> Upload Avatar (Tiktok-video)
     - `upload` (`tiktok-video`, `video-upload`, `run_tiktok_upload_batch`...) -> Đăng Video (Tiktok-video)
     - `follow` (`tiktok-follow`, `follow_runner`...) -> Follow TikTok (tiktok-follow)
     - `2fa` (`tiktok-add-2fa`, `run_batch_live_2fa`...) -> Bật 2FA TikTok (tiktok-add-bao-mat-f2a)
     - `reg_tiktok` (`Tiktok_Reg`, `social_reg_v1`...) -> Đăng Ký TikTok (Tiktok_Reg)
     - `reg_gmail` (`register-gmail`, `run_all_gmail`...) -> Đăng Ký Gmail (register gmail)
2. **Cấu trúc Alert Telegram Chuẩn:**
   - Dòng tiêu đề: `🚨 [FARM ALERT: MÁY N] DỪNG PHIÊN`
   - Dòng định danh: `• Quy trình / Script: <b><Tên quy trình chuẩn></b>`
   - Dòng hiện trường: `• Hiện trường: <Trạng thái>`
   - BẮT BUỘC chỉ định đúng `flow_file`, `log_path` và lệnh canary tương ứng với quy trình đang chạy thay vì mặc định feed session.

## 3. Tự động Thoát Màn hình Sửa Hồ Sơ / Thay Đổi Ảnh (Edit Profile Subpage)
- Khi quy trình Upload Avatar hoặc cập nhật thông tin nick kết thúc hoặc bị gián đoạn, màn hình máy có thể dừng ở trang Sửa hồ sơ (`Thay đổi ảnh` / `Edit profile`).
- Feed session khi khởi chạy trên máy sẽ gặp màn hình này.
- **Cơ chế Auto-Recovery:**
  - `detect_edit_profile_subpage` (trong `automation_core.tiktok.benign_popup` và `python_runner.core.benign_popup`) nhận diện màn hình Sửa hồ sơ (loại trừ các màn hình nhạy cảm chứa password/login và loại trừ main Profile có tab bar).
  - Đăng ký handler `profile_edit_subpage_overlay` (priority 79) trong `BENIGN_POPUP_REGISTRY` để tự động tap nút Quay lại (`Quay lại` / `Back` / `iv_back`) hoặc gửi phím Back thoát về Home an toàn.
