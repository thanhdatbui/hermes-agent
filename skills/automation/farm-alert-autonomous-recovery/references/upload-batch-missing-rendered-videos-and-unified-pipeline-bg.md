# Upload Batch Missing Rendered Videos & Unified Pipeline Background Execution

## 1. Phân Biệt "Hết Video / Cần Cào" vs Lỗi Script
Khi Farm Alert báo cáo nhóm `Hết video/Cần cào (N): <danh sách máy>`:
- **Nguyên nhân cốt lõi:** Các tài khoản thuộc ca nuôi tương ứng (ví dụ Tik4 - Row 4) đã dùng hết dải video được batch render từ trước.
- **Dấu hiệu O(1):** `upload_result.json` ghi `status: "skipped"`, `reason: "video_not_rendered"`, và đường dẫn `expected_video: D:\TIKTOK-videonuoinick\<folder>\<N>.mp4`.
- **Kiểm tra hiện trường:** Soi thư mục `D:\TIKTOK-videonuoinick\<folder>`: thường dải số thứ tự bị đứt đoạn (ví dụ có 1-18 và 25-60, nhưng thiếu 19-24 chưa render).
- **Quy tắc ứng xử:** Tuyệt đối không quy nhầm `video_not_rendered` thành lỗi code hoặc lỗi thiết bị; đây là trạng thái skip chủ động và hợp lệ để bảo vệ tài khoản không bị trùng video.

## 2. Kỷ Luật Kích Hoạt `unified_patch_pipeline.py` Qua Background
Lệnh liên hoàn `python D:/Taadaa/tools/unified_patch_pipeline.py run ...`:
- Bao gồm các tầng thời gian lớn: S1 Gate B Plan (50-70s) + S2 Worker Patch (200-400s) + S3 Focused Test.
- **Cạm bẫy:** Chạy foreground thông thường sẽ bị terminal cắt ngang khi chạm ngưỡng 60s (`Exit 124`).
- **Quy trình chuẩn:**
  1. Luôn kích hoạt với `background=True, notify_on_complete=True`:
     ```python
     terminal(command="python D:/Taadaa/tools/unified_patch_pipeline.py run --repo <repo> --file <target> --task '<task>' --test-cmd '<test>' --no-canary --no-canary-reason '<reason>'", background=True, notify_on_complete=True)
     ```
  2. Dùng `process(action='wait', timeout=60, session_id=...)` hoặc `process(action='poll')` để kiểm soát nhịp, kiểm tra `D:/Taadaa/runs/<run_id>/state.json` và `plan.json`.
  3. Đợi process exit code 0 với `STATUS: AWAITING_USER` trước khi báo cáo User.

## 3. Mẫu Lỗi Post Verification & Truncated Caption Trên Remote Cluster
- **Hashtag Truncation:** Caption dài trên TikTok bị cắt gọn thành "... Xem thêm" / "... See more", làm điều kiện kiểm tra `all(tag in lowered for tag in hashtags)` thất bại. Cần hỗ trợ `truncated_match` (kiểm tra tiền tố hashtag hoặc match một phần) kết hợp gạt popup Repost (`_dismiss_repost_intro_popup`).
- **Remote Latency:** Trên cụm Remote (Admin 192.168.110.119), độ trễ ADB/mạng cao dễ làm toast "Đã đăng" trôi mất trước chu kỳ quét. Cần cho phép `recheck == "FOUND" or recheck == "SUCCESS"` ghi nhận thành công khi TikTok đã tiếp nhận submission.
