# Network Error Retry Overlay Recovery Pattern (Case 99)

## 1. Context & Symptoms
- Khi TikTok gặp sự cố gián đoạn mạng hoặc kết nối proxy lag/chậm, app hiển thị overlay thông báo "Không có kết nối Internet", "Lỗi mạng", "Đã xảy ra lỗi", "Chạm để thử lại" / "Thử lại" / "Tap to retry".
- `classifier.py` nhận diện màn hình này là `manual-needed:network`.

## 2. Anti-Pattern
- Lạm dụng vuốt `_swipe_recovery_on_stuck`: Khi kẹt ở màn hình lỗi mạng, thao tác vuốt thông thường (`input swipe 540 1400 540 400`) không kích hoạt tải lại nội dung trong TikTok. Kết quả: sau 2 lần vuốt màn hình vẫn giữ nguyên trạng thái lỗi và runner dừng phiên.
- Bỏ sót `action_performed` validation: Dismiss handler trả về `dismissed=True` bất kể việc click/tap có thành công hay không, dẫn đến fail-open giả mạo.

## 3. Best-Practice Solution
1. **Đăng ký `network_error_retry_overlay` trong `BENIGN_POPUP_REGISTRY`:**
   - **Detector (`_detect_network_error_retry`):** Bắt buộc kiểm tra `sensitive_markers` (login, captcha, OTP, verify) đầu tiên để loại trừ ngay các màn hình nhạy cảm. Chỉ match khi có cả cặp error term + retry term, hoặc chuỗi hành động trực tiếp ("chạm để thử lại", "tap to retry").
   - **Dismisser (`_dismiss_network_error_retry`):** Bóc tách XML tìm element button/text "Thử lại", "Chạm để thử lại", "Retry" để tap chính xác tọa độ element. Nếu không tìm thấy element trong XML, fallback sang tap reload ở giữa/cuối màn hình (`h * 0.5` hoặc `h * 0.8`).
   - **Fail-Closed Gate:** Bắt buộc kiểm tra `if not action_performed: return PopupDismissResult(dismissed=False, reason="no_action_capability_on_network_error_retry")`.
   - **Gán selector:** Khi thành công, gán `selector={"action": "allowlist_dismiss", "popup_type": "network_error_retry_overlay"}`.
2. **Tích hợp vào `_capture_step`:**
   - Khi phát hiện `NETWORK_RETRY_SCREENS`, gọi `find_matching_handler` để dismiss handler trước, đợi 2.0s và recapture trước khi kích hoạt fallback nặng `_network_force_stop_recovery`.
