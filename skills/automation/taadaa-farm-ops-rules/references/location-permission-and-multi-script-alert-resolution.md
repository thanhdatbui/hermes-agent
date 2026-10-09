# Location Permission Dialog & Multi-Script Farm Alert Resolution

## 1. Multi-Script Farm Alert Resolution (`_SCRIPT_METADATA`)
- **Vấn đề:** Khi có alert `[FARM ALERT: MÁY N]`, nếu chỉ mặc định trỏ về `feed_swipe_smoke.py` và `run-feed-session.ps1` sẽ làm sai lệch context khi máy đang chạy các quy trình khác như Upload Avatar, Đăng Video, Reg TikTok, 2FA, Follow.
- **Quy tắc phân giải chuẩn:**
  - `feed` / `feed-session-smoke`: `tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py` | log: `.ai-runs/latest/summary.txt`
  - `avatar` / `tiktok-upload-avatar`: `Tiktok-video/scripts/tiktok_workflow/run_post.py` | log: `run.log` | canary: `run_tiktok_upload_batch.ps1 -Tik 1 -AvatarOnly -ForceAvatarMachineList "<m>" -MaxParallel 1`
  - `upload` / `tiktok-video`: `Tiktok-video/scripts/tiktok_workflow/run_post.py` | canary: `run_tiktok_upload_batch.ps1 -Tik 1 -ForceMachineList "<m>" -MaxParallel 1`
  - `follow` / `tiktok-follow`: `tiktok-follow/follow_runner/flows/follow_engine.py` | canary: `run-follow.ps1 -Machines <m>`
  - `2fa` / `tiktok-add-2fa`: `tiktok-add-bao-mat-f2a/python_runner/run_batch_live_2fa.py`
  - `reg_tiktok` / `Tiktok_Reg`: `Tiktok_Reg/social_reg_v1.py`
  - `reg_gmail` / `register gmail`: `register gmail/scripts/run_all.ps1`

## 2. TikTok Location Permission Popup ("Chưa có gì thu hút sự chú ý của bạn sao?")
- **Dấu hiệu:**
  - Tiêu đề: `"Chưa có gì thu hút sự chú ý của bạn sao?"` / `"Nothing catching your attention?"` / `"Nothing catching your eye?"`
  - Nội dung: `"Hãy cho phép truy cập vị trí để xem thêm các bài đăng liên quan lân cận."` / `"Allow access to location to see more relevant posts nearby."`
  - Nút từ chối: `"Hủy"` (`android:id/button3`, clickable=true)
  - Nút cài đặt: `"Mở cài đặt"` (`android:id/button1`)
- **Cơ chế xử lý chuẩn:**
  - Thuộc phạm vi `automation-core` (`automation_core.tiktok.benign_popup` và `automation_core.tiktok_popup`).
  - Action dismiss: `dismiss_close_x` / `dismiss_deny_button` tap chính xác vào node `"Hủy"` / `"Cancel"` / `"Không cho phép"` / `"Don't allow"`.
  - Trong flow Upload Avatar (`Tiktok-video` / `ENSURE_AVATAR`): BẮT BUỘC gọi dọn dẹp benign popup trước khi mở màn hình Profile để tránh che khuất root gây lỗi `PROFILE_ROOT_NOT_CONFIRMED`.

## 3. Auto-Dismiss Màn Hình Sửa Hồ Sơ (Edit Profile Subpage Leftover)
- **Dấu hiệu:** Màn hình "Sửa hồ sơ" / "Thay đổi ảnh" / "Edit profile" còn sót lại từ batch upload avatar trước đó.
- **Xử lý:**
  - Detector nhận diện tiêu đề "Sửa hồ sơ" / "Thay đổi ảnh" và không có bottom navigation tabs.
  - Tự động tap node nút Quay lại (`bounds=[24,72][161,204]`, `content-desc="Quay lại"`) hoặc gửi fallback `send_device_back_key` để thoát về Home an toàn.
