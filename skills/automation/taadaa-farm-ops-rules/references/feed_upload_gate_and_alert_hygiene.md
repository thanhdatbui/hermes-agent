# Feed Upload Gate & Alert Hygiene Invariants (2026-10-01)

## 1. QUY TẮC UPLOAD KHI FEED THẤT BẠI vs PROXY PREFLIGHT GATE
- **User Rule (2026-10-01):** Kể cả Feed Session thất bại (0 swipe, lỗi UI, manual-needed...), máy **VẪN ĐƯỢC PHÉP TIẾP TỤC CHẠY UPLOAD VIDEO** theo lịch.
- **Vị trí áp dụng:** `multi_machine_feed_session.py`: Trong `_run_upload_hook()`, tuyệt đối cấm chặn upload chỉ vì `child_result.final_status != "success"` hay feed stop reason.
- **Chốt chặn duy nhất là Proxy/VPN Fail-Closed:**
  - Trong `Tiktok-video/scripts/tiktok_workflow/run_post.py`: Bổ sung kiểm tra `require_android_vpn` ngay đầu hàm `run_real()` / `run_post()` trước khi chạm vào UI hay khởi tạo `StateMachine`.
  - Nếu proxy/VPN bị timeout, rớt mạng hoặc unreachable:
    - Exit code 2 ngay lập tức.
    - Lưu report `FAILED` với `error_type: PREFLIGHT_VPN_BLOCKED` (nếu là `ConsumerPreflightError`) hoặc `PREFLIGHT_SETUP_ERROR` (nếu lỗi setup mapping).
    - **TUYỆT ĐỐI CẤM** mở app TikTok, dump UI hoặc nhảy vào Account Switcher khi mạng đang lỗi.

## 2. KỶ LUẬT ALERT FARM & CHỐNG SPAM MULTILINE RAW
- **Cấm nhận nhầm Proxy/VPN thành Captcha:**
  - Trong `automation-core/src/automation_core/batch_aggregator.py`: Lỗi proxy egress timeout (`egress IP verification failed`) có chứa chữ `verification` nhưng **TUYỆT ĐỐI KHÔNG** được xếp vào `CẢNH BÁO XÁC MINH / CAPTCHA`.
  - `CHALLENGE_EXCLUSIONS` bắt buộc loại trừ: `ip verification`, `verification failed`, `egress`, `proxy`, `vpn`.
- **Chuẩn hóa Inline Error (Collapse Multiline):**
  - Mọi thông báo lỗi đưa vào alert Telegram bắt buộc qua hàm `_format_inline_error(text, max_len=160)`: ép toàn bộ whitespace, newline (`\n`, `\r`) thành 1 khoảng trắng duy nhất qua `' '.join(text.split())`.
  - **CẤM TUYỆT ĐỐI** xả nguyên khối raw HTTP headers (`GET /ip HTTP/1.1\nHost: ...`) hoặc các dòng trống làm loãng kênh chat.

## 3. OUTLOOK APP ONBOARDING TRÊN FARM ANDROID CŨ (S7)
- Khi app Outlook trên máy farm chưa đăng nhập tài khoản nào (fresh install hoặc clear data), nó sẽ kẹt ở onboarding carousel (`Chào mừng bạn đến với Outlook`).
- `read_tiktok_otp_from_outlook_app` sẽ timeout và báo `OUTLOOK_APP_INBOX_NOT_VERIFIED`.
- **Flow xử lý chuẩn:**
  1. Nhấn `THÊM TÀI KHOẢN` (`com.microsoft.office.outlook:id/btn_primary_button`).
  2. Nhập email Hotmail -> nhấn `TIẾP TỤC`.
  3. Chọn provider `Outlook` (`btn_add_account_outlook`).
  4. Nhập mật khẩu trong Microsoft WebView -> nhấn `Tiếp theo`.
  5. Màn hỏi thêm tài khoản khác -> bấm `CÓ LẼ ĐỂ SAU`.
  6. Đi qua 2 màn Privacy Tour (bấm `TIẾP THEO` -> `TIẾP TỤC VỚI OUTLOOK`) để vào đến Hộp thư đến (Inbox).
