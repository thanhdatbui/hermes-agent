# Profile Video Grid Scan Baseline & Scroll Behavior (Upload Workflow)

## Context & Purpose
Trong quy trình đăng video (`D:/Taadaa/Tiktok-video`), tại state `ACCOUNT_READY`, runner tự động quét lưới video trên profile để xác định `pre_post_video_count` (baseline trước khi post).

### Mục đích
1. **Chống đăng trùng (Anti-Duplicate Post):** Khi mạng lag, timeout ADB hoặc TikTok văng/crash sau khi tap "Đăng", runner quay lại Profile đếm lại video. Nếu số video tăng so với baseline -> ghi nhận đã đăng thành công thay vì re-post.
2. **Nhận diện Drafts:** Phân biệt video đã publish với bản nháp còn đọng lại trên profile.

## Hành vi UI trên thiết bị thật (Không phải lỗi / Không phải treo)
- **Cuộn xuống (Swipe Up):** `adapter.scroll_profile_grid()` (`scripts/tiktok_workflow/adapter.py:1180`) thực hiện vuốt tối đa 6 lần (`profile_grid_max_swipes`, default 6) để đọc hết viewports các video cũ trong grid.
- **Cuộn ngược lên đầu (Restore Top):** `_restore_profile_grid_top()` (`adapter.py:1260`) thực hiện vuốt từ trên xuống để đưa profile trở lại vị trí ban đầu trước khi chuyển sang các bước tiếp theo (`RESOLVE_NEXT_VIDEO` -> `MEDIA_PUSH` -> `VIDEO_PICK`).
- **Hiện tượng quan sát được:** Màn hình profile của thiết bị tự động cuộn lên / cuộn xuống nhiều lần liên tiếp trước khi mở picker đăng video.

## Phân biệt với các luồng thao tác khác
- **Upload Flow (TikTok-video):** Cuộn đếm lưới video ở `ACCOUNT_READY` + restore top. Bước `VERIFY_POST` sau khi bấm đăng **không** dùng swipe kiểm tra mà dựa vào marker UI (`post_success`, `upload_done`) hoặc đối soát baseline khi phục hồi.
- **Follow Flow (TikTok-follow):** Pull-to-refresh (vuốt kéo reload profile) sau khi follow để phá cache nút "Nhắn tin" và kiểm tra xem có bị server nhả follow không.
