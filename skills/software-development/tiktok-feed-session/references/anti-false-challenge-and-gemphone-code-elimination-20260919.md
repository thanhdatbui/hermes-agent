# Anti-False-Positive Challenge & GemPhone Code Elimination (Case 2026-09-19)

## 1. Bối cảnh sự cố (P0 False-Alarm)
- **Hiện tượng**: Hệ thống giám sát farm phát cảnh báo đỏ `🚨 [BATCH ALERT: LỖI HỆ THỐNG] ... ⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Máy M35: manual_challenge marker detected`.
- **Thực tế hiện trường**:
  - Máy M35 vẫn đang chạy TikTok For You Feed bình thường, video đang phát, không có bất kỳ captcha hay challenge nào.
  - Kiểm tra Account Switcher: Cả 7/7 nick của Máy 35 vẫn đăng nhập đầy đủ, không có tài khoản nào bị văng hay mất phiên.
  - Máy farm hoàn toàn **không cài đặt và không chạy GemPhone**.

## 2. Root Cause
1. **Giả định code cũ về GemPhone (`verify-bar-close`)**:
   - Trong `classifier.py`, code cũ đưa vào khối kiểm tra `if "verify-bar-close" in resource_ids:` với giả định đây là banner do GemPhone inject.
   - Khi khối này thấy bất kỳ từ khóa nào trong `manual_challenge_terms` (như "Xác minh", "xác minh"), nó lập tức gán nhãn `manual-needed:manual_challenge`.
2. **Quét text không giới hạn scope (Global Text Collision)**:
   - Các từ khóa xác minh được quét trên toàn bộ `texts` và `descs` của màn hình, bao gồm cả caption video (`:id/desc`), tiêu đề (`:id/title`), bình luận (`:id/comment_text`) hoặc thanh trạng thái SystemUI.
   - Một video thông thường trên Feed có chữ "xác minh" trong mô tả video đã vô tình kích hoạt cờ `manual_challenge`.
3. **Đánh đồng Captcha với Mất phiên trong `batch_aggregator.py`**:
   - `AUTH_CRITICAL_KEYWORDS` gom chung `verification`, `manual_challenge` với `login`, `văng`. Bất kỳ máy nào dính từ khóa verification đều bị quy kết thành `P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT`.

## 3. Quy chuẩn khắc phục (Standard Fix Pattern)
1. **Dẹp bỏ triệt để tàn dư GemPhone**:
   - Xóa bỏ hoàn toàn khối logic `verify-bar-close` trong `classifier.py`.
   - Xóa rule rác `verify_bar_close` khỏi `feed_swipe_smoke.py`.
   - Xóa bỏ các đường dẫn fallback ADB trỏ vào thư mục cài đặt `GemPhoneFarm`.
2. **Feed Controls Guard**:
   - Khi `_has_feed_detail_controls(elements)` là `True` (màn hình có các nút feed: like, comment, share, avatar...) HOẶC thanh điều hướng đáy (Trang chủ, Hồ sơ) đang hiển thị bình thường: **TUYỆT ĐỐI CẤM gán nhãn `manual_challenge` hoặc `manual-needed:verification`**.
   - Captcha thật của TikTok luôn là modal toàn màn hình che khuất toàn bộ feed controls.
3. **Loại trừ text video caption / comments**:
   - Khi quét từ khóa `manual_challenge` / `verification`, bắt buộc loại trừ các node có resource-id kết thúc bằng `(":id/desc", ":id/title", ":id/comment_text")` hoặc package `com.android.systemui`.
4. **Phân loại 2 cấp độ cảnh báo trong `batch_aggregator.py`**:
   - `SESSION_LOST_KEYWORDS` (`logged out`, `signed out`, `session expired`, `văng`, `login screen`): Phát cảnh báo `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]`.
   - `CHALLENGE_KEYWORDS` (`verification`, `manual_challenge`, `captcha`, `checkpoint`): Phát cảnh báo `⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]`, tuyệt đối không giật tít P0 mất phiên.
