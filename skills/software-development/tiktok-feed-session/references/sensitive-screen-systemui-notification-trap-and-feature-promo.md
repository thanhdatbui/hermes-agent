# Sensitive Screen SystemUI Notification False-Positive & Feature Promo Overlay Handling

## 1. Hiện tượng & Bối cảnh (Sự cố Máy 45 — 31/08/2026)
- Phiên chạy `multi-machine-feed-session` dừng lại với lý do `unexpected popup/dialog marker detected` (`manual-needed:popup`).
- Màn hình chứa popup dạng `feature_promo_overlay` ("Tìm hiểu thêm" kèm nút "Đóng" `com.ss.android.ugc.trill:id/i2y`).
- Người dùng đã thiết kế cơ chế fallback vuốt 2 cái (`_swipe_recovery_on_stuck`) khi gặp màn hình lạ/kẹt không xử lý được, nhưng cơ chế này **không kích hoạt** mà phiên vẫn dừng lại.

## 2. Phân tích nguyên nhân gốc (Root Causes)

### A. Dương tính giả `_is_sensitive` từ thông báo System UI (Google Play)
- Trong `_swipe_recovery_on_stuck`, hàm `_is_sensitive(d_screen, xml_str, ocr_str)` được gọi để ngăn chặn việc vuốt trên các màn hình nhạy cảm (Login, OTP, Captcha, Verification).
- Hàm thực hiện so khớp chuỗi thô:
  `combined = f"{xml_str or ''} {ocr_str or ''}".lower()`
  và kiểm tra danh sách `sensitive_tokens = ("đăng nhập", "log in", "sign up", "đăng ký", ...)`
- Trên các máy Android/Samsung S7, thanh trạng thái hệ thống (`com.android.systemui`, top bar $y < 72$) thường xuyên có icon/thông báo nền từ Google Play:
  `desc='Dịch vụ Google Play notification: Yêu cầu đăng nhập'`
- Việc tìm kiếm chuỗi con trên toàn bộ XML mà không lọc `com.android.systemui` khiến `_is_sensitive` bắt trúng `"đăng nhập"` của Google Play $\rightarrow$ nhận diện nhầm màn hình hiện tại là màn hình Đăng nhập TikTok $\rightarrow$ lập tức abort (`return None`) để fail-closed $\rightarrow$ **chặn đứng hoàn toàn 2 lượt vuốt fallback cứu kẹt**.

### B. Thiếu đăng ký popup `feature_promo_overlay` trong Registry
- Trong `automation-core`, hàm `detect_feature_promo_overlay` đã nhận diện được cấu trúc popup này (nút "Tìm hiểu thêm" + nút "Đóng").
- Tuy nhiên, popup này **chưa được đăng ký vào `BENIGN_POPUP_REGISTRY`** trong `flows/benign_popup_registry.py`.
- Khi `classify_screen` nhận diện ra `manual-needed:popup` với lý do `known feature_promo_overlay popup detected`, bộ gỡ popup tự động `drain_known_popups` / `find_matching_handler` không tìm thấy handler phù hợp để tap nút "Đóng" `i2y`.

### C. Va chạm detector `learn_more_dialog_dismiss` với sticker CTA in-feed
- Rule `learn_more_dialog_dismiss` trong `GEMPHONEFARM_BLIND_POPUP_RULES` dùng detector XPath tìm text `"Tìm hiểu thêm"` nhưng bắt dính cả nhãn quảng cáo dán trên video in-feed (`resource-id="com.ss.android.ugc.trill:id/o6x"`).
- Khi không có dialog thật, `action_xpath` tìm nút "Đóng" bị miss $\rightarrow$ blind checkpoint trả về `success=False` $\rightarrow$ flow đánh dấu `manual-needed:popup` sai cho video đang chạy bình thường.

## 3. Quy tắc & Giải pháp chuẩn

1. **Lọc sạch `com.android.systemui` và Status Bar khi check sensitive:**
   - Trong `_is_sensitive`, khi có `xml_str`, bắt buộc parse cây XML và lọc bỏ các node thuộc `com.android.systemui`, `com.sec.android.app.launcher`, `com.google.android.gms` hoặc có tọa độ đáy $y \le 100$.
   - Chỉ thu thập text/desc/resource-id từ các node thuộc package TikTok mục tiêu trước khi so khớp với `sensitive_tokens`.

2. **Đồng bộ 100% giữa Core Detectors và Consumer `BENIGN_POPUP_REGISTRY`:**
   - Mọi popup được định nghĩa trong `automation_core.tiktok.benign_popup` (như `feature_promo_overlay`, `live_campaign_overlay`, v.v.) BẮT BUỘC phải có entry tương ứng trong `flows/benign_popup_registry.py` kèm hàm dismisser (tap nút "Đóng" / Back key).

3. **Cập nhật ID nút Đóng mới cho `GEMPHONEFARM_BLIND_POPUP_RULES`:**
   - Thêm `@resource-id="com.ss.android.ugc.trill:id/i2y"` vào `action_xpath` của `learn_more_dialog_dismiss`.
