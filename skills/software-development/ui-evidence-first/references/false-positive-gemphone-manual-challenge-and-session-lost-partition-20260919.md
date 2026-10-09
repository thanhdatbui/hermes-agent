# Bẫy Alert Láo Manual Challenge từ Tàn Dư GemPhone & Phân Biệt Session-Lost P0 (19/09/2026)

## 1. Bối Cảnh & Hiện Tượng
- **Cảnh báo Telegram giật tít:** `🚨 [BATCH ALERT: LỖI HỆ THỐNG] ... ⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện 1 máy dính lỗi login/xác minh: Máy M35: manual_challenge marker detected`.
- **Hiện trường thực tế:** Máy 35 phát video For You bình thường, Account Switcher đủ 7/7 nick, không hề có captcha, văng tài khoản hay mất phiên.

## 2. Nguyên Nhân Kép (Root Cause)
1. **Tàn dư giả định GemPhone trong `python_runner/core/classifier.py`:**
   - Dev cũ giả định view `verify-bar-close` là do GemPhoneFarm inject.
   - Khi `verify-bar-close` xuất hiện (hoặc node view cùng tên), code quét toàn bộ text/desc màn hình tìm `manual_challenge_terms = ("xác minh", "manual_challenge", ...)`.
   - Video caption trên Feed (`:id/desc`, `:id/title`) hoặc comment vô tình chứa từ "xác minh" $\rightarrow$ Classifier gắn cờ `manual-needed:manual_challenge`.
2. **Gộp chung Auth Critical trong `batch_aggregator.py`:**
   - Cũ: Gom `AUTH_CRITICAL_KEYWORDS = ("login", "account screen", "verification", "checkpoint", "auth", "văng", "identity")`.
   - Mọi lỗi chứa `verification` hay `manual_challenge` bị tự động đẩy vào nhóm `[P0 MẤT PHIÊN / VĂNG ACCOUNT]`, gây hoang mang cho user.
3. **Thực tế Farm:** Farm hoàn toàn không chạy và không cài GemPhone (`pm list packages | grep -i gem` = 0).

## 3. Quy Chuẩn Khắc Phục (Invariant)
1. **Dẹp bỏ toàn bộ tàn dư GemPhone & verify-bar-close:**
   - Xóa bỏ hoàn toàn khối `if "verify-bar-close" in resource_ids:` trong `classifier.py`.
   - Xóa bỏ rule `verify_bar_close` trong danh sách blind popup của `feed_swipe_smoke.py`.
2. **Chốt chặn Feed Detail Controls Guard:**
   - Khi màn hình có đầy đủ nút tương tác Feed (`_has_feed_detail_controls(elements)`: like, comment, share, avatar...) $\rightarrow$ **CẤM TUYỆT ĐỐI gán nhãn `manual_challenge` hay `verification`**.
   - Khi quét text kiểm tra verification/challenge, bắt buộc loại trừ các node caption (`:id/desc`, `:id/title`), comment (`:id/comment_text`) và `com.android.systemui`.
3. **Phân biệt rạch ròi 2 mức độ cảnh báo trong `batch_aggregator.py`:**
   - `SESSION_LOST_KEYWORDS`: `"logged out"`, `"signed out"`, `"văng"`, `"session expired"`, `"phiên đã hết hạn"`, `"login screen"`, `"account screen"`, `"đăng nhập lại"`, `"require_login"` $\rightarrow$ Bắn cảnh báo **`⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]`**.
   - `CHALLENGE_KEYWORDS`: `"verification"`, `"manual_challenge"`, `"checkpoint"`, `"captcha"`, `"verify"` $\rightarrow$ Bắn cảnh báo **`⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]`** (chưa mất phiên).
