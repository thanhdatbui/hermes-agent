# Feed Detail Controls Guard & False Manual Challenge Fix (2026-09-19)

## 1. Vấn đề
- Video caption (`:id/desc`), mô tả (`:id/title`) hoặc bình luận (`:id/comment_text`) trên TikTok For You feed thường xuyên chứa các từ khóa như `"xác minh"`.
- Classifier cũ quét text toàn màn hình và kiểm tra tàn dư `verify-bar-close` (GemPhone). Khi thấy `"xác minh"`, classifier tự gán nhãn `manual-needed:manual_challenge` hoặc `manual-needed:verification`, làm dừng phiên và gửi cảnh báo P0 giả.

## 2. Giải pháp kỹ thuật đã chốt
1. **Feed Detail Controls Guard:**
   - Kiểm tra `_has_feed_detail_controls(elements)`: nếu màn hình đang hiển thị các nút like, comment, share, avatar... thì đây là video feed hợp lệ.
   - Khi đó, TUYỆT ĐỐI CẤM gán nhãn `manual_challenge` hoặc `verification` dựa trên text quét được.
2. **Loại bỏ tàn dư GemPhone:**
   - Xóa bỏ hoàn toàn khối `if "verify-bar-close" in resource_ids:` trong `classifier.py`.
   - Xóa rule rác `verify_bar_close` trong danh sách blind popup rules của `feed_swipe_smoke.py`.
3. **Phân loại cảnh báo chuẩn hóa (`batch_aggregator.py`):**
   - Chỉ gắn nhãn `[P0 MẤT PHIÊN / VĂNG ACCOUNT]` khi gặp các lỗi session thật (`logged out`, `signed out`, `session expired`, `login screen`, `account screen`).
   - Lỗi captcha/thử thách chỉ được báo ở cấp độ `[CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]`.
