# Đối soát tài khoản sau phiên nuôi (Profile Verification & UI Lag Recovery)

## Vấn đề thực tế (21/08/2026 - Máy 15)
- Khi kết thúc phiên lướt nuôi (`feed-session-smoke`), script chuyển sang màn hình Hồ sơ để đối soát username TikTok (`_verify_profile_after_session`).
- Khi thiết bị Android bị lag chuyển cảnh, lệnh tap vào tab *Hồ sơ* thành công nhưng UI TikTok tải chậm: node `@username` chưa kịp xuất hiện trong cây UI XML lần đọc 1 (chỉ mới hiện text `Thêm tiểu sử` hoặc `Hồ sơ`).
- Nếu đánh giá ngay ở lần đọc 1, script sẽ kết luận sai là `profile account mismatch` và kích hoạt dừng phiên / báo động giả lên Telegram.

## Quy tắc xử lý chuẩn trong script
1. Khi kiểm tra XML lần 1 không thấy khớp `ctx.account`:
   - Không kết luận `mismatch` ngay lập tức.
   - Thêm nhịp nghỉ: `time.sleep(1.5)`.
   - Chụp lại cây UI XML lần 2: `retry_xml = _capture_xml_text(ctx, f"{artifact_prefix}_profile_retry")`.
2. Phân tích lại danh sách text trong `retry_xml`:
   - Nếu tìm thấy `@username` khớp với `ctx.account` $\rightarrow$ Đánh dấu `matched = True`, cập nhật `profile_verify_status = "matched"` và hoàn thành phiên thành công.
   - Nếu sau retry lần 2 vẫn không thấy $\rightarrow$ Mới xác nhận `mismatch` và kích hoạt quy trình giữ hiện trường an toàn.
