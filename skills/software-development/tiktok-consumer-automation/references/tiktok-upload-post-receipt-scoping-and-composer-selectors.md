# TikTok Upload: Idempotency Post Receipt Scoping & Composer Selectors Recovery

## 1. Idempotency Post Receipt Scoping (Cross-Account & Cross-Run)
- **Vấn đề**: Khi một máy farm chạy luân phiên nhiều tài khoản (hoặc các phiên chạy khác nhau qua ngày), receipt `completed` hoặc `verification_pending` cũ từ phiên trước (hoặc của tài khoản trước, e.g. `muyduyen4589`) có thể bị nạp nhầm vào phiên của tài khoản mới (`phannhu185`), khiến bước `POST` hiểu nhầm là đã tap trong cùng phiên và từ chối tap hoặc fail-closed subprocess với lỗi `upload_subprocess_nonzero`.
- **Quy tắc chuẩn**:
  1. **Run-ID Scoping**: Receipt có status `completed` từ một `run_id` khác phiên hiện tại phải được bỏ qua khi kiểm tra idempotency trong bước `_handle_post` và `_record_post_intent`.
  2. **Target-Account Scoping**: Khi `target_account` được xác định, `_load_post_attempt_receipt` và `_receipt_matches_target_account` phải kiểm tra strict matching theo `target_account`.
  3. **Auto-Advance Video Path Sync**: Khi phát hiện video đã được verify trong ledger (`_auto_advance_verified_videos`), phải cập nhật ngay lập tức cả `video_number` và `self.context.video_path` sang video tiếp theo để tránh drift giữa metadata và file push.

## 2. UIAutomator Helper App Foreground Occlusion
- **Vấn đề**: Khi `atx-agent` khởi động hoặc reset uiautomator stub package (`com.github.uiautomator`, `com.github.uiautomator.test`), ứng dụng helper có thể chiếm foreground đè lên màn hình TikTok trong các state `OPEN_TIKTOK`, `WAIT_FEED`, `ACCOUNT_SWITCHER`.
- **Xử lý**:
  1. Trong `_handle_open_tiktok`, `_wait_for_feed` và `_account_switcher`: nếu phát hiện `com.github.uiautomator` trong foreground, tự động force-stop helper app và bring TikTok trở lại foreground (`_bring_adapter_to_foreground`).
  2. Tuyệt đối không dùng `monkey -p com.github.uiautomator 1` để kích hoạt stub vì monkey sẽ mở giao diện Activity của helper lên màn hình người dùng.

## 3. TikTok Composer Selectors Mở Rộng
- **Post Button**: Các resource-id nút Đăng/Post mở rộng trên các bản cập nhật TikTok gồm: `t66`, `sox`, `soz`, `sp7`, `sh8`, `shd`, `rbp`, `post_action`, `post_button`.
- **Caption Field**: Bổ sung resource-id `h3a`, `g9u`, `gv0`, `caption_edit_text`, `description_edit_text`, `post_description`, `edit_text` và fallback class `EditText`.
- **LIVE Mode Switch**: Nếu camera mở ở tab LIVE (chứa `text="Phát LIVE"` / `text="Trung tâm LIVE"` / `text="LIVE"`), tự động tap chuyển sang tab `ĐĂNG` hoặc `TẠO`.

## 4. An toàn Caption Input & Verification trên Samsung Android 8
- **Clipboard Broadcast**: Lệnh `am broadcast -a clipboard.set` có thể bị timeout/treo trên các máy không cài sẵn Clipper app. Phải bọc try/except với timeout ngắn và fallback an toàn sang tokenized typing hoặc nút `# Hashtag` của TikTok.
- **Caption Visibility Gate**: Khi gõ hashtag, TikTok có thể mở dropdown gợi ý làm che hoặc format hashtag thành tag pill. `_caption_is_visible` chỉ cần xác nhận ít nhất một hashtag hợp lệ trong caption xuất hiện trên UI dump trước khi chuyển sang bước Post.
