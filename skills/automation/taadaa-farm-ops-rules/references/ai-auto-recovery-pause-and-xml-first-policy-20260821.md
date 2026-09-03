# Quy Tắc Tạm Dừng AI Auto-Recovery & Enforce XML-First (2026-08-21)

## 1. Tạm Dừng Autonomous AI Auto-Recovery Subprocess
- **Trạng thái:** Chế độ tự động kích hoạt `ai_recovery/agent.py` từ `automation_core.alerts.send_farm_machine_alert` đã được TẠM THỜI TẮT theo chỉ thị của người dùng.
- **Hành vi Alerts:** Khi máy gặp lỗi / kẹt màn hình:
  1. Chụp ảnh màn hình đính kèm Banner Đỏ `[MAY XX] - HH:MM:SS DD/MM`.
  2. Gửi ảnh và thông tin chi tiết lỗi vào nhóm Telegram Farm Alerts (`-5373649734`).
  3. **GIỮ NGUYÊN HIỆN TRƯỜNG:** Máy dừng lại ở màn hình lỗi để người dùng kiểm tra trực quan và ra lệnh xử lý thủ công cho Hermes Agent. Tuyệt đối KHÔNG tự động spawn background subprocess AI can thiệp máy.

## 2. Enforce XML-First & Loại Bỏ 100% Tọa Độ Cứng
- Mọi hàm xử lý popup / overlay (`benign_popup.py`, `benign_popup_registry.py`) và luồng điều hướng UI BẮT BUỘC dùng **XML Element Bounds**:
  - `parse_xml`, `find_element`, `iter_elements`, `bounds.center`.
- **Cấm Tuyệt Đối Hardcoded Tap Coordinates:** Không dùng `ctx.tap(x, y)` với tọa độ pixel mù.
- **Fail-Closed An Toàn:** Nếu không tìm thấy element trong XML:
  - Trả về `dismissed=False` (NO-OP, không tap mù).
  - Hoặc dùng `KEYCODE_BACK` có hậu kiểm cho các màn hình fullscreen (Camera, LIVE, WebView).

## 3. Policy Firewall Trong `safe_executor.py`
- Đối với AI Auto-Recovery (khi chạy thủ công hoặc kiểm thử):
  - **Strict Leaf Node Validation:** Tọa độ tap phải nằm trong XML leaf node hợp lệ (có metadata hoặc clickable), loại bỏ root fullscreen container `[0,0][1080,1920]`.
  - **Ad/Survey Firewall:** Màn hình quảng cáo / survey BẮT BUỘC `swipe`, chặn tuyệt đối lệnh `tap`.
  - **Account Logged Out Quarantine:** Khi phát hiện popup đăng xuất -> Dừng phiên cách ly nick, CẤM bấm nút OK/Login.
