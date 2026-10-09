# False P0 Manual Challenge & GemPhone Tàn Dư Purge (2026-09-19)

## 1. Sự Cố & Triệu Chứng
- **Alert:** `[BATCH ALERT: LỖI HỆ THỐNG] P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT` trên Máy 35: `manual_challenge marker detected`.
- **Thực tế:** Máy 35 phát video For You feed bình thường, đầy đủ 7/7 tài khoản trên Account Switcher, không mất phiên, không có captcha.

## 2. Nguyên Nhân Gốc Rễ (2 Tầng)
1. **Lỗi Classifier (`classifier.py`)**:
   - Tàn dư code GemPhone cũ kiểm tra `if "verify-bar-close" in resource_ids:`.
   - Kết hợp quét text toàn màn hình (`texts`, `descs`) tìm từ khóa `"xác minh"`.
   - Khi một video bình thường trên Feed có caption hoặc mô tả chứa từ "xác minh", classifier tự động gán nhãn `manual-needed:manual_challenge`.
2. **Lỗi Batch Aggregator (`batch_aggregator.py`)**:
   - Gom chung `verification`, `manual_challenge`, `checkpoint` vào `AUTH_CRITICAL_KEYWORDS` cùng với `login`, `văng`.
   - Khiến lỗi xác minh/captcha tạm thời bị thổi phồng thành `P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT`.

## 3. Quy Tắc Khắc Phục (Invariant)
1. **Feed Controls Guard**:
   - Khi màn hình có các controls tương tác feed (`_has_feed_detail_controls`: like, comment, share, avatar...), TUYỆT ĐỐI KHÔNG gán nhãn `manual_challenge` hay `verification` do text trong caption/bình luận.
2. **Tách Biệt 2 Cấp Độ Cảnh Báo trong `batch_aggregator.py`**:
   - `SESSION_LOST_KEYWORDS`: Chỉ khi có keyword mất phiên thật (`logged out`, `signed out`, `văng`, `session expired`, `login screen`, `account screen`) mới kích hoạt `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]`.
   - `CHALLENGE_KEYWORDS`: Các lỗi captcha/thử thách chỉ được báo là `⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]`.
   - **Đặc biệt lưu ý blocker gộp `login-gms-verification`:** Bắt buộc ưu tiên kiểm tra `CHALLENGE_KEYWORDS` trước (trên `error_message` hoặc `error_type` thuần challenge), tránh để chữ `"login"` trong blocker type làm đè các lỗi captcha/challenge sang P0 mất phiên.
3. **Pitfall Nút Đóng Captcha WebView `verify-bar-close`**:
   - Trong `benign_popup.py`, hàm `_find_captcha_puzzle_close_x` từng exclude `verify-bar-close`. Tuy nhiên thực tế nút X đóng puzzle captcha của TikTok WebView nằm ở góc trên bên phải lại mang đúng id `verify-bar-close`.
   - Cấm exclude mù quáng nếu nút nằm ở góc trên bên phải của khung captcha (`in_top_right(element)`).
4. **Kỷ Luật Tự Tìm Log Runtime (Cấm Hỏi Lại User)**:
   - Toàn bộ log và artifact của các ca nuôi nằm tại: `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/<session>/machines/machine_<N>/<timestamp>/` (`summary.txt`, `log.jsonl`, `artifacts/...`).
   - Phải chủ động đọc log tại đường dẫn này, tuyệt đối cấm hỏi user "code ở đâu / log ở đâu".
