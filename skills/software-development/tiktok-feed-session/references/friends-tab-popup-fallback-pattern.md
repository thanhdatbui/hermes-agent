# Quy tắc xử lý Popup và Empty Feed khi chuyển tab Friends / Following

## Bối cảnh bài toán
Trong phiên nuôi TikTok (`feed_swipe_smoke.py`), khi runner chuyển từ tab *For You* sang tab *Friends* ("Bạn bè") hoặc *Following* ("Đang follow"):
- TikTok rất thường xuyên hiển thị popup gợi ý kết nối danh bạ (`contacts_settings_permission_dialog`, `contact_follow_suggestion`), gợi ý tính năng (`feature_promo_overlay`), hoặc trả về màn hình trống / mạng chậm (`manual-needed:network`, `manual-needed:empty`, `manual-needed:retry`).
- Sau khi cố gắng đóng popup qua allowlist hoặc blind probe, nếu màn hình vẫn còn dính marker popup (`manual-needed:popup`), runner cần quyết định có tiếp tục hay dừng.

## Nguyên lý điều phối cốt lõi

1. **Bảo toàn thứ tự an toàn của `ManualReasonGuard`:**
   - CẤM TUYỆT ĐỐI bỏ qua hoặc gọi trước `ManualReasonGuard.record()`.
   - `ManualReasonGuard` được thiết kế để yêu cầu đúng 2 lần liên tiếp (`consecutive_count >= 2`) gặp cùng lý do lỗi mới kích hoạt trạng thái dừng/chuyển hướng. Điều này bảo vệ farm khỏi việc chuyển tab non chỉ vì một popup thoáng qua.
   - Khi `ManualReasonGuard` kích hoạt trạng thái báo động, NẾU tab hiện tại là Friends hoặc Following:
     -> Không được abort toàn bộ phiên nuôi (`manual-needed`).
     -> Thực hiện **Graceful Fallback**: Chuyển hướng gõ lại tab *For You* (`tap_navigation_target`), đánh dấu `status = DEGRADED`, `safety_status = ok` để máy tiếp tục hoàn thành hạn ngạch video.
     -> Bổ sung telemetry: log `trigger_reason`, `detected`, `safety_status` vào `extra` để dễ truy vết.

2. **Quy tắc pre-push hook khi Closeout:**
   - Khi commit xong, pre-push hook đối soát `commit_sha` trong `gate_audit.jsonl` với `current_commit = git rev-parse HEAD`.
   - Nếu trước đó `closeout_gate.py` chạy trên uncommitted diff (hoặc base khác), BẮT BUỘC phải chạy lại:
     `python D:/Taadaa/tools/closeout_gate.py --repo <path> --base HEAD~1 --json-output`
     để audit binding ghi nhận commit SHA mới nhất trước khi thực hiện `git push`.
