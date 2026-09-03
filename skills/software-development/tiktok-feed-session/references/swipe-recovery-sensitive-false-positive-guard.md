# Fallback Swipe Recovery & Sensitive Screen False-Positive Guard

## 1. Bản chất sự cố
Trong flow nuôi acc TikTok (`feed_swipe_smoke.py`), khi phát sinh màn hình lạ/không xác định hoặc popup chưa gỡ được, hệ thống có cơ chế cứu kẹt bằng 2 lượt vuốt (`_swipe_recovery_on_stuck`).
Trước khi thực hiện vuốt, hàm `_is_sensitive(d_screen, xml_str, ocr_str)` kiểm tra xem màn hình hiện tại có phải màn hình nhạy cảm (Login, OTP, Captcha, Verification) hay không để tránh vuốt nhầm làm hỏng luồng xác thực tài khoản.

## 2. Anti-Pattern: Quét thô chuỗi XML
- Nếu quét chuỗi thô trên toàn bộ `xml_str`:
  ```python
  combined = f"{xml_str or ''} {ocr_str or ''}".lower()
  sensitive_tokens = ("đăng nhập", "log in", "sign up", "đăng ký", ...)
  return any(term in combined for term in sensitive_tokens)
  ```
- Trên các thiết bị Android (đặc biệt là Samsung Galaxy S7), thanh thông báo hệ thống (`com.android.systemui`, vùng $y \le 100$) thường xuyên có thông báo chạy nền từ Google Play:
  `desc='Dịch vụ Google Play notification: Yêu cầu đăng nhập'`
- Quét thô chuỗi XML sẽ lập tức bị **dương tính giả (False-Positive)** $\rightarrow$ tưởng nhầm là màn Login TikTok $\rightarrow$ `_swipe_recovery_on_stuck` abort (`return None`) $\rightarrow$ dừng phiên và khóa máy giữ hiện trường, làm tê liệt toàn bộ cơ chế fallback 2 lần vuốt.

## 3. Pattern chuẩn: Lọc bỏ System UI & Status Bar
Khi kiểm tra từ khóa nhạy cảm trong XML:
1. Phân tích cây XML (`parse_xml(xml_str)`).
2. Bỏ qua hoàn toàn các node thuộc package hệ thống:
   - `com.android.systemui`
   - `com.sec.android.app.launcher` (hoặc các launcher khác)
   - `com.google.android.gms`
3. Bỏ qua các node có bounds nằm hoàn toàn trong thanh status bar ($y \le 100$).
4. Chỉ gom `text`, `content-desc`, `resource-id` của các node còn lại (thuộc app TikTok) để so khớp với `sensitive_tokens`.

## 4. Bổ sung Resource-ID cho Feature Promo Popup
Với popup dạng dialog "Tìm hiểu thêm" / "Đóng" (`feature_promo_overlay` / `learn_more_dialog_dismiss`):
- Nút "Đóng" trên các layout TikTok mới thường mang ID: `com.ss.android.ugc.trill:id/i2y`, `tv_close`, `close_btn`, `hwn`.
- Cần đảm bảo `action_xpath` trong `GEMPHONEFARM_BLIND_POPUP_RULES` bao phủ đầy đủ các resource-id này để popup được bấm tắt ngay lập tức thay vì phải chờ fallback.
